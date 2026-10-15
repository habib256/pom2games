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
PG_COUNT = 6

; page_top -- A = the page: an 80-column text page, its tab row; the cursor
; on row 2 (row 1 blank). Nothing is cleared: each page writes its rows top to bottom (a
; CR, tab and vtab pad what they pass, differentially), so every cell is
; written once and only the cells that change are stored.
page_top:
        XL_JMP  XI_STATUS, page_top_x, @x13   ; (XL: the folder tabs, src/mt_pages.s)
        sta     pg_cur
        jsr     text_screen
        jsr     text_mode80
        ldx     #0
@tab:   stx     pg_i
        cpx     pg_cur
        bne     :+
        lda     #$3F            ; the page shown, in inverse
        sta     INVFLG
:       lda     #' '|$80
        jsr     COUT
        ldx     pg_i
        lda     pg_name_lo,x
        ldy     pg_name_hi,x
        jsr     print_str_ay
        lda     #' '|$80
        jsr     COUT
        lda     #$FF
        sta     INVFLG
        ldx     pg_i
        inx
        cpx     #PG_COUNT
        bcc     @tab
        lda     #57
        jsr     tab
        jsr     puts
        .byte   "S/O/R/H, LEFT/RIGHT||", 0
        rts

        XL_ZERO XI_STATUS, page_top+3, page_keys        ; (XL: page_top_x)
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
        bmi     @own            ; INVENTORY: its group row
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
        lda     pg_go_lo,x
        sta     gp1
        lda     pg_go_hi,x
        sta     gp1+1
        jmp     (gp1)

pg_go_lo: .byte <module_status, <scr_inventory, <pg_craft, <module_help, <module_options, <module_menu
pg_go_hi: .byte >module_status, >scr_inventory, >pg_craft, >module_help, >module_options, >module_menu
pg_view:   .byte KC_ESC, KC_RET, ' '
pg_view_end:
pg_letter: .byte "SIRHOM"
pg_letpg:  .byte PG_STATUS, PG_INVENTORY, PG_CRAFT, PG_HELP, PG_INVENTORY, PG_STATUS
; pg_levels -- below the tab row: 0 nothing, $80 OBJECTS' own levels, else
; the lines of the cursor (STATUS: its active conditions, counted by
; module_status).
pg_levels: .byte 0, $80, 0, 0, 4, 3
pg_line_at: .byte $FF, 0, 0, 0, 0, 4    ; first of pg_line_keys ($FF: the page's own)
pg_focus: .byte 0
pg_name_lo: .byte <pg_n0, <pg_n2, <pg_nc, <pg_n3, <pg_n4, <pg_n5
pg_name_hi: .byte >pg_n0, >pg_n2, >pg_nc, >pg_n3, >pg_n4, >pg_n5
pg_n0:  .byte   "STATUS", 0
pg_n2:  .byte   "OBJECTS", 0
pg_nc:  .byte   "CRAFT", 0
pg_n3:  .byte   "HELP", 0
pg_n4:  .byte   "OPTIONS", 0
pg_n5:  .byte   "MENU", 0
pg_cur: .byte   0
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
pg_col: .byte   0
pg_x:   .byte   0

; ----------------------------------------------------------------------------
; The conditions of STATUS's MEDICAL rows (src/status.s), their care.
pg_act: .res 13                 ; the active conditions (pg_focus - 1)
pg_g:   .byte 0                 ; the gesture chosen
pg_gn:  .byte 0                 ; the condition's gestures (med_foot)
pg_gf:  .byte 0                 ; the focus they belong to
med_name_lo: .byte <med_cuts,<med_arm,<med_leg,<med_shock,<med_sunburn,<med_blind,<med_frost,<med_bite,<med_infection,<med_salt,<med_poison,<med_giardia,<med_malaria,<med_alt_text
med_name_hi: .byte >med_cuts,>med_arm,>med_leg,>med_shock,>med_sunburn,>med_blind,>med_frost,>med_bite,>med_infection,>med_salt,>med_poison,>med_giardia,>med_malaria,>med_alt_text
med_cuts: .byte "SEVERE CUTS",0
med_arm: .byte "BROKEN ARM",0
med_leg: .byte "BROKEN LEG",0
med_shock: .byte "SHOCK",0
med_sunburn: .byte "SUNBURN",0
med_blind: .byte "SNOWBLINDNESS",0
med_frost: .byte "FROSTBITE",0
med_bite: .byte "POISON BITE",0
med_infection: .byte "INFECTION",0
med_salt: .byte "SALT DEFICIENCY",0
med_poison: .byte "FOOD POISONING",0
med_giardia: .byte "GIARDIA",0
med_malaria: .byte "MALARIA",0

med_alt_text: .byte "ALTITUDE SICKNESS",0

; ----------------------------------------------------------------------------
; OPTIONS: wildlife frequency (the NATURE command, typed for the player),
; the player on TOPO and MAP on or off (game_options bits 7 and 6).
module_options:
        lda     #PG_OPTIONS
        jsr     page_top
        XL_ABS  XI_STATUS, mt_skip, @y25        ; (XL: the tab names it)
        jsr     st_heading
        .byte   " OPTIONS ", 0
        XL_ABS  XI_STATUS, pg_lines_x, @p02     ; (XL: a post-it a line)
        jsr     pg_lines
        jsr     puts
        .byte   "C  WILDLIFE FREQUENCY (0-100): ", 0
        lda     nature_frequency
        jsr     pdec
        XL_ABS  XI_STATUS, pg_mark_x, @p11
        jsr     pg_mark
        jsr     puts
        .byte   "A  THE PLAYER ON TOPO: ", 0
        lda     game_options
        and     #$80
        jsr     pg_onoff
        XL_ABS  XI_STATUS, pg_mark_x, @p12
        jsr     pg_mark
        jsr     puts
        .byte   "P  MAP: ", 0
        lda     game_options
        and     #$40
        eor     #$40
        jsr     pg_onoff
        XL_ABS  XI_STATUS, pg_mark_x, @p13
        jsr     pg_mark         ; lot 4: food found on the way (FORAGE.md 11)
        jsr     puts
        .byte   "F  FOOD SOURCES ON THE WAY: ", 0
        lda     fg_ignore
        eor     #1
        jsr     pg_onoff
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
pg_run: lda     mn_word_lo,x
        sta     gp2
        lda     mn_word_hi,x
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
        XL_ABS  XI_STATUS, mt_skip, @y26
        jsr     st_heading
        .byte   " JOURNEY ", 0
        XL_ABS  XI_STATUS, pg_lines_x, @p03
        jsr     pg_lines
        jsr     puts
        .byte   "S  SAVE (GAMES 1-5)", 0
        XL_ABS  XI_STATUS, pg_mark_x, @p21
        jsr     pg_mark
        jsr     puts
        .byte   "R  RESTORE", 0
        XL_ABS  XI_STATUS, pg_mark_x, @p22
        jsr     pg_mark
        jsr     puts
        .byte   "Q  QUIT", 0
        XL_IMM  XI_STATUS, 11, @p04             ; (XL: below the third post-it)
        lda     #8
        jsr     vtab
        jsr     goal_pct        ; also brings journey_left up to date
        sta     st_done
        jsr     st_heading
        .byte   " RANGERS ", 0
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
        XL_IMM  XI_STATUS, <pg_k_menu_x, @x23
        lda     #<pg_k_menu
        XL_IMM  XI_STATUS, >pg_k_menu_x, @x24
        ldy     #>pg_k_menu
        XL_ABS  XI_STATUS, page_foot_x, @x25
        jsr     page_foot
        jmp     pg_menu_key
; pg_onoff -- ON when A <> 0, else OFF.
pg_onoff:
        tax
        lda     #<pg_on
        ldy     #>pg_on
        cpx     #0
        bne     :+
        lda     #<pg_off
        ldy     #>pg_off
:       jmp     print_str_ay
pg_on:  .byte   "ON", 0
pg_off: .byte   "OFF", 0
pg_line_keys: .byte "CAPF"     ; the lines of OPTIONS, then of MENU
mn_keys:    .byte "SRQ"
mn_word_lo: .byte <mn_save, <mn_restore, <mn_quit, <mn_nature, <mn_ignore, <mn_food
mn_word_hi: .byte >mn_save, >mn_restore, >mn_quit, >mn_nature, >mn_ignore, >mn_food
mn_save:    .byte "SAVE", 0
mn_restore: .byte "RESTORE", 0
mn_nature:  .byte "NATURE", 0
mn_quit:    .byte "QUIT", 0
mn_ignore:  .byte "IGNORE FOOD", 0
mn_food:    .byte "GET FOOD", 0

.segment "CODE"
; page_foot -- (resident, MAIN: the STATUS module's store is full on the
; 140 KB edition) A/Y = the page's keys, on row 23 (vtab pads the rows on the
; way); at its right "ESC/DOWN: VIEW", or "ESC: VIEW" on a page with a
; level (DOWN leaves only from its lowest level).
page_foot:
        pha
        tya
        pha
        lda     #23
        jsr     vtab
        pla
        tay
        pla
        jsr     print_str_ay
        lda     #64
        jsr     tab
        jsr     puts
        .byte   "ESC", 0
        ldx     pg_cur
        lda     pg_levels,x
        bne     :+
        jsr     puts
        .byte   "/DOWN", 0
:       jsr     puts
        .byte   ": VIEW", 0
        rts

; pg_lines -- (resident too) the end of the heading row, then the first line of a cursor
; page (row 4, pg_mark).
pg_lines:
        jsr     puts
        .byte   "|", 0
        lda     #0
        sta     pg_i
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
pg_k_menu: .byte "UP/DOWN: CHOOSE  RETURN: SELECT", 0
inventory_keys: .byte "UP/DOWN: TABS/GROUPS/PAGES  1-5 GROUP  N NEXT  B BACK  T TOPO",0
.segment "STATUS"
