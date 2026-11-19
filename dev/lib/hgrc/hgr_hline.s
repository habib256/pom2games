; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_hline(x0,x1,y), cc65 fastcall: A=y, C stack=x1lo,x1hi,x0lo,x0hi.
; Sort full 16-bit endpoints, reject the minimum, clip the maximum to 279.
.include "hgr_clip_axes.inc"
.export _hgr_hline
.import _hgr_fill_span, incsp4
.importzp sp, _hgr_r_x, _hgr_r_xr, _hgr_r_y0, _hgr_r_rows
.code
rejected:
        jmp incsp4
_hgr_hline:
        cmp #192
        bcs rejected
        sta _hgr_r_y0
        ldy #0
        lda (sp),y
        sta _hgr_r_xr
        iny
        lda (sp),y
        sta _hgr_r_xr+1
        iny
        lda (sp),y
        sta _hgr_r_x
        iny
        lda (sp),y
        sta _hgr_r_x+1
        hgr_clip_x 280, _hgr_r_x, _hgr_r_xr, rejected
        lda #1
        sta _hgr_r_rows
        jsr _hgr_fill_span
        jmp incsp4
