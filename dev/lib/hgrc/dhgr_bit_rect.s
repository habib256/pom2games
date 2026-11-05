; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; dhgr_bit_rect(x,y,width,height): A=height, stack=widthlo,widthhi,y,xlo,xhi.
; Validate before changing span parameters. Saturate a 17-bit exclusive end,
; then convert to the inclusive endpoint consumed by the existing kernel.
.export _dhgr_bit_rect
.import _dhgr_span_x, _dhgr_span_end, _dhgr_span_asm, addysp
.importzp sp, tmp1
.code
_dhgr_bit_rect:
        cmp #0
        beq reject
        sta tmp1               ; requested height, no local stack frame
        ldy #4
        lda (sp),y
        cmp #2
        bcc x_valid
        bne reject
        dey
        lda (sp),y
        cmp #48                ; x < 560 ($230)
        bcs reject
x_valid:
        ldy #2
        lda (sp),y
        cmp #192
        bcs reject
        ldy #0
        lda (sp),y
        iny
        ora (sp),y
        bne valid
reject:
        ldy #5
        jmp addysp
valid:
        ldy #3
        lda (sp),y
        sta _dhgr_span_x
        iny
        lda (sp),y
        sta _dhgr_span_x+1
        ldy #0
        lda (sp),y
        clc
        adc _dhgr_span_x
        sta _dhgr_span_end
        iny
        lda (sp),y
        adc _dhgr_span_x+1
        sta _dhgr_span_end+1
        bcs right_edge         ; x+width overflowed 16 bits
        cmp #2
        bcc end_valid
        bne right_edge
        lda _dhgr_span_end
        cmp #49                ; exclusive end <= 560
        bcs right_edge
end_valid:
        lda _dhgr_span_end
        bne decrement_end
        dec _dhgr_span_end+1
decrement_end:
        dec _dhgr_span_end
        jmp clip_height
right_edge:
        lda #47
        sta _dhgr_span_end
        lda #2
        sta _dhgr_span_end+1
clip_height:
        ldy #2
        lda #192
        sec
        sbc (sp),y
        cmp tmp1
        bcc rows_ready
        lda tmp1
rows_ready:
        tax                    ; high byte: clipped row count
        lda (sp),y             ; low byte: first row
        ldy #5
        jsr addysp             ; preserve A/X and discard all arguments
        jmp _dhgr_span_asm
