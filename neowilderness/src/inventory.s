; OBJECTS, the transfer page (16 October 2026, docs/MENUS.md 5, 9): what
; lies on this cell on the left (LOCAL, then LOCAL HUNG), what the player
; carries on the right (HANDS, PACK, WORN), each item with its weight; LEFT
; and RIGHT choose the side, UP and DOWN the item, RETURN sends it to the
; other side (PACK x, or GET WATER, CARRY BACKPACK / CANTEEN; DROP x from
; the right), H takes it in hand (CARRY x). The page types the command as
; the keyboard would (do_command, through obj_type: SIM quietly first, so
; the page stays on the screen), and the grid's queue types INVENTORY
; after it: the page comes back with the game's answer in rows 20-22,
; columns 0-38 (the view's result column, written by message itself). Part
; of the STATUS module (SIM window, src/status.s): scr_inventory computes
; the load totals (SIM) first, then fetches the module.
;
;   row 0       the tab row: OBJECTS
;   row 2       the titles: LOCAL (left), HANDS or PACK (right)
;   rows 3-14   the two lists (overlay_text), twelve entries a side, the
;               window scrolled to the cursor; the groups' headings in
;               inverse; "MORE" on row 15 under a list that goes on
;   rows 16-19  CARRYING (left: food and water carried, here, in reach),
;               LOAD (right: the gauge of the carried weight up to the
;               limit, the walk's slowing, the free volumes)
;   rows 20-22  the answer of the last transfer (left), what RETURN and H
;               type (right)
;   row 23      the keys
; On NeoWildernessXL the blocks are post-its (src/mt_pages.s).
OB_ROWS  = 12                   ; entries a side on the screen (rows 3-14)
OB_NAME  = 3                    ; the name's column in a half
OB_OZ    = 18                   ; the weight's column in a half
OB_RIGHT = 41                   ; the right half
.segment "STATUS"
module_inventory:
        jsr     forage_here     ; lot 4: the ground piles of this cell
        jsr     inventory_settle ; lot 3: the CLUB, the ROCK of this cell
        lda     #19             ; shared page helpers in the $5800 window
        jsr     overlay_load
        lda     obj_keep        ; back from a transfer: the answer stays,
        bpl     inventory_redraw ; the focus on the lists
        lda     #0
        sta     obj_keep
        sta     ob_clear
        lda     #1
        sta     pg_focus
inventory_redraw:
        XL_ABS  XI_STATUS, ob_frames_x, @xobj
        jsr     ob_build
        lda     #PG_INVENTORY
        jsr     page_top
        lda     #0
        jsr     st_heading
        lda     #OB_RIGHT
        jsr     tab
        lda     #$3F
        sta     INVFLG
        jsr     inv_space
        ldx     ob_title
        lda     inventory_name_lo,x
        ldy     inventory_name_hi,x
        jsr     print_str_ay
        jsr     inv_space
        lda     #$FF
        sta     INVFLG
        lda     #0              ; rows 3-14: the lists
        sta     ob_row
@row:   jsr     CROUT
        ldx     #0
        jsr     ob_entry
        ldx     #1
        jsr     ob_entry
        inc     ob_row
        lda     ob_row
        cmp     #OB_ROWS
        bcc     @row
        jsr     CROUT           ; row 15: MORE under a list that goes on
        ldx     #0
        jsr     ob_more
        ldx     #1
        jsr     ob_more
        jsr     CROUT           ; rows 16-19: CARRYING, LOAD
        lda     #8
        jsr     st_heading
        lda     #ST_FOOD
        jsr     tab
        lda     #ob_food_label
        jsr     om_bank_puts
        lda     #ST_WATER
        jsr     tab
        lda     #ob_water_label
        jsr     om_bank_puts
        lda     #OB_RIGHT
        jsr     tab
        lda     #19
        jsr     st_heading
        lda     g1              ; (g1 kept: reach_oz's scratch; the
        pha                     ; reference's INVENTORY leaves it alone)
        lda     #0
        sta     status_stock_kind
@stock: jsr     CROUT
        jsr     status_stock_line
        lda     #OB_RIGHT
        jsr     tab
        jsr     ob_ld           ; (ob_m, num: the carried ounces)
        ldx     status_stock_kind
        bne     @walk
        ldy     #10             ; the gauge: ten cells up to the limit
        jsr     ob_mul
        lda     load_limits
        ldx     load_limits+1
        jsr     ob_div
        jsr     bar
        jsr     ob_ld
        jsr     print_u16
        lda     #'/'|$80        ; the limit: the gauge's end (the original's
        jsr     COUT            ; $4BFA; past it, any GET is refused)
        lda     load_limits
        sta     num
        lda     load_limits+1
        sta     num+1
        jsr     print_u16
        lda     #om_unit_oz
        jsr     om_bank_puts
        jmp     @next
@walk:  dex
        bne     @free
        ; Walk: 100 x INT(ounces/16) / (body + 2), T08/S07.
        lda     #ob_walk_label
        jsr     om_bank_puts
        ldx     #4              ; pounds: INT(ounces / 16), as the core's $50A1
:       lsr     ob_m+1
        ror     ob_m
        dex
        bne     :-
        ldy     #100
        jsr     ob_mul
        lda     body_weight
        clc
        adc     #2
        pha
        lda     body_weight+1
        adc     #0
        tax
        pla
        jsr     ob_div
        jsr     pdec
        lda     #'%'|$80
        jsr     COUT
        lda     #ob_wear_label
        jsr     om_bank_puts
        lda     #2
        sta     ob_t
        jsr     ob_free
        jsr     print_u16
        jmp     @next
@free:  lda     #om_pack_word
        jsr     om_bank_puts
        lda     #4
        jsr     ob_volume
        lda     #ob_hands_label
        jsr     om_bank_puts
        lda     #6
        jsr     ob_volume
        lda     #8              ; preserve INVENTORY's word scratch
        sta     g2
@next:  inc     status_stock_kind
        lda     status_stock_kind
        cmp     #3
        jcc     @stock
        pla
        sta     g1
        lda     #20             ; rows 20-22: the answer (kept after a
        jsr     vtab            ; transfer: its cells are skipped), the
        lda     #0              ; commands of RETURN and H
        sta     ob_row
@res:   lda     ob_clear
        beq     :+
        lda     #39             ; (an arrival: the left cleared)
        jsr     tab
:       lda     #39
        sta     CH
        lda     #OB_RIGHT
        jsr     tab
        lda     ob_row
        beq     @res_end         ; row 20: bottom border, hints on 21 and 22
        dec     ob_row
        lda     ob_row
        jsr     ob_cmd
        bcc     @res_next
        lda     pg_focus
        beq     @res_next
        ldx     ob_row
        lda     ob_hint_lo,x
        ldy     #>ob_hints
        XL_ABS  XI_STATUS, mt_str, @x26
        jsr     print_str_ay
        lda     #<ob_line
        ldx     #>ob_line
        jsr     print_str_ax
@res_next:
        inc     ob_row
@res_end:
        jsr     CROUT
        inc     ob_row
        lda     ob_row
        cmp     #3
        bcc     @res
        lda     #0
        sta     ob_clear
        XL_IMM  XI_STATUS, <inventory_keys_x, @x27
        lda     #<inventory_keys
        XL_IMM  XI_STATUS, >inventory_keys_x, @x28
        ldy     #>inventory_keys
        XL_ABS  XI_STATUS, page_foot23_x, @x29
        jsr     page_foot
inventory_key:
        jsr     wait_key
        ldy     pg_focus        ; the lists: RETURN, H
        bne     :+
        cmp     #KC_RET         ; tab row: RETURN enters the lists; DOWN leaves
        beq     @down
        bne     @page
:
        cmp     #KC_RET
        beq     @return
        cmp     #'H'
        beq     @hand
@page:  jsr     page_keys       ; the tabs, the pages, TOPO, the view
        ldx     obj_side        ; (below the tab row the arrows come back)
        cmp     #KC_DOWN
        beq     @down
        cmp     #KC_UP
        beq     @up
        cmp     #KC_LEFT
        beq     @side
        cmp     #KC_RIGHT
        bne     inventory_key
@side:  txa                     ; the other side
        eor     #1
        sta     obj_side
@redraw:
        jmp     inventory_redraw
@down:  lda     pg_focus        ; the tab row: RETURN enters the lists
        bne     :+
        inc     pg_focus
        bne     @redraw
:       lda     obj_cur,x       ; the next item; past the last, the view
        clc
        adc     #1
        ldy     #1
        jsr     ob_seek
        bcc     @end
@set:   sta     obj_cur,x
        jsr     ob_remember
        jmp     @redraw
@up:    lda     obj_cur,x       ; the item before; above the first, the tabs
        sec
        sbc     #1
        ldy     #$FF
        jsr     ob_seek
        bcs     @set
        dec     pg_focus
        bpl     @redraw
@end:   jmp     back_to_view_now
@hand:  lda     #1
        bne     :+
@return:
        lda     #0
:       jsr     ob_cmd
        bcc     inventory_key
        sta     ob_item         ; ob_cmd returns no useful A: use the noun
        lda     menu_noun
        sta     ob_item
        lda     obj_side
        sta     ob_s
        tax
        lda     obj_cur,x
        sta     ob_e
        jsr     ob_weight       ; capture source stock before replacing MEDVIEW
        lda     num
        sta     ob_m
        lda     num+1
        sta     ob_m+1
        lda     #20
        jsr     overlay_load
        jmp     object_menu

; ob_build -- the entries of the two sides in overlay_text (ob_at: the
; first of a side, ob_n: how many): item numbers, a group's heading $80 +
; group. Left: the ground here, then LOCAL HUNG when something hangs here;
; right: HANDS items, separator, PACK and WORN headings. The cursors are put back on an
; item of their side (ob_fix).
ob_build:
        ldy     #0              ; ob_prog
        sty     ob_k
        ldx     #0
@side:  stx     ob_s
        lda     ob_k
        sta     ob_at,x
@group: lda     ob_prog,y
        iny
        cmp     #$FF
        beq     @end
        cmp     #$8A            ; blank separator below HANDS
        bne     :+
        ldx     ob_k
        sta     overlay_text,x
        inc     ob_k
        bne     @group
:
        sty     ob_t
        sta     ob_g
        and     #7
        sta     inventory_group
        ldx     ob_k
        stx     ob_e            ; (the heading's entry)
        lda     ob_g
        bpl     @items
        and     #$87
        sta     overlay_text,x
        inc     ob_k
@items: ldx     #1
@item:  jsr     inventory_match
        bcc     :+
        txa
        ldy     ob_k
        sta     overlay_text,y
        inc     ob_k
:       inx
        cpx     #95             ; (the shelters are not objects)
        bcc     @item
        lda     ob_g            ; LOCAL HUNG: no heading alone
        and     #$C0
        cmp     #$80
        bne     :+
        ldx     ob_e
        inx
        cpx     ob_k
        bne     :+
        dec     ob_k
:       ldy     ob_t
        jmp     @group
@end:   ldx     ob_s
        lda     ob_k
        sec
        sbc     ob_at,x
        sta     ob_n,x
        inx
        cpx     #2
        jcc     @side
; ob_fix -- each side's cursor on an item: the one under it, else the next,
; else the one before (0 without any).
        dex
@fix:   jsr     ob_restore
        lda     obj_cur,x
        cmp     ob_n,x
        bcc     :+
        lda     ob_n,x          ; past the end: the last entry
        sbc     #1
        bcs     :+
        lda     #0
:       pha
        ldy     #1
        jsr     ob_seek
        bcs     :+
        pla
        pha
        ldy     #$FF
        jsr     ob_seek
        bcs     :+
        lda     #0
:       sta     obj_cur,x
        jsr     ob_remember
        pla
        dex
        bpl     @fix
        ldx     #1              ; heading of the right viewport: HANDS or PACK
        stx     ob_title
        jsr     ob_top
        clc
        adc     ob_at+1
        tay
@title: cpy     ob_at+1
        beq     @title_end
        lda     overlay_text,y
        cmp     #$82
        bne     :+
        inc     ob_title
        rts
:       dey
        bne     @title
@title_end:
        rts
        .pushseg
        .segment "CODE"
ob_prog: .byte  3, $84, $FF, 1, $8A, $C2, $C0, $FF
        .popseg

; ob_seek -- X = side, A = the first entry to try, Y = 1 forward or $FF
; back: C set and A = the first item found that way; C clear at an end. X kept.
ob_seek:
        sta     ob_e
        sty     ob_d
@try:   lda     ob_e
        cmp     ob_n,x          ; (back past 0: $FF)
        bcs     @no
        adc     ob_at,x
        tay
        lda     overlay_text,y
        bpl     @yes
        lda     ob_e
        clc
        adc     ob_d
        sta     ob_e
        jmp     @try
@yes:   lda     ob_e
        sec
        rts
@no:    clc
        rts

; ob_top -- X = side: A = its first entry on the screen (the cursor's entry
; on the last row when it lies below).
ob_top: lda     obj_cur,x
        sec
        sbc     #OB_ROWS-1
        bcs     :+
        lda     #0
:       rts

; ob_entry -- X = side: its entry on the screen row ob_row (from the half's
; first column): the cursor ">" (the lists hold the focus, this side), the
; name, the weight; a group's heading in inverse.
ob_entry:
        stx     ob_s
        jsr     ob_top
        clc
        adc     ob_row
        cmp     ob_n,x
        bcs     @rts
        sta     ob_e
        adc     ob_at,x
        tay
        lda     overlay_text,y
        cmp     #$8A
        beq     @rts
        sta     ob_item
        lda     #1
        jsr     ob_col
        lda     ob_item
        bpl     @item
        and     #7
        tax
        lda     #$3F
        sta     INVFLG
        jsr     inv_space
        lda     inventory_name_lo,x
        ldy     inventory_name_hi,x
        jsr     print_str_ay
        jsr     inv_space
        lda     #$FF
        sta     INVFLG
@rts:   rts
@item:  ldy     #' '|$80
        lda     pg_focus
        beq     :+
        lda     ob_s
        cmp     obj_side
        bne     :+
        tax
        lda     obj_cur,x
        cmp     ob_e
        bne     :+
        ldy     #'>'|$80
:       tya
        jsr     COUT
        lda     #OB_NAME
        jsr     ob_col
        ldx     ob_item
        jsr     inventory_name
        jsr     print_str_ax
        lda     #OB_OZ
        jsr     ob_col
        jsr     ob_weight
        jsr     print_u16
        ldx     ob_item         ; the remedies: their uses (as before)
        jsr     ob_uses
        bcc     :+
        lda     #ob_uses_label
        jsr     st_gauge_text
        rts
:       lda     #om_unit_oz
        jsr     om_bank_puts
        rts
; ob_uses -- C set for item X, a remedy counted in uses (41-51 but the
; SUNGLASSES, 43).
ob_uses:
        cpx     #43
        beq     :+
        cpx     #41
        bcc     :+
        cpx     #52
        bcs     :+
        sec
        rts
:       clc
        rts
; ob_col -- A = a column of the half ob_s: tab there.
ob_col: ldx     ob_s
        beq     :+
        clc
        adc     #OB_RIGHT
:       jmp     tab
; ob_more -- X = side: "MORE" when its list goes on below the screen.
ob_more:
        stx     ob_s
        jsr     ob_top
        clc
        adc     #OB_ROWS
        cmp     ob_n,x
        bcs     :+
        lda     #30
        jsr     ob_col
        lda     #26
        jsr     st_heading
:       rts

; ob_weight -- num = the weight of the entry ob_item (ob_e of side ob_s):
; W5 for the gear, the ounces of a food or a pile in its place, the second
; set's W5 (CRAFT.md 4.1: BOW, SPEAR 50, CLUB, ROCK 100, SPLINT 50).
ob_weight:
        ldx     ob_item
        cpx     #N_WATER
        bcc     @gear
        cpx     #38
        bcc     @oz
        jsr     ob_uses
        bcc     :+
        lda     it_pack_lo,x    ; a remedy: its uses
        sta     num
        lda     it_pack_hi,x
        sta     num+1
        rts
:       cpx     #76
        bcc     @gear
        cpx     #89
        bcc     @oz
        cpx     #94
        bcs     @oz
        lda     ob_crw-89,x
        sta     num
        lda     #0
        sta     num+1
        rts
@gear:  lda     it_oz_lo,x
        sta     num
        lda     it_oz_hi,x
        sta     num+1
        rts
@oz:    ldx     ob_s            ; its group: the heading above it (left:
        lda     ob_e            ; the ground without one)
        clc
        adc     ob_at,x
        tay
        lda     ob_at,x
        sta     ob_d
@up:    lda     #3
        cpy     ob_d
        beq     @group
        dey
        lda     overlay_text,y
        bpl     @up
        and     #7
@group: sta     inventory_group
        ldx     ob_item
        jmp     inventory_match ; (num: the ounces there)
ob_crw: .byte   50, 50, 100, 100, 50

; ob_cmd -- A = 0 RETURN, 1 H: C set with the command for the item under
; the cursor in ob_line (ob_len), the item in menu_noun (its display name
; is not always a word of the vocabulary); C clear without an item. (Not
; inbuf: the page leaves the typed line as the reference's INVENTORY.)
.pushseg
.segment "MEDVIEW"
ob_cmd: sta     ob_t
        ldx     obj_side
        lda     obj_cur,x
        ldy     #1
        jsr     ob_seek
        bcc     @no
        cmp     obj_cur,x       ; (an item under the cursor itself)
        clc
        bne     @no
        adc     ob_at,x
        tay
        lda     overlay_text,y
        sta     menu_noun
        tax
        lda     obj_side
        bne     @default
@group: lda     overlay_text,y  ; only the LOCAL HUNG heading is stored on the left
        bmi     @hung           ; independent LOCAL piles still have normal actions
        dey
        bpl     @group
        bmi     @default
@no:    clc
        rts
@default:
        ldx     menu_noun
        jsr     inventory_name ; fetch before constructing ob_line in tb_buf
        sta     gp2
        stx     gp2+1
        ldy     #OB_CARRY       ; H: CARRY x
        lda     ob_t
        bne     @verb
        ldy     #OB_DROP        ; RETURN from the right: DROP x
        lda     obj_side
        bne     @verb
        ldy     #OB_GET         ; from the left: GET WATER (the canteen),
        cpx     #N_WATER        ; CARRY BACKPACK, CARRY CANTEEN, PACK x
        beq     @verb
        ldy     #OB_CARRY
        cpx     #21
        beq     @verb
        cpx     #64
        beq     @verb
        ldy     #OB_PACK
@verb:  ldx     #0
:       lda     ob_verbs,y
        sta     ob_line,x
        iny
        inx
        cmp     #' '
        bne     :-
        stx     ob_len
        ldy     #0              ; "2QT CANTEEN": CANTEEN (a digit would make
        lda     (gp2),y         ; the line a number for INPUT)
        cmp     #'9'+1
        bcs     @name
:       iny
        lda     (gp2),y
        cmp     #' '
        bne     :-
        iny
@name:  ldx     ob_len
:       lda     (gp2),y
        sta     ob_line,x
        beq     :+
        inx
        iny
        cpx     #MAXLINE
        bcc     :-
        lda     #0
        sta     ob_line,x
:       stx     ob_len
        sec
@rts:   rts
@hung:  ldx     #10
:       lda     ob_lower,x
        sta     ob_line,x
        dex
        bpl     :-
        sec
        rts
.pushseg
.segment "STATUS"
ob_lower: .byte "LOWER FOOD",0
.popseg
ob_verbs:
OB_PACK  = * - ob_verbs
        .byte   "PACK "
OB_DROP  = * - ob_verbs
        .byte   "DROP "
OB_CARRY = * - ob_verbs
        .byte   "CARRY "
OB_GET   = * - ob_verbs
        .byte   "GET "

; ob_ld -- num and ob_m = the carried ounces (load_used).
.popseg
ob_ld:  lda     load_used
        sta     num
        sta     ob_m
        lda     load_used+1
        sta     num+1
        sta     ob_m+1
        rts
.pushseg
.segment "MEDVIEW"
; ob_mul lives in STATX; num = Y x the word at ob_m.
; ob_div -- A = INT(num / (A + 256 X)), at most 255.
ob_div: sta     ob_m
        stx     ob_m+1
        ldx     #0
@sub:   lda     num
        sec
        sbc     ob_m
        tay
        lda     num+1
        sbc     ob_m+1
        bcc     @end
        sta     num+1
        sty     num
        inx
        bne     @sub
        dex
@end:   txa
        rts

; Persistent item identities complement obj_cur (the fallback row if an
; item disappears). X is the side; no state is added to saved game data.
ob_restore:
        lda     obj_cur,x       ; keep the exact row when its identity survives
        clc                     ; LOCAL and LOCAL HUNG can contain the same noun
        adc     ob_at,x
        tay
        lda     overlay_text,y
        cmp     obj_selected,x
        beq     @end
        ldy     ob_at,x
@find:  lda     overlay_text,y
        cmp     obj_selected,x
        beq     @found
        iny
        tya
        sec
        sbc     ob_at,x
        cmp     ob_n,x
        bcc     @find
@end:   rts
@found: tya
        sec
        sbc     ob_at,x
        sta     obj_cur,x
        rts
ob_remember:
        lda     obj_cur,x
        clc
        adc     ob_at,x
        tay
        lda     overlay_text,y
        sta     obj_selected,x
        rts

; Six cells of occupied volume, then the free cubic inches. Capacities
; are at most 6000 IN3: multiplying a legal load by six fits in 16 bits.
ob_volume:
        sta     ob_t
        tay
        lda     load_limits,y
        ora     load_limits+1,y
        beq     @empty
        lda     load_used,y
        cmp     load_limits,y
        lda     load_used+1,y
        sbc     load_limits+1,y
        bcs     @full
        lda     load_used,y
        sta     ob_m
        lda     load_used+1,y
        sta     ob_m+1
        ldy     #6
        jsr     ob_mul
        ldy     ob_t
        lda     load_limits,y
        ldx     load_limits+1,y
        jsr     ob_div
        jmp     @bar
@empty: lda     #0
        beq     @bar
@full:  lda     #6
@bar:   sta     ob_fill
        ldx     #0
@cell:  XL_IMM  XI_MEDVIEW, MT_BLOCK, @fullglyph
        lda     #$20            ; inverse space on 140 KB
        cpx     ob_fill
        bcc     :+
        XL_IMM  XI_MEDVIEW, MT_HALF1, @emptyglyph
        lda     #'.'|$80
:       jsr     COUT
        inx
        cpx     #6
        bcc     @cell
        jsr     inv_space
        jsr     ob_free
        jmp     print_u16
ob_free:
        ldy     ob_t
        sec
        lda     load_limits,y
        sbc     load_used,y
        sta     num
        lda     load_limits+1,y
        sbc     load_used+1,y
        bcs     :+
        lda     #0              ; an overloaded container has no free room
        sta     num
:       sta     num+1
        rts
ob_fill: .byte 0

.popseg
ob_hint_lo: .byte <ob_h_ret, <ob_h_hand
ob_hints:
ob_h_ret:  .byte MS_RET," ",0
ob_h_hand: .byte "H ",0          ; XL-only hints; retired text edition is not rebuilt
.assert >ob_h_ret = >ob_h_hand, error, "object hints share a page"
ob_clear: .byte 1               ; 1: an arrival, the answer's rows cleared
ob_title: .byte 1
ob_row:  .byte 0
ob_s:    .byte 0
ob_e:    .byte 0
ob_d:    .byte 0
ob_g:    .byte 0
ob_k:    .byte 0
ob_t:    .byte 0
ob_item: .byte 0
ob_m:    .word 0
ob_at:   .res 2
ob_n:    .res 2
ob_len:  .byte 0
ob_line = tb_buf                ; the command of RETURN or H (the text bank's
                                ; buffer: banked names are fetched before constructing the command)
.assert TB_MAX >= MAXLINE + 1, error, "ob_line: tb_buf too short"
inventory_group: .byte 0

; X is preserved; carry means membership, num holds provision ounces.
inventory_match:
        cpx     #76
        jcs     inventory_second
        lda     it_place,x
        cmp     #255
        beq     @no
        cpx     #N_WATER
        bcc     @gear
        cpx     #38
        bcs     @gear
        lda     inventory_group
        cmp     #3
        beq     @food_ground
        cmp     #4
        beq     @hung_food
        cmp     #2
        bne     @no
        lda     it_place,x
        cmp     #5
        beq     @no
        jmp     @food_pack
@hung_food:
        lda     it_place,x
        cmp     #5
        bne     @no
        jsr     inventory_hung_here
        bcc     @no
@food_pack:
        lda     it_pack_lo,x
        sta     num
        lda     it_pack_hi,x
        sta     num+1
        ora     num
        beq     @no
        sec
        rts
@food_ground:
        jsr     at_ground
        bcc     @no
        lda     it_gnd_lo,x
        sta     num
        lda     it_gnd_hi,x
        sta     num+1
        ora     num
        beq     @no
        sec
        rts
@gear:  ldy     inventory_group
        cmp     inventory_places,y
        bne     @no
        cpy     #4
        beq     inventory_hung_here
        cpy     #3
        bne     @yes
        jmp     at_ground
@yes:   sec
        rts
@no:    clc
        rts
inventory_hung_here:
        lda     px+1
        cmp     it_x+21
        bne     @no
        lda     py+1
        cmp     it_y+21
        bne     @no
        sec
        rts
@no:    clc
        rts
; inventory_second -- (lot 4) X = 76..94: the pile (inventory_pile) of
; animal meat, GAME .. PLANTS (k = X - 75) or HIDE (94), in the pack (group
; 2) or on the ground here (3).
inventory_second:
        cpx     #89
        bcc     :+
        cpx     #94
        bne     inventory_craft
:       txa
        sec
        sbc     #76
        cmp     #11
        bcc     :+
        cmp     #94-76
        bne     @no
        lda     #FG_HIDE
:       sta     inventory_pile
        tay
        lda     inventory_group
        cmp     #2
        beq     @pack
        cmp     #3
        bne     @no
        lda     fg_gl,y
        sta     num
        lda     fg_gh,y
        jmp     @any
@pack:  lda     fg_pl,y
        sta     num
        lda     fg_ph,y
@any:   sta     num+1
        ora     num
        beq     @no
        sec
        rts
@no:    clc
        rts
; inventory_craft -- (lot 3, src/craft.s) X = 89..93, 95..97: BOW, SPEAR,
; CLUB, ROCK, SPLINT worn, in hand, in the pack or on the ground here (the
; BOW, the SPEAR, the SPLINT on their own cell; the CLUB and the ROCK
; settled by inventory_settle), the HUT, IGLOO, TRENCH standing here.
inventory_craft:
        txa
        sec
        sbc     #89
        tay
        lda     cr_b1,y
        bne     @group          ; ($FF: in no group)
        cpy     #2
        beq     @group          ; CLUB, ROCK: this cell's
        cpy     #3
        beq     @group
        cpy     #4
        bne     :+
        ldy     #2              ; the SPLINT's cell
:       lda     cr_cx,y
        cmp     px+1
        bne     @no
        lda     cr_cy,y
        cmp     py+1
        bne     @no
        lda     #0
@group: ldy     inventory_group
        cmp     inventory_places,y
        bne     @no
        lda     #0
        sta     num
        sta     num+1
        sec
        rts
@no:    clc
        rts

; inventory_settle -- src/craft.s cr_here: once the player has left the
; cell, the CLUB on the ground is lost and a ROCK not carried lies on any
; land cell.
inventory_settle:
        lda     cr_still
        bne     @rts
        inc     cr_still
        lda     cr_b1+2
        bne     :+
        dec     cr_b1+2
:       lda     cr_b1+3
        beq     :+
        cmp     #$FF
        bne     @rts
:       jsr     inventory_here
        asl     a
        lda     #0
        bcc     :+
        lda     #$FF
:       sta     cr_b1+3
@rts:   rts

; Shared cell query while STATUS is present (also the object USE preview).
inventory_here:
        lda     px
        asl     a
        lda     px+1
        rol     a
        tay
        lda     py
        asl     a
        lda     py+1
        rol     a
        tax
        jmp     cell_native

; inventory_name -- A/X = the name of item X: the vocabulary's, the region's
; species for 76..79, the second set's words (lot 4).
inventory_name:
        cpx     #76
        bcs     :+
        lda     it_name_lo,x
        pha
        lda     it_name_hi,x
        tax
        pla
        rts
:       cpx     #80
        bcs     @second
        txa                     ; region_species + 12 (X - 76)
        sbc     #76-1           ; (C clear: - 76)
        asl     a
        asl     a
        sta     inventory_x
        asl     a
        adc     inventory_x
        adc     #<region_species
        ldx     #>region_species
        bcc     @rts
        inx
@rts:   rts
@second:
        lda     inv_second_at-80,x
        pha
        lda     #om_to_sense
        jsr     text_fetch
        pla
        clc
        adc     #<tb_buf+7
        ldx     #>tb_buf
        bcc     @rts
        inx
        rts
inv_second_at: .byte 0, 5, 10, 18, 24, 30, 40, 0, 0     ; 80..88
            .byte 47, 51, 57, 74, 62, 69                ; 89..94 (lot 3)
inventory_pile: .byte 0
inventory_places: .byte 1,3,2,0,5
inv_space:
        lda     #' '|$80
        jmp     COUT
inventory_name_lo: .byte <inv_worn, <inv_hand, <inv_pack, 0, <inv_hung
inventory_name_hi: .byte >inv_worn, >inv_hand, >inv_pack, 0, >inv_hung
inv_worn:   .byte "WORN",0
inv_hand:   .byte "HANDS",0
inv_pack:   .byte "PACK",0
inv_hung:   .byte "LOCAL HUNG",0
inventory_x:    .byte 0
        .pushseg
        .segment "BSS"
obj_selected: .res 2            ; last item on each side; 0 is not an item
        .popseg
