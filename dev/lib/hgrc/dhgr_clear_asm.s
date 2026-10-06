; VERHILLE Arnaud — GPL-3.0. Bank-safe optional DHGR primitive.
.include "apple2.inc"
RAMWRTON = $C005
.code
.export _dhgr_clear_asm
.import _dhgr_base, _dhgr_pattern
.importzp ptr1, tmp1, tmp2
_dhgr_clear_asm:
        php
        sei
        sta RAMWRTON
        lda _dhgr_pattern
        sta tmp1
        lda _dhgr_pattern+2
        sta tmp2
        jsr fill_bank
        sta RAMWRTOFF
        lda _dhgr_pattern+1
        sta tmp1
        lda _dhgr_pattern+3
        sta tmp2
        jsr fill_bank
        plp
        rts
fill_bank:
        lda _dhgr_base
        sta ptr1+1
        clc
        adc #$20
        tax
        ldy #0
        sty ptr1
@pair:  lda tmp1
        sta (ptr1),y
        iny
        lda tmp2
        sta (ptr1),y
        iny
        bne @pair
        inc ptr1+1
        cpx ptr1+1
        bne @pair
        rts
