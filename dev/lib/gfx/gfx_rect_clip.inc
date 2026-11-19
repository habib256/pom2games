; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Input: A=y1, cc65 stack=x1lo,x1hi,y0,x0lo,x0hi.
; Output: inclusive left/right columns, top scanline and visible row count.
; For widths below 256, only the low byte of right is returned.
; Empty rectangles branch to the caller's stack cleanup.
.include "../hgrc/hgr_clip_axes.inc"

.macro gfx_clip_rect width, left, right, top, rows, reject
        sta rows          ; temporary y maximum
        ldy #2
        lda (sp),y
        hgr_clip_y top, rows, reject
        ldy #0
        lda (sp),y
        sta right
        iny
        lda (sp),y
        sta right+1
        ldy #3
        lda (sp),y
        sta left
        iny
        lda (sp),y
        sta left+1
        hgr_clip_x width, left, right, reject
.endmacro
