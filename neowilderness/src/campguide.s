; Explicit cooking preparation. CAMPUI is loaded at $9600 by SITES.
; All retained bytes are UI state outside SAVE. No inspector invokes SIM.
.pushseg
.segment "RESBSS"
camp_pending: .res 1
.segment "CODE"
camp_intent: .byte 0
camp_encounter: .byte 0
camp_saved_line: .res MAXLINE+1
camp_saved_noun: .byte 0
camp_saved_keep: .byte 0
camp_saved_side: .byte 0
camp_saved_portion: .res 3
camp_saved_followup: .res 4
.popseg
.segment "CAMPUI"
; Restore the original exact source and editable portion after preparation.
campguide_restore:
        lda     camp_saved_followup
        sta     dep_mask
        lda     camp_saved_followup+1
        sta     dep_mask+1
        lda     camp_saved_followup+2
        sta     dep_cursor
        lda     camp_saved_followup+3
        sta     dep_running
        ldx     #MAXLINE
@line: lda     camp_saved_line,x
        sta     inbuf,x
        dex
        jpl     @line
        ldx     #0
@length:
        lda     inbuf,x
        beq     @length_done
        inx
        bne     @length
@length_done:
        stx     linelen
        lda     camp_saved_noun
        sta     menu_noun
        lda     camp_saved_keep
        sta     obj_keep
        lda     camp_saved_side
        sta     obj_side
        ldx     #2
@portion:
        lda     camp_saved_portion,x
        sta     menu_portion,x
        dex
        jpl     @portion
        rts
module_campguide:
        sta     camp_intent
        lda     dep_mask
        sta     camp_saved_followup
        lda     dep_mask+1
        sta     camp_saved_followup+1
        lda     dep_cursor
        sta     camp_saved_followup+2
        lda     dep_running
        sta     camp_saved_followup+3
        lda     journey_encounters
        sta     camp_encounter
        ldx     #MAXLINE
@line: lda     inbuf,x
        sta     camp_saved_line,x
        dex
        jpl     @line
        lda     menu_noun
        sta     camp_saved_noun
        lda     obj_keep
        sta     camp_saved_keep
        lda     obj_side
        sta     camp_saved_side
        ldx     #2
@portion:
        lda     menu_portion,x
        sta     camp_saved_portion,x
        dex
        jpl     @portion
        lda     #$80
        sta     camp_pending
        jmp     campguide_review
module_campguide_resume:
        lda     camp_pending
        and     #$40
        jne     camp_checklist_resume
        lda     journey_encounters
        cmp     camp_encounter
        jne     campguide_cancel
        lda     dead
        ora     won
        jne     campguide_cancel
campguide_review:
        lda     #0
        sta     cg_count
        lda     fire_on
        jne     @tools
        lda     camp_use
        and     #U_STOVE
        jne     @tools
        jsr     cg_puts
        .byte "NEEDS HEAT. CHOOSE ONE ACTION.",0
        ldx     #71
        jsr     have
        jcc     @fire
        lda     camp_use
        and     #U_FUEL
        jne     @stove_ignite
        ldx     #40
        jsr     have
        jcc     @fire
        lda     #4
        jne     @stove_add
@stove_ignite:
        lda     fire_near
        jne     @stove_ready
        lda     camp_use
        and     #U_MATCH
        jeq     @fire
@stove_ready:
        lda     #1
@stove_add:
        jsr     cg_add
@fire: lda     camp_use
        and     #U_MATCH|U_GLASS
        jne     @fire_weather
        ldx     #38
        jsr     have
        jcc     @no_ignition
        lda     #5
        jne     @fire_add
@no_ignition:
        ldx     #39
        jsr     have
        jcc     @draw
        lda     #6
        jne     @fire_add
@fire_weather:
        jsr     camp_storm
        jcc     @fire_ready
        lda     shelter_inside
        jne     @fire_ready
        lda     camp_use
        and     #U_FUEL
        jne     @fire_ready
        ldx     #40
        jsr     have
        jcc     @draw
        lda     #4
        jne     @fire_add
@fire_ready:
        lda     #0
@fire_add:
        jsr     cg_add
        jmp     @draw
@tools:
        lda     camp_intent
        cmp     #18
        jne     @ready
        lda     camp_use
        and     #U_UTENS
        jne     @ready
        jsr     cg_puts
        .byte "BOIL NEEDS UTENSILS IN USE.",0
        ldx     #73
        jsr     have
        jcc     @missing
        lda     #2
        jsr     cg_add
        jmp     @draw
@missing:
        jsr     cg_more
        .byte "|RECOVER UTENSILS, THEN CHOOSE BOIL.",0
        jmp     cg_footer
@ready:
        jsr     cg_puts
        .byte "PREPARATION READY.",0
        lda     #3
        jsr     cg_add
@draw: lda     cg_count
        jeq     cg_footer
        lda     #0
        sta     cg_cursor
cg_draw_choice:
        lda     #21
        jsr     fu_position
        ldx     #41
@clear:
        txa
        tay
        lda     #' '|$80
        jsr     t_update
        inx
        cpx     #80
        bcc     @clear
        lda     #41
        sta     CH
        ldx     cg_cursor
        lda     cg_choices,x
        tax
        lda     cg_text_lo,x
        sta     gp1
        lda     cg_text_hi,x
        sta     gp1+1
        jsr     cg_string
cg_footer:
        lda     #23
        jsr     fu_position
        jsr     cg_more
        .byte "ARROWS:CHOOSE RET:ACCEPT ESC:CANCEL",0
cg_key:
        jsr     cg_view_key
        cmp     #KC_ESC
        jeq     campguide_cancel
        cmp     #KC_RET
        jeq     cg_accept
        cmp     #KC_LEFT
        jeq     @toggle
        cmp     #KC_RIGHT
        jne     cg_key
@toggle:
        lda     cg_count
        cmp     #2
        jcc     cg_key
        lda     cg_cursor
        eor     #1
        sta     cg_cursor
        jmp     cg_draw_choice
cg_accept:
        lda     cg_count
        jeq     cg_key
        ldx     cg_cursor
        lda     cg_choices,x
        cmp     #3
        jeq     @original
        tax
        lda     cg_cmd_lo,x
        sta     gp1
        lda     cg_cmd_hi,x
        sta     gp1+1
        ldy     #0
@copy: lda     (gp1),y
        sta     inbuf,y
        jeq     @composed
        iny
        jne     @copy
@composed:
        sty     linelen
        lda     #0
        sta     obj_keep
        sta     menu_noun
        sta     mq_n
        ; Execute exactly this accepted command, without a prerequisite queue.
        jmp     campguide_execute
@original:
        jsr     back_to_view_now
        jsr     campguide_restore
        lda     #0
        sta     camp_pending
        lda     #$FE
        jmp     campguide_execute
campguide_cancel:
        jsr     campguide_restore
        lda     #0
        sta     camp_pending
        lda     #$FF
        jmp     campguide_execute
 ; CAMP retains only the inspected step. No native command is queued.
camp_checklist_resume:
        lda     journey_encounters
        cmp     camp_encounter
        jne     camp_checklist_cancel
        lda     dead
        ora     won
        jne     camp_checklist_cancel
        lda     camp_pending
        and     #$0F
        cmp     #5
        bcc     @prep
        cmp     #7
        bcs     @prep
        jsr     cg_puts
        .byte "REST FOLLOW-UP",0
        lda     #21
        jsr     fu_position
        lda     night
        beq     @morning
        jsr     cg_more
        .byte "> REVIEW REST TO DAWN",0
        jmp     @footer
@morning:
        jsr     cg_more
        .byte "> CAMP DEPARTURE",0
        jmp     @footer
@prep: jsr     cg_puts
        .byte "CAMP: REVIEW UPDATED CHECKLIST",0
        lda     #21
        jsr     fu_position
        jsr     cg_more
        .byte "> RETURN TO THE SAME CAMP STEP",0
@footer:
        lda     #23
        jsr     fu_position
        jsr     cg_more
        .byte "RETURN:REVIEW ESC:VIEW",0
@key:  jsr     cg_view_key
        cmp     #KC_ESC
        jeq     camp_checklist_cancel
        cmp     #KC_RET
        jne     @key
        lda     #0
        sta     dep_running
        lda     camp_pending
        and     #$7F
        sta     camp_pending
        and     #8
        jne     module_camp_departure
        lda     night
        bne     @night
        lda     camp_pending
        and     #7
        cmp     #5
        jcs     module_camp_departure
@night: jmp     camp_night_open
camp_checklist_cancel:
        lda     #0
        sta     camp_pending
        sta     dep_running
        jmp     refusal_close
cg_add:
        ldx     cg_count
        sta     cg_choices,x
        inc     cg_count
        rts
cg_count: .byte 0
cg_departure_origin: .byte 0
cg_cursor: .byte 0
cg_choices: .res 6
cg_text_lo: .byte <cg_fire,<cg_stove,<cg_utens,<cg_original,<cg_fuel,<cg_match,<cg_glass
cg_text_hi: .byte >cg_fire,>cg_stove,>cg_utens,>cg_original,>cg_fuel,>cg_match,>cg_glass
cg_fire: .byte "> MAKE FIRE (30 MIN)",0
cg_stove: .byte "> USE STOVE (FUEL + IGNITION)",0
cg_utens: .byte "> USE UTENSILS (15 MIN IF CARRIED)",0
cg_original: .byte "> CONTINUE ORIGINAL COOK / BOIL",0
cg_fuel: .byte "> USE FUEL (ONE USE)",0
cg_match: .byte "> USE MATCHES (ONE MATCH)",0
cg_glass: .byte "> USE MAGNF GLASS (NEEDS SUNLIGHT)",0
cg_cmd_lo: .byte <cg_cmd_fire,<cg_cmd_stove,<cg_cmd_utens,0,<cg_cmd_fuel,<cg_cmd_match,<cg_cmd_glass
cg_cmd_hi: .byte >cg_cmd_fire,>cg_cmd_stove,>cg_cmd_utens,0,>cg_cmd_fuel,>cg_cmd_match,>cg_cmd_glass
cg_cmd_fire: .byte "MAKE FIRE",0
cg_cmd_stove: .byte "USE STOVE",0
cg_cmd_utens: .byte "USE UTENSILS",0

cg_cmd_fuel: .byte "USE FUEL",0
cg_cmd_match: .byte "USE MATCHES",0
cg_cmd_glass: .byte "USE MAGNF GLASS",0

; Paint only the right pane, retaining the last native result at left.
cg_puts:
        lda     #20
        sta     cg_clear_row
@row:  lda     cg_clear_row
        jsr     fu_position
        ldx     #41
@space:
        txa
        tay
        lda     #' '|$80
        jsr     t_update
        inx
        cpx     #80
        bcc     @space
        inc     cg_clear_row
        lda     cg_clear_row
        cmp     #24
        bcc     @row
        lda     #20
        jsr     fu_position
cg_more:
        pla
        sta     gp2
        pla
        sta     gp2+1
@char: inc     gp2
        bne     :+
        inc     gp2+1
:       ldy     #0
        lda     (gp2),y
        beq     @done
        jsr     cg_char
        jmp     @char
@done: lda     gp2+1
        pha
        lda     gp2
        pha
        rts
cg_string:
        lda     #0
        sta     cg_string_y
@char: ldy     cg_string_y
        lda     (gp1),y
        beq     @done
        jsr     cg_char
        inc     cg_string_y
        bne     @char
@done: rts
cg_char:
        cmp     #'|'
        beq     @newline
        ora     #$80
        ldy     CH
        jsr     t_update
        inc     CH
        lda     CH
        cmp     #80
        bcc     @done
@newline:
        lda     CV
        cmp     #23
        bcs     @done
        clc
        adc     #1
        jsr     fu_position
@done: rts
cg_clear_row: .byte 0
cg_string_y: .byte 0

; CAMP is an inspection menu. Each accepted action is one native command.
module_camp_departure:
        lda     #1
        sta     cg_departure_origin
        jsr     puts_refusal
        .byte "CAMP ACTIONS|CONFIRM EACH ACTION SEPARATELY.|ESC RETURNS TO THE VIEW.",0
        lda     #0
        sta     cg_count
        sta     cg_cursor
        lda     #0
        jsr     cg_add          ; prepare night is always useful to inspect
        lda     shelter_inside
        jeq     @tent
        lda     #1
        jsr     cg_add
@tent: ldx     #9
        jsr     have
        jcc     @fire
        lda     it_place+9
        jne     @fire
        lda     #2
        jsr     cg_add
@fire: lda     fire_on
        jeq     @back
        lda     #3
        jsr     cg_add
@back: lda     route_active
        beq     :+
        lda     #5
        jsr     cg_add
:       lda     #4
        jsr     cg_add
        jsr     cg_puts
        .byte "CAMP - CHOOSE ONE ACTION",0
cd_draw:
        lda     #21
        jsr     fu_position
        ldx     #41
@clear:
        txa
        tay
        lda     #' '|$80
        jsr     t_update
        inx
        cpx     #80
        jcc     @clear
        lda     #41
        sta     CH
        ldx     cg_cursor
        lda     cg_choices,x
        tax
        lda     cd_text_lo,x
        sta     gp1
        lda     cd_text_hi,x
        sta     gp1+1
        jsr     cg_string
        lda     #23
        jsr     fu_position
        jsr     cg_more
        .byte "UP/DOWN:CHOOSE RET:ACCEPT ESC:BACK",0
@key:  jsr     cg_view_key
        cmp     #KC_ESC
        jeq     cd_cancel
        cmp     #KC_RET
        jeq     cd_accept
        cmp     #KC_UP
        jeq     @up
        cmp     #KC_LEFT
        jeq     @up
        cmp     #KC_DOWN
        jeq     @down
        cmp     #KC_RIGHT
        jne     @key
@down: inc     cg_cursor
        lda     cg_cursor
        cmp     cg_count
        jcc     cd_draw
        lda     #0
        sta     cg_cursor
        jeq     cd_draw
@up:   lda     cg_cursor
        bne     :+
        lda     cg_count
        sta     cg_cursor
:       dec     cg_cursor
        jmp     cd_draw
cd_accept:
        ldx     cg_cursor
        lda     cg_choices,x
        jeq     cd_night
        cmp     #4
        jeq     cd_cancel
        cmp     #5
        jeq     camp_trip_open
        tax
        lda     cd_cmd_lo-1,x
        sta     gp1
        lda     cd_cmd_hi-1,x
        sta     gp1+1
        ldy     #0
@copy: lda     (gp1),y
        sta     inbuf,y
        jeq     @ready
        iny
        jne     @copy
@ready:sty     linelen
        lda     #0
        sta     menu_noun
        sta     obj_keep
        sta     mq_n
        lda     cg_departure_origin
        beq     @dispatch
        lda     #$48
        sta     camp_pending
        lda     journey_encounters
        sta     camp_encounter
@dispatch:
        ; QUICK returns to main on cancel. Acceptance instead dispatches
        ; this one composed native command through the existing command path.
        pla
        pla
        lda     #>(main_command-1)
        pha
        lda     #<(main_command-1)
        pha
        lda     #0
        jmp     campguide_execute
cd_night:
        jmp     camp_night_open
cd_cancel:
        lda     #0
        sta     camp_pending
        lda     #$FF
        jmp     campguide_execute
cd_text_lo: .byte <cd_night_text,<cd_exit_text,<cd_tent_text,<cd_fire_text,<cd_back_text,<cd_trip_text
cd_text_hi: .byte >cd_night_text,>cd_exit_text,>cd_tent_text,>cd_fire_text,>cd_back_text,>cd_trip_text
cd_night_text: .byte "> PREPARE NIGHT (REVIEW DURATION)",0
cd_exit_text: .byte "> EXIT SHELTER",0
cd_tent_text: .byte "> PACK LOCAL TENT (CAPACITY APPLIES)",0
cd_fire_text: .byte "> DOUSE FIRE (NO TIME)",0
cd_back_text: .byte "> BACK",0
cd_trip_text: .byte "> REVIEW TRACKED TRIP",0
cd_cmd_lo: .byte <cd_exit_cmd,<cd_tent_cmd,<cd_fire_cmd
cd_cmd_hi: .byte >cd_exit_cmd,>cd_tent_cmd,>cd_fire_cmd
cd_exit_cmd: .byte "EXIT SHELTER",0
cd_tent_cmd: .byte "PACK TENT",0
cd_fire_cmd: .byte "DOUSE FIRE",0
