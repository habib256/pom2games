; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Clothing, wind chill and immersion; see docs/logic/survival.md.
; One disk overlay, no calls into another overlay. Scratch floats t1..t5
; and th_parts at $95A0 never survive a module call.
.segment "SCRATCH"
th_parts: .res 25
.segment "GDATA"
; Persistent cache key: nineteen WORN bits, wet/immersed mode and validity.
; The cached result is the existing resident s_insul, never overlay RAM.
clothing_cache: .res 3
clothing_cache_wet: .byte 0
clothing_cache_valid: .byte 0
.segment "THERMAL"

module_thermal:
        jsr     camp_light              ; $0D5D at each health step (src/camp.s)
        jsr     thermal_clothes
        jsr     thermal_rate
        jsr     thermal_integrate
        jmp     thermal_condition

; Deterministic dry/wet layers: parallel losses R*L/(R+L), rounded after each
; garment, in item order. Bare losses are our reconstruction (500 for
; torso/legs/feet/hands, 200 for head), same in both modes, not original presets.
thermal_clothes:
        lda     #0
        sta     g0
        sta     g1
        sta     g2
        ldx     #18
@key:   lda     it_place+2,x
        cmp     #1
        beq     :+
        clc
:       rol     g0
        rol     g1
        rol     g2
        dex
        bpl     @key
        lda     clothing_cache_valid
        beq     @compute
        lda     wet_mode
        cmp     clothing_cache_wet
        bne     @compute
        ldx     #2
@check: lda     g0,x
        cmp     clothing_cache,x
        bne     @compute
        dex
        bpl     @check
        fld     s_insul
        rts
@compute:
        lda     MAP+37
        beq     @legacy
        jsr     native_clothes_update
        jsr     native_clothes_index
        jmp     @valid
@legacy:
        ldx     #2
@save:  lda     g0,x
        sta     clothing_cache,x
        dex
        bpl     @save
        lda     wet_mode
        sta     clothing_cache_wet
        jsr     thermal_clothes_compute
@valid:
        lda     wet_mode
        sta     clothing_cache_wet
        lda     #1
        sta     clothing_cache_valid
        rts

thermal_clothes_compute:
        lda     #0
        sta     g0
@bare:  ldx     g0
        lda     th_offsets,x
        tax
        ldy     #0
@copy:  lda     th_500,y
        sta     th_parts,x
        inx
        iny
        cpy     #5
        bcc     @copy
        inc     g0
        lda     g0
        cmp     #5
        bcc     @bare
        fld     th_200
        fst     th_parts+5
        lda     #2
        sta     g0
@item:  ldx     g0
        lda     it_place,x
        cmp     #1
        beq     :+
        jmp     @next
:
        ldy     th_loss_lo-2,x
        lda     th_loss_hi-2,x
        ldx     wet_mode
        beq     :+
        ldx     g0
        ldy     th_wet_lo-2,x
        lda     th_wet_hi-2,x
:
        jsr     GIVAYF
        lda     FAC
        beq     @next
        fst     t1                      ; garment loss
        ldx     g0
        lda     it_kcal,x              ; body part 2..6
        tax
        lda     th_offsets-2,x
        sta     g1
        clc
        adc     #<th_parts
        ldy     #>th_parts
        jsr     MOVFM
        fst     t2                      ; previous loss
        fop     FADD, t1
        fst     t3
        fld     t1
        fop     FMULT, t2
        fst     t2
        fld     t3
        fop     FDIV, t2
        fop     FADD, f_half
        jsr     AYINT
        lda     $A0
        ldy     $A1
        jsr     GIVAYF
        lda     g1
        clc
        adc     #<th_parts
        tax
        ldy     #>th_parts
        jsr     MOVMF
@next:  inc     g0
        lda     g0
        cmp     #21
        bcs     :+
        jmp     @item
:
        fld     f_zero
        fst     t1
        lda     #0
        sta     g0
@area:  ldx     g0
        lda     th_offsets,x
        clc
        adc     #<th_parts
        ldy     #>th_parts
        jsr     MOVFM
        fst     t2
        lda     g0
        asl
        tax
        lda     th_area_hi,x
        ldy     th_area_lo,x
        jsr     GIVAYF
        fop     FMULT, t2
        fop     FADD, t1
        fst     t1
        inc     g0
        lda     g0
        cmp     #5
        bcc     @area
        fld     th_surface
        fop     FDIV, t1                ; weighted average loss Q
        ldx     wet_mode
        cpx     #2
        bne     :+
        fop     FMULT, f_2              ; immersion doubles wet surface losses
:
        fst     t1
        fld     th_500
        ldx     wet_mode
        beq     :+
        fld     th_2000                ; original initial global wet loss
:       ldx     wet_mode
        cpx     #2
        bne     :+
        fop     FMULT, f_2              ; immersion also doubles global loss R0
:       fst     t3
        fop     FMULT, t1
        fst     t2
        fld     t1
        fop     FADD, t3
        fop     FDIV, t2                ; R0 Q/(R0+Q)
        lda     MAP+37
        beq     :+
        fop     FMULT, th_native_composition
:
        fop     FADD, f_half
        jsr     AYINT
        lda     $A0
        ldy     $A1
        cpy     #10
        bcs     :+
        cmp     #0
        bne     :+
        ldy     #10
:       jsr     GIVAYF
        fst     s_insul
        rts
.export thermal_clothes_weighted := @area

native_clothes_update:
        lda     #21
        jsr     overlay_load
        jmp     module_native_clothes_update
native_clothes_index:
        lda     #21
        jsr     overlay_load
        jmp     module_native_clothes_index
.segment "ADVENTURE"
module_native_clothes_index:
        lda     #0
        sta     g0
@part: lda     g0
        asl
        clc
        adc     #42
        ldx     wet_mode
        beq     :+
        adc     #12
:       tax
        ldy     MAP,x
        lda     MAP+1,x
        jsr     GIVAYF
        ldx     g0
        lda     th_offsets,x
        clc
        adc     #<th_parts
        tax
        ldy     #>th_parts
        jsr     MOVMF
        inc     g0
        lda     g0
        cmp     #5
        bne     @part
        fld     f_zero
        fst     t1
        lda     #0
        sta     g0
        jmp     thermal_clothes_weighted
.segment "THERMAL"
.pushseg
.segment "GDATA"
th_native_composition: .byte $80,$7C,$E5,$9F,$CE ; 1 - 2/165
.popseg

; thermal_wind -- original m098 $59E5: T-floor(sqrt(mph)/12*(100-T)).
; Keep both subtraction bytes: the original low-byte result can wrap a
; very cold climate to a positive temperature. Uses t1 and the ROM's INT.
thermal_wind:
        ldy     airtemp
        lda     #0
        cpy     #$80
        bcc     :+
        lda     #$FF
:       jsr     GIVAYF
        fop     FSUB, f_100
        fst     t1                      ; 100 - T
        ldy     wind
        lda     #0
        jsr     GIVAYF
        jsr     FSQR
        fop     FMULT, th_inv12
        fop     FMULT, t1
        jsr     AYINT
        lda     airtemp
        sec
        sbc     $A1
        sta     felt_temp
        lda     #0
        ldy     airtemp
        bpl     :+
        lda     #$FF
:       sbc     $A0
        sta     felt_temp+1
        rts

thermal_rate:
        lda     #0
        sta     thermal_mode
        sta     thermal_zone
        fld     f_body
        fop     FSUB, s_body            ; T - 98.6
        fst     t2
        fld     f_rest_rate
        fop     FDIV, s_metabolic       ; M/1.65 (ROM division is memory/FAC)
        jsr     FSQR
        fst     t1                      ; r
        ldy     felt_temp
        lda     felt_temp+1
        jsr     GIVAYF
        ldx     wet_mode
        cpx     #2
        bne     @air
        jsr     level_here
        clc
        adc     M_BASE
        tay
        lda     #0
        adc     #0                     ; keep carry for high base altitudes
        jsr     GIVAYF
        fop     FMULT, th_water_k
        jsr     AYINT
        lda     #70
        sec
        sbc     $A1
        tay
        lda     #0
        sbc     $A0
        jsr     GIVAYF                 ; 70-floor(.3*altitude/100), signed
        jmp     @effective
@fire:  ; T0B/S02 $5986: near a fire (USE FIRE) the byte $EE gains 25 F and
        ; becomes 127 when bit 7 is set, as below -25 F (re_thermal_probe.py).
        lda     felt_temp
        ldx     shelter_inside
        beq     :+
        lda     #35             ; the igloo (lot 3, shelter_inside 2): 35 F
        cpx     #2
        beq     :+
        lda     airtemp
        clc
        adc     #15
:       clc
        adc     #25
        bpl     :+
        lda     #127
:       tay
        lda     #0
        jsr     GIVAYF
        jmp     @effective
@air:   lda     fire_near
        bne     @fire
        lda     shelter_inside
        beq     @effective
        ldy     #35                     ; the igloo (lot 3, shelter_inside 2):
        cmp     #2                      ; 35 F (T0B/S02, B2 of the igloo)
        beq     @igloo
        ldy     airtemp
        lda     #0
        cpy     #128
        bcc     :+
        lda     #$FF
:       jsr     GIVAYF
        fop     FADD, th_shelter15      ; original found shelter: ambient + 15 F
        jmp     @effective
@igloo: lda     #0
        jsr     GIVAYF
@effective:
        fst     t4                      ; signed wind-adjusted air or water temperature
        jsr     clamp0
        fst     t3
        fld     th_10
        fop     FDIV, t3
        fst     t3
        fop     FMULT, t3
        fop     FMULT, t3
        fop     FADD, th_20
        fop     FMULT, t1
        fop     FMULT, th_inv6          ; B = r (20 + max(E,0)^3/1000)/6
        fop     FCOMP, s_insul
        cmp     #1
        beq     @hot
        fop     FMULT, th_9
        fop     FCOMP, s_insul
        cmp     #$FF
        beq     @cold
        ; Neutral recovery uses 0.1*|T-normal| and 0.017*minutes.
        fld     t2
        fop     FMULT, th_0_1
        jsr     negate
        fst     s_therm_rate
        rts
@hot:   lda     #1
        sta     thermal_zone
        ldx     wet_mode
        bne     :+
        sta     thermal_mode            ; original suppresses sweating while wet
:
        fld     s_insul
        jsr     FSQR
        fop     FDIV, th_a
        fop     FMULT, th_55
        fop     FMULT, t1
        fst     t3
        fld     t4
        jsr     clamp0
        fop     FMULT, t3
        fop     FSUB, f_0_2
        jsr     thermal_abs
        fst     s_therm_rate
        rts
@cold:  lda     #2
        sta     thermal_zone
        ldy     body_weight
        lda     body_weight+1
        jsr     GIVAYF
        fop     FMULT, f_shiver_k
        fop     FCOMP, s_metabolic
        cmp     #$FF
        beq     :+
        lda     #2
        sta     thermal_mode
:       fld     t4
        fop     FSUB, th_80
        jsr     thermal_abs
        fst     t3
        fld     s_insul
        jsr     FSQR
        fop     FMULT, th_a
        fop     FMULT, t3
        fst     t3
        ldy     wet_mode
        lda     #0
        jsr     GIVAYF
        fop     FMULT, f_half
        fop     FADD, f_one
        fop     FMULT, t3              ; original cold multiplier 1+.5*wet
        jsr     negate
        fst     s_therm_rate
        rts

; Independently callable for comparisons against original isolated branches.
; s_step is minutes; s_therm_rate is signed F/hour. Zone 0 is neutral.
thermal_integrate:
        fld     f_body
        fop     FSUB, s_body
        fst     t2
        lda     #0
        sta     g1                      ; recovery flag
        lda     thermal_zone
        bne     @drift
        inc     g1
        fld     s_therm_rate
        jsr     thermal_abs
        fst     t1                      ; unbounded rate drives neutral step
        lda     FAC
        bne     :+
        rts
:       fop     FCOMP, f_dead            ; original exposes at least .3 rate
        cmp     #$FF
        bne     :+
        fld     f_dead
        lda     t2+1
        bmi     @rate_positive
        jsr     negate
@rate_positive:
        fst     s_therm_rate
:       fld     t1
        fop     FMULT, s_step
        fop     FMULT, th_0_017
        jmp     @apply
@drift: fld     s_therm_rate
        fop     FMULT, t2
        lda     FACSGN
        bpl     :+
        inc     g1
:       fld     s_therm_rate
        jsr     thermal_abs
        ldx     g1
        bne     @step
        fop     FCOMP, f_dead
        cmp     #$FF
        beq     @done
@step:  fop     FMULT, s_step
        fop     FMULT, f_inv60
@apply: lda     s_therm_rate+1
        bpl     :+
        jsr     negate
:       fop     FADD, s_body
        ldx     g1
        beq     @store
        fop     FCOMP, f_body
        tax
        lda     t2+1
        bmi     @from_cold
        cpx     #$FF
        bne     @store
        beq     @normal
@from_cold:
        cpx     #1
        bne     @store
@normal:
        fld     f_body
@store: fst     s_body
@done:  rts

; Our simplified condition activation: apply original untreated quadratic
; losses whenever T deviates; treatments and original activation gates await
; the injury/weather model. Factor is clamped at zero, as other conditions.
thermal_condition:
        fld     f_body
        fop     FSUB, s_body
        fst     t1
        lda     FACSGN
        pha
        fop     FMULT, t1
        pla
        bmi     @hypo
        fop     FMULT, th_0_027
        jmp     @factor
@hypo:  fop     FMULT, th_0_012
@factor:
        fop     FSUB, f_one
        jsr     clamp0
        fst     s_therm_factor
        rts

thermal_abs:
        lda     #0
        sta     FACSGN
        rts

th_shelter15 = f_15            ; resident 15 F, ordinary found shelter

.segment "RODATA"
th_offsets: .byte 0, 5, 10, 15, 20
; Original body surface*coefficient: torso, head, legs, feet, hands.
th_area_lo: .word 2638, 2100, 790, 255, 260
th_area_hi = th_area_lo+1
; item IDs 2..20; tent, pad and ground cover do not count as worn layers.
th_loss_lo: .byte 20,60,120,100,120,60,60,0,0,0,<500,250,200,150,200,<350,200,200,150
th_loss_hi: .byte 0,0,0,0,0,0,0,0,0,0,>500,0,0,0,0,>350,0,0,0
; Original W11 item losses, excluding tent, pad and ground cover.
th_wet_lo: .byte 60,80,160,150,160,80,80,0,0,0,<600,<500,<2000,<1500,<2000,<600,<2000,<2000,200
th_wet_hi: .byte 0,0,0,0,0,0,0,0,0,0,>600,>500,>2000,>1500,>2000,>600,>2000,>2000,0
