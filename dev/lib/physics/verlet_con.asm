; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; verlet_con.asm -- lib/physics: distance constraints without a square root
; ============================================================================
; Include at the END (after the callers and verlet_hmap.asm, before
; verlet_rot.asm, verlet.asm and mul.asm). dev/tools/verlet/constraint.py is
; the reference.
;
;   vl_con_pass    the VL_NCON constraints once, in order (vl_cur = each)
;   vl_constrain   constraint vl_cur: for its points a = vl_con_a, b = vl_con_b,
;                    q   = min(|delta >> 6|, 180) per axis (quarter pixels)
;                    q2  = qx^2 + qy^2 (quarter-square table)
;                    d8  = clamp((q2 - l2) >> 3, +-4095)
;                    f   = clamp((d8 * k8) >> 8, +-127)
;                    c   = (delta * f) >> 8;  a += c, b -= c
;                  l2 = vl_con_l2h:l2l, k8 = vl_con_k8 at the row of the
;                  constraint (vl_cur, or vl_cur * VL_CON_VARIANTS + vl_con_row
;                  with VL_CON_VARIANTS). |b - a| < 128 px on each axis, a link
;                  up to 45 px (q clamped). ~900-1050 cycles.
;   vl_heavy       (VL_CON_HEAVY_POINT) a link whose b is that point moves it
;                  c - c' and a c + c', c' = c >> VL_CON_HEAVY_SHIFT rounded
;                  toward 0: b weighs (2^n + 1) / (2^n - 1) times a.
;   vl_quarter_abs A/X = signed delta -> A = min(|delta >> 6|, 180)
;   vl_square      A = 0..180 -> A/Y = A^2 (mul_sqr1, ~40 cycles)
;
; VL_CON_MINLEN_POINT / VL_CON_MINLEN: a link whose b is that point with
; q2 < VL_CON_MINLEN (l2q units) sets vl_squashed = 1 (DIRTBIKE: the rider
; squashed on a wheel; the program clears it).
; ============================================================================

.ifndef _VERLET_CON_ASM_LOADED_
_VERLET_CON_ASM_LOADED_ = 1

.ifndef _VERLET_INC_LOADED_
.error "verlet_con.asm: include verlet.inc at the top first"
.endif

.segment "CODE"

.ifref vl_con_pass
.ifndef VL_NCON
.error "vl_con_pass: define VL_NCON before verlet.inc"
.endif
vl_con_pass:
        LDX     #0
@con:   STX     vl_cur
        JSR     vl_constrain
        LDX     vl_cur
        INX
        CPX     #VL_NCON
        BNE     @con
        RTS
.endif

.ifref vl_constrain
vl_constrain:
        LDX     vl_cur
        LDA     vl_con_a,X
        STA     vl_ca
        LDA     vl_con_b,X
        STA     vl_cb
.ifdef VL_CON_VARIANTS
        LDA     vl_con_nl,X             ; cidx = cur * VL_CON_VARIANTS + row
        CLC
        ADC     vl_con_row
        STA     vl_cidx
.endif
        JSR     vl_delta_ab
        LDA     vl_dy
        LDX     vl_dy+1
        JSR     vl_quarter_abs
        STA     vl_qx                   ; (qy, kept while qx is squared)
        LDA     vl_dx
        LDX     vl_dx+1
        JSR     vl_quarter_abs
        JSR     vl_square               ; qx^2 (16 bits)
        STA     vl_pen
        STY     vl_pen+1
        LDA     vl_qx
        JSR     vl_square               ; qy^2
.ifdef VL_CON_VARIANTS
        LDX     vl_cidx                 ; w = qx^2 + qy^2 - L^2 (24 bits)
.else
        LDX     vl_cur
.endif
        CLC
        ADC     vl_pen
        STA     vl_w0
        TYA
        ADC     vl_pen+1
        STA     vl_w1
        LDA     #0
        ADC     #0
        STA     vl_w2
.ifdef VL_CON_MINLEN_POINT
        LDA     vl_cb                   ; a link to that point: short?
        CMP     #VL_CON_MINLEN_POINT
        BNE     @nsq
        LDA     vl_w2
        BNE     @nsq
        LDA     vl_w0
        CMP     #<VL_CON_MINLEN
        LDA     vl_w1
        SBC     #>VL_CON_MINLEN
        BCS     @nsq
        LDA     #1
        STA     vl_squashed
.endif
@nsq:   SEC
        LDA     vl_w0
        SBC     vl_con_l2l,X
        STA     vl_w0
        LDA     vl_w1
        SBC     vl_con_l2h,X
        STA     vl_w1
        LDA     vl_w2
        SBC     #0
        STA     vl_w2
        LDY     #3                      ; >> 3, arithmetic
@sh:    LDA     vl_w2
        CMP     #$80
        ROR     vl_w2
        ROR     vl_w1
        ROR     vl_w0
        DEY
        BNE     @sh
        LDA     vl_w2                   ; clamp to +-4095
        BMI     @dneg
        BNE     @dmax
        LDA     vl_w1
        CMP     #$10
        BCC     @dok
@dmax:  LDA     #$FF
        STA     vl_w0
        LDA     #$0F
        STA     vl_w1
        BNE     @dok
@dneg:  CMP     #$FF
        BNE     @dmin
        LDA     vl_w0
        CMP     #$01
        LDA     vl_w1
        SBC     #$F0
        BCS     @dok
@dmin:  LDA     #$01
        STA     vl_w0
        LDA     #$F0
        STA     vl_w1
@dok:   LDA     vl_w0
        STA     mul_x
        LDA     vl_w1
        STA     mul_x+1
        LDA     vl_con_k8,X
        STA     mul_y
        JSR     mul_s16s8               ; f = clamp(prod >> 8, +-127)
        LDA     mul_p2
        BMI     @fneg
        BNE     @fmax
        LDA     mul_p1
        BPL     @fok
@fmax:  LDA     #$7F
        BNE     @fok
@fneg:  CMP     #$FF
        BNE     @fmin
        LDA     mul_p1
        CMP     #$81
        BCS     @fok
@fmin:  LDA     #$81
@fok:   STA     vl_fcoef
        LDA     vl_dx                   ; cx = (dx * f) >> 8
        STA     mul_x
        LDA     vl_dx+1
        STA     mul_x+1
        LDA     vl_fcoef
        STA     mul_y
        JSR     mul_s16s8
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
.ifdef VL_CON_HEAVY_POINT
        LDA     vl_cb
        CMP     #VL_CON_HEAVY_POINT
        BNE     @px
        JSR     vl_heavy                ; b: c - c', a: c + c'
        LDX     vl_ca
        JSR     vl_add_xv
        LDA     vl_vn
        STA     vl_val
        LDA     vl_vn+1
        STA     vl_val+1
@px:    LDX     vl_cb
        JSR     vl_sub_xv
        LDA     vl_cb
        CMP     #VL_CON_HEAVY_POINT
        BEQ     @cy
        LDX     vl_ca
        JSR     vl_add_xv
.else
        LDX     vl_cb
        JSR     vl_sub_xv
        LDX     vl_ca
        JSR     vl_add_xv
.endif
@cy:    LDA     vl_dy                   ; cy = (dy * f) >> 8
        STA     mul_x
        LDA     vl_dy+1
        STA     mul_x+1
        LDA     vl_fcoef
        STA     mul_y
        JSR     mul_s16s8
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
.ifdef VL_CON_HEAVY_POINT
        LDA     vl_cb
        CMP     #VL_CON_HEAVY_POINT
        BNE     @py
        JSR     vl_heavy
        LDX     vl_ca
        JSR     vl_add_yv
        LDA     vl_vn
        STA     vl_val
        LDA     vl_vn+1
        STA     vl_val+1
        LDX     vl_cb
        JMP     vl_sub_yv
.endif
@py:    LDX     vl_ca
        JSR     vl_add_yv
        LDX     vl_cb
        JMP     vl_sub_yv
.endif

.ifref vl_heavy
.ifndef VL_CON_HEAVY_SHIFT
.error "vl_heavy: define VL_CON_HEAVY_SHIFT (with VL_CON_HEAVY_POINT)"
.endif
; vl_val = c + c', vl_vn = c - c', c' = c >> VL_CON_HEAVY_SHIFT toward 0
vl_heavy:
        LDA     vl_val
        LDY     vl_val+1
        BPL     @p
        CLC
        ADC     #(1 << VL_CON_HEAVY_SHIFT) - 1
        BCC     @p
        INY
@p:     STA     vl_pen
        STY     vl_pen+1
        LDY     #VL_CON_HEAVY_SHIFT
@s:     LDA     vl_pen+1
        CMP     #$80
        ROR     vl_pen+1
        ROR     vl_pen
        DEY
        BNE     @s
        SEC
        LDA     vl_val
        SBC     vl_pen
        STA     vl_vn
        LDA     vl_val+1
        SBC     vl_pen+1
        STA     vl_vn+1
        CLC
        LDA     vl_val
        ADC     vl_pen
        STA     vl_val
        LDA     vl_val+1
        ADC     vl_pen+1
        STA     vl_val+1
        RTS
.endif

.ifref vl_quarter_abs
; A/X = 16-bit signed delta (lo/hi) -> A = min(|floor(d / 64)|, 180)
vl_quarter_abs:
        STA     vl_w0
        STX     vl_w1
        LDY     #0
        TXA
        BPL     @p
        DEY
@p:     STY     vl_w2
        ASL     vl_w0
        ROL     vl_w1
        ROL     vl_w2
        ASL     vl_w0
        ROL     vl_w1
        ROL     vl_w2                   ; w2:w1 = floor(d / 64)
        LDA     vl_w2
        BPL     @pos
        SEC
        LDA     #0
        SBC     vl_w1
        STA     vl_w1
        LDA     #0
        SBC     vl_w2
        STA     vl_w2
@pos:   LDA     vl_w2
        BNE     @max
        LDA     vl_w1
        CMP     #181
        BCC     @ok
@max:   LDA     #180
@ok:    RTS
.endif

.ifref vl_square
; A = x (0..180) -> A/Y = x^2 (lo/hi) = 4 floor(x^2 / 4) + (x & 1), from the
; quarter-square table (lib/math): ~40 cycles instead of a product
vl_square:
        TAX
        LDA     mul_sqr1_hi,X
        STA     vl_w2
        LDA     mul_sqr1_lo,X
        ASL     A
        ROL     vl_w2
        ASL     A
        ROL     vl_w2
        STA     vl_w0
        TXA
        AND     #1
        ORA     vl_w0
        LDY     vl_w2
        RTS
.endif

.ifdef VL_CON_VARIANTS
.ifref vl_con_nl
.segment "RODATA"
vl_con_nl:                              ; constraint * VL_CON_VARIANTS
.repeat VL_NCON, I
        .byte   I * VL_CON_VARIANTS
.endrepeat
.segment "CODE"
.endif
.endif

.endif  ; _VERLET_CON_ASM_LOADED_
