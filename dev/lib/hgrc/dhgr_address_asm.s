; VERHILLE Arnaud — GPL-3.0. Interleaved byte coordinate -> bank address.
.export _dhgr_byte_address
.import _dhgr_addr, _dhgr_aux, _dhgr_base, dhgr_rowlo, dhgr_rowhi, incsp1
.importzp sp
.code
; void dhgr_byte_address(unsigned char bx, unsigned char y): auxiliary
; first, then main, across 80 bytes. Sets dhgr_addr and dhgr_aux.
_dhgr_byte_address:
        tax
        ldy #0
        lda (sp),y
        lsr                     ; C = odd = main
        tay
        lda #0
        rol
        eor #1
        sta _dhgr_aux
        tya
        clc
        adc dhgr_rowlo,x        ; row offsets end at $F7: no carry
        sta _dhgr_addr
        lda dhgr_rowhi,x
        ora _dhgr_base
        sta _dhgr_addr+1
        jmp incsp1
