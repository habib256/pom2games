; VERHILLE Arnaud — GPL-3.0. Compact white DHGR text, color-safe cells.
.export _dhgr_puts_small
.import _dhgr_small_x, _dhgr_small_y, _dhgr_small_string
.importzp sp
.code
; fastcall A=y; software stack: x, string low, string high.
_dhgr_puts_small:
        sta _dhgr_small_y
        ldy #0
        lda (sp),y
        sta _dhgr_small_x
        ldy #2
        lda (sp),y
        tax
        dey
        lda (sp),y
        ; Release the caller arguments before entering the string kernel.
        tay
        lda sp
        clc
        adc #3
        sta sp
        bcc @ready
        inc sp+1
@ready: tya
        jmp _dhgr_small_string
