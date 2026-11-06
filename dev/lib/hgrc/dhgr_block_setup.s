; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export dhgr_block_setup
.import _dhgr_addr,_dhgr_buffer,_dhgr_count,_dhgr_aux
.importzp ptr1,ptr2,tmp2
.code
; Private setup shared by transfer and masked-sprite archive members.
; Shared parameter globals remain intact. ptr1/ptr2, tmp2 and A/X/Y are
; scratch: Y=0, X=initial bank, tmp2=raw count (zero means 256).
dhgr_block_setup:
        lda _dhgr_addr
        sta ptr1
        lda _dhgr_addr+1
        sta ptr1+1
        ldy #0
        lda _dhgr_buffer
        sta ptr2
        lda _dhgr_buffer+1
        sta ptr2+1
        lda _dhgr_count
        sta tmp2
        ldx _dhgr_aux
        rts
