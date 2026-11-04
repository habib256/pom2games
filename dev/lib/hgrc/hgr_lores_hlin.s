; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Inclusive LORES horizontal span: x0,x1,y on C stack, colour in A.
.export _hgr_lores_hlin
.import hgr_lores_draw, incsp3
.importzp sp, ptr2, tmp2, tmp3, tmp4
.code
_hgr_lores_hlin:
        and #15
        sta tmp2
        ldy #0
        lda (sp),y              ; y
        cmp #48
        bcs done
        sta tmp3
        adc #1                  ; successful bound check left C clear
        sta tmp4                ; bottom, exclusive
        iny
        lda (sp),y              ; x1, inclusive
        cmp #40
        bcc :+
        lda #39
:       tax
        inx
        stx ptr2+1              ; right, exclusive
        iny
        lda (sp),y              ; x0
        cmp ptr2+1
        bcs done                ; reversed or off-screen span
        sta ptr2
        lda ptr2+1
        sbc ptr2                ; C clear: right - x0 - 1
        sta ptr2+1              ; width minus one
        jsr incsp3
        jmp hgr_lores_draw
done:   jmp incsp3
