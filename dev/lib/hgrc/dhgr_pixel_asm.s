; VERHILLE Arnaud — GPL-3.0. DHGR 560x192 point write.
; IRQs are masked only around banked access; aux reads use the trampoline.
.include "apple2.inc"
.export _dhgr_plot
.import dhgr_locate
.importzp sp, ptr1, tmp1, tmp2, tmp3, aux_read
.code
; void dhgr_plot(unsigned x, unsigned char y, unsigned char set)
_dhgr_plot:
        sta tmp3
        ldy #2
        lda (sp),y
        tax
        dey
        lda (sp),y
        sta tmp1
        dey
        lda (sp),y
        tay
        lda tmp1
        jsr dhgr_locate
        bcs @done
        eor #$FF
        sta tmp1                ; bits kept
        lda tmp3
        beq @bits
        lda tmp2
@bits:  sta tmp3                ; bits set
        php
        sei
        txa
        bne @main
        jsr aux_read
        and tmp1
        ora tmp3
        sta RAMWRTON
        sta (ptr1),y
        sta RAMWRTOFF
        plp
        jmp @done
@main:  lda (ptr1),y
        and tmp1
        ora tmp3
        sta (ptr1),y
        plp
@done:  lda sp
        clc
        adc #3
        sta sp
        bcc :+
        inc sp+1
:       rts
