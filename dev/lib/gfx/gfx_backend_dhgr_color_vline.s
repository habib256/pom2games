; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Duplicate x0 into the two newly reserved x1 slots; y0 stays in place.
.export _gfx_vline
.import _gfx_filled_rect
.importzp sp
.code
_gfx_vline:
        tax
        lda sp
        sec
        sbc #2
        sta sp
        bcs :+
        dec sp+1
:       ldy #3
        lda (sp),y
        ldy #0
        sta (sp),y
        ldy #4
        lda (sp),y
        ldy #1
        sta (sp),y
        txa
        jmp _gfx_filled_rect
