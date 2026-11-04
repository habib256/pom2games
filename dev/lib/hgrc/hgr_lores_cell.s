; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; unsigned char *hgr_lores_cell(unsigned char x, unsigned char y)
; Fastcall: y in A, x on the C stack. Internal callers guarantee x<40,
; y<48, and initialized tables. Low row address <= $D0, so adding x
; cannot carry. Return the pointer in A/X and consume the stacked x.
; Separate member: native runs/rectangles do not need this C address helper.
.export _hgr_lores_cell
.import _hgr_lo_rowlo, _hgr_lo_rowhi, incsp1
.importzp sp
.code
_hgr_lores_cell:
        lsr a
        tax
        ldy #0
        lda (sp),y
        clc
        adc _hgr_lo_rowlo,x
        tay
        lda _hgr_lo_rowhi,x
        tax
        tya
        jmp incsp1
