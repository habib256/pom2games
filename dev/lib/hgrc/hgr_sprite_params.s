; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_sprite_params.s — Apple II HGR kernel; linked independently from hgrc.lib.
.exportzp _hgr_b_col, _hgr_b_w, _hgr_b_h, _hgr_b_stride, _hgr_b_y, _hgr_b_mode, _hgr_b_src

.segment "ZEROPAGE"
_hgr_b_col:   .res 1        ; start byte column of the pen
_hgr_b_w:     .res 1        ; pixels to draw per row (right-clipped by C)
_hgr_b_h:     .res 1        ; rows (bottom-clipped by C)
_hgr_b_stride:.res 1        ; source bytes per row = (w+7)/8
_hgr_b_y:     .res 1        ; current scanline (advanced per row)
_hgr_b_mode:  .res 1        ; 0 SET (OR) / 1 CLEAR (AND ~) / 2 XOR (EOR)
_hgr_b_src:   .res 2        ; source row pointer (advanced per row)
