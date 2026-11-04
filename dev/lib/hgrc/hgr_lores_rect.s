; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Clipped LORES rectangle: x,y,w,h on C stack, colour in A.
.export _hgr_lores_fill_rect
.import hgr_lores_draw, incsp4
.importzp sp, ptr2, tmp2, tmp3, tmp4
.code
_hgr_lores_fill_rect:
        and #15
        sta tmp2
        ldy #3
        lda (sp),y              ; x
        cmp #40
        bcs done
        sta ptr2
        dey
        lda (sp),y              ; y
        cmp #48
        bcs done
        sta tmp3
        dey
        lda (sp),y              ; width, possibly 255
        beq done
        adc ptr2                ; successful y bound check left C clear
        bcs right_clip
        cmp #40
        bcc right_ready
right_clip:
        lda #40
right_ready:
        clc
        sbc ptr2
        sta ptr2+1              ; width minus one
        dey
        lda (sp),y              ; height, possibly 255
        beq done
        clc
        adc tmp3
        bcs bottom_clip
        cmp #48
        bcc bottom_ready
bottom_clip:
        lda #48
bottom_ready:
        sta tmp4                ; bottom, exclusive
        jsr incsp4
        jmp hgr_lores_draw
done:   jmp incsp4
