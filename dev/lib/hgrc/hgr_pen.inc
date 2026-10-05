; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Private pen advance; included by text16 and bitmap kernels.
advance:
        asl curmask          ; 1,2,4,...,64 -> 2,4,...,128
        lda curmask
        cmp #$80             ; was the column's last (bit 6) pixel just passed?
        bne @done
        lda #$01             ; wrap: back to bit 0 of the next byte column
        sta curmask
        inc curcol
@done:
        rts
