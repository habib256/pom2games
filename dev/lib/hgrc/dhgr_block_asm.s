; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.include "apple2.inc"
.importzp ptr1,ptr2,tmp2,aux_read
.import dhgr_block_setup
.export _dhgr_read_block_asm,_dhgr_write_block_asm
.code
; Read/write row kernels preserve every shared parameter global.
; The block controller retains count and bank between rows; all imported
; scratch and A/X/Y are volatile. IRQ I is preserved, masked for the row.
; Raw count zero means 256; raw bank values >=2 stay auxiliary throughout.
_dhgr_write_block_asm:
        php
        sei
        jsr dhgr_block_setup
        txa
        bne @aux
        inx                     ; valid starts use the aux/main alternating loop
        bne @main
@aux:
        lda (ptr2),y
        and #$7F
        sta RAMWRTON
        sta (ptr1),y
        sta RAMWRTOFF
        inc ptr2
        bne :+
        inc ptr2+1
:       dec tmp2
        beq @done
        cpx #1                  ; raw bank values >=2 historically stay auxiliary
        bne @aux
@main:
        lda (ptr2),y
        and #$7F
        sta (ptr1),y
        inc ptr2
        bne :+
        inc ptr2+1
:       inc ptr1
        bne :+
        inc ptr1+1
:       dec tmp2
        bne @aux
@done:
        plp
        rts
_dhgr_read_block_asm:
        php
        sei
        jsr dhgr_block_setup
        txa
        bne @aux
        inx
        bne @main
@aux:
        jsr aux_read
        and #$7F
        sta (ptr2),y
        inc ptr2
        bne :+
        inc ptr2+1
:       dec tmp2
        beq @done
        cpx #1
        bne @aux
@main:
        lda (ptr1),y
        and #$7F
        sta (ptr2),y
        inc ptr2
        bne :+
        inc ptr2+1
:       inc ptr1
        bne :+
        inc ptr1+1
:       dec tmp2
        bne @aux
@done:
        plp
        rts
