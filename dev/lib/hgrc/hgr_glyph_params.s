; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Shared glyph arguments, independent of string traversal and font lookup.
.exportzp _hgr_g_glyph, _hgr_g_col, _hgr_g_bit, _hgr_g_y
.segment "ZEROPAGE"
_hgr_g_glyph: .res 2        ; pointer to glyph bytes
_hgr_g_col:   .res 1        ; starting byte column
_hgr_g_bit:   .res 1        ; starting bit within the column (0..6)
_hgr_g_y:     .res 1        ; top scanline
