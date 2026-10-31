; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; plot.inc -- monochrome HGR lines that remember what they lit
; ============================================================================
; Moving thin shapes over a fixed backdrop (the floor, a hill): each pixel
; plotted sets only bits that were dark and records (address, those bits)
; in the page's history; pl_erase gives them back (EOR), so the backdrop
; under a shape is left exactly as it was and nothing is redrawn. Up to 255
; pixels a page.
;
;   pl_page      A = 0 / 1: the page drawn (history pointers, address offset)
;   pl_erase     clear what the page's history lit, empty it (~40 c a pixel)
;   pl_line      pl_x0, pl_y0 -> pl_x1, pl_y1 (x 0..255, y 0..191)
;   pl_plot      pl_x, pl_y (~75 c a pixel)
;
; Needs hgr_lo / hgr_hi (page 1, hgr_scanline.inc) and hgr_div7 / hgr_mod7
; (hgr_div7_ram.asm). PL_HIST = a page-aligned 1.5 KB (6 pages of 256 B).
; ============================================================================

.segment "ZEROPAGE"
pl_x0:  .res 1
pl_y0:  .res 1
pl_x1:  .res 1
pl_y1:  .res 1
pl_x:   .res 1
pl_y:   .res 1
pl_dx:  .res 1
pl_dy:  .res 1
pl_err: .res 1
pl_cnt: .res 1
pl_m:   .res 1
pl_pg:  .res 1                          ; $00 or $60: hgr_hi EOR it = page 2
pl_ptr: .res 2
pl_hl:  .res 2                          ; the page's history: addresses lo,
pl_hh:  .res 2                          ; hi, bits
pl_hb:  .res 2
pl_cur: .res 1                          ; the page (0 / 1)

.segment "BSS"
pl_n:   .res 2                          ; pixels recorded, per page

.segment "CODE"

pl_page:
        STA     pl_cur
        TAX
        LDA     #0
        STA     pl_hl
        STA     pl_hh
        STA     pl_hb
        TXA
        BEQ     :+
        LDA     #$60
:       STA     pl_pg
        TXA                             ; history: PL_HIST + 3 pages * page
        ASL     A
        ADC     pl_cur                  ; (C = 0)
        ADC     #>PL_HIST
        STA     pl_hl+1
        ADC     #1
        STA     pl_hh+1
        ADC     #1
        STA     pl_hb+1
        RTS

pl_erase:
        LDX     pl_cur
        LDA     pl_n,X
        BEQ     @rts
        STA     pl_cnt
        LDA     #0
        STA     pl_n,X
        LDY     #0
@p:     LDA     (pl_hl),Y
        STA     pl_ptr
        LDA     (pl_hh),Y
        STA     pl_ptr+1
        LDA     (pl_hb),Y
        LDX     #0
        EOR     (pl_ptr,X)
        STA     (pl_ptr,X)
        INY
        CPY     pl_cnt
        BNE     @p
@rts:   RTS

; one pixel at pl_x, pl_y: light the dark bits of its mask, record them
pl_plot:
        LDX     pl_cur
        LDA     pl_n,X
        CMP     #255
        BEQ     @rts                    ; history full: nothing drawn
        LDY     pl_y
        LDA     hgr_lo,Y
        STA     pl_ptr
        LDA     hgr_hi,Y
        EOR     pl_pg
        STA     pl_ptr+1
        LDX     pl_x
        LDA     hgr_mod7,X
        LDY     hgr_div7,X
        TAX
        LDA     (pl_ptr),Y
        EOR     #$FF
        AND     pl_bits,X
        BEQ     @rts                    ; already lit
        STA     pl_m
        ORA     (pl_ptr),Y
        STA     (pl_ptr),Y
        TYA                             ; the byte's address (no carry: a row
        CLC                             ; starts at $x00, $x28, $x50, ..)
        ADC     pl_ptr
        LDX     pl_cur
        LDY     pl_n,X
        STA     (pl_hl),Y
        LDA     pl_ptr+1
        STA     (pl_hh),Y
        LDA     pl_m
        STA     (pl_hb),Y
        INC     pl_n,X
@rts:   RTS

; a line, Bresenham on the dominant axis (both ends drawn)
pl_line:
        LDA     pl_x0
        STA     pl_x
        LDA     pl_y0
        STA     pl_y
        SEC                             ; dx = |x1 - x0|, the x step
        LDA     pl_x1
        SBC     pl_x0
        LDX     #$E6                    ; INC zp
        BCS     :+
        EOR     #$FF
        ADC     #1
        LDX     #$C6                    ; DEC zp
:       STA     pl_dx
        STX     @sx1
        STX     @sx2
        SEC
        LDA     pl_y1
        SBC     pl_y0
        LDX     #$E6
        BCS     :+
        EOR     #$FF
        ADC     #1
        LDX     #$C6
:       STA     pl_dy
        STX     @sy1
        STX     @sy2
        CMP     pl_dx
        BCS     @ymaj
        LDA     pl_dx                   ; x major: dx + 1 pixels
        STA     pl_cnt
        LSR     A
        STA     pl_err
@xl:    JSR     pl_plot
        LDA     pl_cnt
        BEQ     @rts
        DEC     pl_cnt
@sx1:   INC     pl_x                    ; (INC or DEC, set above)
        LDA     pl_err
        CLC
        ADC     pl_dy
        BCS     :+
        CMP     pl_dx
        BCC     @xs
:       SBC     pl_dx
@sy1:   INC     pl_y
@xs:    STA     pl_err
        JMP     @xl
@ymaj:  LDA     pl_dy                   ; y major: dy + 1 pixels
        STA     pl_cnt
        LSR     A
        STA     pl_err
@yl:    JSR     pl_plot
        LDA     pl_cnt
        BEQ     @rts
        DEC     pl_cnt
@sy2:   INC     pl_y
        LDA     pl_err
        CLC
        ADC     pl_dx
        BCS     :+
        CMP     pl_dy
        BCC     @ys
:       SBC     pl_dy
@sx2:   INC     pl_x
@ys:    STA     pl_err
        JMP     @yl
@rts:   RTS

.segment "RODATA"
pl_bits: .byte $01, $02, $04, $08, $10, $20, $40
.segment "CODE"
