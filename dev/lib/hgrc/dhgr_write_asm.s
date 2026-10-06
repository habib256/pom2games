; VERHILLE Arnaud — GPL-3.0. Bank-safe optional DHGR access.
.include "apple2.inc"
RAMWRTON = $C005
.code
.export _dhgr_write_asm
.import _dhgr_aux, _dhgr_mask, _dhgr_bits, dhgr_select, dhgr_read_byte
.importzp ptr1, tmp1
_dhgr_write_asm:
        php
        sei
        jsr dhgr_select
        lda _dhgr_mask
        cmp #$7F
        beq @whole
        jsr dhgr_read_byte
        sta tmp1
        lda _dhgr_mask
        eor #$FF
        and tmp1
        ora _dhgr_bits
        jmp @write
@whole: lda _dhgr_bits
@write: sta tmp1
        lda _dhgr_aux
        beq @main
        sta RAMWRTON
@main:  lda tmp1
        sta (ptr1),y
        sta RAMWRTOFF
        plp
        rts
