; OBJECTS transaction editor. Lives beside TREE, outside STATUS/MEDVIEW.
; Everything up to object_commit is a read-only view of simulation state.
.segment "TREE"
om_line = overlay_text          ; modal-only copy; banked hints may overwrite tb_buf
object_menu:
        ldx     #MAXLINE
:       lda     ob_line,x
        sta     om_line,x
        dex
        bpl     :-
        lda     obj_side
        ldx     pg_cur
        cpx     #PG_EQUIPMENT
        bne     :+
        lda     ob_s
:       sta     om_side
        lda     #0
        sta     om_phase
        sta     om_action
        sta     om_many
        ldx     #0
:       lda     om_line,x
        inx
        cmp     #' '
        bne     :-
        stx     om_name
        lda     om_line
        cmp     #'C'
        bne     :+
        inc     om_action
:       cmp     #'D'
        bne     :+
        lda     #2
        sta     om_action
:       cmp     #'U'
        bne     :+
        lda     #4
        sta     om_action
:       lda     om_line
        cmp     #'L'
        bne     @normal
        lda     #4
        sta     om_action
        lda     #135            ; LOWER acts on FOOD/the whole bag, not this item
        sta     menu_noun
        lda     #$10
        sta     om_mask
        lda     #<om_lower
        sta     om_words_lo+4
        lda     #>om_lower
        sta     om_words_hi+4
        lda     #<om_t_restore
        sta     om_to_lo+4
        lda     #>om_t_restore
        sta     om_to_hi+4
        jmp     @valid_mask
@normal:ldx     menu_noun
        lda     #$17            ; PACK, HANDS, DROP, USE
        cpx     #22
        beq     @water
        cpx     #23
        bcc     @gear
        cpx     #38
        bcc     @food
        cpx     #76
        bcc     @gear
        cpx     #89
        bcc     @food
        cpx     #93
        beq     @wear
        cpx     #94
        bne     @mask
        lda     #5              ; HIDE: PACK or DROP
        bne     @many
@food:  lda     #<om_taste
        sta     om_words_lo+6
        lda     #>om_taste
        sta     om_words_hi+6
        lda     #<om_t_sense
        sta     om_to_lo+6
        lda     #>om_t_sense
        sta     om_to_hi+6
        lda     #$65             ; PACK, DROP, EAT, TASTE
@many:  inc     om_many
        bne     @mask
@water: inc     om_many
        lda     #7
        sta     om_action
        lda     #$C4            ; DROP, DRINK, GET
        bne     @mask
@gear:  cpx     #47
        bcc     :+
        cpx     #51
        bcs     :+
        cpx     #49             ; oxygen is applied, never swallowed
        beq     :+
        ora     #$20            ; oral medicine: EAT exactly one dose
:       cpx     #2
        bcc     @mask
        cpx     #9
        bcc     @wear
        cpx     #12
        bcc     @mask
        cpx     #21
        bcc     @wear
        cpx     #43
        beq     @wear
        cpx     #54
        bne     @mask
@wear:  ora     #8
@mask:  sta     om_mask
        ldx     menu_noun
        cpx     #N_WATER
        bne     @regular_mask
        lda     om_side
        beq     @local_water
        lda     #2
        sta     om_action
        lda     #$44
        bne     @source_mask
@local_water:
        lda     #$C0
        bne     @source_mask
@regular_mask:
        lda     om_side
        bne     @carried_mask
        lda     om_mask
        and     #$FB            ; LOCAL DROP must never touch the carried stock
        bne     @source_mask
@carried_mask:
        lda     om_many
        beq     @masked
        lda     om_mask
        and     #$FE            ; PACK of carried provisions would read LOCAL
        bne     @source_mask
@source_mask:
        sta     om_mask
@masked:
        ldx     menu_noun
        cpx     #89
        bcs     @valid_mask
        ldy     #om_usable_end-om_usable-1
@usable:
        txa
        cmp     om_usable,y
        beq     @valid_mask
        dey
        bpl     @usable
        lda     om_mask
        and     #$EF
        sta     om_mask
@valid_mask:
        ldx     om_action
        lda     om_bits,x
        and     om_mask
        bne     :+
        ldx     #0
@valid: lda     om_bits,x
        and     om_mask
        bne     @found
        inx
        bne     @valid
@found: stx     om_action
:       lda     ob_m
        sta     om_max
        lda     ob_m+1
        sta     om_max+1
        jsr     om_all
object_draw:
        jsr     om_project
        lda     #20
        jsr     vtab
        jsr     puts
        .byte   "ACTION: ",0
        ldx     om_action
        lda     om_words_lo,x
        ldy     om_words_hi,x
        jsr     print_str_ay
        ldx     om_name
@name:  lda     om_line,x
        beq     @source
        ora     #$80
        jsr     COUT
        inx
        bne     @name
@source:
        jsr     om_cr
        jsr     puts
        .byte   "FROM ",0
        lda     om_side
        bne     :+
        jsr     puts
        .byte   "LOCAL",0
        jmp     @quantity
:       jsr     puts
        .byte   "CARRIED",0
@quantity:
        jsr     puts
        .byte   " TO ",0
        ldx     om_action
        lda     om_to_lo,x
        ldy     om_to_hi,x
        jsr     print_str_ay
        lda     om_action
        cmp     #7
        bne     @qty_text
        lda     #'/'|$80
        jsr     COUT
        ldx     #0
        lda     it_place+64
        cmp     #2
        beq     @can_side
        inx
@can_side:
        lda     om_to_lo,x
        ldy     om_to_hi,x
        jsr     print_str_ay
@qty_text:
        lda     om_line
        cmp     #'L'
        bne     :+
        lda     #om_lower_detail
        jsr     om_bank_puts
        lda     om_bad
        jne     @capacity_line
        jmp     @need
:       jsr     puts
        .byte   " QTY ",0
        jsr     om_quantities
        beq     @single
        lda     om_qty
        sta     num
        lda     om_qty+1
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte   " OZ",0
        jmp     @preview
@single:
        lda     om_many
        beq     @use
        lda     #om_sample
        jsr     om_bank_puts
        jmp     @preview
@use:   lda     om_action
        cmp     #4
        bcc     @object
        ldx     menu_noun
        cpx     #41
        bcc     @object
        cpx     #52
        bcs     @object
        cpx     #43
        beq     @object
        jsr     puts
        .byte "1 USE; DOSES LEFT ",0
        lda     it_pack_lo,x
        sta     num
        lda     it_pack_hi,x
        bpl     :+
        lda     #0
        sta     num
:       sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " / ",0
        ldx     menu_noun
        lda     care_use_minutes-41,x
        sta     num
        lda     #0
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " MIN",0
        jmp     @preview
@object:jsr     puts
        .byte   "ONE OBJECT",0
@preview:
        lda     om_action
        cmp     #7
        beq     @need
        cmp     #4
        bcs     @capacity_line
@need:  jsr     puts
        .byte   " NEED ",0
        lda     om_v
        sta     num
        lda     om_v+1
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte   " IN3",0
@capacity_line:
        jsr     om_cr
        lda     om_bad
        beq     :+
        lda     #om_overflow
        jsr     om_bank_puts
        jmp     @preview_end
:
        lda     menu_noun
        cmp     #N_WATER
        bne     @forecast
        jsr     puts
        .byte   "CAN FREE ",0
        lda     #0
        sta     num+1
        lda     it_pack_hi+N_WATER
        bne     @full_can
        sec
        lda     #64
        sbc     it_pack_lo+N_WATER
        bcs     @can_free
@full_can:
        lda     #0
@can_free:
        sta     num
        jsr     print_u16
        jsr     puts
        .byte   " OZ ",0
@forecast:
        lda     om_line
        cmp     #'L'
        beq     @after
        lda     om_action
        cmp     #7
        beq     @after
        cmp     #4
        bcs     :+
@after: jsr     puts
        .byte   "FREE AFTER: ",0
        jmp     @free
:       jsr     puts
        .byte   "FREE NOW: ",0
@free:
        ldy     #0
        jsr     om_free
        jsr     puts
        .byte   " OZ  PACK ",0
        ldy     #4
        jsr     om_free
        jsr     puts
        .byte   " IN3  HANDS ",0
        ldy     #6
        jsr     om_free
        jsr     puts
        .byte   " WEAR ",0
        ldy     #2
        jsr     om_free
        jsr     puts
        .byte   " IN3",0
@preview_end:
        jsr     om_cr
        ldx     om_phase
        lda     om_help_ids,x
        jsr     om_bank_puts
        jsr     topo_pad
object_key:
        jsr     wait_key
        cmp     #KC_ESC
        bne     @enter
        lda     om_phase
        jeq     object_cancel
        dec     om_phase
        jsr     om_quantities
        bne     :+
        sta     om_phase        ; indivisible uses have no quantity screen
:       jmp     object_draw
@enter: cmp     #KC_RET
        bne     @arrows
        lda     om_phase
        cmp     #2
        jeq     object_commit
        inc     om_phase
        jsr     om_quantities
        jne     @draw
        lda     #2
        sta     om_phase
@draw:  jmp     object_draw
@arrows:
        ldx     om_phase
        cpx     #2
        beq     object_key
        cmp     #KC_UP
        beq     @up
        cmp     #KC_DOWN
        beq     @down
        cpx     #1
        bne     object_key
        cmp     #KC_LEFT
        beq     @one
        cmp     #KC_RIGHT
        bne     object_key
        lda     om_action
        cmp     #5              ; never ALL when consuming; GET WATER can use ALL
        jeq     object_key
        cmp     #6
        jeq     object_key
        jsr     om_all
        jmp     object_draw
@one:   lda     #1
        sta     om_qty
        lda     #0
        sta     om_qty+1
        jmp     object_draw
@up:    cpx     #0
        beq     @previous
        lda     om_qty
        cmp     om_max
        lda     om_qty+1
        sbc     om_max+1
        jcs     object_key
        inc     om_qty
        jne     @draw
        inc     om_qty+1
        jne     @draw
@down:  cpx     #0
        beq     @next
        lda     om_qty+1
        bne     :+
        lda     om_qty
        cmp     #2
        jcc     object_key
:       lda     om_qty
        bne     :+
        dec     om_qty+1
:       dec     om_qty
        jmp     object_draw
@previous:
        lda     #$FF
        bne     @step
@next:  lda     #1
@step:  sta     @step_amount+1
@cycle: lda     om_action
        clc
@step_amount: adc #1
        and     #7
        sta     om_action
        tax
        lda     om_bits,x
        and     om_mask
        beq     @cycle
        jsr     om_all
        lda     om_action
        cmp     #5
        beq     @meal_one
        cmp     #6
        jne     @draw
@meal_one:
        jmp     @one
object_cancel:
        lda     pg_cur
        cmp     #PG_EQUIPMENT
        bne     :+
        lda     #$40
        sta     obj_keep
        jmp     scr_equipment
:       lda     #1
        sta     ob_clear
        jmp     module_inventory
om_cr:  jsr     topo_pad
        jmp     CROUT
om_all: lda     ob_m
        sta     om_max
        lda     ob_m+1
        sta     om_max+1
        lda     om_action
        cmp     #5
        beq     @meal
        cmp     #6
        bne     :+
@meal:  ldx     menu_noun
        cpx     #38
        bcs     :+
        lda     om_max+1
        beq     :+
        lda     #255
        sta     om_max
        lda     #0
        sta     om_max+1
:       lda     om_max
        sta     om_qty
        lda     om_max+1
        sta     om_qty+1
        rts
om_free:
        sec
        lda     load_limits,y
        sbc     om_total,y
        sta     num
        lda     load_limits+1,y
        sbc     om_total+1,y
        sta     num+1
        bcs     :+
        lda     num
        eor     #$FF
        clc
        adc     #1
        sta     num
        lda     num+1
        eor     #$FF
        adc     #0
        sta     num+1
        jsr     puts
        .byte   "OVER ",0
:       jmp     print_u16

om_project:
        lda     #0
        sta     om_bad
        sta     om_v
        sta     om_v+1
        ldx     #7
:       lda     load_used,x
        sta     om_total,x
        dex
        bpl     :-
        lda     om_line
        cmp     #'L'
        jeq     @bag
        lda     menu_noun
        cmp     #N_WATER
        bne     @normal
        lda     om_action
        cmp     #2
        beq     @water
        cmp     #7
        jne     @done
@water: lda     it_place+64
        asl     a
        sta     om_from
        sta     om_dest
        lda     om_action
        cmp     #2
        bne     :+
        lda     #0
        sta     om_dest
:       lda     om_qty
        sta     om_w
        asl     a
        sta     om_v
        lda     om_qty+1
        sta     om_w+1
        rol     a
        sta     om_v+1
        bcc     :+
        inc     om_bad
:       jmp     @source
@normal:
        lda     om_action
        cmp     #4
        jcs     @done           ; USE/EAT/DRINK: simulation changes, no transfer forecast
        asl     a
        tax
        lda     om_destinations,x
        sta     om_dest
        ldx     menu_noun
        cpx     #22
        jeq     @done
        cpx     #76
        bcc     @first
        cpx     #89
        jcc     @done           ; native piles add no load
        cpx     #94
        jcs     @done
        lda     ob_crw-89,x
        sta     om_w
        lda     om_crvol-89,x
        sta     om_v
        lda     #0
        sta     om_w+1
        sta     om_v+1
        lda     cr_b1-89,x
        asl     a
        sta     om_from
        jmp     @source
@first:
        lda     it_oz_lo,x
        sta     om_w
        lda     it_oz_hi,x
        sta     om_w+1
        lda     it_vol_lo,x
        sta     om_v
        lda     it_vol_hi,x
        sta     om_v+1
        cpx     #21             ; native backpack volume is outside its own capacity
        bne     :+
        lda     #0
        sta     om_v
        sta     om_v+1
:       lda     it_place,x
        asl     a
        sta     om_from
        cpx     #23
        bcc     @source
        cpx     #38
        bcs     @source
        lda     #4              ; provisions occupy PACK even for CARRY
        sta     om_from
        lda     om_qty
        sta     om_w
        lda     om_qty+1
        sta     om_w+1
        lda     #0
        sta     om_v
        sta     om_v+1
        ldy     it_vol_lo,x
@volume:
        clc
        lda     om_v
        adc     om_w
        sta     om_v
        lda     om_v+1
        adc     om_w+1
        sta     om_v+1
        bcc     :+
        inc     om_bad
        lda     #$FF
        sta     om_v
        sta     om_v+1
        jmp     @source
:       dey
        bne     @volume
@source:
        lda     om_side
        bne     :+
        lda     #0
        sta     om_from
:       lda     om_w
        sta     num
        lda     om_w+1
        sta     num+1
        ldy     #0
        lda     om_from
        bne     @carried
        lda     om_dest
        beq     @done
        jsr     om_add
        jmp     @vol
@carried:
        lda     om_dest
        bne     @vol
        jsr     om_sub
@vol:   lda     om_v
        sta     num
        lda     om_v+1
        sta     num+1
        ldy     om_from
        beq     :+
        jsr     om_sub
:       ldy     om_dest
        beq     @done
        jsr     om_add
@done:  rts
; LOWER restores each first-set item marked 5; water is in its canteen.
; Reuse the ordinary read-only item calculation with the packed stock.
@bag:   lda     #4
        sta     om_dest
        ldx     #75
@bag_item:
        lda     it_place,x
        cmp     #5
        bne     @bag_next
        cpx     #N_WATER
        beq     @bag_next
        lda     it_pack_lo,x
        sta     om_qty
        lda     it_pack_hi,x
        sta     om_qty+1
        jsr     @first
@bag_next:
        dex
        bne     @bag_item
        sec
        lda     om_total+4
        sbc     load_used+4
        sta     om_v
        lda     om_total+5
        sbc     load_used+5
        sta     om_v+1
        rts
om_sub:
        sec
        lda     om_total,y
        sbc     num
        sta     om_total,y
        lda     om_total+1,y
        sbc     num+1
        sta     om_total+1,y
        rts
om_add:
        clc
        lda     om_total,y
        adc     num
        sta     om_total,y
        lda     om_total+1,y
        adc     num+1
        sta     om_total+1,y
        bcc     :+
        inc     om_bad
:       rts
om_crvol: .byte 90,90,200,100,120
om_destinations: .word 4,6,0,2
om_total: .res 8
om_from: .byte 0
om_dest: .byte 0
om_w: .word 0
om_v: .word 0

.pushseg
.segment "STATUS"
object_commit:
        ldx     om_action
        lda     om_words_lo,x
        sta     gp2
        lda     om_words_hi,x
        sta     gp2+1
        ldy     #0
@verb:  lda     (gp2),y
        beq     @name
        sta     inbuf,y
        iny
        bne     @verb
@name:  ldx     om_name
:       lda     om_line,x
        sta     inbuf,y
        beq     @amount
        inx
        iny
        bne     :-
@amount:
        jsr     om_quantities
        beq     @end
        lda     #' '
        sta     inbuf,y
        iny
        sty     om_out
        lda     om_qty
        sta     num
        lda     om_qty+1
        sta     num+1
        ldx     #0
        stx     om_started
@digit: lda     #'0'
        sta     om_digit
@sub:   sec
        lda     num
        sbc     om_tens,x
        tay
        lda     num+1
        sbc     om_tens+1,x
        bcc     @emit
        sta     num+1
        sty     num
        inc     om_digit
        bne     @sub
@emit:  lda     om_digit
        cmp     #'0'
        bne     :+
        ldy     om_started
        bne     :+
        cpx     #8
        bne     @next
:       inc     om_started
        ldy     om_out
        sta     inbuf,y
        inc     om_out
@next:  inx
        inx
        cpx     #10
        bcc     @digit
        ldy     om_out
@end:   lda     #0
        sta     inbuf,y
        sty     linelen
        lda     #S_CARRY
        sta     mq_list
        lda     #S_OBJECTS
        ldx     pg_cur
        cpx     #PG_EQUIPMENT
        bne     :+
        lda     #S_EQUIPMENT
:       sta     mq_list+1
        lda     #2
        sta     mq_n
        lsr     a
        sta     mq_i
        lda     journey_encounters
        sta     mq_enc
        lda     #$80
        sta     obj_keep
        lda     #20
        sta     WNDTOP
        lda     #0
        sta     shown
        jmp     obj_type
.popseg
om_words_lo: .byte <om_pack,<om_hand,<om_drop,<om_wear,<om_use,<om_eat,<om_drink,<om_get
om_words_hi: .byte >om_pack,>om_hand,>om_drop,>om_wear,>om_use,>om_eat,>om_drink,>om_get
om_pack: .byte "PACK ",0
om_hand: .byte "CARRY ",0
om_drop: .byte "DROP ",0
om_wear: .byte "WEAR ",0
om_use: .byte "USE ",0
om_eat: .byte "EAT ",0
om_drink: .byte "DRINK ",0
om_get: .byte "GET ",0
om_bits: .byte 1,2,4,8,16,32,64,128
om_help_ids: .byte om_h0,om_h1,om_h2
om_tens: .word 10000,1000,100,10,1
om_phase: .byte 0
om_action: .byte 0
om_many: .byte 0
om_mask: .byte 0
om_name: .byte 0
om_max: .word 0
om_qty: .word 0
om_out: .byte 0
om_digit: .byte 0
om_started: .byte 0
om_bad: .byte 0

om_side: .byte 0

om_to_lo: .byte <om_t_pack,<om_t_hand,<om_t_local,<om_t_worn,<om_t_use,<om_t_body,<om_t_body,<om_t_can
om_to_hi: .byte >om_t_pack,>om_t_hand,>om_t_local,>om_t_worn,>om_t_use,>om_t_body,>om_t_body,>om_t_can
om_t_pack: .byte "PACK",0
om_t_hand: .byte "HANDS",0
om_t_local: .byte "LOCAL",0
om_t_worn: .byte "WORN",0
om_t_use: .byte "USE",0
om_t_body: .byte "BODY",0
om_t_can: .byte "CANTEEN",0

om_usable: .byte 9,11,12,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,66,67,71,72,73
om_usable_end:

om_lower: .byte "LOWER ",0

om_t_restore: .byte "CARRIED",0

om_taste: .byte "TASTE ",0
om_t_sense: .byte "SENSES",0
; TASTE is a native inspection: no amount, no ounce, no consumption.
om_quantities:
        lda     om_action
        cmp     #6
        bne     @ordinary
        lda     menu_noun
        cmp     #N_WATER
        beq     @ordinary
        lda     #0
        rts
@ordinary:
        lda     om_many
        rts
om_bank_puts:
        jsr     text_fetch
        jmp     print_str_ax
