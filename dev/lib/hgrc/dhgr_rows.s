; VERHILLE Arnaud — GPL-3.0. DHGR scanline offsets: OR the draw page ($20/$40)
; into the high byte. Immutable, shared by the C-callable primitives.
.include "dhgr_layout.inc"
.export dhgr_rowlo, dhgr_rowhi
.rodata
dhgr_row_tables dhgr_rowlo, dhgr_rowhi
