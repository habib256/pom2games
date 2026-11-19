; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; LORES read: x on the C stack, y in A. Return the colour in A, X = 0.
.include "hgr_lores_point.inc"
.export _hgr_lores_getblock
.import _hgr_lores_build, _hgr_lo_rowlo, _hgr_lo_rowhi, incsp1
.importzp sp, ptr1, ptr2, tmp2
.code
_hgr_lores_getblock:
        cmp #48
        bcs outside
        sta tmp2                ; y survives the lazy table builder
        ldy #0
        lda (sp),y
        lores_point_address tmp2, outside
        lda (ptr1),y             ; row offset + x <= $F7: no page crossing
        bcc even                ; addressing and load preserved C
        lsr a
        lsr a
        lsr a
        lsr a
even:   and #15
        ldx #0
        jmp incsp1
outside:
        lda #0
        tax
        jmp incsp1
