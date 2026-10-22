; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; =============================================
; hgr_div7_ram.asm - x / 7 and x mod 7 for x = 0..255, built at start
; =============================================
; hgr_div7[x] = x / 7 (byte column), hgr_mod7[x] = x mod 7 (bit phase): the
; 512 bytes go in BSS instead of the file, and hgr_div7_init (28 bytes, in
; the current segment) fills them once, ~6 000 cycles. Like
; hgr_scanline_ram.asm for the row tables. Clobbers A, X, Y.
; Usage: .include "hgr_div7_ram.asm" (any segment), JSR hgr_div7_init before
; the first lookup. hgr_xor.asm takes them as HGR_XOR_DIV7/MOD7.
; (hgr_line.asm's HGR_LINE_DIV7/MOD7 are 32-byte tables of another kind.)
; =============================================

.ifndef _HGR_DIV7_RAM_LOADED_
_HGR_DIV7_RAM_LOADED_ = 1

.pushseg
.segment "BSS"
hgr_div7: .res 256
hgr_mod7: .res 256
.popseg

hgr_div7_init:
        LDX     #0
        LDY     #0                      ; x mod 7
        TXA                             ; x / 7
@x:     STA     hgr_div7,X
        PHA
        TYA
        STA     hgr_mod7,X
        PLA
        INY
        CPY     #7
        BCC     @next
        LDY     #0
        ADC     #0                      ; C = 1: next column
@next:  INX
        BNE     @x
        RTS

.endif
