; Deferred alongside narrator text: no title/menu code depends on this region.
.segment "NARRATOR"

; The five-bit narrator retains all 96 original lines and RNG calls.
unpack_narrator:
        LDA #0
        STA narrator_left
        STA ch_idx
@next:  JSR narrator_symbol
        BEQ @end
        CMP #31
        BNE @plain
        JSR narrator_symbol
        TAX
        LDA narrator_escape,X
        JMP @put
@plain: TAX
        LDA narrator_alphabet,X
@put:   LDX ch_idx
        STA narrator_buffer,X
        INC ch_idx
        JMP @next
@end:   LDX ch_idx
        STA narrator_buffer,X
        LDA #<narrator_buffer
        LDX #>narrator_buffer
        JMP set_msg

narrator_symbol:
        LDA #0
        STA tmp2
        LDX #5
@bit:   LDA narrator_left
        BNE @ready
        LDY #0
        LDA (str_lo),Y
        STA narrator_bits
        INC str_lo
        BNE @same_page
        INC str_hi
@same_page:
        LDA #8
        STA narrator_left
@ready: ASL narrator_bits
        ROL tmp2
        DEC narrator_left
        DEX
        BNE @bit
        LDA tmp2
        RTS
narrator_alphabet: .byte 0," ABCDEFGHIJKLMNOPQRSTUVWXYZ!.,"
narrator_escape: .byte "'-?"

; Spend one potion to restore 10 HP, up to 30. Carry signals success.
drink_potion:
        LDA p_potions
        BEQ @empty
        LDA p_hp
        CMP #30
        BCS @full
        DEC p_potions
        CLC
        ADC #10
        CMP #31
        BCC @store
        LDA #30
@store: STA p_hp
        LDA #<str_healed
        LDX #>str_healed
        JSR ux_message
        JSR sound_level
        SEC
        RTS
@empty: LDA #<str_no_potion
        LDX #>str_no_potion
        BNE @refuse
@full:  LDA #<str_full_hp
        LDX #>str_full_hp
@refuse:
        JSR ux_message
        CLC
        RTS


; A=price. Carry set when paid; gold is held to the HUD's two digits.
shop_pay:
        STA tmp2
        LDA p_gold
        CMP tmp2
        BCC @no
        SEC
        SBC tmp2
        STA p_gold
        SEC
        RTS
@no:    LDA #<str_no_gold
        LDX #>str_no_gold
        JSR ux_message
        CLC
        RTS

; Set feedback without advancing the turn or altering random state.
ux_message:
        JSR set_msg
        LDA #HUD_BOTH
        STA hud_dirty
        LDA gstate
        CMP #ST_COMBAT
        BNE @done
        JSR draw_feedback
@done:  RTS

draw_feedback:
        LDA #176
        LDX #184
        JSR clear_span
        LDA msg_lo
        LDX msg_hi
        LDY #22
        JMP draw_str_centered

draw_objective:
        STY rd_face
        LDA p_relic
        BEQ @relic
        LDA p_floor
        CMP #LAST_FLOOR
        BNE @exit
        LDA mob_type+NUM_MOBS-1
        CMP #MOB_DEAD
        BEQ @exit
        LDA #<str_goal_dragon
        LDX #>str_goal_dragon
        BNE @draw
@exit:  LDA #<str_goal_exit
        LDX #>str_goal_exit
        BNE @draw
@relic: LDA #<str_goal_relic
        LDX #>str_goal_relic
@draw:  LDY rd_face
        JMP draw_str_centered

round_begin:
        STA round_action
        LDA #0
        STA round_hit
        LDA p_gold
        STA round_gold
        RTS

; Display damage and the action's outcome on separate, stable rows.
draw_round_result:
        LDA #176
        LDX #192
        JSR clear_span
        LDA #3
        STA ch_cx
        LDA #22
        STA ch_cy
        LDA #<str_damage
        LDX #>str_damage
        JSR print_str_ax
        LDA #7
        STA ch_cx
        LDA round_hit
        JSR write_decimal_2d
        LDA #19
        STA ch_cx
        LDA ev_dmg
        JSR write_decimal_2d
        LDA round_action
        CMP #KEY_F
        BEQ @flee
        CMP #KEY_P
        BEQ @heal
        LDA p_gold
        CMP round_gold
        BCC @stolen
        LDA p_focus
        BNE @guard
        LDA #<str_attack_done
        LDX #>str_attack_done
        BNE @draw
@guard: LDA #<str_guarded
        LDX #>str_guarded
        BNE @draw
@stolen:
        LDA #<str_stolen
        LDX #>str_stolen
        BNE @draw
@heal:  LDA #<str_healed
        LDX #>str_healed
        BNE @draw
@flee:  LDA #<str_flee_failed
        LDX #>str_flee_failed
@draw:  JSR set_msg
        LDY #23
        JMP draw_str_centered

str_choose_action: .byte "CHOOSE YOUR ACTION",0
str_vitals: .byte "HP   /30  POTIONS     GOLD",0
str_stats: .byte "ATK     DEF     LVL     XP",0
str_goal_relic: .byte "GOAL: FIND THE RELIC",0
str_goal_dragon: .byte "GOAL: DEFEAT THE DRAGON",0
str_goal_exit: .byte "GOAL: REACH THE EXIT",0
str_no_potion: .byte "NO POTIONS LEFT",0
str_full_hp: .byte "HEALTH ALREADY FULL",0
str_full_bag: .byte "POTION BAG FULL",0
str_no_gold: .byte "NOT ENOUGH GOLD",0
str_bought: .byte "PURCHASE COMPLETE",0
str_healed: .byte "POTION USED: UP TO +10 HP",0
str_fled: .byte "ESCAPED TO PREVIOUS CELL",0
str_killed: .byte "FOE SLAIN: GOLD AND +4 XP",0
str_damage: .byte "HIT      TAKEN",0
str_attack_done: .byte "ATTACK COMPLETE",0
str_guarded: .byte "GUARD: HALF HIT, NEXT ATK +2",0
str_stolen: .byte "GOBLIN STOLE 1 GOLD",0
str_flee_failed: .byte "ESCAPE FAILED: FOE ATTACKS",0
.code
