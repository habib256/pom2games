; VERHILLE Arnaud — GPL-3.0. Reversible native hunting preparation.
.segment "GUIDANCE"
; Loaded by SITES after leaving GRID. No command, random draw, clock or
; inventory write occurs until the player accepts the proposed queue.
navigation_hunt_review:
        lda     #0
        beq     hunt_review_start
navigation_hunt_change:
        lda     #1
hunt_review_start:
        sta     hunt_action
        ; The native weapon already in use is distinct from an activation
        ; proposal. Browsing changes only the unexecuted UI queue.
        jsr     hunt_weapon
        stx     hunt_active
        lda     #0
        sta     hunt_choice
        sta     hunt_craft
        ldx     #1
        jsr     hunt_crafted
        cmp     #$FF
        bne     @draw
        jsr     woods_here
        bcc     @draw
        lda     region_number
        cmp     #3
        bcc     @rope
        cmp     #6
        bcc     @can_craft
@rope: ldx     #60
        jsr     have
        bcs     @can_craft
        ldx     #67
        jsr     have
        bcc     @draw
@can_craft:
        inc     hunt_craft
@draw: lda     #<hunt_active_text
        ldx     #>hunt_active_text
        jsr     message
        ldy     hunt_active
        jsr     hunt_name
        lda     #<hunt_proposal
        ldx     #>hunt_proposal
        jsr     hunt_append
        jsr     hunt_proposed
        stx     hunt_tool
        txa
        tay
        jsr     hunt_name
        lda     mq_n
        beq     @ready
        lda     #<hunt_prepare
        ldx     #>hunt_prepare
        bne     @status
@ready: lda     #<hunt_ready
        ldx     #>hunt_ready
@status:
        jsr     hunt_append
        ldx     hunt_tool
        beq     @none
        lda     light
        beq     @dark
        cpx     #4
        bcs     @weak
        lda     #<hunt_light
        ldx     #>hunt_light
        bne     @detail
@none: lda     #<hunt_need
        ldx     #>hunt_need
        bne     @detail
@dark: lda     #<hunt_dark
        ldx     #>hunt_dark
        bne     @detail
@weak: lda     #<hunt_weak
        ldx     #>hunt_weak
@detail:
        jsr     hunt_append
        ldy     hunt_action
        bne     @action
        lda     mq_n
        beq     @action
        lda     #<hunt_activate
        ldx     #>hunt_activate
        bne     @action_text
@action:
        lda     hunt_actions_lo,y
        ldx     hunt_actions_hi,y
@action_text:
        jsr     hunt_append
@key:  jsr     wait_key
        cmp     #KC_RET
        beq     @accept
        cmp     #KC_LEFT
        beq     @previous
        cmp     #KC_UP
        beq     @previous
        cmp     #KC_RIGHT
        beq     @next
        cmp     #KC_DOWN
        beq     @next
        cmp     #'W'
        jeq     @weapon
        cmp     #'C'
        jeq     @craft
        cmp     #KC_ESC
        jne     @key
        lda     #0
        jeq     hunt_leave
@accept:
        lda     hunt_action
        beq     @yes
        cmp     #1
        jeq     @weapon
        bne     @craft
@previous:
        lda     hunt_action
        bne     :+
        lda     #2
        ldx     hunt_craft
        bne     @set_action
        lda     #1
        bne     @set_action
:       sec
        sbc     #1
        jmp     @set_action
@next: lda     hunt_action
        clc
        adc     #1
        cmp     #2
        bcc     @set_action
        bne     @first
        ldx     hunt_craft
        bne     @set_action
@first:lda     #0
@set_action:
        sta     hunt_action
        jmp     @draw
@craft:lda     hunt_craft
        jeq     @key
        lda     #2              ; MAKE SPEAR only; never queue a hunt yet
        jne     hunt_leave
@yes:  lda     #1
        jne     hunt_leave
@weapon:
        inc     hunt_choice
        lda     hunt_choice
        cmp     #4
        bcc     :+
        lda     #1
        sta     hunt_choice
:       cmp     #1
        bne     @crafted
        ldx     #57
        jsr     have
        bcc     @skip
        lda     it_pack_lo+57
        ora     it_pack_hi+57
        beq     @skip
        lda     #S_GUN
        bne     @select
@crafted:
        sec
        sbc     #2
        tax
        jsr     hunt_crafted
        cmp     #$FF
        beq     @skip
        lda     hunt_choice
        clc
        adc     #S_BOW-2
@select:
        sta     mq_list
        lda     #1
        sta     mq_n
        lda     #0
        sta     mq_i
        jmp     @draw
@skip: ; An unavailable entry never composes a command or changes stock.
        lda     hunt_choice
        cmp     #3
        jcc     @weapon
        jmp     @draw
hunt_leave:
        pha
        lda     #10
        jsr     overlay_load
        pla
        jmp     hunt_execute
hunt_append:
        sta     gp1
        stx     gp1+1
        jmp     message_text
hunt_name:
        lda     hunt_names_lo,y
        ldx     hunt_names_hi,y
        jmp     hunt_append
; X = BOW/SPEAR slot, exact native cr_where availability.
hunt_crafted:
        lda     cr_b1,x
        bne     @done
        lda     cr_cx,x
        cmp     px+1
        bne     @away
        lda     cr_cy,x
        cmp     py+1
        bne     @away
        lda     #0
@done: rts
@away: lda     #$FF
        rts
hunt_proposed:
        lda     mq_n
        beq     hunt_weapon
        lda     mq_list
        ldx     #1
        cmp     #S_GUN
        beq     hunt_return
        inx
        cmp     #S_BOW
        beq     hunt_return
        inx
        cmp     #S_SPEAR
        beq     hunt_return
        inx
        cmp     #S_AXE
        beq     hunt_return
        inx
        cmp     #S_KNIFE
        beq     hunt_return
        jmp     hunt_weapon
hunt_return: rts

; Match fr_hunt's native precedence, including an active CLUB/ROCK.
; X: none, gun, bow, spear, axe, knife, club/rock.
hunt_weapon:
        ldx     #1
        lda     camp_use
        and     #U_GUN
        bne     @done
        inx
        lda     fg_use
        and     #FT_BOW
        bne     @done
        inx
        lda     fg_use
        and     #FT_SPEAR
        bne     @done
        lda     care_tools
        and     #3
        beq     @club
        lda     care_tool_x
        cmp     px+1
        bne     @club
        lda     care_tool_y
        cmp     py+1
        bne     @club
        ldx     #4
        lda     care_tools
        and     #1
        bne     @done
        inx
        bne     @done
@club: ldx     #6
        lda     fg_use
        and     #FT_CLUB
        bne     @done
@none: ldx     #0
@done: rts
hunt_tool: .byte 0
hunt_active: .byte 0
hunt_choice: .byte 0
hunt_craft: .byte 0
hunt_action: .byte 0
hunt_names_lo: .byte <hunt_none,<hunt_gun,<hunt_bow,<hunt_spear,<hunt_axe,<hunt_knife,<hunt_club
hunt_names_hi: .byte >hunt_none,>hunt_gun,>hunt_bow,>hunt_spear,>hunt_axe,>hunt_knife,>hunt_club
hunt_none: .byte "NONE",0
hunt_gun: .byte "GUN",0
hunt_bow: .byte "BOW",0
hunt_spear: .byte "SPEAR",0
hunt_axe: .byte "AXE",0
hunt_knife: .byte "KNIFE",0
hunt_club: .byte "CLUB/ROCK",0
hunt_active_text: .byte "IN USE: ",0
hunt_proposal: .byte "; NEXT: ",0
hunt_prepare: .byte " (OWNED)",0
hunt_ready: .byte "",0
hunt_light: .byte "|15 MIN; SUCCESS UNCERTAIN",0
hunt_dark: .byte "|NO LIGHT: NO CHANCE",0
hunt_weak: .byte "|NO CHANCE WITH THIS WEAPON",0
hunt_need: .byte "|NEED GUN/BOW/SPEAR",0
hunt_actions_lo: .byte <hunt_attempt,<hunt_change,<hunt_make
hunt_actions_hi: .byte >hunt_attempt,>hunt_change,>hunt_make
hunt_attempt: .byte "|> HUNT  ARROWS:CHOOSE ESC:BACK",0
hunt_activate: .byte "|> PREPARE WEAPON  RET:SELECT ESC:BACK",0
hunt_change: .byte "|> CHANGE WEAPON  RET:SELECT ESC:BACK",0
hunt_make: .byte "|> MAKE SPEAR  RET:CONFIRM ESC:BACK",0

; Native hunting results keep the left result intact. The four dependency
; bytes are the retained UI context; every next native action is explicit.
navigation_hunt_result:
        lda     #0
        sta     hunt_choice
        sta     hunt_active     ; 1 = miss, with three deliberate choices
        lda     #$FF
        sta     hunt_tool       ; next native verb, or no remaining prey
        lda     #4
        sta     hunt_craft      ; title: prey gone
        lda     dep_mask
        sec
        sbc     #76
        cmp     #4
        jcc     hunt_result_draw
        cmp     #6
        jcs     hunt_result_draw
        tax
        lda     fg_x
        cmp     px+1
        jne     hunt_result_draw
        lda     fg_y
        cmp     py+1
        jne     hunt_result_draw
        lda     fg_b2,x
        jmi     hunt_result_draw
        bne     @carcass
        lda     #21
        sta     hunt_tool
        lda     #0
        sta     hunt_craft
        lda     dep_running
        cmp     #$85
        jeq     hunt_result_draw
        inc     hunt_active
        inc     hunt_craft
        jne     hunt_result_draw
@carcass:
        lda     fg_gl,x
        ora     fg_gh,x
        jeq     hunt_result_draw
        lda     #7
        sta     hunt_tool
        lda     #3
        sta     hunt_craft
        cpx     #4
        jne     hunt_result_draw ; FISH is never skinned
        lda     fg_skin
        and     #16
        jeq     hunt_result_draw
        lda     #19
        sta     hunt_tool
        dec     hunt_craft
hunt_result_draw:
        lda     #20
        sta     hunt_row
@clear: lda     hunt_row
        jsr     hunt_result_position
        ldx     #41
@space: txa
        tay
        lda     #' '|$80
        jsr     t_update
        inx
        cpx     #80
        bcc     @space
        inc     hunt_row
        lda     hunt_row
        cmp     #24
        bcc     @clear
        lda     #20
        jsr     hunt_result_position
        ldy     hunt_craft
        lda     hunt_result_titles_lo,y
        ldx     hunt_result_titles_hi,y
        jsr     hunt_result_string
        lda     #21
        jsr     hunt_result_position
        lda     dep_mask
        cmp     #81
        beq     @fish
        jsr     puts
        .byte "GAME",0
        jmp     @quantity
@fish: jsr     puts
        .byte "FISH",0
@quantity:
        lda     hunt_tool
        cmp     #7
        beq     @ounces
        cmp     #19
        bne     @choice
@ounces:
        jsr     puts
        .byte " GROUND ",0
        ldx     dep_mask
        lda     fg_gl-76,x
        sta     num
        lda     fg_gh-76,x
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " OZ",0
@choice:
        lda     #22
        jsr     hunt_result_position
        lda     hunt_active
        beq     @single
        ldy     hunt_choice
        lda     hunt_result_choices_lo,y
        ldx     hunt_result_choices_hi,y
        jsr     hunt_result_string
        jmp     @hint
@single:
        lda     hunt_tool
        cmp     #19
        beq     @skin
        cmp     #7
        beq     @get
        cmp     #21
        beq     @review
        jsr     puts
        .byte "> RETURN TO VIEW",0
        jmp     @hint
@review:
        jsr     puts
        .byte "> REVIEW WEAPON / HUNT",0
        jmp     @hint
@skin: jsr     puts
        .byte "> SKIN THIS CARCASS",0
        jmp     @hint
@get:  jsr     puts
        .byte "> GET THIS MEAT",0
@hint: lda     #23
        jsr     hunt_result_position
        jsr     puts
        .byte "RET:SELECT ESC:BACK ARROWS:CHOOSE",0
@key:  jsr     guidance_view_key
        cmp     #KC_ESC
        beq     hunt_result_cancel
        cmp     #KC_RET
        beq     hunt_result_accept
        cmp     #KC_LEFT
        beq     @previous
        cmp     #KC_UP
        beq     @previous
        cmp     #KC_RIGHT
        beq     @next
        cmp     #KC_DOWN
        bne     @key
@next: lda     hunt_active
        beq     @key
        inc     hunt_choice
        lda     hunt_choice
        cmp     #3
        bcc     @redraw
        lda     #0
        sta     hunt_choice
        beq     @redraw
@previous:
        lda     hunt_active
        beq     @key
        dec     hunt_choice
        bpl     @redraw
        lda     #2
        sta     hunt_choice
@redraw:
        jmp     hunt_result_draw
hunt_result_accept:
        lda     hunt_active
        beq     @single
        ldx     hunt_choice
        lda     hunt_result_verbs,x
        jmp     hunt_result_leave
@single:
        lda     hunt_tool
        jmp     hunt_result_leave
hunt_result_cancel:
        lda     #$FF
hunt_result_leave:
        pha
        lda     #10
        jsr     overlay_load
        pla
        jmp     hunter_result_execute
hunt_result_position:
        sta     CV
        jsr     t_vtab
        lda     #41
        sta     CH
        rts
hunt_result_string:
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
hunt_row: .byte 0
hunt_result_verbs: .byte 21,$FE,$FF
hunt_result_titles_lo: .byte <hunt_prepared,<hunt_missed,<hunt_carcass,<hunt_skinned,<hunt_gone
hunt_result_titles_hi: .byte >hunt_prepared,>hunt_missed,>hunt_carcass,>hunt_skinned,>hunt_gone
hunt_prepared: .byte "PREPARATION RESULT",0
hunt_missed: .byte "HUNT RESULT: PREY STILL ALIVE",0
hunt_carcass: .byte "HUNT RESULT: CARCASS",0
hunt_skinned: .byte "MEAT READY TO RECOVER",0
hunt_gone: .byte "PREY NO LONGER HERE",0
hunt_result_choices_lo: .byte <hunt_retry,<hunt_change_result,<hunt_abandon
hunt_result_choices_hi: .byte >hunt_retry,>hunt_change_result,>hunt_abandon
hunt_retry: .byte "> RETRY (REVIEW FIRST)",0
hunt_change_result: .byte "> CHANGE WEAPON",0
hunt_abandon: .byte "> ABANDON",0
