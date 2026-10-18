; VERHILLE Arnaud — GPL-3.0. Encounter choices over the native result.
; Inspection changes UI memory only. Accepted actions reopen native forms;
; their rules alone determine elapsed time, injuries, weapon use and escape.
.segment "THREATUI"
module_threat:
        lda     #0
        sta     th_cursor
        sta     th_present
        lda     animal_kind
        beq     @ready
        lda     animal_x
        cmp     px+1
        bne     @ready
        lda     animal_y
        cmp     py+1
        bne     @ready
        inc     th_present
@ready:jsr     th_weapon
th_draw:
        lda     #20
        sta     th_row
@clear:lda     th_row
        jsr     th_position
        ldx     #41
@space:txa
        tay
        lda     #' '|$80
        jsr     t_update
        inx
        cpx     #80
        bcc     @space
        inc     th_row
        lda     th_row
        cmp     #24
        bcc     @clear
        lda     #20
        jsr     th_position
        lda     th_present
        jeq     th_resolved
        lda     animal_kind
        sec
        sbc     #6
        cmp     #4
        bcc     :+
        lda     #3
:       tay
        lda     th_animals_lo,y
        ldx     th_animals_hi,y
        jsr     th_string
        lda     threat_seen
        cmp     animal_kind
        beq     @still
        jsr     puts
        .byte " HERE",0
        jmp     @goal
@still:jsr     puts
        .byte " STILL HERE",0
@goal: lda     animal_kind
        sta     threat_seen
        lda     threat_context
        cmp     #1
        bne     :+
        jsr     puts
        .byte "; TRIP KEPT",0
        jmp     @equipment
:       cmp     #2
        bne     @equipment
        jsr     puts
        .byte "; REST KEPT",0
@equipment:
        lda     #21
        jsr     th_position
        ldy     th_tool
        lda     th_tools_lo,y
        ldx     th_tools_hi,y
        jsr     th_string
        lda     fire_on
        beq     @no_fire
        jsr     puts
        .byte "; FIRE ON",0
        jmp     @choice
@no_fire:
        jsr     puts
        .byte "; FIRE OFF",0
@choice:
        lda     #22
        jsr     th_position
        ldy     th_cursor
        cpy     #4
        bne     @ordinary_choice
        lda     fire_on
        beq     @ordinary_choice
        lda     #<th_douse
        ldx     #>th_douse
        bne     @choice_text
@ordinary_choice:
        lda     th_choices_lo,y
        ldx     th_choices_hi,y
@choice_text:
        jsr     th_string
        jmp     th_hint
th_resolved:
        jsr     puts
        .byte "THREAT NO LONGER HERE",0
        lda     #21
        jsr     th_position
        lda     threat_context
        cmp     #1
        beq     @trip
        cmp     #2
        beq     @rest
        jsr     puts
        .byte "CHOOSE YOUR NEXT ACTION",0
        jmp     @view
@trip: jsr     puts
        .byte "TRACKED TRAVEL WAS RETAINED",0
        lda     #22
        jsr     th_position
        jsr     puts
        .byte "> REVIEW ROUTE / RESUME",0
        jmp     th_hint
@rest: jsr     puts
        .byte "PROPOSED REST WAS RETAINED",0
        lda     #22
        jsr     th_position
        jsr     puts
        .byte "> REVIEW REST / CAMP",0
        jmp     th_hint
@view: lda     #22
        jsr     th_position
        jsr     puts
        .byte "> RETURN TO VIEW",0
th_hint:
        lda     #23
        jsr     th_position
        jsr     puts
        .byte "RET:OPEN ARROWS:CHOOSE ESC:VIEW",0
th_key:
        jsr     text_finish
        jsr     show_dhgr
        jsr     keyboard_wait
        cmp     #KC_ESC
        jeq     th_cancel
        cmp     #KC_RET
        jeq     th_accept
        cmp     #KC_LEFT
        beq     @previous
        cmp     #KC_UP
        beq     @previous
        cmp     #KC_RIGHT
        beq     @next
        cmp     #KC_DOWN
        bne     th_key
@next: lda     th_present
        beq     th_key
        inc     th_cursor
        lda     th_cursor
        cmp     #7
        bcc     @draw
        lda     #0
        sta     th_cursor
        beq     @draw
@previous:
        lda     th_present
        beq     th_key
        dec     th_cursor
        bpl     @draw
        lda     #6
        sta     th_cursor
@draw: jmp     th_draw
th_accept:
        lda     th_present
        beq     @resolved
        ldx     th_cursor
        cpx     #4
        bne     @verb
        lda     fire_on
        beq     @verb
        lda     #15
        bne     th_leave
@verb: lda     th_verbs,x
        jmp     th_leave
@resolved:
        lda     threat_context
        cmp     #1
        beq     @trip
        cmp     #2
        bne     th_cancel
        lda     #$F2
        bne     th_leave
@trip: lda     #$F1
        bne     th_leave
th_cancel:
        lda     #0
        sta     threat_context
        sta     threat_seen
        lda     #$FF
th_leave:
threat_return:
        cmp     #$FF
        beq     @cancel
        cmp     #$F1
        beq     @goal
        cmp     #$F2
        beq     @goal
        jmp     flows_execute
@cancel:
        lda     #0
        sta     threat_context
        sta     threat_seen
        jmp     refusal_close
@goal: pha
        lda     dep_running
        cmp     #$84
        bne     :+
        lda     #0
        sta     dep_running
:       lda     camp_pending
        and     #$7F            ; retain checklist, require explicit continuation
        sta     camp_pending
        lda     #0
        sta     threat_context
        sta     threat_seen
        pla
        tax
        pla
        pla
        lda     #>(main_command_done-1)
        pha
        lda     #<(main_command_done-1)
        pha
        cpx     #$F1
        beq     @trip
        lda     #4
        jmp     guidance_open
@trip: jmp     navigation_route_open
; Match OUTDOOR precedence by inspecting flags without consuming them.
; A carried blade is an additional native ATTACK fallback, not activation.
th_weapon:
        ldy     #1
        lda     camp_use
        and     #U_GUN
        bne     @done
        iny
        lda     fg_use
        and     #FT_BOW
        bne     @done
        iny
        lda     fg_use
        and     #FT_SPEAR
        bne     @done
        lda     care_tool_x
        cmp     px+1
        bne     @club
        lda     care_tool_y
        cmp     py+1
        bne     @club
        lda     care_tools
        and     #3
        beq     @club
        ldy     #4
        bne     @done
@club: ldy     #5
        lda     fg_use
        and     #FT_CLUB
        bne     @done
        ldx     #58
        jsr     have
        bcs     @blade
        ldx     #59
        jsr     have
        bcs     @blade
        ldy     #0
        beq     @done
@blade:ldy     #6
@done: sty     th_tool
        rts
th_position:
        sta     CV
        jsr     t_vtab
        lda     #41
        sta     CH
        rts
th_string:
        sta     gp1
        stx     gp1+1
        ldy     #0
@char: lda     (gp1),y
        beq     @done
        ora     #$80
        jsr     COUT
        iny
        bne     @char
@done: rts
th_cursor: .byte 0
th_present: .byte 0
th_tool: .byte 0
th_row: .byte 0
th_verbs: .byte 12,13,14,10,11,1,0
th_animals_lo: .byte <th_bear,<th_cougar,<th_snake,<th_cannibal
th_animals_hi: .byte >th_bear,>th_cougar,>th_snake,>th_cannibal
th_bear: .byte "BEAR",0
th_cougar: .byte "COUGAR",0
th_snake: .byte "RATTLESNAKE",0
th_cannibal: .byte "CANNIBAL",0
th_tools_lo: .byte <th_none,<th_gun,<th_bow,<th_spear,<th_blade,<th_club,<th_available
th_tools_hi: .byte >th_none,>th_gun,>th_bow,>th_spear,>th_blade,>th_club,>th_available
th_none: .byte "IN USE: NO WEAPON",0
th_gun: .byte "IN USE: GUN",0
th_bow: .byte "IN USE: BOW",0
th_spear: .byte "IN USE: SPEAR",0
th_blade: .byte "IN USE: AXE/KNIFE",0
th_club: .byte "IN USE: CLUB/ROCK",0
th_available: .byte "BLADE AVAILABLE, NOT IN USE",0
th_choices_lo: .byte <th_attack,<th_scare,<th_ignore,<th_equip,<th_fire,<th_walk,<th_swim
th_choices_hi: .byte >th_attack,>th_scare,>th_ignore,>th_equip,>th_fire,>th_walk,>th_swim
th_attack: .byte "> ATTACK (MAY FAIL / INJURE)",0
th_scare: .byte "> SCARE (MAY FAIL / INJURE)",0
th_ignore: .byte "> IGNORE (MAY INJURE / STEAL)",0
th_equip: .byte "> PREPARE WEAPON (NATIVE USE)",0
th_fire: .byte "> MAKE FIRE (NATIVE FORM)",0
th_douse: .byte "> DOUSE FIRE (BEFORE MOVING)",0
th_walk: .byte "> FLEE: WALK (NATIVE FORM)",0
th_swim: .byte "> FLEE: SWIM (NATIVE FORM)",0
