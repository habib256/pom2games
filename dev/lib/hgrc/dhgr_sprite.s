; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.include "dhgr_transfer_row.inc"
.export _dhgr_sprite
.import pushax, _dhgr_cellbyte, _dhgr_cellphase, dhgr_rowlo, dhgr_rowhi
.import _dhgr_addr, _dhgr_aux, _dhgr_base, _dhgr_buffer, _dhgr_sprite_mask, _dhgr_count
.import _dhgr_sprite_asm
.importzp sp, ptr1, tmp1, tmp2, tmp3, tmp4
.code
; fastcall AX=mask; caller frame: data low/high, stride, height, width, y, x.
; Push only the mask: [mask(2), data(2), stride, height, width, y, x].
; The final x slot becomes the byte column. No local frame or new state.
_dhgr_sprite:
        jsr pushax
        ldy #8
        lda (sp),y
        cmp #140
        bcc :+
        jmp @done
:       tax
        dey
        lda (sp),y
        cmp #192
        bcc :+
        jmp @done
:       dey
        lda (sp),y
        bne :+
        jmp @done
:       dey
        lda (sp),y
        bne :+
        jmp @done
:       lda _dhgr_cellphase,x
        sta tmp1
        lda _dhgr_cellbyte,x
        sta tmp2
        ldy #6
        lda (sp),y
        cmp #140
        bcc @narrow
        sbc #140
        tax
        lda #80
        bne @base
@narrow:
        tax
        lda #0
@base: clc
        adc _dhgr_cellbyte,x
        sta tmp3
        lda _dhgr_cellphase,x
        clc
        adc tmp1
        beq @extent
        cmp #8
        lda tmp3
        adc #1                  ; one extra byte, or two when phase sum > 7
        sta tmp3
@extent:
        ldy #4
        lda tmp3
        cmp (sp),y
        bcc @valid
        beq @valid
        jmp @done
@valid:
        lda #80
        sec
        sbc tmp2
        cmp tmp3
        bcc @count
        lda tmp3
@count: sta _dhgr_count
        lda tmp2
        lsr
        ldy #8
        sta (sp),y
        dhgr_select_byte_bank
        ; Bank offsets use the original height, before bottom clipping.
        ldx tmp1
        beq @offset_done
        ldy #4
        lda (sp),y
        sta tmp4
        iny
        lda (sp),y
        sta tmp3
        lda #0
        ldy #8
        lsr tmp3
@multiply:
        bcc @no_add
        clc
        adc tmp4
@no_add:
        ror a
        ror tmp3
        dey
        bne @multiply
        sta ptr1+1
        sta tmp4
        lda tmp3
        sta ptr1
        dex
        beq @apply_offset
        ; Form phase * bank once, then adjust both pointers just once.
@phase:
        clc
        lda ptr1
        adc tmp3
        sta ptr1
        lda ptr1+1
        adc tmp4
        sta ptr1+1
        dex
        bne @phase
@apply_offset:
        ldy #0
@word: lda (sp),y
        clc
        adc ptr1
        sta (sp),y
        iny
        lda (sp),y
        adc ptr1+1
        sta (sp),y
        iny
        cpy #4
        bne @word
@offset_done:
        ldy #7
        lda (sp),y
        sta tmp4
        lda #192
        sec
        sbc tmp4
        ldy #5
        cmp (sp),y
        bcs @row
        sta (sp),y
@row:
        ldy #7
        lda (sp),y
        tax
        iny
        lda (sp),y
        dhgr_set_row_address
        ldy #0
        dhgr_load_buffer_pointer _dhgr_sprite_mask
        iny
        dhgr_load_buffer_pointer _dhgr_buffer
        jsr _dhgr_sprite_asm
        dhgr_next_transfer_row 5, 7, @done
        ldy #4
        lda (sp),y
        sta tmp1
        ldy #0
@next_pointer:
        lda (sp),y
        clc
        adc tmp1
        sta (sp),y
        iny
        lda (sp),y
        adc #0
        sta (sp),y
        iny
        cpy #4
        bne @next_pointer
        jmp @row
@done:  dhgr_return_from_transfer 9
