; VERHILLE Arnaud — GPL-3.0. Explicit continuation after a native result.
;
; Entry contract (SITES preserves the preceding native result):
; dep_running = $80 collected food, $81 collected water,
;               $82 cooked food, $83 boiled water, $84 proposed REST.
; dep_mask = exact noun, dep_mask+1 = confirmed ounces (0 means ask).
; dep_cursor = journey_encounters when the successful command completed.
; These four bytes are an exclusive union with PREPARE and SURVIVAL.
; Opening, browsing and cancelling change no simulation state.
.segment "CAMPUI"
.pushseg
.segment "MENUSWAP"
; menu_gather has just restored this code; no native window is assumed live.
followup_poll:
        lda     obj_keep
        eor     #$C0
        bne     :+
        sta     obj_keep
:       lda     mq_n
        bne     @done
        lda     animal_kind
        ora     threat_context
        ora     route_active
        ora     camp_pending
        ora     dep_running
        bne     @open
@done: rts
@open: pla
        pla
        lda     #10
        jsr     overlay_load
        jmp     followup_open
.popseg
followup_check:
        lda     dead
        ora     won
        jne     fu_cancel
        lda     threat_context
        bne     @threat
        lda     route_context
        beq     @camp
        lda     animal_kind
        beq     @camp
        lda     animal_x
        cmp     px+1
        bne     @camp
        lda     animal_y
        cmp     py+1
        bne     @camp
        lda     #3
        ldx     route_active
        beq     :+
        lda     #1
:       ldx     dep_running
        cpx     #$84
        beq     @rest
        ldx     camp_pending
        txa
        and     #$40
        beq     @set_goal
        txa
        and     #7
        cmp     #5
        bcc     @set_goal
@rest: lda     #2
        bne     @save_goal
@set_goal:
        lda     #3
        ldx     travel_pending
        bne     @trip_goal
        ldx     route_active
        beq     @save_goal
@trip_goal:lda   #1
@save_goal:
        sta     threat_context
@threat:jmp     threat_open
@camp: lda     camp_pending
        bmi     @camp_resume
        and     #$40
        jne     refusal_close
        lda     dep_running
        bmi     @native_followup
        and     #$60
        beq     :+
        lda     #0
        sta     dep_running
:       lda     route_active
        beq     @view
        lda     route_context
        jne     route_post_action
@view: jmp     refusal_close
@camp_resume:
        jmp     module_campguide_resume
@native_followup:
        lda     dep_cursor
        cmp     journey_encounters
        jne     fu_cancel
        lda     dead
        ora     won
        jne     fu_cancel
        lda     dep_running
        cmp     #$85
        jcs     hunter_result_open
        cmp     #$84
        jeq     night_rest_followup
module_followup:
        lda     dep_running
        and     #3
        sta     fu_kind
        lda     #0
        sta     fu_cursor
fu_draw:
        ; Keep the native result at left. Replace the entire right grid,
        ; including its old footer, with the deliberate next choice.
        lda     #20
        sta     fu_row
@clear:
        lda     fu_row
        jsr     fu_position
        ldx     #41
@space: txa
        tay
        lda     #' '|$80
        jsr     t_update         ; preserves X, clobbers Y
        inx
        cpx     #80
        bcc     @space
        inc     fu_row
        lda     fu_row
        cmp     #24
        bcc     @clear
        lda     #20
        jsr     fu_position
        ldx     fu_kind
        lda     fu_text_lo,x
        sta     gp1
        lda     fu_text_hi,x
        sta     gp1+1
        jsr     fu_string
        lda     #21
        jsr     fu_position
        ldx     dep_mask
        cpx     #76
        bcs     @forage
        lda     it_name_lo,x
        sta     gp1
        lda     it_name_hi,x
        bne     @name
@forage:
        ; Native FORAGE resolved its exact identity into nounbuf.
        lda     #<nounbuf
        sta     gp1
        lda     #>nounbuf
@name: sta     gp1+1
        jsr     fu_string
        jsr     puts
        .byte   " ",0
        lda     dep_mask+1
        sta     num
        lda     #0
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte   " OZ ",0
        lda     fu_kind
        cmp     #2
        bcs     @ground
        cmp     #1
        beq     @canteen
        jsr     puts
        .byte   "PACK",0
        jmp     @choice
@canteen:
        jsr     puts
        .byte   "CANTEEN",0
        jmp     @choice
@ground:
        jsr     puts
        .byte   "GROUND",0
@choice:
        lda     #22
        jsr     fu_position
        ldx     fu_kind
        lda     fu_cursor
        beq     :+
        inx
        inx
:       lda     fu_choice_lo,x
        sta     gp1
        lda     fu_choice_hi,x
        sta     gp1+1
        jsr     fu_string
        lda     #23
        jsr     fu_position
        jsr     puts
        .byte   "RET:SELECT ESC:CANCEL ARROWS:CHOOSE",0
fu_key:
        jsr     cg_view_key
        cmp     #KC_ESC
        beq     fu_cancel
        cmp     #KC_RET
        beq     fu_accept
        cmp     #KC_LEFT
        beq     @toggle
        cmp     #KC_RIGHT
        beq     @toggle
        cmp     #KC_UP
        beq     @toggle
        cmp     #KC_DOWN
        bne     fu_key
@toggle:
        lda     fu_kind
        cmp     #2
        bcs     fu_key
        lda     fu_cursor
        eor     #1
        sta     fu_cursor
        jmp     fu_draw
fu_cancel:
        lda     #0
        sta     dep_running
        lda     #$FF
        jmp     followup_execute
fu_accept:
        ; Only acceptance composes a command. The native source/quantity
        ; dialogs and prerequisite queue remain authoritative.
        ldx     fu_kind
        lda     fu_cursor
        beq     :+
        inx
        inx
:       lda     fu_verbs,x
        cmp     #18
        jeq     @boil
        pha
        jsr     fu_compose
        pla
        cmp     #17
        jne     @ordinary
        ldx     fire_on
        jne     @ordinary
        ldx     camp_use
        txa
        and     #U_STOVE
        jne     @cook_ready
        lda     #17
        jmp     module_campguide
@cook_ready:
        lda     #17
        jne     @ordinary
@ordinary:
        jmp     followup_execute
@boil: lda     camp_use
        and     #U_UTENS
        jeq     @boil_prepare
        lda     fire_on
        jne     @boil_ready
        lda     camp_use
        and     #U_STOVE
        jne     @boil_ready
@boil_prepare:
        ldy     #0
@boil_copy:
        lda     fu_boil_command,y
        sta     inbuf,y
        jeq     @boil_composed
        iny
        jne     @boil_copy
@boil_composed:
        sty     linelen
        lda     #22
        sta     menu_noun
        lda     #$C0
        sta     obj_keep
        lda     #1
        sta     obj_side
        lda     dep_mask+1
        sta     menu_portion+2
        lda     #$41
        sta     dep_running
        lda     #18
        jmp     module_campguide
@boil_ready:
        lda     dep_mask+1
        sta     menu_portion+2
        lda     #0
        sta     dep_running
        lda     #18
        jmp     followup_execute

; A command names its noun through resolve_menu, preserving identities whose
; display labels differ from parser vocabulary. Its quantity stays editable.
fu_compose:
        ldx     #0
        cmp     #17
        beq     @word
        ldx     #5
        cmp     #5
        beq     @meal
        ldx     #9
        lda     dep_mask+1
        cmp     #8
        bcc     @word
        lda     #8
        bne     @portion
@meal: lda     dep_mask+1
        cmp     #48
        bcc     @word
        lda     #48
@portion:
        sta     dep_mask+1
@word: ldy     #0
@copy: lda     fu_commands,x
        sta     inbuf,y
        beq     @ready
        inx
        iny
        bne     @copy
@ready:sty     linelen
        lda     dep_mask
        sta     menu_noun
        lda     #$C0            ; exact source, owned by this one native command
        sta     obj_keep
        ldx     #0
        lda     fu_kind
        cmp     #2
        bcs     :+
        inx
:       stx     obj_side
        lda     fu_kind
        ora     #$40            ; one editable native quantity prefill
        sta     dep_running
        rts
fu_commands: .byte "COOK",0,"EAT",0,"DRINK",0
fu_kind: .byte 0
fu_cursor: .byte 0
; Identities in verb_table: COOK, BOIL, EAT, DRINK.
fu_verbs: .byte 17,18,5,6
fu_text_lo: .byte <fu_food,<fu_water,<fu_cooked,<fu_boiled
fu_text_hi: .byte >fu_food,>fu_water,>fu_cooked,>fu_boiled
fu_food: .byte "FOOD RECOVERED",0
fu_water: .byte "WATER COLLECTED",0
fu_cooked: .byte "COOKED PORTION",0
fu_boiled: .byte "BOILED PORTION",0
fu_choice_lo: .byte <fu_cook,<fu_boil,<fu_eat,<fu_drink
fu_choice_hi: .byte >fu_cook,>fu_boil,>fu_eat,>fu_drink
fu_cook: .byte "> COOK (HEAT)        EAT",0
fu_boil: .byte "> BOIL (HEAT/TOOLS)  DRINK",0
fu_eat: .byte "> EAT",0
fu_drink: .byte "> DRINK",0
fu_row: .byte 0
; Right pane helpers never touch the native result cursor or its contents.
fu_position:
        sta     CV
        jsr     t_vtab
        lda     #41
        sta     CH
        rts
fu_string:
        ldy     #0
@char: lda     (gp1),y
        beq     @done
        ora     #$80
        jsr     COUT
        iny
        bne     @char
@done: rts

fu_boil_command: .byte "BOIL WATER",0

; A proposed REST has finished or stopped. Preserve its native result at left;
; continuation is an inspection, and a further native rest needs confirmation.
night_rest_followup:
        lda     #20
        sta     fu_row
@clear: lda     fu_row
        jsr     fu_position
        ldx     #41
@space: txa
        tay
        lda     #' '|$80
        jsr     t_update
        inx
        cpx     #80
        bcc     @space
        inc     fu_row
        lda     fu_row
        cmp     #24
        bcc     @clear
        lda     #20
        jsr     fu_position
        jsr     puts
        .byte "REST FOLLOW-UP",0
        lda     #21
        jsr     fu_position
        lda     night
        beq     @morning
        jsr     puts
        .byte "> REVIEW REST TO DAWN",0
        jmp     @hint
@morning:
        jsr     puts
        .byte "> CAMP DEPARTURE",0
@hint: lda     #22
        jsr     fu_position
        jsr     puts
        .byte "NO ACTION UNTIL CONFIRMED",0
        lda     #23
        jsr     fu_position
        jsr     puts
        .byte "RETURN:OPEN ESC:VIEW",0
@key:  jsr     cg_view_key
        cmp     #KC_ESC
        beq     @cancel
        cmp     #KC_RET
        bne     @key
        lda     #0
        sta     dep_running
        lda     night
        beq     @camp
        ; NIGHT cancellation returns like a completed STATUS inspection.
        ; Its accepted forms replace this return with main_command themselves.
        pla
        pla
        lda     #>(main_command_done-1)
        pha
        lda     #<(main_command_done-1)
        pha
        lda     #4
        jmp     guidance_open
@camp: jmp     module_camp_departure
@cancel:
        lda     #0
        sta     dep_running
        jmp     refusal_close
