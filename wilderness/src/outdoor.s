; Playable port rules; native filters, medical curves and load accounting remain.
.segment "OUTDOOR"
module_outdoor:
        lda     #0
        sta     outdoor_minutes
        sta     outdoor_act
        lda     #6
        sta     outdoor_result
        lda     input_argument
        jne     @done
        lda     animal_kind
        jeq     @done
        lda     animal_x
        cmp     px+1
        jne     @done
        lda     animal_y
        cmp     py+1
        jne     @done
        ; Refuse a command targeting a different animal.
        lda     noun
        beq     @target
        cmp     #80             ; GAME is a generic target
        beq     @target
        ldx     animal_kind
        cmp     out_nouns-6,x
        beq     @target
        cpx     #7
        jne     @done
        cmp     #192            ; PUMA is a synonym for COUGAR
        jne     @done
@target:
        lda     verb
        cmp     #37             ; IGNORE evaluates the encounter, never guarantees escape
        beq     @ignore
        lda     tree_in
        ora     shelter_inside
        bne     @protected
        lda     #0
        sta     animal_age
        lda     verb
        cmp     #18
        beq     @scare
        ; ATTACK: native weapon-dependent injury and success rolls are independent.
        jsr     outdoor_weapon
        bcc     @weapon
        sta     out_tool
        lda     #10
        sta     outdoor_minutes
        lda     #0
        sta     out_hurt
        ldx     out_tool
        lda     out_attack_injury,x
        jsr     outdoor_roll
        bcs     :+
        inc     out_hurt
:       ldx     out_tool
        lda     out_attack_success,x
        jsr     outdoor_roll
        php                     ; severity must not change the victory roll
        ldx     out_hurt
        beq     :+
        jsr     outdoor_injure
:       plp
        bcs     @failed
        lda     #10
        ldx     out_hurt
        beq     @clear
        lda     #17             ; won the exchange, but still injured
        bne     @clear
@failed:
        lda     #14
        ldx     out_hurt
        beq     @result
        lda     #11
        bne     @result
@ignore:
        lda     #5
        sta     outdoor_minutes
        jmp     outdoor_passive
@protected:
        lda     #16
        bne     @result
@weapon:
        lda     #8
        bne     @result
@scare:
        lda     MAP+37
        beq     :+
        jsr     outdoor_scare_effort
:
        ldy     #5
        lda     MAP+37
        beq     :+
        ldy     #15
:       sty     outdoor_minutes
        ldx     animal_kind
        lda     out_noise-6,x
        jsr     outdoor_roll
        bcc     @scared
        ldx     animal_kind
        lda     out_noise_injury-6,x
        jsr     outdoor_roll
        bcs     @stays
        jsr     outdoor_injure
        lda     MAP+37
        beq     :+
        lda     #5              ; a wound returns through native clock/resources
        sta     outdoor_act
:
        lda     #11
        bne     @result
@stays: lda     #12
        bne     @result
@scared:
        lda     #9
@clear: ldx     #0
        stx     animal_kind
@result:
        sta     outdoor_result
        lda     MAP+37
        beq     @done
        lda     verb
        cmp     #18
        bne     @done
        jsr     outdoor_scare_theft
@done:  rts

; T06/S04 noise effort: 1.65 + .02 * (body pounds + carried ounces / 16).
outdoor_scare_effort:
        jsr     load_totals
        lda     load_used
        sta     out_loss
        lda     load_used+1
        sta     out_loss+1
        ldx     #4
@divide:
        lsr     out_loss+1
        ror     out_loss
        dex
        bne     @divide
        clc
        lda     out_loss
        adc     body_weight
        tay
        lda     out_loss+1
        adc     body_weight+1
        jsr     GIVAYF
        fop     FMULT, tree_effort
        fop     FADD, f_rest_rate
        fst     s_metabolic
        lda     #4
        sta     outdoor_act
        rts

; A failed noise attempt still evaluates the species' food-theft risk.
outdoor_scare_theft:
        lda     animal_kind
        beq     @done
        cmp     #8
        beq     @done
        lda     #13
        ldx     it_place+21      ; suspended food: native one-percent risk
        cpx     #5
        bne     :+
        lda     #3
:       jsr     outdoor_roll
        bcs     @done
        jsr     outdoor_steal
        bcc     @done
        lda     #15
        sta     outdoor_result
@done:  rts

; Native travel evaluates the animal still present BEFORE preparing its
; next raster step. Its injury/theft rolls share the compass/weather stream.
; The previous sighting is cleared as the player leaves, including odd units.
module_native_walk_reaction:
        ldx     animal_kind
        lda     out_active_injury-6,x
        jsr     outdoor_roll
        bcs     :+
        jsr     outdoor_injure
:
        jsr     outdoor_scare_theft
        lda     #0
        sta     animal_kind
        sta     animal_age
        jmp     walk_prepare    ; reload TRAVEL; the cleared sighting prevents recursion

; T0A/S05 evaluates the existing animal before scanning after a new wound.
module_wound_retention:
        jsr     weather_random
        fop     FCOMP, out_0_7
        cmp     #$FF
        bne     @done
        lda     #0
        sta     animal_kind
@done:  lda     #5
        rts
out_0_7: .byte $80,$33,$33,$33,$33

; Return species index with an accessible axe or knife (native method 18).
; Access alone is insufficient: a hung tool and a remote ground tool are excluded.
outdoor_weapon:
        lda     animal_kind
        sec
        sbc     #6
        sta     out_tool
        ldx     #58
        jsr     have
        bcs     @axe
        ldx     #59
        jsr     have
        bcc     @done
@axe:   lda     out_tool
        sec
@done:  rts

; Quantized native probability; <= boundary retained, zero never succeeds.
; One shared fauna generator, independent of weather and water contamination.
outdoor_roll:
        sta     out_threshold
        ldx     MAP+37
        bne     outdoor_native_roll
        ldx     #7              ; separate consecutive decision rolls
        lda     fauna_rng
        bne     @step
        lda     #$B7
@step:  lsr
        bcc     :+
        eor     #$B8
:       dex
        bne     @step
        sta     fauna_rng
        cmp     out_threshold
        rts

outdoor_native_roll:
        lda     #3
        jsr     overlay_load
        ldy     out_threshold
        cpy     #129
        bne     :+
        dey                     ; noise .5 exactly
:       lda     #0
        jsr     GIVAYF
        lda     FAC
        beq     :+
        sec
        sbc     #8              ; other existing thresholds remain quantized
        sta     FAC
:       fst     t3
        jsr     weather_random
        fop     FCOMP, t3
        cmp     #$FF
        beq     @hit
        sec
        rts
@hit:  clc
        rts

; Called by the simulation after 60 minutes with the same animal present.
; Bit 7 marks a reaction report, distinct from the ordinary sighting alert.
module_animal_attack:
        lda     MAP+37
        beq     :+
        lda     scene_minutes
        bne     :+
        jmp     module_native_walk_reaction
:
        jsr     outdoor_passive
        lda     #128
        sta     fauna_alert
        rts

outdoor_passive:
        lda     #0
        sta     animal_age
        lda     shelter_inside
        bne     @depart
        ldx     animal_kind
        lda     out_passive_injury-6,x
        ldy     tree_in
        bne     @roll           ; tree method 16 has the same Sierra risk as IGNORE
        ldy     verb
        cpy     #22
        bcs     @roll
        lda     out_active_injury-6,x ; native method 13 for meals/rest/wait
@roll:  jsr     outdoor_roll
        bcs     @food
        jsr     outdoor_injure
        lda     #11
        bne     @result
@food:  lda     animal_kind
        cmp     #8              ; Sierra rattlesnake does not steal provisions
        beq     @leave_roll
        lda     #13             ; native 5%; climbing without hanging doubles it
        ldx     tree_in
        beq     :+
        lda     #26
:       jsr     outdoor_roll
        bcs     @leave_roll
        jsr     outdoor_steal
        bcc     @leave_roll
        lda     #15
        bne     @clear
@leave_roll:
        ldx     animal_kind
        lda     out_departure-6,x ; port withdrawal, not a reconstructed native rate
        jsr     outdoor_roll
        bcs     @stays
@depart:
        lda     #7
@clear: ldx     #0
        stx     animal_kind
@result:
        sta     outdoor_result
        rts
@stays: lda     #13
        bne     @result

outdoor_injure:
        ldx     #7              ; poisonous bite from rattlesnake
        lda     animal_kind
        cmp     #8
        beq     outdoor_poison
        ldy     #0
        cmp     #7
        bne     :+
        ldy     #3
:       lda     #0
        jsr     outdoor_roll    ; separate severity sample, after combat decisions
        ldx     #0
@severity:
        cmp     out_severity,y
        bcc     @begin
        iny
        inx
        cpx     #3
        bcc     @severity
@begin: jmp     outdoor_begin_injury

outdoor_poison:
        lda     MAP+37
        beq     @begin
        jsr     weather_random  ; native venom severity, INT(30*RND + 60)
        fop     FMULT, out_30
        fop     FADD, f_60
        jsr     AYINT
        lda     $A1
        sta     poison_floor
@begin: ldx     #7
        jmp     outdoor_begin_injury
out_30: .byte $85,$70,0,0,0
out_0_01: .byte $7A,$23,$D7,$0A,$3E
.segment "SCRATCH"
poison_floor: .res 1
.segment "OUTDOOR"

; INT(1+5*RND^row[22]): bear exponent 1, cougar exponent 2.
; Quantized boundaries for cuts, arm, leg; both upper outcomes become shock.
out_severity: .byte 52,103,154,115,162,199

; Remove only accessible food (23..37), preserving water, gear, hung stocks
; and remote ground piles. Subtract stolen ounces from the total atomically.
outdoor_steal:
        lda     #0
        sta     out_stolen
        ldx     #23
@food:
        stx     out_food
        lda     #0
        sta     out_loss
        sta     out_loss+1
        lda     it_place,x
        cmp     #5
        beq     @ground
        lda     it_pack_lo,x
        sta     out_loss
        lda     it_pack_hi,x
        sta     out_loss+1
        lda     #0
        sta     it_pack_lo,x
        sta     it_pack_hi,x
@ground:
        jsr     at_ground
        bcc     @total
        clc
        lda     out_loss
        adc     it_gnd_lo,x
        sta     out_loss
        lda     out_loss+1
        adc     it_gnd_hi,x
        sta     out_loss+1
        lda     #0
        sta     it_gnd_lo,x
        sta     it_gnd_hi,x
@total: lda     out_loss
        ora     out_loss+1
        beq     @next
        inc     out_stolen
        sec
        lda     it_oz_lo,x
        sbc     out_loss
        sta     it_oz_lo,x
        lda     it_oz_hi,x
        sbc     out_loss+1
        sta     it_oz_hi,x
        lda     it_pack_lo,x
        ora     it_pack_hi,x
        beq     @only_ground
        lda     #5              ; surviving carried stock is hanging
        bne     @place
@only_ground:
        lda     #0
        ldy     it_gnd_lo,x
        bne     @place
        ldy     it_gnd_hi,x
        bne     @place
        lda     #255
@place: sta     it_place,x
@next:  ldx     out_food
        inx
        cpx     #38
        jcc     @food
        jsr     load_totals
        lda     out_stolen
        cmp     #1
        rts

; Sierra native thresholds, ordinary outside mode ($0D5D=0).
; Noise: .8 - .03 * row[14]. Failed noise uses row[14] * .02 for injury.
; Blade injury: row[18] * .02; success: row[24] * .01 / 2.
out_noise:           .byte 129,129,0
out_noise_injury:    .byte 52,52,154
out_attack_injury:   .byte 180,129,103
out_attack_success:  .byte 4,13,39
out_passive_injury:  .byte 11,11,16 ; native rows[15/16] * .02
out_active_injury:   .byte 6,6,11   ; native row[13] * .02
out_departure:       .byte 128,64,192 ; port: bear 50%, cougar 25%, snake 75%
out_tool:           .byte 0
out_hurt:           .byte 0
out_threshold:      .byte 0
out_food:           .byte 0
out_loss:           .word 0
out_stolen:         .byte 0

outdoor_begin_injury:
        lda     injury_prevented,x
        bne     @present
        lda     injury_active,x
        bne     @present
        lda     #1
        sta     injury_active,x
        sta     health_period   ; evaluate a new wound during this transaction
        lda     #0
        sta     injury_treated,x
        txa
        asl
        asl
        stx     out_condition
        clc
        adc     out_condition
        tay
        lda     MAP+37
        beq     @legacy_stamp
        tya
        pha
        ldy     #15
        lda     #0
        jsr     GIVAYF
        fop     FMULT, out_0_01
        fop     FADD, s_elap
        fst     t3              ; native onset stamp = elapsed + .01 * reaction minutes
        pla
        tay
        ldx     #0
@native_stamp:
        lda     t3,x
        sta     injury_since,y
        iny
        inx
        cpx     #5
        bcc     @native_stamp
        rts
@legacy_stamp:
        ldx     #0
@stamp: lda     s_elap,x
        sta     injury_since,y
        iny
        inx
        cpx     #5
        bcc     @stamp
@present:
        rts

; River-water contamination is a port rule: independent RNG, 1/8 per drink.
; A refill neither hydrates the player nor starts illness before consumption.
module_water_hazard:
        lda     water_drinking_untreated
        beq     @done
        lda     water_rng
        bne     @step
        lda     #$B7
@step:  lsr
        bcc     :+
        eor     #$B8
:       sta     water_rng
        cmp     #32
        bcs     @stock
        ldx     #11             ; GIARDIA; native incubation and FLAGYL treatment
        jsr     outdoor_begin_injury
@stock: lda     it_pack_lo+N_WATER
        ora     it_pack_hi+N_WATER
        bne     :+
        lda     #0
        sta     water_untreated
:       lda     it_gnd_lo+N_WATER
        ora     it_gnd_hi+N_WATER
        bne     @done
        lda     #0
        sta     water_ground_untreated
@done:  rts

module_outdoor_report:
        lda     fauna_alert
        and     #127
        sta     fauna_alert
        ldx     outdoor_result
        jeq     @done
        lda     out_message_lo-1,x
        pha
        lda     out_message_hi-1,x
        tax
        pla
        jmp     message
@done:  rts
out_message_lo: .byte <out_no_water,<out_no_canteen,<out_full,<out_filled,<out_heavy,<out_no_animal,<out_calm,<out_weapon,<out_scared,<out_defended,<out_injured,<out_noise_failed,<out_watching,<out_attack_failed,<out_stolen_msg,<out_protected,<out_wounded_win
out_message_hi: .byte >out_no_water,>out_no_canteen,>out_full,>out_filled,>out_heavy,>out_no_animal,>out_calm,>out_weapon,>out_scared,>out_defended,>out_injured,>out_noise_failed,>out_watching,>out_attack_failed,>out_stolen_msg,>out_protected,>out_wounded_win
out_no_water: .byte "REFILL NEEDS A NEARBY BANK.|USE FILL CANTEEN WITHOUT A QUANTITY.",0
out_no_canteen: .byte "CARRY A CANTEEN BEFORE COLLECTING WATER.",0
out_full: .byte "YOUR 2QT CANTEEN IS FULL: 64 OZ.",0
out_filled: .byte "CANTEEN FILLED TO 64 OZ. 10 MINUTES.|RIVER WATER IS UNTREATED.",0
out_heavy: .byte "REFILL REFUSED: WEIGHT OR VOLUME.|DROP SOME GEAR AND TRY AGAIN.",0
out_no_animal: .byte "NO MATCHING ANIMAL HERE.",0
out_calm: .byte "THE ANIMAL LEAVES.",0
out_weapon: .byte "ATTACK NEEDS ACCESSIBLE AXE OR KNIFE.",0
out_scared: .byte "YOU DRIVE THE ANIMAL AWAY.",0
out_defended: .byte "YOU DEFEND YOURSELF. ANIMAL GONE.",0
out_injured: .byte "THE ANIMAL INJURES YOU AND STAYS.|STATUS M: CHECK WOUNDS AND CARE.",0
out_noise_failed: .byte "NOISE FAILS. ANIMAL STAYS.",0
out_watching: .byte "ANIMAL STILL WATCHING YOU.|SCARE, IGNORE OR MOVE AWAY.",0
out_attack_failed: .byte "ATTACK FAILS. ANIMAL STAYS.|MOVE AWAY OR TRY AGAIN.",0
out_stolen_msg: .byte "FOOD STOLEN. THE ANIMAL LEAVES.|HANG FOOD TO PROTECT IT.",0
out_protected: .byte "LEAVE COVER TO SCARE OR ATTACK.",0
out_wounded_win: .byte "ANIMAL GONE. YOU ARE INJURED.|STATUS M: CHECK WOUNDS AND CARE.",0
out_nouns: .byte 76,181,182
out_condition: .byte 0
