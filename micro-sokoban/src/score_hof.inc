; Move totals and Hall of Fame. Existing SOK2 record slots remain compatible.
; Rank solved levels descending, then total best moves ascending (exact 32-bit sum).
; MICROHOF ranks ten independent profiles; stable slots select save files.
.code

calculate_score:
        LDA #0
        STA score_total
        STA score_total+1
        STA score_total+2
        STA score_total+3
        STA score_solved
        STA score_solved+1
        LDA #<TOTAL_LEVELS
        STA score_left
        LDA #>TOTAL_LEVELS
        STA score_left+1
        LDA #<(save_buf+SAVE_HDR)
        STA sptr_lo
        LDA #>(save_buf+SAVE_HDR)
        STA sptr_hi
@level: LDY #0
        LDA (sptr_lo),Y
        INY
        ORA (sptr_lo),Y
        BEQ @next
        INC score_solved
        BNE @points
        INC score_solved+1
@points:
        LDY #0
        LDA score_total
        CLC
        ADC (sptr_lo),Y
        STA score_total
        INY
        LDA score_total+1
        ADC (sptr_lo),Y
        STA score_total+1
        LDA score_total+2
        ADC #0
        STA score_total+2
        LDA score_total+3
        ADC #0
        STA score_total+3
@next:  LDA sptr_lo
        CLC
        ADC #4
        STA sptr_lo
        BCC @count
        INC sptr_hi
@count: LDA score_left
        BNE @dec
        DEC score_left+1
@dec:   DEC score_left
        LDA score_left
        ORA score_left+1
        BNE @level
        RTS

; Eight digits from the u32 score_work, at the usual text cursor.
print_score:
        LDA #0
        STA num_pow
@digit: LDX num_pow
        LDA #0
        STA score_digit
@sub:   LDA score_work
        SEC
        SBC score_pow_lo,X
        STA temp
        LDA score_work+1
        SBC score_pow_mid,X
        STA temp2
        LDA score_work+2
        SBC score_pow_hi,X
        STA rank_hi
        LDA score_work+3
        SBC score_pow_top,X
        BCC @put
        STA score_work+3
        LDA rank_hi
        STA score_work+2
        LDA temp
        STA score_work
        LDA temp2
        STA score_work+1
        INC score_digit
        BNE @sub
@put:   LDA score_digit
        JSR put_glyph
        INC num_pow
        LDA num_pow
        CMP #8
        BCC @digit
        RTS

reset_hof:
        LDX #HOF_LEN-1
        LDA #0
@zero:  STA hof_buf,X
        DEX
        BPL @zero
        LDX #HOF_HDR-1
@head:  LDA hof_header,X
        STA hof_buf,X
        DEX
        BPL @head
        LDX #2
@profile:
        LDA hof_header+4,X
        STA hof_buf+HOF_PROFILES,X
        DEX
        BPL @profile
        LDA #2
        STA hof_buf+HOF_TUTORIAL
        LDA #3                          ; game and menu sound on by default
        STA hof_buf+HOF_SOUND
        RTS

load_hof:
        JSR reset_hof                   ; a short file cannot expose stale RAM
        JSR hof_file
        JSR fast_read
        JSR remember_hof
        LDX #2
@magic: LDA hof_buf,X
        CMP hof_header,X
        BEQ @magic_ok
        JMP @bad
@magic_ok:
        DEX
        BPL @magic
        LDA hof_buf+3
        CMP #'3'
        BEQ @names
        CMP #'2'
        BNE @old
        INC rankings_old
        LDA #'3'
        STA hof_buf+3
        JMP @names
@old:
        CMP #'1'
        BNE @bad_jump
        ; Legacy shared records belong to the last active initials, slot zero.
        LDX #2
@legacy:
        LDA hof_buf+4,X
        STA hof_buf+HOF_PROFILES,X
        DEX
        BPL @legacy
        LDA #0
        LDX #HOF_COUNT*HOF_ENTRY-1
@clear: STA hof_buf+HOF_HDR,X
        DEX
        BPL @clear
        LDA #'3'
        STA hof_buf+3
        JMP @names
@bad_jump:
        JMP @bad
@names: LDX #4
@name:  LDA hof_buf,X
        CMP #'A'
        BCC @bad
        CMP #'Z'+1
        BCS @bad
        INX
        CPX #HOF_HDR
        BCC @name
        LDX #HOF_HDR
@entry: LDA hof_buf,X
        BEQ @next
        STX hof_offset
        LDY #3
@letters:
        LDA hof_buf,X
        CMP #'A'
        BCC @bad
        CMP #'Z'+1
        BCS @bad
        INX
        DEY
        BNE @letters
        LDX hof_offset
@solved:
        LDA hof_buf+7,X
        AND #$7F
        CMP #>TOTAL_LEVELS
        BCC @next
        BNE @bad
        LDA hof_buf+6,X
        CMP #<TOTAL_LEVELS
        BCC @next
        BNE @bad
@next:  TXA
        CLC
        ADC #HOF_ENTRY
        TAX
        CPX #HOF_END
        BCC @entry
        LDA hof_buf+HOF_TUTORIAL
        CMP #4
        BCS @bad
        LSR A
        STA deadwarn_on
        LDA hof_buf+HOF_SOUND
        CMP #16                         ; bits 0-3: game, menu, demo, cheat
        BCS @bad
        JMP validate_profiles
@bad:   JSR reset_hof
        LDA #1
        STA deadwarn_on
        RTS

write_hof:
        LDX #HOF_LEN-1
@compare:
        LDA hof_buf,X
        CMP hof_disk_copy,X
        BNE @changed
        DEX
        BPL @compare
        RTS
@changed:
        JSR disk_protected
        BCS @done
        JSR hof_file
        JSR fast_write
        JMP remember_hof
@done:  RTS

; Update this named profile, then sort by solved count and move efficiency.
update_hof:
        LDX #HOF_HDR
@entry: LDA hof_buf,X
        BEQ @store
        CMP hof_buf+4
        BNE @next
        LDA hof_buf+1,X
        CMP hof_buf+5
        BNE @next
        LDA hof_buf+2,X
        CMP hof_buf+6
        BEQ @store
@next:  TXA
        CLC
        ADC #HOF_ENTRY
        TAX
        CPX #HOF_END
        BCC @entry
        LDX #HOF_END-HOF_ENTRY
@store: LDA hof_buf+4
        STA hof_buf,X
        LDA hof_buf+5
        STA hof_buf+1,X
        LDA hof_buf+6
        STA hof_buf+2,X
        LDA score_total
        STA hof_buf+3,X
        LDA score_total+1
        STA hof_buf+4,X
        LDA score_total+2
        STA hof_buf+5,X
        LDA score_solved
        STA hof_buf+6,X
        LDA score_total+3
        LSR A
        ROR A                           ; sum bit 24 in spare solved-count bit 15
        ORA score_solved+1
        STA hof_buf+7,X
        ; Sort all rows so fingerprint resets can also lower a profile's score.
        LDA #HOF_COUNT-1
        STA hof_index
@pass:  LDX #HOF_HDR+HOF_ENTRY
@pair:  LDA hof_buf,X
        BEQ @next_pair
        LDA hof_buf-HOF_ENTRY,X
        BEQ @swap
        LDA hof_buf+7-HOF_ENTRY,X
        AND #1
        STA temp
        LDA hof_buf+7,X
        AND #1
        CMP temp
        BCC @next_pair
        BNE @swap
        LDA hof_buf+6,X
        CMP hof_buf+6-HOF_ENTRY,X
        BCC @next_pair
        BNE @swap
        LDA hof_buf+7,X
        AND #$80
        STA temp
        LDA hof_buf+7-HOF_ENTRY,X
        AND #$80
        CMP temp
        BCC @next_pair
        BNE @swap
        LDA hof_buf+5-HOF_ENTRY,X
        CMP hof_buf+5,X
        BCC @next_pair
        BNE @swap
        LDA hof_buf+4-HOF_ENTRY,X
        CMP hof_buf+4,X
        BCC @next_pair
        BNE @swap
        LDA hof_buf+3-HOF_ENTRY,X
        CMP hof_buf+3,X
        BCC @next_pair
        BEQ @next_pair
@swap:  STX hof_offset
        LDY #HOF_ENTRY
@byte:  LDA hof_buf,X
        PHA
        LDA hof_buf-HOF_ENTRY,X
        STA hof_buf,X
        PLA
        STA hof_buf-HOF_ENTRY,X
        INX
        DEY
        BNE @byte
        LDX hof_offset
@next_pair:
        TXA
        CLC
        ADC #HOF_ENTRY
        TAX
        CPX #HOF_END
        BCC @pair
        DEC hof_index
        BNE @pass
        RTS

; ASCII letter -> the existing font's glyph index.
hof_letter:
        SEC
        SBC #'A'
        TAX
        LDA hof_letters,X
        RTS

run_hof_attract:
        LDA #10
        BNE hof_open
run_hof:
        LDA #0
hof_open:
        STA hof_cycles
@paint: JSR begin_screen
        LDA #<hof_table
        STA tbl_lo
        LDA #>hof_table
        STA tbl_hi
        JSR draw_from_table
        LDA #8
        STA num_step
        LDA #0
        STA hof_row
        LDA #HOF_HDR
        STA hof_offset
        LDA #52
        STA num_sl
@row:
        LDA #16
        STA num_col
        LDA hof_row
        CLC
        ADC #1
        STA num_lo
        LDA #0
        STA num_hi
        LDA #2
        JSR print_num
        LDX hof_offset
        LDA hof_buf,X
        BEQ @empty
        LDA #56
        STA num_col
        LDA #0
        STA hof_index
@name:  LDA hof_offset
        CLC
        ADC hof_index
        TAX
        LDA hof_buf,X
        JSR hof_letter
        JSR put_glyph
        INC hof_index
        LDA hof_index
        CMP #3
        BCC @name
        LDX hof_offset
        LDA hof_buf+7,X
        ASL A
        LDA #0
        ROL A
        STA score_work+3
        LDA hof_buf+3,X
        STA score_work
        LDA hof_buf+4,X
        STA score_work+1
        LDA hof_buf+5,X
        STA score_work+2
        LDA #112
        STA num_col
        JSR print_score
        LDX hof_offset
        LDA hof_buf+6,X
        STA num_lo
        LDA hof_buf+7,X
        AND #1
        STA num_hi
        LDA #208
        STA num_col
        LDA #3
        JSR print_num
        JMP @next
@empty: LDA #56
        STA num_col
        LDA #<hof_blank3
        STA sptr_lo
        LDA #>hof_blank3
        STA sptr_hi
        JSR draw_str
        LDA #112
        STA num_col
        LDA #<hof_blank6
        STA sptr_lo
        LDA #>hof_blank6
        STA sptr_hi
        JSR draw_str
        LDA #208
        STA num_col
        LDA #<hof_blank3
        STA sptr_lo
        LDA #>hof_blank3
        STA sptr_hi
        JSR draw_str
@next:  LDA num_sl
        CLC
        ADC #11
        STA num_sl
        LDA hof_offset
        CLC
        ADC #HOF_ENTRY
        STA hof_offset
        INC hof_row
        LDA hof_row
        CMP #HOF_COUNT
        BCS @shown
        JMP @row
@shown: LDA #HOF_TICK
        STA hof_blink_tick
        LDA #1
        STA hof_blink_state
        LDA #COLOR_ORANGE
        STA hof_blink_color
        JSR show_screen
@wait:  JSR get_input
        TAX
        LDA hof_cycles
        BEQ @action
        LDA in_src
        BNE @action
        TXA
        BNE @back                       ; any key interrupts the timed presentation
@action:
        TXA
        CMP #ACT_MENU
        BEQ @back
        CMP #ACT_SELECT
        BEQ @back
        CMP #ACT_UNDO
        BNE @blink
        LDA in_src
        BEQ @blink
@back:  LDA #0
        STA hof_cycles
        SEC
        RTS
@blink: DEC hof_blink_tick
        BNE @wait
        LDA #HOF_TICK
        STA hof_blink_tick
        JSR hof_title_step
        LDA hof_cycles
        BEQ @wait
        DEC hof_cycles
        BNE @wait
        CLC
        RTS

; Only redraw the heading; ranking, input handling and disk stay untouched.
hof_title_step:
        LDA hof_blink_state
        EOR #1
        STA hof_blink_state
        BEQ @off
        INC hof_blink_color
        LDA hof_blink_color
        CMP #COLOR_BLUE+1
        BCC @color
        LDA #COLOR_GREEN
        STA hof_blink_color
@color: STA big_color
        LDA #<hof_title
        STA sptr_lo
        LDA #>hof_title
        BNE @draw
@off:   LDA #COLOR_WHITE
        STA big_color
        LDA #<hof_title_blank
        STA sptr_lo
        LDA #>hof_title_blank
@draw:  STA sptr_hi
        LDA #8
        STA title_col_start
        STA title_scanline
        JMP draw_title_big_line

edit_initials:
        LDA profile_sel
        JSR profile_offset
        LDA hof_buf+HOF_PROFILES,X
        BEQ @default
        LDY #0
@selected:
        LDA hof_buf+HOF_PROFILES,X
        STA hof_initials,Y
        INX
        INY
        CPY #3
        BCC @selected
        BEQ @ready
@default:
        LDX #2
@copy:  LDA hof_buf+4,X
        STA hof_initials,X
        DEX
        BPL @copy
@ready: LDA #0
        STA hof_index
@paint: JSR begin_screen
        LDA #<initials_table
        STA tbl_lo
        LDA #>initials_table
        STA tbl_hi
        JSR draw_from_table
        TEXT 108, 20, menu_profiles
@letters:
        LDA #8
        STA num_step
        LDA #128
        STA num_col
        LDA #72
        STA num_sl
        LDA #0
        STA hof_row
@name:  LDX hof_row
        LDA hof_initials,X
        JSR hof_letter
        JSR put_glyph
        INC hof_row
        LDA hof_row
        CMP #3
        BCC @name
        TEXT 128, 82, hof_cursor_blank
        LDA hof_index
        ASL A
        ASL A
        ASL A
        CLC
        ADC #128
        STA num_col
        LDA #82
        STA num_sl
        LDA #G_MINUS
        JSR put_glyph
        JSR show_screen
@wait:  JSR poll_key
        BEQ @joystick
        CMP #$1B
        BNE @return
        JMP @cancel
@return:
        CMP #$0D
        BEQ @save
        CMP #$08
        BEQ @left
        CMP #$15
        BEQ @right
        CMP #'A'
        BCC @wait
        CMP #'Z'+1
        BCS @wait
        LDX hof_index
        STA hof_initials,X
        JMP @right
@joystick:
        JSR get_stick
        CMP #ACT_UP
        BEQ @up
        CMP #ACT_DOWN
        BEQ @down
        CMP #ACT_LEFT
        BEQ @left
        CMP #ACT_RIGHT
        BEQ @right
        CMP #ACT_UNDO
        BEQ @save
        CMP #ACT_MENU
        BEQ @cancel
        JMP @wait
@up:    LDX hof_index
        INC hof_initials,X
        LDA hof_initials,X
        CMP #'Z'+1
        BCC @redraw
        LDA #'A'
        BNE @letter
@down:  LDX hof_index
        DEC hof_initials,X
        LDA hof_initials,X
        CMP #'A'
        BCS @redraw
        LDA #'Z'
@letter:
        STA hof_initials,X
@redraw:
        JMP @letters
@left:  LDA hof_index
        BEQ @redraw
        DEC hof_index
        JMP @letters
@right: LDA hof_index
        CMP #2
        BCS @redraw
        INC hof_index
        JMP @letters
@save:  JSR profile_name_unique
        BCC @accepted
        TEXT 96, 152, profile_name_used
        JMP @wait
@accepted:
        SEC
        RTS
@cancel:
        CLC
        RTS

.rodata
score_pow_lo:  .byte <10000000, <1000000, <100000, <10000, <1000, <100, <10, <1
score_pow_mid: .byte >10000000, >1000000, >100000, >10000, >1000, >100, >10, >1
score_pow_hi:  .byte (10000000>>16)&255, (1000000>>16)&255, 100000>>16, 0, 0, 0, 0, 0
score_pow_top: .byte 0, 0, 0, 0, 0, 0, 0, 0
hof_header:    .byte "HOF3GIS"
hof_load_cmd:  .byte "BLOAD MICROHOF,A$", 0
hof_save_cmd:  .byte "BSAVE MICROHOF,A$", 0
hof_letters:
.repeat 26, I
        .byte .ident(.sprintf("G_%c", 'A'+I))
.endrepeat
hof_table:
        .byte <hof_title,  >hof_title,   8,  8, 2
        .byte <hof_name,   >hof_name,   56, 38, STYLE_COMPACT
        .byte <str_score,  >str_score, 112, 38, STYLE_COMPACT
        .byte <hof_levels, >hof_levels,200, 38, STYLE_COMPACT
        .byte <hof_help,   >hof_help,   80,180, STYLE_COMPACT
        .word $FFFF
initials_table:
        .byte <hof_initials_title, >hof_initials_title, 12,40,1
        .byte <hof_initials_keys,  >hof_initials_keys,  56,104,STYLE_COMPACT
        .byte <hof_initials_save,  >hof_initials_save,  84,120,STYLE_COMPACT
        .byte <hof_initials_back,  >hof_initials_back,  88,136,STYLE_COMPACT
        .word $FFFF
hof_title:          GSTR "HALL OF FAME"
hof_title_blank:    GSTR "            "
hof_name:           GSTR "NAME"
hof_levels:         GSTR "LEVELS"
hof_help:           GSTR "RETURN/ESC BACK"
hof_blank3:         GSTR "---"
hof_blank6:         GSTR "------"
hof_cursor_blank:   GSTR "   "
hof_initials_title: GSTR "INITIALS"
hof_initials_keys:  GSTR "A-Z TYPE  STICK CHOOSE"
hof_initials_save:  GSTR "RETURN/B0 SAVE"
hof_initials_back:  GSTR "ESC/B1 CANCEL"

.code
; One-time HOF2 conversion: rebuild every named row from its own records.
; Names, options and active slot survive. No fabricated conversion of points.
migrate_rankings:
        LDA rankings_old
        BEQ @done
        LDA hof_buf+HOF_ACTIVE
        PHA
        LDA #0
        STA profile_sel
@slot:  LDA profile_sel
        JSR profile_offset
        LDA hof_buf+HOF_PROFILES,X
        BEQ @next
        LDY #0
@name:  LDA hof_buf+HOF_PROFILES,X
        STA hof_buf+4,Y
        INX
        INY
        CPY #3
        BCC @name
        LDA profile_sel
        STA hof_buf+HOF_ACTIVE
        JSR set_profile_save
        JSR load_save
        JSR calculate_score
        JSR update_hof
@next:  INC profile_sel
        LDA profile_sel
        CMP #HOF_COUNT
        BCC @slot
        PLA
        STA hof_buf+HOF_ACTIVE
        JSR profile_offset
        LDY #0
@restore:
        LDA hof_buf+HOF_PROFILES,X
        STA hof_buf+4,Y
        INX
        INY
        CPY #3
        BCC @restore
        JMP write_hof
@done:  RTS
