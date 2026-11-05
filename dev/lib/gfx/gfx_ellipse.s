; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native 64-chord ellipse, exact C ordering, truncation and endpoint clipping.
; Initial six-byte frame: y1,x1lo,x1hi,y0,x0lo,x0hi. Ordinary ellipses
; reuse it in a twelve-byte private frame; backend cc65 scratch is free.
; Degenerate boxes reuse five slots and tail-call their single gfx_line.
.export _gfx_ellipse
.import _gfx_line, _gfx_width, _gfx_height, _gfx_ellipse_offset
.import pusha, pushax, incsp6, addysp
.importzp sp, ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
.code
_gfx_ellipse:
        jsr pusha
        ldy #4
        lda (sp),y
        sta ptr1
        iny
        lda (sp),y
        sta ptr1+1
        ldy #1
        lda (sp),y
        sta ptr2
        iny
        lda (sp),y
        sta ptr2+1
        cmp ptr1+1
        bcc swap
        bne sorted
        lda ptr2
        cmp ptr1
        bcs sorted
swap:
        ldx ptr1
        lda ptr2
        sta ptr1
        stx ptr2
        ldx ptr1+1
        lda ptr2+1
        sta ptr1+1
        stx ptr2+1
sorted:
        lda ptr1+1
        cmp _gfx_width+1
        bcc check_y
        bne reject
        lda ptr1
        cmp _gfx_width
        bcs reject
check_y:
        ldy #0
        lda (sp),y
        cmp _gfx_height
        bcc visible
        ldy #3
        lda (sp),y
        cmp _gfx_height
        bcc visible
reject:
        jmp incsp6
visible:
        sec
        lda ptr2
        sbc ptr1
        sta tmp1
        lda ptr2+1
        sbc ptr1+1
        lsr
        sta tmp2
        ror tmp1
        ; C retains the original extent bit zero: rx=0 means width 0 or 1.
        ora tmp1
        bne dimensions
        bcc vertical
        ldy #0
        lda (sp),y
        ldy #3
        cmp (sp),y
        bne vertical
        ; A one-pixel horizontal extent and equal y falls through to ry=0.
dimensions:
        ; ADC carry supplies the ninth bit of y0+y1 to the centre shift.
        ldy #0
        clc
        lda (sp),y
        ldy #3
        adc (sp),y
        ror
        sta tmp3
        ldy #0
        sec
        lda (sp),y
        ldy #3
        sbc (sp),y
        bcs magnitude
        eor #$ff
        adc #1
magnitude:
        lsr
        sta tmp4
        bne ordinary
        lda tmp3
        ldx #0
        jsr clamp_y
        sta tmp1
        sta tmp2
        jmp horizontal
vertical:
        lda ptr1
        ldx ptr1+1
        jsr clamp_x
        sta ptr1
        stx ptr1+1
        sta ptr2
        stx ptr2+1
        ldy #3
        lda (sp),y
        ldx #0
        jsr clamp_y
        sta tmp1
        ldy #0
        lda (sp),y
        ldx #0
        jsr clamp_y
        sta tmp2
        jmp degenerate
horizontal:
        lda ptr1
        ldx ptr1+1
        jsr clamp_x
        sta ptr1
        stx ptr1+1
        lda ptr2
        ldx ptr2+1
        jsr clamp_x
        sta ptr2
        stx ptr2+1
degenerate:
        ; Discard the saved y1 slot, then rebuild gfx_line's five-byte frame.
        inc sp
        bne :+
        inc sp+1
:       ldy #0
        lda ptr2
        sta (sp),y
        iny
        lda ptr2+1
        sta (sp),y
        iny
        lda tmp1
        sta (sp),y
        iny
        lda ptr1
        sta (sp),y
        iny
        lda ptr1+1
        sta (sp),y
        lda tmp2
        jmp _gfx_line
ordinary:
        ; The twelve-byte frame is i,ay,ax(2),ry,yc,rx(2),xc(2),bx(2).
        clc
        lda ptr1
        adc tmp1
        sta ptr1
        lda ptr1+1
        adc tmp2
        sta ptr1+1
        sec
        lda sp
        sbc #6
        sta sp
        bcs :+
        dec sp+1
:       ldy #4
        lda tmp4
        sta (sp),y
        iny
        lda tmp3
        sta (sp),y
        iny
        lda tmp1
        sta (sp),y
        iny
        lda tmp2
        sta (sp),y
        iny
        lda ptr1
        sta (sp),y
        iny
        lda ptr1+1
        sta (sp),y
        ; Initial point is (xc+rx,yc), clamped.
        clc
        lda ptr1
        adc tmp1
        sta tmp1
        lda ptr1+1
        adc tmp2
        tax
        lda tmp1
        jsr clamp_x
        ldy #2
        sta (sp),y
        iny
        txa
        sta (sp),y
        lda tmp3
        ldx #0
        jsr clamp_y
        ldy #1
        sta (sp),y
        dey
        lda #1
        sta (sp),y
ellipse_loop:
        ; Sample angles 1..63,0: the previous point is already clamped.
        ldy #7
        lda (sp),y
        tax
        dey
        lda (sp),y
        jsr pushax
        ldy #2
        lda (sp),y
        tay
        lda wave+16,y
        jsr _gfx_ellipse_offset
        sta tmp1
        stx tmp2
        ldy #8
        clc
        lda (sp),y
        adc tmp1
        sta tmp1
        iny
        lda (sp),y
        adc tmp2
        tax
        lda tmp1
        jsr clamp_x
        ldy #10
        sta (sp),y
        iny
        txa
        sta (sp),y
        ldy #4
        lda (sp),y
        ldx #0
        jsr pushax
        ldy #2
        lda (sp),y
        tay
        lda wave,y
        jsr _gfx_ellipse_offset
        ldy #5
        clc
        adc (sp),y
        sta tmp1
        txa
        adc #0
        tax
        lda tmp1
        jsr clamp_y
        sta tmp4
        ; Five outgoing arguments. Update ax/ay before entering the backend;
        ; neither the next point nor the iterator may live in scratch there.
        sec
        lda sp
        sbc #5
        sta sp
        bcs :+
        dec sp+1
:       ldy #7
        lda (sp),y
        ldy #3
        sta (sp),y
        ldy #8
        lda (sp),y
        ldy #4
        sta (sp),y
        ldy #6
        lda (sp),y
        ldy #2
        sta (sp),y
        ldy #15
        lda (sp),y
        ldy #0
        sta (sp),y
        ldy #7
        sta (sp),y
        ldy #16
        lda (sp),y
        ldy #1
        sta (sp),y
        ldy #8
        sta (sp),y
        ldy #6
        lda tmp4
        sta (sp),y
        jsr _gfx_line
        ldy #0
        lda (sp),y
        clc
        adc #1
        and #63
        sta (sp),y
        cmp #1
        beq finished
        jmp ellipse_loop
finished:
        ldy #12
        jmp addysp
clamp_x:
        cpx _gfx_width+1
        bcc done_x
        bne max_x
        cmp _gfx_width
        bcc done_x
max_x:
        sec
        lda _gfx_width
        sbc #1
        tay
        lda _gfx_width+1
        sbc #0
        tax
        tya
done_x:
        rts
clamp_y:
        cpx #0
        beq byte_y
        bmi zero_y
max_y:
        lda _gfx_height
        sec
        sbc #1
        rts
byte_y:
        cmp _gfx_height
        bcs max_y
        rts
zero_y:
        lda #0
        rts
.rodata
; One sine period plus its first quarter; cosine is wave+16.
wave:
        .byte 0,6,12,19,24,30,36,41,45,49,53,56,59,61,63,64
        .byte 64,64,63,61,59,56,53,49,45,41,36,30,24,19,12,6
        .byte 0,250,244,237,232,226,220,215,211,207,203,200,197,195,193,192
        .byte 192,192,193,195,197,200,203,207,211,215,220,226,232,237,244,250
        .byte 0,6,12,19,24,30,36,41,45,49,53,56,59,61,63,64
