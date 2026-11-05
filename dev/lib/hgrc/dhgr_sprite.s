; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
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
        lda #0
        rol
        eor #1
        sta _dhgr_aux
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
        clc
        adc dhgr_rowlo,x
        sta _dhgr_addr
        lda dhgr_rowhi,x
        ora _dhgr_base
        sta _dhgr_addr+1
        ldy #0
        lda (sp),y
        sta _dhgr_sprite_mask
        iny
        lda (sp),y
        sta _dhgr_sprite_mask+1
        iny
        lda (sp),y
        sta _dhgr_buffer
        iny
        lda (sp),y
        sta _dhgr_buffer+1
        jsr _dhgr_sprite_asm
        ldy #5
        lda (sp),y
        sec
        sbc #1
        sta (sp),y
        beq @done
        ldy #7
        lda (sp),y
        clc
        adc #1
        sta (sp),y
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
@done: lda sp
        clc
        adc #9
        sta sp
        bcc :+
        inc sp+1
:       rts
