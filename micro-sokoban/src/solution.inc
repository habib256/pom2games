; Cheat-mode solution playback.
; MICROSOL: DOS header, 508 bytes of reader (this SOLCODE, run at $1004 over
; the decoded level pack), then 4-byte entries (payload offset, move count)
; and the moves packed four to a byte. Watching skips history and records;
; the moves are read above the reader (sol_buf), so the game's history stays.
.segment "WORKBSS"
sol_cache:      .res 20
sol_buf = pack_buf+512          ; index entry, then the packed moves, in the
                                ; pack buffer above the reader (1.5 KB; the
                                ; longest solution takes 264 bytes)

.segment "CODE"

play_solution:
        LDA #1
        STA demo_active
        STA watching
        JSR watch_level
        JSR draw_level
        JSR sol_bind
        JSR sol_load_reader
        JMP load_level_solution

sol_bind:
        LDA front_page
        EOR #$40
        STA io_base
        CLC
        ADC #16
        STA io_page
        LDA #<sol_cache
        STA hptr_lo
        LDA #>sol_cache
        STA hptr_hi
        LDY #0
        TYA
        STA (hptr_lo),Y
        LDA #<sol_name
        STA io_name
        LDA #>sol_name
        STA io_name+1
        JMP find_disk_file

; First two data sectors of MICROSOL -> pack_buf. The reader starts at $1004.
sol_load_reader:
        LDA #0
        STA temp
@sec:   LDA temp
        ASL A
        TAY
        INY
        LDA (hptr_lo),Y
        STA io_track
        INY
        LDA (hptr_lo),Y
        STA io_sector
        LDA #>pack_buf
        CLC
        ADC temp
        STA io_page
        LDA #1
        JSR io_rwts
        INC temp
        LDA temp
        CMP #2
        BNE @sec
        RTS

.segment "RODATA"
sol_name:       .byte "MICROSOL", 0

.segment "SOLCODE"

; Fills sol_buf and demo_src / demo_left from the current level, or a lesson.
load_level_solution:
        LDA tutorial_on
        BEQ @disk
        LDX tutorial_idx
        LDA tut_len,X
        STA demo_left_lo
        LDA #0
        STA demo_left_hi
        LDA tut_lo,X
        STA demo_src_lo
        LDA tut_hi,X
        STA demo_src_hi
        JMP play_loaded
@disk:  LDX cur_coll
        LDA coll_base_lo,X
        CLC
        ADC cur_lvl
        STA num_lo
        LDA coll_base_hi,X
        ADC #0
        STA num_hi
        ASL num_lo
        ROL num_hi
        ASL num_lo
        ROL num_hi
        INC num_hi
        INC num_hi                      ; file offset 512 + 4 * level
        LDA #<sol_buf
        STA ptr_lo
        LDA #>sol_buf
        STA ptr_hi
        LDA #4
        STA sol_left
        LDA #0
        STA sol_more
        JSR sol_read
        LDA sol_buf
        STA num_lo
        LDA sol_buf+1
        STA num_hi
        INC num_hi
        INC num_hi                      ; payload offset + 512
        LDA sol_buf+2
        STA demo_left_lo
        LDA sol_buf+3
        STA demo_left_hi
        LDA demo_left_lo
        CLC
        ADC #3
        STA sol_left
        LDA demo_left_hi
        ADC #0
        LSR A
        ROR sol_left
        LSR A
        ROR sol_left
        STA sol_more
        LDA #<sol_buf
        STA ptr_lo
        LDA #>sol_buf
        STA ptr_hi
        STA demo_src_hi
        LDA #<sol_buf
        STA demo_src_lo
        JSR sol_read
play_loaded:
        LDA #0
        STA demo_nbits
        LDA #DEMO_START
        JSR demo_pause
        BCS @stop
@mv:    LDA demo_left_lo
        ORA demo_left_hi
        BEQ @end
        JSR demo_next
        STA dir_code
        JSR execute_move
        LDA demo_left_lo
        BNE @d
        DEC demo_left_hi
@d:     DEC demo_left_lo
        LDA #DEMO_STEP
        JSR demo_pause
        BCC @mv
        BCS @stop
@end:   JSR play_fanfare
        LDA #DEMO_END
        JSR demo_pause
@stop:  LDA #$FF
        STA loaded_pack                 ; the reader replaced pack_buf
        LDA #0
        STA demo_active
        STA watching
        STA position_dirty
        RTS

sol_read:
@sector:
        LDA sol_left
        ORA sol_more
        BEQ @done
        LDA sol_ts_track
        STA io_track
        LDA sol_ts_sector
        STA io_sector
        LDA io_base
        CLC
        ADC #16
        STA io_page
        LDA #1
        JSR io_rwts
        LDA #0
        STA src_lo
        LDA io_page
        STA src_hi
        LDA num_hi
        ASL A
        CLC
        ADC #12
        TAY
        LDA (src_lo),Y
        STA io_track
        INY
        LDA (src_lo),Y
        STA io_sector
        LDA io_base
        STA io_page
        LDA #1
        JSR io_rwts
        LDA #0
        STA src_lo
        LDA io_page
        STA src_hi
        LDY num_lo
@byte:  LDA sol_left
        ORA sol_more
        BEQ @done
        LDA (src_lo),Y
        STY temp2
        LDY #0
        STA (ptr_lo),Y
        INC ptr_lo
        BNE @pi
        INC ptr_hi
@pi:    LDY temp2
        LDA sol_left
        BNE @dl
        DEC sol_more
@dl:    DEC sol_left
        INY
        INC num_lo
        BNE @byte
        INC num_hi
        JMP @sector
@done:  RTS

tut_len:        .byte 2, 2, 5, 5, 7
tut_lo:         .byte <tut0, <tut1, <tut2, <tut3, <tut4
tut_hi:         .byte >tut0, >tut1, >tut2, >tut3, >tut4
tut0:           .byte $0F
tut1:           .byte $03
tut2:           .byte $8F, $02
tut3:           .byte $F4, $00
tut4:           .byte $5F, $02
