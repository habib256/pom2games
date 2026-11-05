; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Private ellipse scaling: radius=0..32767 on stack, signed coefficient
; -64..64 in A. Return sign(c)*floor(radius*abs(c)/64) in AX.
; Six low-to-high coefficient bits: acc=(acc+bit*radius)>>1. Each addition
; is at most 65534, so a 16-bit accumulator is sufficient without overflow.
.export _gfx_ellipse_offset
.import incsp2
.importzp sp, ptr1, tmp1, tmp2, tmp3
.code
_gfx_ellipse_offset:
        sta tmp3
        ldy #0
        lda (sp),y
        sta ptr1
        iny
        lda (sp),y
        sta ptr1+1
        ora ptr1
        beq zero
        lda tmp3
        bpl magnitude
        eor #$ff
        clc
        adc #1
magnitude:
        beq zero
        cmp #64
        beq whole
        sta tmp2
        lda #0
        sta tmp1
        ldy #6
multiply:
        lsr tmp2
        bcc halve
        tax
        lda tmp1
        clc
        adc ptr1
        sta tmp1
        txa
        adc ptr1+1
halve:
        lsr
        ror tmp1
        dey
        bne multiply
        tax
        lda tmp1
        jmp sign
whole:
        lda ptr1
        ldx ptr1+1
sign:
        bit tmp3
        bpl done
        sta tmp1
        stx tmp2
        sec
        lda #0
        sbc tmp1
        sta tmp1
        lda #0
        sbc tmp2
        tax
        lda tmp1
done:
        jmp incsp2
zero:
        lda #0
        tax
        jmp incsp2
