; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Original daily air cycle (T0C/S03) and hourly evaluation (T09/S08).
; All routines share the simulation image, so no intermediate DOS loads.
.segment "THERMAL"

weather_temperature:
        fld     s_t0
        jsr     AYINT
        lda     $A1
        sta     wc_mean
        lda     weather_day_level
        clc
        adc     M_BASE
        tay
        lda     #0
        jsr     GIVAYF
        fst     t2
        fop     FMULT, f_quarter
        jsr     AYINT
        lda     wc_mean
        sec
        sbc     $A1
        sta     wc_mean
        fld     t2
        fop     FMULT, f_0_2
        fop     FADD, f_15
        fst     t2
        ldy     M_LAT
        lda     #0
        cpy     #$80
        bcc     :+
        tya
        eor     #$FF
        tay
        iny
        lda     #0
:       jsr     GIVAYF
        fop     FMULT, f_0_15
        fop     FADD, t2
        jsr     AYINT
        lda     $A1
        sta     wc_range
        lsr
        sta     g0
        lda     wc_mean
        sec
        sbc     g0
        sta     wc_min
        lda     wc_mean
        clc
        adc     g0
        sta     wc_max
.if DRINK_FIDELITY
        jsr     sweat_update    ; $4C7A (src/camp.s)
.endif
        jsr     weather_cycle
        ; Pick the same half-open segments as $58B9.
@choose:
        fld     s_hour
        fop     FCOMP, wc_end
        cmp     #$FF
        bne     @night
        fop     FCOMP, wc_peak
        cmp     #$FF
        bne     @evening
        fop     FCOMP, wc_dawn
        cmp     #$FF
        beq     @night
        fld     wc_morning
        fst     t1
        fld     wc_peak
        fst     t2
        lda     wc_max
        jmp     @evaluate
@evening:
        fld     wc_evening
        fst     t1
        fld     wc_peak
        fst     t2
        lda     wc_max
        jmp     @evaluate
@night:
        fld     wc_night
        fst     t1
        fld     s_rise
        fop     FADD, wc_23
        fst     t2
        lda     wc_min
@evaluate:
        sta     wc_reference
        fld     t2
        fop     FMULT, t1
        jsr     AYINT
        sec
        lda     wc_reference
        sbc     $A1
        sta     wc_reference
        fld     s_hour
        fop     FCOMP, wc_dawn
        cmp     #$FF
        bne     :+
        fop     FADD, f_24
:       fop     FMULT, t1
        jsr     AYINT
        clc
        lda     wc_reference
        adc     $A1
        sta     airtemp
        rts
.export weather_evaluate := @choose

; Integer endpoints and floating slopes, matching native $5C88.
; Inputs wc_min/max/range, s_rise/set. Does not load another module.
weather_cycle:
        fld     f_one
        fop     FSUB, s_rise
        fst     wc_dawn
        fld     f_4
        fop     FSUB, s_set
        fop     FCOMP, wc_14
        cmp     #$FF
        bne     :+
        fld     wc_14
:       fst     wc_peak
        fld     s_set
        fop     FADD, f_2
        fst     wc_end
        sec
        lda     wc_max
        sbc     wc_min
        jsr     wc_signed
        fst     t1
        fld     wc_dawn
        fop     FSUB, wc_peak
        jsr     wc_divide
        fst     wc_morning
        lda     wc_range
        jsr     wc_signed
        fop     FMULT, wc_minus_two_thirds
        fst     t1
        fst     t3
        fld     wc_peak
        fop     FSUB, wc_end
        jsr     wc_divide
        fst     wc_evening
        sec
        lda     wc_min
        sbc     wc_max
        jsr     wc_signed
        fst     t1
        fld     t3
        fop     FSUB, t1         ; minimum - maximum - evening change
        fst     t1
        fld     s_rise
        fop     FADD, wc_23
        fst     t2
        fld     wc_end
        fop     FSUB, t2
        jsr     wc_divide
        fst     wc_night
        rts
wc_divide:
        lda     FAC
        beq     :+
        fop     FDIV, t1
:       rts
wc_signed:
        tay
        lda     #0
        cpy     #$80
        bcc     :+
        lda     #$FF
:       jmp     GIVAYF

wc_14: .byte $84,$60,0,0,0
wc_23: .byte $85,$38,0,0,0
; Exact coefficient stored by the original day module.
wc_minus_two_thirds: .byte $80,$AA,$AA,$AA,$AB
wc_mean: .byte 0
wc_min: .byte 0
wc_max: .byte 0
wc_range: .byte 0
wc_reference: .byte 0
wc_dawn: .res 5
wc_peak: .res 5
wc_end: .res 5
wc_morning: .res 5
wc_evening: .res 5
wc_night: .res 5

; Persistent Sierra weather state survives reloading WILDSIM after a view.
.segment "GDATA"
weather_seed: .byte $BA,$56,$F3,$03
weather_clock: .byte 0,0,0,0,0
weather_start: .byte $88,$67,$07,$5C,$88
weather_previous: .byte $88,$96,0,0,0
weather_duration: .word 125
weather_previous_duration: .word 100
weather_frequency: .byte $82,$63,$75,$17,$62
weather_cap: .word 360
weather_visibility: .byte 240
weather_day_level: .byte 0      ; altitude used when the native day cycle starts
weather_sky: .byte 0           ; clear, cloudy, rain, snow
weather_trend: .byte 2         ; native NO CHANGE=2, WORSE=3, BETTER=1
weather_inside_front: .byte 0
weather_short: .byte 0
weather_previous_short: .byte 0
.segment "THERMAL"

; Sierra monthly precipitation: 0.1*(2+29*(1+SIN((360*date+47)*rad))).
; The regional correction and multiplier for other regions remain separate.
weather_daily:
        lda     #21
        jsr     overlay_load
        jmp     module_weather_daily
; The preparation's storm frequency (src/prepare.s): in the raw SIM image,
; which NEOWILD.PRE patches through pr_patch_sim (ADVENTURE is LZ-packed).
.pushseg
.segment "GDATA"
wf_storm: .byte $81,0,0,0,0
.popseg
.segment "ADVENTURE"
module_weather_daily:
        fld     s_date
        fop     FMULT, wf_360
        fop     FADD, wf_47
        fop     FMULT, wf_rad
        jsr     FSIN
        fop     FADD, f_one
        fst     t1
        fld     wf_29
        fop     FMULT, t1
        fst     t1
        fld     f_2
        fop     FADD, t1
        fop     FMULT, wf_0_1
        fop     FMULT, wf_storm  ; storm frequency $4C52 (1.0; NEOWILD.PRE patches it)
        fop     FCOMP, wf_0_1
        cmp     #$FF
        bne     :+
        fld     wf_0_1
:       fst     weather_frequency
        rts

.segment "THERMAL"
weather_air_visibility:
        jsr     level_here
        clc
        adc     M_BASE
        tay
        lda     #0
        jsr     GIVAYF
        fst     t1
        ldy     weather_visibility
        lda     #0
        jsr     GIVAYF
        jsr     FSQR
        fop     FDIV, t1
        fop     FMULT, wf_0_16
        jsr     AYINT
        clc
        lda     airtemp
        adc     $A1
        sta     airtemp
        rts

; Original wind/front refresh uses accumulated time at the health cadence,
; after evaluating the air and felt temperatures with the preceding wind.
weather_step:
        jsr     weather_random
        fop     FMULT, f_4
        fop     FSUB, f_2
        fop     FADD, f_half
        jsr     AYINT
        sec
        lda     wind
        sbc     $A1
        tax
        lda     #0
        sbc     $A0
        bmi     @minimum
        cpx     #2
        bcc     @minimum
        cpx     M_WIND
        bcc     @wind
        ldx     M_WIND
        jmp     @wind
@minimum:
        ldx     #2
@wind:  stx     wind
        fld     s_step
        fop     FMULT, f_quarter
        fop     FADD, weather_clock
        fst     weather_clock
        jsr     weather_front
        jsr     weather_conditions
        ; Wetness is selected now for this health update, never dried slowly.
weather_wet:
        lda     wet_mode
        cmp     #2
        beq     @done
        lda     #0
        ldx     shelter_inside
        bne     @wet
        ldx     it_place+12      ; worn raincoat protects from precipitation
        cpx     #1
        beq     @wet
        ldx     weather_sky
        cpx     #2
        bcc     @wet
        lda     #1
@wet:   sta     wet_mode
@done:  rts

weather_front:
@again: fld     weather_clock
        fop     FCOMP, weather_start
        cmp     #$FF
        bne     @during
        lda     #0
        sta     weather_inside_front
        fop     FSUB, weather_start
        fop     FCOMP, wf_90
        ldx     #2
        cmp     #$FF
        bne     :+
        inx
:       stx     weather_trend
        rts
@during:
        lda     weather_duration+1
        ldy     weather_duration
        jsr     GIVAYF
        fop     FADD, weather_start
        fop     FCOMP, weather_clock
        cmp     #$FF
        beq     @next
        lda     #1
        sta     weather_inside_front
        fld     weather_start
        fop     FSUB, weather_clock
        fst     t1
        lda     weather_duration+1
        ldy     weather_duration
        jsr     GIVAYF
        fop     FDIV, t1
        fop     FMULT, wf_3
        fop     FADD, wf_0_999
        jsr     AYINT
        lda     #4
        sec
        sbc     $A1
        sta     weather_trend
        rts
@next:  fld     weather_start
        fst     weather_previous
        lda     weather_duration
        sta     weather_previous_duration
        lda     weather_duration+1
        sta     weather_previous_duration+1
        lda     weather_short
        sta     weather_previous_short
        jsr     weather_random
        fop     FMULT, wf_180
        jsr     AYINT
        clc
        lda     $A1
        adc     #30
        sta     weather_duration
        lda     $A0
        adc     #0
        sta     weather_duration+1
        lda     #0
        ldx     weather_duration
        cpx     #120
        bcs     :+
        lda     #1
:       sta     weather_short
        jsr     weather_random
        fop     FMULT, wf_20000
        fst     t1
        fld     weather_frequency
        fop     FDIV, t1
        fop     FCOMP, wf_40
        cmp     #$FF
        bne     :+
        fld     wf_40
:       fst     t1
        lda     weather_previous_duration+1
        ldy     weather_previous_duration
        jsr     GIVAYF
        fop     FADD, t1
        fop     FADD, weather_previous
        fst     weather_start
        jmp     @again

weather_conditions:
        lda     #240
        sta     weather_visibility
        fld     weather_clock
        fop     FSUB, weather_start
        fop     FMULT, wf_2_4
        fst     t1
        lda     weather_previous_duration+1
        ldy     weather_previous_duration
        jsr     GIVAYF
        fop     FADD, weather_previous
        fop     FSUB, weather_clock
        fop     FMULT, wf_2_4
        fop     FCOMP, wf_120
        cmp     #1
        beq     @cap
        ldx     weather_previous_short
        bne     @cap
        jsr     AYINT
        lda     $A1
        sta     weather_visibility
@cap:   fld     t1
        fop     FCOMP, wf_360
        cmp     #1
        bne     :+
        ldx     #1
        ldy     #104             ; 360 minutes
        jmp     @save_cap
:
        fop     FCOMP, wf_120
        cmp     #1
        bne     :+
        ldx     #0
        ldy     #120
        jmp     @save_cap
:
        lda     weather_short
        bne     @thirty
        lda     #7
        pha
        lda     weather_inside_front
        bne     :+
        pla
        jsr     AYINT
        lda     $A1
        pha
:       pla
        cmp     weather_visibility
        bcs     @thirty
        sta     weather_visibility
@thirty:
        ldx     #0
        ldy     #30
@save_cap:
        stx     weather_cap+1
        sty     weather_cap
        lda     weather_visibility
        cmp     #24
        bcs     :+
        lda     #24
        sta     weather_visibility
:       ldx     #0
        lda     weather_inside_front
        bne     @precipitation
        lda     weather_visibility
        cmp     #240
        bcs     @sky
        inx
        bne     @sky
@precipitation:
        ldx     #3
        lda     airtemp
        bmi     @sky
        cmp     #33              ; at the freezing level itself: snow
        bcc     @sky
        dex
@sky:   stx     weather_sky
        rts

; Authored Lehmer generator: 13 modular doublings, then S / modulus.
; All integers are below 2^26, exactly representable by the ROM floats.
weather_random:
        lda     #13
        sta     wf_iterations
@double:
        asl     weather_seed
        rol     weather_seed+1
        rol     weather_seed+2
        rol     weather_seed+3
        ldx     #3
@compare:
        lda     weather_seed,x
        cmp     wf_modulus,x
        bcc     @next
        bne     @subtract
        dex
        bpl     @compare
@subtract:
        sec
        ldx     #0
        ldy     #4
@sub:   lda     weather_seed,x
        sbc     wf_modulus,x
        sta     weather_seed,x
        inx
        dey
        bne     @sub             ; index/count updates preserve the borrow
@next:  dec     wf_iterations
        bne     @double
        lda     #0
        sta     FAC
        fst     wf_integer
        lda     #3
        sta     wf_byte
@convert:
        fld     wf_integer
        fop     FMULT, wf_256
        fst     wf_integer
        ldx     wf_byte
        ldy     weather_seed,x
        lda     #0
        jsr     GIVAYF
        fop     FADD, wf_integer
        fst     wf_integer
        dec     wf_byte
        bpl     @convert
        fld     wf_modulus_float
        fop     FDIV, wf_integer
        rts

wf_modulus: .byte $9B,$DB,$FF,$03
wf_modulus_float: .byte $9A,$7F,$F6,$E6,$C0 ; 67099547
wf_256: .byte $89,0,0,0,0
wf_360: .byte $89,$34,0,0,0
wf_47: .byte $86,$3C,0,0,0
wf_rad: .byte $7B,$0E,$FA,$35,$12 ; native day coefficient
wf_29: .byte $85,$68,0,0,0
wf_0_1: .byte $7D,$4C,$CC,$CC,$CD
wf_0_16: .byte $7E,$23,$D7,$0A,$3D
wf_3: .byte $82,$40,0,0,0
wf_0_999: .byte $80,$7F,$BE,$76,$CA ; native literal, one bit above Python .999
wf_180: .byte $88,$34,0,0,0
wf_20000: .byte $8F,$1C,$40,0,0
wf_40: .byte $86,$20,0,0,0
wf_90: .byte $87,$34,0,0,0
wf_120: .byte $87,$70,0,0,0
wf_2_4: .byte $82,$19,$99,$99,$9A
wf_iterations: .byte 0
wf_byte: .byte 0
wf_integer: .res 5
