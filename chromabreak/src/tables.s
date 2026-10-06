; VERHILLE Arnaud — GPL-3.0. Addresses in the table image that CHROMA.SYS
; copies to $0800 at start (see payload.s and tables.inc).
.include "tables.inc"
.export _dhgr_row_lo := TABLES_BASE+T_ROW_LO
.export _dhgr_row_hi := TABLES_BASE+T_ROW_HI
.export _dhgr_color_byte := TABLES_BASE+T_XBYTE
.export _dhgr_dot_phase := TABLES_BASE+T_XPHASE
.export _dhgr_dot_masks := TABLES_BASE+T_DOTS
.export _dhgr_end_byte := TABLES_BASE+T_END_BYTE
.export _dhgr_left_mask := TABLES_BASE+T_LEFT
.export _dhgr_right_mask := TABLES_BASE+T_RIGHT
.export _bg_tiles := TABLES_BASE+T_BG
