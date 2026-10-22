; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native x/7 and 1<<(x%7) tables. Default: 256 entries per table.
; HGR_FULL_WIDTH_TABLES adds columns 256..279 for hgr_plot16.
; HGR_PLOT_TABLES_RAM = 1 before the include: the tables are reserved in BSS
; instead of stored in the file, and hgr_plot_tables_init (~40 bytes,
; assembled in the current segment) fills them; call it once before any
; drawing. Clobbers A, X, Y.
.ifdef HGR_FULL_WIDTH_TABLES
HGR_PLOT_COLUMNS = 280
.else
HGR_PLOT_COLUMNS = 256
.endif
.ifdef _HGR_PLOT_LOADED_                ; hgr_plot16 reads columns 256..279
.assert HGR_PLOT_COLUMNS = 280, error, "hgr_plot16 needs HGR_FULL_WIDTH_TABLES = 1 (columns 256..279)"
.endif
.ifdef HGR_PLOT_TABLES_RAM
.pushseg
.segment "BSS"
hgr_col:  .res HGR_PLOT_COLUMNS
hgr_mask: .res HGR_PLOT_COLUMNS
.popseg
; One step of the fill: A = mask, Y = column, X = x (low byte).
.macro HGR_PLOT_TABLES_STEP base
        STA     hgr_mask+base,X
        PHA
        TYA
        STA     hgr_col+base,X
        PLA
        ASL     A
        BPL     :+                      ; $80: past bit 6, next byte column
        LDA     #1
        INY
:       INX
.endmacro
hgr_plot_tables_init:
        LDA     #1
        LDX     #0
        LDY     #0
@lo:    HGR_PLOT_TABLES_STEP 0
        BNE     @lo
.if HGR_PLOT_COLUMNS > 256
@hi:    HGR_PLOT_TABLES_STEP 256
        CPX     #HGR_PLOT_COLUMNS-256
        BNE     @hi
.endif
        RTS
.else
hgr_col:
        .repeat HGR_PLOT_COLUMNS, col
        .byte col / 7
        .endrepeat
hgr_mask:
        .repeat HGR_PLOT_COLUMNS, col
        .byte 1 << (col .mod 7)
        .endrepeat
.endif
