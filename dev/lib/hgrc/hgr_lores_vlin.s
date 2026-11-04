; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Inclusive LORES vertical span: x,y0,y1 on C stack, colour in A.
.export _hgr_lores_vlin
.import hgr_lores_draw, incsp3
.importzp sp, ptr2, tmp2, tmp3, tmp4
.code
_hgr_lores_vlin:
        and #15
        sta tmp2
        ldy #0
        lda (sp),y              ; y1, inclusive
        cmp #48
        bcc :+
        lda #47
:       tax
        inx
        stx tmp4                ; bottom, exclusive
        iny
        lda (sp),y              ; y0
        cmp tmp4
        bcs done                ; reversed or off-screen span
        sta tmp3
        iny
        lda (sp),y              ; x
        cmp #40
        bcs done
        sta ptr2
        lda #0
        sta ptr2+1              ; width minus one
        jsr incsp3
        jmp hgr_lores_draw
done:   jmp incsp3
