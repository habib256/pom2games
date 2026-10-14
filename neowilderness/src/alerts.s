; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Fidelity lot 13 (medicine):
;   - the original's health alerts (T0A/S0C $5BED, T0B/S02, T0B/S0D): the
;     rules and texts in the ALERT module (ID 27, docs/MEMORY.md 13), loaded
;     after the health update (which has just replaced the $5800 window with
;     MED) and after a command that queued an alert; their state resident;
;   - the forced sleep of an exhausted player (parser $0B, T15/S0B $585F),
;     resident (it loads SIM and MED);
;   - the infection and malaria onsets of T0B/S07 ($5B3F, $5B8D), in SIM;
;   - the resident bridges of the care commands (care.s, WILDMVI).
; See docs/IMPLEMENTATION.md, "Soins, alertes et maladies (lot 13)".

.segment "LOWTEXT"
; Persistent care state, contiguous for the save of lot 9.
care_state:
al_daily:     .byte 0          ; once a day: 1 hunger 173, 2 thirst 174, 4 tired 175 ($4B88-$4B8A)
al_forced:    .byte 0          ; original $0B: next command is a forced sleep
al_eaten0:    .res 5           ; s_eaten / s_spent at the last midnight: the original
al_spent0:    .res 5           ; clears its daily $4BDC / $4BDA (T0A/S05 $5961)
al_drunk:     .word 10         ; $4BD4: ounces of the current drinking session (saved 10)
al_rest_h:    .word 7          ; $4BE2: hours of the current rest session (saved 7)
al_last:      .res 21,100      ; condition percentages 1..21 of the last health update
al_strong:    .byte 1          ; health above 1 at the last health update
care_tools:   .byte 0          ; B2 in use: 1 AXE (58), 2 KNIFE (59)
care_tool_x:  .byte $FF        ; square where they were put in use (T0C/S0B clears
care_tool_y:  .byte $FF        ; their B2 when the player leaves it)
splint_place: .byte $FF        ; lot 3 hook: second set item 93 (SPLINT), $FF absent, 1 worn
disease_triggers: .byte 1      ; H1 switch: infection and malaria onsets (T0B/S07)
care_state_end:
; Per command (not saved).
al_once:      .byte 0          ; 1 sweat/shiver 203/204 ($4B8B), 2 deterioration 187 ($4B8C)
al_events:    .byte 0          ; end-of-command events: 1 160, 2 175, 4 176, 8 177, 16 178
al_count:     .byte 0
al_queue:     .res 8
al_i:         .byte 0
al_w:         .word 0
al_k40:   .byte $86,$20,0,0,0
al_k300:  .byte $89,$16,0,0,0

ALERT_MODULE = 27
tb_buf:   .res 96               ; memory.s text_fetch (TB_MAX)

.segment "LOWCODE"
; ----------------------------------------------------------------------------
; spend: the health update, framed by the original alert rules (print only;
; except the forced sleep they write no simulation state). The health update
; leaves MED in the $5800 window and SIM loaded: the rules run in ALERT.
health_alerts:
        jsr     health
        lda     dead
        beq     :+
        rts
:       lda     #ALERT_MODULE
        jsr     overlay_load
        jmp     module_health_alerts
al_event:
        ora     al_events
        sta     al_events
        rts

.segment "ALERT"
module_health_alerts:
        ; T0A/S0C $5BED, before the thermal and health modules of the step.
        lda     al_daily
        lsr     a
        jcs     @thirst
        fld     s_eat           ; A2[17] > 12 h
        fop     FCOMP, f_12
        cmp     #1
        beq     @hungry
        fld     s_hour          ; 3 x kcal eaten today < (hour + 1) x weight
        fop     FADD, f_one
        fst     al_t1
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FMULT, al_t1
        fst     al_t1
        fld     al_eaten0
        fop     FSUB, s_eaten
        fst     al_t2           ; eaten today
        fop     FMULT, al_k3
        fop     FCOMP, al_t1
        cmp     #$FF
        bne     @thirst
        fld     al_spent0       ; and today's balance below -850 kcal
        fop     FSUB, s_spent
        fop     FSUB, al_t2
        fop     FCOMP, al_m850
        cmp     #$FF
        bne     @thirst
@hungry:
        lda     #1
        ora     al_daily
        sta     al_daily
        lda     #0              ; message 173
        jsr     al_add
@thirst:
        lda     al_daily
        and     #2
        bne     @forced
        fld     s_drink         ; A2[16] x $4C7A > 6
        fop     FMULT, al_sweat
        fst     al_t1
        fop     FCOMP, f_6
        cmp     #1
        beq     @thirsty
        fld     al_t1           ; oz of the session < 2 x A2[16] x $4C7A^2
        fop     FMULT, al_sweat
        fop     FMULT, al_k2
        fst     al_t1
        lda     al_drunk+1
        ldy     al_drunk
        jsr     GIVAYF
        fop     FCOMP, al_t1
        cmp     #$FF
        bne     @forced
@thirsty:
        lda     #2
        ora     al_daily
        sta     al_daily
        lda     #1              ; message 174
        jsr     al_add
@forced:
        fld     s_defr          ; A1[24] >= 60: $0B, event 43 (message 178)
        fop     FCOMP, al_k60
        cmp     #$FF
        beq     @tired
        lda     #1
        sta     al_forced
        lda     #16
        jsr     al_event
@tired: lda     al_daily
        and     #4
        bne     @thermal
        fld     s_rest          ; A2[18] > 16 h
        fop     FCOMP, al_k16
        cmp     #1
        beq     @weary
        lda     al_last+17      ; exhaustion of the last update below 95 %
        cmp     #95
        bcs     @thermal
        lda     al_rest_h+1     ; and 4 x hours of the last rest < A2[18]
        ldy     al_rest_h
        jsr     GIVAYF
        fop     FMULT, f_4
        fop     FCOMP, s_rest
        cmp     #$FF
        bne     @thermal
@weary: lda     #4
        ora     al_daily
        sta     al_daily
        lda     #2              ; event 40, message 175
        jsr     al_event
@thermal:
        ; T0B/S02 $5A35/$5A7D: one sweat/shiver message per timed command.
        lda     al_once
        lsr     a
        bcs     @conditions
        lda     thermal_mode
        beq     @conditions
        clc
        adc     #1              ; 1 sweating -> 2 (204), 2 shivering -> 3 (203)
        eor     #1              ; ids 3 = 204, 2 = 203
        jsr     al_add
        lda     #1
        ora     al_once
        sta     al_once
@conditions:
        ; T0B/S0D $5979: a percentage falling from 96 to under 95 (once per
        ; timed command, message 187), else from 51 to under 50 (event 25).
        jsr     al_percents
        ldx     #0
@compare:
        lda     al_last,x
        cmp     #96
        bcc     @serious
        lda     al_now,x
        cmp     #95
        bcs     @next
        lda     al_once
        and     #2
        bne     @next
        lda     #2
        ora     al_once
        sta     al_once
        stx     al_i
        lda     #4              ; message 187
        jsr     al_add
        ldx     al_i
        jmp     @next
@serious:
        cmp     #51
        bcc     @next
        lda     al_now,x
        cmp     #50
        bcs     @next
        lda     #1              ; event 25, message 160
        ora     al_events
        sta     al_events
@next:  lda     al_now,x
        sta     al_last,x
        inx
        cpx     #21
        bcc     @compare
        ; $59F3: health passing under 1 (event 41, message 176).
        fld     s_health
        fop     FCOMP, f_one
        ldx     #0
        cmp     #1
        bne     :+
        inx
:       cmp     #$FF
        bne     @strong
        lda     al_strong
        beq     @strong
        lda     #4
        jsr     al_event
@strong:
        stx     al_strong
        rts

; A = alert id (al_lo/al_hi); the queue keeps the original order of display.
al_add: ldx     al_count
        cpx     #8
        bcs     @full
        sta     al_queue,x
        inc     al_count
@full:  rts

; al_now <- percentages of conditions 1..21: the 15 conditions, the three
; deficits (native INT(100 (1 - (d/tol)^2))), altitude, hypo- and hyperthermia.
al_percents:
        ldx     #14
:       lda     injury_percent,x
        sta     al_now,x
        dex
        bpl     :-
        lda     #0
        sta     al_i
@deficit:
        ldx     al_i
        lda     cdef_lo,x
        ldy     cdef_hi,x
        jsr     MOVFM
        lda     #100
        ldx     FACSGN
        bmi     @store
        ldx     FAC
        beq     @store
        fst     al_t1
        ldx     al_i
        lda     ctol_lo,x
        ldy     ctol_hi,x
        jsr     MOVFM
        fop     FDIV, al_t1
        fst     al_t1
        fop     FMULT, al_t1
        fop     FSUB, f_one
        jsr     al_percent
@store: ldx     al_i
        sta     al_now+15,x
        inc     al_i
        lda     al_i
        cmp     #3
        bcc     @deficit
        lda     altitude_percent
        sta     al_now+18
        fld     s_therm_factor
        jsr     al_percent
        sta     al_i
        lda     #100
        sta     al_now+19
        sta     al_now+20
        fld     s_body
        fop     FCOMP, f_body
        ldx     #19             ; under 98.6: hypothermia, else hyperthermia
        cmp     #$FF
        beq     :+
        inx
:       lda     al_i
        sta     al_now,x
        rts
; A = INT(100 x FAC), 0..100 (native x10 twice, then INT).
al_percent:
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

; ----------------------------------------------------------------------------
al_show:
        lda     #0
        sta     al_i
@queue: ldx     al_i
        cpx     al_count
        bcs     @events
        lda     al_queue,x
        jsr     al_text
        inc     al_i
        bne     @queue
@events:
        lda     #0
        sta     al_count
        ldx     #5              ; ids 5..9: messages 160, 175, 176, 177, 178
@event: lsr     al_events
        bcc     :+
        txa
        pha
        jsr     al_text
        pla
        tax
:       inx
        cpx     #10
        bcc     @event
        rts

; Append alert A under the result (rows 20-23, column 40), in the first row
; left blank; an empty result column receives it as an ordinary message.
al_text:
        tax
        lda     al_lo,x
        sta     gp1
        lda     al_hi,x
        sta     gp1+1
        lda     shown
        beq     @fresh
        ldx     #MN_BOTTOM+1-MN_ROWS
@row:   txa
        jsr     t_bascalc
        ldy     #MN_RIGHT/2
        sta     PAGE2_AUX
        lda     (BASL),y
        sta     PAGE2_MAIN
        cmp     #' '|$80
        beq     @found
        inx
        cpx     #MN_BOTTOM+1
        bcc     @row
        jsr     keyboard_wait   ; full: the original waits for a key before
        jmp     @fresh          ; a further message of the same turn
@found: stx     CV
        jsr     t_vtab
        lda     #MN_RIGHT
        sta     CH
        lda     #0
        sta     msg_wlen
        jmp     message_text
@fresh: lda     gp1
        ldx     gp1+1
        jmp     message

; ----------------------------------------------------------------------------
.segment "LOWCODE"
; main loop, after a command: the queued alerts are appended to the result
; (ALERT module), then an exhausted player sleeps without input (parser
; $B033 with $0B).
alerts_after:
        lda     al_count
        ora     al_events
        beq     :+
        lda     #ALERT_MODULE
        jsr     overlay_load
        jsr     al_show
:       lda     #0
        sta     al_once         ; $4B84: once-per-command messages rearm
        lda     dead
        ora     won
        bne     @done
        lda     al_forced
        beq     @done
        jsr     al_sleep
        jmp     alerts_after
@done:  jmp     summary_refresh

; T15/S0B $585F: 180 + INT(RND x 300) minutes of REST at the base rate,
; or, in a river or lake, condition 14 and 15 minutes ($58A1, message 177).
al_sleep:
        lda     #0
        sta     al_forced
        sta     shown
        lda     #3
        jsr     overlay_load
        jsr     native_here
        asl     a
        bcs     @drown
        jsr     weather_random
        fop     FMULT, al_k300
        jsr     AYINT
        clc
        lda     $A1
        adc     #180
        sta     msgnum
        lda     $A0
        adc     #0
        sta     msgnum+1
        lda     #V_REST
        sta     verb
        lda     #2
        sta     input_argument  ; validated inline duration, in minutes
        sta     input_unit
        jsr     do_rest
        jmp     finish_simulation
@drown: lda     #17
        jsr     overlay_load
        ldx     #13
        jsr     module_injury_begin
        fld     al_k40          ; A1[24] = 40
        fst     s_defr
        lda     #8              ; event 42, message 177
        jsr     al_event
        lda     #15
        ldx     #0
        jsr     spend
        jsr     report
        jmp     finish_simulation

.segment "OUTDOOR"
; New day (module_medical_day, OUTDOOR): T0A/S05 $5952 rearms the three gauge
; messages and restarts the day's energy counters.
alerts_day:
        lda     #0
        sta     al_daily
        ldx     #4
:       lda     s_eaten,x
        sta     al_eaten0,x
        lda     s_spent,x
        sta     al_spent0,x
        dex
        bpl     :-
        rts

.segment "TEXT"
; Simulation hooks: they run with SIM loaded (module_drink,
; module_rest_prepare, module_hazards); resident (TEXT) since lot 2 filled
; the SIM window, which must end below $B500 (boot.s TABLE).
; DRINK WATER (module_drink, before A2[16] is reset): T0F/S00 $5C50 adds the
; ounces to the session when the last drink is under two hours old.
alert_drink:
        fld     s_drink
        fop     FCOMP, al_k2
        cmp     #$FF
        beq     @add
        lda     #0
        sta     al_drunk
        sta     al_drunk+1
@add:   clc
        lda     al_drunk
        adc     msgnum
        sta     al_drunk
        lda     al_drunk+1
        adc     msgnum+1
        sta     al_drunk+1
        rts

; REST (module_rest_prepare, t1 = minutes, before A2[18] is reset):
; T15/S0B $59AA adds INT(.017 x minutes) hours when A2[18] < 2.
alert_rest:
        fld     t1
        fop     FMULT, sv_0_017
        jsr     AYINT
        lda     $A1
        sta     al_w
        lda     $A0
        sta     al_w+1
        fld     s_rest
        fop     FCOMP, al_k2
        cmp     #$FF
        beq     @add
        lda     #0
        sta     al_rest_h
        sta     al_rest_h+1
@add:   clc
        lda     al_rest_h
        adc     al_w
        sta     al_rest_h
        lda     al_rest_h+1
        adc     al_w+1
        sta     al_rest_h+1
        rts

; ----------------------------------------------------------------------------
; H1: T0B/S07 onsets, run after the port's exposure counters (module_hazards,
; MED and SIM loaded). Native order: infection (9) draws before malaria (13).
hz_diseases:
        lda     disease_triggers
        jeq     @done
        ; $5B8D: active cuts for at least 6 h, infection neither active nor
        ; prevented: RND < minutes x $4C7A x .0002.
        lda     injury_active+8
        ora     injury_prevented+8
        bne     @malaria
        lda     injury_active
        beq     @malaria
        lda     injury_since_lo
        ldy     injury_since_hi
        jsr     MOVFM
        fop     FSUB, s_elap
        fop     FCOMP, f_6
        cmp     #$FF
        beq     @malaria
        fld     s_step
        fop     FMULT, al_sweat
        fop     FMULT, al_k2e4
        jsr     al_roll
        bcc     @malaria
        ldx     #8
        jsr     module_injury_begin
@malaria:
        ; $5B3F: regions 3-5 (Burma, New Guinea, Bolivia), under 6000 ft, not
        ; on clear ground, outside a shelter: RND < minutes x .00005.
        lda     injury_active+12
        ora     injury_prevented+12
        bne     @done
        lda     region_number   ; not MAP+32 (rewritten by the wild food scan)
        cmp     #3
        bcc     @done
        cmp     #6
        bcs     @done
        jsr     level_here
        sta     al_i
        clc
        adc     M_BASE
        cmp     #60
        bcs     @done
        lda     shelter_inside
        bne     @done
        lda     al_i
        cmp     #96             ; rocky ground counts as cover ($4B56 = 2)
        bcs     @ground
        jsr     native_here
        asl     a
        bcs     @ground         ; river or lake
        jsr     woods_here
        bcc     @done           ; clear ground ($4B56 = 0)
@ground:
        fld     s_step
        fop     FMULT, al_k5e5
        jsr     al_roll
        bcc     @done
        ldx     #12
        jmp     module_injury_begin
@done:  rts
; C set when the native generator draws under FAC.
al_roll:
        fst     al_t1
        jsr     weather_random
        fop     FCOMP, al_t1
        cmp     #$FF
        beq     :+
        clc
        rts
:       sec
        rts

; ----------------------------------------------------------------------------
.segment "LOWCODE"
; Bridges of the care commands (care.s runs in WILDMVI at $5800).
; A = minutes; T11/S00 $5BA4 raises the rate by .02 x weight (SPLINT).
medical_spend_effort:
        pha
        jsr     medical_apply
        lda     #<m_ok
        ldx     #>m_ok
        jsr     message
        pla
        ldx     #3              ; act 3: rest rate + .02 x body weight
        jsr     spend
        jmp     report
; A/X = message, after the care selectors have been applied.
care_message_apply:
        pha
        txa
        pha
        jsr     medical_apply
        pla
        tax
        pla
        jmp     message
; WET BODY from the canteen: ounces through INPUT, then WILDMVI again.
care_quantity:
        lda     #N_WATER
        sta     noun
        lda     #<m_ounces
        ldx     #>m_ounces
        jsr     get_quantity
        php
        lda     #158            ; BODY
        sta     noun
        lda     #19
        jsr     overlay_load
        plp
        rts
; C set when river or lake water is at hand (lot 2's resident water_here,
; which loads SIM only: WILDMVI stays in its window).
care_water_near:
        lda     camp_untreated  ; a river would mark a drink untreated
        pha
        jsr     water_here
        pla
        sta     camp_untreated
        rts
; Verbs without a table entry: the care verbs DRY/WARM, COOL, CUT and WET.
verb_more:
        lda     verb
        cmp     #13
        beq     @care
        cmp     #14
        beq     @care
        cmp     #31
        beq     @care
        cmp     #33
        beq     @care
        jmp     camp_verb       ; lot 2: MAKE/BUILD, BOIL (src/camp.s)
@care:  jmp     do_medical

.segment "TEXT"
; Shared by the SIM hooks above and by ALERT.
al_sweat: .byte $80,$15,$55,$55,$56 ; $4C7A of the saved game (.5833333)
al_k2:    .byte $82,$00,0,0,0
al_k2e4:  .byte $74,$51,$B7,$17,$5A   ; T0B/S07 $5D22 (.0002)
al_k5e5:  .byte $72,$51,$B7,$17,$5A   ; T0B/S07 $5D1D (.00005)
al_t1:    .res 5

.segment "ALERT"
al_k3:    .byte $82,$40,0,0,0
al_k16:   .byte $85,$00,0,0,0
al_k60:   .byte $86,$70,0,0,0
al_m850:  .byte $8A,$D4,$80,0,0       ; -850
al_t2:    .res 5
al_now:   .res 21
; Alert texts: messages 173, 174, 187, 203, 204 (direct), then the events
; 25, 40, 41, 42, 43 (messages 160, 175, 176, 177, 178).
al_lo: .byte <al_173,<al_174,<al_203,<al_204,<al_187,<al_160,<al_175,<al_176,<al_177,<al_178
al_hi: .byte >al_173,>al_174,>al_203,>al_204,>al_187,>al_160,>al_175,>al_176,>al_177,>al_178
al_173: .byte "YOU ARE HUNGRY ENOUGH TO EAT A HORSE.",0
al_174: .byte "YOU ARE THIRSTY ENOUGH TO DRINK A LAKE.",0
al_203: .byte "YOU ARE SHIVERING.",0
al_204: .byte "YOU ARE SWEATING.",0
al_187: .byte "HEALTH DETERIORATED. CHECK YOUR STATUS.",0
al_160: .byte "YOUR CONDITION IS BECOMING SERIOUS.",0
al_175: .byte "TOO TIRED TO RAISE A LITTLE FINGER.",0
al_176: .byte "YOU ARE NOT LONG FOR THIS WORLD.",0
al_177: .byte "YOU ARE DROWNING.",0
al_178: .byte "EXHAUSTED: INVOLUNTARY SLEEP.",0
.segment "GCODE"
