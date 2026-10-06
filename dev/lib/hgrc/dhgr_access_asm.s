; VERHILLE Arnaud — GPL-3.0. Bank-safe optional DHGR access.
.include "apple2.inc"
RAMWRTON = $C005
.code
.export dhgr_select, dhgr_read_byte
.import _dhgr_addr, _dhgr_aux
.importzp ptr1, aux_read
dhgr_select:
        lda _dhgr_addr
        sta ptr1
        lda _dhgr_addr+1
        sta ptr1+1
        ldy #0
        rts
dhgr_read_byte:
        lda _dhgr_aux
        beq @main
        jmp aux_read
@main:  lda (ptr1),y
        rts
