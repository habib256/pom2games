; VERHILLE Arnaud — GPL-3.0. Bounded DHGR visible-row clear.
; Inputs: dhgr_addr in main RAM, dhgr_pattern[aux even/main even/aux odd/main odd].
; Main code/ZP/stack, ROM visible, ALTZP/80STORE/RAMRD/RAMWRT off.
; Writes 40 bytes in each bank, preserves holes and display. IRQ I preserved.
; A/X/Y, ptr1,tmp1,tmp2 destroyed; non-reentrant; <1300 masked cycles/row.
.include "apple2.inc"
RAMWRTON = $C005
.export _dhgr_clear_row_asm
.import _dhgr_addr, _dhgr_pattern
.importzp ptr1, tmp1, tmp2
.code
_dhgr_clear_row_asm:
        php
        sei
        lda _dhgr_addr
        sta ptr1
        lda _dhgr_addr+1
        sta ptr1+1
        lda _dhgr_pattern
        sta tmp1
        lda _dhgr_pattern+2
        sta tmp2
        sta RAMWRTON
        jsr fill_row
        sta RAMWRTOFF
        lda _dhgr_pattern+1
        sta tmp1
        lda _dhgr_pattern+3
        sta tmp2
        jsr fill_row
        plp
        rts
fill_row:
        ldy #0
@pair:
        lda tmp1
        sta (ptr1),y
        iny
        lda tmp2
        sta (ptr1),y
        iny
        cpy #40
        bne @pair
        rts
