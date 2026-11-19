; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Full-word corner sorting/clipping, then the existing six-byte bit-fill ABI.
; A=y1, stack=x1lo,x1hi,y0,x0lo,x0hi. One additional byte is reserved only
; after validation; the bit filler consumes the whole reused frame.
.include "gfx_rect_clip.inc"
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
        gfx_clip_rect 560, ptr1, ptr2, tmp1, tmp2, rejected
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
