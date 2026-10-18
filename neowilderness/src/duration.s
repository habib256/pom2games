; UI-only minute selector with separate travel, rest and wait memories. Explicit typed arguments
; keep the native parser; accepting here supplies its ordinary MIN unit.
.segment "TRIPUI"
duration_select:
        lda     #1
        sta     input_mode
        lda     duration_pending
        bne     @seeded
        lda     dep_mask
        bpl     @seeded
        and     #7
        tax
        lda     duration_guide_lo,x
        sta     duration_proposal
        lda     duration_guide_hi,x
        sta     duration_proposal+1
        lda     #1
        sta     duration_pending
        lda     #0
        sta     dep_mask
@seeded:
        lda     duration_pending
        sta     duration_is_proposal
        jsr     duration_memory
        stx     duration_slot
        ldy     #1
@copy:  lda     duration_last,x
        sta     input_value,y
        lda     duration_pending
        beq     :+
        lda     duration_proposal,y
        sta     input_value,y
:       dex
        dey
        bpl     @copy
        lda     #0
        sta     duration_pending
@draw:  lda     input_value
        sta     msgnum
        lda     input_value+1
        sta     msgnum+1
        lda     #<duration_prompt
        ldx     #>duration_prompt
        jsr     message
@key:   jsr     wait_key
        cmp     #KC_ESC
        jeq     @cancel
        cmp     #KC_RET
        jeq     @accept
        cmp     #KC_UP
        jeq     @more_fast
        cmp     #KC_DOWN
        jeq     @less_fast
        cmp     #KC_RIGHT
        jeq     @more
        cmp     #KC_LEFT
        jeq     @less
        cmp     #'0'
        bcc     @typed_check
        cmp     #'9'+1
        bcc     @typed
@typed_check:
        and     #$DF
        cmp     #'T'
        bne     @key
@typed: sta     input_value
        lda     #13
        jsr     overlay_load
        jmp     input_duration_typed
@cancel:
        jsr     camp_cancel_preparation
        lda     #0
        sta     msgnum
        sta     msgnum+1
        lda     #<duration_cancelled
        ldx     #>duration_cancelled
        jsr     message
        sec
        rts
@accept:
        lda     duration_is_proposal
        bne     @supplied
        ldx     duration_slot
        ldy     #1
@save:  lda     input_value,y
        sta     duration_last,x
        sta     msgnum,y
        dex
        dey
        bpl     @save
@supplied:
        lda     duration_is_proposal
        beq     @unit
        lda     verb
        cmp     #V_REST
        bne     @unit
        lda     #$84
        sta     dep_running
        lda     journey_encounters
        sta     dep_cursor
@unit:  lda     #2
        sta     input_unit
        lda     #0
        sta     shown
        clc
        rts
@more_fast:
        ldx     #0
@next_preset:
        lda     input_value
        cmp     duration_quick_lo,x
        lda     input_value+1
        sbc     duration_quick_hi,x
        bcc     @preset
        inx
        cpx     #duration_quick_count
        bcc     @next_preset
        dex
@preset:
        lda     duration_quick_lo,x
        sta     input_value
        lda     duration_quick_hi,x
        sta     input_value+1
        jmp     @changed
@more:  ldx     #1
@increase:
        lda     input_value
        cmp     #<15300
        lda     input_value+1
        sbc     #>15300
        bcs     @changed
        inc     input_value
        bne     :+
        inc     input_value+1
:       dex
        bne     @increase
        beq     @changed
@less_fast:
        ldx     #duration_quick_count-1
@previous_preset:
        lda     duration_quick_lo,x
        cmp     input_value
        lda     duration_quick_hi,x
        sbc     input_value+1
        bcc     @preset
        dex
        bpl     @previous_preset
        inx
        beq     @preset
@less:  ldx     #1
@decrease:
        lda     input_value+1
        bne     :+
        lda     input_value
        cmp     #2
        bcc     @changed
:       lda     input_value
        bne     :+
        dec     input_value+1
:       dec     input_value
        dex
        bne     @decrease
@changed:
        jmp     @draw

; Memory index is the high byte of each contiguous UI-only word.
duration_memory:
        ldx     #1
        lda     verb
        cmp     #V_WAIT
        bne     :+
        ldx     #5
        rts
:       cmp     #V_REST
        beq     @rest
        cmp     #V_CAMP
        bne     @done
@rest:  ldx     #3
@done:  rts
duration_slot: .byte 1
duration_is_proposal: .byte 0
duration_quick_lo: .byte <1,<5,<10,<20,<30,<60,<120,<240,<480,<960,<1440,<2880,<5760,<10080,<15300
duration_quick_hi: .byte >1,>5,>10,>20,>30,>60,>120,>240,>480,>960,>1440,>2880,>5760,>10080,>15300
duration_quick_count = *-duration_quick_hi

duration_prompt:
        .byte "DURATION # MIN|UP/DOWN QUICK  LEFT/RIGHT 1 MIN|RETURN CONFIRM  ESC BACK  TYPE HOURS OR MIN",0

duration_cancelled: .byte "ACTION CANCELLED.",0

; Legacy guide recommendations retain their exact native minute values.
duration_guide_lo: .byte <10,<20,<30,<60,<120,<240,<480,<60
duration_guide_hi: .byte >10,>20,>30,>60,>120,>240,>480,>60
