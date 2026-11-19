; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.include "dhgr_transfer_row.inc"
.export dhgr_transfer
.import _dhgr_addr, _dhgr_aux, _dhgr_base, _dhgr_buffer, _dhgr_count
.import dhgr_rowlo, dhgr_rowhi, _dhgr_read_block_asm, _dhgr_write_block_asm
.importzp sp, tmp1, tmp2, tmp3, tmp4
.code
; Internal entry: A=stride, X=$80 for read or 0 for write.
; Caller frame: data low/high, height, width, y, interleaved byte x.
; After validation, width becomes stride and x becomes column | read flag.
; Kernels preserve the shared parameter globals; scratch registers are volatile.
dhgr_transfer:
        sta tmp1
        stx tmp2
        ldy #5
        lda (sp),y
        cmp #80
        bcc :+
        jmp @done
:       sta tmp3
        dey
        lda (sp),y
        cmp #192
        bcc :+
        jmp @done
:       sta tmp4
        dey
        lda (sp),y
        beq @reject
        cmp tmp1
        bcc @valid
        beq @valid
@reject:
        jmp @done
@valid: tax
        lda #80
        sec
        sbc tmp3
        cmp (sp),y
        bcc @count
        txa
@count: sta _dhgr_count
        ; A valid zero-height call still updates count, as the C entry did.
        dey
        lda #192
        sec
        sbc tmp4
        cmp (sp),y
        bcc @height
        lda (sp),y
@height:
        sta (sp),y
        bne :+
        jmp @done
:       iny
        lda tmp1
        sta (sp),y
        lda tmp3
        lsr
        sta tmp3
        dhgr_select_byte_bank
        lda tmp3
        ora tmp2
        ldy #5
        sta (sp),y
@row:
        ldy #4
        lda (sp),y
        tax
        iny
        lda (sp),y
        and #$3F
        dhgr_set_row_address
        ldy #0
        dhgr_load_buffer_pointer _dhgr_buffer
        ldy #5
        lda (sp),y
        bmi @read
        jsr _dhgr_write_block_asm
        jmp @advance
@read: jsr _dhgr_read_block_asm
@advance:
        dhgr_next_transfer_row 2, 4, @done
        ldy #3
        lda (sp),y
        ldy #0
        clc
        adc (sp),y
        sta (sp),y
        iny
        lda (sp),y
        adc #0
        sta (sp),y
        jmp @row
@done:  dhgr_return_from_transfer 6
