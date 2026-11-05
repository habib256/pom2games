; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Full-word corner sorting/clipping, then the existing six-byte bit-fill ABI.
; A=y1, stack=x1lo,x1hi,y0,x0lo,x0hi. One additional byte is reserved only
; after validation; the bit filler consumes the whole reused frame.
.export _gfx_filled_rect
.import _dhgr_fill_bits, _gfx_dhgr_mono_pen
.importzp sp, ptr1, ptr2, tmp1, tmp2
.code
rejected:
        clc
        lda sp
        adc #5
        sta sp
        bcc :+
        inc sp+1
:       rts
_gfx_filled_rect:
        sta tmp2
        ldy #2
        lda (sp),y
        cmp tmp2
        bcc y_ordered
        beq y_ordered
        tax
        lda tmp2
        stx tmp2
y_ordered:
        cmp #192
        bcs rejected
        sta tmp1
        lda tmp2
        cmp #192
        bcc y_clipped
        lda #191
y_clipped:
        sec
        sbc tmp1
        adc #0
        sta tmp2
        ldy #0
        lda (sp),y
        sta ptr2
        iny
        lda (sp),y
        sta ptr2+1
        ldy #3
        lda (sp),y
        sta ptr1
        iny
        lda (sp),y
        sta ptr1+1
        cmp ptr2+1
        bcc x_ordered
        bne swap
        lda ptr1
        cmp ptr2
        bcc x_ordered
        beq x_ordered
swap:
        ldx ptr1
        lda ptr2
        sta ptr1
        stx ptr2
        ldx ptr1+1
        lda ptr2+1
        sta ptr1+1
        stx ptr2+1
x_ordered:
        lda ptr1+1
        cmp #3
        bcs rejected
        cmp #2
        bne left_ready
        lda ptr1
        cmp #48
        bcs rejected
left_ready:
        lda ptr2+1
        cmp #2
        bcc right_ready
        bne clip
        lda ptr2
        cmp #48
        bcc right_ready
clip:
        lda #<559
        sta ptr2
        lda #>559
        sta ptr2+1
right_ready:
        sec
        lda ptr2
        sbc ptr1
        sta ptr2
        lda ptr2+1
        sbc ptr1+1
        sta ptr2+1
        inc ptr2
        bne :+
        inc ptr2+1
:       lda sp
        bne :+
        dec sp+1
:       dec sp
        ldy #0
        lda tmp2
        sta (sp),y
        iny
        lda ptr2
        sta (sp),y
        iny
        lda ptr2+1
        sta (sp),y
        iny
        lda tmp1
        sta (sp),y
        iny
        lda ptr1
        sta (sp),y
        iny
        lda ptr1+1
        sta (sp),y
        lda _gfx_dhgr_mono_pen
        jmp _dhgr_fill_bits
