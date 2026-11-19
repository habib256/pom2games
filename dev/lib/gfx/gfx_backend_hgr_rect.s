; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; gfx_filled_rect(x0,y0,x1,y1): A=y1, stack=x1lo,x1hi,y0,x0lo,x0hi.
; Sort full-width corners before clipping. Inclusive dimensions are computed
; only after clipping; no overflow at x1=$ffff or y1=$ff. Rejected rectangles
; never initialize tables. The existing span kernel owns all rendering.
.include "gfx_rect_clip.inc"
.export _gfx_filled_rect
.import _hgr_fill_span
.importzp sp, _hgr_r_x, _hgr_r_xr, _hgr_r_y0, _hgr_r_rows
.code
_gfx_filled_rect:
        gfx_clip_rect 280, _hgr_r_x, _hgr_r_xr, _hgr_r_y0, _hgr_r_rows, done
        jsr _hgr_fill_span
done:
        clc
        lda sp
        adc #5
        sta sp
        bcc :+
        inc sp+1
:       rts
