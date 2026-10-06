; VERHILLE Arnaud — GPL-3.0. The 2 KiB table image copied to $0800 at start:
; scanline addresses, color-pixel bytes and dot phases, pixel-to-dot masks
; for every phase, rectangle edge masks, the background tiles and the enemy
; masks (the font is in the AUX level bank).
.include "dhgr_layout.inc"
.include "tables.inc"
.segment "RODATA"
image:
dhgr_row_tables row_lo,row_hi
dhgr_byte_table xbyte,141
xphase:
.repeat 140,I
.byte (I*4) .mod 7
.endrepeat
; Four color pixels (bit 0 = left) as dots, from dot phase P, bytes 0..3.
dots:
.repeat 7,P
.repeat 16,G
.repeat 4,B
.byte (((((G&1)*15)+(((G>>1)&1)*240)+(((G>>2)&1)*3840)+(((G>>3)&1)*61440))<<P)>>(B*7))&$7F
.endrepeat
.endrepeat
.endrepeat
dhgr_end_table endbyte,141
dhgr_left_table leftm,141
dhgr_right_table rightm,141
.include "bg_tiles.inc"
.assert row_hi-image=T_ROW_HI, error, "row_hi offset"
.assert xbyte-image=T_XBYTE, error, "xbyte offset"
.assert xphase-image=T_XPHASE, error, "xphase offset"
.assert dots-image=T_DOTS, error, "dot mask offset"
.assert endbyte-image=T_END_BYTE, error, "end byte offset"
.assert leftm-image=T_LEFT, error, "left mask offset"
.assert rightm-image=T_RIGHT, error, "right mask offset"
.assert bg_tiles-image=T_BG, error, "background tile offset"
.assert spool_masks-image=T_SPOOL, error, "spool mask offset"
.assert *-image=T_END, error, "table image size"
