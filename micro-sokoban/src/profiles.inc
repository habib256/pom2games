; Ten stable profile slots, independently saved as MICROSAVE / MICROSAV1..9.
.code
profile_offset:
        STA temp
        ASL A
        CLC
        ADC temp
        TAX
        RTS

validate_profiles:
        LDA hof_buf+HOF_ACTIVE
        CMP #HOF_COUNT
        BCS @bad
        JSR profile_offset
        LDA hof_buf+HOF_PROFILES,X
        BEQ @bad
        LDX #0
@slot:  LDA hof_buf+HOF_PROFILES,X
        BEQ @next
        LDY #3
@letter:
        LDA hof_buf+HOF_PROFILES,X
        CMP #'A'
        BCC @bad
        CMP #'Z'+1
        BCS @bad
        INX
        DEY
        BNE @letter
        BEQ @check
@next: INX
        INX
        INX
@check: CPX #30
        BCC @slot
        RTS
@bad:   JMP reset_hof

set_profile_save:
        LDA hof_buf+HOF_ACTIVE
        BEQ @default
        CLC
        ADC #'0'
        BNE @store
@default:
        LDA #'E'
@store: STA save_load_str+14
        STA save_save_str+14
        RTS

; An inset black panel separates white letters from the blue wall's phase
; bits. Twelve pixels of padding at each side prevent pink fringe artifacts.
draw_title_profile:
        LDX #178
@row:   LDA hgr_lo,X
        CLC
        ADC #12                         ; byte 12: pixel 84
        STA ptr_lo
        LDA hgr_hi,X
        ADC #0
        STA ptr_hi
        LDA #0
        LDY #15                         ; 16 bytes / 112 pixels
@clear: STA (ptr_lo),Y
        DEY
        BPL @clear
        INX
        CPX #190
        BCC @row
        LDA #180
draw_profile_name:
        STA num_sl
        LDA #96
        STA num_col
        LDA #<profile_label
        STA sptr_lo
        LDA #>profile_label
        STA sptr_hi
        JSR draw_str
        LDA #0
        STA hof_row
@name:  LDX hof_row
        LDA hof_buf+4,X
        JSR hof_letter
        JSR put_glyph
        INC hof_row
        LDA hof_row
        CMP #3
        BCC @name
        RTS

; C = 1 if the edited name belongs to another profile.
profile_name_unique:
        LDA profile_sel
        JSR profile_offset
        STX temp2
        LDX #0
@slot:  CPX temp2
        BEQ @next
        LDA hof_buf+HOF_PROFILES,X
        CMP hof_initials
        BNE @next
        LDA hof_buf+HOF_PROFILES+1,X
        CMP hof_initials+1
        BNE @next
        LDA hof_buf+HOF_PROFILES+2,X
        CMP hof_initials+2
        BEQ @duplicate
@next: INX
        INX
        INX
        CPX #30
        BCC @slot
        CLC
        RTS
@duplicate:
        SEC
        RTS

run_profiles:
        LDA hof_buf+HOF_ACTIVE
        STA profile_sel
@paint: JSR begin_screen
        LDA #<profiles_table
        STA tbl_lo
        LDA #>profiles_table
        STA tbl_hi
        JSR draw_from_table
        LDA #52
        STA num_sl
        LDA #0
        STA hof_row
@row:
        LDA #80
        STA num_col
        LDA #G_SPACE
        LDX hof_row
        CPX profile_sel
        BNE @mark
        LDA #G_PLUS
@mark:  JSR put_glyph
        LDA #112
        STA num_col
        LDA hof_row
        JSR profile_offset
        LDA hof_buf+HOF_PROFILES,X
        BEQ @empty
        STX hof_offset
        LDA #0
        STA hof_index
@name:  LDX hof_offset
        LDA hof_buf+HOF_PROFILES,X
        JSR hof_letter
        JSR put_glyph
        INC hof_offset
        INC hof_index
        LDA hof_index
        CMP #3
        BCC @name
        JMP @next
@empty: LDA #<hof_blank3
        STA sptr_lo
        LDA #>hof_blank3
        STA sptr_hi
        JSR draw_str
@next:  LDA hof_row
        CMP hof_buf+HOF_ACTIVE
        BNE @advance
        LDA #152
        STA num_col
        LDA #G_MINUS                   ; underline/dash identifies active profile
        JSR put_glyph
@advance:
        LDA num_sl
        CLC
        ADC #11
        STA num_sl
        INC hof_row
        LDA hof_row
        CMP #HOF_COUNT
        BCC @row
        JSR show_screen
@wait:  JSR get_input
        CMP #ACT_MENU
        BNE @up
        CLC
        RTS
@up:    CMP #ACT_UP
        BNE @down
        DEC profile_sel
        BPL @redraw
        LDA #HOF_COUNT-1
        STA profile_sel
@redraw:
        JMP @paint
@down:  CMP #ACT_DOWN
        BNE @new
        INC profile_sel
        LDA profile_sel
        CMP #HOF_COUNT
        BCC @redraw
        LDA #0
        STA profile_sel
        BEQ @redraw
@new:   CMP #ACT_NEXT
        BNE @rename
        LDA #0
        STA profile_sel
@free:  LDA profile_sel
        JSR profile_offset
        LDA hof_buf+HOF_PROFILES,X
        BEQ @edit
        INC profile_sel
        LDA profile_sel
        CMP #HOF_COUNT
        BCC @free
        LDA hof_buf+HOF_ACTIVE
        STA profile_sel
        JMP @paint
@rename:
        CMP #ACT_RESET
        BEQ @edit
        CMP #ACT_SELECT
        BEQ @select
        CMP #ACT_UNDO
        BNE @wait
        LDA in_src
        BEQ @wait
@select:
        LDA profile_sel
        JSR profile_offset
        LDA hof_buf+HOF_PROFILES,X
        BNE activate_profile
@edit:  JSR edit_initials
        BCC @redraw
        ; Rename its ranked row before replacing the registry initials.
        LDA profile_sel
        JSR profile_offset
        STX temp2
        LDX #HOF_HDR
@find:  LDY temp2
        LDA hof_buf+HOF_PROFILES,Y
        BEQ @commit
        CMP hof_buf,X
        BNE @find_next
        LDA hof_buf+HOF_PROFILES+1,Y
        CMP hof_buf+1,X
        BNE @find_next
        LDA hof_buf+HOF_PROFILES+2,Y
        CMP hof_buf+2,X
        BEQ @rename_row
@find_next:
        TXA
        CLC
        ADC #HOF_ENTRY
        TAX
        CPX #HOF_END
        BCC @find
        BCS @commit
@rename_row:
        LDY #0
@rename_byte:
        LDA hof_initials,Y
        STA hof_buf,X
        INX
        INY
        CPY #3
        BCC @rename_byte
@commit:
        LDX temp2
        LDY #0
@copy:  LDA hof_initials,Y
        STA hof_buf+HOF_PROFILES,X
        INX
        INY
        CPY #3
        BCC @copy

activate_profile:
        LDA profile_sel
        CMP hof_buf+HOF_ACTIVE
        PHP
        LDA profile_sel
        STA hof_buf+HOF_ACTIVE
        JSR profile_offset
        LDY #0
@copy:  LDA hof_buf+HOF_PROFILES,X
        STA hof_buf+4,Y
        INX
        INY
        CPY #3
        BCC @copy
        PLP
        BNE @switch
        JSR update_hof
        JSR write_hof
        CLC
        RTS
@switch:
        LDA #0
        STA tutorial_on
        STA tutorial_idx
        JSR set_profile_save
        JSR load_save
        JSR restore_tutorial
        JSR calculate_score
        JSR update_hof
        JSR write_hof
        JSR first_unsolved
        JSR select_resume
        JSR find_level
        SEC
        RTS

restore_tutorial:
        LDA hof_buf+HOF_TUTORIAL
        AND #$FE
        BIT save_buf+4
        BPL @store
        ORA #1
@store: STA hof_buf+HOF_TUTORIAL
        RTS

.rodata
profiles_table:
        .byte <menu_profiles,>menu_profiles,12,8,2
        .byte <profiles_hint,>profiles_hint,40,30,STYLE_COMPACT
        .byte <profiles_edit,>profiles_edit,68,166,STYLE_COMPACT
        .byte <profiles_back,>profiles_back,84,180,STYLE_COMPACT
        .word $FFFF
profile_label: GSTR "PROFILE "
profiles_hint: GSTR "STICK/I/K  RETURN/B0 SELECT"
profiles_edit: GSTR "N NEW    R RENAME"
profiles_back: GSTR "ESC/B1 BACK"
profile_name_used: GSTR "NAME IN USE"
