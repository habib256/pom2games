; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Midpoint circles, exact C point order and tie rules, one write per pixel.
; Private seven-byte frame: x,y,dlo,dhi,yc,xclo,xchi. Backend scratch is free.
.export _gfx_circle
.import _gfx_plot, _gfx_width, _gfx_height, pushax, incsp3, incsp7
.importzp sp, tmp1, tmp2, tmp4
.code
_gfx_circle:
        sta tmp4
        ldy #1
        sec
        lda (sp),y
        sbc _gfx_width
        sta tmp1
        iny
        lda (sp),y
        sbc _gfx_width+1
        bcc check_y
        bne rejected
        lda tmp1
        cmp tmp4
        bcs rejected
check_y:
        ldy #0
        lda (sp),y
        cmp _gfx_height
        bcc visible
        sec
        sbc _gfx_height
        cmp tmp4
        bcs rejected
visible:
        lda tmp4
        bne interior_check
        lda (sp),y             ; y=0, original centre y
        inc sp
        bne :+
        inc sp+1
:       jmp _gfx_plot
rejected:
        jmp incsp3
interior_check:
        ; Select an unchecked symmetry loop only when every point is on screen.
        ldx #0
        ldy #0
        lda (sp),y
        cmp tmp4
        bcc prepare
        clc
        adc tmp4
        bcs prepare
        cmp _gfx_height
        bcs prepare
        ldy #1
        sec
        lda (sp),y
        sbc tmp4
        iny
        lda (sp),y
        sbc #0
        bcc prepare
        dey
        clc
        lda (sp),y
        adc tmp4
        sta tmp1
        iny
        lda (sp),y
        adc #0
        bcs prepare
        cmp _gfx_width+1
        bcc interior
        bne prepare
        lda tmp1
        cmp _gfx_width
        bcs prepare
interior:
        inx
prepare:
        sec
        lda sp
        sbc #4
        sta sp
        bcs :+
        dec sp+1
:
        ldy #0
        lda #0
        sta (sp),y
        iny
        lda tmp4
        sta (sp),y
        iny
        sec
        lda #1
        sbc tmp4
        sta (sp),y
        iny
        lda #0
        sbc #0
        sta (sp),y

.macro point xslot, yslot, negative_x, negative_y, fast
        .local skip
        ldy #yslot
        lda (sp),y
        ldy #4
        .if negative_y
        eor #$ff
        sec
        .else
        clc
        .endif
        adc (sp),y
        .if !fast
          .if negative_y
        bcc skip
          .else
        bcs skip
          .endif
        cmp _gfx_height
        bcs skip
        .endif
        sta tmp1
        ldy #xslot
        lda (sp),y
        ldy #5
        .if negative_x
        eor #$ff
        sec
        adc (sp),y
        sta tmp2
        iny
        lda (sp),y
        sbc #0
        .else
        clc
        adc (sp),y
        sta tmp2
        iny
        lda (sp),y
        adc #0
        .endif
        tax
        lda tmp2
        .if fast
        jsr pushax
        lda tmp1
        jsr _gfx_plot
        .else
        jsr plot_clip
        .endif
skip:
.endmacro

.macro outline fast
        .local circle_loop,axis,swap_points,advance_loop,again
circle_loop:
        ldy #0
        lda (sp),y
        beq axis
        point 0,1,0,0,fast
        point 0,1,1,1,fast
axis:
        point 0,1,1,0,fast
        point 0,1,0,1,fast
        ldy #0
        lda (sp),y
        ldy #1
        cmp (sp),y
        bne swap_points
        jmp incsp7
swap_points:
        point 1,0,0,0,fast
        point 1,0,1,0,fast
        ldy #0
        lda (sp),y
        beq advance_loop
        point 1,0,0,1,fast
        point 1,0,1,1,fast
advance_loop:
        jsr advance
        beq again
        bcc again
        jmp incsp7
again:
        jmp circle_loop
.endmacro

        cpx #0
        beq :+
        jmp fast_loop
:       outline 0
fast_loop:
        outline 1

advance:
        ldy #3
        lda (sp),y
        bmi inside
        ldy #0
        lda (sp),y
        ldy #1
        sec
        sbc (sp),y
        asl                     ; x < y: the signed difference has high byte $ff
        sta tmp1
        lda #$ff
        rol
        sta tmp2
        lda (sp),y
        ; ROL of $ff left carry set, so this decrement needs no SEC.
        sbc #1
        sta (sp),y
        ldx #5
        bne delta
inside:
        ldy #0
        lda (sp),y
        asl
        sta tmp1
        lda #0
        rol
        sta tmp2
        ldx #3
delta:
        ; The constant is already in X; add it directly to the low delta.
        txa
        clc
        adc tmp1
        sta tmp1
        lda tmp2
        adc #0
        sta tmp2
        ldy #2
        clc
        lda (sp),y
        adc tmp1
        sta (sp),y
        iny
        lda (sp),y
        adc tmp2
        sta (sp),y
        ldy #0
        clc
        lda (sp),y
        adc #1
        sta (sp),y
        iny
        cmp (sp),y
        rts

; AX=x, tmp1=y; unsigned comparison also rejects a negative x coordinate.
plot_clip:
        cpx _gfx_width+1
        bcc draw
        bne done
        cmp _gfx_width
        bcs done
draw:
        jsr pushax
        lda tmp1
        jmp _gfx_plot
done:
        rts
