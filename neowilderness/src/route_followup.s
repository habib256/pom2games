; A completed survival/care command may offer the retained trip explicitly.
; This state is UI only. Choosing a mode opens its ordinary native form.
.segment "CAMPUI"
route_post_action:
        lda     #0
        sta     route_context
        lda     dead
        ora     won
        jne     refusal_close
        lda     verb
        ldx     #route_care_end-route_care_verbs-1
@eligible:
        cmp     route_care_verbs,x
        beq     @open
        dex
        bpl     @eligible
        jmp     refusal_close
@open: lda     #0
        sta     cg_cursor
        jsr     cg_puts
        .byte "TRACKED TRIP: TARGET / TIME RETAINED",0
route_post_draw:
        lda     #21
        jsr     fu_position
        ldx     #41
@clear:txa
        tay
        lda     #' '|$80
        jsr     t_update
        inx
        cpx     #80
        bcc     @clear
        lda     #41
        sta     CH
        ldx     cg_cursor
        lda     route_post_lo,x
        sta     gp1
        lda     route_post_hi,x
        sta     gp1+1
        jsr     cg_string
        lda     #22
        jsr     fu_position
        jsr     cg_more
        .byte "WALK:LAND SWIM:WATER HERE/NEXT STEP",0
        lda     #23
        jsr     fu_position
        jsr     cg_more
        .byte "ARROWS:CHOOSE RET:OPEN ESC:VIEW",0
@key:  jsr     cg_view_key
        cmp     #KC_ESC
        jeq     refusal_close
        cmp     #KC_RET
        beq     @take
        cmp     #KC_UP
        beq     @previous
        cmp     #KC_LEFT
        beq     @previous
        cmp     #KC_DOWN
        beq     @next
        cmp     #KC_RIGHT
        bne     @key
@next: inc     cg_cursor
        lda     cg_cursor
        and     #3
        sta     cg_cursor
        jmp     route_post_draw
@previous:
        dec     cg_cursor
        lda     cg_cursor
        and     #3
        sta     cg_cursor
        jmp     route_post_draw
@take: lda     cg_cursor
        beq     @review
        cmp     #3
        jeq     refusal_close
        eor     #3              ; 1 WALK -> verb_table 1; 2 SWIM -> 0
        sec
        sbc     #1
        jmp     flows_execute
@review:
        jmp     camp_trip_open
route_care_verbs:
        .byte V_USE,V_WEAR,V_DRINK,V_EAT,V_REST,V_WAIT,9,13,14,26,29,30,31,32,33
route_care_end:
route_post_lo: .byte <route_post_review,<route_post_walk,<route_post_swim,<route_post_back
route_post_hi: .byte >route_post_review,>route_post_walk,>route_post_swim,>route_post_back
route_post_review: .byte "> REVIEW / READJUST TRACKED CAP",0
route_post_walk: .byte "> WALK SAME CAP (CONFIRM DURATION)",0
route_post_swim: .byte "> SWIM SAME CAP (CONFIRM DURATION)",0
route_post_back: .byte "> BACK",0
