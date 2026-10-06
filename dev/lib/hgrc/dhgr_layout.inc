; VERHILLE Arnaud — GPL-3.0. Shared DHGR address and color-cell tables.
.ifndef DHGR_LAYOUT_INCLUDED
DHGR_LAYOUT_INCLUDED = 1
.macro dhgr_row_tables low_table, high_table
low_table:
.repeat 192,I
.byte <((I&7)*1024+((I>>3)&7)*128+(I>>6)*40)
.endrepeat
high_table:
.repeat 192,I
.byte >((I&7)*1024+((I>>3)&7)*128+(I>>6)*40)
.endrepeat
.endmacro
.macro dhgr_byte_table target, count
 target:
.repeat count,I
.byte (I*4)/7
.endrepeat
.endmacro
.macro dhgr_end_table target, count
 target:
.repeat count,I
.byte (I*4+6)/7
.endrepeat
.endmacro
.macro dhgr_left_table target, count
 target:
.repeat count,I
.byte ($7F<<((I*4) .mod 7))&$7F
.endrepeat
.endmacro
.macro dhgr_right_table target, count
 target:
.repeat count,I
.if (I*4) .mod 7
.byte (1<<((I*4) .mod 7))-1
.else
.byte $7F
.endif
.endrepeat
.endmacro
.endif
