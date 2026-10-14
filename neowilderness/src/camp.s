; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Fire and light (lot 2, docs/CAMP.md): Journey T11/S00 $5964-$5B7D (MAKE
; and USE of MATCHES, GLASS, FUEL, STICKS, FIRE), the core's DOUSE/STOP FIRE
; ($51D3), the light of T0D/S07 ($5BB7) and the USE of FLASHLIGHT, STOVE,
; UTENSILS, GND COVER and RAINCOAT ($5CCD-$5DA9). The water rules (T0F/S00)
; share the module: src/water.s. Messages are the original's (msg n).
;
; Resident state, contiguous for a saved game (camp_state..camp_state_end):
;   camp_use   the "in use" flags B2 of the camp items (U_*); MATCHES, GLASS,
;              FUEL and FLASHLIGHT lose theirs whenever time passes (probe:
;              WAIT 1 clears B2 of 38-42, 51, 52, 54-57, 66, 68, 69, 74)
;   fire_on    a fire burns on the player's cell (second-set B1[FIRE] = 0);
;              no coordinates: M5 forbids leaving it ($58B5, msg 132)
;   fire_near  USE FIRE: near the fire (B2[FIRE], $45E9), +25 F in THERMAL
;   sticks_on  STICKS made (second-set B1[STICKS]): 1 ground, 3 carried
;   light      $0D5D: daylight, dawn/dusk under a clear sky, or MATCHES or
;              FLASHLIGHT in use; set by USE FIRE/MATCHES/FLASHLIGHT,
;              recomputed at each health step (camp_light, THERMAL)
U_MATCH  = 1
U_GLASS  = 2
U_FUEL   = 4
U_FLASH  = 8
U_STOVE  = 16
U_UTENS  = 32
U_COVER  = 64
U_KEEP   = U_STOVE|U_UTENS|U_COVER  ; flags that survive the passing of time
N_STICKS = 87
N_FIRE   = 88
SNGFLT   = $E301                ; FAC <- Y (unsigned)
DIV10    = $EA55                ; FAC <- FAC / 10

.segment "LOWTEXT"
camp_state:
camp_use:   .byte 0
fire_on:    .byte 0
fire_near:  .byte 0
sticks_on:  .byte 0
light:      .byte 1             ; the first journey starts in daylight
; DRINK_FIDELITY (src/game.s): $4C7A, the saved 70/120 until the first
; midnight, then the day's maximum / 120 (T0C/S03 $5C9B).
s_sweat:    .byte $80,$15,$55,$55,$56
sweat_day:  .byte 0             ; 1 after the first midnight
camp_state_end:
camp_minutes: .word 0           ; time of the action (camp_done)
camp_act:   .byte 0             ; its activity (spend): 0 rest rate, 6 effort
camp_med:   .byte 0             ; care selector set by the action (0: none)
camp_said:  .byte 0             ; messages already printed by this command
; Kept across the numeric prompts (INPUT takes the window; CAMP is reloaded
; from its image).
camp_last:  .byte 0             ; message number of a successful end
camp_fill:  .byte 0             ; FILL/REFILL: as much as the canteen holds
camp_untreated: .byte 0         ; the source is untreated ($4B48 = 0)
w_avail:    .word 0             ; ounces available (msg 64)
w_room:     .byte 0             ; canteen room; BOIL: nonzero from the canteen
camp_douse_msg: .byte "SMOKEY THE BEAR SAYS TO DOUSE YOUR FIRE FIRST",$A1,0
.export camp_state, camp_state_end, camp_use, fire_on, fire_near, sticks_on, light, s_sweat

.segment "LOWCODE"
; Verbs without an entry of their own in the dispatch table (the table is
; resident and VOCAB is full): MAKE/BUILD (3) and BOIL (9) load CAMP.
camp_verb:
        lda     verb
        cmp     #3
        beq     camp_command
        cmp     #9
        beq     camp_command
        lda     #<m_notyet
        ldx     #>m_notyet
        jmp     message
; Also the USE and DOUSE/STOP that the medical module does not handle.
camp_command:
        lda     #4
        jsr     overlay_load
        jmp     module_camp

; WALK, RUN, MOVE, CRAWL, SWIM (T08/S00 $58B5): refused while a fire burns
; on the cell, unless an animal shares it ($4B72). Otherwise returns the
; flags of LDA night, the instruction it replaces in do_walk.
camp_walk:
        lda     fire_on
        beq     @night
        lda     animal_kind
        beq     @douse
        lda     animal_x
        cmp     px+1
        bne     @douse
        lda     animal_y
        cmp     py+1
        beq     @night
@douse: pla
        pla
        lda     #<camp_douse_msg
        ldx     #>camp_douse_msg
        jmp     message
@night: lda     night
        rts

; camp_say -- A = message number (M_*): the first of the command clears the
; result column, the next ones follow it (the original prints each in turn).
camp_say:
        asl     a
        tay
        ldx     camp_msgs-1,y
        lda     camp_msgs-2,y
        ldy     camp_said
        inc     camp_said
        cpy     #0
        bne     :+
        jmp     message
:       sta     gp1
        stx     gp1+1
        lda     #' '|$80
        jsr     msg_char
        jmp     message_body

; camp_done -- A = last message number (0: none), then the care selector
; camp_med (medical module, as T06/S00 does for $4B41 = 1), then
; camp_minutes at activity camp_act in steps of the health period, then the
; common report. The module may be replaced from the selector on.
camp_done:
        cmp     #0
        beq     :+
        jsr     camp_say
:       ldx     camp_med
        beq     @time
        lda     #1
        sta     medical_actions-1,x
        jsr     medical_apply
@time:  lda     camp_minutes+1
        bne     @full
        lda     camp_minutes
        beq     @done
        cmp     health_period
        bcc     @last
@full:  lda     health_period
@last:  sta     stepmin
        sec
        lda     camp_minutes
        sbc     stepmin
        sta     camp_minutes
        bcs     :+
        dec     camp_minutes+1
:       lda     stepmin
        ldx     camp_act
        jsr     spend
        lda     dead
        ora     fauna_alert
        beq     @time
@done:  jmp     report

; Bridges for the numeric prompts of INPUT, which take the $5800 window
; (and ADVENTURE for the hours: prepare_minutes): CAMP is reloaded with the
; carry preserved (C set: cancelled); the next message starts afresh.
camp_quantity:
        jsr     get_quantity
        jmp     camp_back
camp_duration:
        jsr     get_duration
        bcs     camp_back
        jsr     prepare_minutes ; minutes
        clc
camp_back:
        php
        lda     #0
        sta     camp_said
        lda     #4
        jsr     overlay_load
        plp
        rts

; camp_begin -- a new command: no time, no selector, no message yet.
camp_begin:
        lda     #0
        sta     camp_minutes
        sta     camp_minutes+1
        sta     camp_med
        sta     camp_act
        sta     camp_said
        sta     camp_fill
        sta     camp_untreated
        sta     water_ground_untreated  ; ground water is safe ($587C)
        lda     #M_OK
        sta     camp_last
        rts

; camp_sim -- SIM loaded (the water piles live there).
camp_sim:
        lda     #3
        jmp     overlay_load
; camp_cell -- native_here (in SIM: the star module may hold the window at
; night): A = the player's cell, N = water.
camp_cell:
        jsr     camp_sim
        jmp     native_here

; Helpers shared with the later lots (crafting, foraging use the same
; ground class, storm test and effort of an action).
; camp_storm -- C set in rain ($4B4C = 2) or with a wind of 41 mph and more.
camp_storm:
        lda     weather_sky
        cmp     #2
        beq     @yes
        lda     wind
        cmp     #41
        rts
@yes:   sec
        rts

; camp_class -- A = the original ground class $4B56 of the player's cell:
; 3 water, 1 woods, 2 rocky (bare, level 96 and above, as STATUS), 0 clear.
camp_class:
        jsr     camp_cell
        bpl     :+
        lda     #3
        rts
:       jsr     woods_here
        lda     #1
        bcs     @done
        jsr     level_here
        cmp     #96
        lda     #2
        bcs     @done
        lda     #0
@done:  rts

; camp_effort2/1 -- the effort of the action ($5E33, $5D49): the activity
; rate 1.65 + k x the total weight in pounds (body + load / 16).
camp_effort2:
        lda     #<c_0_02
        ldy     #>c_0_02
        bne     camp_effort
camp_effort1:
        lda     #<c_0_01
        ldy     #>c_0_01
camp_effort:
        sta     gp2
        sty     gp2+1
        lda     load_used+1
        sta     g1
        lda     load_used
        ldx     #4
:       lsr     g1
        ror     a
        dex
        bne     :-
        clc
        adc     body_weight
        tay
        lda     g1
        adc     body_weight+1
        jsr     GIVAYF
        lda     gp2
        ldy     gp2+1
        jsr     FMULT
        fop     FADD, f_rest_rate
        fst     s_metabolic
        lda     #6
        sta     camp_act
        rts

c_0_02: .byte $7B,$23,$D7,$0A,$3E      ; T11/S00 $5E2E
c_0_01: .byte $7A,$23,$D7,$0A,$3E      ; T0F/S00 $5EB8


; SIM must end below $B500 (the loader's record table, read again at the end
; of a game): the light and the limit of a drink live in the resident CODE.
.segment "CODE"
; drink_limit -- T0F/S00 $5C26: more than .2 x body weight at once is refused
; ("DON'T BE RIDICULOUS!", msg 87). C set: refused.
drink_limit:
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FMULT, f_0_2
        fst     t1
        lda     msgnum+1
        ldy     msgnum
        jsr     GIVAYF
        fop     FCOMP, t1
        cmp     #1
        clc
        bne     :+
        lda     #<m_ridiculous
        ldx     #>m_ridiculous
        jsr     message
        sec
:       rts
m_ridiculous: .byte "DON'T BE RIDICULOUS",$A1,0   ; msg 87, T0F/S00 $5C4B
.if DRINK_FIDELITY
; drink_credit -- FAC = msgnum x (.73 - .6 x $4C7A), the ROM operations of
; T0F/S00 $5CAD-$5CD4 (constants $5D95, $5D9A).
drink_credit:
        fld     s_sweat
        fop     FMULT, dr_0_6
        fop     FSUB, dr_0_73
        fst     t1
        ldy     msgnum
        lda     msgnum+1
        jsr     GIVAYF
        fop     FMULT, t1
        rts
; drink_care -- $5CED: $4B41 = 1, $4B42 = 6: care selector 6.
drink_care:
        lda     #1
        sta     medical_actions+5
        jmp     medical_apply
; sweat_update -- T0C/S03 $5C9B, from the first midnight on: $4C7A = the
; day's maximum (signed) / 120. Called by weather_temperature (SIM).
sweat_update:
        lda     sweat_day
        beq     @done
        ldy     wc_max
        lda     #0
        cpy     #$80
        bcc     :+
        lda     #$FF
:       jsr     GIVAYF
        fop     FMULT, dr_inv120
        fst     s_sweat
@done:  rts
dr_0_6:    .byte $80,$19,$99,$99,$9A    ; T0F/S00 $5D95
dr_0_73:   .byte $80,$3A,$E1,$47,$AE    ; T0F/S00 $5D9A
dr_inv120: .byte $7A,$08,$88,$88,$89    ; T0C/S03 $5E64
.endif
; camp_light -- $0D5D at the health step (T0D/S07 $5BB7): 1 by day (AM, PM),
; at dawn and dusk under a clear sky, else only with MATCHES or FLASHLIGHT
; in use. A fire gives light only through USE FIRE, until this step.
camp_light:
        lda     period          ; 0 night, 1 dawn, 2 am, 3 pm, 4 dusk
        beq     @items
        cmp     #1
        beq     @twilight
        cmp     #4
        bne     @on
@twilight:
        lda     weather_sky
        beq     @on
@items: lda     camp_use
        and     #U_MATCH|U_FLASH
        beq     @off
@on:    lda     #1
        .byte   $2C             ; BIT abs: skip the next LDA
@off:   lda     #0
        sta     light
        rts

.segment "CAMP"
; Entry for MAKE/BUILD, BOIL, USE and DOUSE/STOP (camp_verb, camp_command).
module_camp:
        jsr     camp_begin
        lda     verb
        cmp     #3
        jeq     camp_make
        cmp     #9
        jeq     camp_boil
        cmp     #26
        beq     camp_stop
        ldx     noun            ; USE
        cpx     #N_FIRE
        jeq     use_fire
        cpx     #N_STICKS
        jeq     use_sticks
        ldy     #cu_lo-cu_item-1
@find:  txa
        cmp     cu_item,y
        beq     camp_item
        dey
        bpl     @find
camp_notyet:
        lda     #<m_notyet
        ldx     #>m_notyet
        jmp     message
camp_item:
        sty     camp_k
        jsr     have            ; X = noun
        bcs     :+
        jmp     no_item
:       ldy     camp_k
        lda     cu_lo,y
        sta     gp1
        lda     cu_hi,y
        sta     gp1+1
        jmp     (gp1)
cu_item: .byte  38, 39, 40, 66, 71, 73, 11, 12
cu_lo:  .byte   <use_matches, <use_glass, <use_fuel, <use_flash
        .byte   <use_stove, <use_utensils, <use_cover, <use_cover
cu_hi:  .byte   >use_matches, >use_glass, >use_fuel, >use_flash
        .byte   >use_stove, >use_utensils, >use_cover, >use_cover

; DOUSE/STOP FIRE (core $51D3): the fire goes out, no time; also without one.
camp_stop:
        lda     noun
        cmp     #N_FIRE
        bne     camp_notyet
        lda     #0
        sta     fire_on
        sta     fire_near
camp_end:
        lda     camp_last
        jmp     camp_done

; USE MATCHES / STICKS / FIRE ($59FC-$5A62): inside a shelter "PLEASE BE
; CAREFUL." and nothing else is checked; in water (78); rain or wind of
; 41 mph and more without FUEL in use (79). Returns only when permitted.
use_checks:
        lda     shelter_inside
        beq     :+
        lda     #M_M77
        jmp     camp_say
:       jsr     camp_cell
        bpl     :+
        pla
        pla
        lda     #M_M78
        jmp     camp_done
:       jsr     camp_storm
        bcc     camp_rts
        lda     camp_use
        and     #U_FUEL
        bne     camp_rts
        pla
        pla
camp_m79:
        lda     #M_M79
        jmp     camp_done
camp_rts:
        rts

use_matches:
        jsr     use_checks
        lda     #1              ; $5B14: light before the transaction
        sta     light
use_fuel:
        ; $5AF0: one use or ounce goes (T0E/S02); an empty stock prints
        ; msg 88 and the item is not in use.
        ldx     noun
        lda     it_pack_hi,x
        bmi     @empty
        ora     it_pack_lo,x
        beq     @empty
        lda     it_pack_lo,x
        bne     :+
        dec     it_pack_hi,x
:       dec     it_pack_lo,x
        jsr     camp_bit
        ora     camp_use
        sta     camp_use
        jmp     camp_hand
@empty: jsr     camp_bit
        eor     #$FF
        and     camp_use
        sta     camp_use
        lda     #M_M88
        jsr     camp_say
camp_hand:
        ldx     noun            ; the item goes to the hand (B1 = 3)
        lda     #3
        sta     it_place,x
        jsr     load_totals
        jmp     camp_end

; camp_bit -- A = the U_ flag of noun 38, 39, 40 or 66.
camp_bit:
        lda     noun
        cmp     #66
        beq     @flash
        sec
        sbc     #37             ; 1, 2, 3
        cmp     #3
        bne     :+
        lda     #U_FUEL
:       rts
@flash: lda     #U_FLASH
        rts

; USE GLASS ($59DC): clear sky, outside a shelter, sun at 30 degrees or
; more; else msg 53. 15 minutes, in the hand; the flag lasts until time
; passes, so that the glass never lights a fire (probe: msg 25 after it).
use_glass:
        lda     weather_sky
        ora     shelter_inside
        ora     night
        bne     @dark
        lda     #3
        jsr     overlay_load
        jsr     sky_position
        fld     sky_up          ; sine of the sun's altitude
        fop     FCOMP, f_half   ; sin 30
        cmp     #$FF
        beq     @dark
        lda     camp_use
        ora     #U_GLASS
        sta     camp_use
        lda     #15
        sta     camp_minutes
        jmp     camp_hand
@dark:  lda     #M_M53
        jmp     camp_done

; USE FLASHLIGHT ($5D00): batteries left (W8[66]) or msg 83; light.
use_flash:
        lda     it_pack_lo+66
        ora     it_pack_hi+66
        bne     :+
        lda     #M_M83
        jmp     camp_done
:       lda     #1
        sta     light
        jmp     use_fuel

; USE STOVE ($5D1D): FUEL in use and a fire or MATCHES in use (msg 85);
; USE UTENSILS. Each is set down on the cell ($5D95: DROP), 30 or 15
; minutes, or no time when it already lies here.
use_stove:
        lda     camp_use
        and     #U_FUEL
        beq     @refused
        lda     fire_near
        bne     @ok
        lda     camp_use
        and     #U_MATCH
        bne     @ok
@refused:
        lda     #M_M85
        jmp     camp_done
@ok:    lda     #U_STOVE
        ldy     #30
        bne     camp_set_down
use_utensils:
        lda     #U_UTENS
        ldy     #15
camp_set_down:
        ora     camp_use
        sta     camp_use
        ldx     noun
        lda     it_place,x
        jeq     camp_end        ; already on the ground here: msg 10 only
        sty     camp_minutes
        lda     #0
        sta     it_place,x
        lda     px+1
        sta     it_x,x
        lda     py+1
        sta     it_y,x
        jsr     load_totals
        jmp     camp_end

; USE GND COVER / RAINCOAT ($58F6): spread for condensation (B2 = 1).
; The original also lays them on the ground; the port leaves them in place.
use_cover:
        lda     camp_use
        ora     #U_COVER
        sta     camp_use
        jmp     camp_end

; USE STICKS ($5B59): 30 minutes of effort, into the hand.
use_sticks:
        lda     sticks_on
        beq     camp_absent
        jsr     use_checks
        lda     #3
        sta     sticks_on
        lda     #30
        sta     camp_minutes
        jsr     camp_effort2
        jmp     camp_end
camp_absent:
        lda     #M_M1
        jmp     camp_done

; USE FIRE ($5B2E): near the fire (+25 F), light, health steps of 15
; minutes ($4BCC), care selector 24; no time.
use_fire:
        lda     fire_on
        beq     camp_absent
        jsr     use_checks
        lda     #15
        sta     health_period
        lda     #1
        sta     light
        sta     fire_near
        lda     #24
        sta     camp_med
        jmp     camp_end

; MAKE/BUILD ($5964): MATCHES, GLASS, FUEL: "YOU ALREADY HAVE." (msg 11)
; or msg 75; STICKS; FIRE; WATER (condensation, src/water.s).
camp_make:
        ldx     noun
        cpx     #N_FIRE
        beq     make_fire
        cpx     #N_STICKS
        beq     make_sticks
        cpx     #N_WATER
        jeq     make_water
        cpx     #38
        bcc     @no
        cpx     #41
        bcs     @no
        lda     it_place,x
        cmp     #$FF
        bne     camp_already
        lda     #M_M75
        jmp     camp_done
@no:    jmp     camp_notyet
camp_already:
        lda     #M_M11
        jmp     camp_done

; MAKE STICKS ($5998): clear ground or woods (class < 2), else msg 76;
; 30 minutes of effort, the sticks on the ground.
make_sticks:
        lda     sticks_on
        bne     camp_already
        jsr     camp_class
        cmp     #2
        bcs     camp_m76
        lda     #1
        sta     sticks_on
camp_made:
        lda     #30
        sta     camp_minutes
        jsr     camp_effort2
        lda     #M_M15
        jmp     camp_done
camp_m76:
        lda     #M_M76
        jmp     camp_done

; MAKE FIRE ($5A09-$5AED): not in water (78), not on snowy rocky ground
; (76); MATCHES or GLASS in use (25); in rain or a wind of 41 mph and
; more, FUEL in use or a shelter (79). The match is spent, the fire burns
; on the cell, care selector 24, 30 minutes of effort, msg 15.
make_fire:
        lda     fire_on
        bne     camp_already
        jsr     camp_class
        cmp     #3
        bne     :+
        lda     #M_M78
        jmp     camp_done
:       cmp     #2
        bne     @lit
        jsr     level_here
        cmp     M_SNOW
        bcs     camp_m76
@lit:   lda     camp_use
        and     #U_MATCH|U_GLASS
        bne     :+
        lda     #M_M25
        jmp     camp_done
:       jsr     camp_storm
        bcc     @burn
        lda     camp_use
        and     #U_FUEL
        ora     shelter_inside
        jeq     camp_m79
@burn:  lda     camp_use
        and     #<~U_MATCH
        sta     camp_use
        lda     #1
        sta     fire_on
        lda     #24
        sta     camp_med
        jmp     camp_made

camp_k:     .res 2
.segment "LOWTEXT"
; Original messages (msg n of Journey), resident: other lots reuse them.

; Message numbers (camp_say, camp_done): 1 + index in camp_msgs.
M_OK = 1
M_M1 = 2
M_M11 = 3
M_M15 = 4
M_M25 = 5
M_M53 = 6
M_M75 = 7
M_M76 = 8
M_M77 = 9
M_M78 = 10
M_M79 = 11
M_M83 = 12
M_M85 = 13
M_M88 = 14
M_M2 = 15
M_M27 = 16
M_M50 = 17
M_M55 = 18
M_M56 = 19
M_M57 = 20
M_M58 = 21
M_M62 = 22
M_M63 = 23
M_M64 = 24
M_M65 = 25
M_M179 = 26
M_M186 = 27
M_HEAVY = 28
camp_msgs:
        .addr   m_ok
        .addr   c_m1
        .addr   c_m11
        .addr   c_m15
        .addr   c_m25
        .addr   c_m53
        .addr   c_m75
        .addr   c_m76
        .addr   c_m77
        .addr   c_m78
        .addr   c_m79
        .addr   c_m83
        .addr   c_m85
        .addr   c_m88
        .addr   w_m2
        .addr   w_m27
        .addr   w_m50
        .addr   w_m55
        .addr   w_m56
        .addr   w_m57
        .addr   w_m58
        .addr   w_m62
        .addr   w_m63
        .addr   w_m64
        .addr   w_m65
        .addr   w_m179
        .addr   w_m186
        .addr   w_heavy
c_m1:   .byte "SORRY, THAT ITEM IS NOT AVAILABLE.",0
c_m11:  .byte "YOU ALREADY HAVE.",0
c_m15:  .byte "IT TOOK A WHILE TO MAKE YOUR ^.",0
c_m25:  .byte "USE THE APPROPRIATE ITEM FIRST.",0
c_m53:  .byte "SORRY, THERE IS INSUFFICIENT LIGHT.",0
c_m75:  .byte "NO DOUBT POSSIBLE, BUT BEYOND THE SCOPE OF THE GAME.",0
c_m76:  .byte "SORRY, SUFFICIENT RAW MATERIAL IS NOT AVAILABLE.",0
c_m77:  .byte "PLEASE BE CAREFUL.",0
c_m78:  .byte "SORRY, NOT PERMITTED IF YOU ARE IN OR ON WATER.",0
c_m79:  .byte "SORRY, TOO MUCH RAIN OR WIND.",0
c_m83:  .byte "SORRY, THE BATTERIES ARE USED UP.",0
c_m85:  .byte "YOU NEED BOTH FUEL AND FIRE.",0
c_m88:  .byte "THE ^ HAS BEEN USED UP.",0
