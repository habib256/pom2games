; VERHILLE Arnaud — GPL-3.0. Shared DHGR point address, bank and mask.
.include "dhgr_pixel_address.inc"
.export dhgr_locate
.import _dhgr_base, dhgr_rowlo, dhgr_rowhi, _dhgr_cellbyte, _dhgr_cellphase
.importzp ptr1, tmp1, tmp2
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
        dhgr_scanline_address
        sta ptr1+1
        dhgr_pixel_cell_phase
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

