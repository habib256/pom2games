; VERHILLE Arnaud — GPL-3.0. Layout of the 2 KiB table image that CHROMA.SYS
; copies to $0800 (built from payload.s); shared by tables.s and finetext.s.
TABLES_BASE = $0800
T_ROW_LO = 0
T_ROW_HI = T_ROW_LO+192
T_XBYTE = T_ROW_HI+192
T_XPHASE = T_XBYTE+141
T_DOTS = T_XPHASE+140
T_END_BYTE = T_DOTS+7*16*4
T_LEFT = T_END_BYTE+141
T_RIGHT = T_LEFT+141
T_BG = T_RIGHT+141
T_SPOOL = T_BG+6*32
T_END = T_SPOOL+7*8
; The font doubling tables are computed at start right after the image.
FINE_LEFT = $0F00
FINE_RIGHT = $0F80
.assert TABLES_BASE+T_END<=FINE_LEFT, error, "table image overlaps the doubling tables"
