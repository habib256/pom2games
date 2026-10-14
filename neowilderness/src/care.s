; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Medical commands share WILDMVI with their status page. The resident
; completion loads WILDMED before applying care or advancing the clock.
.segment "MEDVIEW"
module_medical_command:
        ; Lot 13: the care verbs of T15/S0A and T12/S08 come first (WET BODY
        ; may carry an inline quantity, see care_wet).
        lda     verb
        cmp     #13             ; DRY, WARM
        jeq     care_dry
        cmp     #14             ; COOL
        jeq     care_cut
        cmp     #31             ; CUT
        jeq     care_cut
        cmp     #33             ; WET
        jeq     care_wet
        cmp     #V_HANG
        jeq     care_hang
        ; EAT/DRINK can arrive here through the numeric food parser, but
        ; medical actions consume one use and have no ounce/time argument.
        ; Refuse before changing doses, action flags or treatment state.
        lda     input_argument
        beq     :+
        lda     #<care_argument_message
        ldx     #>care_argument_message
        jmp     message
:
        lda     #0
        sta     care_minutes
        lda     verb
        cmp     #26             ; STOP BLEEDING
        bne     @shield
        lda     noun
        cmp     #159
        jne     care_unsupported
        ldx     #0              ; selector 1, compression
        lda     #30
        sta     care_minutes
        jmp     care_apply
@shield:
        cmp     #30             ; SHIELD EYES: native T15/S0A
        bne     @lower
        lda     noun
        cmp     #160
        jne     care_invalid
        ldx     #9              ; selector 10, no time spent
        jmp     care_apply
@lower: cmp     #29             ; LOWER HEAD, or existing backpack retrieval
        bne     @suck
        lda     noun
        cmp     #163
        beq     :+
        jmp     do_tree
:       ldx     #3              ; selector 4, shock prerequisite
        jmp     care_apply
@suck:  cmp     #32             ; SUCK VENOM requires an active poison bite
        bne     @medicine
        lda     noun
        cmp     #161
        jne     care_invalid
        lda     injury_active+7
        jeq     care_invalid
        ldx     #22             ; selector 23, 15 minutes
        lda     #15
        sta     care_minutes
        jmp     care_apply
@medicine:
        lda     verb
        cmp     #V_USE
        bne     @compass
        lda     noun
        cmp     #162            ; PRESSURE: core $527B, selector 2, 30 minutes
        jeq     care_pressure
        cmp     #93             ; SPLINT: T11/S00 $5B80
        jeq     care_splint
        cmp     #58             ; AXE, KNIFE: T11/S00 $5C42
        jeq     care_tool
        cmp     #59
        jeq     care_tool
@compass:
        lda     noun
        cmp     #53             ; COMPASS with a care verb (USE COMPASS:
        jeq     care_invalid    ; orient_use, src/orient.s)
        lda     noun
        cmp     #41
        jcc     care_unsupported
        cmp     #52
        jcs     care_unsupported
        tax
        jsr     have
        jcc     care_missing
        lda     verb
        cmp     #V_USE
        beq     @use
        ; Native T12/S08: oral medicines are 47,48,50. Oxygen is
        ; applied with USE; kits, glasses and creams are never swallowed.
        lda     noun
        cmp     #49
        jeq     care_use_instead
        cmp     #51
        jeq     care_use_instead
        cmp     #47
        jcc     care_use_instead
@use:   ldx     noun
        cpx     #41             ; FIRSTAID KIT needs light (T11/S00 $5BAE, lot 2)
        bne     :+
        lda     light
        bne     :+
        lda     #<c_m53
        ldx     #>c_m53
        jmp     message
:       ; Automatic placement: T11/S00 $5BCF continues with CARRY (WEAR for
        ; the sunglasses, 43); T12/S08 $58D1 with CARRY for oral doses.
        lda     #3
        cpx     #43
        bne     :+
        lda     #1
:       sta     it_place,x
        jsr     load_totals
        ldx     noun
        lda     care_use_minutes-41,x
        sta     care_minutes
        jsr     module_care_dose
        ; Native empty-use behavior is verified separately from the care
        ; matrix: this flag reports whether a positive dose was consumed.
        txa
        sec
        sbc     #31
        tax
care_apply:
        lda     #1
        sta     medical_actions,x
        cpx     #18
        bne     :+
        lda     care_consumed   ; native oxygen uses B2, not the care selector
        sta     oxygen_active
:       lda     care_minutes
        jmp     medical_spend

; X = item. Native T0E/S02 $5DC7 consumes a use only from a positive
; signed word, preserving zero/negative words instead of wrapping them.
; Kits with zero W8 and glasses still have their native reusable effects.
module_care_dose:
        lda     #0
        sta     care_consumed
        lda     it_pack_hi,x
        bmi     @done
        ora     it_pack_lo,x
        beq     @done
        lda     it_pack_lo,x
        bne     :+
        dec     it_pack_hi,x
:       dec     it_pack_lo,x
        inc     care_consumed
@done:  rts
care_missing:
        jmp     no_item

; ----------------------------------------------------------------------------
; Lot 13: care commands of T11/S00, T12/S08 and T15/S0A (docs/IMPLEMENTATION.md,
; "Soins, alertes et maladies (lot 13)").

; USE PRESSURE: the core's second cut treatment (selector 2), 30 minutes.
care_pressure:
        lda     #30
        sta     care_minutes
        ldx     #1
        jmp     care_apply

; USE SPLINT: selector 3, the splint worn, W7 30 minutes at .02 x weight.
; The second item set (crafted splint) is lot 3: splint_place is its hook.
care_splint:
        lda     splint_place
        cmp     #$FF
        jeq     care_missing
        lda     #1
        sta     splint_place
        sta     medical_actions+2
        lda     #30
        jmp     medical_spend_effort

; USE AXE / USE KNIFE: in use (B2) on this square, carried, no time.
care_tool:
        ldx     noun
        jsr     have
        jcc     care_missing
        ldx     noun
        lda     #3
        sta     it_place,x
        lda     px+1
        sta     care_tool_x
        lda     py+1
        sta     care_tool_y
        lda     noun
        sec
        sbc     #57             ; 1 AXE, 2 KNIFE
        ora     care_tools
        sta     care_tools
        jsr     load_totals
        jmp     care_ok

; C set when an AXE or KNIFE put in use on this square is still accessible.
; The kits never qualify: T0A/S05 $58C4 clears their B2 at the first step of
; the timed USE that set it.
care_tool_in_use:
        lda     px+1
        cmp     care_tool_x
        bne     @lost
        lda     py+1
        cmp     care_tool_y
        bne     @lost
        lda     care_tools
        lsr     a
        bcc     @knife
        ldx     #58
        jsr     have
        bcs     @done
@knife: lda     care_tools
        and     #2
        beq     @no
        ldx     #59
        jmp     have
@lost:  lda     #0
        sta     care_tools
@no:    clc
@done:  rts

; COOL and CUT share T12/S08 selector 14 ($5833): BODY with a tool in use
; gives care selector 7 (poison bite) without time.
care_cut:
        jsr     care_family
        cmp     #4
        bcs     :+
        lda     #<care_whatever_message ; message 18
        ldx     #>care_whatever_message
        jmp     message
:       cmp     #10
        bcs     @high
        lda     verb
        cmp     #14
        jeq     care_invalid    ; COOL: message 2
        lda     #<care_unwise_message   ; CUT: message 39
        ldx     #>care_unwise_message
        jmp     message
@high:  cmp     #15
        beq     @body
        cmp     #11
        bne     @core
        lda     verb            ; game: COOL message 17, CUT the hunting module
        cmp     #14
        jne     care_unsupported
@specific:
        lda     #<care_specific_message
        ldx     #>care_specific_message
        jmp     message
@core:  cmp     #13             ; core refusals (not probed): themes 17, others 2
        beq     @specific
        jmp     care_invalid
@body:  lda     noun
        cmp     #158            ; BODY
        jne     care_invalid
        jsr     care_tool_in_use
        bcs     :+
        lda     #<care_item_message     ; message 25
        ldx     #>care_item_message
        jmp     message
:       lda     #0
        sta     care_minutes
        ldx     #6              ; selector 7
        jmp     care_apply

; DRY / WARM (T15/S0A -> T12/S08 $58D8): clothing only; dry clothes need a
; hypothermia percentage under 86, then message 117 (118 for a shelter).
care_dry:
        jsr     care_family
        cmp     #1
        jne     care_invalid
        jsr     care_present
        jcc     care_missing
        lda     wet_mode
        bne     @hang
        jsr     care_hypothermia
        cmp     #86
        jcs     care_invalid
@hang:  lda     noun
        cmp     #95
        bcs     @party
        lda     #<care_dry_message
        ldx     #>care_dry_message
        jmp     message
@party: lda     #<care_party_message
        ldx     #>care_party_message
        jmp     message

; A = INT(100 x thermal factor) on the cold side ($48AC), else 100.
care_hypothermia:
        fld     s_body
        fop     FCOMP, f_body
        cmp     #$FF
        bne     @warm
        fld     s_therm_factor
        jmp     al_percent
@warm:  lda     #100
        rts

; HANG clothing (T12/S08 $58F9): a tree, then wet clothes outside the rain;
; the Sun or a fire dries them ($4B70 = 0); the item is dropped (DROP).
; FOOD, the BACKPACK alias and other nouns keep the tree module.
care_hang:
        jsr     care_family
        cmp     #1
        bne     @tree
        lda     noun
        cmp     #21
        bne     :+
@tree:  jmp     do_tree
:       jsr     care_present
        jcc     care_missing
        jsr     care_tree_here
        bcs     :+
        lda     #<care_tree_message     ; message 16
        ldx     #>care_tree_message
        jmp     message
:       lda     noun
        cmp     #95
        bcc     :+
        lda     #<care_far_message      ; message 21
        ldx     #>care_far_message
        jmp     message
:       lda     wet_mode
        beq     @think
        lda     weather_sky
        cmp     #2
        bcc     :+
@think: lda     #<care_think_message    ; message 49
        ldx     #>care_think_message
        jmp     message
:       jsr     care_dry_source
        bcc     @drop
        lda     #0
        sta     wet_mode
@drop:  ldx     noun
        lda     #0
        sta     it_place,x
        lda     px+1
        sta     it_x,x
        lda     py+1
        sta     it_y,x
        jsr     load_totals
        jmp     care_ok

; C set by the Sun ($4B49 = 1: sunrise to sunset) or a fire.
care_dry_source:
        fld     s_hour
        fop     FCOMP, s_rise
        cmp     #$FF
        beq     care_fire_here
        fld     s_hour
        fop     FCOMP, s_set
        cmp     #$FF
        bne     care_fire_here
        sec
        rts
; Lot 2 hook: C set when a fire burns on this square (original second set
; B1[13] = 0, $45CD). There is no fire yet.
care_fire_here:
        clc
        rts

; The tree test of the TREE module (unreachable from this window).
care_tree_here:
        lda     shelter_inside
        bne     @no
        jsr     woods_here
        bcc     @no
        jsr     level_here
        clc
        adc     M_BASE
        sta     care_level
        lda     MAP+27
        bne     :+
        lda     #110
:       cmp     care_level
        beq     @no
        bcc     @no
        sec
        rts
@no:    clc
        rts

; WET BODY (T15/S0A $584C): during a weather front or in a river or lake the
; body is already wet (message 11, selector 9); otherwise the water module:
; river or lake water at hand, else ounces poured from the canteen.
care_wet:
        lda     noun
        cmp     #158
        jne     care_invalid
        lda     weather_inside_front
        bne     @already
        lda     wet_mode
        cmp     #2
        beq     @already
        jsr     care_water_near
        bcs     @wet
        ldx     #N_WATER
        jsr     have
        bcc     @none
        jsr     care_quantity   ; reloads this window: keep no state here
        bcs     @cancel
        lda     msgnum+1
        cmp     stock_available+1
        bcc     @pour
        bne     @exceed
        lda     stock_available
        cmp     msgnum
        bcs     @pour
@exceed:
        lda     #<care_exceed_message   ; message 64
        ldx     #>care_exceed_message
        jmp     message
@pour:  ldx     #N_WATER
        jsr     take_oz
        jsr     load_totals
@wet:   lda     #0
        sta     care_minutes
        ldx     #8              ; selector 9
        jmp     care_apply
@already:
        lda     #1
        sta     medical_actions+8
        lda     #<care_already_message  ; message 11 (resident: MED replaces this window)
        ldx     #>care_already_message
        jmp     care_message_apply
@none:  lda     #<care_nowater_message
        ldx     #>care_nowater_message
        jmp     message
@cancel:
        rts

; C set when the item named exists: the first set (1..75), or the splint.
care_present:
        ldx     noun
        cpx     #76
        bcs     :+
        jmp     have
:       cpx     #93
        bne     @no
        lda     splint_place
        cmp     #$FF
        beq     @no
        sec
        rts
@no:    clc
        rts

; A = original noun family of `noun` (parser.md, $528E-$5408).
care_family:
        ldx     #0
        lda     noun
@find:  cmp     care_family_top,x
        bcc     @found
        beq     @found
        inx
        bne     @find
@found: lda     care_family_id,x
        rts
care_family_top: .byte 0,21,22,37,40,51,56,59,63,75,81,86,88,92,93,97,100,109,134,144,157,165,168,171,255
care_family_id:  .byte 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,11, 3, 4, 7, 5, 1,12, 0,10,13,14,15,16, 2,17
care_level: .byte 0
care_dry_message: .byte "HANG YOUR ^ TO WARM BY THE SUN|OR BY A FIRE.",0
care_tree_message: .byte "YOU ARE NOT NEAR A TREE.",0
care_far_message: .byte "YOUR POWERS DON'T EXTEND THAT FAR.",0
care_think_message: .byte "THINK.",0
care_whatever_message: .byte "WHATEVER TURNS YOU ON.",0
care_unwise_message: .byte "THAT'S NOT VERY WISE.",0
care_specific_message: .byte "TRY TO BE MORE SPECIFIC.",0
; The longer texts stay resident (WILDERNESS): they would otherwise cost the
; auxiliary module stock, full with a large native atlas.
.segment "RODATA"
.segment "MEDVIEW"
care_use_instead:
        lda     #<care_use_message
        ldx     #>care_use_message
        jmp     message
care_invalid:
        lda     #<care_invalid_message
        ldx     #>care_invalid_message
        jmp     message
care_unsupported:
        jmp     camp_command    ; fire, light, stove... (src/camp.s)
care_ok:
        lda     #<m_ok
        ldx     #>m_ok
        jmp     message
care_use_message: .byte "PLEASE USE 'USE'.",0
care_argument_message: .byte "MEDICINES USE ONE DOSE AT A TIME.|OMIT THE NUMBER AND UNIT.",0
care_invalid_message: .byte "THAT ACTION DOES NOT APPLY HERE.",0
care_minutes: .byte 0
care_consumed: .byte 0
care_use_minutes: .byte 30,30,0,0,0,30,0,0,15,0,0
