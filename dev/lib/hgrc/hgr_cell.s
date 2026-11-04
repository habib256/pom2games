; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_cell(cx, cy, set), cc65 fastcall. The native kernel checks bounds.
.export _hgr_cell
.import _hgr_build_rows, _hgr_build_columns, _hgr_build_masks, _hgr_cell_asm, incsp2
.importzp sp, _hgr_c_cx, _hgr_c_cy, _hgr_c_set
.code
_hgr_cell:
        sta _hgr_c_set
        jsr _hgr_build_rows
        jsr _hgr_build_columns
        jsr _hgr_build_masks
        ldy #1
        lda (sp),y
        sta _hgr_c_cx
        dey
        lda (sp),y
        sta _hgr_c_cy
        jsr _hgr_cell_asm
        jmp incsp2
