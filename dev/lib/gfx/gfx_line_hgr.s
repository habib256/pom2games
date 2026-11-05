; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; gfx_line(x0,y0,x1,y1): A=y1, stack=x1lo,x1hi,y0,x0lo,x0hi.
; Axis spans sort/clip; diagonals delegate endpoint rejection to hgr_line.
; Reuse the caller's frame; all three destinations consume their arguments.
.export _gfx_line
.import _gfx_hline, _gfx_vline, _hgr_line
.importzp sp, tmp1
.code
_gfx_line:
        sta tmp1
        ldy #2
        cmp (sp),y
        beq horizontal
        ldy #0
        lda (sp),y
        ldy #3
        cmp (sp),y
        bne diagonal
        ldy #1
        lda (sp),y
        ldy #4
        cmp (sp),y
        beq vertical
diagonal:
        lda tmp1
        jmp _hgr_line
horizontal:
        ; Replace y0 with x1hi and move x1lo up one slot, then drop a byte.
        ldy #1
        lda (sp),y
        iny
        sta (sp),y
        ldy #0
        lda (sp),y
        iny
        sta (sp),y
        inc sp
        bne :+
        inc sp+1
:       lda tmp1
        jmp _gfx_hline
vertical:
        ; Discard x1: y0,x0lo,x0hi already match the vertical signature.
        clc
        lda sp
        adc #2
        sta sp
        bcc :+
        inc sp+1
:       lda tmp1
        jmp _gfx_vline
