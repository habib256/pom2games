; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Exposure counters and disease onset from Journey T0B/S07. The renderer's
; snow line supplies snow cover until the native terrain/day selectors port.
.segment "GDATA"
exposure_counter: .word 0,0,0,0 ; salt loss, sunburn, snowblindness, frostbite
.segment "HAZARDS"
module_hazards:
        lda     s_step
        bne     :+
        rts
:
        ; Native $4A4A counters use integer increments per health update.
        fld     s_step
        jsr     AYINT
        lda     $A1
        sta     hz_minutes
        lda     $A0
        sta     hz_minutes+1
        lda     #0
        sta     hz_index
@condition:
        ldx     hz_index
        lda     hz_condition,x
        sta     hz_condition_index
        tax
        lda     injury_active,x
        jne     @next
        lda     injury_prevented,x
        beq     @expose
        lda     hz_index
        cmp     #2              ; native decay only salt/frost counters
        jeq     @next
        cmp     #1
        jeq     @next
        jsr     hz_decay
        jmp     @next
@expose:
        lda     hz_index
        beq     @salt
        cmp     #3
        beq     @cold
        jsr     hz_sun
        jcc     @next
        fld     s_step
        jmp     @increment
@salt:  jsr     hz_air
        fop     FCOMP, hz_71
        cmp     #$FF
        bne     :+
        fld     f_zero
        jmp     @increment
:       fop     FSUB, hz_70
        jsr     negate
        fop     FMULT, hz_0_0167
        fop     FMULT, s_step
        fst     t1
        ldy     #1
        lda     thermal_mode
        cmp     #1
        bne     :+
        iny
:       lda     #0
        jsr     GIVAYF
        fop     FMULT, t1
        jmp     @increment
@cold:  jsr     hz_air
        fop     FSUB, hz_30
        fop     FMULT, hz_0_02
        fop     FMULT, s_step
        fst     t1
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FMULT, t1
        fst     t1
        fld     s_metabolic
        fop     FDIV, t1
        fop     FCOMP, hz_max
        cmp     #1
        bne     :+
        fld     hz_max
:       fop     FCOMP, hz_min
        cmp     #$FF
        bne     @increment
        fld     hz_min
@increment:
        jsr     AYINT
        ldx     hz_index
        txa
        asl
        tax
        clc
        lda     exposure_counter,x
        adc     $A1
        sta     exposure_counter,x
        lda     exposure_counter+1,x
        adc     $A0
        sta     exposure_counter+1,x
        bmi     @zero
        lda     hz_limit+1,x
        cmp     exposure_counter+1,x
        bcc     @begin
        jne     @next
        lda     hz_limit,x
        cmp     exposure_counter,x
        jcs     @next
@begin:
        jsr     hz_zero
        ldx     hz_condition_index
        lda     #1
        sta     injury_active,x
        lda     hz_since_lo,x
        sta     gp2
        lda     hz_since_hi,x
        sta     gp2+1
        ldy     #4
@stamp: lda     s_elap,y
        sta     (gp2),y
        dey
        bpl     @stamp
        jmp     @next
@zero:  jsr     hz_zero
@next:  inc     hz_index
        lda     hz_index
        cmp     #4
        jne     @condition
        jmp     hz_diseases     ; lot 13: infection and malaria (alerts.s)
hz_zero:
        lda     #0
        sta     exposure_counter,x
        sta     exposure_counter+1,x
        rts

hz_air:
        lda     felt_temp+1
        ldy     felt_temp
        jsr     GIVAYF
        ldx     shelter_inside
        beq     @done
        lda     #0
        ldy     airtemp
        cpy     #128
        bcc     :+
        lda     #255
:       jsr     GIVAYF
        fop     FADD, th_shelter15
@done:  rts

; Compare the solar sine with SIN(31/46 degrees), avoiding an unnecessary
; inverse trig operation. No burn under woods, shelter or precipitation.
hz_sun:
        lda     night
        ora     shelter_inside
        bne     @no
        lda     weather_sky
        cmp     #2
        bcs     @no
        jsr     sky_position
        fld     sky_up
        fop     FCOMP, hz_sin31
        cmp     #$FF
        beq     @no
        jsr     level_here
        cmp     M_SNOW
        bcc     @not_snow
        lda     hz_index
        cmp     #2
        bne     @burn
        lda     verb
        cmp     #V_REST
        beq     @no
        cmp     #V_CAMP
        beq     @no
        lda     weather_sky
        bne     @no
        sec
        rts
@not_snow:
        lda     hz_index
        cmp     #2
        beq     @no
@burn:  jsr     woods_here
        bcs     @no
        fld     sky_up
        fop     FCOMP, hz_sin46
        cmp     #$FF
        bne     @yes
        jsr     level_here
        clc
        adc     M_BASE
        cmp     #101
        bcs     @yes
        jsr     level_here
        cmp     M_SNOW
        bcc     @no
@yes:  sec
        rts
@no:   clc
        rts

hz_decay:
        fld     s_step
        fop     FMULT, sv_0_017
        fop     FADD, hz_3
        fst     t1
        fld     hz_3
        fop     FDIV, t1
        fst     t1
        lda     hz_index
        asl
        tax
        lda     exposure_counter+1,x
        ldy     exposure_counter,x
        jsr     GIVAYF
        fst     t2
        fld     t1
        fop     FDIV, t2
        jsr     AYINT
        lda     hz_index
        asl
        tax
        lda     $A1
        sta     exposure_counter,x
        lda     $A0
        sta     exposure_counter+1,x
        rts

; Native daily action resets; acquired treatment is retained. Protection is
; recomputed in the medical module after the next action that changes care.
.segment "OUTDOOR"
module_medical_day:
        ldx     #8
        lda     #0
@reset: ldy     hz_daily,x
        sta     medical_actions-1,y
        dex
        bpl     @reset
        jsr     alerts_day      ; lot 13: daily gauge alerts and energy counters
        jmp     medical_apply
hz_daily: .byte 2,5,9,13,14,16,17,19,24

.segment "HAZARDS"
hz_condition: .byte 9,4,5,6
hz_limit: .word 500,240,240,7200
hz_minutes: .word 0
hz_index: .byte 0
hz_condition_index: .byte 0
hz_0_0167: .byte $7B,$08,$CE,$70,$3B
hz_0_02: .byte $7B,$23,$D7,$0A,$3E ; original final mantissa bit
hz_30: .byte $85,$70,0,0,0
hz_70: .byte $87,$0C,0,0,0
hz_71: .byte $87,$0E,0,0,0
hz_3: .byte $82,$40,0,0,0
hz_max: .byte $8F,$40,0,0,0
hz_min: .byte $8F,$C0,0,0,0
hz_sin31: .byte $80,$03,$D9,$89,$08
hz_sin46: .byte $80,$38,$26,$A7,$35
hz_since_lo: .repeat 15,I
        .byte <(injury_since+5*I)
        .endrepeat
hz_since_hi: .repeat 15,I
        .byte >(injury_since+5*I)
        .endrepeat
