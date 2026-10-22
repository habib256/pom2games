; VERHILLE Arnaud — GPL-3.0. One 140x192 color pixel: four bits of the
; color's byte pattern, in one byte or across an aux/main pair. Off-screen
; pixels are ignored. IRQs are masked only around auxiliary accesses.
.include "apple2.inc"
RAMWRTON = $C005
.export _dhgr_plot_color, _dhgr_color_dot, _dhgr_dot_x, _dhgr_dot_color
.import _dhgr_base, dhgr_rowlo, dhgr_rowhi, _dhgr_cellbyte, _dhgr_cellphase
.import dhgr_color_patterns, incsp2
.importzp sp, ptr1, ptr2, tmp1, tmp2, tmp3, tmp4, aux_read
.bss
_dhgr_dot_x: .res 1             ; dhgr_color_dot inputs (gfx color backend)
_dhgr_dot_color: .res 1         ; its pen, 0..15
.rodata
; Bits of the four-bit cell at phase 0..6 in its first and second byte.
low_mask:
.repeat 7,P
.byte ($0F<<P)&$7F
.endrepeat
high_mask:
.repeat 7,P
.byte ($0F<<P)>>7
.endrepeat
.code
; void dhgr_plot_color(unsigned char x, unsigned char y, unsigned char color)
_dhgr_plot_color:
        and #15
        asl
        asl
        sta tmp3
        ldy #1
        lda (sp),y
        tax
        dey
        lda (sp),y
        tay
        jsr plot
        jmp incsp2

; void __fastcall__ dhgr_color_dot(unsigned char y): at dhgr_dot_x, pen
; dhgr_dot_color (unmasked, 0..15).
_dhgr_color_dot:
        tay
        lda _dhgr_dot_color
        asl
        asl
        sta tmp3
        ldx _dhgr_dot_x
; X = x, Y = y, tmp3 = color*4. A/X/Y, ptr1, ptr2, tmp1-tmp4 destroyed.
plot:   cpx #140
        bcs @out
        cpy #192
        bcs @out
        lda dhgr_rowlo,y
        sta ptr1
        lda dhgr_rowhi,y
        ora _dhgr_base
        sta ptr1+1
        lda _dhgr_cellbyte,x
        sta tmp1
        lda _dhgr_cellphase,x
        sta ptr2
        tax
        lda low_mask,x
        jsr put
        ldx ptr2
        cpx #4
        bcc @out
        inc tmp1
        lda high_mask,x
        jmp put
@out:   rts

; Byte tmp1 (interleaved 0..79), mask A, color tmp3: merge the pattern bits.
put:    sta tmp2
        lda tmp1
        and #3
        ora tmp3
        tax
        lda dhgr_color_patterns,x
        and tmp2
        sta tmp4
        lda tmp2
        eor #$FF
        sta tmp2
        lda tmp1
        lsr                     ; C = main
        tay
        bcs @main
        php
        sei
        jsr aux_read
        and tmp2
        ora tmp4
        sta RAMWRTON
        sta (ptr1),y
        sta RAMWRTOFF
        plp
        rts
@main:  lda (ptr1),y
        and tmp2
        ora tmp4
        sta (ptr1),y
        rts
