; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Clock/event accounting from T09/S05, food T12/S00, REST T15/S0B.
; ENV overlay: scratch t1..t3; t4/t5 belong to spend and are preserved.
.segment "ENVIRON"

module_survival_clock:
        lda     act
        cmp     #1
        beq     :+
        jsr     fauna_age       ; travel ages animals in module_fauna instead
:
        clc
        lda     health_minutes
        adc     scene_minutes
        sta     health_minutes
        bcc     :+
        inc     health_minutes+1
:       lda     #0
        sta     health_due
        lda     health_minutes+1
        bne     @update
        lda     health_minutes
        cmp     health_period
        bcs     @update
        rts
@update:
        inc     health_due
        lda     health_minutes+1
        ldy     health_minutes
        jsr     GIVAYF
        fop     FMULT, f_inv60
        fst     t1              ; original $FB: accumulated interval, not dt
        lda     #0
        sta     g0
@counter:
        ldx     g0
        lda     sv_last_lo,x
        ldy     sv_last_hi,x
        jsr     MOVFM
        fop     FSUB, s_elap
        fop     FCOMP, f_half
        cmp     #$FF
        bne     :+
        fld     f_half
:       ldx     g0
        lda     sv_since_lo,x
        pha
        lda     sv_since_hi,x
        tay
        pla
        tax
        jsr     MOVMF
        ldx     g0
        lda     cdef_lo,x
        ldy     cdef_hi,x
        jsr     MOVFM
        fop     FADD, t1
        ldx     g0
        lda     cdef_lo,x
        pha
        lda     cdef_hi,x
        tay
        pla
        tax
        jsr     MOVMF
        inc     g0
        lda     g0
        cmp     #3
        bcc     @counter
        rts

module_rest_prepare:
        lda     #30
        sta     health_period
        lda     verb
        cmp     #V_WAIT
        beq     @done
        lda     minutes+1
        ldy     minutes
        jsr     GIVAYF
        fst     t1
        fop     FMULT, sv_0_05
        fop     FSUB, s_defr     ; original credits requested rest before clock
        fst     s_defr
        fld     t1
        fop     FMULT, sv_0_017
        jsr     AYINT
        lda     $A0
        ldy     $A1
        jsr     GIVAYF
        fop     FADD, s_elap
        fst     s_last+10
        fld     f_half
        fst     s_rest
@done:  rts

module_meal_prepare:
        ; t1 = kcal eaten, already included in s_eaten; msgnum = oz.
        fld     t1
        fop     FMULT, sv_0_8
        fst     t1
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FDIV, t1        ; original .8 * kcal / weight
        fop     FSUB, s_deff
        fst     s_deff
        ldx     noun
        lda     sv_food_water-23,x
        sta     g0
        jsr     oz_times
        fop     FMULT, sv_0_007
        fop     FMULT, f_oz_hour
        fop     FSUB, s_defw
        fst     s_defw
        fld     sv_meal_stamp   ; original planned 16 minutes * .017
        fop     FADD, s_elap
        fst     s_last+5
        fld     f_zero          ; m095 raises this to .5 only when counters refresh
        fst     s_eat
        rts

; T0B/S0D converts each condition to an integer percent before multiplying.
; This includes the truncation to 99% for a small positive deficit.
module_health:
        jsr     injury_health
        fld     s_injury_factor
        fst     t1
        lda     #0
        sta     g0
@condition:
        ldx     g0
        lda     cdef_lo,x
        ldy     cdef_hi,x
        jsr     MOVFM
        jsr     clamp0
        ldx     g0
        lda     cdef_lo,x
        pha
        lda     cdef_hi,x
        tay
        pla
        tax
        jsr     MOVMF
        lda     FAC
        beq     @next          ; nonpositive: clear deficit, no health loss
        fst     t2
        ldx     g0
        lda     ctol_lo,x
        ldy     ctol_hi,x
        jsr     MOVFM
        fop     FDIV, t2
        fst     t2
        fop     FMULT, t2
        fop     FSUB, f_one
        jsr     clamp0
        jsr     $EA39          ; native multiplies by 10 twice, then INT
        jsr     $EA39
        jsr     AYINT
        lda     $A0
        ldy     $A1
        jsr     GIVAYF
        fst     t2
        fld     f_100
        fop     FDIV, t2
        fop     FMULT, t1
        fst     t1
@next:  inc     g0
        lda     g0
        cmp     #3
        bcs     :+
        jmp     @condition
:
        fld     f_hmax
        fop     FMULT, t1
        fop     FMULT, s_therm_factor
        fst     s_health
        fop     FCOMP, f_dead
        cmp     #$FF
        bne     :+
        lda     #1
        sta     dead
:       lda     #0
        sta     health_minutes
        sta     health_minutes+1
        fld     s_metabolic
        lda     thermal_mode
        cmp     #2
        bne     @period
        fst     t2
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FMULT, f_shiver_k
        fop     FADD, t2
@period:
        fop     FDIV, sv_495    ; 300 * base / effective metabolic rate
        jsr     AYINT
        lda     $A0
        bne     @max
        lda     $A1
        cmp     #240
        bcc     :+
@max:   lda     #240
:       cmp     #29
        bcs     :+
        lda     #29
:       ldx     weather_cap+1
        bne     :+
        cmp     weather_cap
        bcc     :+
        lda     weather_cap
:       jsr     module_medical_cap
        sta     health_period
        rts

sv_last_lo: .byte <s_last, <(s_last+5), <(s_last+10)
sv_last_hi: .byte >s_last, >(s_last+5), >(s_last+10)
sv_since_lo: .byte <s_drink, <s_eat, <s_rest
sv_since_hi: .byte >s_drink, >s_eat, >s_rest
sv_food_water: .byte 5,0,25,0,0,20,0,60,0,20,50,20,80,60,90
sv_0_05: .byte $7C,$4C,$CC,$CC,$CD ; 0.05
sv_0_017: .byte $7B,$0B,$43,$95,$81 ; 0.017
sv_0_8: .byte $80,$4C,$CC,$CC,$CD ; 0.8
sv_0_007: .byte $79,$65,$60,$41,$89 ; 0.007
sv_meal_stamp: .byte $7F,$0B,$43,$95,$81 ; 0.272
sv_495: .byte $89,$77,$80,$00,$00 ; 495.0
