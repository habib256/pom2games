; VERHILLE Arnaud — GPL-3.0. DHGR 560x192 point through the row and cell
; tables: no division. IRQs are masked only around the banked byte access;
; auxiliary reads use the zero-page trampoline, writes RAMWRT (dhgr_asm.s).
.include "apple2.inc"
RAMWRTON = $C005
.export _dhgr_plot, dhgr_locate
.import _dhgr_base, dhgr_rowlo, dhgr_rowhi, _dhgr_cellbyte, _dhgr_cellphase
.import incsp3
.importzp sp, ptr1, tmp1, tmp2, tmp3, aux_read
.rodata
; Cell phase + (x & 3) = 0..9; bits 7..9 are bits 0..2 of the next byte.
bitmask: .byte 1,2,4,8,16,32,64,1,2,4
.code
; In: A/X = x, Y = y. Out: C=1 off-screen. Otherwise C=0, A = tmp2 = mask,
; X = 1 main / 0 aux, Y = page column, ptr1 = draw-page scanline; tmp1 used.
dhgr_locate:
        cpy #192
        bcs @out
        cpx #2
        bcc @in
        bne @out                ; C=1
        cmp #<560
        bcs @out
@in:    sta tmp1
        and #3
        sta tmp2
        lda dhgr_rowlo,y
        sta ptr1
        lda dhgr_rowhi,y
        ora _dhgr_base
        sta ptr1+1
        txa
        lsr
        ror tmp1
        lsr
        ror tmp1
        ldx tmp1                ; x >> 2: color cell 0..139
        lda _dhgr_cellphase,x
        clc
        adc tmp2
        tay
        lda bitmask,y
        sta tmp2
        cpy #7                  ; C = the bit lies in the next byte
        lda _dhgr_cellbyte,x
        adc #0
        lsr                     ; C = odd byte = main bank
        tay
        lda #0
        rol
        tax
        lda tmp2                ; C=0
@out:   rts

; void dhgr_plot(unsigned x, unsigned char y, unsigned char set)
_dhgr_plot:
        sta tmp3
        ldy #2
        lda (sp),y
        tax
        dey
        lda (sp),y
        pha
        dey
        lda (sp),y
        tay
        pla
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
        jmp incsp3
@main:  lda (ptr1),y
        and tmp1
        ora tmp3
        sta (ptr1),y
        plp
@done:  jmp incsp3
