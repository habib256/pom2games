; VERHILLE Arnaud — GPL-3.0. Bounded DHGR visible-row clear.
; Inputs: dhgr_addr in main RAM, dhgr_pattern[aux even/main even/aux odd/main odd].
; Main code/ZP/stack, ROM visible, ALTZP/80STORE/RAMRD/RAMWRT off.
; Writes 40 bytes in each bank, preserves holes and display. IRQ I preserved.
; A/X/Y, ptr1 low destroyed; non-reentrant; about 700 masked cycles a row.
; A row never crosses a page and its offset in the page is at most $D0, so
; the kernel stores through five page-aligned operands (offsets 0, 8, 16, 24
; and 32), Y walking the row's 40 bytes two by two: one pass per pattern byte,
; five cycles a byte. Only the page byte of those operands is patched, while
; RAMWRT is main (under RAMWRTON the write would reach the auxiliary copy
; of this code).
.include "apple2.inc"
.export _dhgr_clear_row_asm, _dhgr_clear_rows_asm
.import _dhgr_addr, _dhgr_pattern, _dhgr_base, dhgr_rowlo, dhgr_rowhi
.importzp ptr1, tmp3, tmp4
.code
; void __fastcall__ dhgr_clear_rows_asm(unsigned rows_y): rows (>=1, clipped)
; in the high byte, first row in the low byte, on the draw page; the row
; kernel below without dhgr_addr. tmp3/tmp4 destroyed too.
_dhgr_clear_rows_asm:
        sta tmp4
        stx tmp3
@row:   ldy tmp4
        lda dhgr_rowlo,y
        sta ptr1
        lda dhgr_rowhi,y
        ora _dhgr_base
        jsr clear_row
        inc tmp4
        dec tmp3
        bne @row
        rts
_dhgr_clear_row_asm:
        lda _dhgr_addr
        sta ptr1
        lda _dhgr_addr+1
; A = row page byte, ptr1 low = row offset. No high-byte scratch needed.
clear_row:
        sta store+2
        sta store+5
        sta store+8
        sta store+11
        sta store+14
        php
        sei
        sta RAMWRTON
        lda _dhgr_pattern
        ldy ptr1
        jsr fill_half
        lda _dhgr_pattern+2
        ldy ptr1
        iny
        jsr fill_half
        sta RAMWRTOFF
        lda _dhgr_pattern+1
        ldy ptr1
        jsr fill_half
        lda _dhgr_pattern+3
        ldy ptr1
        iny
        jsr fill_half
        plp
        rts
; Bytes Y, Y+2, ... Y+38 of the row take A (Y = row offset, or one more).
fill_half:
        ldx #4                  ; four turns, independent of row/column parity
store:  sta $FF00,y
        sta $FF08,y
        sta $FF10,y
        sta $FF18,y
        sta $FF20,y
        iny
        iny
        dex
        bne store
        rts
