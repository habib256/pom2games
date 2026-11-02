; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; unsigned char gfx_hexstr(char *buf, unsigned value), cc65 fastcall.
; Uppercase, no leading zeroes, NUL terminated; zero emits "0".
; Returns length in A, X=0. D=0; standard cc65 scratch, no private ZP/BSS.
.export _gfx_hexstr
.import popax
.importzp ptr1, tmp1, tmp2
.code
_gfx_hexstr:
        sta tmp1
        stx tmp2
        jsr popax
        sta ptr1
        stx ptr1+1
        ldy #0
        ldx #4
digit:
        lda tmp2
        lsr a
        lsr a
        lsr a
        lsr a
        bne emit
        cpy #0
        bne emit
        cpx #1
        bne next
emit:
        cmp #10
        bcc decimal
        adc #6                  ; C=1: map 10..15 to 17..22
decimal:
        clc
        adc #'0'
        sta (ptr1),y
        iny
next:
        dex
        beq done
        .repeat 4
        asl tmp1
        rol tmp2
        .endrepeat
        jmp digit
done:
        lda #0
        sta (ptr1),y
        tya                     ; X is already zero
        rts
