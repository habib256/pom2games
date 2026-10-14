; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Found shelter and a first text TOPO. No disk loads while this module runs:
; transitions tail-call show_view, which may replace the shared window.
.segment "SITES"
module_site:
        lda     #1
        sta     ui_dirty
        lda     verb
        cmp     #V_ENTER
        beq     @enter
        cmp     #V_EXIT
        beq     @exit
        lda     #<site_leave
        ldx     #>site_leave
        jmp     message
@enter: lda     noun
        cmp     #137             ; SHELTER, not manufactured HUT (95)
        bne     @specific
        lda     tree_in
        beq     :+
        jmp     do_tree          ; tail-call resident loader before replacing SITES
:
        lda     shelter_inside
        bne     @already
        lda     MAP+16
        beq     @absent
        lda     px+1
        cmp     MAP+17
        bne     @absent
        lda     py+1
        cmp     MAP+18
        bne     @absent
        lda     MAP+37
        beq     :+
        lda     px
        cmp     MAP+34
        bne     @absent
        lda     py
        cmp     MAP+35
        bne     @absent
:       lda     #1
        sta     shelter_inside
        lda     #0
        sta     animal_kind
        jmp     show_view
@exit:  lda     noun
        cmp     #137
        bne     @specific
        lda     shelter_inside
        beq     @outside
        lda     #0
        sta     shelter_inside
        sta     scene_minutes
        lda     night
        bne     @exit_view       ; dark view supplies its own single message
        lda     #<site_outside
        ldx     #>site_outside
        jsr     message
@exit_view:
        jmp     show_view
@specific:
        lda     #<site_specific
        ldx     #>site_specific
        jmp     message
@absent:
        lda     #<site_absent
        ldx     #>site_absent
        jmp     message
@already:
        lda     #<site_already
        ldx     #>site_already
        jmp     message
@outside:
        lda     #<site_outside
        ldx     #>site_outside
        jmp     message

module_shelter_view:
        lda     #0
        sta     scene_drawn
        sta     scene_minutes        ; indoor time cannot roll outdoor fauna
        sta     tmp
        lda     #40
        sta     tmp2
        jsr     clear_rows
        ; Keep action results (REST, meals...) visible. A fresh VIEW supplies
        ; the indoor description when the command has no message yet.
        lda     shown
        bne     @done
        lda     #<site_inside
        ldx     #>site_inside
        jmp     message
@done:  rts

site_inside: .byte "YOU ARE INSIDE THE CABIN.|USE EXIT SHELTER TO GO OUTSIDE.",0
site_outside: .byte "YOU ARE OUTSIDE THE SHELTER.",0
site_already: .byte "YOU ARE ALREADY INSIDE THE SHELTER.",0
site_absent: .byte "THERE IS NO SHELTER HERE.",0
site_specific: .byte "USE ENTER SHELTER OR EXIT SHELTER.|CRAFTED SHELTERS ARE NOT AVAILABLE.",0
site_leave: .byte "EXIT SHELTER BEFORE TRAVELLING.",0

; MAP fills the 80 x 24 text screen: 40 x 24 cells of the 112 x 84 grid, two
; 80-column characters per cell (square on screen), north up, centred on
; the player and clamped to the grid. Row 0 starts with a short inverse cue
; (minutes travelled while walking, the player's cell, magnetic heading
; and cardinal, the site under P); every other character is map. Arrow keys
; (or WASD) scroll, C recentres; Return, Space and Escape return to the
; view (kept intact: MAP only writes the text page). During WALK/SWIM the
; window stays put: a half-step rewrites P's old and new cells and the
; changed characters of the cue; within TOPO_MARGIN cells of an edge it
; scrolls by a quarter window (one full differential redraw).
; docs/IMPLEMENTATION.md "MAP plein écran 80 × 24".
TOPO_W = 40                     ; cells across
TOPO_H = 24                     ; cells down
TOPO_MARGIN = 4                 ; walking this close to an edge scrolls
.segment "RESBSS"
; Resident (TRAVEL replaces SITES at every half-step), cleared at boot by the
; loader like the rest of RESBSS (BSS of the GAME area is full since lot 9 and
; LOOK UP/DOWN), not journey state: SAVE leaves it out (src/save.s sv_ranges).
topo_x: .res 1                  ; window origin (cells); topo_y follows
topo_y: .res 1
topo_px: .res 1                 ; the cell where the walk last drew P
topo_py: .res 1
topo_cue_end: .res 1            ; cells under that cue; 0: no walking map shown
.export topo_cue_end
.segment "SITES"
module_topo:
        lda     #0
        sta     topo_walk
        jsr     topo_center
        jmp     topo_redraw

; One update per WALK/SWIM half-step. Simulation already hides HGR;
; preserve its code and the message cursor. The end of the walk clears
; rows 20-23 and topo_cue_end (game.s do_walk) for the results.
module_topo_moving:
        lda     CH
        pha
        lda     CV
        pha
        lda     #1
        sta     topo_walk
        jsr     topo_follow
        bcc     @step
        jsr     topo_draw       ; first update or scroll: the whole screen
        jmp     @drawn
@step:  jsr     text_begin      ; same window: two cells and the cue
        lda     topo_px
        ldx     topo_py
        jsr     topo_put_cell   ; the terrain or site P leaves (P if it stays)
        lda     px+1
        ldx     py+1
        jsr     topo_put_cell
        lda     #0
        jsr     vtab
        jsr     topo_cue        ; A = where the previous cue ended
        jsr     topo_span       ; the map a shorter cue uncovers
@drawn: lda     px+1
        sta     topo_px
        lda     py+1
        sta     topo_py
        jsr     text_release
        lda     #20
        sta     WNDTOP
        pla
        jsr     vtab
        pla
        sta     CH
topo_moving_done:
        rts

; topo_follow -- C set when the walk needs a full redraw: no walking map on
; screen yet, P outside the window (recentred once), or P within
; TOPO_MARGIN cells of an edge (a quarter window that way, clamped to the
; grid, like the arrows). C clear: same window, P's last cell still shown.
topo_follow:
        lda     topo_x
        sta     topo_cols       ; scratch: the window before
        lda     topo_y
        sta     topo_rows
        ldx     #0              ; X: axis (topo_x, topo_y); Y: px+1, py+1
        ldy     #0
@axis:  lda     px+1,y
        sec
        sbc     topo_x,x        ; P's cell in the window
        bcc     @centre
        cmp     topo_size,x
        bcs     @centre
        cmp     #TOPO_MARGIN
        bcc     @back
        adc     #TOPO_MARGIN-1  ; C set: + TOPO_MARGIN
        cmp     topo_size,x
        bcc     @next
        lda     topo_x,x
        clc
        adc     topo_quarter,x
        cmp     topo_max,x
        bcc     @set
        lda     topo_max,x
        bcs     @set
@back:  lda     topo_x,x
        sec
        sbc     topo_quarter,x
        bcs     @set
        lda     #0
@set:   sta     topo_x,x
@next:  iny
        iny
        inx
        cpx     #2
        bcc     @axis
        lda     topo_cue_end
        beq     @redraw
        lda     topo_x
        cmp     topo_cols
        bne     @redraw
        lda     topo_y
        cmp     topo_rows
        bne     @redraw
        lda     topo_px         ; P's glyph still shown (inverse letter +
        ldx     topo_py         ; space: $20 in main memory; view_hide
        jsr     topo_at         ; would have left $A0)
        lsr     a
        tay
        lda     ($28),y
        cmp     #$20
        bne     @redraw
        clc
        rts
@centre:
        jsr     topo_center
@redraw:
        sec
        rts
topo_size:    .byte TOPO_W, TOPO_H
topo_quarter: .byte TOPO_W/4, TOPO_H/4
topo_max:     .byte GW-TOPO_W, GH-TOPO_H

; topo_at -- A = cell X, X = cell Y, inside the window: topo_col/topo_row,
; its grid row in gp1, CV and BASL on its text row; A = CH = its column.
topo_at:
        sta     topo_col
        stx     topo_row
        lda     grid_lo,x
        sta     gp1
        lda     grid_hi,x
        sta     gp1+1
        lda     topo_y
        clc
        adc     #TOPO_H-1       ; world Y increases north: highest Y is on top
        sec
        sbc     topo_row
        sta     CV
        jsr     t_vtab
        lda     topo_col
        sec
        sbc     topo_x
        asl     a
        sta     CH
        rts
; topo_put_cell -- redraw the cell A = X, X = Y (differential).
topo_put_cell:
        jsr     topo_at
        jsr     topo_cell
        ora     #$80
        jmp     topo_put2

topo_center:
        lda     px+1
        sec
        sbc     #TOPO_W/2
        bcs     :+
        lda     #0
:       cmp     #GW-TOPO_W+1
        bcc     :+
        lda     #GW-TOPO_W
:       sta     topo_x
        lda     py+1
        sec
        sbc     #TOPO_H/2
        bcs     :+
        lda     #0
:       cmp     #GH-TOPO_H+1
        bcc     :+
        lda     #GH-TOPO_H
:       sta     topo_y
        rts
topo_redraw:
        jsr     topo_draw
        jsr     text_release
        jmp     topo_show
topo_draw:
        ; Capture all COUT users (including decimal printing) with a renderer
        ; that advances normally but stores only bytes differing on screen.
        ; No HOME or ROM newline clearing: those rewrite unchanged cells.
        jsr     text_begin
        lda     #0
        sta     WNDTOP
        jsr     vtab
        jsr     topo_cue
        lda     #TOPO_H
        sta     topo_rows
@row:   lda     #TOPO_W
        jsr     topo_span
        dec     topo_rows
        beq     @done           ; no newline after row 23: no scroll
        jsr     CROUT
        dec     topo_row
        jmp     @row
@done:  rts

; topo_span -- the cells of row topo_row from the cursor (CH/2) up to
; cell A (exclusive), if any.
topo_span:
        sta     topo_cols
        ldx     topo_row
        lda     grid_lo,x
        sta     gp1
        lda     grid_hi,x
        sta     gp1+1
        lda     CH
        lsr     a
        sta     topo_col
        lda     topo_cols
        sec
        sbc     topo_col
        beq     @done
        bcc     @done
        sta     topo_cols
        lda     topo_col
        clc
        adc     topo_x
        sta     topo_col
@cell_loop:
        jsr     topo_cell
        ora     #$80
        jsr     topo_put2
        inc     topo_col
        dec     topo_cols
        bne     @cell_loop
@done:  rts

; topo_cue -- the inverse cue from the start of row 0, padded to a whole
; cell; topo_row = the top map row; A = the previous cue's end (cells),
; topo_cue_end = this one's.
topo_cue:
        lda     #$3F            ; the cue in inverse (topo_output: AND $32)
        sta     INVFLG
        lda     #' '|$80
        jsr     COUT
        lda     topo_walk
        beq     @cell
        lda     used
        sta     num
        lda     used+1
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " MIN ",0
@cell:  lda     px+1
        jsr     pdec
        lda     #','|$80
        jsr     COUT
        lda     py+1
        jsr     pdec
        jsr     puts
        .byte " HEAD ",0
        sec
        lda     heading
        sbc     hud_offset
        sta     ang
        lda     heading+1
        sbc     hud_offset+1
        sta     ang+1
        jsr     wrap_ang
        lda     ang
        sta     num
        lda     ang+1
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " ",0
        clc
        lda     ang
        adc     #35
        sta     ang
        lda     ang+1
        adc     #0
        sta     ang+1
        jsr     wrap_ang
        ldx     #0
@card:  lda     ang+1
        bne     @card_sub
        lda     ang
        cmp     #70
        bcc     @card_done
@card_sub:
        sec
        lda     ang
        sbc     #70
        sta     ang
        lda     ang+1
        sbc     #0
        sta     ang+1
        inx
        bne     @card
@card_done:
        lda     #<topo_cardinals
        sta     gp2
        lda     #>topo_cardinals
        sta     gp2+1
        lda     #2
        jsr     word
        jsr     topo_here
        lda     #' '|$80        ; closing space, and one more to end on a cell
        jsr     COUT
        lda     CH
        lsr     a
        bcc     :+
        lda     #' '|$80
        jsr     COUT
:       lda     #$FF
        sta     INVFLG
        lda     topo_y
        clc
        adc     #TOPO_H-1
        sta     topo_row
        lda     CH
        lsr     a
        ldx     topo_cue_end
        sta     topo_cue_end
        txa
        rts

; MAP is 80-column text: a cell is two characters (square on screen), the
; terrain symbol twice, a site or the player as an inverse letter + space.
topo_put2:
        sta     topo_c_main     ; terrain: the symbol twice
        sta     topo_c_aux
        ldx     #3
:       cmp     topo_marks,x
        beq     @mark
        dex
        bpl     :-
        bmi     @put
@mark:  and     #$3F            ; site or player: inverse letter + space
        sta     topo_c_aux
        lda     #$20
        sta     topo_c_main
@put:   lda     CH              ; even column: aux byte CH/2, then main
        lsr     a
        tay
        lda     topo_c_main
        cmp     ($28),y
        beq     :+
topo_store_main:
        sta     ($28),y
:       php
        sei
        sta     PAGE2_AUX
        lda     topo_c_aux
        cmp     ($28),y
        beq     :+
topo_store_aux:
        sta     ($28),y
:       sta     PAGE2_MAIN
        plp
        inc     CH
        inc     CH
        rts
topo_c_main: .byte 0
topo_c_aux:  .byte 0
topo_marks: .byte 'P'|$80, 'C'|$80, 'H'|$80, 'R'|$80

topo_show:
        jsr     show_text
topo_key:
        jsr     wait_key
        cmp     #KC_RET
        beq     topo_done
        cmp     #KC_ESC
        beq     topo_done
        cmp     #' '
        beq     topo_done
        cmp     #'C'
        beq     topo_recenter
        cmp     #KC_LEFT
        beq     topo_left
        cmp     #'A'
        beq     topo_left
        cmp     #KC_RIGHT
        beq     topo_right
        cmp     #'D'
        beq     topo_right
        cmp     #KC_UP
        beq     topo_up
        cmp     #'W'
        beq     topo_up
        cmp     #KC_DOWN
        beq     topo_down
        cmp     #'S'
        beq     topo_down
        jmp     topo_key
topo_done:
        ; Restore the mixed window without waiting for a second key or
        ; redrawing HGR: the text map has preserved all its pixels.
        ; back_to_view_now clears rows 20-23; the prompt redraws them.
        lda     #0              ; a later walk draws its whole map first
        sta     topo_cue_end
        jmp     back_to_view_now
topo_recenter:
        jsr     topo_center
        jmp     topo_redraw
; A quarter of the window per key: 10 cells across, 6 down.
topo_left:
        lda     topo_x
        sec
        sbc     #TOPO_W/4
        bcs     :+
        lda     #0
:       sta     topo_x
        jmp     topo_redraw
topo_right:
        lda     topo_x
        clc
        adc     #TOPO_W/4
        cmp     #GW-TOPO_W+1
        bcc     :+
        lda     #GW-TOPO_W
:       sta     topo_x
        jmp     topo_redraw
topo_down:
        lda     topo_y
        sec
        sbc     #TOPO_H/4
        bcs     :+
        lda     #0
:       sta     topo_y
        jmp     topo_redraw
topo_up:
        lda     topo_y
        clc
        adc     #TOPO_H/4
        cmp     #GH-TOPO_H+1
        bcc     :+
        lda     #GH-TOPO_H
:       sta     topo_y
        jmp     topo_redraw

topo_cell:
        lda     topo_col
        cmp     px+1
        bne     @site
        lda     topo_row
        cmp     py+1
        bne     @site
        lda     #'P'
        rts
@site:  jsr     topo_site
        beq     @terrain
        rts
@terrain:
        ldy     topo_col
        lda     (gp1),y
        bpl     @level
        lda     #'='
        rts
@level: sta     topo_height
        lda     gp1
        pha
        lda     gp1+1
        pha
        ldx     topo_col
        ldy     topo_row
        jsr     forest_contains
        pla
        sta     gp1+1
        pla
        sta     gp1
        bcc     @bare
        lda     topo_height
        clc
        adc     M_BASE
        ldx     MAP+27
        bne     :+
        ldx     #110            ; legacy/default timberline, like the renderer
:       stx     num
        cmp     num
        lda     #'T'
        bcc     @tree
        lda     #'t'
@tree:  rts
@bare:  lda     topo_height
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        tax
        lda     topo_levels,x
        rts

; topo_site -- A = 'R' (outpost), 'H' (found cabin) or 'C' (crash) at cell
; (topo_col, topo_row), in that priority, else A = 0 (Z set).
topo_site:
        lda     topo_col
        cmp     M_GOALX
        bne     @cabin
        lda     topo_row
        cmp     M_GOALY
        bne     @cabin
        lda     #'R'
        rts
@cabin: lda     MAP+16
        beq     @crash
        lda     topo_col
        cmp     MAP+17
        bne     @crash
        lda     topo_row
        cmp     MAP+18
        bne     @crash
        lda     #'H'
        rts
@crash: lda     topo_col
        cmp     M_STARTX+1
        bne     @none
        lda     topo_row
        cmp     M_STARTY+1
        bne     @none
        lda     #'C'
        rts
@none:  lda     #0
        rts
topo_levels: .byte ".,:;+*^#"
topo_height: .byte 0
topo_row: .byte 0
topo_col: .byte 0
topo_rows: .byte 0
topo_cols: .byte 0
topo_walk: .byte 0              ; 1: WALK/SWIM progress (minutes in the cue)
.export topo_key, topo_show, topo_x, topo_y
.export topo_moving_done

; P hides the site it stands on: name it in the cue (" P+R", " P+H", " P+C").
topo_here:
        lda     px+1
        sta     topo_col
        lda     py+1
        sta     topo_row
        jsr     topo_site
        beq     @none
        pha
        jsr     puts
        .byte " P+",0
        pla
        ora     #$80
        jmp     COUT
@none:  rts
topo_cardinals: .byte "N NEE SES SWW NW"

.segment "SITES"
; TOPO: the DHGR sheet computed from the resident map by TOPOGEN (module 0,
; SIM window, src/topo_dhgr.s), which also keeps a snapshot of the view:
; the return copies it back instead of redrawing. No time passes.
module_graphical_topo:
        ldx     #0              ; TOPOGEN -> $9600 (SIM is reloaded later)
        jsr     mem_fetch
        lda     #0
        sta     sim_loaded
        sta     shown
        jsr     topo_open
graphical_topo_key:
        jsr     wait_key
        cmp     #KC_ESC
        beq     @done
        cmp     #KC_RET
        beq     @done
        cmp     #' '
        bne     graphical_topo_key
@done:  jsr     topo_close      ; C clear: view and band copied back
        bcs     @redraw
        jsr     t_home          ; legend rows
        jmp     show_dhgr
@redraw:
        lda     #0
        sta     scene_drawn
        lda     #1
        sta     ui_dirty
        jsr     view_hide
        jsr     t_home
        jmp     show_view_hidden
