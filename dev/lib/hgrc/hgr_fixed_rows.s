; VERHILLE Arnaud — GPL-3.0. Immutable offsets, no code or mutable state.
.export hgr_fixed_rowlo, hgr_fixed_rowhi
.rodata
hgr_fixed_rowlo:
.repeat 192, row
 .byte (((row & 7)*$400 + ((row >> 3)&7)*$80 + (row >> 6)*40) & $ff)
.endrepeat
hgr_fixed_rowhi:
.repeat 192, row
 .byte (((row & 7)*$400 + ((row >> 3)&7)*$80 + (row >> 6)*40) >> 8)
.endrepeat
