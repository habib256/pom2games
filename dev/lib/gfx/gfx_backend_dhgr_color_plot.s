; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Only x is narrowed/rejected here. Even an invalid y still updates dot_x,
; preserving the C adapter's inputs to the color-dot kernel.
.export _gfx_plot
.import _dhgr_dot_x, _dhgr_color_dot, incsp2
.importzp sp
.code
rejected:
        jmp incsp2
_gfx_plot:
        tax
        ldy #1
        lda (sp),y
        bne rejected
        dey
        lda (sp),y
        cmp #140
        bcs rejected
        sta _dhgr_dot_x
        clc
        lda sp
        adc #2
        sta sp
        bcc :+
        inc sp+1
:       txa
        jmp _dhgr_color_dot
