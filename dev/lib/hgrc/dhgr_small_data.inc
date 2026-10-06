; VERHILLE Arnaud — GPL-3.0. Compact DHGR text lookup data (1652 bytes).
.include "dhgr_small_font.inc"
small_font_lo:
.repeat 64,I
.byte <(small_font+I*6)
.endrepeat
small_font_hi:
.repeat 64,I
.byte >(small_font+I*6)
.endrepeat
small_xbyte:
.repeat 140,I
.byte (I*4)/7
.endrepeat
small_xphase:
.repeat 140,I
.byte (I*4) .mod 7
.endrepeat
small_left_masks:
.repeat 7,P
.byte ($7F<<P)&$7F
.endrepeat
small_right_masks:
.repeat 7,P
.if ((20+P) .mod 7)=0
.byte $7F
.else
.byte (1<<((20+P) .mod 7))-1
.endif
.endrepeat
small_row_lo:
.repeat 192,I
.byte <((I&7)*1024+((I>>3)&7)*128+(I>>6)*40)
.endrepeat
small_row_hi:
.repeat 192,I
.byte >((I&7)*1024+((I>>3)&7)*128+(I>>6)*40)
.endrepeat
small_ink:
.repeat 7,P
.repeat 16,G
.repeat 4,B
.byte (((((G&1)*15)+(((G>>1)&1)*240)+(((G>>2)&1)*3840)+(((G>>3)&1)*61440))<<P)>>(B*7))&$7F
.endrepeat
.endrepeat
.endrepeat
small_ink_lo:
.repeat 7,P
.byte <(small_ink+P*64)
.endrepeat
small_ink_hi:
.repeat 7,P
.byte >(small_ink+P*64)
.endrepeat
