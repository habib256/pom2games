; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Conditions 1..15 and prevention/treatment prerequisites reconstructed from
; Journey T0B/S0D and T06/S00. State is resident; this overlay may be evicted
; by STATUS, inventory, sprites or the simulation without losing a condition.
.segment "GDATA"
medical_state:
injury_active: .res 15
injury_treated: .res 15
injury_prevented: .byte 0,0,0,0,1,0,1,0,0,0,0,0,0,0,1
injury_percent: .repeat 15
        .byte 100
        .endrepeat
injury_since: .res 75
medical_actions: .byte 0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0
s_injury_factor: .byte $81,0,0,0,0
altitude_percent: .byte 100
oxygen_active: .byte 0
medical_state_end:
.segment "MEDICAL"

; X = zero-based condition. Prevention blocks the same conditions as native
; T06/S00; infection, food poisoning and giardia may restart when active.
module_injury_begin:
        cpx     #15
        bcs     @done
        lda     injury_prevented,x
        bne     @done
        cpx     #8
        beq     @begin
        cpx     #10
        beq     @begin
        cpx     #11
        beq     @begin
        lda     injury_active,x
        bne     @done
@begin:
        lda     #1
        sta     injury_active,x
        lda     #0
        sta     injury_treated,x
        lda     injury_since_lo,x
        sta     gp2
        lda     injury_since_hi,x
        sta     gp2+1
        ldy     #4
@stamp: lda     s_elap,y
        sta     (gp2),y
        dey
        bpl     @stamp
@done:  rts

; Progression returns the product of integer condition percentages. Native
; incubation rounds the positive loss before subtracting from the floor;
; recovery rounds the gain. A condition heals at t + duration (inclusive).
module_injury_health:
        lda     MAP+37
        beq     :+
        lda     poison_floor
        sta     med_floor+7
:
        fld     f_one
        fst     s_injury_factor
        lda     #0
        sta     med_index
@condition:
        ldx     med_index
        lda     injury_active,x
        bne     @active
        lda     #100
        jmp     @store
@active:
        lda     injury_since_lo,x
        ldy     injury_since_hi,x
        jsr     MOVFM
        fop     FSUB, s_elap
        jsr     clamp0
        ldx     MAP+37
        beq     :+
        fop     FCOMP, f_half
        cmp     #$FF
        bne     :+
        fld     f_half          ; native condition clock never reports less than .5 h
:
        fst     t1              ; elapsed since onset, in hours
        ldx     med_index
        ldy     med_incubation,x
        lda     #0
        jsr     GIVAYF
        fst     t2              ; incubation
        ldx     med_index
        cpx     #4
        bcc     @recover
        cpx     #13
        beq     @recover
        fld     t1
        fop     FCOMP, t2
        cmp     #1
        beq     @recover
        lda     t2
        beq     @recover        ; no division by zero for zero incubation
        fld     t1
        fop     FSUB, t2        ; t - h
        fst     t3
        fld     t2
        fop     FDIV, t3
        jsr     med_loss
        jsr     AYINT
        ldx     med_index
        clc
        lda     $A1
        adc     med_floor,x
        jmp     @store
@recover:
        ldx     med_index
        lda     med_untreated_lo,x
        ldy     med_untreated_hi,x
        pha
        lda     injury_treated,x
        beq     @duration
        pla
        lda     med_treated_lo,x
        ldy     med_treated_hi,x
        pha
@duration:
        pla
        tax
        tya
        pha
        txa
        tay
        pla
        jsr     GIVAYF          ; A high, Y low
        fst     t3              ; recovery duration
        fop     FADD, t2
        fop     FCOMP, t1
        cmp     #1
        beq     @gain
        ldx     med_index
        lda     #0
        sta     injury_active,x
        sta     injury_treated,x
        lda     #100
        jmp     @store
@gain:
        fld     t2
        fop     FSUB, t1        ; h - t
        fst     t2
        fld     t3
        fop     FDIV, t2
        jsr     med_loss
        jsr     AYINT
        ldx     med_index
        clc
        lda     $A1
        adc     med_floor,x
@store: ldx     med_index
        sta     injury_percent,x
        tay
        lda     #0
        jsr     GIVAYF
        fop     FMULT, s_injury_factor
        fop     FMULT, med_0_01
        fst     s_injury_factor
        inc     med_index
        lda     med_index
        cmp     #15
        jne     @condition
        jmp     med_altitude

; Native altitude condition 19 uses the preceding health value for its
; threshold, then INT(100*(1-.00144*(altitude/10)^2)). Oxygen suppresses it.
med_altitude:
        lda     oxygen_active
        beq     @height
        ldx     #49
        jsr     have
        bcs     @healthy
@height:
        jsr     level_here
        clc
        adc     M_BASE
        sta     med_altitude_level
        fld     s_health
        fop     FMULT, f_5
        jsr     AYINT
        clc
        lda     $A1
        adc     #100
        cmp     med_altitude_level
        bcs     @healthy
        lda     #0
        ldy     med_altitude_level
        jsr     GIVAYF
        jsr     $EA55          ; native /10
        fst     t1
        fop     FMULT, t1
        fop     FMULT, med_altitude_k
        fop     FSUB, f_one
        jsr     $EA39
        jsr     $EA39
        jsr     AYINT
        lda     $A1
        jmp     @factor
@healthy:
        lda     #100
@factor:
        sta     altitude_percent
        tay
        lda     #0
        jsr     GIVAYF
        fop     FMULT, s_injury_factor
        fop     FMULT, med_0_01
        fst     s_injury_factor
        rts

med_loss:
        fst     t2
        ldx     med_index
        sec
        lda     #100
        sbc     med_floor,x
        tay
        lda     #0
        jsr     GIVAYF
        fop     FMULT, t2
        rts

; T0B/S0D shortens the next health step for critical health and the first
; eight hours of active conditions 6..11. A holds the previous period limit.
module_medical_cap:
        sta     med_minutes
        lda     MAP+37
        jeq     @health
        lda     s_therm_rate
        jeq     @health
        lda     night
        jne     @health
        jsr     sky_position
        ; Native B7 is the integer elevation, and clouds hide the sun when
        ; SIN(B7 degrees) < 15 / visibility. Shelter and woods do not alter
        ; this scheduling limit (unlike the sunburn exposure test).
        fld     sky_up
        fop     FMULT, sky_up
        fop     FSUB, f_one
        jsr     FSQR
        fop     FDIV, sky_up
        jsr     FATN
        fst     t1
        fld     f_rad
        fop     FDIV, t1
        jsr     AYINT
        ldy     $A1
        cpy     #31
        bcc     @health
        lda     #0
        jsr     GIVAYF
        fop     FMULT, f_rad
        jsr     FSIN
        fst     t1
        ldy     #15
        lda     #0
        jsr     GIVAYF
        fst     t2
        ldy     weather_visibility
        lda     #0
        jsr     GIVAYF
        fop     FDIV, t2
        fop     FCOMP, t1
        cmp     #1
        beq     @health
        lda     med_minutes
        cmp     #61
        bcc     @health
        lda     #60
        sta     med_minutes
@health:
        fld     s_health
        fop     FCOMP, f_one
        cmp     #$FF
        beq     @short
        lda     #5
        sta     med_index
@condition:
        ldx     med_index
        lda     injury_active,x
        beq     @next
        lda     injury_since_lo,x
        ldy     injury_since_hi,x
        jsr     MOVFM
        fop     FSUB, s_elap
        fop     FCOMP, med_8
        cmp     #$FF
        beq     @short
@next:  inc     med_index
        lda     med_index
        cmp     #11
        bcc     @condition
        lda     med_minutes
        rts
@short: lda     med_minutes
        cmp     #31
        bcc     @done
        lda     #30
@done:  rts

; Native prevention is any of prerequisites 1/2; active treatment uses all
; of 4/5/6 when row 3 is set, otherwise any. An already treated condition
; retains its treatment. Placeholder selector 30 is always absent.
module_medical_apply:
        lda     #0
        sta     med_index
@condition:
        ldx     med_index
        lda     injury_active,x
        bne     @treatment
        cpx     #4
        bcc     @next
        cpx     #7
        beq     @next
        cpx     #10
        beq     @next
        cpx     #13
        bcs     @next
        lda     med_prevent1,x
        jsr     med_action
        bne     @prevent
        lda     med_prevent2,x
        jsr     med_action
@prevent:
        sta     injury_prevented,x
        jmp     @next
@treatment:
        lda     injury_treated,x
        bne     @next
        lda     med_all,x
        bne     @all
        lda     med_treat1,x
        jsr     med_action
        bne     @treated
        lda     med_treat2,x
        jsr     med_action
        bne     @treated
        lda     med_treat3,x
        jsr     med_action
        jmp     @treated
@all:   lda     med_treat1,x
        jsr     med_action
        beq     @treated
        lda     med_treat2,x
        jsr     med_action
        beq     @treated
        lda     med_treat3,x
        jsr     med_action
@treated:
        sta     injury_treated,x
@next:  inc     med_index
        lda     med_index
        cmp     #13
        bcc     @condition
        rts
med_action:
        tay
        lda     #0
        cpy     #31
        bcs     @done
        lda     medical_actions-1,y
@done:  rts

; Inventory T0E/S0A updates care selectors 27 and 8 from full-body
; coverage. Sleeping bag, tent, ground cover and raincoat count only worn.
module_medical_clothing:
        lda     #0
        sta     medical_actions+26
        lda     it_place+1
        cmp     #1
        beq     @frost
        ldx     #0
@frost_item:
        ldy     med_frost_gear,x
        lda     it_place,y
        cmp     #1
        bne     @sun
        inx
        cpx     #3
        bcc     @frost_item
@frost: lda     #1
        sta     medical_actions+26
@sun:   lda     #0
        sta     medical_actions+7
        ldx     #3
@cover: ldy     med_full_cover,x
        lda     it_place,y
        cmp     #1
        beq     @covered
        dex
        bpl     @cover
        lda     it_place+4
        cmp     #1
        beq     @shirt
        lda     it_place+15
        cmp     #1
        bne     @done
@shirt: ldx     #2
@upper: ldy     med_upper_cover,x
        lda     it_place,y
        cmp     #1
        beq     @covered
        dex
        bpl     @upper
        rts
@covered:
        lda     #1
        sta     medical_actions+7
@done:  rts
med_frost_gear: .byte 3,5,7
med_full_cover: .byte 1,11,12,9
med_upper_cover: .byte 2,8,14

med_index: .byte 0
med_minutes: .byte 0
med_0_01: .byte $7A,$23,$D7,$0A,$3E ; native coefficient, final mantissa bit
med_altitude_k: .byte $77,$3C,$BE,$61,$CF
med_8: .byte $84,0,0,0,0
med_altitude_level: .byte 0
med_floor: .byte 75,70,40,20,75,75,60,20,50,70,50,85,40,1,100
med_incubation: .byte 0,0,0,0,8,3,6,3,4,24,6,24,240,0,1
med_treated_lo: .byte <60,<672,<672,<72,<48,<8,<48,<24,<48,<24,<48,<48,<672,<100,<2
med_treated_hi: .byte >60,>672,>672,>72,>48,>8,>48,>24,>48,>24,>48,>48,>672,>100,>2
med_untreated_lo: .byte <240,<1008,<1344,<336,<96,<24,<336,<168,<336,<30000,<120,<336,<1008,<100,<3
med_untreated_hi: .byte >240,>1008,>1344,>336,>96,>24,>336,>168,>336,>30000,>120,>336,>1008,>100,>3
med_prevent1: .byte 30,30,30,30,14,13,27,30,11,18,30,22,15
med_prevent2: .byte 30,30,30,30,8,30,24,30,21,25,30,16,20
med_all: .byte 0,0,0,1,1,0,0,0,0,0,0,0,0
med_treat1: .byte 1,3,3,4,6,13,27,12,11,18,6,17,20
med_treat2: .byte 2,30,30,5,6,10,24,7,30,25,30,30,30
med_treat3: .byte 30,30,30,6,9,30,30,23,30,30,30,30,30
injury_since_lo: .repeat 15,I
        .byte <(injury_since+5*I)
        .endrepeat
injury_since_hi: .repeat 15,I
        .byte >(injury_since+5*I)
        .endrepeat
.segment "MEDVIEW"
        .include "care.s"
