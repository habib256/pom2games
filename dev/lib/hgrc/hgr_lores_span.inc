; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Y indexes the inclusive end on the cc65 stack, followed by the start.
; Store the exclusive end and the start. On success Y indexes the start
; and carry is clear for the horizontal width-minus-one subtraction.
.macro lores_clip_span limit, first, past_last, reject
        lda (sp),y
        cmp #limit
        bcc :+
        lda #(limit-1)
:       tax
        inx
        stx past_last
        iny
        lda (sp),y
        cmp past_last
        bcs reject
        sta first
.endmacro
