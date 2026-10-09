; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native x/7 and 1<<(x%7) tables. Default: 256 entries per table.
; HGR_FULL_WIDTH_TABLES adds columns 256..279 for hgr_plot16.
.ifdef HGR_FULL_WIDTH_TABLES
HGR_PLOT_COLUMNS = 280
.else
HGR_PLOT_COLUMNS = 256
.endif
hgr_col:
        .repeat HGR_PLOT_COLUMNS, col
        .byte col / 7
        .endrepeat
hgr_mask:
        .repeat HGR_PLOT_COLUMNS, col
        .byte 1 << (col .mod 7)
        .endrepeat
