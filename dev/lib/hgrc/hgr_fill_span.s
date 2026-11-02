; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Shared white fill entry for clipped, inclusive HGR spans/rectangles.
; Caller supplies hgr_r_x/xr, y0 and rows (1..192). No 8-bit width limit.
; Table builders leave this parameter block intact, including on first use.
.export _hgr_fill_span
.import _hgr_build_rows, _hgr_build_columns, _hgr_build_masks, _hgr_pixrect_asm
.importzp _hgr_r_mode
.code
_hgr_fill_span:
        jsr _hgr_build_rows
        jsr _hgr_build_columns
        jsr _hgr_build_masks
        lda #1
        sta _hgr_r_mode
        jmp _hgr_pixrect_asm
