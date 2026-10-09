; Five scores, initials, difficulty and sector progression in a DOS binary.
record_data = $1B00             ; outside the $1800-$1A43 sector pack
.export record_data, save_status
.bss
record_rank: .res 1
record_offset: .res 1
record_digit: .res 1
save_status: .res 1             ; 0 none, 1 saved, 2 write protected
record_initials: .res 4
.code
records_load:
        jsr dos_cmd_new
        lda #<records_load_command
        ldy #>records_load_command
        jsr dos_cmd_add
        jsr dos_cmd_run
        lda record_data
        cmp #'A'
        bne @empty
        lda record_data+1
        cmp #'B'
        bne @empty
        lda record_data+2
        cmp #'R'
        bne @empty
        lda record_data+3
        cmp #1
        bne @empty
        lda record_data+4
        cmp #60
        bcs @empty
        sta furthest
        ldx #0
@best:  lda record_data+5,x
        cmp #'0'
        bcc @empty
        cmp #':'
        bcs @empty
        sta best_score,x
        inx
        cpx #6
        bne @best
        rts
@empty: lda #'A'
        sta record_data
        lda #'B'
        sta record_data+1
        lda #'R'
        sta record_data+2
        lda #1
        sta record_data+3
        lda #0
        sta record_data+4
        sta furthest
        ldx #0
@row:   lda #'0'
        ldy #6
@zero:  sta record_data+5,x
        inx
        dey
        bne @zero
        lda #'A'
        ldy #3
@name:  sta record_data+5,x
        inx
        dey
        bne @name
        lda #1
        sta record_data+5,x
        inx
        cpx #50
        bcc @row
        rts
records_submit:
        lda demo
        jne records_done
        lda furthest
        sta record_data+4
        lda #0
        sta record_rank
        sta record_offset
@rank:  ldx #0
        ldy record_offset
@compare:
        lda score,x
        cmp record_data+5,y
        bcc @next
        bne @insert
        iny
        inx
        cpx #6
        bcc @compare
@next:  inc record_rank
        lda record_rank
        cmp #5
        jcs records_save
        lda record_offset
        clc
        adc #10
        sta record_offset
        jmp @rank
@insert:
        jsr clear_pages
        text record_new, 9, 40
        text record_prompt, 4, 72
        text record_accept, 4, 88
        jsr show_graphics
        lda #'A'
        sta record_initials
        sta record_initials+1
        sta record_initials+2
        lda #0
        sta record_initials+3
        sta record_digit
@key:   jsr wait_key
        cmp #KC_SPACE
        beq @commit
        cmp #$0D
        beq @commit
        cmp #KC_ESC
        beq @commit
        cmp #'A'
        bcc @key
        cmp #'Z'+1
        bcs @key
        ldx record_digit
        sta record_initials,x
        text record_initials, 18, 112
        inc record_digit
        lda record_digit
        cmp #3
        bcc @key
@commit:
        ldx #49
@shift: txa
        cmp #10
        bcc @copy
        sec
        sbc #10
        cmp record_offset
        bcc @copy
        tay
        lda record_data+5,y
        sta record_data+5,x
        dex
        bpl @shift
@copy:  ldx #0
        ldy record_offset
@score: lda score,x
        sta record_data+5,y
        iny
        inx
        cpx #6
        bcc @score
        ldx #0
@name:  lda record_initials,x
        sta record_data+5,y
        iny
        inx
        cpx #3
        bcc @name
        lda difficulty
        sta record_data+5,y
records_save:
        jsr disk_protected
        bcs @protected
        jsr dos_cmd_new
        lda #<records_save_command
        ldy #>records_save_command
        jsr dos_cmd_add
        jsr dos_cmd_run
        lda #1
        sta save_status
        rts
@protected:
        lda #2
        sta save_status
records_done: rts
records_show:
        jsr clear_pages
        text record_title, 13, 24
        lda #0
        sta record_offset
        sta record_rank
@row:   lda record_rank
        asl
        asl
        asl
        asl
        clc
        adc #56
        sta ht_sl
        lda #9
        sta ht_col
        ldx #0
@letter:
        cpx #6
        bne :+
        lda #18
        sta ht_col
:       txa
        clc
        adc record_offset
        tay
        lda record_data+5,y
        jsr hgr_putc8
        inx
        cpx #9
        bcc @letter
        lda record_offset
        clc
        adc #10
        sta record_offset
        inc record_rank
        lda record_rank
        cmp #5
        bcc @row
        text help_back, 6, 168
        jsr show_graphics
        jmp wait_key
.rodata
records_load_command: .asciiz "BLOAD RECORDS,A$1B00"
records_save_command: .asciiz "BSAVE RECORDS,A$1B00,L$0037"
record_new: .asciiz "A NEW HIGH SCORE!"
record_prompt: .asciiz "TYPE THREE LETTERS FOR YOUR NAME"
record_accept: .asciiz "ENTER / SPACE ACCEPTS AAA"
record_title: .asciiz "HIGH SCORES"
save_failed: .asciiz "DISK WRITE PROTECTED - NOT SAVED"
