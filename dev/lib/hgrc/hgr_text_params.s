; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_text_params.s — Apple II HGR kernel; linked independently from hgrc.lib.
.exportzp _hgr_g_glyph, _hgr_g_col, _hgr_g_mask, _hgr_g_y, _hgr_t_col, _hgr_t_bit, _hgr_t_n, _hgr_t_s, _hgr_t_font

.segment "ZEROPAGE"
_hgr_g_glyph: .res 2        ; pointer to 8 glyph bytes
_hgr_g_col:   .res 1        ; starting byte column
_hgr_g_mask:  .res 1        ; starting bit mask
_hgr_g_y:     .res 1        ; top scanline
_hgr_t_col:   .res 1        ; current byte column of the pen
_hgr_t_bit:   .res 1        ; current bit within the column (0..6)
_hgr_t_n:     .res 1        ; glyph cells left to draw (C precomputes the fit)
_hgr_t_s:     .res 2        ; string pointer
_hgr_t_font:  .res 2        ; glyph table base (kBBFontAscii)
