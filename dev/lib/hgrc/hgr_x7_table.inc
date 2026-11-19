; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.ifndef HGR_X7_TABLE_INC
HGR_X7_TABLE_INC = 1
.ifndef HGRC_X7_FOLDED
HGRC_X7_FOLDED = 0
.endif

; Each independent builder owns its table and its lazy initialization flag.
; On a cold call ptr1 points to the first group of seven pixels.
.macro hgr_x7_begin entry, table
.export entry, table
.importzp ptr1
.bss
table: .res 280
ready: .res 1
.code
entry:
        lda ready
        beq :+
        rts
:       lda #<table
        sta ptr1
        lda #>table
        sta ptr1+1
.endmacro

; Tables may begin at any byte alignment. Preserve X (the group counter).
.macro hgr_x7_next_column
        clc
        lda ptr1
        adc #7
        sta ptr1
        bcc :+
        inc ptr1+1
:
.endmacro
.endif
