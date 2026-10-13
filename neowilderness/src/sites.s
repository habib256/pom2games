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

; 32 x 14 cells, one character per cell, centred on the player initially.
; Four arrow keys (or WASD) scroll; Return, Space and Escape restore HGR.
module_topo:
        jsr     topo_center
        jmp     topo_redraw

; Refresh only the top twenty text rows during travel. Simulation already
; hides HGR; preserve its code, the progress message and the message cursor.
module_topo_moving:
        lda     CH
        pha
        lda     CV
        pha
        lda     #20
        sta     $23             ; WNDBTM, exclusive
        jsr     topo_center
        jsr     topo_draw
        jsr     topo_finish
        lda     #24
        sta     $23
        lda     #20
        sta     WNDTOP
        pla
        jsr     vtab
        pla
        sta     CH
topo_moving_done:
        rts

topo_center:
        lda     px+1
        sec
        sbc     #16
        bcs     :+
        lda     #0
:       cmp     #GW-32+1
        bcc     :+
        lda     #GW-32
:       sta     topo_x
        lda     py+1
        sec
        sbc     #7
        bcs     :+
        lda     #0
:       cmp     #GH-14+1
        bcc     :+
        lda     #GH-14
:       sta     topo_y
        rts
topo_redraw:
        jsr     topo_draw
        jsr     puts
        .byte "|ARROWS/WASD SCROLL  C CENTER|ESC/RETURN/SPACE: VIEW",0
        jsr     topo_finish
        jmp     topo_show
topo_draw:
        ; Capture all COUT users (including decimal printing) with a renderer
        ; that advances normally but stores only bytes differing on screen.
        ; No HOME or ROM newline clearing: those rewrite unchanged cells.
        jsr     text_begin
        lda     #0
        sta     WNDTOP
        jsr     vtab
        jsr     puts
        .byte "MAP P YOU C CRASH H CABIN R RANGERS|CELL ",0
        lda     px+1
        jsr     pdec
        lda     #','|$80
        jsr     COUT
        lda     py+1
        jsr     pdec
        jsr     puts
        .byte "   HEAD ",0
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
        jsr     puts
        .byte " MAG",0
        jsr     puts
        .byte "|WINDOW ",0
        lda     topo_x
        jsr     pdec
        lda     #','|$80
        jsr     COUT
        lda     topo_y
        jsr     pdec
        jsr     puts
        .byte "   NORTH IS UP|",0
        jsr     topo_here
        jsr     CROUT
        lda     topo_y
        clc
        adc     #13             ; world Y increases north: highest Y is on top
        sta     topo_row
        lda     #14
        sta     topo_rows
@row:   ldx     topo_row
        lda     grid_lo,x
        sta     gp1
        lda     grid_hi,x
        sta     gp1+1
        lda     topo_x
        sta     topo_col
        lda     #32
        sta     topo_cols
@cell:  jsr     topo_cell
        ora     #$80
        jsr     COUT
        inc     topo_col
        dec     topo_cols
        bne     @cell
        jsr     CROUT
        dec     topo_row
        dec     topo_rows
        bne     @row
        jsr     puts
        .byte "|= WATER T WOODS t SCRUB .,:;+*^# LOW-HI",0
        rts

topo_finish:
        jsr     topo_pad
@row:   lda     CV
        clc
        adc     #1
        cmp     $23             ; moving: stop before progress rows 20..23
        bcs     @restore
        sta     CV
        lda     #0
        sta     CH
        jsr     t_vtab
        jsr     topo_pad
        jmp     @row
@restore:
        jmp     text_release
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
        jmp     back_to_view_now
topo_recenter:
        jsr     topo_center
        jmp     topo_redraw
topo_left:
        lda     topo_x
        sec
        sbc     #8
        bcs     :+
        lda     #0
:       sta     topo_x
        jmp     topo_redraw
topo_right:
        lda     topo_x
        clc
        adc     #8
        cmp     #GW-32+1
        bcc     :+
        lda     #GW-32
:       sta     topo_x
        jmp     topo_redraw
topo_down:
        lda     topo_y
        sec
        sbc     #4
        bcs     :+
        lda     #0
:       sta     topo_y
        jmp     topo_redraw
topo_up:
        lda     topo_y
        clc
        adc     #4
        cmp     #GH-14+1
        bcc     :+
        lda     #GH-14
:       sta     topo_y
        jmp     topo_redraw

topo_cell:
        lda     topo_col
        cmp     px+1
        bne     @goal
        lda     topo_row
        cmp     py+1
        bne     @goal
        lda     #'P'
        rts
@goal:  lda     topo_col
        cmp     M_GOALX
        bne     @crash
        lda     topo_row
        cmp     M_GOALY
        bne     @crash
        lda     #'R'
        rts
@crash: lda     topo_col
        cmp     M_STARTX+1
        bne     @cabin
        lda     topo_row
        cmp     M_STARTY+1
        bne     @cabin
        lda     #'C'
        rts
@cabin: lda     MAP+16
        beq     @terrain
        lda     topo_col
        cmp     MAP+17
        bne     @terrain
        lda     topo_row
        cmp     MAP+18
        bne     @terrain
        lda     #'H'
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
topo_levels: .byte ".,:;+*^#"
topo_height: .byte 0
topo_x: .byte 0
topo_y: .byte 0
topo_row: .byte 0
topo_col: .byte 0
topo_rows: .byte 0
topo_cols: .byte 0
.export topo_key, topo_show, topo_x, topo_y
.export topo_moving_done

; P remains visible on the grid; name its underlying site explicitly.
topo_here:
        lda     px+1
        cmp     M_GOALX
        bne     @cabin
        lda     py+1
        cmp     M_GOALY
        bne     @cabin
        jsr     puts
        .byte "AT RANGERS (P+R)",0
        rts
@cabin: lda     MAP+16
        beq     @crash
        lda     px+1
        cmp     MAP+17
        bne     @crash
        lda     py+1
        cmp     MAP+18
        bne     @crash
        lda     shelter_inside
        bne     @inside
        jsr     puts
        .byte "AT CABIN (P+H): ENTER SHELTER",0
        rts
@inside: jsr    puts
        .byte "IN CABIN (P+H): EXIT SHELTER",0
        rts
@crash: lda     px+1
        cmp     M_STARTX+1
        bne     @none
        lda     py+1
        cmp     M_STARTY+1
        bne     @none
        jsr     puts
        .byte "AT CRASH (P+C)",0
        rts
@none:  jsr     puts
        .byte "",0
        rts
topo_cardinals: .byte "N NEE SES SWW NW"

