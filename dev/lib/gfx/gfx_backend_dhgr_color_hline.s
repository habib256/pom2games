; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Insert y0 between x1 and x0; y1 remains the fastcall argument.
.export _gfx_hline
.import _gfx_filled_rect
.importzp sp
.code
_gfx_hline:
        tax
        lda sp
        bne :+
        dec sp+1
:       dec sp
        ldy #1
        lda (sp),y
        dey
        sta (sp),y
        ldy #2
        lda (sp),y
        dey
        sta (sp),y
        iny
        txa
        sta (sp),y
        jmp _gfx_filled_rect
