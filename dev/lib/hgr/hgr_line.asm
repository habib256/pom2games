; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native monochrome OR line, dominant-axis Bresenham (Fdraw-inspired).
; Inputs hl_ln_x0/x1: native HGR x=0..255; hl_ln_y0/y1: y=0..191.
; Deliberately an 8-bit X kernel, not a full 280-pixel API. No clipping.
; Uses hgr_lo/hi; writable CODE (INX/DEX self-modification); not reentrant.
; Endpoints and scratch are modified; clobbers A,X,Y. Bit 7 is preserved.
; Define hl_* ZP aliases before including to reuse caller scratch.
; HGR_LINE_DIV7 / HGR_LINE_MOD7 = tables of x div 7 / x mod 7 (x = 0..255),
; defined BEFORE the include (e.g. HGR_LINE_DIV7 = div7), replace the
; subtraction loop (up to 36 turns) by two lookups.
; With hgr_pages.inc included first, the three hgr_hi reads are HGR_HI_SITEs
; (the draw page follows hgr_select_page).
; Apache-2.0 provenance: dev/tests/techniques/upstream/fdraw.
.ifndef _HGR_LINE_LOADED_
_HGR_LINE_LOADED_ = 1

.macro HL_LDA_HI
.ifdef _HGR_PAGES_INC_LOADED_
        HGR_HI_SITE
.endif
        LDA hgr_hi,X
.endmacro
.zeropage
.ifndef hl_ln_x0
hl_ln_x0: .res 1
.endif
.ifndef hl_ln_y0
hl_ln_y0: .res 1
.endif
.ifndef hl_ln_x1
hl_ln_x1: .res 1
.endif
.ifndef hl_ln_y1
hl_ln_y1: .res 1
.endif
.ifndef hl_ln_dx
hl_ln_dx: .res 1
.endif
.ifndef hl_ln_dy
hl_ln_dy: .res 1
.endif
.ifndef hl_ln_sx
hl_ln_sx: .res 1
.endif
.ifndef hl_ln_err
hl_ln_err: .res 1
.endif
.ifndef hl_pix_mask
hl_pix_mask: .res 1
.endif
.ifndef hl_pix_addr_lo
hl_pix_addr_lo: .res 1
.endif
.ifndef hl_pix_addr_hi
hl_pix_addr_hi: .res 1
.endif
.code
hgr_line8:
        LDA hl_ln_x1
        CMP hl_ln_x0
        BCS hl_sorted
        LDX hl_ln_x0
        STA hl_ln_x0
        STX hl_ln_x1
        LDA hl_ln_y0
        LDX hl_ln_y1
        STA hl_ln_y1
        STX hl_ln_y0
hl_sorted:
        SEC
        LDA hl_ln_x1
        SBC hl_ln_x0
        STA hl_ln_dx
        SEC
        LDA hl_ln_y1
        SBC hl_ln_y0
        LDX #$E8                ; INX: downwards
        BCS hl_positive
        EOR #$FF
        ADC #1                  ; carry clear after subtraction
        LDX #$CA                ; DEX: upwards
hl_positive:
        STA hl_ln_dy
        STX hl_hy_step
        STX hl_vy_step
        ; Divide the native left endpoint once to obtain byte column/mask.
.ifdef HGR_LINE_DIV7
        LDX hl_ln_x0
        LDY HGR_LINE_MOD7,X
        LDA hl_native_mask,Y
        STA hl_pix_mask
        LDY HGR_LINE_DIV7,X     ; native byte column
.else
        LDA hl_ln_x0
        LDX #0
hl_div:   CMP #7
        BCC hl_remainder
        SBC #7                  ; carry set by CMP
        INX
        BNE hl_div
hl_remainder:
        TAY
        LDA hl_native_mask,Y
        STA hl_pix_mask
        TXA
        TAY                     ; native byte column
.endif
        LDX hl_ln_y0
        LDA hl_ln_dx
        CMP hl_ln_dy
        BCC hl_vertical
        STA hl_ln_sx            ; pixels = steps + 1, 0 = 256 (DEC / BEQ)
        LSR
        STA hl_ln_err
        INC hl_ln_sx
        LDA hgr_lo,X
        STA hl_pix_addr_lo
        HL_LDA_HI
        STA hl_pix_addr_hi
hl_horizontal:
        LDA (hl_pix_addr_lo),Y
        ORA hl_pix_mask
        STA (hl_pix_addr_lo),Y
        DEC hl_ln_sx
        BEQ hl_done
        ASL hl_pix_mask
        BPL hl_hmask
        INY
        LDA #1
        STA hl_pix_mask
hl_hmask: SEC
        LDA hl_ln_err
        SBC hl_ln_dy
        STA hl_ln_err
        BCS hl_horizontal       ; no row step
        ADC hl_ln_dx
        STA hl_ln_err
hl_hy_step:
        INX                     ; self modified: up/down
        LDA hgr_lo,X
        STA hl_pix_addr_lo
        HL_LDA_HI
        STA hl_pix_addr_hi
        JMP hl_horizontal
hl_vertical:
        LDA hl_ln_dy
        STA hl_ln_sx
        LSR
        STA hl_ln_err
        INC hl_ln_sx
hl_vloop:
        LDA hgr_lo,X
        STA hl_pix_addr_lo
        HL_LDA_HI
        STA hl_pix_addr_hi
        LDA (hl_pix_addr_lo),Y
        ORA hl_pix_mask
        STA (hl_pix_addr_lo),Y
        DEC hl_ln_sx
        BEQ hl_done
hl_vy_step:
        INX
        SEC
        LDA hl_ln_err
        SBC hl_ln_dx
        STA hl_ln_err
        BCS hl_vloop            ; no column step
        ADC hl_ln_dy
        STA hl_ln_err
        ASL hl_pix_mask
        BPL hl_vloop
        INY
        LDA #1
        STA hl_pix_mask
        BNE hl_vloop            ; (A = 1)
hl_done:  RTS

hl_native_mask: .byte 1,2,4,8,16,32,64
.endif
