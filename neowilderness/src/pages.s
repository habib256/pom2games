; pages.s -- the top pages of the STATUS module (14 October 2026): STATUS
; (with MEDICAL's conditions and care since 15 October 2026), OBJECTS (the
; inventory), CRAFT (lot 3 step 2: its page is the CRAFT module's, read over
; this one, pg_craft), HELP, OPTIONS and MENU share a tab row (row 0, the
; page shown in inverse) and turn in a cycle with the left and right arrows;
; the up arrow of the view opens them, ESC returns to it. UP/DOWN move a
; focus through the levels of a page (pg_focus: the tab row, STATUS's
; active conditions, OBJECTS' group row and pages, the cursor of OPTIONS
; and MENU) before DOWN leaves it from the lowest one (docs/MENUS.md). The
; module runs in the SIM window (scr_status): every page but OBJECTS, whose
; load totals need SIM first (scr_inventory), is reached without loading
; anything.
.segment "STATUS"
PG_STATUS = 0
PG_INVENTORY = 1                ; OBJECTS (15 October 2026)
PG_CRAFT = 2                    ; lot 3: the recipes (src/craft.s craft_page)
PG_HELP = 3
PG_OPTIONS = 4
PG_MENU = 5
PG_EQUIPMENT = 6
PG_COUNT = 7

; page_top -- A = the page: an 80-column text page, its tab row; the cursor
; on row 2 (row 1 blank). Nothing is cleared: each page writes its rows top to bottom (a
; CR, tab and vtab pad what they pass, differentially), so every cell is
; written once and only the cells that change are stored.
page_top:
        jmp     page_top_x       ; active XL edition
        .res    80,0            ; dedicated MouseText row frame (PF_BUF)
        XL_ZERO XI_STATUS, page_top+3, page_top+83

; page_keys -- A = a key of a page. pg_focus is the level holding the focus
; (0: the tab row, reset on every arrival; pg_levels says what lies below).
; On the tab row the arrows turn the pages, DOWN goes down a level (or back
; to the view on a page without one), UP opens TOPO (15 October 2026: the
; storeys loop, the maps above the pages; docs/MENUS.md 5). On a cursor page
; (OPTIONS, MENU) UP/DOWN move the cursor, DOWN past the last line returns
; to the view, RETURN and SPACE come back as the line's letter; INVENTORY
; moves its own focus (the arrows come back to it). Everywhere S, M, I, R
; (CRAFT), H open a page, O and I OBJECTS, M STATUS (but on MENU, whose
; letters are its own), T opens TOPO; ESC,
; RETURN and SPACE return to the view; any other key comes back (A kept).
; The focus moves redraw the page: the drawing is differential, so only
; the cells of the marker that moved are stored.
page_keys:
        ldx     pg_cur
        ldy     pg_focus
        bne     @level
        cmp     #KC_UP          ; the tab row: UP is the maps' storey
        beq     @topo
        cmp     #KC_DOWN
        bne     @keys
        ldy     pg_levels,x     ; (A kept for INVENTORY)
        beq     @view           ; no level: DOWN leaves
        bmi     @view           ; OBJECTS tab: DOWN returns to the view
@down:  inc     pg_focus
        bne     @show
@level: ldy     pg_levels,x
        bmi     @keys           ; INVENTORY: its arrows come back
        cmp     #KC_UP
        bne     :+
        dec     pg_focus        ; the first line: back to the tab row
        bpl     @show
:       cmp     #KC_DOWN
        bne     :+
        cpy     pg_focus
        bne     @down
        beq     @view           ; past the last line
:       cmp     #KC_RET
        beq     :+
        cmp     #' '
        bne     @keys
:       ldy     pg_line_at,x    ; RETURN: the letter of the cursor's
        bmi     @own            ; line (STATUS: its own, the gesture)
        tya
        clc
        adc     pg_focus
        tay
        lda     pg_line_keys-1,y
@own:   rts
@view:  pla
        pla
        jmp     back_to_view_now
@keys:  ldy     #pg_view_end-pg_view-1
:       cmp     pg_view,y
        beq     @view
        dey
        bpl     :-
        cpx     #PG_MENU
        beq     @arrows
        ldy     #pg_letpg-pg_letter-1
:       cmp     pg_letter,y
        beq     @letter
        dey
        bpl     :-
        cmp     #'T'
        bne     @arrows
@topo:  pla
        pla
        jmp     scr_topo
@letter:
        ldx     pg_letpg,y      ; S, I, R, H, O, M: their pages
        bpl     @go
@arrows:
        ldy     pg_focus        ; below the tab row the arrows are the page's
        bne     @own
        cmp     #KC_RIGHT
        bne     :+
        inx
        cpx     #PG_COUNT
        bcc     @go
        ldx     #0
        beq     @go
:       cmp     #KC_LEFT
        bne     @own
        dex
        bpl     @go
        ldx     #PG_COUNT-1
@go:    ldy     #0              ; a page arrives with the tab row focused
        sty     pg_focus
@show:  pla                     ; the page's key loop is left
        pla
page_dispatch:                 ; X = page, also used when UP reopens the storey
        lda     pg_go_lo,x
        sta     gp1
        lda     pg_go_hi,x
        sta     gp1+1
        jmp     (gp1)

pg_go_lo: .byte <module_status, <scr_inventory, <pg_craft, <module_help, <module_options, <module_menu, <scr_equipment
pg_go_hi: .byte >module_status, >scr_inventory, >pg_craft, >module_help, >module_options, >module_menu, >scr_equipment
pg_view:   .byte KC_ESC, KC_RET, ' '
pg_view_end:
pg_letter: .byte "SIRHOME"
pg_letpg:  .byte PG_STATUS, PG_INVENTORY, PG_CRAFT, PG_HELP, PG_INVENTORY, PG_STATUS, PG_EQUIPMENT
; pg_levels -- below the tab row: 0 nothing, $80 OBJECTS' own levels, else
; the lines of the cursor (STATUS: its active conditions, counted by
; module_status).
pg_levels: .byte 0, $80, 0, 0, 4, 3, $80
pg_line_at: .byte $FF, 0, 0, 0, 0, 4, 0    ; first of pg_line_keys ($FF: the page's own)
pg_focus: .byte 0
pg_name_offsets: .byte 11,18,26,32,37,45,50
.pushseg
.segment "LOWPAGE"
pg_cur: .byte   0               ; survives STATUS/CRAFT/SIM swaps
.popseg
pg_i:   .byte   0
; pg_craft -- the CRAFT page (lot 3 step 2): its tab row here, then the
; CRAFT module read over this one (NEOWILD.BLK, the SIM window): sim_fetch
; returns to its page (src/craft.s craft_page), which goes back to the
; other pages through their resident entries.
pg_craft:
        lda     #PG_CRAFT
        jsr     page_top
        XL_IMM  XI_STATUS, <(crx_end-CRAFT_RUN), @x14 ; (XL: and its tail)
        lda     #<(craft_end-CRAFT_RUN)         ; the whole module: the
        sta     module_dir+9*DIR_SIZE+3 ; recipes and the page
        XL_IMM  XI_STATUS, >(crx_end-CRAFT_RUN), @x15
        lda     #>(craft_end-CRAFT_RUN)         ; (craft_page puts back the
        sta     module_dir+9*DIR_SIZE+4 ; recipes' length)
        lda     #>(craft_page-1)
        pha
        lda     #<(craft_page-1)
        pha
        ldx     #CRAFT_MODULE
        jmp     sim_fetch
pg_x:   .byte   0

; ----------------------------------------------------------------------------
; The conditions of STATUS's MEDICAL rows (src/status.s), their care.
pg_act: .res 13                 ; the active conditions (pg_focus - 1)
pg_g:   .byte 0                 ; the gesture chosen
pg_gn:  .byte 0                 ; the condition's gestures (med_foot)
pg_gf:  .byte 0                 ; the focus they belong to
med_name_offsets: .byte 0,12,23,34,40,48,62,0,12,22,38,53,61,69
med_name_ids: .byte pg_med_a,pg_med_a,pg_med_a,pg_med_a,pg_med_a,pg_med_a,pg_med_a,pg_med_b,pg_med_b,pg_med_b,pg_med_b,pg_med_b,pg_med_b,pg_med_b

; ----------------------------------------------------------------------------
; OPTIONS (15 October 2026: one post-it, a line an option, its state in
; a column, the line of the focus in inverse, what it does below): wildlife
; frequency (the NATURE command, typed for the player), the player on TOPO
; and the MAP page on or off (game_options bits 7 and 6), the food sources
; on the way (IGNORE FOOD / GET FOOD).
PG_VAL = 31                     ; the column of the states
PG_DESC = 8                     ; the row of the description
module_options:
        lda     #PG_OPTIONS
        jsr     page_top
        lda     #56
        jsr     st_heading
        jsr     pg_first
        lda     #0
        jsr     pg_line_text
        jsr     pg_val
        lda     nature_frequency
        jsr     pdec
        jsr     pg_line
        lda     #22
        jsr     pg_line_text
        lda     game_options
        and     #$80
        jsr     pg_onoff
        jsr     pg_line
        lda     #40
        jsr     pg_line_text
        lda     game_options
        and     #$40
        eor     #$40
        jsr     pg_onoff
        jsr     pg_line         ; lot 4: food found on the way (FORAGE.md 11)
        lda     #52
        jsr     pg_line_text
        lda     fg_ignore
        eor     #1
        jsr     pg_onoff
        lda     #PG_DESC        ; (XL: the focused option, in a sentence)
        XL_ABS  XI_STATUS, pg_desc_x, @x27
        jsr     vtab
        XL_IMM  XI_STATUS, <pg_k_menu_x, @x19
        lda     #<pg_k_menu
        XL_IMM  XI_STATUS, >pg_k_menu_x, @x20
        ldy     #>pg_k_menu
        XL_ABS  XI_STATUS, page_foot_x, @x21
        jsr     page_foot
@key:   jsr     wait_key
        jsr     page_keys
        ldx     #3
        cmp     #'C'            ; NATURE asks the frequency
        beq     pg_run
        cmp     #'F'            ; IGNORE FOOD or GET FOOD, typed
        bne     :+
        inx
        lda     fg_ignore
        beq     pg_run
        inx
        bne     pg_run
:       cmp     #'A'            ; the options turn on and off
        bne     :+
        lda     #$80
        bne     @flip
:       cmp     #'P'
        bne     @key
        lda     #$40
@flip:  eor     game_options
        sta     game_options
        jmp     module_options
; pg_menu_key -- MENU's key loop, here within reach of pg_run.
pg_menu_key:
        jsr     wait_key
        jsr     page_keys
        ldx     #2
:       cmp     mn_keys,x
        beq     pg_run
        dex
        bpl     :-
        bmi     pg_menu_key

; pg_run -- the command X of mn_word (SAVE, RESTORE, QUIT, NATURE) in inbuf,
; the view back, then do_command.
pg_run: lda     mn_word_offsets,x
        pha
        lda     #om_to_can
        jsr     text_fetch
        pla
        clc
        adc     #<tb_buf
        sta     gp2
        lda     #>tb_buf
        adc     #0
        sta     gp2+1
; pg_type -- (MEDVIEW's gestures too) the string at gp2.
pg_type:
        ldy     #0
:       lda     (gp2),y
        sta     inbuf,y
        beq     :+
        iny
        bne     :-
:       sty     linelen
        jsr     back_to_view_now
        jmp     do_command
; ----------------------------------------------------------------------------
; MENU: the journey's own commands, typed for the player (inbuf, then
; do_command: the same paths as the keyboard), and the journey's progress
; (RANGERS, from STATUS since 15 October 2026: the distance, the bearing
; with a compass, the journey done and its gauge).
module_menu:
        lda     #PG_MENU
        jsr     page_top
        jsr     goal_pct        ; also brings journey_left up to date
        sta     st_done
        lda     #66
        jsr     st_heading
        jsr     st_rangers
        jsr     puts
        .byte   "|JOURNEY DONE: ", 0
        lda     st_done
        jsr     pdec
        jsr     puts
        .byte   "%  ", 0
        lda     st_done
        jsr     st_cells
        jsr     bar
        lda     #6              ; (XL: under the RANGERS post-it)
        jsr     vtab
        lda     #76
        jsr     st_heading
        jsr     pg_first
        lda     #79
        jsr     pg_line_text
        jsr     pg_line
        lda     #99
        jsr     pg_line_text
        lda     #10             ; (XL: the QUIT post-it, its title from
        jsr     vtab            ; the table; 140 KB: a blank row)
        jsr     pg_line
        lda     #110
        jsr     pg_line_text
        lda     #$FF
        sta     INVFLG
        XL_IMM  XI_STATUS, <pg_k_menu_x, @x23
        lda     #<pg_k_menu
        XL_IMM  XI_STATUS, >pg_k_menu_x, @x24
        ldy     #>pg_k_menu
        XL_ABS  XI_STATUS, page_foot_x, @x25
        jsr     page_foot
        jmp     pg_menu_key
; pg_onoff -- the states' column, then [X] when A <> 0, else [ ] (XL: a
; check mark in the box).
pg_onoff:
        pha
        jsr     pg_val
        pla
        tax
        lda     #<pg_on
        ldy     #>pg_on
        cpx     #0
        bne     :+
        lda     #<pg_off
        ldy     #>pg_off
:       XL_ABS  XI_STATUS, mt_str, @x26         ; (XL: the glyph)
        jmp     print_str_ay
pg_on:  .byte   "[X]", 0
pg_off: .byte   "[ ]", 0
        XL_BYTE XI_STATUS, pg_on+1, MS_CHECK
pg_line_keys: .byte "CAPF"     ; the lines of OPTIONS, then of MENU
mn_keys:    .byte "SRQ"
mn_word_offsets: .byte 8,13,28,21,33,45
mn_quit: .byte "QUIT",0
; pg_first -- the first line of a cursor page, under its heading;
; pg_line -- the next one (pg_mark): its text in inverse when it holds the
; focus.
pg_first:
        lda     #0
        sta     pg_i
pg_line:
        lda     #$FF            ; (the marker in normal video)
        sta     INVFLG
        jsr     pg_mark
        ldx     pg_i
        cpx     pg_focus
        bne     :+
        lda     #$3F            ; the line of the focus: in inverse
        sta     INVFLG
:       rts
; pg_val -- spaces (in the line's video) up to the states' column, then
; the normal video for the state.
pg_val: lda     #' '|$80
:       jsr     COUT
        ldx     CH
        cpx     #PG_VAL
        bcc     :-
        lda     #$FF
        sta     INVFLG
        rts

.segment "CODE"
; The retired text footer's resident area now explicitly reserves the XL
; pad, curtain and frame hook copied by build_disk.py (XL_COPIES).
page_foot:
        .res    53, 0           ; dedicated XLRES copy: pad, curtain, frame hook

; pg_lines -- (resident) the OBJECTS page's state and its command since
; 16 October 2026 (the cursor pages' header, unused since 15 October, held
; these ten bytes: the resident image does not move).
pg_lines:
obj_keep: .byte 0               ; $80: back from a transfer (src/inventory.s)
obj_side: .byte 0               ; 0 LOCAL, 1 CARRIED
obj_cur:  .byte 0, 0            ; each side's entry under the cursor
; obj_type -- (OBJECTS, after it has typed a transfer in inbuf) SIM quietly
; over the STATUS module (no curtain; finish_simulation keeps the page),
; then the command as typed.
obj_type:
        jsr     load_totals_quiet
        jmp     do_command
; pg_mark -- (resident too) a new line of a cursor page: CR, then ">" in column 1 on the
; line holding the focus (pg_i counts the lines from 1).
pg_mark:
        inc     pg_i
        jsr     CROUT
        lda     #' '|$80
        jsr     COUT
        ldx     pg_i
        cpx     pg_focus
        bne     :+
        lda     #'>'|$80
:       jmp     COUT
; the keys of the cursor pages and of INVENTORY
pg_k_menu = pg_k_menu_x
inventory_keys = inventory_keys_x

; Read-only equivalent of water_here: native cell, legacy adjacent banks.
; No SIM load, camp_untreated update or saved-state writes.
med_water_legacy:
        lda     py+1
        sec
        sbc     #1
        sta     mw_y
        lda     #3
        sta     mw_rows
@row:   lda     px+1
        sec
        sbc     #1
        sta     mw_x
        lda     #3
        sta     mw_cols
@cell:  ldx     mw_y
        cpx     #GH
        bcs     @next
        ldy     mw_x
        cpy     #GW
        bcs     @next
        jsr     cell_at
        bmi     @yes
@next:  inc     mw_x
        dec     mw_cols
        bne     @cell
        inc     mw_y
        dec     mw_rows
        bne     @row
        clc
        rts
@yes:  sec
        rts
mw_x = overlay_text+74
mw_y = overlay_text+75
mw_rows = overlay_text+76
mw_cols = overlay_text+77
.segment "STATUS"

med_water_near:
        lda     MAP+37
        jeq     med_water_legacy
med_water_native:
        lda     geo_wooded
        pha
        lda     geo_water_kind
        pha
        jsr     inventory_here
        asl     a
        pla
        sta     geo_water_kind
        pla
        sta     geo_wooded
        rts
