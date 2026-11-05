; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Card-neutral outline. Keep the normalized corners in the caller's frame:
; y1,x1lo,x1hi,y0,x0lo,x0hi. Backends may destroy every cc65 scratch byte.
; Far edges stay at their original coordinates; only visible edges are sent.
.export _gfx_rect
.import _gfx_width, _gfx_height, _gfx_hline, _gfx_vline
.import pusha, incsp2, incsp3, incsp6
.importzp sp, tmp1, tmp2
.code
_gfx_rect:
        jsr pusha
        ldy #2
        lda (sp),y
        ldy #5
        cmp (sp),y
        bcc swap_x
        bne x_ready
        dey
        lda (sp),y
        ldy #1
        cmp (sp),y
        bcc x_ready
        beq x_ready
swap_x:
        ldy #1
        lda (sp),y
        tax
        ldy #4
        lda (sp),y
        pha
        txa
        sta (sp),y
        ldy #1
        pla
        sta (sp),y
        iny
        lda (sp),y
        tax
        ldy #5
        lda (sp),y
        pha
        txa
        sta (sp),y
        ldy #2
        pla
        sta (sp),y
x_ready:
        ldy #0
        lda (sp),y
        ldy #3
        cmp (sp),y
        bcs y_ready
        tax
        lda (sp),y
        pha
        txa
        sta (sp),y
        ldy #0
        pla
        sta (sp),y
y_ready:
        ldy #5
        lda (sp),y
        cmp _gfx_width+1
        bcc check_y
        bne rejected
        dey
        lda (sp),y
        cmp _gfx_width
        bcs rejected
check_y:
        ldy #3
        lda (sp),y
        cmp _gfx_height
        bcs rejected
        ldy #5
        lda (sp),y
        ldy #2
        cmp (sp),y
        bne check_flat_y
        ldy #4
        lda (sp),y
        ldy #1
        cmp (sp),y
        bne check_flat_y
        dey
        lda (sp),y
        tax
        jsr incsp3
        txa
        jmp _gfx_vline
rejected:
        jmp incsp6
check_flat_y:
        ldy #0
        lda (sp),y
        ldy #3
        cmp (sp),y
        bne outline
        tax
        dey
        lda (sp),y
        iny
        sta (sp),y
        ldy #1
        lda (sp),y
        iny
        sta (sp),y
        jsr incsp2
        txa
        jmp _gfx_hline
outline:
        lda (sp),y             ; y0, Y=3
        jsr horizontal
        ldy #0
        lda (sp),y
        cmp _gfx_height
        bcs sides
        jsr horizontal
sides:
        ldy #3
        lda (sp),y
        clc
        adc #1
        ldy #0
        cmp (sp),y
        bcs rejected
        ldy #4
        jsr vertical
        ldy #2
        lda (sp),y
        cmp _gfx_width+1
        bcc right
        bne rejected
        dey
        lda (sp),y
        cmp _gfx_width
        bcs rejected
right:
        ldy #1
        jsr vertical
        jmp incsp6

; Prepare each argument frame directly; no nested runtime pushes are needed.
horizontal:
        sta tmp1
        sec
        lda sp
        sbc #4
        sta sp
        bcs :+
        dec sp+1
:
        ldy #9
        lda (sp),y
        ldy #3
        sta (sp),y
        ldy #8
        lda (sp),y
        ldy #2
        sta (sp),y
        ldy #6
        lda (sp),y
        ldy #1
        sta (sp),y
        ldy #5
        lda (sp),y
        ldy #0
        sta (sp),y
        lda tmp1
        jmp _gfx_hline

; Y selects the low byte of x. Horizontal spans already own the corners.
vertical:
        lda (sp),y
        sta tmp1
        iny
        lda (sp),y
        sta tmp2
        sec
        lda sp
        sbc #3
        sta sp
        bcs :+
        dec sp+1
:
        ldy #2
        lda tmp2
        sta (sp),y
        dey
        lda tmp1
        sta (sp),y
        ldy #6
        lda (sp),y
        clc
        adc #1
        ldy #0
        sta (sp),y
        ldy #3
        lda (sp),y
        sec
        sbc #1
        jmp _gfx_vline
