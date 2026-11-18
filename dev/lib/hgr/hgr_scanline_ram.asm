; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; =============================================
; hgr_scanline_ram.asm - hgr_lo / hgr_hi built at start (no data in the file)
; =============================================
; The same tables as hgr_scanline.inc, for a program short of space: the
; 384 bytes go in the RAM segment HGR_SCANLINE_SEGMENT (BSS-like, e.g. the
; unused $0200 page), and hgr_scanline_init (~50 bytes, in the current
; segment: boot code that may be overwritten later) fills them once:
;   addr[y] = $2000 + (y%8)*$0400 + ((y/8)%8)*$80 + (y/64)*$28
; Usage:
;   .define HGR_SCANLINE_SEGMENT "SYSBSS"   ; before the include
;   .segment "INIT"
;   .include "hgr_scanline_ram.asm"
;   ...     JSR hgr_scanline_init          ; before any drawing
; Clobbers A, X, Y.
; Options: hgr_lo (and hgr_hi) defined before the include: the caller's own
; tables, no HGR_SCANLINE_SEGMENT needed. HGR_SCANLINE_HI2 = 1: the same
; loop also fills hgr_hi2 (page 2's high bytes, hgr_pages.asm's table or the
; caller's): +9 bytes here, and no hgr_pages_init to keep in resident code.
; =============================================

.ifndef _HGR_SCANLINE_RAM_LOADED_
_HGR_SCANLINE_RAM_LOADED_ = 1

.ifndef HGR_SCANLINE_HI2
HGR_SCANLINE_HI2 = 0
.endif
.ifndef hgr_lo
.pushseg
.segment HGR_SCANLINE_SEGMENT
hgr_lo: .res 192
hgr_hi: .res 192
.popseg
.endif

hgr_scanline_init:
        LDX     #0
@y:     TXA                             ; hi = $20 + (y%8)*4 + (y/8%8)/2
        AND     #7
        ASL     A
        ASL     A
        ORA     #$20
        STA     hgr_hi,X
        TXA
        LSR     A
        LSR     A
        LSR     A
        TAY                             ; Y = y/8
        AND     #7
        LSR     A                       ; C = (y/8%8) & 1: $80 in lo
        ORA     hgr_hi,X
        STA     hgr_hi,X
        LDA     #0
        ROR     A
        STA     hgr_lo,X
        TYA                             ; + (y/64) * $28
        LSR     A
        LSR     A
        LSR     A
        TAY
        LDA     hgr_lo,X
        CLC
        ADC     hgr_sl_third,Y
        STA     hgr_lo,X
.if HGR_SCANLINE_HI2
        LDA     hgr_hi,X                ; page 2: + $2000
        CLC
        ADC     #$20
        STA     hgr_hi2,X
.endif
        INX
        CPX     #192
        BNE     @y
        RTS
hgr_sl_third: .byte $00, $28, $50

.endif
