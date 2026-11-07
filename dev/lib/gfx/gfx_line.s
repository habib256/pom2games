; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Generic Bresenham; the same strict ties and axis shortcuts as gfx_line_ref.c.
; Persistent state is private on the C stack, so gfx_plot may destroy every
; cc65 scratch byte. The doubled error lives in scratch only between calls.
.export _gfx_line
.import _gfx_plot, _gfx_hline, _gfx_vline, _gfx_width, _gfx_height
.import pusha, pushax, incsp5
.importzp sp, tmp1, tmp2, tmp3, tmp4
.code
_gfx_line:
        sta tmp4
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
diagonal:
        lda tmp4
        cmp _gfx_height
        bcs rejected
        ldy #2
        lda (sp),y
        cmp _gfx_height
        bcs rejected
        ldy #4
        lda (sp),y
        cmp _gfx_width+1
        bcc x0_ready
        bne rejected
        dey
        lda (sp),y
        cmp _gfx_width
        bcs rejected
x0_ready:
        ldy #1
        lda (sp),y
        cmp _gfx_width+1
        bcc accepted
        bne rejected
        dey
        lda (sp),y
        cmp _gfx_width
        bcs rejected
accepted:
        jmp prepare
rejected:
        jmp incsp5
horizontal:
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
:       lda tmp4
        jmp _gfx_hline
vertical:
        clc
        lda sp
        adc #2
        sta sp
        bcc :+
        inc sp+1
:       lda tmp4
        jmp _gfx_vline

; 13-byte frame: err(2), dx(2), -dy low, sx, sy, ye, xe(2), y, x(2).
; Both endpoints have byte y coordinates, and axes were dispatched already:
; -abs(dy) is nonzero with an implicit $ff high byte.
prepare:
        lda tmp4
        jsr pusha
        sec
        lda sp
        sbc #7
        sta sp
        bcs :+
        dec sp+1
:
        ldy #11
        lda (sp),y
        sta tmp1
        iny
        lda (sp),y
        sta tmp2
        ldy #8
        sec
        lda (sp),y
        sbc tmp1
        sta tmp1
        iny
        lda (sp),y
        sbc tmp2
        sta tmp2
        ldx #1
        bcs dx_ready
        ldx #$ff
        sec
        lda #0
        sbc tmp1
        sta tmp1
        lda #0
        sbc tmp2
        sta tmp2
dx_ready:
        ldy #2
        lda tmp1
        sta (sp),y
        iny
        lda tmp2
        sta (sp),y
        ldy #5
        txa
        sta (sp),y
        ldy #10
        lda (sp),y
        sta tmp1
        ldy #7
        sec
        lda (sp),y
        sbc tmp1
        ldx #1
        bcs dy_ready
        ldx #$ff
        eor #$ff
        adc #1
dy_ready:
        eor #$ff                ; -abs(dy), nonzero because axes are handled
        clc
        adc #1
        sta tmp1
        ldy #4
        sta (sp),y
        ldy #6
        txa
        sta (sp),y
        ldy #2
        clc
        lda (sp),y
        adc tmp1
        sta tmp1
        iny
        lda (sp),y
        adc #$ff
        ldy #1
        sta (sp),y
        dey
        lda tmp1
        sta (sp),y
plot:
        ldy #12
        lda (sp),y
        tax
        dey
        lda (sp),y
        jsr pushax
        ldy #12                ; y at 10, plus the pushed x word
        lda (sp),y
        jsr _gfx_plot
        ldy #11
        lda (sp),y
        ldy #8
        cmp (sp),y
        bne advance
        ldy #12
        lda (sp),y
        ldy #9
        cmp (sp),y
        bne advance
        ldy #10
        lda (sp),y
        ldy #7
        cmp (sp),y
        bne advance
        clc
        lda sp
        adc #13
        sta sp
        bcc :+
        inc sp+1
:       rts
advance:
        ldy #0
        lda (sp),y
        asl
        sta tmp1
        iny
        lda (sp),y
        rol
        sta tmp2
        ; Strict e2 > -dy: signed (-dy - e2) < 0.
        ldy #4
        sec
        lda (sp),y
        sbc tmp1
        lda #$ff
        sbc tmp2
        bvc :+
        eor #$80
:       bpl step_y
        ldy #4
        lda (sp),y
        tax
        ldy #0
        clc
        txa
        adc (sp),y
        sta (sp),y
        iny
        lda (sp),y
        adc #$ff
        sta (sp),y
        ldy #5
        lda (sp),y
        bmi x_left
        ldy #11
        clc
        lda (sp),y
        adc #1
        sta (sp),y
        bcc step_y
        iny
        lda (sp),y
        adc #0
        sta (sp),y
        jmp step_y
x_left:
        ldy #11
        sec
        lda (sp),y
        sbc #1
        sta (sp),y
        bcs step_y
        iny
        lda (sp),y
        sbc #0
        sta (sp),y
step_y:
        ; Strict e2 < dx, using the same doubled error as the x decision.
        ldy #2
        sec
        lda tmp1
        sbc (sp),y
        iny
        lda tmp2
        sbc (sp),y
        bvc :+
        eor #$80
:       bpl next
        ldy #2
        lda (sp),y
        sta tmp3
        iny
        lda (sp),y
        tax
        ldy #0
        clc
        lda (sp),y
        adc tmp3
        sta (sp),y
        iny
        txa
        adc (sp),y
        sta (sp),y
        ldy #6
        lda (sp),y
        ldy #10
        clc
        adc (sp),y
        sta (sp),y
next:
        jmp plot
