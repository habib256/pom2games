; VERHILLE Arnaud — GPL-3.0. Color pixel x (0..139) -> interleaved byte (4x)/7
; and first bit (4x) mod 7. A 560-bit x indexes x>>2, then adds x&3 to the bit.
.include "dhgr_layout.inc"
.export _dhgr_cellbyte, _dhgr_cellphase
.rodata
dhgr_byte_table _dhgr_cellbyte, 140
_dhgr_cellphase:
.repeat 140,I
.byte (I*4) .mod 7
.endrepeat
