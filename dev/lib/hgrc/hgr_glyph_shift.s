; VERHILLE Arnaud — GPL-3.0. Doubled 16x16 glyph rows, pre-shifted.
; Index bit*16 + nibble: the nibble's four pixels each doubled (bit k ->
; bits 2k, 2k+1), shifted left by the pen bit 0..6, low/high bytes. A glyph
; row is lo[low nibble], hi[low nibble] | lo[high nibble], hi[high nibble].
.export hgr_dbl_lo, hgr_dbl_hi
.rodata
hgr_dbl_lo:
.repeat 7,S
.repeat 16,N
.byte <(((N&1)*3|((N>>1)&1)*12|((N>>2)&1)*48|((N>>3)&1)*192)<<S)
.endrepeat
.endrepeat
hgr_dbl_hi:
.repeat 7,S
.repeat 16,N
.byte >(((N&1)*3|((N>>1)&1)*12|((N>>2)&1)*48|((N>>3)&1)*192)<<S)
.endrepeat
.endrepeat
