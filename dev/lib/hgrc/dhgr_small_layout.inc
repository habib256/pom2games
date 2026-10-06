; VERHILLE Arnaud — GPL-3.0. One schema for linked and relocated text data.
.ifndef DHGR_SMALL_LAYOUT_INCLUDED
DHGR_SMALL_LAYOUT_INCLUDED = 1
DHGR_SMALL_FIRST = 32
DHGR_SMALL_COUNT = 64
DHGR_SMALL_STRIDE = 6
DHGR_SMALL_ADVANCE = 5
DHGR_SMALL_HEIGHT = 5
.ifndef DHGR_SMALL_FONT_BASE
DHGR_SMALL_FONT_BASE = $0800
.endif
.struct DhgrSmallLayout
font           .byte ::DHGR_SMALL_COUNT*::DHGR_SMALL_STRIDE
font_lo        .byte ::DHGR_SMALL_COUNT
font_hi        .byte ::DHGR_SMALL_COUNT
xbyte          .byte 141
xphase         .byte 140
left_masks     .byte 7
right_masks    .byte 7
row_lo         .byte 192
row_hi         .byte 192
ink            .byte 7*16*4
ink_lo         .byte 7
ink_hi         .byte 7
.endstruct
DHGR_SMALL_DATA_BYTES = .sizeof(DhgrSmallLayout)
.endif
