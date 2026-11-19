; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Full-word corner sorting/clipping, then the existing four-byte color-fill ABI.
; A=y1, stack=x1lo,x1hi,y0,x0lo,x0hi. One byte is discarded after
; validation; the color filler consumes the remaining four-byte frame.
.include "gfx_rect_clip.inc"
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
        gfx_clip_rect 140, ptr1, ptr2, tmp1, tmp2, rejected
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
