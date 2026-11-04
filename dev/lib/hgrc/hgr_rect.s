; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_fill_rect(y0, rows, col0, ncols, value), cc65 fastcall.
; Build rows even for an empty/outside call, as the C entry always did.
.export _hgr_fill_rect
.import _hgr_build_rows, _hgr_fill_rect_asm, incsp4
.importzp sp, _hgr_f_y0, _hgr_f_rows, _hgr_f_col0, _hgr_f_cols, _hgr_f_val
.code
_hgr_fill_rect:
        sta _hgr_f_val
        jsr _hgr_build_rows
        ldy #3
        lda (sp),y
        cmp #192
        bcs outside
        sta _hgr_f_y0
        lda #192
        sec
        sbc _hgr_f_y0
        dey
        cmp (sp),y              ; rows = min(request, space to bottom)
        bcc rows_ready
        lda (sp),y
rows_ready:
        beq outside
        sta _hgr_f_rows
        dey
        lda (sp),y
        cmp #40
        bcs outside
        sta _hgr_f_col0
        lda #40
        sec
        sbc _hgr_f_col0
        dey
        cmp (sp),y              ; columns = min(request, space to right)
        bcc cols_ready
        lda (sp),y
cols_ready:
        beq outside
        sta _hgr_f_cols
        jsr _hgr_fill_rect_asm
        jmp incsp4
outside:
        jmp incsp4
