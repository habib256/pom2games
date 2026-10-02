; DOS-compatible sector I/O. Discover catalog/T/S chains by filename once,
; cache only metadata, and keep every binary header and allocated sector intact.
; Data are staged on the hidden HGR page; the displayed screen is untouched.
IO_FILES = NUM_PACKS+11
.segment "BSS"
io_cache: .res IO_FILES*20
dos_zp_prog: .res DOS_ZP_LEN
.segment "WORKBSS"
hof_disk_copy: .res HOF_LEN
io_id: .res 1
io_command: .res 1
io_dest: .res 2
io_limit: .res 2
io_name: .res 2
io_base: .res 1
io_track: .res 1
io_sector: .res 1
io_page: .res 1
io_count: .res 1
io_entry: .res 1
io_index: .res 1
io_mask: .res 1
save_mask: .res 1
io_error: .res 1
io_iob: .res 2
.code
init_disk_cache:
        LDX #0
        LDA #0
@clear: STA io_cache,X
        STA io_cache+IO_FILES*20-256,X
        INX
        BNE @clear
        LDA #$FF
        STA save_mask
        RTS

; File selector and destination are supplied by the small wrappers below.
fast_read:
        LDA #1
        BNE fast_file
fast_write:
        LDA #2
fast_file:
        STA io_command
        LDA front_page
        EOR #$40
        STA io_base
        CLC
        ADC #16
        STA io_page                     ; metadata scratch, far from file data
        LDX io_id
        LDA cache_lo,X
        STA hptr_lo
        LDA cache_hi,X
        STA hptr_hi
        LDY #0
        LDA (hptr_lo),Y
        BNE @cached
        JSR find_disk_file
@cached:
        STA io_count
        LDA io_command
        CMP #2
        BNE @data
        ; Never extend a file beyond its allocated T/S chain.
        LDA io_limit
        CLC
        ADC #4
        TAY
        LDA io_limit+1
        ADC #0
        CPY #0
        BEQ @pages
        CLC
        ADC #1
@pages: CMP io_count
        BCC @capacity
        BEQ @capacity
        JMP disk_error
@capacity:
        ; Stage a DOS binary header plus the current payload.
        LDA #0
        STA ptr_lo
        LDA io_base
        STA ptr_hi
        LDY #0
        LDA io_dest
        STA (ptr_lo),Y
        INY
        LDA io_dest+1
        STA (ptr_lo),Y
        INY
        LDA io_limit
        STA (ptr_lo),Y
        INY
        LDA io_limit+1
        STA (ptr_lo),Y
        LDA io_dest
        STA src_lo
        LDA io_dest+1
        STA src_hi
        LDA #4
        STA ptr_lo
        JSR io_copy
@data:  LDA io_base
        STA io_page
        LDA #0
        STA io_index
@sector:
        LDA io_command
        CMP #1
        BEQ @transfer
        LDA io_index
        CMP #8
        BCS @transfer
        TAX
        LDA io_mask
        AND sector_bits,X
        BEQ @skip
@transfer:
        LDA io_index
        ASL A
        TAY
        INY
        LDA (hptr_lo),Y
        STA io_track
        INY
        LDA (hptr_lo),Y
        STA io_sector
        LDA io_command
        JSR io_rwts
@skip:  INC io_page
        INC io_index
        LDA io_index
        CMP io_count
        BCC @sector
        LDA io_command
        CMP #2
        BEQ @done
        ; Validate the binary length before copying into game memory.
        LDA #0
        STA src_lo
        LDA io_base
        STA src_hi
        LDY #3
        LDA (src_lo),Y
        CMP io_limit+1
        BCC @length
        BNE disk_error
        DEY
        LDA (src_lo),Y
        CMP io_limit
        BCC @length
        BNE disk_error
@length:
        LDY #2
        LDA (src_lo),Y
        STA io_limit
        INY
        LDA (src_lo),Y
        STA io_limit+1
        LDA #4
        STA src_lo
        LDA io_dest
        STA ptr_lo
        LDA io_dest+1
        STA ptr_hi
        JSR io_copy
@done:  RTS

; Copy io_limit bytes, preserving that length and the sector cache pointer.
io_copy:
        LDX io_limit+1
        LDY #0
        CPX #0
        BEQ @rest
@page:  LDA (src_lo),Y
        STA (ptr_lo),Y
        INY
        BNE @page
        INC src_hi
        INC ptr_hi
        DEX
        BNE @page
@rest:  CPY io_limit
        BEQ @done
        LDA (src_lo),Y
        STA (ptr_lo),Y
        INY
        BNE @rest
@done:  RTS

disk_error:
        LDA #<str_disk_error
        LDY #>str_disk_error
        JSR show_status
        JSR wait_any
        JMP apple2_exit

find_disk_file:
        LDA #17
        STA io_track
        LDA #15
        STA io_sector
@catalog:
        LDA #1
        JSR io_rwts
        LDA #0
        STA src_lo
        LDA io_page
        STA src_hi
        LDA #11
        STA io_entry
@entry: LDY io_entry
        LDA (src_lo),Y
        BEQ @next
        CMP #$FF
        BEQ @next
        LDA io_name
        STA ptr_lo
        LDA io_name+1
        STA ptr_hi
        LDA io_entry
        CLC
        ADC #3
        STA temp2
        LDX #0
@name:  TXA
        TAY
        LDA (ptr_lo),Y
        BEQ @endname
        CMP #','
        BEQ @endname
        STA temp
        LDY temp2
        LDA (src_lo),Y
        AND #$7F
        CMP temp
        BNE @next
        INC temp2
        INX
        BNE @name
@endname:
        LDY temp2
        LDA (src_lo),Y
        CMP #$A0
        BEQ @found
@next:  LDA io_entry
        CLC
        ADC #35
        STA io_entry
        BCC @entry
        LDY #1
        LDA (src_lo),Y
        STA io_track
        INY
        LDA (src_lo),Y
        STA io_sector
        LDA io_track
        BNE @catalog
        JMP disk_error
@found: LDY io_entry
        LDA (src_lo),Y
        STA io_track
        INY
        LDA (src_lo),Y
        STA io_sector
        LDA #1
        JSR io_rwts
        ; All our files fit one T/S list, at most nine data sectors.
        LDX #0
@pair:  TXA
        CLC
        ADC #12
        TAY
        LDA (src_lo),Y
        BEQ @end
        STA temp
        INY
        LDA (src_lo),Y
        PHA
        TXA
        TAY
        INY
        LDA temp
        STA (hptr_lo),Y
        INY
        PLA
        STA (hptr_lo),Y
        INX
        INX
        CPX #18
        BCC @pair
@end:   TXA
        LSR A
        LDY #0
        STA (hptr_lo),Y
        ORA #0
        BNE @done
        JMP disk_error
@done:  RTS

; Use DOS's own IOB/DCT so drive/head/motor state remains coherent with DOS.
; RWTS borrows zero page: preserve the game's complete declared range.
io_rwts:
        PHA
        LDX #DOS_ZP_LEN-1
@save:  LDA DOS_ZP_START,X
        STA dos_zp_prog,X
        DEX
        BPL @save
        JSR $03E3
        STY $80
        STA $81
        LDY #2
        LDA #1
        STA ($80),Y                     ; drive 1
        INY
        LDA #0
        STA ($80),Y                     ; accept mounted volume
        INY
        LDA io_track
        STA ($80),Y
        INY
        LDA io_sector
        STA ($80),Y
        LDY #8
        LDA #0
        STA ($80),Y
        INY
        LDA io_page
        STA ($80),Y
        LDY #12
        PLA
        STA ($80),Y
        JSR $03E3
        JSR $03D9
        PHP
        LDX #DOS_ZP_LEN-1
@restore:
        LDA dos_zp_prog,X
        STA DOS_ZP_START,X
        DEX
        BPL @restore
        PLP
        BCC @done
        JMP disk_error
@done:  RTS

profile_file:
        LDA hof_buf+HOF_ACTIVE
        CLC
        ADC #NUM_PACKS
        STA io_id
        LDA #<save_buf
        STA io_dest
        LDA #>save_buf
        STA io_dest+1
        LDA #<SAVE_LEN
        STA io_limit
        LDA #>SAVE_LEN
        STA io_limit+1
        LDA #<(save_load_str+6)
        STA io_name
        LDA #>(save_load_str+6)
        STA io_name+1
        RTS
hof_file:
        LDA #NUM_PACKS+10
        STA io_id
        LDA #<hof_buf
        STA io_dest
        LDA #>hof_buf
        STA io_dest+1
        LDA #HOF_LEN
        STA io_limit
        LDA #0
        STA io_limit+1
        LDA #<(hof_load_cmd+6)
        STA io_name
        LDA #>(hof_load_cmd+6)
        STA io_name+1
        LDA #$FF
        STA io_mask
        RTS
.rodata
cache_lo:
.repeat IO_FILES, I
        .byte <(io_cache+20*I)
.endrepeat
cache_hi:
.repeat IO_FILES, I
        .byte >(io_cache+20*I)
.endrepeat
sector_bits: .byte 1,2,4,8,16,32,64,128
str_disk_error: GSTR "IO ERR"

.code
disk_protected:
        LDA $C0E9
        LDA $C0ED
        LDA $C0EE
        ASL A
        LDA $C0E8
        RTS

remember_hof:
        LDX #HOF_LEN-1
@copy:  LDA hof_buf,X
        STA hof_disk_copy,X
        DEX
        BPL @copy
        RTS
