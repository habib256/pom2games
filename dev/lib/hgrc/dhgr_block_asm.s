; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.include "apple2.inc"
RAMWRTON = $C005
.importzp ptr1, ptr2, ptr3, tmp1, tmp2, tmp3, tmp4, aux_read
.import _dhgr_addr, _dhgr_aux, _dhgr_buffer, _dhgr_count, _dhgr_sprite_mask
.export _dhgr_read_block_asm, _dhgr_write_block_asm, _dhgr_sprite_asm
.segment "CODE"
select:
        lda _dhgr_addr
        sta ptr1
        lda _dhgr_addr+1
        sta ptr1+1
        ldy #0
        rts

block_setup:
        jsr select
        lda _dhgr_buffer
        sta ptr2
        lda _dhgr_buffer+1
        sta ptr2+1
        lda _dhgr_count
        sta tmp2
        ldx _dhgr_aux
        rts
; Inline the per-byte advance to avoid a JSR/RTS pair for every byte.
; DEC must remain last: its Z flag controls each caller's row loop.
.macro BLOCK_NEXT
        .local @buffer_ok, @same_address
        inc ptr2
        bne @buffer_ok
        inc ptr2+1
@buffer_ok:
        cpx #0
        bne @same_address
        inc ptr1
        bne @same_address
        inc ptr1+1
@same_address:
        txa
        eor #1
        tax
        dec tmp2
.endmacro
_dhgr_write_block_asm:
        php
        sei
        jsr block_setup
@byte:  lda (ptr2),y
        and #$7F
        ; CPX and the bank-switch STA preserve the byte already in A.
        cpx #0
        beq @main
        sta RAMWRTON
@main:  sta (ptr1),y
        sta RAMWRTOFF
        BLOCK_NEXT
        bne @byte
        plp
        rts
_dhgr_read_block_asm:
        php
        sei
        jsr block_setup
@byte:  cpx #0
        beq @main
        jsr aux_read
        jmp @store
@main:  lda (ptr1),y
@store: and #$7F
        sta (ptr2),y
        BLOCK_NEXT
        bne @byte
        plp
        rts

_dhgr_sprite_asm:
        php
        sei
        jsr block_setup
        lda _dhgr_sprite_mask
        sta ptr3
        lda _dhgr_sprite_mask+1
        sta ptr3+1
@byte:  lda (ptr3),y
        eor #$FF
        and #$7F
        beq @next
        sta tmp3
        lda (ptr2),y
        and tmp3
        sta tmp4
        lda tmp3
        cmp #$7F
        beq @write
        cpx #0
        beq @read_main
        jsr aux_read
        jmp @merge
@read_main:
        lda (ptr1),y
@merge: sta tmp1
        lda tmp3
        eor #$FF
        and tmp1
        ora tmp4
        sta tmp4
@write: cpx #0
        beq @write_main
        sta RAMWRTON
@write_main:
        lda tmp4
        sta (ptr1),y
        sta RAMWRTOFF
@next:  inc ptr3
        bne @mask_ok
        inc ptr3+1
@mask_ok:
        BLOCK_NEXT
        bne @byte
        plp
        rts
