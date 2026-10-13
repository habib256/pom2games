; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Medical commands share WILDMVI with their status page. The resident
; completion loads WILDMED before applying care or advancing the clock.
.segment "MEDVIEW"
module_medical_command:
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
        lda     noun
        cmp     #53
        bne     :+
        lda     verb
        cmp     #V_USE
        jne     care_invalid
        ldx     #53
        jsr     have
        jcc     care_missing
        lda     #3              ; USE COMPASS puts the direction aid in hand
        sta     it_place+53
        jsr     load_totals
        jmp     care_ok
:       lda     noun
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
        cpx     #43
        bcs     :+
        lda     #3              ; a used medical kit is held, like the compass
        sta     it_place,x
        jsr     load_totals
        ldx     noun
:       lda     care_use_minutes-41,x
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
care_use_instead:
        lda     #<care_use_message
        ldx     #>care_use_message
        jmp     message
care_invalid:
        lda     #<care_invalid_message
        ldx     #>care_invalid_message
        jmp     message
care_unsupported:
        lda     #<m_notyet
        ldx     #>m_notyet
        jmp     message
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
