; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; unsigned char gfx_hexstr(char *buf, unsigned value), cc65 fastcall.
; Uppercase, no leading zeroes, NUL terminated; zero emits "0".
; Returns length in A, X=0. D=0; standard cc65 scratch, no private ZP/BSS.
; Leaves ptr1 at the buffer start, reused by the native hgr_putx entry.
; Skip an empty high byte, then share the two-nibble conversion. The upper
; nibble is omitted only before the first digit. No table or 16-bit shifts.
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
        lda tmp2
        beq low_byte
        jsr byte
low_byte:
        lda tmp1
        jsr byte
        lda #0
        sta (ptr1),y
        tya
        ldx #0
        rts
byte:
        sta tmp2
        lsr a
        lsr a
        lsr a
        lsr a
        bne emit
        cpy #0
        beq low_nibble
emit:
        jsr nibble
low_nibble:
        lda tmp2
        and #$0f
nibble:
        cmp #10
        bcc decimal
        adc #6                  ; C=1: map 10..15 to 17..22
decimal:
        adc #'0'                ; both paths have C=0 (ADC #6 cannot carry)
        sta (ptr1),y
        iny
        rts
