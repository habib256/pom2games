; Optional 134-byte position appended to SOK2 records. Old short saves work.
; P, version, collection, level, fingerprint, player row/col, moves/pushes,
; boxes left, CRC-8 checksum, 120 packed pairs of tiles. Undo starts fresh.
snapshot = save_buf + RECORD_LEN
.code
select_resume:
        LDA #0
        STA resume_pending
        LDA snapshot
        CMP #'P'
        BNE @done
        LDA snapshot+1
        CMP #1
        BNE @done
        LDX snapshot+2
        CPX #NUM_COLLS
        BCS @done
        LDA snapshot+3
        CMP coll_count,X
        BCS @done
        LDA snapshot+4
        CMP coll_fp_lo,X
        BNE @done
        LDA snapshot+5
        CMP coll_fp_hi,X
        BNE @done
        JSR position_checksum
        CMP snapshot+13
        BNE @done
        LDA snapshot+6
        CMP #NROWS
        BCS @done
        LDA snapshot+7
        CMP #NCOLS
        BCS @done
        LDA snapshot+12
        BEQ @done
        LDA snapshot+2
        STA cur_coll
        LDA snapshot+3
        STA cur_lvl
        INC resume_pending
@done:  RTS

position_checksum:
        LDA #0
        LDX #133
@byte:  CPX #13
        BEQ @next
        EOR snapshot,X
        LDY #8
@bit:   ASL A
        BCC @shift
        EOR #7
@shift: DEY
        BNE @bit
@next:  DEX
        CPX #$FF
        BNE @byte
        RTS

restore_position:
        LDA resume_pending
        BEQ @done
        LDA tutorial_on
        BNE @done
        LDA #0
        STA resume_pending
        LDA cur_coll
        CMP snapshot+2
        BNE @done
        LDA cur_lvl
        CMP snapshot+3
        BNE @done
        LDA snapshot+6
        STA player_row
        LDA snapshot+7
        STA player_col
        LDX #4
@stats: LDA snapshot+8,X
        STA moves_lo,X                  ; moves, pushes, boxes_left contiguous
        DEX
        BPL @stats
        LDX #0
        LDY #0
@grid:  LDA snapshot+14,Y
        AND #15
        STA STATE_GRID,X
        INX
        LDA snapshot+14,Y
        LSR A
        LSR A
        LSR A
        LSR A
        STA STATE_GRID,X
        INX
        INY
        CPY #120
        BCC @grid
        LDA #0
        STA position_dirty
@done:  RTS

idle_save:
        INC autosave_lo
        BNE @done
        INC autosave_hi
        LDA autosave_hi
        CMP #4                          ; about six seconds without input
        BCC @done
        LDA #0
        STA autosave_hi
        JMP save_position
@done:  RTS

save_position:
        LDA game_active
        BEQ @done
        LDA position_dirty
        BEQ @done
        LDA tutorial_on
        ORA demo_active
        BNE @done
        LDA #0
        STA position_dirty
        JSR disk_protected
        BCS @done
        LDA #'P'
        STA snapshot
        LDA #1
        STA snapshot+1
        LDX cur_coll
        STX snapshot+2
        LDA cur_lvl
        STA snapshot+3
        LDA coll_fp_lo,X
        STA snapshot+4
        LDA coll_fp_hi,X
        STA snapshot+5
        LDA player_row
        STA snapshot+6
        LDA player_col
        STA snapshot+7
        LDX #4
@stats: LDA moves_lo,X
        STA snapshot+8,X
        DEX
        BPL @stats
        LDX #0
        LDY #0
@grid:  LDA STATE_GRID+1,X
        ASL A
        ASL A
        ASL A
        ASL A
        ORA STATE_GRID,X
        STA snapshot+14,Y
        INX
        INX
        INY
        CPY #120
        BCC @grid
        JSR position_checksum
        STA snapshot+13
        LDA save_mask
        ORA #$80
        STA save_mask
        JSR write_save
        JMP draw_hud
@done:  RTS
