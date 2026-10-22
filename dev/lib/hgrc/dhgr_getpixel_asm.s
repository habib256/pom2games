; VERHILLE Arnaud — GPL-3.0. DHGR 560x192 readback; off-screen reads 0.
.export _dhgr_getpixel
.import dhgr_locate, incsp2
.importzp sp, ptr1, tmp2, aux_read
.code
; unsigned char dhgr_getpixel(unsigned x, unsigned char y)
_dhgr_getpixel:
        pha
        ldy #1
        lda (sp),y
        tax
        dey
        lda (sp),y
        sta tmp2
        pla
        tay
        lda tmp2
        jsr dhgr_locate
        bcs @zero
        php
        sei
        txa
        bne @main
        jsr aux_read
        jmp @read
@main:  lda (ptr1),y
@read:  plp
        and tmp2
        beq @zero
        lda #1
        .byte $2C               ; BIT abs: skip the zero
@zero:  lda #0
        ldx #0
        jmp incsp2
