; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; gfx_line(x0,y0,x1,y1): A=y1, stack=x1lo,x1hi,y0,x0lo,x0hi.
; Axis spans sort/clip; diagonals delegate endpoint rejection to hgr_line.
; Reuse the caller's frame; all three destinations consume their arguments.
.export _gfx_line
.import _gfx_hline, _gfx_vline, _hgr_line
.importzp sp, tmp1
.include "gfx_line_axes.inc"
.code
_gfx_line:
        gfx_line_classify tmp1, horizontal, vertical, diagonal
diagonal:
        lda tmp1
        jmp _hgr_line
        gfx_line_spans tmp1, horizontal, vertical
