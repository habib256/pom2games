; All simulated actions spend integer minutes. Round the total, rather than
; truncating a fractional hour just below its intended minute. The total
; also carries 59 -> 00 into the hour and wraps midnight into 00:00.
.macro display_clock hour, minute
        fld     s_hour
        fop     FMULT, f_60
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     num
        lda     $A0
        sta     num+1
        ldx     #0
@clock_subtract:
        sec
        lda     num
        sbc     #60
        tay
        lda     num+1
        sbc     #0
        bcc     @clock_remainder
        sta     num+1
        sty     num
        inx
        bne     @clock_subtract
@clock_remainder:
        cpx     #24
        bcc     @clock_store
        ldx     #0
@clock_store:  stx     hour
        lda     num
        sta     minute
.endmacro
