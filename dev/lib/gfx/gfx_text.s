; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; gfx_text(s), A/X=pointer. Save the iterator on the hardware stack across
; the renderer, which may destroy all scratch or make nested text calls.
; No C-stack frame; two hardware-stack bytes remain private during each call.
.export _gfx_text
.import _gfx_putc
.importzp ptr1
.code
_gfx_text:
        sta ptr1
        stx ptr1+1
next:
        ldy #0
        lda (ptr1),y
        beq done
        tay
        lda ptr1+1
        pha
        lda ptr1
        pha
        tya
        jsr _gfx_putc
        pla
        clc
        adc #1
        sta ptr1
        pla
        adc #0
        sta ptr1+1
        jmp next
done:
        rts
