; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; LORES read: x on the C stack, y in A. Return the colour in A, X = 0.
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
        cmp #40
        bcs outside
        sta ptr2                ; x
        jsr _hgr_lores_build    ; clobbers only A/X/Y/tmp1
        lda tmp2
        lsr a
        tax                     ; text row; C = odd block-row
        lda _hgr_lo_rowlo,x
        sta ptr1
        lda _hgr_lo_rowhi,x
        sta ptr1+1
        ldy ptr2
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
