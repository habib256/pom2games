; OBJECTS transaction editor. Lives beside TREE, outside STATUS/MEDVIEW.
; Everything up to object_commit is a read-only view of simulation state.
.segment "TREE"
.export om_total, om_from, om_dest, om_w, om_v
.export om_phase, om_action, om_many, om_mask, om_name, om_max, om_qty
.export om_out, om_digit, om_started, om_bad, om_side
om_line = overlay_text          ; command [0,36], modal state [37,64]; no page list is live
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
        lda     #om_lower_word
        sta     om_words+4
        lda     #om_carried_label
        sta     om_to+4
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
@food:  lda     #om_taste_word
        sta     om_words+6
        lda     #om_to_sense
        sta     om_to+6
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
        lda     om_many
        bne     @usable_check   ; split piles use source quantities, not place
        cpx     #89
        bcs     @crafted_place
        lda     it_place,x
        bcc     @place
@crafted_place:
        lda     cr_b1-89,x
@place: tay
        lda     om_place_masks,y
        and     om_mask
        cpx     #21             ; the backpack can never contain itself
        bne     :+
        and     #$FE
:       sta     om_mask
@usable_check:
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
:       jsr     om_all
object_draw:
        jsr     om_project
        lda     #20
        jsr     vtab
        lda     #om_action_label
        jsr     om_bank_puts
        ldx     om_action
        lda     om_words,x
        jsr     om_bank_puts
        ldx     om_name
@name:  lda     om_line,x
        beq     @source
        ora     #$80
        jsr     COUT
        inx
        bne     @name
@source:
        jsr     om_cr
        lda     #om_from_label
        jsr     om_bank_puts
        lda     om_side
        bne     :+
        lda     #om_local_label
        jsr     om_bank_puts
        jmp     @quantity
:       lda     #om_carried_label
        jsr     om_bank_puts
@quantity:
        lda     #om_to_label
        jsr     om_bank_puts
        ldx     om_action
        lda     om_to,x
        jsr     om_bank_puts
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
        lda     om_to,x
        jsr     om_bank_puts
@qty_text:
        lda     om_line
        cmp     #'L'
        bne     :+
        lda     #om_lower_detail
        jsr     om_bank_puts
        lda     om_bad
        jne     @capacity_line
        jmp     @need
:       lda     #om_qty_label
        jsr     om_bank_puts
        jsr     om_quantities
        beq     @single
        lda     om_qty
        sta     num
        lda     om_qty+1
        sta     num+1
        jsr     print_u16
        lda     #om_unit_oz
        jsr     om_bank_puts
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
        lda     #om_doses_label
        jsr     om_bank_puts
        ldx     menu_noun
        lda     it_pack_lo,x
        sta     num
        lda     it_pack_hi,x
        bpl     :+
        lda     #0
        sta     num
:       sta     num+1
        jsr     print_u16
        lda     #om_separator
        jsr     om_bank_puts
        ldx     menu_noun
        lda     care_use_minutes-41,x
        sta     num
        lda     #0
        sta     num+1
        jsr     print_u16
        lda     #om_unit_min
        jsr     om_bank_puts
        jmp     @preview
@object:lda     #om_object_label
        jsr     om_bank_puts
@preview:
        lda     om_action
        cmp     #7
        beq     @need
        cmp     #4
        bcs     @capacity_line
@need:  lda     #om_need
        jsr     om_bank_puts
        lda     om_v
        sta     num
        lda     om_v+1
        sta     num+1
        jsr     print_u16
        lda     #om_in3_label
        jsr     om_bank_puts
        jsr     om_weight_change
@capacity_line:
        jsr     om_cr
        lda     om_bad
        beq     :+
        lda     #om_overflow
        jsr     om_bank_puts
        jmp     @preview_end
:
        jsr     om_requirement
        beq     :+
        jsr     om_bank_puts
        jmp     @preview_end
:
        lda     menu_noun
        cmp     #N_WATER
        bne     @forecast
        lda     #om_can_free
        jsr     om_bank_puts
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
        lda     #om_unit_oz_space
        jsr     om_bank_puts
@forecast:
        lda     om_line
        cmp     #'L'
        beq     @after
        lda     om_action
        cmp     #7
        beq     @after
        cmp     #4
        bcs     :+
@after: lda     #om_free_after
        bne     @free_text
:       lda     #om_free_now
@free_text:
        jsr     om_bank_puts
@free:
        ldy     #0
        jsr     om_free
        lda     #om_pack_free
        jsr     om_bank_puts
        ldy     #4
        jsr     om_free
        lda     #om_hands_free
        jsr     om_bank_puts
        ldy     #6
        jsr     om_free
        lda     #om_wear_free
        jsr     om_bank_puts
        ldy     #2
        jsr     om_free
        lda     #om_in3_label
        jsr     om_bank_puts
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
        lda     om_qty
        cmp     om_max
        lda     om_qty+1
        sbc     om_max+1
        bcs     @one            ; ALL -> 1: restart the quick quantity cycle
        asl     om_qty
        rol     om_qty+1
        bcs     @all            ; preserve exact source stock on 16-bit overflow
        lda     om_qty
        cmp     om_max
        lda     om_qty+1
        sbc     om_max+1
        jcc     @draw
@all:
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
        lda     #om_over
        jsr     om_bank_puts
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
om_destinations: .byte 4,6,0,2
om_total = overlay_text+37
om_from = overlay_text+45
om_dest = overlay_text+46
om_w = overlay_text+47
om_v = overlay_text+49

.pushseg
.segment "STATUS"
object_commit:
        ldx     om_action
        lda     om_words,x
        jsr     text_fetch
        sta     gp2
        stx     gp2+1
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
        lda     #0
        sta     om_started
        ldx     #8
@digit: lda     #'0'
        sta     om_digit
@sub:   sec
        lda     num
        sbc     pow10,x
        tay
        lda     num+1
        sbc     pow10+1,x
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
        cpx     #0
        bne     @next
:       inc     om_started
        ldy     om_out
        sta     inbuf,y
        inc     om_out
@next:  dex
        dex
        bpl     @digit
        ldy     om_out
@end:   lda     #0
        sta     inbuf,y
        sty     linelen
        lda     #S_OBJECTS
        ldx     pg_cur
        cpx     #PG_EQUIPMENT
        bne     :+
        lda     #S_EQUIPMENT
:       sta     mq_list         ; previous-step guard: both page entries have flags 0
        sta     mq_list+1
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
om_words: .byte om_pack_word,om_hand_word,om_drop_word,om_wear_word,om_use_word,om_eat_word,om_drink_word,om_get_word
om_bits: .byte 1,2,4,8,16,32,64,128
om_place_masks: .byte $FF,$F7,$FE,$FD
om_help_ids: .byte om_h0,om_h1,om_h2
om_phase = overlay_text+51
om_action = overlay_text+52
om_many = overlay_text+53
om_mask = overlay_text+54
om_name = overlay_text+55
om_max = overlay_text+56
om_qty = overlay_text+58
om_out = overlay_text+60
om_digit = overlay_text+61
om_started = overlay_text+62
om_bad = overlay_text+63

om_side = overlay_text+64
.assert om_side < overlay_text+160, error, "modal scratch exceeds overlay_text"

om_to: .byte om_to_pack,om_to_hand,om_local_label,om_to_worn,om_to_use,om_to_body,om_to_body,om_to_can

om_usable: .byte 9,11,12,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,66,67,71,72,73
om_usable_end:

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
; Shared bank printer is in STATUS, which stays loaded while the modal runs.
.pushseg
.segment "STATUS"
om_bank_puts:
        jsr     text_fetch
        jmp     print_str_ax

; Signed change in carried ounces, not item weight: internal moves cost 0.
; LOWER uses the aggregate projection, never the last visited item's weight.
om_weight_change:
        lda     om_bad
        bne     @done
        lda     #om_weight_label
        jsr     om_bank_puts
        sec
        lda     om_total
        sbc     load_used
        sta     num
        lda     om_total+1
        sbc     load_used+1
        sta     num+1
        bcs     @positive
        lda     num
        eor     #$FF
        clc
        adc     #1
        sta     num
        lda     num+1
        eor     #$FF
        adc     #0
        sta     num+1
        lda     #'-'|$80
        bne     @sign
@positive:
        lda     #'+'|$80
@sign:  jsr     COUT
        jsr     print_u16
        lda     #om_unit_oz
        jmp     om_bank_puts
@done:  rts
.popseg

; Exact native prerequisites only; no preparation or simulation during drawing.
om_requirement:
        lda     om_action
        cmp     #4
        bne     @none
        ldx     menu_noun
        txa
        sec
        sbc     #52
        cmp     #5
        bcc     @instrument
        cpx     #71
        beq     @stove
        cpx     #66
        jeq     @stock
        cpx     #39
        jeq     @glass
        cpx     #40
        jeq     @stock
        cpx     #38
        beq     @matches
        cpx     #67
        beq     @bait
        cpx     #72
        beq     @bait
        cpx     #41
        bne     @none
        lda     light
        beq     @dark
        lda     #om_light_ready
        rts
@dark:  lda     #om_need_light
        rts
@bait:  lda     fg_bait
        beq     @missing
        lda     #om_bait_ready
        rts
@missing:
        lda     #om_need_bait
        rts
@none:  lda     #0
        rts
@instrument:
        cpx     #53
        beq     @instrument_ready
        lda     period
        beq     @instrument_dark
        cmp     #2
        bcc     @twilight
        cmp     #4
        bcc     @instrument_ready
@twilight:
        lda     weather_sky
        beq     @instrument_ready
@instrument_dark:
        lda     #om_instrument_dark
        rts
@instrument_ready:
        lda     @instrument_ids-52,x
        rts
@instrument_ids:
        .byte om_map_ready,om_compass_ready,om_watch_ready,om_altimeter_ready,om_chart_refused
@stove:
        lda     camp_use
        and     #U_FUEL
        beq     @fuel_inactive
        lda     fire_near
        bne     @ignited
        lda     camp_use
        and     #U_MATCH
        beq     @no_ignition
@ignited:
        lda     it_place+71
        beq     @stove_down
        lda     #om_stove_ready
        rts
@stove_down:
        lda     #om_stove_already_down
        rts
@fuel_inactive:
        lda     #om_fuel_inactive
        rts
@no_ignition:
        lda     #om_no_ignition
        rts
@matches:
        lda     shelter_inside
        beq     @outside
        lda     #om_matches_inside
        rts
@outside:
        lda     geo_wooded
        pha
        lda     geo_water_kind
        pha
        jsr     inventory_here
        tax
        pla
        sta     geo_water_kind
        pla
        sta     geo_wooded
        txa
        bmi     @water
        jsr     camp_storm
        bcc     @stock
        lda     camp_use
        and     #U_FUEL
        bne     @stock
        lda     weather_sky
        cmp     #2
        beq     @rain
        lda     #om_matches_wind
        rts
@rain:  lda     #om_matches_rain
        rts
@water: lda     #om_matches_water
        rts
@glass:
        lda     #om_glass_outside
        ldx     shelter_inside
        bne     @return
        lda     #om_glass_day
        ldx     night
        bne     @return
        lda     #om_glass_clear
        ldx     weather_sky
        bne     @return
        lda     #om_glass_sun
        rts
@stock: ldx     menu_noun
        lda     it_pack_hi,x
        bmi     @empty
        ora     it_pack_lo,x
        beq     @empty
        lda     #om_flash_ready
        cpx     #66
        beq     @return
        lda     #om_fuel_ready
        cpx     #38
        bne     @return
        lda     #om_matches_ready
@return:tax                     ; callers branch on the returned text ID
        rts
@empty: lda     #om_flash_empty
        cpx     #66
        beq     @return
        lda     #om_fuel_empty
        cpx     #38
        bne     @return
        lda     #om_matches_empty
        rts
