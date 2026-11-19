; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; gfx_line(x0,y0,x1,y1): A=y1, stack=x1lo,x1hi,y0,x0lo,x0hi.
; Keep horizontal priority for a single point; a diagonal falls through.
.macro gfx_line_classify saved_y, horizontal, vertical, diagonal
        sta saved_y
        ldy #2
        cmp (sp),y
        beq horizontal
        ldy #0
        lda (sp),y
        ldy #3
        cmp (sp),y
        bne diagonal
        ldy #1
        lda (sp),y
        ldy #4
        cmp (sp),y
        beq vertical
.endmacro

; Both span entries reuse the caller's stack frame and consume its arguments.
.macro gfx_line_spans saved_y, horizontal, vertical
horizontal:
        ; Replace y0 with x1hi and move x1lo up one slot, then drop a byte.
        ldy #1
        lda (sp),y
        iny
        sta (sp),y
        ldy #0
        lda (sp),y
        iny
        sta (sp),y
        inc sp
        bne :+
        inc sp+1
:       lda saved_y
        jmp _gfx_hline
vertical:
        ; Discard x1: y0,x0lo,x0hi already match the vertical signature.
        clc
        lda sp
        adc #2
        sta sp
        bcc :+
        inc sp+1
:       lda saved_y
        jmp _gfx_vline
.endmacro
