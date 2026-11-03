; VERHILLE Arnaud — GPL-3.0. Bank-safe optional DHGR primitive.
; Both banks of the draw page (8 KB each, holes included) take
; dhgr_pattern[]: a page of 256 bytes is two passes (even bytes, odd bytes)
; of one pattern byte through eight absolute stores, 5 cycles a byte.
; The page operand of those stores is patched while RAMWRT is main (a
; write under RAMWRTON would reach the auxiliary copy of this code), then
; the bank is selected for the passes alone. IRQs are masked one page at
; a time (about 1,750 cycles), not for the whole clear.
.include "apple2.inc"
.code
.export _dhgr_clear_asm
.import _dhgr_base, _dhgr_pattern
.importzp ptr1, tmp1
_dhgr_clear_asm:
        ldx #0                  ; aux bank: patterns 0 (even) and 2 (odd)
        jsr fill_bank
        ldx #1                  ; main bank: patterns 1 and 3
fill_bank:
        stx tmp1
        lda _dhgr_base
        sta ptr1                ; current page, $20..$3F or $40..$5F
@page:  lda ptr1
        ldx #21                 ; the eight operands, three bytes apart
@patch: sta store+2,x
        dex
        dex
        dex
        bpl @patch
        php
        sei
        ldx tmp1
        bne @bank
        sta RAMWRTON
@bank:  lda _dhgr_pattern,x
        ldy #0
        jsr fill_page
        ldx tmp1
        lda _dhgr_pattern+2,x
        ldy #1
        jsr fill_page
        sta RAMWRTOFF
        plp
        inc ptr1
        lda ptr1
        and #$1F                ; 0 again past the bank's 32 pages
        bne @page
        rts
; Bytes Y, Y+2, ... Y+254 of the patched page take A.
fill_page:
store:  sta $FF00,y
        sta $FF20,y
        sta $FF40,y
        sta $FF60,y
        sta $FF80,y
        sta $FFA0,y
        sta $FFC0,y
        sta $FFE0,y
        iny
        iny
        cpy #32
        bcc store
        rts
