; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Water (lot 2, docs/CAMP.md): Journey T0F/S00, in the CAMP module with the
; fire (src/camp.s). Sources: rain (RAIN) and snow or ice (SNOW, ICE) give
; 160 oz of safe water; a river or lake 160 oz of untreated water; else
; cacti (RND < .5, safe), or a search of the given time that succeeds when
; RND <= minutes x $4C43 x k (untreated). A source becomes a pile on the
; cell; GET needs the canteen (msg 57) and stops at 64 oz (msg 186); the
; canteen is contaminated by untreated water (B2[22] = water_untreated) and
; stays so. MAKE WATER condenses under a GND COVER or RAINCOAT in use.
; BOIL WATER needs UTENSILS in use and a STOVE in use or a fire (msg 25, 65).
.segment "CAMP"
; GET/FILL/REFILL (verb 1) of WATER, CANTEEN (FILL/REFILL), RAIN, SNOW, ICE.
; Entered by JMP from do_get: another item goes on to ITEMS (get_item);
; otherwise the command ends through camp_done (or a cancelled prompt).
module_collect:
        jsr     camp_begin
        lda     input_argument
        beq     @normal
        lda     noun
        cmp     #N_WATER
        bne     @ordinary
        ldx     #N_WATER
        jsr     at_ground
        bcc     @missing
        lda     it_gnd_lo+N_WATER
        ora     it_gnd_hi+N_WATER
        bne     @ordinary
@missing:
        jmp     no_item
@normal:
        lda     noun
        cmp     #N_WATER
        beq     @water
        cmp     #64
        beq     @canteen
        cmp     #169
        bcc     @ordinary
        cmp     #172
        bcs     @ordinary
        jsr     water_named
        jcs     water_source
        jmp     camp_absent
@canteen:
        lda     inbuf
        cmp     #'R'            ; REFILL CANTEEN
        beq     @fill
        cmp     #'F'
        bne     @ordinary
        lda     inbuf+2
        cmp     #'L'            ; FILL, not FIND
        bne     @ordinary
@fill:  inc     camp_fill
@water: lda     MAP+37
        bne     @here
        ldx     #N_WATER
        jsr     at_ground
        bcc     @here
        lda     it_gnd_lo+N_WATER
        ora     it_gnd_hi+N_WATER
        beq     @here
        lda     camp_fill       ; a pile here: FILL takes from it, GET is the
        jne     water_take      ; ordinary transfer (ITEMS); ground water is safe
@ordinary:
        jmp     get_item
@here:  jsr     water_here
        jcs     water_source
        ; Cacti ($5909, B1 of the second set here): RND < .5, safe water.
        lda     resource_seen
        and     #16
        beq     @search
        jsr     water_random
        fop     FCOMP, f_half
        cmp     #$FF
        bne     @search
        lda     #M_M179         ; shown as the result of the transfer (the
        sta     camp_last       ; original prints it before the amount)
        jmp     water_source
@search:
        ; $5924: "DO YOU WANT TO SEARCH..." then the time ($5935): RND <=
        ; minutes x $4C43 x k, k = .004 in tropical woods (regions 3-5),
        ; .00083 in other woods, .00033 elsewhere.
        lda     #M_M55
        jsr     water_yes
        bne     water_hint
        lda     #<w_m27
        ldx     #>w_m27
        jsr     camp_duration
        bcc     :+
        rts
:
        lda     minutes
        sta     camp_minutes
        lda     minutes+1
        sta     camp_minutes+1
        jsr     camp_effort1
        jsr     woods_here  ; (X is not kept)
        ldx     #0
        bcc     @k
        ldx     #5
        lda     MAP+32          ; region 3, 4, 5: Burma, New Guinea, Bolivia
        cmp     #3
        bcc     @k
        cmp     #6
        bcs     @k
        ldx     #10
@k:     ldy     #0
:       lda     w_k_open,x
        sta     w_k,y
        inx
        iny
        cpy     #5
        bcc     :-
        lda     camp_minutes+1
        ldy     camp_minutes
        jsr     GIVAYF
        fop     FMULT, weather_frequency
        fop     FMULT, w_k
        fst     w_p
        jsr     water_random
        fop     FCOMP, w_p
        cmp     #1
        beq     @failed
        lda     #M_M56          ; idem: "YOU WERE SUCCESSFUL!" as the result
        sta     camp_last
        inc     camp_untreated
        jmp     water_source
@failed:
        lda     #M_M62
        jsr     camp_say
; $59A7: a GND COVER or RAINCOAT, by day under a clear sky, before sunset:
; "WHY DON'T YOU TRY TO MAKE WATER BY CONDENSATION ?" (msg 50), else msg 58.
water_hint:
        jsr     water_condense_ok
        bcc     water_m58
        lda     #M_M50
        jmp     camp_done
water_m58:
        lda     #M_M58
        jmp     camp_done

; water_condense_ok -- C set: a cover is present, it is AM or PM ($4B49 =
; 1) under a clear sky, and the hour after camp_minutes precedes sunset.
water_condense_ok:
        lda     it_place+11
        and     it_place+12
        cmp     #$FF
        beq     @no
        lda     period
        cmp     #2
        bcc     @no
        cmp     #4
        bcs     @no
        lda     weather_sky
        bne     @no
        lda     camp_minutes+1
        ldy     camp_minutes
        jsr     GIVAYF
        fop     FMULT, w_0_017
        fop     FADD, s_hour
        fop     FSUB, s_set     ; sunset - hour
        lda     FACSGN
        bmi     @no
        lda     FAC
        beq     @no
        sec
        rts
@no:    clc
        rts

.segment "CODE"
; Water piles (T0F/S00 $5ABC, $5DAE): resident (WILDERNESS) since the
; integration of lots 2, 7 and 13 (docs/MEMORY.md 13: SIM must end below
; $B500 with room to spare); DRINK runs them with SIM loaded.
; water_pile -- $5ABC/$5DAE: the pile on the cell grows by 160 oz unless it
; holds 321 oz or more; a pile left on another cell is abandoned (the port
; keeps one ground cell per item).
water_pile:
        ldx     #N_WATER
        jsr     at_ground
        bcc     @new
        lda     it_gnd_hi+N_WATER
        cmp     #2
        bcs     @total
        cmp     #1
        bcc     @add
        lda     it_gnd_lo+N_WATER
        cmp     #$41
        bcs     @total
@add:   clc
        lda     it_gnd_lo+N_WATER
        adc     #160
        sta     it_gnd_lo+N_WATER
        bcc     @total
        inc     it_gnd_hi+N_WATER
        bne     @total
@new:   jsr     water_cell
        lda     #160
        sta     it_gnd_lo+N_WATER
@total: lda     #160
        sta     w_avail
        lda     #0
        sta     w_avail+1
; water_total -- W5 = ground + canteen, and the place of the water.
water_total:
        clc
        lda     it_gnd_lo+N_WATER
        adc     it_pack_lo+N_WATER
        sta     it_oz_lo+N_WATER
        lda     it_gnd_hi+N_WATER
        adc     it_pack_hi+N_WATER
        sta     it_oz_hi+N_WATER
water_place:
        lda     #0              ; 0 ground only, 4 ground and canteen, 2 canteen
        ldx     it_gnd_lo+N_WATER
        bne     :+
        ldx     it_gnd_hi+N_WATER
        beq     @canteen
:       ldx     it_pack_lo+N_WATER
        bne     @both
        ldx     it_pack_hi+N_WATER
        beq     @store
@both:  lda     #4
        bne     @store
@canteen:
        lda     #2
@store: sta     it_place+N_WATER
        rts

; water_cell -- the pile of water moves to the player's cell (emptied when
; it was elsewhere).
water_cell:
        ldx     #N_WATER
        jsr     at_ground
        bcs     :+
        lda     #0
        sta     it_gnd_lo+N_WATER
        sta     it_gnd_hi+N_WATER
        lda     px+1
        sta     it_x+N_WATER
        lda     py+1
        sta     it_y+N_WATER
:       rts

; DRINK of RAIN, SNOW, ICE, or of WATER with none at hand (module_drink):
; C set when a source made a pile on the cell (a river: untreated).
drink_source:
        jsr     camp_begin
        lda     noun
        cmp     #N_WATER
        beq     @water
        jsr     water_named
        bcs     @pile
        lda     #M_M1
        jsr     camp_say
        clc
        rts
@water: jsr     water_here
        bcs     @pile
        jsr     no_item
        clc
        rts
@pile:  lda     camp_untreated
        sta     water_ground_untreated
        jsr     water_pile
        sec
        rts

.segment "CAMP"
; A source: the pile, the canteen (msg 57), the amount (FILL: up to 64 oz;
; GET: asked, at most 160, msg 64), the contamination, 64 oz (msg 186), the
; transfer from the pile, atomic against the load limits. water_take: FILL
; from the pile here, its whole amount available.
water_source:
        jsr     camp_sim
        jsr     water_pile
        jmp     water_canteen
water_take:
        lda     it_gnd_lo+N_WATER
        sta     w_avail
        lda     it_gnd_hi+N_WATER
        sta     w_avail+1
water_canteen:
        ldx     #64
        jsr     have
        bcs     :+
        lda     #M_M57
        jmp     camp_done
:       lda     #0
        sta     msgnum+1
        sec
        lda     #64
        sbc     it_pack_lo+N_WATER
        ldx     it_pack_hi+N_WATER
        beq     :+
        lda     #0
:       bcs     :+
        lda     #0
:       sta     w_room
        sta     msgnum
        lda     camp_fill
        beq     @ask
        lda     w_room          ; FILL of a full canteen
        bne     @amount
        lda     #M_M186
        sta     camp_last
        bne     @amount
@ask:   lda     w_avail+1       ; GET (16 October 2026, not the original's
        bne     :+              ; question): as much as the source, the
        lda     w_avail         ; canteen's room and the weight left allow
        cmp     msgnum
        bcs     :+
        sta     msgnum
:       jsr     load_totals
        sec
        lda     load_limits
        sbc     load_used
        tax
        lda     load_limits+1
        sbc     load_used+1
        bcc     @heavy
        bne     :+
        cpx     msgnum
        bcs     :+
        stx     msgnum
:       lda     msgnum
        beq     :+
        lda     #$80            ; "YOU TOOK n OUNCES." at the end
        sta     camp_fill
        bne     @amount
:       lda     #M_M186         ; the canteen full
        ldx     w_room
        beq     @full
@heavy: lda     #M_HEAVY
        jmp     camp_done
@full:  sta     camp_last
@amount:
        lda     camp_untreated  ; $5B38: B2[22] AND $4B48
        beq     :+
        lda     #1
        sta     water_untreated
:       lda     msgnum
        cmp     w_room
        bcc     @transfer
        beq     @transfer
        lda     w_room
        sta     msgnum
        lda     #M_M186
        sta     camp_last
@transfer:
        lda     it_pack_lo+N_WATER
        sta     w_old
        lda     it_gnd_lo+N_WATER
        sta     w_old+1
        lda     it_gnd_hi+N_WATER
        sta     w_old+2
        clc
        lda     it_pack_lo+N_WATER
        adc     msgnum
        sta     it_pack_lo+N_WATER
        sec
        lda     it_gnd_lo+N_WATER
        sbc     msgnum
        sta     it_gnd_lo+N_WATER
        bcs     :+
        dec     it_gnd_hi+N_WATER
:       jsr     water_place
        jsr     load_totals     ; SIM lives at $9600, so this module survives
        lda     load_bad
        bne     @rollback
        ldx     #6
@capacity:
        lda     load_limits+1,x
        cmp     load_used+1,x
        bcc     @rollback
        bne     @next
        lda     load_limits,x
        cmp     load_used,x
        bcc     @rollback
@next:  dex
        dex
        bpl     @capacity
        lda     camp_last       ; (the source's words: SUCCESSFUL, cacti...)
        bit     camp_fill       ; GET (16 October 2026): then the ounces
        bpl     :+              ; taken, instead of OK
        cmp     #M_OK
        beq     @took
        jsr     camp_say
@took:  lda     #w_took
        jsr     camp_say_tb
        lda     #0
:       jmp     camp_done
@rollback:
        lda     w_old
        sta     it_pack_lo+N_WATER
        lda     w_old+1
        sta     it_gnd_lo+N_WATER
        lda     w_old+2
        sta     it_gnd_hi+N_WATER
        jsr     water_place
        jsr     load_totals
        lda     #M_HEAVY
        jmp     camp_done

; MAKE WATER ($59A7, $5A09): the condensation conditions (msg 58), a GND
; COVER or RAINCOAT in use (msg 25), the time; INT(.1 x t + .5) oz with t
; bounded by 60 x (sunset - hour - .5), on the ground; t + 30 minutes.
make_water:
        jsr     water_condense_ok
        jcc     water_m58
        lda     camp_use
        and     #U_COVER
        bne     :+
        lda     #M_M25
        jmp     camp_done
:       lda     #<w_m27
        ldx     #>w_m27
        jsr     camp_duration
        bcc     :+
        rts
:
        jsr     camp_effort1
        jsr     camp_sim
        fld     s_hour
        jsr     FADDH
        fop     FSUB, s_set     ; sunset - (hour + .5)
        fop     FMULT, f_60
        fst     w_p
        lda     minutes+1
        ldy     minutes
        jsr     GIVAYF
        fop     FCOMP, w_p
        cmp     #$FF
        beq     :+
        fld     w_p
:       fop     FMULT, w_0_1
        jsr     FADDH
        jsr     AYINT
        lda     $A1
        sta     msgnum
        lda     $A0
        sta     msgnum+1
        jsr     water_cell
        clc
        lda     it_gnd_lo+N_WATER
        adc     msgnum
        sta     it_gnd_lo+N_WATER
        lda     it_gnd_hi+N_WATER
        adc     msgnum+1
        sta     it_gnd_hi+N_WATER
        jsr     water_total
        clc
        lda     minutes
        adc     #30
        sta     camp_minutes
        lda     minutes+1
        adc     #0
        sta     camp_minutes+1
        lda     #M_M63
        jmp     camp_done

; BOIL WATER ($5BD4): from the canteen, else the pile here; the amount
; (msg 64), UTENSILS in use (25), a STOVE in use or a fire (65); 15 minutes
; of effort .01; boiled canteen water is set down on the cell ($03 = 8);
; care selector 22 (the giardia prevention of T06/S00).
camp_boil:
        lda     noun
        cmp     #N_WATER
        beq     :+
        jmp     camp_notyet
:       ldx     #N_WATER
        jsr     have
        bcs     :+
        jmp     no_item
:       lda     it_pack_lo+N_WATER
        sta     w_avail
        lda     it_pack_hi+N_WATER
        sta     w_avail+1
        ora     w_avail
        sta     w_room          ; nonzero: from the canteen
        bne     :+
        lda     it_gnd_lo+N_WATER
        sta     w_avail
        lda     it_gnd_hi+N_WATER
        sta     w_avail+1
:       jsr     water_amount
        lda     camp_use
        and     #U_UTENS
        bne     :+
        lda     #M_M25
        jmp     camp_done
:       lda     camp_use
        and     #U_STOVE
        ora     fire_on
        bne     :+
        lda     #M_M65
        jmp     camp_done
:       jsr     camp_sim
        lda     w_room
        beq     @boil           ; the pile here stays where it is
        jsr     water_cell
        sec
        lda     it_pack_lo+N_WATER
        sbc     msgnum
        sta     it_pack_lo+N_WATER
        lda     it_pack_hi+N_WATER
        sbc     msgnum+1
        sta     it_pack_hi+N_WATER
        clc
        lda     it_gnd_lo+N_WATER
        adc     msgnum
        sta     it_gnd_lo+N_WATER
        lda     it_gnd_hi+N_WATER
        adc     msgnum+1
        sta     it_gnd_hi+N_WATER
        jsr     water_total
        jsr     load_totals
@boil:  lda     #22
        sta     camp_med
        lda     #15
        sta     camp_minutes
        jsr     camp_effort1
        jmp     camp_end

; water_amount -- the ounces (msgnum); returns only with a valid amount:
; zero (msg 2), more than w_avail (msg 64, $5B80) or ESC end the command.
water_amount:
        lda     #N_WATER        ; RAIN, SNOW, ICE: the prompt names the water
        sta     noun
        lda     #<m_ounces
        ldx     #>m_ounces
        jsr     camp_quantity
        bcs     @quiet
        lda     msgnum
        ora     msgnum+1
        bne     :+
        lda     #M_M2
        bne     @refuse
:       lda     w_avail
        cmp     msgnum
        lda     w_avail+1
        sbc     msgnum+1
        bcc     @over           ; C clear only when msgnum > w_avail
        rts
@over:  lda     w_avail
        sta     msgnum
        lda     w_avail+1
        sta     msgnum+1
        lda     #M_M64
@refuse:
        tax
        pla                     ; the command ends here (camp_done reports)
        pla
        txa
        jmp     camp_done
@quiet: pla
        pla
        lda     #0
        jmp     camp_done

; water_yes -- A/X = question [Y/N]: Z set for Y (prompt and key, as QUIT).
water_yes:
        jsr     camp_say
        jsr     water_confirm
        ldx     #0
        stx     camp_said       ; the answer starts a new message
        cmp     #'Y'
        rts

FADDH = $E7A0                   ; FAC <- FAC + .5
w_p:    .res 5
w_k:    .res 5
w_old:  .res 3
w_k_open:   .byte $75,$2D,$03,$D9,$A9  ; .00033 ($5D77)
w_k_woods:  .byte $76,$59,$94,$5B,$6D  ; .00083 ($5D81)
w_k_tropic: .byte $79,$03,$12,$6E,$98  ; .004 ($5D7C)
w_0_017:    .byte $7B,$0B,$43,$95,$82  ; .017 ($5D8B)
w_0_1:      .byte $7D,$4C,$CC,$CC,$CD  ; .1 ($5EBD)
.segment "LOWCODE"
; Resident water helpers (DRINK reaches them without CAMP; foraging and
; fishing will test the same river or lake).
; water_here -- C set at a river or lake (msg 61, answered yes): the
; player's native cell, or on a legacy map this cell or an adjacent bank.
water_here:
        lda     MAP+37
        beq     @legacy
        jsr     camp_cell
        asl     a
        bcc     @rts
        inc     camp_untreated
@rts:   rts
@legacy:
        lda     py+1
        sec
        sbc     #1
        sta     w_y
        lda     #3
        sta     w_rows
@row:   lda     px+1
        sec
        sbc     #1
        sta     w_x
        lda     #3
        sta     w_cols
@cell:  ldx     w_y
        cpx     #GH
        bcs     @next
        ldy     w_x
        cpy     #GW
        bcs     @next
        jsr     cell_at
        bmi     @yes
@next:  inc     w_x
        dec     w_cols
        bne     @cell
        inc     w_y
        dec     w_rows
        bne     @row
        clc
        rts
@yes:   inc     camp_untreated
        sec
        rts

; water_named -- C set when RAIN falls ($4B4C = 2), or for SNOW and ICE when
; it snows or the ground is snowy ($5813-$5834).
water_named:
        ldx     weather_sky
        lda     noun
        cmp     #169
        bne     @snow
        cpx     #2
        beq     @yes
@no:    clc
        rts
@snow:  cpx     #3
        beq     @yes
        jsr     level_here
        cmp     M_SNOW
        bcc     @no
@yes:   sec
        rts

; water_random -- the shared RND ($0321), SIM loaded.
.segment "CAMP"                ; only collection calls this helper
water_random:
        lda     #3
        jsr     overlay_load
        jmp     weather_random

.segment "LOWTEXT"
w_x:    .res 1
w_y:    .res 1
w_rows: .res 1
.segment "TEXT"                ; one transient byte, keeps LOW within 4 KB
w_cols: .res 1
.segment "LOWTEXT"
; Original messages (msg n of Journey), resident: other lots reuse them.

.segment "CAMP"
        UI_TWO water_confirm, 'N', 'Y'
