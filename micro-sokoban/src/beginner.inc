; Five teaching levels and user-selectable sound options.
.segment "WORKBSS"
title_music_index: .res 1
title_music_wait:  .res 1
.code
sound_enabled:
        LDA demo_active
        BEQ @game
        LDA hof_buf+HOF_SOUND
        AND #4
        RTS
@game:  LDA hof_buf+HOF_SOUND
        AND #1
        RTS

cheat_on:
        LDA hof_buf+HOF_SOUND
        AND #8
        RTS

menu_sound:
        LDA hof_buf+HOF_SOUND
        AND #2
        BEQ @done
        LDA #8
        LDX #48
        JSR tone
@done:  RTS

; Sparse swung ii-V-I: Dm9 / G13 / Cmaj9, with low bass notes and upper
; extensions. Three 4/4 bars at ~100 BPM, with 2:1 swung eighths in the
; outer bars and steady quarters in the middle. MENU SOUND controls it;
; input and animation keep running between notes.
title_music:
        LDA hof_buf+HOF_SOUND
        AND #2
        BEQ @done
        DEC title_music_wait
        BNE @done
        LDX title_music_index
        LDA title_note_rest,X
        STA title_music_wait
        LDA title_note_length,X
        PHA
        LDA title_note_period,X
        TAX
        PLA
        JSR title_tone
        ; Account for time spent sustaining the note, so the corridor and
        ; attract countdown keep their pace instead of counting only rests.
        LDX title_music_index
        LDA idle_lo
        ORA idle_hi
        BEQ @animation
        LDA idle_lo
        SEC
        SBC title_note_ticks,X
        STA idle_lo
        LDA idle_hi
        SBC #0
        STA idle_hi
        BCS @animation
        LDA #0
        STA idle_lo
        STA idle_hi
@animation:
        LDA title_tick
        BNE @remaining
        LDA #$FF                        ; zero encodes a freshly reset 256-poll tick
@remaining:
        SEC
        SBC title_note_ticks,X
        BCS @tick
        CLC
        ADC #<TITLE_TICK
        STA title_tick
        JSR title_step
        JMP @next
@tick:  STA title_tick
@next:
        INC title_music_index
        LDA title_music_index
        CMP #16
        BCC @done
        LDA #0
        STA title_music_index
@done:  RTS

; Longer half-periods than gameplay beeps: C3..A4 (~130..440 Hz).
; A duration unit is a full speaker cycle (two flips), allowing longer
; sustains than the old byte-sized flip count. The score converts musical
; durations to cycle counts for each pitch, keeping the beat consistent.
title_tone:
        TAY
        STX snd_period
@cycle: JSR title_half_period
        JSR title_half_period
        DEY
        BNE @cycle
        RTS

title_half_period:
        LDA SPKR
        LDX snd_period
@delay: NOP
        NOP
        NOP
        NOP
        NOP
        NOP
        DEX
        BNE @delay
        RTS

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
        ADC #80
        STA num_sl
        LDA #184
        STA num_col
        JSR draw_str
        INC hof_row
        LDA hof_row
        CMP #5
        BCC @status
        LDA option_sel
        ASL A
        ASL A
        ASL A
        ASL A
        CLC
        ADC #80
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
        CPX #5
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
        LDA #5
        BNE @cursor
@down:  INC option_sel
        LDA option_sel
        CMP #6
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
; One poll is ~6.3 ms (~6426 CPU cycles). A quarter is 95 polls:
; ~600 ms / 100 BPM. Swung eighths divide it into 63 + 32 polls.
; Each event includes its sustain AND its following gap. Derive all four
; tables from the same score so changing a pitch cannot change the tempo.
TITLE_QUARTER = 95
TITLE_SWING_LONG = 63
TITLE_SWING_SHORT = TITLE_QUARTER-TITLE_SWING_LONG
TITLE_POLL_CYCLES = 6426

.macro TITLE_NOTE field, period, slot, gap
        .local length, ticks
        ; Two half-period calls plus DEY/BNE: ~34*period+43 cycles.
        length = ((slot-gap)*TITLE_POLL_CYCLES+(34*period+43)/2)/(34*period+43)
        ticks = (length*(34*period+43)+TITLE_POLL_CYCLES/2)/TITLE_POLL_CYCLES
        .assert length > 0 .and length < 256, error, "Title note duration out of range"
        .assert ticks < slot, error, "Title note needs a rest"
        .if field = 0
                .byte period
        .elseif field = 1
                .byte length
        .elseif field = 2
                .byte slot-ticks
        .else
                .byte ticks
        .endif
.endmacro

.macro TITLE_SCORE field
        ; Dm9: D3 F3 A3 C4 E4 C4, swung with a quarter on each end.
        TITLE_NOTE field, 203, TITLE_QUARTER, 8
        TITLE_NOTE field, 171, TITLE_SWING_LONG, 8
        TITLE_NOTE field, 135, TITLE_SWING_SHORT, 8
        TITLE_NOTE field, 114, TITLE_SWING_LONG, 8
        TITLE_NOTE field,  90, TITLE_SWING_SHORT, 8
        TITLE_NOTE field, 114, TITLE_QUARTER, 16
        ; G13: G3 B3 E4 A4, four relaxed quarters.
        TITLE_NOTE field, 152, TITLE_QUARTER, 8
        TITLE_NOTE field, 120, TITLE_QUARTER, 8
        TITLE_NOTE field,  90, TITLE_QUARTER, 8
        TITLE_NOTE field,  68, TITLE_QUARTER, 16
        ; Cmaj9: C3 E3 B3 D4 G4 E4, breathe before the loop repeats.
        TITLE_NOTE field, 229, TITLE_QUARTER, 8
        TITLE_NOTE field, 181, TITLE_SWING_LONG, 8
        TITLE_NOTE field, 120, TITLE_SWING_SHORT, 8
        TITLE_NOTE field, 101, TITLE_SWING_LONG, 8
        TITLE_NOTE field,  76, TITLE_SWING_SHORT, 8
        TITLE_NOTE field,  90, TITLE_QUARTER, 24
.endmacro

title_note_period: TITLE_SCORE 0
title_note_length: TITLE_SCORE 1
title_note_rest:   TITLE_SCORE 2
title_note_ticks:  TITLE_SCORE 3
option_masks: .byte 1, 2, 4, 0, 8
options_table:
        .byte <options_title, >options_title, 13,16,2
        .byte <options_keys, >options_keys, 48,48,STYLE_COMPACT
        .byte <option_game, >option_game, 64,80,STYLE_COMPACT
        .byte <option_menu, >option_menu, 64,96,STYLE_COMPACT
        .byte <option_demo, >option_demo, 64,112,STYLE_COMPACT
        .byte <option_dead, >option_dead, 64,128,STYLE_COMPACT
        .byte <option_cheat, >option_cheat, 64,144,STYLE_COMPACT
        .byte <option_back, >option_back, 64,160,STYLE_COMPACT
        .byte <options_back, >options_back, 100,180,STYLE_COMPACT
        .word $FFFF
options_title: GSTR "OPTIONS"
options_keys:  GSTR "STICK/I/K  RETURN CHANGE"
option_game:   GSTR "GAME SOUND"
option_menu:   GSTR "MENU SOUND"
option_demo:   GSTR "DEMO SOUND"
option_dead:   GSTR "DEADLOCK"
option_cheat:  GSTR "CHEAT MODE"
option_back:   GSTR "BACK"
options_back:  GSTR "ESC BACK"
option_on:     GSTR "ON"
option_off:    GSTR "OFF"
tutorial_title:GSTR "TUTORIAL "
tutorial_keys: GSTR "IJKL MOVE  U UNDO  H HELP"
.include "tutorial.inc"
