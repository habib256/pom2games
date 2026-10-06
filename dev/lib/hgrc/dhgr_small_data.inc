; VERHILLE Arnaud — GPL-3.0. Compact DHGR text lookup data (see dhgr_small_layout.inc).
.include "dhgr_layout.inc"
.include "dhgr_small_layout.inc"
.include "dhgr_small_font.inc"
small_font_lo:
.repeat 64,I
.byte <(small_font+I*DHGR_SMALL_STRIDE)
.endrepeat
small_font_hi:
.repeat 64,I
.byte >(small_font+I*DHGR_SMALL_STRIDE)
.endrepeat
dhgr_byte_table small_xbyte,141
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
dhgr_row_tables small_row_lo,small_row_hi
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

.assert *-small_font=DHGR_SMALL_DATA_BYTES,error,"DHGR compact data size differs from schema"
.assert small_font-small_font=DhgrSmallLayout::font,error,"DHGR compact font offset differs from schema"
.assert small_font_lo-small_font=DhgrSmallLayout::font_lo,error,"DHGR compact font_lo offset differs from schema"
.assert small_font_hi-small_font=DhgrSmallLayout::font_hi,error,"DHGR compact font_hi offset differs from schema"
.assert small_xbyte-small_font=DhgrSmallLayout::xbyte,error,"DHGR compact xbyte offset differs from schema"
.assert small_xphase-small_font=DhgrSmallLayout::xphase,error,"DHGR compact xphase offset differs from schema"
.assert small_left_masks-small_font=DhgrSmallLayout::left_masks,error,"DHGR compact left_masks offset differs from schema"
.assert small_right_masks-small_font=DhgrSmallLayout::right_masks,error,"DHGR compact right_masks offset differs from schema"
.assert small_row_lo-small_font=DhgrSmallLayout::row_lo,error,"DHGR compact row_lo offset differs from schema"
.assert small_row_hi-small_font=DhgrSmallLayout::row_hi,error,"DHGR compact row_hi offset differs from schema"
.assert small_ink-small_font=DhgrSmallLayout::ink,error,"DHGR compact ink offset differs from schema"
.assert small_ink_lo-small_font=DhgrSmallLayout::ink_lo,error,"DHGR compact ink_lo offset differs from schema"
.assert small_ink_hi-small_font=DhgrSmallLayout::ink_hi,error,"DHGR compact ink_hi offset differs from schema"
