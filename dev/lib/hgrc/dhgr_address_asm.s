; VERHILLE Arnaud — GPL-3.0. Interleaved byte coordinate -> bank address.
.include "dhgr_transfer_row.inc"
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
        dhgr_select_byte_bank
        tya
        dhgr_set_row_address
        jmp incsp1
