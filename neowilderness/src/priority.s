; Interface recommendations reuse observed state and existing native forms.
.segment "CODE"
duration_last: .word 60
duration_rest: .word 60
duration_wait: .word 60
duration_proposal: .word 0
duration_pending: .byte 0
.segment "LOWCODE"
duration_entry:
        lda     input_argument
        bne     @native
        jsr     travel_ui_load
        jmp     duration_select
@native: ldy    #1
        jmp     number_entry
; Replaces the original LDA minutes+1 at the native step-budget check.
; $40 is a transient request; consuming it as $20 keeps cancellation safe
; with get_line's existing UI cleanup, including a refusal before this point.
travel_short_budget:
        bit     dep_running
        bvc     @ready
        lsr     dep_running
        lda     stepmin
        sta     minutes
        lda     #0
        sta     minutes+1
@ready: lda     minutes+1
        rts

.segment "CODE"
threat_context: .byte 0
threat_seen: .byte 0
route_context: .byte 0
threat_open:
        ldx     #8
        jsr     ui_overlay_load
        jmp     module_threat
; A checklist form is only armed when its composed command is dispatched.
camp_command_begin:
        lda     mn_mode
        sta     route_context
        lda     camp_pending
        and     #$40
        beq     @done
        lda     camp_pending
        ora     #$80
        sta     camp_pending
@done: rts

.segment "GUIDANCE"
guidance_execute:
        cmp     #2
        bcs     @action
        asl     a
        asl     a
        jmp     navigation_flows ; NAVIGATION is still present, no reload
@action:
        lda     #3             ; REST's native duration form
        ldx     dep_cursor
        cpx     #2
        jeq     flows_execute
        ldx     thermal_mode
        cpx     #1             ; heat: resting rather than lighting a fire
        jeq     flows_execute
        lda     #11            ; MAKE FIRE, or USE FIRE if already present
        ldx     fire_on
        jeq     flows_execute
        lda     #10
        jne     flows_execute
guidance_dispatch:
        cmp     #6
        jeq     navigation_hunt_change
        cmp     #4
        beq     @night
        cmp     #5
        beq     module_priority
        jmp     module_guidance
@night: jmp     module_night

; MENU's explicit NEXT ACTION opens advice only. Opening advice never
; consumes, rests, equips or moves; the player confirms the native action.
module_priority:
        lda     weak_health
        beq     @body_check
        ldx     #12
@injury:
        lda     injury_active,x
        bne     @care
        dex
        bpl     @injury
@body_check:
        lda     thermal_mode
        ora     wet_mode
        bne     @body
        lda     ui_previous+5
        lsr     a
        bcs     @water
        lsr     a
        bcs     @meal
        lsr     a
        bcs     @energy
        lda     ui_previous+1
        cmp     ui_previous
        bcc     @meal_check
        cmp     #1
        bcs     @water
@meal_check:
        lda     ui_previous
        bne     @meal
        lda     night
        bne     @night
        fld     s_rest
        fop     FCOMP, f_12
        cmp     #1
        beq     @energy
        ; No pressing survival need: inspect the map and tracked objective.
        jmp     scr_map
@care: lda     #1
        sta     pg_open
        jmp     scr_status
@body: lda     #3
        bne     @guide
@water:lda     #1
        bne     @guide
@meal: lda     #0
        beq     @guide
@energy:
        lda     #2
@guide:jmp     module_guidance
@night:jmp     module_night

.segment "CAMPUI"
camp_night_open:
        pla
        pla
        lda     #>(main_command_done-1)
        pha
        lda     #<(main_command_done-1)
        pha
        lda     #4
        jmp     guidance_open

camp_trip_open:
        pla
        pla
        lda     #>(main_command_done-1)
        pha
        lda     #<(main_command_done-1)
        pha
        jmp     navigation_route_open

; Compose one deliberate native hunting continuation, preserving its prey.
fu_hunt_execute:
        cmp     #$FF
        jeq     fu_cancel
        cmp     #$FE
        beq     @change
        cmp     #21
        beq     @again
        cmp     #2
        beq     @craft
        ldx     #0
        cmp     #19
        beq     @skin
        ldx     #hunt_command_pack-hunt_native_words
        lda     #0
        sta     dep_running
        beq     @copy
@skin: lda     #$88
        sta     dep_running
        bne     @copy
@craft:ldx     #hunt_command_spear-hunt_native_words
@copy: ldy     #0
@char: lda     hunt_native_words,x
        sta     inbuf,y
        beq     @noun
        inx
        iny
        bne     @char
@noun: cpx     #hunt_command_game-hunt_native_words-1
        bcs     @ready
        lda     dep_mask
        cmp     #81
        ldx     #hunt_command_game-hunt_native_words
        bne     :+
        ldx     #hunt_command_fish-hunt_native_words
:       lda     hunt_native_words,x
        sta     inbuf,y
        beq     @ready
        inx
        iny
        bne     :-
@ready:sty     linelen
        lda     #0
        sta     menu_noun
        sta     obj_keep
        sta     mq_n
        jmp     campguide_execute
@again:jmp     hunter_again
@change:
        lda     #0
        sta     mq_n
        lda     dep_mask
        sta     mq_noun
        lda     #6
        jmp     guidance_open
hunt_native_words: .byte "SKIN ",0
hunt_command_pack: .byte "PACK ",0
hunt_command_spear: .byte "MAKE SPEAR",0
hunt_command_game: .byte "GAME",0
hunt_command_fish: .byte "FISH",0
