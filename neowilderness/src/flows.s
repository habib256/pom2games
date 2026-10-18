; VERHILLE Arnaud — GPL-3.0. Deliberate survival follow-ups.
; UI only: every acceptance enters an existing native command/form. No stock,
; elapsed time or RNG is changed by opening, browsing or cancelling this menu.
.segment "GUIDANCE"
navigation_flows:
        ; A = first choice (0 food, 4 water), supplied by SURVIVAL.
        sta     flow_first
        lda     #4
        ldx     flow_first
        beq     :+
        lda     #3
:       sta     flow_count
        lda     dep_running
        sec
        sbc     #1
        sec
        sbc     flow_first
        cmp     flow_count
        bcc     :+
        lda     #0
:       sta     flow_cursor
flow_draw:
        clc
        lda     flow_first
        adc     flow_cursor
        tay
        lda     flow_text_lo,y
        ldx     flow_text_hi,y
        jsr     message
flow_key:
        jsr     guidance_view_key
        cmp     #KC_ESC
        beq     flow_cancel
        cmp     #KC_UP
        beq     @up
        cmp     #KC_DOWN
        beq     @down
        cmp     #KC_RET
        bne     flow_key
        clc
        lda     flow_first
        adc     flow_cursor
        tay
        tya
        clc
        adc     #1
        sta     dep_running     ; UI memory, never a simulation queue.
        lda     flow_verbs,y
        jmp     flow_leave
@up:    dec     flow_cursor
        bpl     flow_draw
        lda     flow_count
        sec
        sbc     #1
        sta     flow_cursor
        jmp     flow_draw
@down:  inc     flow_cursor
        lda     flow_cursor
        cmp     flow_count
        bcc     flow_draw
        lda     #0
        sta     flow_cursor
        beq     flow_draw
flow_cancel:
        lda     #$FF
flow_leave:
        pha
        lda     #10
        jsr     overlay_load
        pla
        jmp     flows_execute
flow_cursor: .byte 0
flow_first: .byte 0
flow_count: .byte 0
; Fixed identities in verb_table; every choice reopens a native source list.
flow_verbs: .byte 7,19,17,5,7,18,6
flow_text_lo: .byte <flow_get,<flow_skin,<flow_cook,<flow_eat,<flow_collect,<flow_boil,<flow_drink
flow_text_hi: .byte >flow_get,>flow_skin,>flow_cook,>flow_eat,>flow_collect,>flow_boil,>flow_drink
flow_get: .byte "1/4 RECOVER MEAT: GROUND TO PACK|UP/DOWN CHOOSE RET:GET ESC:BACK",0
flow_skin: .byte "2/4 SKIN: MEAT TO HIDE, TAKES TIME|UP/DOWN CHOOSE RET:SKIN ESC:BACK",0
flow_cook: .byte "3/4 COOK: PACK TO GROUND; NEED HEAT|UP/DOWN CHOOSE RET:COOK ESC:BACK",0
flow_eat: .byte "4/4 EAT: FOOD STOCK DECREASES|UP/DOWN CHOOSE RET:PORTION ESC:BACK",0
flow_collect: .byte "1/3 COLLECT: WATER TO CANTEEN|UP/DOWN CHOOSE RET:GET ESC:BACK",0
flow_boil: .byte "2/3 BOIL: CANTEEN TO GROUND; 15 MIN|NEED HEAT/UTENSILS|UP/DOWN RET:PORTION ESC:BACK",0
flow_drink: .byte "3/3 DRINK: SOURCE / CANTEEN / GROUND|UP/DOWN CHOOSE RET:PORTION ESC:BACK",0
