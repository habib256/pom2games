; Five teaching levels and user-selectable options.
sound_enabled:
        LDA demo_active
        BEQ @game
        LDA hof_buf+HOF_SOUND
        AND #OPT_DEMO
        RTS
@game:  LDA hof_buf+HOF_SOUND
        AND #OPT_GAME
        RTS

cheat_on:
        LDA hof_buf+HOF_SOUND
        AND #OPT_CHEAT
        RTS

menu_sound:
        LDA hof_buf+HOF_SOUND
        AND #OPT_MENU
        BEQ @done
        LDA #8
        LDX #48
        JSR tone
@done:  RTS

tutorial_next:
        INC tutorial_idx
        LDA tutorial_idx
        CMP #5
        BCC @next
        LDA #0
        STA tutorial_on
        STA tutorial_idx
        LDA hof_buf+HOF_TUTORIAL
        ORA #1
        STA hof_buf+HOF_TUTORIAL
        LDA save_buf+4
        ORA #$80
        STA save_buf+4
        LDA save_mask
        ORA #1
        STA save_mask
        JSR write_save
        JSR write_hof
@next:  JMP game_loop

draw_tutorial_info:
        LDA #8
        STA num_step
        TEXT 92, 24, tutorial_title
        LDA tutorial_idx
        CLC
        ADC #1
        JSR put_glyph
        LDA #G_SLASH
        JSR put_glyph
        LDA #5
        JSR put_glyph
        LDX tutorial_idx
        LDA tutorial_hint_lo,X
        STA sptr_lo
        LDA tutorial_hint_hi,X
        STA sptr_hi
        LDA #48
        STA num_sl
        LDA #56
        STA num_col
        JSR draw_str
        TEXT 48, 164, tutorial_keys
        RTS

run_options:
        LDA #0
        STA option_sel
@paint: JSR begin_screen
        LDA #<options_table
        STA tbl_lo
        LDA #>options_table
        STA tbl_hi
        JSR draw_from_table
        LDA #8
        STA num_step
        LDA #0
        STA hof_row
@status:
        LDX hof_row
        CPX #3
        BEQ @deadlock
        LDA hof_buf+HOF_SOUND
        AND option_masks,X
        JMP @value
@deadlock:
        LDA deadwarn_on
@value: BEQ @off
        LDA #<option_on
        STA sptr_lo
        LDA #>option_on
        STA sptr_hi
        JMP @text
@off:   LDA #<option_off
        STA sptr_lo
        LDA #>option_off
        STA sptr_hi
@text:
        LDA hof_row
        ASL A
        ASL A
        ASL A
        ASL A
        CLC
        ADC #OPTIONS_SL0
        STA num_sl
        LDA #184
        STA num_col
        JSR draw_str
        INC hof_row
        LDA hof_row
        CMP #OPTIONS_BACK
        BCC @status
        LDA option_sel
        ASL A
        ASL A
        ASL A
        ASL A
        CLC
        ADC #OPTIONS_SL0
        STA num_sl
        LDA #40
        STA num_col
        LDA #G_PLUS
        JSR put_glyph
        JSR draw_screen_sides
        JSR show_screen
@wait:  JSR get_input
        CMP #ACT_MENU
        BEQ @back
        CMP #ACT_UP
        BEQ @up
        CMP #ACT_DOWN
        BEQ @down
        CMP #ACT_SELECT
        BEQ @select
        CMP #ACT_DEADWARN
        BEQ @dead
        CMP #ACT_UNDO
        BNE @wait
        LDA in_src
        BEQ @wait
@select:
        LDX option_sel
        CPX #OPTIONS_BACK
        BEQ @back
        CPX #3
        BEQ @dead
        LDA hof_buf+HOF_SOUND
        EOR option_masks,X
        STA hof_buf+HOF_SOUND
        JMP @changed
@dead:  LDA deadwarn_on
        EOR #1
        STA deadwarn_on
@changed:
        JSR menu_sound
        JMP @paint
@up:    DEC option_sel
        BPL @changed
        LDA #OPTIONS_BACK
        BNE @cursor
@down:  INC option_sel
        LDA option_sel
        CMP #OPTIONS_BACK+1
        BCC @changed
        LDA #0
@cursor:
        STA option_sel
        JMP @changed
@back:  LDA hof_buf+HOF_TUTORIAL
        AND #1
        STA temp
        LDA deadwarn_on
        ASL A
        ORA temp
        STA hof_buf+HOF_TUTORIAL
        JMP write_hof

.rodata
OPTIONS_SL0  = 64       ; scanline of the first switch; 16 lines per row
OPTIONS_BACK = 6        ; row of BACK, below the switches
option_masks: .byte OPT_GAME, OPT_MENU, OPT_DEMO, 0, OPT_CHEAT, OPT_COLOR
options_table:
        .byte <options_title, >options_title, 13,16,2
        .byte <options_keys, >options_keys, 48,48,STYLE_COMPACT
        .byte <option_game, >option_game, 64,OPTIONS_SL0,STYLE_COMPACT
        .byte <option_menu, >option_menu, 64,OPTIONS_SL0+16,STYLE_COMPACT
        .byte <option_demo, >option_demo, 64,OPTIONS_SL0+32,STYLE_COMPACT
        .byte <option_dead, >option_dead, 64,OPTIONS_SL0+48,STYLE_COMPACT
        .byte <option_cheat, >option_cheat, 64,OPTIONS_SL0+64,STYLE_COMPACT
        .byte <option_color, >option_color, 64,OPTIONS_SL0+80,STYLE_COMPACT
        .byte <option_back, >option_back, 64,OPTIONS_SL0+16*OPTIONS_BACK,STYLE_COMPACT
        .byte <options_back, >options_back, 100,180,STYLE_COMPACT
        .word $FFFF
options_title = menu_options    ; same glyph string; the table chooses its size
options_keys:  GSTR "STICK/I/K  RETURN CHANGE"
option_game:   GSTR "GAME SOUND"
option_menu:   GSTR "MENU SOUND"
option_demo:   GSTR "DEMO SOUND"
option_dead:   GSTR "DEADLOCK"
option_cheat:  GSTR "CHEAT MODE"
option_color:  GSTR "COLOR MODE"
option_back:   GSTR "BACK"
options_back:  GSTR "ESC BACK"
option_on:     GSTR "ON"
option_off:    GSTR "OFF"
tutorial_title:GSTR "TUTORIAL "
tutorial_keys: GSTR "IJKL MOVE  U UNDO  H HELP"
.include "tutorial.inc"
