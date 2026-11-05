; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; gfx_text(s), A/X=pointer. Keep the private iterator on the C stack so the
; renderer may destroy all scratch, and nested text calls cannot overwrite it.
.export _gfx_text
.import _gfx_putc, pushax
.importzp sp, ptr1
.code
_gfx_text:
        jsr pushax
next:
        ldy #1
        lda (sp),y
        sta ptr1+1
        dey
        lda (sp),y
        sta ptr1
        lda (ptr1),y
        beq done
        jsr _gfx_putc
        ldy #0
        clc
        lda (sp),y
        adc #1
        sta (sp),y
        bcc next
        iny
        lda (sp),y
        adc #0
        sta (sp),y
        jmp next
done:
        clc
        lda sp
        adc #2
        sta sp
        bcc :+
        inc sp+1
:       rts
