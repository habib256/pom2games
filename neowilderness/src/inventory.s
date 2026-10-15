; Grouped inventory, 80 columns (14 October 2026): each placement is a group
; (tab), its items in three columns of sixteen rows, no duplicate ounces.
; Part of the STATUS module (SIM window, src/status.s): scr_inventory
; computes the load totals (SIM) first, then fetches the module.
;
;   row 0       the tab row: OBJECTS (15 October 2026)
;   row 2       the five groups and their counts, the shown one in inverse
;               when the group row has the focus, else in brackets
;   row 3       the group's name (in inverse)
;   rows 4-14   the items of the page, across then down (33 a page)
;   row 15      PAGE p/n (in inverse, at column 67)
;   rows 16-19  CARRYING (from STATUS, 15 October 2026): food and water
;               carried, here, within reach
;   row 21      FREE: the four capacities left
;   rows 22-23  the keys
; On NeoWildernessXL the group and CARRYING are post-its (src/mt_pages.s).
INV_ROWS = 11                   ; rows of items
INV_PAGE = 3 * INV_ROWS         ; items a page
INV_COL  = 26                   ; column width; quantity at +13
.segment "STATUS"
module_inventory:
        jsr     forage_here     ; lot 4: the ground piles of this cell
        jsr     inventory_settle ; lot 3: the CLUB, the ROCK of this cell
        lda     #0
        sta     inventory_group
        sta     inventory_page
inventory_redraw:
        lda     #PG_INVENTORY   ; the tab row (src/pages.s)
        jsr     page_top
        jsr     inventory_counts
        ldx     inventory_group
        lda     inventory_n,x
        sta     inventory_count
        ldx     #1              ; pages: 1 + (count - 1) / INV_PAGE
        sec
        sbc     #1
        bcc     @pages_done     ; no item: one page
@pages: sbc     #INV_PAGE
        bcc     @pages_done
        inx
        bne     @pages
@pages_done:
        stx     inventory_pages
        lda     inventory_page
        cmp     inventory_pages
        bcc     :+
        dex                     ; backward group transition selects last page
        stx     inventory_page
:
        ; the tabs (row 2)
        ldx     #0
@tab:   stx     inventory_tab
        ldy     #' '|$80        ; the group's edges
        cpx     inventory_group
        bne     @edge
        lda     pg_focus        ; the group shown: in inverse when its row
        cmp     #1              ; has the focus, else between brackets
        bne     :+
        lda     #$3F
        sta     INVFLG
        bne     @edge
:       ldy     #'['|$80
@edge:  sty     inventory_edge
        tya
        jsr     COUT
        txa
        clc
        adc     #'1'|$80
        jsr     COUT
        lda     #' '|$80
        jsr     COUT
        ldx     inventory_tab
        lda     inventory_name_lo,x
        ldy     inventory_name_hi,x
        jsr     print_str_ay
        lda     #' '|$80
        jsr     COUT
        ldx     inventory_tab
        lda     inventory_n,x
        jsr     pdec
        lda     inventory_edge  ; ' ' stays ' ', '[' becomes ']'
        cmp     #'['|$80
        bne     :+
        lda     #']'|$80
:       jsr     COUT
        lda     #$FF
        sta     INVFLG
        lda     #' '|$80
        jsr     COUT
        ldx     inventory_tab
        inx
        cpx     #5
        bcc     @tab
        jsr     puts            ; row 3: the group's name in inverse; each
        .byte "|",0             ; item row starts with CROUT
        lda     #$3F
        sta     INVFLG
        jsr     inv_space
        ldx     inventory_group
        lda     inventory_name_lo,x
        ldy     inventory_name_hi,x
        jsr     print_str_ay
        jsr     inv_space
        lda     #$FF
        sta     INVFLG
        ; the items of the page, across then down
        lda     #0
        sta     inventory_skip
        sta     inventory_lines
        ldx     inventory_page
        beq     @items
@skip:  clc
        adc     #INV_PAGE
        dex
        bne     @skip
        sta     inventory_skip
@items: lda     #1
        sta     inventory_item
@item:  ldx     inventory_item
        jsr     inventory_match
        jcc     @next
        lda     inventory_skip
        beq     @print
        dec     inventory_skip
        jmp     @next
@print: lda     inventory_lines ; column (lines mod 3) * INV_COL
        ldx     #0
:       cmp     #3
        bcc     :+
        sbc     #3
        bcs     :-
:       tax
        lda     inventory_cols,x
        bne     :+
        jsr     CROUT           ; a new row
        lda     #0
:       jsr     tab
        lda     CH
        sta     inventory_x
        ldx     inventory_item
        jsr     inventory_name
        jsr     print_str_ax
        lda     inventory_x
        clc
        adc     #13
        jsr     tab
        ldx     inventory_item
        cpx     #76
        jcs     @second
        cpx     #N_WATER
        bcc     @line
        cpx     #38
        bcs     @uses
        jsr     inventory_match
        jsr     print_u16
        jsr     puts
        .byte " OZ",0
        jmp     @line
@uses:  cpx     #41
        bcc     @line
        cpx     #52
        bcs     @line
        cpx     #43             ; sunglasses are equipment, not a consumable
        beq     @line
        lda     it_pack_lo,x
        sta     num
        lda     it_pack_hi,x
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " USES",0
        jmp     @line
@second:                        ; lot 4: ounces, SPOIL past its counter
        cpx     #89             ; lot 3: the crafted things, no quantity
        bcc     :+
        cpx     #94
        jne     @line
:       jsr     inventory_match
        jsr     print_u16
        jsr     puts
        .byte " OZ",0
        lda     inventory_pile
        cmp     #FG_HIDE
        beq     @line
        clc
        ldy     inventory_group
        cpy     #2
        beq     :+
        adc     #FG_CGND
:       tax
        lda     fg_ch,x
        bmi     :+
        ora     fg_cl,x
        bne     @line
:       jsr     puts
        .byte " SPOIL",0
@line:  inc     inventory_lines
        lda     inventory_lines
        cmp     #INV_PAGE
        bcs     @footer
@next:  inc     inventory_item
        lda     inventory_item
        cmp     #98             ; lots 4, 3: the second set up to TRENCH
        jcc     @item
        lda     inventory_lines
        bne     @footer
        jsr     puts
        .byte "|NONE",0
@footer:
        lda     #15             ; PAGE p/n on row 15, in inverse
        jsr     vtab
        lda     #67
        jsr     tab
        lda     #$3F
        sta     INVFLG
        jsr     puts
        .byte " PAGE ",0
        lda     inventory_page
        clc
        adc     #1
        jsr     pdec
        lda     #'/'|$80
        jsr     COUT
        lda     inventory_pages
        jsr     pdec
        jsr     inv_space
        lda     #$FF
        sta     INVFLG
        jsr     puts            ; rows 16-19: CARRYING, food and water
        .byte "|",0
        jsr     st_heading
        .byte " CARRYING ",0
        lda     #ST_FOOD
        jsr     tab
        jsr     puts
        .byte "FOOD",0
        lda     #ST_WATER
        jsr     tab
        jsr     puts
        .byte "WATER",0
        lda     g1              ; (g1 kept: reach_oz's scratch; the
        pha                     ; reference's INVENTORY leaves it alone)
        lda     #0
        sta     status_stock_kind
:       jsr     CROUT
        jsr     status_stock_line
        inc     status_stock_kind
        lda     status_stock_kind
        cmp     #3
        bcc     :-
        pla
        sta     g1
        lda     #21
        jsr     vtab
        jsr     puts            ; at most 77 characters: never column 79
        .byte "FREE  ",0
        lda     #0
        sta     inventory_capacity
@capacity:
        beq     :+
        jsr     puts
        .byte "  ",0
:
        ldx     inventory_capacity
        lda     #<load_words
        sta     gp2
        lda     #>load_words
        sta     gp2+1
        lda     #8
        jsr     word
        lda     #' '|$80
        jsr     COUT
        lda     inventory_capacity
        asl     a
        tay
        sec
        lda     load_limits,y
        sbc     load_used,y
        sta     num
        lda     load_limits+1,y
        sbc     load_used+1,y
        sta     num+1
        jsr     print_u16
        lda     inventory_capacity
        bne     @volume
        jsr     puts
        .byte " OZ",0
        jmp     @capacity_next
@volume:
        jsr     puts
        .byte " IN3",0
@capacity_next:
        inc     inventory_capacity
        lda     inventory_capacity
        cmp     #4
        jcc     @capacity
        XL_IMM  XI_STATUS, <inventory_keys_x, @x26
        lda     #<inventory_keys
        XL_IMM  XI_STATUS, >inventory_keys_x, @x27
        ldy     #>inventory_keys
        XL_ABS  XI_STATUS, page_foot_x, @x28
        jsr     page_foot
inventory_key:
        jsr     wait_key
        jsr     page_keys       ; the pages, TOPO, the view
        ldy     pg_focus        ; the focus: 0 the tab row, 1 the group row
        cmp     #KC_DOWN        ; and the pages of its group
        beq     @down
        cmp     #KC_UP
        beq     @up
        ldx     inventory_group ; LEFT/RIGHT (below the tab row: page_keys
        cmp     #KC_RIGHT       ; turns the pages on it) change the group
        bne     :+
        inx
        cpx     #5
        bcc     @group_x
        ldx     #0
        beq     @group_x
:       cmp     #KC_LEFT
        bne     @digit
        dex
        bpl     @group_x
        ldx     #4
@group_x:
        txa
        bpl     @group
@down:  tya                     ; the tab row: down to the group row
        beq     @focus
        ldx     inventory_page  ; then the next page, the view after the
        inx                     ; last one
        cpx     inventory_pages
        bcs     @end
        stx     inventory_page
        bcc     @redraw
@up:    tya                     ; nothing above the tab row
        beq     inventory_key
        lda     inventory_page  ; up a page, the tab row above the first
        beq     @focus
        dec     inventory_page
        jmp     inventory_redraw
@focus: tya                     ; Y = 0: focus 1, Y = 1: focus 0
        eor     #1
        sta     pg_focus
        jmp     inventory_redraw
@digit: cmp     #'1'
        bcc     @navigation
        cmp     #'6'
        bcs     @navigation
        sec
        sbc     #'1'
@group: sta     inventory_group
        lda     #0
        sta     inventory_page
        jmp     inventory_redraw
@navigation:
        cmp     #'B'
        beq     @back
        cmp     #'N'
        bne     inventory_key
@forward:
        inc     inventory_page
        lda     inventory_page
        cmp     inventory_pages
        bcc     @redraw
        lda     #0
        sta     inventory_page
        inc     inventory_group
        lda     inventory_group
        cmp     #4
        bcc     @redraw
        bne     @end
        lda     it_place+21
        cmp     #5
        beq     @redraw
@end:   jmp     back_to_view_now
@redraw: jmp    inventory_redraw
@back:  lda     inventory_page
        beq     @group_back
        dec     inventory_page
        jmp     inventory_redraw
@group_back:
        lda     inventory_group
        jeq     inventory_key
        dec     inventory_group
        lda     #255            ; resolved after counting the preceding group
        sta     inventory_page
        jmp     inventory_redraw

; inventory_counts -- inventory_n: the items of each group (the tabs).
inventory_counts:
        lda     inventory_group
        pha
        ldy     #4
@group: sty     inventory_group
        lda     #0
        sta     inventory_n,y
        ldx     #1
@count: jsr     inventory_match
        bcc     :+
        ldy     inventory_group
        lda     inventory_n,y
        clc
        adc     #1
        sta     inventory_n,y
:       inx
        cpx     #98
        bcc     @count
        ldy     inventory_group
        dey
        bpl     @group
        pla
        sta     inventory_group
        rts

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
        cpx     #95
        bcs     @shelter
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
@shelter:
        txa
        sbc     #95             ; (C set)
        tay
        lda     cr_sx,y
        cmp     px+1
        bne     @no
        lda     cr_sy,y
        cmp     py+1
        bne     @no
        lda     #0
        beq     @group
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
:       lda     px
        asl     a
        lda     px+1
        rol     a
        tay
        lda     py
        asl     a
        lda     py+1
        rol     a
        tax
        jsr     cell_native
        asl     a
        lda     #0
        bcc     :+
        lda     #$FF
:       sta     cr_b1+3
@rts:   rts

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
        clc
        adc     #<inv_second
        ldx     #>inv_second
        bcc     @rts
        inx
        rts
inv_second: .byte "GAME",0,"FISH",0,"INSECTS",0,"FRUIT",0,"CACTI",0,"MUSHROOMS",0,"PLANTS",0
            .byte "BOW",0,"SPEAR",0,"CLUB",0,"SPLINT",0,"HIDE",0,"HUT",0,"IGLOO",0,"TRENCH",0
            .byte "ROCK",0
inv_second_at: .byte 0, 5, 10, 18, 24, 30, 40, 0, 0     ; 80..88
            .byte 47, 51, 57, 91, 62, 69, 74, 78, 84    ; 89..97 (lot 3)
inventory_pile: .byte 0
inventory_places: .byte 1,3,2,0,5
inventory_cols:   .byte 0, INV_COL+1, 2 * INV_COL+1   ; (0: column 1 in a post-it, XL)
inv_space:
        lda     #' '|$80
        jmp     COUT
inventory_name_lo: .byte <inv_worn, <inv_hand, <inv_pack, <inv_ground, <inv_hung
inventory_name_hi: .byte >inv_worn, >inv_hand, >inv_pack, >inv_ground, >inv_hung
inv_worn:   .byte "WORN",0
inv_hand:   .byte "IN HAND",0
inv_pack:   .byte "IN PACK",0
inv_ground: .byte "GROUND HERE",0
inv_hung:   .byte "HUNG HERE",0
inventory_group: .byte 0
inventory_page: .byte 0
inventory_pages: .byte 0
inventory_count: .byte 0
inventory_capacity: .byte 0
inventory_skip: .byte 0
inventory_lines: .byte 0
inventory_item: .byte 0
inventory_tab:  .byte 0
inventory_x:    .byte 0
inventory_edge: .byte 0
inventory_n:    .res 5
