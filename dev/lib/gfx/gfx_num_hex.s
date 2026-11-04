; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; unsigned char gfx_hexstr(char *buf, unsigned value), cc65 fastcall.
; Uppercase, no leading zeroes, NUL terminated; zero emits "0".
; Returns length in A, X=0. D=0; standard cc65 scratch, no private ZP/BSS.
; Leaves ptr1 at the buffer start, reused by the native hgr_putx entry.
; X=4,3 selects the high byte; X=2,1 the low byte. Even X extracts the
; upper nibble, odd X the lower. No 16-bit shifts or conversion lookup table.
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
        txa
        lsr a                   ; odd digit index selects the low nibble
        lda tmp2
        bcs low_nibble
        lsr a
        lsr a
        lsr a
        lsr a
low_nibble:
        and #$0f
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
        adc #'0'                ; both paths have C=0 (ADC #6 cannot carry)
        sta (ptr1),y
        iny
next:
        dex
        beq done
        cpx #2
        bne digit
        lda tmp1                ; switch bytes once, after the high-byte pair
        sta tmp2
        jmp digit
done:
        lda #0
        sta (ptr1),y
        tya                     ; X is already zero
        rts
