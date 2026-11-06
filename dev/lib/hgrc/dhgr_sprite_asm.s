; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.include "apple2.inc"
.importzp ptr1,ptr2,ptr3,tmp1,tmp2,tmp3,tmp4,aux_read
.import _dhgr_sprite_mask,dhgr_block_setup
.export _dhgr_sprite_asm
.code
; Partial bytes: dst=(dst & (mask|$80)) | (data & (~mask & $7F)).
; A fully opaque byte stores data&$7F without reading its old palette bit.
; All shared parameters stay intact; A/X/Y, ptr1..ptr3/tmp1..tmp4 are scratch.
; IRQ I is preserved and masked for the row. Count zero means 256; raw bank
; values >=2 keep the historical auxiliary-only, fixed-screen-address path.
.macro MASKED_BYTE bank
        .local next,write
        ldy tmp1
        lda (ptr3),y
        ora #$80
        sta tmp3                ; keep mask, preserving the palette bit
        eor #$FF                ; write mask is exactly (~raw)&$7F
        beq next
        and (ptr2),y
        sta tmp4
        ldy #0
        lda tmp3
        cmp #$80
        beq write
.if bank
        jsr aux_read
.else
        lda (ptr1),y
.endif
        and tmp3
        ora tmp4
        sta tmp4
write:
.if bank
        sta RAMWRTON
.endif
        lda tmp4
        sta (ptr1),y
.if bank
        sta RAMWRTOFF
.endif
next:
.endmacro
_dhgr_sprite_asm:
        php
        sei
        jsr dhgr_block_setup
        lda _dhgr_sprite_mask
        sta ptr3
        lda _dhgr_sprite_mask+1
        sta ptr3+1
        sty tmp1
        txa
        bne aux
        inx
        bne main
aux:
        MASKED_BYTE 1
        inc tmp1
        dec tmp2
        beq done
        cpx #1
        bne aux
main:
        MASKED_BYTE 0
        inc tmp1
        inc ptr1
        bne :+
        inc ptr1+1
:       dec tmp2
        bne aux
done:
        plp
        rts
