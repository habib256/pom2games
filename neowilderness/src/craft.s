; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; craft.s -- lot 3, step 1: the MAKE recipes of the original (docs/CRAFT.md)
; ============================================================================
; The CRAFT module, directory entry 9 (free since the hut left the store),
; read from NEOWILD.BLK into the SIM window on both editions by CAMP
; (src/camp.s camp_craft), which computes first what the module cannot (the
; ground class, the snow line: SIM) and spends its time afterwards (effort,
; camp_done). It runs at $9600 with SIM away and calls resident code only.
;   MAKE (T05/S00 $551E, then T10/S00):
;     HUT, IGLOO, TRENCH  $599C: 4000 k / ((light + 2)(axe + 2) health) min
;     CLUB                $5B54: 60 / SQR(health)
;     SPEAR, AXE, BOW     $5BAA: 600 / (SQR(health)(3 knife + 1)), BOW
;                         x 4 / (light + 1); rope or gear outside Burma,
;                         New Guinea, Bolivia (msg 4)
;     SPLINT              $5A65: 300 / (SQR(health)(light + 1)(knife + 1))
;     SUNGLASSES, SUNSCREEN  $5A86: bark shades, mud, 30 minutes
;     HIDE                msg 35 or 101; the other nouns: msg 2, 11, 17, 21
;     clothes, tent and pack from hide ($584A), ROPE, RAFT, CANTEEN... (T10/S05):
;     lot 5, "NOT IN THIS VERSION YET."
;   USE HUT, IGLOO, TRENCH ($58BD), TENT ($58E4), BOW, SPEAR, CLUB, ROCK
;   ($5C42)
;   GET, PACK, CARRY, DROP, REMOVE, WEAR of BOW, SPEAR, CLUB, ROCK, SPLINT
;   (the transaction T0E/S02, measured in the real game: GET and CARRY put
;   it in hand; the SPLINT worn sets care selector 3, taken off clears it):
;   from ITEMS (src/game.s item_noun)
;   the CRAFT page (lot 3 step 2, craft_page at the end): the recipes and
;   their ingredients here, RETURN types MAKE x
; No draw: the original's MAKE has none.
;
; Resident state (LOWPAGE and WILDERNESS, saved by SAVE: src/save.s
; sv_ranges):
;   cr_b1   b1[14..18] of BOW, SPEAR, CLUB, ROCK, SPLINT (splint_place): $FF
;           none, 0 on the ground, 1 worn (the SPLINT), 2 in the pack, 3 in
;           hand (the second set weighs nothing in the port, as the piles of
;           lot 4); their "in use" B2 are bits of fg_use (FT_BOW, FT_SPEAR,
;           FT_CLUB for the CLUB or the ROCK, means 17: time and leaving the
;           cell clear them)
;   cr_cx, cr_cy  (WILDERNESS) the cell where the BOW, the SPEAR, the SPLINT
;           lie when on the ground: they stay there, absent elsewhere and
;           found again on the way back (T0C/S0B $596E keeps b3/b4, T0A/S00
;           $5BD0 finds them, docs/CRAFT.md 3.3)
;   cr_still  0 once the player has left the cell (forage_here): the CLUB on
;           the ground is lost, and a ROCK not carried lies on every land
;           cell (T0D/S00 $585F: $4B56 < 3); cr_here settles it, then 1
;   cr_sx, cr_sy  the cells of the HUT, the IGLOO, the TRENCH ($FF: none);
;           a shelter stays where it was made, as b1/b3/b4 of the original
;           (one of each kind)
; ============================================================================
CRAFT_MODULE = 9                ; directory entry (tools/build_disk.py MODULES;
                                ; src/pages.s pg_craft writes its length)
CRAFT_RUN    = $9600            ; src/wild.cfg CRAFTM: the SIM window
FT_BOW   = 4                    ; fg_use: B2 of BOW, SPEAR, CLUB (b2[14..16])
FT_SPEAR = 8
FT_CLUB  = 16
N_TENT   = 9
N_AXE    = 58
N_ROPE   = 60
N_GEAR   = 67
N_BOW    = 89
N_SPLINT = 93
N_HIDE   = 94
N_HUT    = 95
N_IGLOO  = 96

.segment "LOWPAGE"
craft_state:
cr_b1:  .byte   $FF, $FF, $FF   ; BOW, SPEAR, CLUB
        .byte   0               ; ROCK: the stone of the start cell (b1[17] = 0)
splint_place: .byte $FF         ; SPLINT (lot 13: USE SPLINT wears it, 1)
cr_still: .byte 1               ; 0: the player has left the cell (forage_here)
cr_sx:  .byte   $FF, $FF, $FF   ; HUT, IGLOO, TRENCH (nouns 95..97)
cr_sy:  .byte   $FF, $FF, $FF
craft_state_end:
.export craft_state, craft_state_end, cr_b1, splint_place, cr_still, cr_sx, cr_sy

.segment "DATA"                 ; WILDERNESS: LOWPAGE is full (docs/MEMORY.md 22)
craft_cells:
cr_cx:  .byte   $FF, $FF, $FF   ; BOW, SPEAR, SPLINT: b3/b4, their cell on
cr_cy:  .byte   $FF, $FF, $FF   ; the ground
craft_cells_end:
.export craft_cells, craft_cells_end, cr_cx, cr_cy

.segment "CRAFT"
craft_main:
        jsr     cr_here
        lda     verb
        cmp     #3
        jeq     cr_make
        cmp     #2
        jne     cr_items        ; GET, PACK, CARRY, DROP, WEAR (from ITEMS)
        ldx     noun            ; USE (camp_use_more: 9, 89..92, 95..97)
        cpx     #N_TENT
        jeq     cr_use_tent
        cpx     #N_HUT
        jcs     cr_use_shelter
; USE BOW, SPEAR, CLUB, ROCK (T11/S00 $5C42): b2 = 1, then CARRY: in the
; hand. The ROCK's b2 counts as the CLUB's (both are means 17, cleared
; together: T0F/S07 $590F).
        jsr     cr_item
        sta     cr_n
        cmp     #$FF
        jeq     cr_m1
        lda     cr_ft,x         ; in use, even when the hand cannot take it
        ora     fg_use          ; (the original: msg 7, the weapon stays)
        sta     fg_use
        lda     #3
        jsr     cr_load
        bcs     cr_heavy
        sta     cr_b1,x
        jmp     cr_ok
cr_heavy:
        stx     cr_report_item
        lda     #0
        sta     cr_report_pass
        lda     #cr_refused
        ldx     #0
        jsr     message
        inc     camp_said
@part:  ldx     cr_report_item
        ldy     #0
        lda     cr_report_pass
        bne     @volume
        lda     cr_w,x
        jmp     @need
@volume:
        ldy     cr_ld
        lda     cr_v,x
@need:  sta     msgnum
        lda     #0
        sta     msgnum+1
        sty     cr_report_slot
        sec
        lda     load_limits,y
        sbc     load_used,y
        sta     stock_available
        lda     load_limits+1,y
        sbc     load_used+1,y
        sta     stock_available+1
        bcs     :+
        lda     #0
        sta     stock_available
        sta     stock_available+1
:       lda     stock_available
        cmp     msgnum
        lda     stock_available+1
        sbc     #0
        bcs     @next
        jsr     msg_newline
        lda     cr_report_slot
        lsr     a
        tax
        lda     cr_report_texts,x
        jsr     text_fetch
        sta     gp1
        stx     gp1+1
        jsr     message_body
@next:  inc     cr_report_pass
        lda     cr_report_pass
        cmp     #2
        bcc     @part
        rts
cr_report_texts: .byte cr_weight,cr_wear,cr_pack,cr_hands
cr_report_item: .byte 0
cr_report_pass: .byte 0
cr_report_slot: .byte 0
cr_ft:  .byte   FT_BOW, FT_SPEAR, FT_CLUB, FT_CLUB

; ---------------------------------------------------------------------------
; MAKE: the core's answers by noun family (T05/S00 $551E: present -> msg 11,
; the SPLINT msg 10), then T10/S00.
; ---------------------------------------------------------------------------
cr_make:
        ldx     noun
        ldy     #0
:       txa
        cmp     cr_top,y
        bcc     :+
        beq     :+
        iny
        bne     :-
:       lda     cr_go_hi,y
        pha
        lda     cr_go_lo,y
        pha
        rts
; The families, by the last noun of each range (WATER, 38..40, STICKS and
; FIRE never come here: CAMP's); 172..177 (TREE, SHADOW, BAIT: the core's
; USE, selector 17) and the words past the animals: not yet; the regional
; animals (the core's 76..79 when absent): msg 21.
cr_top: .byte   21,  37,  51,  56,  59,  63,  75,  81,  86,  91,  92,  93,  94,  97
        .byte  100, 109, 134, 144, 165, 168, 171, 177, 199, 255
cr_go_lo:
        .byte   <(cr_clothes-1), <(cr_have21-1), <(cr_care-1), <(cr_have21-1)
        .byte   <(cr_tools-1), <(cr_ropes-1), <(cr_gear-1), <(cr_pile21-1)
        .byte   <(cr_pile21-1), <(cr_weapon-1), <(cr_rock-1), <(cr_splint-1)
        .byte   <(cr_hide-1), <(cr_shelter-1), <(cr_site-1), <(cr_notyet-1)
        .byte   <(cr_m2-1), <(cr_m17-1), <(cr_m2-1), <(cr_m17-1), <(cr_m21-1)
        .byte   <(cr_notyet-1), <(cr_m21-1), <(cr_notyet-1)
cr_go_hi:
        .byte   >(cr_clothes-1), >(cr_have21-1), >(cr_care-1), >(cr_have21-1)
        .byte   >(cr_tools-1), >(cr_ropes-1), >(cr_gear-1), >(cr_pile21-1)
        .byte   >(cr_pile21-1), >(cr_weapon-1), >(cr_rock-1), >(cr_splint-1)
        .byte   >(cr_hide-1), >(cr_shelter-1), >(cr_site-1), >(cr_notyet-1)
        .byte   >(cr_m2-1), >(cr_m17-1), >(cr_m2-1), >(cr_m17-1), >(cr_m21-1)
        .byte   >(cr_notyet-1), >(cr_m21-1), >(cr_notyet-1)

; 1..21: present msg 11, else the clothes, tent and pack from hide ($584A,
; A3): lot 5.
cr_clothes:
        jsr     cr_have
        jcs     cr_m11
cr_notyet:
        lda     #<m_notyet
        ldx     #>m_notyet
        jmp     cr_say
; 23..37, 52..56: present msg 11, else msg 21.
cr_have21:
        jsr     cr_have
        jcs     cr_m11
        jmp     cr_m21
; 57..59: GUN, KNIFE msg 21; the AXE.
cr_tools:
        jsr     cr_have
        jcs     cr_m11
        cpx     #N_AXE
        jne     cr_m21
        jmp     cr_weapon
; 60..63: ROPE and SNOWSHOES (T10/S05): lot 5; PITONS, CRAMPONS msg 21.
cr_ropes:
        jsr     cr_have
        jcs     cr_m11
        cpx     #N_ROPE
        beq     cr_notyet
        cpx     #63
        beq     cr_notyet
        jmp     cr_m21
; 64..75 (T10/S05 $5A5E): FLASHLIGHT, BINOCULARS, THERMOMETER, GOLD msg 21;
; STOVE: msg 2 with a fire here, else msg 65; the others lot 5.
cr_gear:
        jsr     cr_have
        jcs     cr_m11
        cpx     #75
        jeq     cr_m21
        cpx     #66
        jeq     cr_m21
        cpx     #68
        jeq     cr_m21
        cpx     #69
        jeq     cr_m21
        cpx     #71
        bne     cr_notyet
        lda     fire_on
        jne     cr_m2
        lda     #<w_m65
        ldx     #>w_m65
        jmp     cr_say
; 76..86: a carcass, game, fish, a wild food here (lot 4's piles) msg 11,
; else msg 21.
cr_pile21:
        lda     fg_b1-76,x
        cmp     #$FF
        jne     cr_m11
        jmp     cr_m21
; ROCK (92, family 7): on the ground of a land cell or carried, the core's
; msg 11; absent (in the water), T10/S00: msg 21 (measured: MAKE ROCK).
cr_rock:
        lda     cr_b1+3
        cmp     #$FF
        jne     cr_m11
        jmp     cr_m21
; 98..100: the airplane at the wreck, the outpost at the goal: msg 11.
cr_site:
        cpx     #98
        bne     :+
        jsr     cr_wreck
        jcs     cr_m11
        jmp     cr_m21
:       cpx     #99
        jne     cr_m21
        jsr     cr_outpost
        jcs     cr_m11
        jmp     cr_m21

; HIDE ($5827): msg 101 when there is some, else msg 35.
cr_hide:
        lda     fg_b1+FG_HIDE
        cmp     #$FF
        beq     :+
        lda     #<cr_m101
        ldx     #>cr_m101
        jmp     cr_say
:       lda     #<cr_m35
        ldx     #>cr_m35
        jmp     cr_say

; HUT, IGLOO, TRENCH ($5832, $599C): here already msg 11; in the water msg
; 92; at the wreck or the outpost msg 49 ($D9, $D8 = $7F); the HUT in the
; woods, the IGLOO on snow (msg 76). Effort .023; 4000 k / ((light + 2)
; (axe in use + 2) health) minutes, k = 1 TRENCH, 2 HUT, 3 IGLOO.
cr_shelter:
        jsr     cr_shelter_here
        jcs     cr_m11
        lda     cr_class
        cmp     #3
        bne     :+
        lda     #<cr_m92
        ldx     #>cr_m92
        jmp     cr_say
:       jsr     cr_wreck
        bcs     @think
        jsr     cr_outpost
        bcc     :+
@think: lda     #<cr_m49
        ldx     #>cr_m49
        jmp     cr_say
:       ldx     noun
        cpx     #N_HUT
        bne     :+
        lda     cr_class
        cmp     #1
        jne     cr_m76
:       cpx     #N_IGLOO
        bne     :+
        lda     cr_snow
        jeq     cr_m76
:       jsr     cr_minutes
        lda     noun
        sec
        sbc     #N_HUT
        tax
        lda     px+1
        sta     cr_sx,x
        lda     py+1
        sta     cr_sy,x
        lda     #0              ; the next view draws it (XL: site sprite,
        sta     scene_cache_valid ; src/project.s), not scene_prepare's cache
        lda     #3              ; .023
        jmp     cr_made

; CLUB, SPEAR, BOW, AXE ($5B44): in the woods (msg 76). CLUB ($5B54): .01,
; 60 / SQR(health). The others: rope or gear outside regions 3-5 (msg 4),
; .02, 600 / (SQR(health)(3 knife + 1)), the BOW x 4 / (light + 1).
cr_weapon:
        cpx     #N_AXE          ; (present: cr_tools)
        beq     :+
        jsr     cr_item         ; here or carried: msg 11
        ldx     noun
        cmp     #$FF
        jne     cr_m11
:       lda     cr_class
        cmp     #1
        jne     cr_m76
        cpx     #91             ; CLUB: .01
        beq     @time
        lda     region_number
        cmp     #3
        bcc     :+
        cmp     #6
        bcc     @time
:       jsr     cr_rope
        bcs     @time
        lda     #<cr_m4
        ldx     #>cr_m4
        jmp     cr_say
@time:  jsr     cr_minutes
        lda     #1              ; .01 the CLUB, .02 the others
        ldx     noun
        cpx     #91
        beq     @made
        lda     #2
@made:  pha
        ldx     noun
        cpx     #N_AXE
        bne     :+
        jsr     cr_ground_item
        pla
        jmp     cr_made
:       jsr     cr_item
        lda     #0              ; on the ground of this cell
        jsr     cr_put
        pla
        jmp     cr_made

; SUNGLASSES, SUNSCREEN ($5A86, $5B0A): clear ground or woods (msg 76), .01,
; the bark shades (msg 28) or the mud (msg 205), on the ground; 30 minutes.
cr_care:
        jsr     cr_have
        jcs     cr_m11
        cpx     #43
        beq     :+
        cpx     #44
        jne     cr_m21
:       lda     cr_class
        cmp     #2
        jcs     cr_m76
        jsr     cr_ground_item
        lda     #<cr_m28
        ldy     #>cr_m28
        cpx     #43
        beq     :+
        lda     #<cr_m205
        ldy     #>cr_m205
:       pha
        tya
        tax
        pla
        jsr     cr_say
        jsr     cr_minutes      ; 30
        lda     #1              ; .01
        jmp     cr_made

; SPLINT ($5A65): one already msg 10. A SPEAR, the AXE, the wreck or the
; outpost: straight to the time. Else ground class 0 or 1 (msg 76), .01, the
; woods (msg 76), rope or gear in every region (msg 4). 300 / (SQR(health)
; (light + 1)(knife + 1)) minutes; the splint on the ground.
cr_splint:
        ldx     #4
        jsr     cr_where        ; here, worn or carried: msg 10
        cmp     #$FF
        jne     cr_ok
        ldx     #1              ; a SPEAR here or carried
        jsr     cr_where
        cmp     #$FF
        bne     @time
        jsr     cr_wreck
        bcs     @time
        jsr     cr_outpost
        bcs     @time
        ldx     #N_AXE
        jsr     have
        bcs     @time
        lda     cr_class
        cmp     #2
        jcs     cr_m76
        lda     #1              ; (the effort stays: no time anyway)
        sta     cr_eff
        lda     cr_class
        cmp     #1
        jne     cr_m76
        jsr     cr_rope
        bcs     @time
        lda     #<cr_m4
        ldx     #>cr_m4
        jmp     cr_say
@time:  jsr     cr_minutes
        ldx     #4
        lda     #0              ; on the ground of this cell
        jsr     cr_put
        lda     cr_eff          ; .01 when the materials were looked for
        jmp     cr_made

; ---------------------------------------------------------------------------
; USE
; ---------------------------------------------------------------------------
; USE HUT, IGLOO, TRENCH ($58BD): here (else msg 1), inside (the IGLOO: 35 F,
; shelter_inside 2), health steps of 15 minutes, msg 9; no time.
cr_use_shelter:
        jsr     cr_shelter_here
        jcc     cr_m1
        lda     #1
        cpx     #N_IGLOO
        bne     :+
        lda     #2
:       sta     shelter_inside
        lda     #15
cr_inside:
        sta     health_period
        lda     #1
        sta     cr_view
        lda     #<cr_m9
        ldx     #>cr_m9
        jmp     cr_say

; USE TENT ($58E4): the tent here or carried (msg 1), not at the wreck nor
; the outpost (msg 49); 30 minutes (W7[9]) at .02, inside, health steps of
; 20 minutes, msg 9; a carried tent is set down here.
cr_use_tent:
        jsr     have
        jcc     cr_m1
        jsr     cr_wreck
        bcs     :+
        jsr     cr_outpost
        bcc     :++
:       lda     #<cr_m49
        ldx     #>cr_m49
        jmp     cr_say
:       lda     it_gnd_lo+N_TENT
        sta     camp_minutes
        lda     #2
        sta     cr_eff
        lda     #1
        sta     shelter_inside
        ldx     #N_TENT
        lda     it_place,x
        beq     :+
        jsr     cr_ground_item
:       lda     #20
        jmp     cr_inside

; ---------------------------------------------------------------------------
; Helpers
; ---------------------------------------------------------------------------
; cr_here -- once the player has left the cell (cr_still 0, forage_here:
; T0C/S0B $596E), the CLUB left on the ground is lost, and a ROCK not
; carried lies on the new cell unless it is water (T0D/S00 $585F: b1[17] = 0
; when $4B56 < 3). The BOW, the SPEAR, the SPLINT keep their own cell.
cr_here:
        lda     cr_still
        bne     @rts
        inc     cr_still
        lda     cr_b1+2         ; the CLUB on the ground: lost
        bne     :+
        dec     cr_b1+2
:       lda     cr_b1+3         ; the ROCK carried (2, 3): kept
        beq     :+
        cmp     #$FF
        bne     @rts
:       jsr     cr_water        ; N: water
        asl     a
        lda     #0
        bcc     :+
        lda     #$FF
:       sta     cr_b1+3
@rts:   rts
; cr_water -- the player's fine cell (native_here, which is SIM's): N set
; on water.
cr_water:
        lda     px
        asl     a
        lda     px+1
        rol     a
        tay
        lda     py
        asl     a
        lda     py+1
        rol     a
        tax
        jmp     cell_native

; cr_item -- noun 89..93: X = 0..4 (BOW, SPEAR, CLUB, ROCK, SPLINT), then
; cr_where.
cr_item:
        lda     noun
        sec
        sbc     #N_BOW
        tax
; cr_where -- X = 0..4: A = its place (cr_b1), $FF when it lies on the
; ground of another cell (the original's b1 once the player has left it,
; b3/b4 kept); X kept. The CLUB and the ROCK on the ground are this cell's
; (cr_here).
cr_where:
        lda     cr_b1,x
        bne     @rts
        ldy     #2              ; the SPLINT's cell
        cpx     #4
        beq     :+
        cpx     #2
        bcs     @rts            ; CLUB, ROCK: A = 0
        txa
        tay
:       lda     cr_cx,y
        cmp     px+1
        bne     @away
        lda     cr_cy,y
        cmp     py+1
        bne     @away
        lda     #0
        rts
@away:  lda     #$FF
@rts:   rts

; cr_put -- X = 0..4, A = its new place; the BOW, the SPEAR, the SPLINT
; remember this cell (b3/b4). X kept.
cr_put:
        sta     cr_b1,x
        ldy     #2
        cpx     #4
        beq     :+
        cpx     #2
        bcs     @rts
        txa
        tay
:       lda     px+1
        sta     cr_cx,y
        lda     py+1
        sta     cr_cy,y
@rts:   rts

; ---------------------------------------------------------------------------
; GET, PACK, CARRY, DROP/REMOVE, WEAR of BOW, SPEAR, CLUB, ROCK, SPLINT:
; the transaction T0E/S02 (measured: tools/re_craft_probe.py part 3). GET
; and CARRY put it in hand, PACK in the pack, DROP on the ground of this
; cell, WEAR the SPLINT only ("TRY ANOTHER VERB.": the port's text; worn,
; the care selector 3 of USE SPLINT, no time); there
; already msg 11, absent msg 1. Run from ITEMS (src/game.s item_noun): CAMP
; is not in $5800, the messages are printed by message directly. Lot 14
; (16 October 2026): taken from the ground, within the load (cr_load).
; ---------------------------------------------------------------------------
cr_items:
        jsr     cr_item
        sta     cr_n            ; the place now
        ldy     verb
        lda     cr_dest-1,y
        cmp     #1              ; WEAR: the SPLINT only
        bne     :+
        cpx     #4
        beq     :+
        lda     #m_notwear
        bne     @say
:       ldy     cr_n
        iny
        bne     :+
        lda     #c_m1           ; absent here: msg 1
        bne     @say
:       cmp     cr_n
        bne     :+
        lda     #c_m11          ; there already: msg 11
        bne     @say
:       cmp     #2              ; PACK: the backpack carried (as ITEMS)
        bne     :+
        ldy     it_place+21
        beq     @nopack
        cpy     #5
        bcs     @nopack
:       jsr     cr_load         ; lot 14: from the ground, within the limits
        bcs     @heavy
        pha
        cpx     #4              ; the SPLINT: worn, care selector 3 (USE
        bne     @put            ; SPLINT's); any other place clears it
        ldy     #0              ; (T0E/S0A $5AC4, measured)
        cmp     #1
        bne     :+
        iny
:       sty     medical_actions+2
@put:   jsr     cr_put
        pla
        tax
        lda     cr_said,x
@say:   ldx     #0              ; a text of the bank
        jmp     message
@heavy: jmp     cr_heavy        ; both capacity causes, without changing cr_load
@nopack:
        lda     #m_needpack
        bne     @say
cr_dest: .byte  3, 0, 0, 0, 1, 2, 3, 0  ; verbs 1 GET, 5 WEAR, 6 PACK, 7 CARRY, 8 DROP

; cr_load -- (lot 14, T0E/S02) X = 0..4 taken from place cr_n to place A
; (1 worn, 2 pack, 3 hand): from the ground, the load made by the caller
; (load_totals, ITEMS or CAMP) plus its weight and its volume (W5, W6 of
; CRAFT.md 4.1) must stay within load_limits; C set when it passes one
; (the original's msg 7). A, X kept.
cr_load:
        pha
        ldy     cr_n
        bne     @ok             ; carried already: its weight stays
        asl     a
        sta     cr_ld
        ldy     #0
        lda     cr_w,x
        jsr     cr_fit
        bcc     @no
        ldy     cr_ld
        lda     cr_v,x
        jsr     cr_fit
        bcc     @no
@ok:    pla
        clc
        rts
@no:    pla
        sec
        rts
; cr_fit -- C clear when A more in word Y of load_used passes load_limits.
cr_fit: clc
        adc     load_used,y
        sta     cr_ld+1
        lda     #0
        adc     load_used+1,y
        sta     cr_ld+2
        lda     load_limits,y
        cmp     cr_ld+1
        lda     load_limits+1,y
        sbc     cr_ld+2
        rts
cr_w:   .byte   50, 50, 100, 100, 50    ; W5 (oz), as src/game.s lt_crw
cr_v:   .byte   90, 90, 200, 100, 120   ; W6 (in3)
cr_ld:  .res    3
cr_said: .byte  m_dropped, m_worn, m_taken, m_carried

; cr_have -- X = noun (1..75): C set when present (have), X kept.
cr_have:
        stx     cr_n
        jsr     have
        ldx     cr_n
        rts

; cr_rope -- C set with ROPE or FISHNG GEAR ($5B94, $5A7B: B1 >= 0).
cr_rope:
        ldx     #N_ROPE
        jsr     have
        bcs     :+
        ldx     #N_GEAR
        jsr     have
:       ldx     noun
        rts

; cr_tool -- A = 1 the AXE, 2 the KNIFE: A = 1 when it is in use on this
; cell (B2[58], B2[59]: care_tools, lot 13), else 0.
cr_tool:
        and     care_tools
        beq     @no
        lda     px+1
        cmp     care_tool_x
        bne     @no
        lda     py+1
        cmp     care_tool_y
        bne     @no
        lda     #1
        rts
@no:    lda     #0
        rts

; cr_wreck, cr_outpost -- C set on the cell of the wreck ($D9 = $7F: the
; crash site, MAP+3/MAP+5) or of the outpost ($D8: the goal, MAP+8/MAP+9).
cr_wreck:
        lda     px+1
        cmp     MAP+3
        bne     cr_no
        lda     py+1
        cmp     MAP+5
        bne     cr_no
        sec
        rts
cr_outpost:
        lda     px+1
        cmp     M_GOALX
        bne     cr_no
        lda     py+1
        cmp     M_GOALY
        bne     cr_no
        sec
        rts
cr_no:  clc
        rts

; cr_shelter_here -- noun 95..97: C set when that shelter stands here; X =
; the noun.
cr_shelter_here:
        lda     noun
        sec
        sbc     #N_HUT
        tax
        lda     cr_sx,x
        cmp     px+1
        bne     :+
        lda     cr_sy,x
        cmp     py+1
        bne     :+
        ldx     noun
        sec
        rts
:       ldx     noun
        clc
        rts

; cr_ground_item -- item X of the first set made or set down on this cell
; (the tent: a site sprite on XL, so scene_prepare's cache is dropped).
cr_ground_item:
        lda     #0
        sta     it_place,x
        sta     scene_cache_valid
        lda     px+1
        sta     it_x,x
        lda     py+1
        sta     it_y,x
        rts

; cr_minutes -- camp_minutes = the minutes MAKE noun takes here, by the
; ROM's formulas in its order of operations (T10/S00; tools/re_craft_probe.py):
;   HUT, IGLOO, TRENCH  4000 k / ((light + 2)(axe + 2) health), k = 2, 3, 1
;   CLUB                60 / SQR(health)
;   SPEAR, AXE, BOW     600 / (SQR(health)(3 knife + 1)); the BOW
;                       INT(4 t / (light + 1))
;   SPLINT              300 / (SQR(health)(light + 1)(knife + 1))
;   SUNGLASSES, SUNSCREEN  30
; MAKE calls it once its checks pass; the CRAFT page for every recipe.
cr_minutes:
        lda     noun
        cmp     #N_HUT
        bcc     @tools
        sbc     #N_HUT-2        ; HUT 2, IGLOO 3, TRENCH 4 -> 1
        cmp     #4
        bne     :+
        lda     #1
:       tay
        jsr     SNGFLT
        fop     FMULT, cr_4000
        fst     cr_t1
        ldy     light
        iny
        iny
        jsr     SNGFLT
        fst     cr_t2
        lda     #1
        jsr     cr_tool         ; the AXE in use
        clc
        adc     #2
        tay
        jsr     SNGFLT
        fop     FMULT, cr_t2
        fop     FMULT, s_health
        fop     FDIV, cr_t1
        jmp     cr_time
@tools: cmp     #N_AXE
        bcs     :+
        lda     #0              ; SUNGLASSES, SUNSCREEN
        sta     camp_minutes+1
        lda     #30
        sta     camp_minutes
        rts
:       pha
        fld     s_health
        jsr     FSQR
        pla
        cmp     #91
        bne     :+
        fop     FDIV, f_60      ; CLUB
        jmp     cr_time
:       fst     cr_t1
        lda     noun
        cmp     #N_SPLINT
        beq     @splint
        lda     #2
        jsr     cr_tool         ; the KNIFE in use
        sta     cr_t2
        asl     a
        adc     cr_t2
        tay
        iny
        jsr     SNGFLT
        fop     FMULT, cr_t1
        fop     FDIV, cr_600
        jsr     cr_time
        lda     noun
        cmp     #N_BOW
        bne     @rts
        lda     camp_minutes+1  ; INT(4 t / (light + 1))
        ldy     camp_minutes
        jsr     GIVAYF
        fop     FMULT, f_4
        fst     cr_t1
        ldy     light
        iny
        jsr     SNGFLT
        fop     FDIV, cr_t1
        jmp     cr_time
@splint:
        ldy     light
        iny
        jsr     SNGFLT
        fst     cr_t2
        lda     #2
        jsr     cr_tool
        tay
        iny
        jsr     SNGFLT
        fop     FMULT, cr_t2
        fop     FMULT, cr_t1
        fop     FDIV, cr_300
        jmp     cr_time
@rts:   rts

; cr_time -- camp_minutes = INT(FAC) ($E10C).
cr_time:
        jsr     AYINT
        lda     $A1
        sta     camp_minutes
        lda     $A0
        sta     camp_minutes+1
        rts

; cr_made -- A = the effort (1 .01, 2 .02, 3 .023), then "IT TOOK A WHILE
; TO MAKE YOUR ^." (msg 15) with the time (camp_craft).
cr_made:
        sta     cr_eff
        lda     #M_M15
        sta     cr_msg
        rts

; cr_say -- A/X a message (X = 0: a text of the bank): the first of the
; command replaces the result, the next follow it (camp_say's rule).
cr_say: ldy     camp_said
        inc     camp_said
        cpy     #0
        bne     :+
        jmp     message
:       cpx     #0
        bne     :+
        jsr     text_fetch
:       sta     gp1
        stx     gp1+1
        lda     #' '|$80
        jsr     msg_char
        jmp     message_body
cr_m1:  lda     #<c_m1
        ldx     #>c_m1
        jmp     cr_say
cr_m2:  lda     #<w_m2
        ldx     #>w_m2
        jmp     cr_say
cr_ok:  lda     #<m_ok
        ldx     #>m_ok
        jmp     cr_say
cr_m11: lda     #<c_m11
        ldx     #>c_m11
        jmp     cr_say
cr_m17: lda     #<care_specific_message
        ldx     #>care_specific_message
        jmp     cr_say
cr_m21: lda     #<cr_m21_text
        ldx     #>cr_m21_text
        jmp     cr_say
cr_m76: lda     #<c_m76
        ldx     #>c_m76
        jmp     cr_say

cr_4000: .byte  $8C,$7A,$00,$00,$00     ; T10/S00 $5C89
cr_600:  .byte  $8A,$16,$00,$00,$00     ; $5C84
cr_300:  .byte  $89,$16,$00,$00,$00     ; $5C7A
cr_t1:   .res   5
cr_t2:   .res   5
cr_n:    .res   1
; The original's texts (msg n of Journey); "!" is $A1 (src/game.s message).
cr_m4:   .byte  "YOU NEED STRONG ROPE.",0
cr_m9:   .byte  "YOU'RE NOW SAFELY INSIDE SHELTER.",0
cr_m21_text: .byte "YOUR POWERS DON'T EXTEND THAT FAR",$A1,0
cr_m28:  .byte  "GOOD",$A1," YOU MADE EYE SHADES FROM SLITTED BARK.",0
cr_m35:  .byte  "YOU NEED TO SKIN A CREATURE FOR ITS HIDE.",0
cr_m49:  .byte  "THINK",$A1,0
cr_m92:  .byte  "YOU'RE IN THE WATER ALREADY",$A1,0
cr_m101: .byte  "FOR MORE HIDE, SKIN A CREATURE AND ADD TO YOUR SUPPLY.",0
cr_m205: .byte  "SMEARING MUD ON YOUR SKIN TO BLOCK THE SUN'S RAYS.",0

; ---------------------------------------------------------------------------
; The CRAFT page (lot 3, step 2: the "book of recipes", docs/CRAFT.md 8.6):
; a top page between INVENTORY and HELP (src/pages.s). pg_craft (STATUS)
; draws the tab row (page_top), then reads this module over STATUS and
; returns here (sim_fetch's RTS): no resident byte. The recipes are the
; original's MAKE that CRAFT carries out (A1, A2), in three groups (headers
; not selectable): SHELTERS (HUT, IGLOO, TRENCH), WEAPONS AND TOOLS (CLUB,
; SPEAR, BOW, AXE, SPLINT), PROTECTION (SUNGLASSES, SUNSCREEN). Left, each
; recipe with its state (MouseText, ALTCHARSET on while the page is shown:
; a check mark possible, an inverse X missing, a diamond done: one here or
; carried already) and the minutes MAKE would spend here (cr_minutes, the
; ROM's formulas with the light, the axe or knife in use, the health now).
; Right, the recipe chosen: its effect, each check of craft.s in its order
; (here or not), the time with what it depends on, what makes it slower.
; Same focus as the cursor pages: the tab row (LEFT/RIGHT turn the pages),
; then UP/DOWN from recipe to recipe, DOWN past the last one: the view;
; S, M, I, H, T as everywhere; ESC the view. RETURN (or SPACE) on a
; possible recipe types MAKE x (inbuf, do_command: the keyboard's path);
; on another it beeps. The row 23 says what RETURN does. Drawing:
; differential (t_update), the left half then the right half, each cell
; written once; the times and states are computed once at arrival.
; ---------------------------------------------------------------------------
CP_N     = 10                   ; recipes
CP_SHORT = 1                    ; the SPLINT's shortcut: AXE, SPEAR, wreck, outpost
CP_LAND  = 2                    ; not in the water (msg 92)
CP_AWAY  = 4                    ; not at the wreck nor the outpost (msg 49)
CP_WOODS = 8                    ; the woods (msg 76)
CP_SNOW  = 16                   ; at the snow line (msg 76)
CP_ROPE  = 32                   ; ROPE or FISHNG GEAR (msg 4)
CP_SOIL  = 64                   ; clear ground or woods (msg 76)
CP_EXEMPT = 128                 ; no rope in Burma, New Guinea, Bolivia (3-5)
CP_SEP   = 30                   ; the column of the separator
CP_PANEL = 31                   ; the right half (a space, then the panel)
CP_LAST  = 21                   ; last row of the halves
ALTCHARON  = $C00F              ; MouseText ($40-$5F) on the page only
ALTCHAROFF_ = $C00E
G_OK   = 1                      ; glyphs in the strings (cp_gl): check mark,
G_NO   = 2                      ; inverse X, diamond, up and down arrows
G_DONE = 3
G_UP   = 4
G_DOWN = 5
craft_page:
        sta     ALTCHARON
        lda     #<(craft_page-CRAFT_RUN)        ; MAKE reads the recipes only
        sta     module_dir+CRAFT_MODULE*DIR_SIZE+3
        lda     #>(craft_page-CRAFT_RUN)
        sta     module_dir+CRAFT_MODULE*DIR_SIZE+4
        jsr     cr_here         ; the CLUB, the ROCK of this cell (as MAKE)
        lda     #CP_LAND        ; the ingredients here (cp_have)
        sta     cp_have
        jsr     cr_water
        bpl     :+
        lda     #0              ; water: class 3
        sta     cp_have
        beq     @snow
:       jsr     woods_here      ; class 1 woods, 2 rocky (96 and up), 0
        lda     #CP_WOODS|CP_SOIL
        bcs     @class
        jsr     level_here
        cmp     #96
        bcs     @snow
        lda     #CP_SOIL
@class: jsr     cp_or
@snow:  jsr     level_here
        cmp     M_SNOW
        bcc     :+
        lda     #CP_SNOW
        jsr     cp_or
:       jsr     cr_rope
        bcc     :+
        lda     #CP_ROPE
        jsr     cp_or
:       jsr     cr_wreck        ; the wreck, the outpost: no shelter, the
        bcs     @short          ; SPLINT's shortcut
        jsr     cr_outpost
        bcs     @short
        lda     #CP_AWAY
        jsr     cp_or
        ldx     #1              ; a SPEAR here or carried
        jsr     cr_where
        cmp     #$FF
        bne     @short
        ldx     #N_AXE
        jsr     have
        bcc     @prep
@short: lda     #CP_SHORT
        jsr     cp_or
; The states and the minutes of the ten recipes (noun and camp_minutes:
; the next command sets them again, camp_begin), the health in percent
; (STATUS's rounding).
@prep:
        ldx     #CP_N-1
@rec:   stx     cp_i
        jsr     cp_eval
        lda     cp_low          ; 0 possible, 1 missing, 2 done
        clc
        adc     cp_one
        ldx     cp_i
        sta     cp_st,x
        lda     cp_noun,x
        sta     noun
        jsr     cr_minutes
        ldx     cp_i
        lda     camp_minutes
        sta     cp_mlo,x
        lda     camp_minutes+1
        sta     cp_mhi,x
        dex
        bpl     @rec
        fld     f_hmax
        fop     FDIV, s_health
        fop     FMULT, f_100
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     cp_pct
; The left half: rows 1..21, the groups and the recipes, then the separator.
; (XL, docs/MENUS.md 9: rows 2..20, under the tabs' line; the legend on 21,
; the footer of the pages below it.)
cp_draw:
        XL_IMM  XI_CRAFT, 1, @x31
        lda     #0
        sta     cp_r
@left:  ldx     #0
        inc     cp_r
        lda     cp_r
        jsr     cp_at
        ldx     cp_r
        XL_ABS  XI_CRAFT, cp_rows_x-2, @x32     ; (XL: the post-its' rows)
        lda     cp_rows-1,x
        bmi     @group
        cmp     #CP_N
        bcs     @sep            ; (the empty rows)
        sta     cp_i
        tax
        inx
        lda     #' '            ; the marker in column 1
        XL_ABS  XI_CRAFT, crx_rts, @p35         ; (XL: the post-it's bar in column 0)
        jsr     cp_ch
        cpx     cp_focus
        bne     :+
        lda     #'>'
:       jsr     cp_ch
        jsr     cp_puts
        .byte   " ", 0
        ldx     cp_i
        jsr     cp_name
        lda     #15
        jsr     tab
        ldx     cp_i
        ldy     cp_st,x
        lda     cp_gl,y
        jsr     COUT
        cpy     #2
        beq     @sep            ; done: no time
        jsr     cp_puts
        .byte   " ", 0
        sec                     ; padded: the minutes under the minutes
        jsr     cp_time
        jmp     @sep
@group: and     #$7F
        tax
        lda     cp_grp_lo,x
        ldy     #>cp_grp
        XL_ABS  XI_CRAFT, crx_rts, @p30         ; (XL: the post-it's title, fr_craft)
        jsr     cp_str
@sep:   XL_IMM  XI_CRAFT, CP_SEP+1, @p31        ; (XL: the gap, then the right
        lda     #CP_SEP                         ; post-it's bar in column 30)
        jsr     tab
        lda     #$5A            ; MouseText: a vertical bar
        XL_ABS  XI_CRAFT, crx_rts, @p36
        jsr     COUT
        lda     cp_r
        XL_IMM  XI_CRAFT, CP_LAST-1, @x33
        cmp     #CP_LAST
        bcc     @left
; The right half: the recipe chosen (HUT on the tab row), from row 1.
        ldx     cp_focus
        dex
        bpl     :+
        inx
:       stx     cp_i
        jsr     cp_eval
        XL_IMM  XI_CRAFT, 2, @x34
        lda     #1
        ldx     #CP_PANEL
        XL_ABS  XI_CRAFT, cp_at_inv, @p32       ; (XL: the title of the post-it)
        jsr     cp_at
        lda     #' '
        jsr     cp_ch
        ldy     cp_focus
        beq     :+
        lda     #'>'
        jsr     cp_ch
        lda     #' '
        jsr     cp_ch
:       ldx     cp_i
        jsr     cp_name
        lda     #70
        XL_ABS  XI_CRAFT, cp_tab_x, @p33
        jsr     tab
        jsr     cp_verdict
        jsr     cp_nl           ; the effect
        ldx     cp_i
        lda     cp_eff_lo,x
        ldy     cp_eff_hi,x
        jsr     cp_str
        jsr     cp_nl
        jsr     cp_puts
        .byte   "NEEDS:", 0
        lda     cp_one
        beq     :+
        jsr     cp_cond
        jsr     cp_puts
        .byte   G_DONE, " YOU HAVE ONE ALREADY", 0
:       lda     #1              ; each check, in craft.s's order
@bit:   sta     cp_b
        and     cp_need
        beq     @next
        jsr     cp_cond
        lda     cp_b
        and     cp_have
        cmp     #1
        lda     #G_NO
        bcc     :+
        lda     #G_OK
:       jsr     cp_ch
        lda     #' '
        jsr     cp_ch
        ldx     #$FF
        lda     cp_b
:       inx
        lsr     a
        bcc     :-
        lda     cp_tok_lo,x
        ldy     #>cp_tok
        jsr     cp_str
@next:  lda     cp_b
        asl     a
        bpl     @bit
        lda     cp_one          ; done: MAKE spends no time
        bne     @fill
        jsr     cp_nl
        jsr     cp_puts
        .byte   "TIME: ", 0
        ldx     cp_i
        clc
        jsr     cp_time
        jsr     cp_puts
        .byte   " (", 0
        clc
        jsr     cp_factors
        lda     #')'
        jsr     cp_ch
        ldx     cp_i
        lda     cp_fac,x
        beq     @fill
        jsr     cp_nl
        jsr     cp_puts
        .byte   "SLOWER: ", 0
        sec
        jsr     cp_factors
@fill:  lda     CV              ; the rows below, cleared
        XL_IMM  XI_CRAFT, CP_LAST-1, @x35
        cmp     #CP_LAST
        bcs     :+
        jsr     cp_nl
        jmp     @fill
:       jsr     topo_pad
        XL_IMM  XI_CRAFT, 21, @x36
        lda     #22
        ldx     #0
        jsr     cp_at
        jsr     cp_puts
        .byte   " ", G_OK, " POSSIBLE   ", G_NO, " MISSING   ", G_DONE, " DONE", 0
        jsr     topo_pad
        XL_JMP  XI_CRAFT, cr_foot_x, @x37     ; (XL: the footer of the pages)
        lda     #23
        ldx     #0
        jsr     cp_at
        jsr     cp_puts
        .byte   G_UP, G_DOWN, " CHOOSE   RETURN: ", 0
cp_after_keys = *
        ldx     cp_focus
        bne     :+
        jsr     cp_puts
        .byte   "VIEW", 0
        jmp     @esc
:       dex
        lda     cp_st,x
        bne     :+
        jsr     cp_puts
        .byte   "MAKE ", 0
        ldx     cp_i
        jsr     cp_name
        jmp     @esc
:       jsr     cp_puts
        .byte   "NOTHING (", 0
        jsr     cp_verdict
        lda     #')'
        jsr     cp_ch
@esc:   XL_IMM  XI_CRAFT, 69, @x47
        lda     #70
        jsr     tab
        jsr     cp_puts
cp_esc_text = *
        .byte   "ESC: VIEW", 0
        XL_TEXT XI_CRAFT, cp_esc_text, " ESC VIEW"      ; (XL: at 70)
; The keys (src/pages.s page_keys, the cursor pages').
cp_key: jsr     wait_key
        ldy     cp_focus
        cmp     #KC_UP
        bne     :+
        dey
        bpl     @focus
        ldx     #4              ; above the tab row: TOPO (docs/MENUS.md 5)
        bne     @letter
:       cmp     #KC_DOWN
        bne     :+
        iny
        cpy     #CP_N+1
        jcs     cp_view         ; past the last recipe
@focus: sty     cp_focus
        XL_ABS  XI_CRAFT, cp_redraw_x, @p34     ; (XL: drawn by the post-its' COUT)
        jmp     cp_draw
:       cmp     #KC_ESC
        beq     cp_view
        ldx     #5
:       cmp     cp_letter,x     ; S, M, I, H, T, O
        beq     @letter
        dex
        bpl     :-
        cpy     #0
        bne     @line
        ldx     #2
        cmp     #KC_LEFT        ; the tab row: the pages turn
        beq     @letter         ; (INVENTORY)
        inx
        cmp     #KC_RIGHT
        beq     @letter         ; (HELP)
        cmp     #KC_RET
        beq     cp_view
        cmp     #' '
        beq     cp_view
        bne     cp_key
@letter:
        lda     cp_go_hi,x      ; the resident entries of the screens
        pha
        lda     cp_go_lo,x
        pha
        XL_IMM  XI_CRAFT, <ALTCHARON, @x38    ; (XL: MouseText for the whole game)
        sta     ALTCHAROFF_
        rts
@line:  cmp     #KC_RET         ; a recipe: RETURN (or SPACE) makes it
        beq     :+
        cmp     #' '
        bne     cp_key
:       dey
        sty     cp_i
        lda     cp_st,y
        beq     :+
        jsr     BELL1           ; missing or done: it cannot be made here
        jmp     cp_key
:       ldy     #4              ; "MAKE x", as typed
:       lda     cp_make_t,y
        sta     inbuf,y
        dey
        bpl     :-
        ldx     cp_i
        jsr     cp_nm_at
        ldx     #5
        ldy     #0
:       lda     (gp1),y
        sta     inbuf,x
        beq     :+
        inx
        iny
        bne     :-
:       stx     linelen
        lda     #0              ; the words name the noun
        sta     menu_noun
        jsr     cp_view
        jmp     do_command
cp_view:
        XL_IMM  XI_CRAFT, <ALTCHARON, @x39
        sta     ALTCHAROFF_
        jmp     back_to_view_now

; cp_eval -- recipe cp_i: cp_need its checks (the rope dropped in regions
; 3-5 for the weapons), cp_one 1 when one is here or carried already,
; cp_low 1 when it cannot be made here.
cp_eval:
        ldx     cp_i
        lda     cp_mask,x
        bpl     :+
        ldy     region_number
        cpy     #3
        bcc     :+
        cpy     #6
        bcs     :+
        and     #<~CP_ROPE
:       and     #$7F
        sta     cp_need
        lda     #0              ; already: a shelter here, the second set
        sta     cp_one          ; here or carried, the first set present
        lda     cp_noun,x
        cmp     #N_HUT
        bcc     @second
        sbc     #N_HUT
        tax
        lda     cr_sx,x
        cmp     px+1
        bne     @set
        lda     cr_sy,x
        cmp     py+1
        bne     @set
        beq     @one
@second:
        cmp     #N_BOW
        bcc     @first
        sbc     #N_BOW
        tax
        jsr     cr_where
        cmp     #$FF
        beq     @set
        bne     @one
@first: tax
        jsr     have
        bcc     @set
@one:   inc     cp_one
@set:   lda     cp_one
        sta     cp_low
        lda     cp_need         ; the SPLINT's shortcut makes it at once
        lsr     a
        bcc     :+
        lda     cp_have
        lsr     a
        bcs     @rts
:       lda     cp_need
        and     #<~CP_SHORT
        ora     cp_have
        cmp     cp_have
        beq     @rts            ; every ingredient here
        lda     #1
        sta     cp_low
@rts:   rts

; cp_time -- the minutes of recipe X: "1 H 24", "12 MIN"; C set: padded
; for the list (" 1 H 24", "      12 MIN": the minutes in one column).
cp_time:
        ror     cp_pad
        lda     cp_mlo,x
        sta     num
        lda     cp_mhi,x
        sta     num+1
        ldx     #0              ; hours
@h:     lda     num
        sec
        sbc     #60
        tay
        lda     num+1
        sbc     #0
        bcc     :+
        sta     num+1
        sty     num
        inx
        bne     @h
:       lda     num
        sta     cp_m
        txa
        beq     @min
        jsr     cp_pad2
        jsr     cp_puts
        .byte   " H ", 0
        lda     cp_m
        cmp     #10
        bcs     :+
        lda     #'0'
        jsr     cp_ch
:       lda     cp_m
        jmp     pdec
@min:   bit     cp_pad
        bpl     :+
        jsr     cp_puts
        .byte   "     ", 0
:       lda     cp_m
        jsr     cp_pad2
        jsr     cp_puts
        .byte   " MIN", 0
        rts
; cp_pad2 -- A (0..255) in decimal, a space first when padded and < 10.
cp_pad2:
        bit     cp_pad
        bpl     :+
        cmp     #10
        bcs     :+
        pha
        lda     #' '
        jsr     cp_ch
        pla
:       jmp     pdec

; cp_factors -- what the time of recipe cp_i depends on: C clear, as they
; are now ("DAY, NO AXE, HEALTH 100%"); C set, what makes it slower
; ("NIGHT, AXE NOT IN USE, LOW HEALTH"); none: "ALWAYS".
cp_factors:
        ror     cp_pad
        ldx     cp_i
        lda     cp_fac,x
        bne     :+
        jsr     cp_puts
        .byte   "ALWAYS", 0
        rts
:       sta     cp_b
        lda     #0
        sta     cp_m            ; 1 after the first word
        ldx     #0
@bit:   lsr     cp_b
        jcc     @next
        stx     cp_f
        lda     cp_m
        beq     :+
        jsr     cp_puts
        .byte   ", ", 0
:       inc     cp_m
        ldx     cp_f
        bne     @tool
        lda     light           ; the light: DAY (1), NIGHT (0)
        bit     cp_pad
        bmi     :+
        and     #1
        tax
        lda     cp_light_lo,x
        ldy     #>cp_word
        jsr     cp_str
        jmp     @nx
:       lda     #<cp_w_night
        ldy     #>cp_word
        jsr     cp_str
        jmp     @nx
@tool:  cpx     #3
        beq     @health
        txa                     ; 1 the AXE, 2 the KNIFE
        jsr     cr_tool
        ldx     cp_f
        bit     cp_pad
        bmi     @slow
        cmp     #1              ; in use: "AXE", else "NO AXE"
        lda     cp_tool_lo-1,x
        bcc     :+
        adc     #2              ; (+3: past "NO ")
:       ldy     #>cp_word
        jsr     cp_str
        jmp     @nx
@slow:  lda     cp_tool_lo-1,x
        clc
        adc     #3
        ldy     #>cp_word
        jsr     cp_str
        jsr     cp_puts
        .byte   " NOT IN USE", 0
        jmp     @nx
@health:
        bit     cp_pad
        bmi     :+
        jsr     cp_puts
        .byte   "HEALTH ", 0
        lda     cp_pct
        jsr     pdec
        lda     #'%'
        jsr     cp_ch
        jmp     @nx
:       jsr     cp_puts
        .byte   "LOW HEALTH", 0
@nx:    ldx     cp_f
@next:  inx
        cpx     #4
        jcc     @bit
        rts

; cp_verdict -- the state of recipe cp_i in words.
cp_verdict:
        ldx     cp_i
        ldy     cp_st,x
        lda     cp_verd_lo,y
        ldy     #>cp_word
        jmp     cp_str

; cp_at -- the cursor at row A, column X (no padding: each half writes
; its own cells).
cp_at:  sta     CV
        jsr     t_vtab
        stx     CH
        rts
; cp_nl -- the rest of the row cleared, then the next row of the right
; half, at column 34.
cp_nl:  jsr     topo_pad
        inc     CV
        jsr     t_vtab
        lda     #CP_PANEL
        sta     CH
        jsr     cp_puts
        .byte   "   ", 0
        rts
; cp_cond -- a new row for a check, at column 35.
cp_cond:
        jsr     cp_nl
        lda     #' '
        jmp     cp_ch

; cp_name -- recipe X's name.
cp_name:
        jsr     cp_nm_at
        lda     gp1
        ldy     gp1+1
; cp_str -- the string at A/Y (glyphs 1..5: cp_gl).
cp_str: sta     gp2
        sty     gp2+1
        ldy     #0
@ch:    lda     (gp2),y
        beq     @end
        jsr     cp_ch
        iny
        bne     @ch
@end:   rts
; cp_puts -- the string after the JSR, as cp_str.
cp_puts:
        pla
        sta     gp2
        pla
        sta     gp2+1
        ldy     #0
@ch:    inc     gp2
        bne     :+
        inc     gp2+1
:       lda     (gp2),y
        beq     @end
        jsr     cp_ch
        jmp     @ch
@end:   lda     gp2+1
        pha
        lda     gp2
        pha
        rts
; cp_ch -- a character, or glyph 1..5 (MouseText, the inverse X); X, Y kept.
cp_ch:  cmp     #G_DOWN+1
        bcs     :+
        stx     cp_x
        tax
        lda     cp_gl-1,x
        ldx     cp_x
        jmp     COUT            ; (below $80: stored as is, t_cout)
:       ora     #$80
        jmp     COUT
; cp_nm_at -- gp1 = the name of recipe X.
cp_nm_at:
        lda     #<cp_names
        sta     gp1
        lda     #>cp_names
        sta     gp1+1
        ldy     #0
@skip:  dex
        bmi     @rts
@ch:    lda     (gp1),y
        inc     gp1
        bne     :+
        inc     gp1+1
:       cmp     #0
        bne     @ch
        beq     @skip
@rts:   rts
cp_or:  ora     cp_have
        sta     cp_have
        rts

cp_focus: .byte 0               ; 0 the tab row, 1..10 a recipe
; Glyphs (state 0..2, string codes G_OK..G_DOWN): check mark, inverse X
; (the standard set: MouseText has no cross), diamond, up and down arrows.
cp_gl:    .byte $44, $18, $5B, $4B, $4A
; The left half, rows 1..21: $80 + a group, a recipe, $7F nothing.
cp_rows:  .byte $80, 0, 1, 2, $81, 3, 4, 5, 6, 7, $82, 8, 9
          .res  CP_LAST-13, $7F
; The recipes in the order of the original's families (shelters, weapons,
; care): noun, checks, what their time depends on (1 the light, 2 the AXE
; in use, 4 the KNIFE in use, 8 the health), effect.
cp_noun:  .byte N_HUT, N_IGLOO, 97, 91, 90, N_BOW, N_AXE, N_SPLINT, 43, 44
cp_mask:  .byte CP_LAND|CP_AWAY|CP_WOODS, CP_LAND|CP_AWAY|CP_SNOW, CP_LAND|CP_AWAY
          .byte CP_WOODS, CP_WOODS|CP_ROPE|CP_EXEMPT, CP_WOODS|CP_ROPE|CP_EXEMPT
          .byte CP_WOODS|CP_ROPE|CP_EXEMPT, CP_SHORT|CP_WOODS|CP_ROPE, CP_SOIL, CP_SOIL
cp_fac:   .byte 11, 11, 11, 8, 12, 13, 12, 13, 0, 0
cp_eff_lo: .byte <cp_e_hut, <cp_e_igloo, <cp_e_hut, <cp_e_club, <cp_e_spear
          .byte <cp_e_bow, <cp_e_axe, <cp_e_splint, <cp_e_glass, <cp_e_screen
cp_eff_hi: .byte >cp_e_hut, >cp_e_igloo, >cp_e_hut, >cp_e_club, >cp_e_spear
          .byte >cp_e_bow, >cp_e_axe, >cp_e_splint, >cp_e_glass, >cp_e_screen
cp_e_hut:    .byte "SHELTER: AIR +15 F, ANIMALS 10X SAFER", 0
cp_e_igloo:  .byte "SHELTER: 35 F, ANIMALS 10X SAFER", 0
cp_e_club:   .byte "WEAPON: KILL GAME, ATTACK (THE WEAKEST)", 0
cp_e_spear:  .byte "WEAPON: KILL GAME OR FISH, ATTACK", 0
cp_e_bow:    .byte "WEAPON: KILL GAME, ATTACK (BEST AFTER A GUN)", 0
cp_e_axe:    .byte "TOOL: SHELTERS FASTER IN USE, SPLINT, ATTACK", 0
cp_e_splint: .byte "CARE: A BROKEN ARM OR LEG (USE SPLINT)", 0
cp_e_glass:  .byte "PROTECTION: SNOW BLINDNESS", 0
cp_e_screen: .byte "PROTECTION: SUNBURN", 0
cp_names: .byte "HUT",0,"IGLOO",0,"TRENCH",0,"CLUB",0,"SPEAR",0,"BOW",0,"AXE",0
          .byte "SPLINT",0,"SUNGLASSES",0,"SUNSCREEN",0
cp_make_t: .byte "MAKE "
cp_letter: .byte "SMIHTO"      ; (M: STATUS, MEDICAL's since 15 October 2026; O, I: OBJECTS)
cp_go_lo: .byte <(scr_status-1), <(scr_status-1), <(scr_inventory-1), <(scr_help-1), <(scr_topo-1), <(scr_inventory-1)
cp_go_hi: .byte >(scr_status-1), >(scr_status-1), >(scr_inventory-1), >(scr_help-1), >(scr_topo-1), >(scr_inventory-1)
cp_tok_lo: .byte <cp_t_short, <cp_t_land, <cp_t_away, <cp_t_woods, <cp_t_snow, <cp_t_rope, <cp_t_soil
cp_grp_lo: .byte <cp_g0, <cp_g1, <cp_g2
cp_light_lo: .byte <cp_w_night, <cp_w_day
cp_tool_lo: .byte <cp_w_noaxe, <cp_w_noknife
cp_verd_lo: .byte <cp_v0, <cp_v1, <cp_v2
cp_tok:
cp_t_short: .byte "AXE, SPEAR, WRECK OR POST; OR:", 0
cp_t_land:  .byte "DRY LAND", 0
cp_t_away:  .byte "NOT AT THE WRECK OR THE POST", 0
cp_t_woods: .byte "WOODS", 0
cp_t_snow:  .byte "SNOW", 0
cp_t_rope:  .byte "ROPE OR FISHING GEAR", 0
cp_t_soil:  .byte "SOIL OR WOODS", 0
;ASSERT0
cp_grp:
cp_g0:    .byte " SHELTERS", 0
cp_g1:    .byte " WEAPONS AND TOOLS", 0
cp_g2:    .byte " PROTECTION", 0
;ASSERT1
cp_word:
cp_w_night:   .byte "NIGHT", 0
cp_w_day:     .byte "DAY", 0
cp_w_noaxe:   .byte "NO AXE", 0
cp_w_noknife: .byte "NO KNIFE", 0
cp_v0:    .byte "POSSIBLE", 0
cp_v1:    .byte "MISSING", 0
cp_v2:    .byte "DONE", 0
;ASSERT2
craft_end:
; Work bytes past the image (the rest of its last block, then GRID's
; window: GRID is copied again at each use, src/menu.s grid_fetch).
cp_have  = craft_end            ; the ingredients here (CP_*)
cp_need  = craft_end+1
cp_low   = craft_end+2
cp_one   = craft_end+3
cp_b     = craft_end+4
cp_i     = craft_end+5
cp_r     = craft_end+6
cp_m     = craft_end+7
cp_f     = craft_end+8
cp_x     = craft_end+9
cp_pad   = craft_end+10
cp_pct   = craft_end+11         ; the health in percent
cp_st    = craft_end+12         ; 0 possible, 1 missing, 2 done
cp_mlo   = cp_st+CP_N           ; the minutes MAKE would spend here
cp_mhi   = cp_mlo+CP_N
.assert cp_mhi+CP_N <= crx_base, error, "CRAFT page: work bytes below its XL tail"

; ---------------------------------------------------------------------------
; NeoWildernessXL only (docs/MENUS.md 9): the tail of CRAFT (segment CRAFTX,
; build/wildcrx.bin), read with the page on XL (pg_craft's length, XL), and
; the XL_* bytes above: the halves one row lower, the legend on row 21 and
; the pages' footer on rows 22-23; ALTCHARSET stays on.
.segment "CRAFTX"
crx_base:
; cr_foot_x -- the footer: a line across row 22, then on row 23 the arrows
; and the keys (MouseText); back to the page's RETURN text.
cr_foot_x:
        lda     #22
        ldx     #0
        jsr     cp_at
        ldy     #80             ; (the 80th wraps to row 23)
        lda     #MT_LINE
:       jsr     COUT
        dey
        bne     :-
        ldx     #0
@ch:    lda     crx_keys,x
        beq     @end
        cmp     #$20
        bcs     :+
        eor     #$50            ; MS_*: a MouseText glyph
        bne     @out
:       ora     #$80
@out:   jsr     COUT
        inx
        bne     @ch
@end:   jmp     cp_after_keys
crx_keys: .byte " ", MS_LEFT, MS_RIGHT, " PAGE  ", MS_UP, MS_DOWN, " CHOOSE  ", MS_RET, " ", 0
; The post-its (src/mt_pages.s fr_craft): left SHELTERS (rows 2-6), WEAPONS
; AND TOOLS (7-13), PROTECTION (14-17), their titles drawn by the frame
; (crx_rts: the group rows print nothing), columns 0-28; right the recipe
; chosen (rows 2-20, columns 30-79: its text where the 140 KB edition has
; it), its name in inverse on its first row.
cp_rows_x: .byte $80, 0, 1, 2, $7F, $81, 3, 4, 5, 6, 7, $7F, $82, 8, 9
           .res  CP_LAST-1-15, $7F
pf_craft:                       ; (src/mt_pages.s PF: rows, columns, title)
        PF      2, 6, 0, 28, cp_g0+1
        PF      7, 13, 0, 28, cp_g1+1
        PF      14, 17, 0, 28, cp_g2+1
        PF      2, 20, 30, 79, 0                ; the recipe chosen
        .byte   PF_END
; cp_at_inv -- the recipe's title row: in inverse from its first column.
cp_at_inv:
        jsr     cp_at
        lda     #$3F
        sta     INVFLG
crx_rts:
        rts
; cp_tab_x -- (the title's tab to the verdict) its last space, then normal.
cp_tab_x:
        pha
        lda     #' '|$80
        jsr     COUT
        lda     #$FF
        sta     INVFLG
        pla
        jmp     tab
; cp_redraw_x -- (a move of the focus) the page drawn again through the
; pages' COUT (wait_key's text_finish gave back the previous one).
cp_redraw_x:
        jsr     text_begin
        lda     #<mt_cout
        sta     $36
        lda     #>mt_cout
        sta     $37
        jmp     cp_draw
crx_end:
.segment "CRAFT"
