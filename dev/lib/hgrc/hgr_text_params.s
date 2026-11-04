; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_text_params.s — Apple II HGR kernel; linked independently from hgrc.lib.
; String traversal state, linked only by the 8x8/16x16 string kernels.
; Glyph arguments and font-address calculation have independent members.
.exportzp _hgr_t_col, _hgr_t_bit, _hgr_t_n, _hgr_t_s

.segment "ZEROPAGE"
_hgr_t_col:   .res 1        ; current byte column of the pen
_hgr_t_bit:   .res 1        ; current bit within the column (0..6)
_hgr_t_n:     .res 1        ; glyph cells left to draw (C precomputes the fit)
_hgr_t_s:     .res 2        ; string pointer
