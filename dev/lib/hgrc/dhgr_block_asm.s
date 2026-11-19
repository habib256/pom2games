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
.macro write_byte auxiliary
        lda (ptr2),y
        and #$7F
        .if auxiliary
        sta RAMWRTON
        .endif
        sta (ptr1),y
        .if auxiliary
        sta RAMWRTOFF
        .endif
.endmacro

.macro read_byte auxiliary
        .if auxiliary
        jsr aux_read
        .else
        lda (ptr1),y
        .endif
        and #$7F
        sta (ptr2),y
.endmacro

; The buffer advances every byte, the screen address only after a main byte.
.macro transfer_row transfer_byte
        php
        sei
        jsr dhgr_block_setup
        txa
        bne @aux
        inx                     ; valid starts use the aux/main alternating loop
        bne @main
@aux:
        transfer_byte 1
        inc ptr2
        bne :+
        inc ptr2+1
:       dec tmp2
        beq @done
        cpx #1                  ; raw bank values >=2 historically stay auxiliary
        bne @aux
@main:
        transfer_byte 0
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
.endmacro

_dhgr_write_block_asm:
        transfer_row write_byte
_dhgr_read_block_asm:
        transfer_row read_byte
