; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Full-width 16-bit Bresenham walker, preserving LOGO's raster ties:
; step X when 2*err >= -dy; step Y when 2*err < dx.
; Endpoints h16_x0/x1 (signed 16-bit), h16_y0/y1 (unsigned 8-bit). Valid screen inputs
; draw normally; nearby off-screen endpoints are clipped by the plot hook.
; Require |dx|<=511: the signed error tests are for screen-sized lines.
; Negative X vertices near the left edge advance toward the screen normally;
; hgr_plot16 drops those pixels before accessing any table.
; Defaults: HGR_LINE16_PLOT=hgr_plot16, h16_pix_x/y=hp_x/y. Include the
; plot module first, or define a callback and its pixel coordinate aliases.
; Hook may destroy A/X/Y but must preserve the h16_* walker state.
; Endpoints/scratch modified; no bank/page/IRQ changes; non-reentrant, D=0.
.ifndef _HGR_LINE16_LOADED_
_HGR_LINE16_LOADED_ = 1
.ifndef HGR_LINE16_PLOT
HGR_LINE16_PLOT = hgr_plot16
.endif
.ifndef h16_pix_x
h16_pix_x = hp_x
.endif
.ifndef h16_pix_y
h16_pix_y = hp_y
.endif
.zeropage
.ifndef h16_x0
h16_x0: .res 2
.endif
.ifndef h16_y0
h16_y0: .res 1
.endif
.ifndef h16_x1
h16_x1: .res 2
.endif
.ifndef h16_y1
h16_y1: .res 1
.endif
.ifndef h16_dx
h16_dx: .res 2
.endif
.ifndef h16_dy
h16_dy: .res 1
.endif
.ifndef h16_sx
h16_sx: .res 1
.endif
.ifndef h16_sy
h16_sy: .res 1
.endif
.ifndef h16_err
h16_err: .res 2
.endif
.ifndef h16_e2
h16_e2: .res 2
.endif
.code
hgr_line16:
        ; --- dx (16-bit) + sx ---
        SEC
        LDA h16_x1
        SBC h16_x0
        STA h16_dx
        LDA h16_x1+1
        SBC h16_x0+1
        STA h16_dx+1
        BPL @xpos               ; signed delta >= 0, including negative vertices
        ; negate 16-bit dx, sx = -1
        SEC
        LDA #0
        SBC h16_dx
        STA h16_dx
        LDA #0
        SBC h16_dx+1
        STA h16_dx+1
        LDA #$FF
        STA h16_sx
        JMP @dy
@xpos:  LDA #$01
        STA h16_sx
@dy:    ; --- dy (8-bit) + sy ---
        SEC
        LDA h16_y1
        SBC h16_y0
        BCS @syp
        EOR #$FF
        CLC
        ADC #1
        STA h16_dy
        LDA #$FF
        STA h16_sy
        JMP @init
@syp:   STA h16_dy
        LDA #$01
        STA h16_sy
@init:  ; --- err = dx - dy (16-bit signed) ---
        SEC
        LDA h16_dx
        SBC h16_dy
        STA h16_err
        LDA h16_dx+1
        SBC #0
        STA h16_err+1
        LDA h16_x0
        STA h16_pix_x
        LDA h16_x0+1
        STA h16_pix_x+1
        LDA h16_y0
        STA h16_pix_y
@step:  JSR HGR_LINE16_PLOT
        ; end test: x0 == x1 (both bytes) and y0 == y1
        LDA h16_x0
        CMP h16_x1
        BNE @do
        LDA h16_x0+1
        CMP h16_x1+1
        BNE @do
        LDA h16_y0
        CMP h16_y1
        BEQ @end
@do:    LDA h16_err
        STA h16_e2
        LDA h16_err+1
        STA h16_e2+1
        ASL h16_e2
        ROL h16_e2+1
        ; test 1: step x if 2*err >= -dy  (dy 8-bit, zero-extended)
        CLC
        LDA h16_e2
        ADC h16_dy
        LDA h16_e2+1
        ADC #0
        BMI @no_x
        ; err -= dy
        SEC
        LDA h16_err
        SBC h16_dy
        STA h16_err
        LDA h16_err+1
        SBC #0
        STA h16_err+1
        ; x0 += sx (16-bit)
        LDA h16_sx
        BPL @xinc
        LDA h16_x0
        BNE @decok
        DEC h16_x0+1
@decok: DEC h16_x0
        JMP @after_x
@xinc:  INC h16_x0
        BNE @after_x
        INC h16_x0+1
@after_x:
        LDA h16_x0
        STA h16_pix_x
        LDA h16_x0+1
        STA h16_pix_x+1
@no_x:  ; test 2: step y if 2*err < dx  (dx 16-bit)
        SEC
        LDA h16_e2
        SBC h16_dx
        LDA h16_e2+1
        SBC h16_dx+1
        BPL @no_y
        ; err += dx (16-bit)
        CLC
        LDA h16_err
        ADC h16_dx
        STA h16_err
        LDA h16_err+1
        ADC h16_dx+1
        STA h16_err+1
        LDA h16_sy
        BPL @syp2
        DEC h16_y0
        JMP @after_y
@syp2:  INC h16_y0
@after_y:
        LDA h16_y0
        STA h16_pix_y
@no_y:  JMP @step
@end:   RTS

.endif
