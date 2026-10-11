; Grouped inventory: each placement gets its own pages, no duplicate ounces.
.segment "SCREENS"
module_inventory:
        lda     #0
        sta     inventory_group
        sta     inventory_page
inventory_redraw:
        jsr     text_screen
        jsr     load_totals
        lda     #0
        sta     inventory_count
        ldx     #1
@count: jsr     inventory_match
        bcc     :+
        inc     inventory_count
:       inx
        cpx     #76
        bcc     @count
        lda     inventory_count
        ldx     #1
@pages: cmp     #13
        bcc     @pages_done
        sec
        sbc     #12
        inx
        bne     @pages
@pages_done:
        stx     inventory_pages
        jsr     puts
        .byte "INVENTORY PAGE ",0
        lda     inventory_page
        clc
        adc     #1
        jsr     pdec
        jsr     puts
        .byte "/",0
        lda     inventory_pages
        jsr     pdec
        jsr     CROUT
        ldx     inventory_group
        lda     #<inventory_groups
        sta     gp2
        lda     #>inventory_groups
        sta     gp2+1
        lda     #12
        jsr     word
        lda     #0
        sta     inventory_capacity
@capacity:
        jsr     CROUT
        ldx     inventory_capacity
        lda     #<load_words
        sta     gp2
        lda     #>load_words
        sta     gp2+1
        lda     #8
        jsr     word
        lda     #10
        jsr     tab
        lda     inventory_capacity
        asl
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
        bcc     @capacity
        jsr     puts
        .byte "|---------------------------------------",0
        lda     #0
        sta     inventory_skip
        sta     inventory_lines
        ldx     inventory_page
        beq     @items
@skip:  clc
        adc     #12
        dex
        bne     @skip
        sta     inventory_skip
@items: lda     #1
        sta     inventory_item
@item:  ldx     inventory_item
        jsr     inventory_match
        bcc     @next
        lda     inventory_skip
        beq     @print
        dec     inventory_skip
        jmp     @next
@print: jsr     CROUT
        ldx     inventory_item
        lda     it_name_lo,x
        pha
        lda     it_name_hi,x
        tax
        pla
        jsr     print_str_ax
        lda     #15
        jsr     tab
        ldx     inventory_item
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
@line:  inc     inventory_lines
        lda     inventory_lines
        cmp     #12
        bcs     @footer
@next:  inc     inventory_item
        lda     inventory_item
        cmp     #76
        bcc     @item
        lda     inventory_lines
        bne     @footer
        jsr     puts
        .byte "|NONE",0
@footer:
        lda     #19
        jsr     vtab
        jsr     puts
        .byte "1 WORN 2 HAND 3 PACK 4 HERE 5 HUNG|GET/WEAR/PACK/CARRY/DROP|SPACE/N NEXT  B BACK  ESC VIEW",0
inventory_key:
        jsr     wait_key
        cmp     #KC_ESC
        jeq     back_to_view_now
        cmp     #'1'
        bcc     @navigation
        cmp     #'6'
        bcs     @navigation
        sec
        sbc     #'1'
        sta     inventory_group
        lda     #0
        sta     inventory_page
        jmp     inventory_redraw
@navigation:
        cmp     #'B'
        beq     @back
        cmp     #' '
        beq     @forward
        cmp     #KC_RET
        beq     @forward
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
        beq     inventory_key
        dec     inventory_group
        jmp     inventory_redraw

; X is preserved; carry means membership, num holds provision ounces.
inventory_match:
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
inventory_places: .byte 1,3,2,0,5
inventory_groups: .byte "WORN        IN HAND     IN PACK     GROUND HERE HUNG HERE   "
inventory_group: .byte 0
inventory_page: .byte 0
inventory_pages: .byte 0
inventory_count: .byte 0
inventory_capacity: .byte 0
inventory_skip: .byte 0
inventory_lines: .byte 0
inventory_item: .byte 0
