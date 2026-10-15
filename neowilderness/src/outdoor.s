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
        sta     fauna_named     ; species named by the result message
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
        cmp     #192            ; PUMA is a synonym for COUGAR
        jne     @done
        lda     out_nouns-6,x
        cmp     #181
        jne     @done
@target:
        lda     verb
        cmp     #37             ; IGNORE evaluates the encounter, never guarantees escape
        beq     @ignore
        lda     tree_in         ; (a shelter is no cover: D4, outdoor_hurt)
        bne     @protected
        lda     #0
        sta     animal_age
        lda     verb
        cmp     #18
        beq     @scare
        ; ATTACK: native weapon-dependent injury and success rolls are independent.
        jsr     outdoor_weapon
        bcc     @weapon
        lda     #10
        sta     outdoor_minutes
        lda     #0
        sta     out_hurt
        ldx     out_tool
        lda     out_means_injury,x
        jsr     outdoor_hurt
        bcs     :+
        inc     out_hurt
:       ldx     out_tool
        lda     out_means_success,x
        jsr     outdoor_roll
        php                     ; severity must not change the victory roll
        ldx     out_hurt
        beq     :+
        jsr     outdoor_injure
:       plp
        bcs     @failed
        jsr     forage_kill     ; lot 4: the carcass (src/forage.s)
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
        jsr     outdoor_hurt
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
        ldx     animal_kind
        beq     @done
        lda     out_kind-6,x
        bpl     @done           ; header byte 28: no theft
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
        jsr     outdoor_hurt
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

; outdoor_weapon -- the means of ATTACK (T0F/S07 $590F, as KILL GAME in
; src/frg.s): the first in use, its flag cleared: GUN 21, BOW 20, SPEAR 19
; (lot 3), AXE or KNIFE put in use on this cell 18 (both cleared), CLUB or
; ROCK 17. None in use: an accessible AXE or KNIFE, 18 (the port's rule
; before lot 3, kept; a hung tool and a remote ground tool are excluded).
; C set: out_tool = 4 (means - 17) + species, the row of out_means_*.
outdoor_weapon:
        lda     camp_use
        and     #U_GUN
        beq     :+
        eor     camp_use
        sta     camp_use
        lda     #4
        bne     @means
:       lda     #FT_BOW
        ldy     #3
        jsr     outdoor_in_use
        bcs     @means
        lda     #FT_SPEAR
        ldy     #2
        jsr     outdoor_in_use
        bcs     @means
        lda     care_tools
        and     #3
        beq     :+
        lda     px+1
        cmp     care_tool_x
        bne     :+
        lda     py+1
        cmp     care_tool_y
        bne     :+
        lda     care_tools
        and     #$FC
        sta     care_tools
        lda     #1
        bne     @means
:       lda     #FT_CLUB
        ldy     #0
        jsr     outdoor_in_use
        bcs     @means
        ldx     #58
        jsr     have
        bcs     @blade
        ldx     #59
        jsr     have
        bcc     @done
@blade: lda     #1
@means: asl     a
        asl     a               ; (C clear)
        adc     animal_kind
        sbc     #6-1            ; (C clear: - 6)
        sta     out_tool
        sec
@done:  rts
outdoor_in_use:                 ; A = an fg_use bit, Y = its row: C set,
        and     fg_use          ; A = Y and the bit cleared when in use
        beq     :+
        eor     fg_use
        sta     fg_use
        tya
        sec
        rts
:       clc
        rts

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
        ldx     animal_kind
        stx     fauna_named
        lda     out_tree_injury-6,x
        ldy     tree_in
        bne     @roll           ; native method 16 (equal to 15 in the Sierra)
        lda     out_passive_injury-6,x
        ldy     verb
        cpy     #22
        bcs     @roll
        lda     out_active_injury-6,x ; native method 13 for meals/rest/wait
@roll:  jsr     outdoor_hurt
        bcs     @food
        jsr     outdoor_injure
        lda     #11
        bne     @result
@food:  ldx     animal_kind
        lda     out_kind-6,x
        bpl     @leave_roll     ; header byte 28: no theft (Sierra rattlesnake)
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

; Venomous species (severity exponent >= 4: the snakes) bite with poison;
; the others take the cuts/arm/leg/shock row of their exponent (1 to 3).
outdoor_injure:
        ldx     animal_kind
        lda     out_kind-6,x
        and     #$4F
        cmp     #$40
        bcs     outdoor_poison
        tay
        lda     #0
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

; INT(1+5*RND^row[22]): exponent 1 (bear), 2 (cougar), 3 (wolf, cat).
; Quantized boundaries for cuts, arm, leg; both upper outcomes become shock.
out_severity: .byte 52,103,154,115,162,199,150,189,216

; A successful injury roll. New Guinea's cannibal (out_kind bit 5) spares a
; player who carries TRINKETS unless a second roll is below .02 (T06/S04
; $58DA-$58FA); every other species draws once, as before.
outdoor_hurt:
        ldy     shelter_inside  ; D4 (lot 3): in a shelter the risk x .1
        beq     @roll           ; (T06/S04 $5866-$5888)
        ldy     #$FF
:       iny
        sec
        sbc     #10
        bcs     :-
        tya
@roll:  jsr     outdoor_roll
        bcs     @done
        ldx     animal_kind
        lda     out_kind-6,x
        and     #$20
        beq     @done           ; C clear: injured
        lda     it_place+74     ; TRINKETS carried (place 1..4)
        beq     @done
        cmp     #5
        bcs     @hurt
        lda     #6              ; .02
        jmp     outdoor_roll
@hurt:  clc
@done:  rts

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

; fauna_reactions: native thresholds of the four species of the loaded
; region, ordinary outside mode ($0D5D=0), floor(256 p) + 1 (0: never),
; rewritten by its pack (76 bytes, tools/build_disk.py); the trunk holds
; the Sierra Nevada. Noise: .8 - .03 * row[14]. Failed noise uses
; row[14] * .02 for injury. ATTACK with means m = 17..21 (CLUB or ROCK,
; AXE or KNIFE, SPEAR, BOW, GUN; lot 3): injury row[m] * .02, success
; row[m + 6] * .01 / 2 (T06/S04 $589A, $593A; build/regions/fauna.json).
; out_kind: bit 7 theft (row[28]), bit 6 venom (row[22] >= 4), bit 5
; trinkets rule, bits 0-3 out_severity offset.
fauna_reactions:
out_noise:           .byte 129,129,0,0
out_noise_injury:    .byte 52,52,154,0
out_means_injury:    .byte 180,129,26,0 ; 17 CLUB, ROCK
out_attack_injury:   .byte 180,129,103,0 ; 18 AXE, KNIFE
                     .byte 129,103,26,0 ; 19 SPEAR
                     .byte 77,77,52,0   ; 20 BOW
                     .byte 26,36,36,0   ; 21 GUN
out_means_success:   .byte 2,4,77,0     ; 17
out_attack_success:  .byte 4,13,39,0    ; 18
                     .byte 9,26,77,0    ; 19
                     .byte 26,39,20,0   ; 20
                     .byte 45,52,45,0   ; 21
out_passive_injury:  .byte 11,11,16,0 ; native row[15] * .02 (IGNORE, commands >= 22)
out_tree_injury:     .byte 11,11,16,0 ; native row[16] * .02 (in a tree)
out_active_injury:   .byte 6,6,11,0   ; native row[13] * .02
out_departure:       .byte 128,64,192,0 ; port: bear 50%, cougar 25%, snake 75%
out_nouns:           .byte 76,181,182,0
out_kind:            .byte $80,$83,$40,0
out_value:           .byte 6,3,1,0      ; lot 4: header byte 30, V (meat 65 V^2, hide 12 V)
.export fauna_reactions
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

; Giardia (T0F/S00 $5CF7): drinking untreated water starts condition 12
; when the shared RND <= .2 / ((level + base) / 10), i.e. 2 / the altitude
; in hundreds of feet (lot 2, docs/CAMP.md). The canteen flag (B2[22]) is
; never cleared; BOIL (care selector 22) and IODINE (16) prevent the illness.
module_water_hazard:
        lda     water_drinking_untreated
        beq     @done
        jsr     level_here
        clc
        adc     M_BASE          ; byte sum, as $D4 + $60A1
        tay
        jsr     $E301           ; SNGFLT: FAC <- Y
        jsr     $EA55           ; DIV10
        fop     FDIV, f_0_2     ; .2 / FAC
        fst     t1
        jsr     weather_random
        fop     FCOMP, t1
        cmp     #1
        beq     @done           ; RND > p: no infection
        ldx     #11             ; GIARDIA; native incubation and FLAGYL treatment
        jsr     outdoor_begin_injury
@done:  rts

module_outdoor_report:
        lda     fauna_alert
        and     #127
        sta     fauna_alert
        ldx     outdoor_result
        jeq     @done
        lda     out_message_lo-1,x ; a text of the bank
        ldx     #0
        jmp     message
@done:  rts
out_message_lo: .byte <out_no_water,<out_no_canteen,<out_full,<out_filled,<out_heavy,<out_no_animal,<out_calm,<out_weapon,<out_scared,<out_defended,<out_injured,<out_noise_failed,<out_watching,<out_attack_failed,<out_stolen_msg,<out_protected,<out_wounded_win
out_condition: .byte 0

; ----------------------------------------------------------------------------
; The background under the animal (docs/MEMORY.md 28). PROJECT module_animal
; draws the animal of the cell over the whole view; an arrow turn (or LOOK
; L/R/B) would have to redraw it all, the animal staying centred. Instead,
; before the animal is drawn, the bytes of its columns (AB_N + 1 from byte
; AB_J0 of both banks, rows 16..175: the view and its cached rows) go to the
; auxiliary language card, bank 1 ($D000, TOPO's snapshot zone: a legacy
; map only, src/topo_dhgr.s tp_save drops them); scene_drawn = $83. The turn
; (game.s animal_unpan) puts them back, the view scrolls and only the new
; columns and the animal are drawn: the same pixels as a full redraw.
; AB_J0, AB_N (LOWTEXT) come from PROJECT module_animal.
AB_BUF  = $D000                 ; auxiliary language card, bank 1
AB_MAXN = 21                    ; 160 * 2 * 22 bytes stay below $EC00 (72 columns)
ABZ     = $F0                   ; auxiliary zero page: the screen, AB_BUF
.assert AB_BUF + 160 * 2 * (AB_MAXN + 1) <= $EC00, error, "AB_BUF passes TP_SNAP_END"
; module_animal_bg -- (ANIMAL_RUN) keep the background, but on a native
; map (its atlas fills the area: turns redraw the view).
module_animal_bg:
        lda     MAP+37
        bne     ab_rts
        lda     #$83            ; turn_view: put it back and scroll
        sta     scene_drawn
        lda     #ABZ            ; from (ABZ), the screen, to (ABZ + 2)
        .byte   $2C             ; (BIT abs: skips the next LDA)
; module_animal_unbg -- (game.s animal_unpan) the background back on screen.
module_animal_unbg:
        lda     #ABZ+2          ; from AB_BUF to the screen
; ab_copy -- A = the source pointer of ab_bank. ALTZP selects the auxiliary
; zero page, stack and language card (no main zero page until ALTZPOFF:
; hgr_row's hp is auxiliary too, as in tp_save).
ab_copy:
        sta     ab_ld+1
        eor     #ABZ ^ (ABZ+2)
        sta     ab_st+1
        php
        sei
        sta     ALTZPON
        bit     LCBANK1         ; twice: read and write RAM bank 1
        bit     LCBANK1
        lda     #<AB_BUF
        sta     ABZ+2
        lda     #>AB_BUF
        sta     ABZ+3
        ldx     #16
@row:   jsr     hgr_row
        lda     hp
        clc
        adc     AB_J0
        sta     ABZ
        lda     hp+1
        sta     ABZ+1
        sta     PAGE2_AUX
        jsr     ab_bank
        sta     PAGE2_MAIN
        jsr     ab_bank
        inx
        cpx     #176
        bne     @row
        bit     LCROM
        sta     ALTZPOFF
        plp
ab_rts: rts
; ab_bank -- AB_N + 1 bytes of the row, one bank; AB_BUF moves on.
ab_bank:
        ldy     AB_N
ab_ld:  lda     (ABZ),y
ab_st:  sta     (ABZ+2),y
        dey
        bpl     ab_ld
        sec
        lda     AB_N
        adc     ABZ+2
        sta     ABZ+2
        bcc     :+
        inc     ABZ+3
:       rts
