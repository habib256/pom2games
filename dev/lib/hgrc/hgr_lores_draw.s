; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Shared, clipped LORES rectangle kernel. The public wrappers consume their
; C arguments and pass x/(width-1) in ptr2, y/bottom-exclusive in tmp3/tmp4,
; and the low-nibble colour in tmp2. All extents are nonempty and visible.
; Whole pairs of block rows become direct byte stores; only the first/last
; unmatched nibble needs a read-modify-write. No new BSS or zero page.
.export hgr_lores_draw
.import _hgr_lores_build, _hgr_lo_rowlo, _hgr_lo_rowhi
.importzp ptr1, ptr2, ptr3, tmp1, tmp2, tmp3, tmp4
.code
hgr_lores_draw:
        jsr _hgr_lores_build    ; internal ABI: only A/X/Y/tmp1 are clobbered
        lda tmp2
        asl a
        asl a
        asl a
        asl a
        ora tmp2
        sta tmp2                ; duplicated colour nibble
row:
        lda tmp3
        lsr a
        tax
        lda _hgr_lo_rowlo,x
        clc
        adc ptr2                ; row low <= $D0, x <= 39: cannot carry
        sta ptr1
        lda _hgr_lo_rowhi,x
        sta ptr1+1
        ldy ptr2+1
        lda tmp3
        lsr a
        bcs upper
        inc tmp3
        lda tmp3
        cmp tmp4
        beq lower
        inc tmp3                ; both nibbles of this text row are covered
        lda tmp2
full:   sta (ptr1),y
        dey
        bpl full
next:   lda tmp3
        cmp tmp4
        bcc row
        rts
upper:  inc tmp3
        lda #$0f                ; preserve upper/even block
        bne partial
lower:  lda #$f0                ; preserve lower/odd block
partial:
        sta tmp1
        eor #$ff
        and tmp2
        sta ptr3                ; replacement nibble
masked: lda (ptr1),y
        and tmp1
        ora ptr3
        sta (ptr1),y
        dey
        bpl masked
        jmp next
