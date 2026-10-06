; VERHILLE Arnaud — GPL-3.0. Bank-safe optional DHGR primitive.
.include "apple2.inc"
RAMWRTON = $C005
.code
.export _dhgr_span_asm
.import _dhgr_addr, _dhgr_pattern
.import _dhgr_first, _dhgr_last, _dhgr_first_mask, _dhgr_last_mask
.importzp ptr1, tmp1, tmp2, tmp3, tmp4, aux_read
; One scanline, interleaved byte indices first..last. Full bytes use stores,
; only the two edges read/modify/write. IRQ masking covers one row.
_dhgr_span_asm:
        php
        sei
        lda _dhgr_addr
        sta ptr1
        lda _dhgr_addr+1
        sta ptr1+1
        lda _dhgr_first
        sta tmp2
@byte:  lda #$7F
        sta tmp3
        lda tmp2
        cmp _dhgr_first
        bne @last
        lda _dhgr_first_mask
        sta tmp3
@last:  lda tmp2
        cmp _dhgr_last
        bne @pattern
        lda _dhgr_last_mask
        and tmp3
        sta tmp3
@pattern:
        lda tmp2
        and #3
        tax
        lda _dhgr_pattern,x
        and tmp3
        sta tmp4
        lda tmp2
        lsr
        tay
        lda tmp3
        cmp #$7F
        beq @value
        lda tmp2
        and #1
        bne @read_main
        jsr aux_read
        jmp @merge
@read_main:
        lda (ptr1),y
@merge: sta tmp1
        lda tmp3
        eor #$FF
        and tmp1
        ora tmp4
        sta tmp4
@value: lda tmp2
        and #1
        bne @write_main
        sta RAMWRTON
@write_main:
        lda tmp4
        sta (ptr1),y
        sta RAMWRTOFF
        lda tmp2
        cmp _dhgr_last
        beq @done
        inc tmp2
        jmp @byte
@done:  plp
        rts
