; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Full-word corner sorting/clipping, then the existing four-byte color-fill ABI.
; A=y1, stack=x1lo,x1hi,y0,x0lo,x0hi. One byte is discarded after
; validation; the color filler consumes the remaining four-byte frame.
.export _gfx_filled_rect
.import _dhgr_fill_rect, _dhgr_dot_color
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
        bne rejected
        lda ptr1
        cmp #140
        bcs rejected
        lda ptr2+1
        bne clip
        lda ptr2
        cmp #140
        bcc right_ready
clip:
        lda #139
        sta ptr2
right_ready:
        sec
        lda ptr2
        sbc ptr1
        adc #0                  ; inclusive width, at most 140
        ldy #2
        sta (sp),y
        dey
        lda tmp2
        sta (sp),y
        ldy #3
        lda tmp1
        sta (sp),y
        iny
        lda ptr1
        sta (sp),y
        inc sp
        bne :+
        inc sp+1
:       lda _dhgr_dot_color
        jmp _dhgr_fill_rect
