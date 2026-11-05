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
;
; VL_CON_FIXED_K = s (0..8): every link's gain is 2^s: f = clamp((q2 - l2)
; / 2^(11 - s), +-127) rounded toward zero (no d8: a dead band the same both
; ways, no creep of a body flying free), shifts instead of the product, no
; vl_con_k8 table: ~-170 cycles a link. VL_CON_MIN_ONLY: a link whose vl_con_b has bit 7 set only pushes
; (no correction when q2 >= l2: a minimum distance). VL_PIN: a pinned end
; (vl_pin) does not move, the other end takes the whole correction 2 c;
; both pinned, nothing moves (+~25 c a link without pins, the heavy point
; does not apply to a link with a pinned end).
;
; Speed switches (exact: the same results bit for bit):
; VL_CON_SKIP_ZERO: return as soon as f = 0 (every correction is then 0, on
; the plain, heavy and pinned paths): +5 B, -480..-520 c a link at rest.
; VL_CON_FAST: vl_delta_ab, vl_quarter_abs, the squares (vl_sq_lo / vl_sq_hi:
; x^2 for x = 0..180, 362 B RODATA) and the add/sub helpers of a plain link
; inline; vl_square reads the same table: -290 c a plain link (fixed gain),
; ~-220 c a pinned or heavy one.
; ============================================================================

.ifndef _VERLET_CON_ASM_LOADED_
_VERLET_CON_ASM_LOADED_ = 1

.ifndef _VERLET_INC_LOADED_
.error "verlet_con.asm: include verlet.inc at the top first"
.endif

.segment "CODE"

.ifdef VL_CON_FAST
; A = min(|floor((hi:lo) / 64)|, 180) (vl_quarter_abs inline): with h = hi
; signed, t = lo >> 6, floor(d / 64) = 4 h + t; |.| > 180 when h >= 45 or
; h <= -46. vl_w0 = t. ~33 cycles (h >= 0), ~37 (h < 0).
.macro _VL_QABS lo, hi
        LDA     lo
        ASL     A
        ROL     A
        ROL     A
        AND     #3
        STA     vl_w0
        LDA     hi
        BMI     :+
        CMP     #45
        BCS     :++
        ASL     A                       ; (h < 64: C = 0)
        ASL     A
        ORA     vl_w0
        BCC     :+++
:       CMP     #<-45                   ; h < 0
        BCC     :+
        ASL     A                       ; (h >= -64: C = 1)
        ASL     A
        ORA     vl_w0                   ; 4 h + t (mod 256), then negated
        EOR     #$FF
        ADC     #0
        BCC     :++                     ; (|4 h + t| >= 1: no carry)
:       LDA     #180
:
.endmacro
; point vl_ca x += c, point vl_cb x -= c, c = mul_p1:mul_p2 (signed 8.8)
.macro _VL_CORR_X
        LDY     #0
        LDA     mul_p2
        BPL     :+
        DEY
:       STY     vl_w2
        LDX     vl_ca
        CLC
        LDA     vl_xf,X
        ADC     mul_p1
        STA     vl_xf,X
        LDA     vl_xl,X
        ADC     mul_p2
        STA     vl_xl,X
        LDA     vl_xh,X
        ADC     vl_w2
        STA     vl_xh,X
        LDX     vl_cb
        SEC
        LDA     vl_xf,X
        SBC     mul_p1
        STA     vl_xf,X
        LDA     vl_xl,X
        SBC     mul_p2
        STA     vl_xl,X
        LDA     vl_xh,X
        SBC     vl_w2
        STA     vl_xh,X
.endmacro
; the same on y (16 bits; VL_Y_HIGH: 24)
.macro _VL_CORR_Y
.ifdef VL_Y_HIGH
        LDY     #0
        LDA     mul_p2
        BPL     :+
        DEY
:       STY     vl_w2
.endif
        LDX     vl_ca
        CLC
        LDA     vl_yf,X
        ADC     mul_p1
        STA     vl_yf,X
        LDA     vl_yh,X
        ADC     mul_p2
        STA     vl_yh,X
.ifdef VL_Y_HIGH
        LDA     vl_yu,X
        ADC     vl_w2
        STA     vl_yu,X
.endif
        LDX     vl_cb
        SEC
        LDA     vl_yf,X
        SBC     mul_p1
        STA     vl_yf,X
        LDA     vl_yh,X
        SBC     mul_p2
        STA     vl_yh,X
.ifdef VL_Y_HIGH
        LDA     vl_yu,X
        SBC     vl_w2
        STA     vl_yu,X
.endif
.endmacro
.endif

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
.ifdef VL_CON_MIN_ONLY
        AND     #$7F
.endif
        STA     vl_cb
.ifdef VL_CON_VARIANTS
        LDA     vl_con_nl,X             ; cidx = cur * VL_CON_VARIANTS + row
        CLC
        ADC     vl_con_row
        STA     vl_cidx
.endif
.ifdef VL_CON_FAST
        LDX     vl_cb                   ; vl_delta_ab, inline
        LDY     vl_ca
        SEC
        LDA     vl_xf,X
        SBC     vl_xf,Y
        STA     vl_dx
        LDA     vl_xl,X
        SBC     vl_xl,Y
        STA     vl_dx+1
        SEC
        LDA     vl_yf,X
        SBC     vl_yf,Y
        STA     vl_dy
        LDA     vl_yh,X
        SBC     vl_yh,Y
        STA     vl_dy+1
        _VL_QABS vl_dy, vl_dy+1         ; qy
        STA     vl_qx
        _VL_QABS vl_dx, vl_dx+1         ; qx
        TAX
        LDY     vl_qx
        CLC                             ; w = qx^2 + qy^2 (the square table)
        LDA     vl_sq_lo,X
        ADC     vl_sq_lo,Y
        STA     vl_w0
        LDA     vl_sq_hi,X
        ADC     vl_sq_hi,Y
        STA     vl_w1
        LDA     #0                      ; (<= 2 * 180^2 < 2^16: no carry)
        STA     vl_w2
.ifdef VL_CON_VARIANTS
        LDX     vl_cidx                 ; w -= L^2 (24 bits) below
.else
        LDX     vl_cur
.endif
.else
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
.endif                                  ; (VL_CON_FAST)
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
.ifdef VL_CON_MIN_ONLY
        BMI     @mo                     ; a minimum only and q2 >= l2: no move
        LDY     vl_cur
        LDA     vl_con_b,Y
        BPL     @mo
        RTS
@mo:
.endif
.ifdef VL_CON_FIXED_K
        .assert VL_CON_FIXED_K >= 0 .and VL_CON_FIXED_K <= 8, error, "VL_CON_FIXED_K is 0..8 (gain 2^s)"
_VL_FKN = 11 - VL_CON_FIXED_K           ; f = clamp(w / 2^n, +-127), toward 0
        LDA     vl_w2
        BPL     @fk
        CLC
        LDA     vl_w0
        ADC     #<((1 << _VL_FKN) - 1)
        STA     vl_w0
        LDA     vl_w1
        ADC     #>((1 << _VL_FKN) - 1)
        STA     vl_w1
        LDA     vl_w2
        ADC     #0
        STA     vl_w2
@fk:
.if _VL_FKN < 8
.repeat 8 - _VL_FKN                     ; w << (8 - n): f = w2:w1
        ASL     vl_w0
        ROL     vl_w1
        ROL     vl_w2
.endrepeat
        LDA     vl_w2
.else
        LDA     vl_w2                   ; w2:w1 >> (n - 8)
.repeat _VL_FKN - 8
        CMP     #$80
        ROR     A
        ROR     vl_w1
.endrepeat
.if _VL_FKN > 8
        ORA     #0                      ; clamp tests the high byte, not shifted low
.endif
.endif
        BMI     @fneg                   ; A = high byte, vl_w1 = low
        BNE     @fmax
        LDA     vl_w1
.ifdef VL_CON_SKIP_ZERO
        BEQ     @fz
.endif
        BPL     @fok
@fmax:  LDA     #$7F
        BNE     @fok
.ifdef VL_CON_SKIP_ZERO
@fz:    STA     vl_fcoef                ; f = 0: every correction is 0
        RTS
.endif
@fneg:  CMP     #$FF
        BNE     @fmin
        LDA     vl_w1
        CMP     #$81
        BCS     @fok
@fmin:  LDA     #$81
@fok:   STA     vl_fcoef
.else
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
.ifdef VL_CON_SKIP_ZERO
        BEQ     @fz
.endif
        BPL     @fok
@fmax:  LDA     #$7F
        BNE     @fok
.ifdef VL_CON_SKIP_ZERO
@fz:    STA     vl_fcoef                ; f = 0: every correction is 0
        RTS
.endif
@fneg:  CMP     #$FF
        BNE     @fmin
        LDA     mul_p1
        CMP     #$81
        BCS     @fok
@fmin:  LDA     #$81
@fok:   STA     vl_fcoef
.endif                                  ; (VL_CON_FIXED_K)
.ifdef VL_PIN
        LDX     vl_ca                   ; qx = a pinned (bit 7), b pinned (6)
        LDA     vl_pin,X
        BEQ     @pa
        LDA     #$80
@pa:    LDX     vl_cb
        LDY     vl_pin,X
        BEQ     @pb
        ORA     #$40
@pb:    STA     vl_qx
        TAY
        BEQ     @free                   ; no pin: the plain link
        CMP     #$C0
        BNE     @one
        RTS                             ; both pinned: no move
@one:   LDA     vl_dx                   ; the free end takes 2 cx, 2 cy
        LDX     vl_dx+1
        JSR     vl_cmul2
        BIT     vl_qx
        BMI     @bx
        LDX     vl_ca
        JSR     vl_add_xv
        JMP     @y2
@bx:    LDX     vl_cb
        JSR     vl_sub_xv
@y2:    LDA     vl_dy
        LDX     vl_dy+1
        JSR     vl_cmul2
        BIT     vl_qx
        BMI     @by
        LDX     vl_ca
        JMP     vl_add_yv
@by:    LDX     vl_cb
        JMP     vl_sub_yv
@free:
.endif
.ifdef VL_CON_FAST
        LDA     vl_dx                   ; cx = (dx * f) >> 8
        STA     mul_x
        LDA     vl_dx+1
        STA     mul_x+1
        LDA     vl_fcoef
        STA     mul_y
        JSR     mul_s16s8
.ifdef VL_CON_HEAVY_POINT
        LDA     vl_cb
        CMP     #VL_CON_HEAVY_POINT
        BNE     @fx
        LDA     mul_p1                  ; the heavy b: the helpers
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
        JSR     vl_heavy                ; b: c - c', a: c + c'
        LDX     vl_ca
        JSR     vl_add_xv
        LDA     vl_vn
        STA     vl_val
        LDA     vl_vn+1
        STA     vl_val+1
        LDX     vl_cb
        JSR     vl_sub_xv
        JMP     @cy
@fx:
.endif
        _VL_CORR_X                      ; a += c, b -= c (inline)
@cy:    LDA     vl_dy                   ; cy = (dy * f) >> 8
        STA     mul_x
        LDA     vl_dy+1
        STA     mul_x+1
        JSR     mul_s16s8               ; (mul_y = f still)
.ifdef VL_CON_HEAVY_POINT
        LDA     vl_cb
        CMP     #VL_CON_HEAVY_POINT
        BNE     @fy
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
        JSR     vl_heavy
        LDX     vl_ca
        JSR     vl_add_yv
        LDA     vl_vn
        STA     vl_val
        LDA     vl_vn+1
        STA     vl_val+1
        LDX     vl_cb
        JMP     vl_sub_yv
@fy:
.endif
        _VL_CORR_Y
        RTS
.else
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
.endif                                  ; (VL_CON_FAST)
.endif

.ifref vl_cmul2
; val = 2 ((A/X signed * vl_fcoef) >> 8)
vl_cmul2:
        STA     mul_x
        STX     mul_x+1
        LDA     vl_fcoef
        STA     mul_y
        JSR     mul_s16s8
        LDA     mul_p1
        ASL     A
        STA     vl_val
        LDA     mul_p2
        ROL     A
        STA     vl_val+1
        RTS
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
        TYA                             ; high byte stays in A during the shift
        LDY     #VL_CON_HEAVY_SHIFT
@s:     CMP     #$80
        ROR     A
        ROR     vl_pen
        DEY
        BNE     @s
        STA     vl_pen+1
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
; Keeps X, returns the input sign in Y ($00/$ff). NZCV are scratch flags;
; decimal and IRQ state are unchanged (the library requires D=0).
vl_quarter_abs:
        ; floor(d/64) = 4 * signed(high) + (low >> 6). Only high bytes
        ; -45..44 need arithmetic; all others clamp immediately to 180.
        ASL     A
        ROL     A
        ROL     A
        AND     #3
        STA     vl_w0
        LDY     #0
        TXA
        BMI     @neg
        CMP     #45
        BCS     @max
        ASL     A
        ASL     A
        ORA     vl_w0
        RTS
@neg:   DEY                             ; retain X and the original Y sign result
        CMP     #<-45
        BCC     @max
        ASL     A
        ASL     A
        ORA     vl_w0
        EOR     #$FF
        ADC     #0                      ; the shifts left C=1: complement plus one
        RTS
@max:   LDA     #180
        RTS
.endif

.ifref vl_square
; A = x (0..180) -> A/Y = x^2 (lo/hi). The quarter-square entry at 2*x
; is floor((2*x)^2/4) = x^2 exactly. X/NZCV are clobbered; I/D unchanged.
vl_square:
.ifdef VL_CON_FAST
        TAX                             ; the square table (VL_CON_FAST)
        LDA     vl_sq_lo,X
        LDY     vl_sq_hi,X
        RTS
.else
        ASL     A                       ; 2*x indexes one of the two table pages
        TAX
        BCS     @upper
        LDA     mul_sqr1_lo,X
        LDY     mul_sqr1_hi,X
        RTS
@upper: LDA     mul_sqr1_lo+256,X
        LDY     mul_sqr1_hi+256,X
        RTS
.endif                                  ; (VL_CON_FAST)
.endif

.ifdef VL_CON_FAST
.ifref vl_sq_lo
.segment "RODATA"
vl_sq_lo:                               ; x^2, x = 0..180 (VL_CON_FAST)
.repeat 181, I
        .byte   <(I * I)
.endrepeat
vl_sq_hi:
.repeat 181, I
        .byte   >(I * I)
.endrepeat
.segment "CODE"
.endif
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
