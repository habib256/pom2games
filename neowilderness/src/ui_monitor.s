; Interface-only thresholds already used by STATUS: 6/12h, 20% health
; bands and factors under .95. No damage, resources or clock writes.
.segment "THERMAL"
ui_monitor:
        lda     #1
        sta     ui_dirty
        fld     s_eat
        jsr     ui_gauge_index
        sta     ui_now
        fld     s_drink
        jsr     ui_gauge_index
        sta     ui_now+1
        fld     f_hmax
        fop     FDIV, s_health
        fop     FCOMP, f_third
        cmp     #1
        beq     @healthy
        lda     #1
        bne     @weak_store
@healthy:
        lda     #0
@weak_store:
        sta     weak_health
        fop     FMULT, f_5
        jsr     AYINT
        lda     $A1
        cmp     #5
        bcc     :+
        lda     #4
:       eor     #255
        clc
        adc     #5
        sta     ui_now+2
        lda     #0
        sta     ui_now+3
        fld     s_therm_factor
        fop     FCOMP, ui_factor95
        cmp     #255
        bne     @wet
        fld     s_body
        fop     FCOMP, f_body
        ldx     #1
        cmp     #255
        beq     :+
        inx
:       stx     ui_now+3
@wet:   lda     #0
        ldx     wet_mode
        cpx     #2
        bne     :+
        lda     #1
:       sta     ui_now+4
        ; Preserve the original condition appearance threshold as a mask.
        lda     #0
        sta     ui_now+5
        sta     ui_class
@condition:
        ldx     ui_class
        lda     cdef_lo,x
        ldy     cdef_hi,x
        jsr     MOVFM
        fst     t1
        ldx     ui_class
        lda     ctol_lo,x
        ldy     ctol_hi,x
        jsr     MOVFM
        fop     FMULT, f_0_2236
        fop     FCOMP, t1
        cmp     #255
        bne     :+
        ldx     ui_class
        lda     ui_condition_bits,x
        ora     ui_now+5
        sta     ui_now+5
:       inc     ui_class
        lda     ui_class
        cmp     #3
        bcc     @condition
        ldx     #5
@compare:
        ; Switching from hot to cold remains a warning, never a recovery.
        cpx     #3
        bne     @condition_compare
        lda     ui_now,x
        beq     @normal
        cmp     ui_previous,x
        beq     @next
        bne     @warning
@condition_compare:
        cpx     #5
        bne     @normal
        lda     ui_previous+5
        eor     #255
        and     ui_now+5
        beq     @normal
        lda     ui_now+5
@warning:
        sec
        bcs     @record
@normal:
        lda     ui_now,x
        cmp     ui_previous,x
        beq     @next
@record: sta    ui_previous,x
        lda     ui_initialized
        beq     @next
        bcc     @recovery
        ; Retain the highest-priority warning until the result is shown.
        txa
        clc
        adc     #1
        sta     ui_changed
        lda     ui_pending
        beq     @event
        cmp     #9
        bcs     @event
        cmp     ui_changed
        bcs     @next
        bcc     @event
@recovery:
        txa
        clc
        adc     #9
        sta     ui_changed
        lda     ui_pending
        beq     @event
        cmp     #9
        bcs     @event
        adc     #8              ; carry clear: pending warning's recovery ID
        cmp     ui_changed
        bne     @next           ; keep warnings from other classes
@event: lda     ui_changed
        sta     ui_pending
        inc     ui_events
@next:  dex
        bpl     @compare
        lda     #1
        sta     ui_initialized
        rts
ui_gauge_index:
        fop     FCOMP, f_12
        cmp     #1
        beq     @very
        fop     FCOMP, f_6
        cmp     #1
        beq     @some
        lda     #0
        rts
@some:  lda     #1
        rts
@very:  lda     #2
        rts
ui_factor95: .byte $80,$73,$33,$33,$33
ui_condition_bits: .byte 1,2,4
ui_now: .res 6
ui_class: .byte 0
ui_changed: .byte 0
