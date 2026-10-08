; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native monochrome OR line, dominant-axis Bresenham (Fdraw-inspired).
; Inputs hl_ln_x0/x1: native HGR x=0..255; hl_ln_y0/y1: y=0..191.
; Deliberately an 8-bit X kernel, not a full 280-pixel API. No clipping.
; Uses hgr_lo/hi; writable CODE (INX/DEX self-modification); not reentrant.
; Endpoints and scratch are modified; clobbers A,X,Y. Bit 7 is preserved.
; Define hl_* ZP aliases before including to reuse caller scratch.
; Apache-2.0 provenance: dev/tests/techniques/upstream/fdraw.
.ifndef _HGR_LINE_LOADED_
_HGR_LINE_LOADED_ = 1
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
        BCS @sorted
        LDX hl_ln_x0
        STA hl_ln_x0
        STX hl_ln_x1
        LDA hl_ln_y0
        LDX hl_ln_y1
        STA hl_ln_y1
        STX hl_ln_y0
@sorted:
        SEC
        LDA hl_ln_x1
        SBC hl_ln_x0
        STA hl_ln_dx
        SEC
        LDA hl_ln_y1
        SBC hl_ln_y0
        LDX #$E8                ; INX: downwards
        BCS @positive
        EOR #$FF
        ADC #1                  ; carry clear after subtraction
        LDX #$CA                ; DEX: upwards
@positive:
        STA hl_ln_dy
        STX @hy_step
        STX @vy_step
        ; Divide the native left endpoint once to obtain byte column/mask.
        LDA hl_ln_x0
        LDX #0
@div:   CMP #7
        BCC @remainder
        SBC #7                  ; carry set by CMP
        INX
        BNE @div
@remainder:
        TAY
        LDA hl_native_mask,Y
        STA hl_pix_mask
        TXA
        TAY                     ; native byte column
        LDX hl_ln_y0
        LDA hl_ln_dx
        CMP hl_ln_dy
        BCC @vertical
        STA hl_ln_sx               ; remaining steps (not inclusive count)
        LSR
        STA hl_ln_err
        LDA hgr_lo,X
        STA hl_pix_addr_lo
        LDA hgr_hi,X
        STA hl_pix_addr_hi
@horizontal:
        LDA (hl_pix_addr_lo),Y
        ORA hl_pix_mask
        STA (hl_pix_addr_lo),Y
        LDA hl_ln_sx
        BEQ @done
        DEC hl_ln_sx
        ASL hl_pix_mask
        BPL @hmask
        INY
        LDA #1
        STA hl_pix_mask
@hmask: SEC
        LDA hl_ln_err
        SBC hl_ln_dy
        BCS @herror
        ADC hl_ln_dx
        STA hl_ln_err
@hy_step:
        INX                     ; self modified: up/down
        LDA hgr_lo,X
        STA hl_pix_addr_lo
        LDA hgr_hi,X
        STA hl_pix_addr_hi
        JMP @horizontal
@herror:
        STA hl_ln_err
        JMP @horizontal
@vertical:
        LDA hl_ln_dy
        STA hl_ln_sx
        LSR
        STA hl_ln_err
@vloop:
        LDA hgr_lo,X
        STA hl_pix_addr_lo
        LDA hgr_hi,X
        STA hl_pix_addr_hi
        LDA (hl_pix_addr_lo),Y
        ORA hl_pix_mask
        STA (hl_pix_addr_lo),Y
        LDA hl_ln_sx
        BEQ @done
        DEC hl_ln_sx
@vy_step:
        INX
        SEC
        LDA hl_ln_err
        SBC hl_ln_dx
        BCS @verror
        ADC hl_ln_dy
        STA hl_ln_err
        ASL hl_pix_mask
        BPL @vloop
        INY
        LDA #1
        STA hl_pix_mask
        JMP @vloop
@verror:
        STA hl_ln_err
        JMP @vloop
@done:  RTS

hl_native_mask: .byte 1,2,4,8,16,32,64
.endif
