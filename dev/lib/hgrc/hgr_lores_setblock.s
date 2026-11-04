; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; LORES point: x,y on the C stack, colour in A. Preserve the other nibble.
.export _hgr_lores_setblock
.import _hgr_lores_build, _hgr_lo_rowlo, _hgr_lo_rowhi, incsp2
.importzp sp, ptr1, ptr2, tmp1, tmp2, tmp3
.code
_hgr_lores_setblock:
        and #15
        sta tmp2
        ldy #0
        lda (sp),y
        cmp #48
        bcs done
        sta tmp3                ; y survives the lazy table builder
        iny
        lda (sp),y
        cmp #40
        bcs done
        sta ptr2                ; x
        jsr _hgr_lores_build    ; clobbers only A/X/Y/tmp1
        lda tmp3
        lsr a
        tax                     ; text row; C = odd block-row
        lda _hgr_lo_rowlo,x
        sta ptr1
        lda _hgr_lo_rowhi,x
        sta ptr1+1
        ldy ptr2
        lda #$f0
        bcc even
        lda tmp2
        asl a
        asl a
        asl a
        asl a
        sta tmp2
        lda #$0f
even:   sta tmp1
        lda (ptr1),y
        and tmp1
        ora tmp2
        sta (ptr1),y
done:   jmp incsp2
