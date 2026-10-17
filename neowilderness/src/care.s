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
; MAKE SPLINT (lot 3, src/craft.s) leaves it on the ground of its cell
; (cr_cx/cr_cy + 2); carried (2, 3) it is put on as well.
care_splint:
        jsr     med_splint_here
        jcc     care_missing
        lda     #1
        sta     splint_place
        sta     medical_actions+2
        lda     #30
        jmp     medical_spend_effort

; Shared read-only presence predicate, with the native ground-cell rule.
med_splint_here:
        lda     splint_place
        cmp     #$FF
        beq     @no
        cmp     #0
        bne     @yes
        lda     px+1
        cmp     cr_cx+2
        bne     @no
        lda     py+1
        cmp     cr_cy+2
        bne     @no
@yes:   sec
        rts
@no:    clc
        rts

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
        ldy     #1              ; real command expires a tool left on another cell
med_tool_check:                  ; Y = 0: read-only query, including stale flags
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
@lost:  tya
        beq     @no
        lda     #0
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
        jmp     care_percent
@warm:  lda     #100
        rts

; Same conversion as al_percent, but ALERTS is not loaded over MEDVIEW.
care_percent:
        jsr     clamp0
        jsr     $EA39
        jsr     $EA39
        jsr     AYINT
        lda     $A0
        bne     @full
        lda     $A1
        cmp     #101
        bcc     @done
@full:  lda     #100
@done:  rts

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
care_minutes: .byte 0
care_consumed: .byte 0
.pushseg
.segment "LOWCODE"
care_use_minutes: .byte 30,30,0,0,0,30,0,0,15,0,0
.popseg

; ----------------------------------------------------------------------------
; STATUS's care (src/status.s module_status, docs/MENUS.md 5): the
; treatment gestures of the focused condition, here rather than in the STATUS
; module (its store is the short one); the page loads this module when the
; focus reaches a condition. The STATUS module stays in the SIM window: its
; routines and state are called directly.
.segment "MEDVIEW"
; med_foot -- row 23: the gestures of the focused condition (the chosen one,
; pg_g, in inverse), then "ESC: VIEW"; pg_gn = their count.
med_foot:
        jmp     med_foot_x       ; active XL edition
med_foot_gest = *
        jsr     med_gest_at
        ldx     #0
@gest:  stx     pg_i
        cpx     pg_g
        bne     :+
        lda     #$3F
        sta     INVFLG
:       sty     pg_x
        lda     med_gest,y
        jsr     med_word
        jsr     print_str_ay
        lda     #$FF
        sta     INVFLG
        lda     #' '|$80
        jsr     COUT
        jsr     COUT
        ldy     pg_x
        iny
        ldx     pg_i
        inx
        cpx     pg_gn
        bcc     @gest
        XL_IMM  XI_MEDVIEW, 69, @x41
        lda     #64
        jsr     tab
        jsr     puts
med_esc_text = *
        .byte   "ESC: VIEW", 0
        XL_TEXT XI_MEDVIEW, med_esc_text, " ESC VIEW"   ; (XL: at 70)
        rts

; med_gest_at -- Y = the first gesture of the focused condition in med_gest,
; pg_gn = how many it has (1 to 3).
med_gest_at:
        ldx     pg_focus
        lda     pg_act-1,x
        sta     pg_x
        asl     a
        adc     pg_x
        tay
        ldx     #0
:       lda     med_gest,y
        beq     :+
        iny
        inx
        cpx     #3
        bcc     :-
:       stx     pg_gn
        tya
        sec
        sbc     pg_gn
        tay
        rts

; med_word -- A = gesture (1..), or MG_KNIFE..MG_FLASH: A/Y = its text.
med_word:
        tax
        lda     mg_offset-1,x
        pha
        lda     mg_bank-1,x
med_bank_word:
        jsr     text_fetch
        pla
        clc
        adc     #<tb_buf
        ldy     #>tb_buf
        bcc     :+
        iny
:       rts

; med_run -- RETURN: the gesture typed (pages.s pg_type); CUT BODY without a
; blade in use, the FRSTAID KIT in the dark: USE KNIFE (AXE) or USE
; FLASHLIGHT typed first, the gesture queued after it (src/grid.s).
med_run:
        jsr     sr_prepare
        jsr     med_gest_at
        tya
        clc
        adc     pg_g
        tay
        lda     med_gest,y
        sta     pg_x            ; the gesture
        cmp     #MG_CUT
        bne     @kit
        ldy     #0              ; same current-cell/access predicate as CUT
        jsr     med_tool_check
        bcs     @type
        ldy     #S_KNIFE
        ldx     #59
        jsr     have
        lda     #MG_KNIFE
        bcs     @queue
        dey                     ; S_AXE
        ldx     #58
        jsr     have
        lda     #MG_AXE
        bcc     @type
@queue: sty     mq_list
        pha                     ; the word typed first
        ldy     #S_CUT
        lda     pg_x
        cmp     #MG_CUT
        beq     :+
        ldy     #S_KIT
:       sty     mq_list+1
        lda     #S_CARE_RETURN
        sta     mq_list+2
        lda     #3
        sta     mq_n
        lsr     a
        sta     mq_i
        lda     journey_encounters
        sta     mq_enc
        pla
        bne     @word
@kit:   cmp     #MG_KIT         ; FRSTAID KIT in the dark: the flashlight
        bne     @type
        lda     light
        bne     @type
        ldx     #66
        jsr     have
        bcc     @type
        ldy     #S_FLASH
        lda     #MG_FLASH
        bne     @queue
@type:  lda     pg_x
@word:  jsr     med_word
        sta     gp2
        sty     gp2+1
        jmp     pg_type
; Gestures per condition (0: none): the care selectors of src/medical.s
; med_treat1-3 that the port's commands set (src/care.s, camp.s).
MG_CUT   = 11
MG_KIT   = 13
MG_KNIFE = 17
MG_AXE   = 18
MG_FLASH = 19
med_gest:
        .byte   1, 2, 0         ; SEVERE CUTS: STOP BLEEDING, USE PRESSURE
        .byte   3, 0, 0         ; BROKEN ARM: USE SPLINT
        .byte   3, 0, 0         ; BROKEN LEG
        .byte   4, 5, 0         ; SHOCK: LOWER HEAD, DRINK WATER
        .byte   5, 6, 0         ; SUNBURN: DRINK WATER, WET BODY
        .byte   7, 8, 0         ; SNOWBLINDNESS: USE SUNGLASSES, SHIELD EYES
        .byte   9, 0, 0         ; FROSTBITE: USE FIRE
        .byte   10, 11, 12      ; POISON BITE: USE SNAKEBT KIT, CUT BODY, SUCK VENOM
        .byte   13, 0, 0        ; INFECTION: USE FRSTAID KIT
        .byte   14, 0, 0        ; SALT DEFICIENCY: USE SALT TAB
        .byte   5, 0, 0         ; FOOD POISONING: DRINK WATER
        .byte   15, 0, 0        ; GIARDIA: USE FLAGYL
        .byte   16, 0, 0        ; MALARIA: USE QUININE
mg_bank: .byte pg_med_a,pg_med_a,pg_med_a,pg_med_b,pg_med_b,om_need_light,om_need_light,om_need_light,om_need_light,om_need_light,om_need_light,om_need_light,om_light_ready,om_light_ready,om_light_ready,om_light_ready,om_light_ready,pg_med_a,om_light_ready
mg_offset: .byte 72,86,99,87,98,37,46,61,73,82,98,107,41,57,70,81,93,110,103
.pushseg
.segment "STATUS"
med_hint_bank: .byte om_doses_label,om_doses_label,om_doses_label,om_can_free,om_can_free,om_can_free,om_can_free,om_can_free,om_can_free,om_can_free,om_sample,om_sample,om_sample,om_can_free,om_can_free,om_can_free
med_hint_offset: .byte 80,80,95,10,28,42,64,78,99,64,22,52,73,64,64,64
.popseg
.pushseg
.segment "STATUS"
med_times: .byte 30,30,30,0,0,0,0,0,0,30,0,15,30,0,0,0
.popseg

; NeoWildernessXL footer: resident prefix, then the gestures in MEDVIEW.
; MEDVX now holds the OBJECTS legend at $5FE0.
.segment "GCODE"
med_foot_x:
        jsr     med_preview
        lda     #23
        jsr     vtab
        jmp     med_foot_prefix
.segment "TEXT"
med_foot_prefix:
        jsr     mt_puts
        .byte   " ", MS_LEFT, MS_RIGHT, " ", 0
        jmp     med_foot_gest
.segment "MEDVIEW"

; Informational only: no care flags, inventory, clock or RNG writes.
med_preview:
        lda     #22
        jsr     vtab
        jsr     med_gest_at
        tya
        clc
        adc     pg_g
        tay
        lda     med_gest,y
        sta     med_selected
        tax
        lda     med_times-1,x
        jsr     pdec
        jsr     puts
        .byte   " MIN; ",0
        ldx     med_selected
        jsr     med_hint_word
        jsr     print_str_ay
        ldx     med_selected
        lda     med_items-1,x
        beq     @done
        tax
        stx     med_item
        jsr     med_have
        bcs     @here
        jsr     puts
        .byte   "; NOT HERE",0
        rts
@here:  jsr     puts
        .byte   "; HERE",0
        ldx     med_item
        cpx     #43             ; sunglasses have no dose counter
        beq     @done
        cpx     #52             ; fire and splint have no dose counter either
        bcs     @done
        jsr     puts
        .byte   "; DOSES ",0
        ldx     med_item
        lda     it_pack_lo,x
        sta     num
        lda     it_pack_hi,x
        bpl     :+
        lda     #0
        sta     num
:       sta     num+1
        jsr     print_u16
        lda     med_selected
        cmp     #MG_KIT
        bne     @done
        lda     light
        beq     @dark
        jsr     puts
        .byte   "; LIT",0
        rts
@dark:  jsr     puts
        .byte   "; DARK",0
@done:  rts
.pushseg
.segment "STATUS"
med_items: .byte 0,0,93,0,0,0,43,0,88,42,0,0,41,48,47,50
med_have:
        cpx     #93
        beq     @splint
        cpx     #88
        bne     @item
        lda     fire_on
        cmp     #1
        rts
@splint:jmp     med_splint_here
@item:  jmp     have
.popseg
med_selected = overlay_text+72
med_item = overlay_text+73
.pushseg
.segment "STATUS"
med_hint_word:
        cpx     #5              ; DRINK WATER
        beq     med_water_word
        cpx     #6              ; WET BODY
        beq     med_water_word
        cpx     #MG_CUT
        beq     med_blade_word
        lda     med_hint_offset-1,x
        pha
        lda     med_hint_bank-1,x
        jmp     med_bank_word
.segment "STATUS"
med_blade_word:
        ldy     #0
        jsr     med_tool_check
        bcs     @active
        ldx     #59             ; preparation uses KNIFE before AXE
        jsr     have
        bcs     @prepare
        dex
        jsr     have
        bcs     @prepare
        lda     #61
        bne     @word
@active:lda     #11
        bne     @word
@prepare:
        lda     #24
@word:  pha
        lda     #om_object_label
        jmp     med_bank_word

.popseg

.pushseg
.segment "STATUS"
med_water_word:
        cpx     #6
        bne     @drink
        lda     weather_inside_front
        bne     @wet
        lda     wet_mode
        cmp     #2
        beq     @wet
        jsr     med_water_near
        bcs     @near
@drink: ldx     #N_WATER
        jsr     have
        bcs     @stock
        jsr     med_water_near
        bcs     @near
        lda     #30
        bne     @word
@stock: lda     #4
        bne     @word
@near:  lda     #56
        bne     @word
@wet:   lda     #72
@word:  pha
        lda     #om_to_use
        jmp     med_bank_word
.popseg
