; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; verlet.asm -- lib/physics: the points (integration, moves, damping, wrap)
; ============================================================================
; Include at the END, after the callers and the other verlet_*.asm, before
; mul.asm. dev/tools/verlet/points.py is the reference. X = a point (0..
; VL_NPOINTS-1) where a routine takes one; x is 24 bits (vl_xf/xl/xh), y 16.
;
;   vl_wrap          vl_lap_len > 0 and point VL_WRAP_POINT (0) at or past
;                    vl_lap_len + VL_WRAP_MARGIN px: every point and old point
;                    moves back vl_lap_len px, then the hook VL_WRAP_AFTER
;                    (C = 1 there; C = 0 out: nothing moved). ~60 c / ~170 c.
;   vl_integrate_all every point, X = VL_NPOINTS-1 down to 0
;   vl_integrate     point X: vx = clamp(x - ox, +-VL_VMAX_X), vy = clamp(y -
;                    oy + VL_GRAVITY, +-VL_VMAX_Y), old := pos, pos += v
;                    (16-bit velocities); VL_INTEGRATE_LEFTWALL = wall (16.8,
;                    whole px, < 256 px): a point left of it stops there
;                    (x = ox = wall; x is taken unsigned). ~190 cycles.
;   vl_clamp_vx/vy   vl_val = clamp(vl_val, +-VL_VMAX_X / Y)
;   vl_add_xv / vl_sub_xv / vl_add_yv / vl_sub_yv
;                    point X +/- the signed 8.8 vl_val (x sign-extended to
;                    24 bits). Keep X. ~30 cycles.
;   vl_delta_ab      vl_dx/vl_dy = point vl_cb - point vl_ca (low 16 bits)
;   vl_pair_damp     VL_PAIR_DAMP = n: the relative speed of points VL_PAIR_B
;                    and VL_PAIR_A (1, 0) fades by 1/2^n (d = (v_b - v_a) >> n,
;                    old b += d, old a -= d): the spin of the pair, not its
;                    common speed. ~330 cycles.
;   vl_damp          vl_vt -= vl_vt >> (8 - Y), Y = 1..7 (floor): friction
;                    in a ground hook. Keeps X. ~70 cycles.
;   vl_rest          VL_REST as a routine (every point at rest)
;   vl_ceiling       VL_CEILING as a routine (VL_CEILING_CLAMP)
; ============================================================================

.ifndef _VERLET_ASM_LOADED_
_VERLET_ASM_LOADED_ = 1

.ifndef _VERLET_INC_LOADED_
.error "verlet.asm: include verlet.inc at the top first"
.endif
.ifndef VL_WRAP_POINT
VL_WRAP_POINT = 0
.endif
.ifndef VL_PAIR_A
VL_PAIR_A = 0
.endif
.ifndef VL_PAIR_B
VL_PAIR_B = 1
.endif
.if .not .definedmacro(VL_WRAP_AFTER)
.macro VL_WRAP_AFTER
.endmacro
.endif

.segment "CODE"

.ifref vl_wrap
.ifndef VL_WRAP_MARGIN
.error "vl_wrap: define VL_WRAP_MARGIN before verlet.inc"
.endif
vl_wrap:
        LDA     vl_lap_len
        ORA     vl_lap_len+1
        BEQ     @rts
        CLC
        LDA     vl_lap_len
        ADC     #<VL_WRAP_MARGIN
        STA     vl_w0
        LDA     vl_lap_len+1
        ADC     #>VL_WRAP_MARGIN
        STA     vl_w1
        LDA     vl_xl+VL_WRAP_POINT
        CMP     vl_w0
        LDA     vl_xh+VL_WRAP_POINT
        SBC     vl_w1
        BCC     @rts
        LDX     #VL_NPOINTS-1
@p:     SEC
        LDA     vl_xl,X
        SBC     vl_lap_len
        STA     vl_xl,X
        LDA     vl_xh,X
        SBC     vl_lap_len+1
        STA     vl_xh,X
        SEC
        LDA     vl_oxl,X
        SBC     vl_lap_len
        STA     vl_oxl,X
        LDA     vl_oxh,X
        SBC     vl_lap_len+1
        STA     vl_oxh,X
        DEX
        BPL     @p
        VL_WRAP_AFTER
@rts:   RTS
.endif

.ifref vl_integrate_all
vl_integrate_all:
        LDX     #VL_NPOINTS-1
@p:     JSR     vl_integrate
        DEX
        BPL     @p
        RTS
.endif

.ifref vl_integrate
vl_integrate:
        SEC
        LDA     vl_xf,X
        SBC     vl_oxf,X
        STA     vl_val
        LDA     vl_xl,X
        SBC     vl_oxl,X
        STA     vl_val+1
        JSR     vl_clamp_vx
        LDA     vl_val
        STA     vl_vx
        LDA     vl_val+1
        STA     vl_vx+1
        SEC
        LDA     vl_yf,X
        SBC     vl_oyf,X
        STA     vl_val
        LDA     vl_yh,X
        SBC     vl_oyh,X
        STA     vl_val+1
        CLC
        LDA     vl_val
        ADC     #<VL_GRAVITY
        STA     vl_val
        LDA     vl_val+1
        ADC     #>VL_GRAVITY
        STA     vl_val+1
        JSR     vl_clamp_vy             ; val = vy
        LDA     vl_xf,X
        STA     vl_oxf,X
        LDA     vl_xl,X
        STA     vl_oxl,X
        LDA     vl_xh,X
        STA     vl_oxh,X
        LDA     vl_yf,X
        STA     vl_oyf,X
        LDA     vl_yh,X
        STA     vl_oyh,X
        JSR     vl_add_yv
        LDA     vl_vx
        STA     vl_val
        LDA     vl_vx+1
        STA     vl_val+1
.ifdef VL_INTEGRATE_LEFTWALL
        .assert <VL_INTEGRATE_LEFTWALL = 0 .and VL_INTEGRATE_LEFTWALL < $10000, error, "VL_INTEGRATE_LEFTWALL: whole px < 256"
        JSR     vl_add_xv
        LDA     vl_xh,X                 ; x < the wall ?
        BNE     @ok
        LDA     vl_xl,X
        CMP     #>VL_INTEGRATE_LEFTWALL
        BCS     @ok
        LDA     #>VL_INTEGRATE_LEFTWALL
        STA     vl_xl,X
        STA     vl_oxl,X
        LDA     #0
        STA     vl_xf,X
        STA     vl_oxf,X
        STA     vl_oxh,X
@ok:    RTS
.else
        JMP     vl_add_xv
.endif
.endif

.ifref vl_clamp_vx
vl_clamp_vx: VL_CLAMP_VAL VL_VMAX_X
.endif
.ifref vl_clamp_vy
vl_clamp_vy: VL_CLAMP_VAL VL_VMAX_Y
.endif

.ifref vl_add_xv
vl_add_xv:
        LDY     #0
        LDA     vl_val+1
        BPL     @p
        DEY
@p:     CLC
        LDA     vl_xf,X
        ADC     vl_val
        STA     vl_xf,X
        LDA     vl_xl,X
        ADC     vl_val+1
        STA     vl_xl,X
        TYA
        ADC     vl_xh,X
        STA     vl_xh,X
        RTS
.endif

.ifref vl_sub_xv
vl_sub_xv:
        LDY     #0
        LDA     vl_val+1
        BPL     @p
        DEY
@p:     STY     vl_w2
        SEC
        LDA     vl_xf,X
        SBC     vl_val
        STA     vl_xf,X
        LDA     vl_xl,X
        SBC     vl_val+1
        STA     vl_xl,X
        LDA     vl_xh,X
        SBC     vl_w2
        STA     vl_xh,X
        RTS
.endif

.ifref vl_add_yv
vl_add_yv:
        CLC
        LDA     vl_yf,X
        ADC     vl_val
        STA     vl_yf,X
        LDA     vl_yh,X
        ADC     vl_val+1
        STA     vl_yh,X
        RTS
.endif

.ifref vl_sub_yv
vl_sub_yv:
        SEC
        LDA     vl_yf,X
        SBC     vl_val
        STA     vl_yf,X
        LDA     vl_yh,X
        SBC     vl_val+1
        STA     vl_yh,X
        RTS
.endif

.ifref vl_delta_ab
; dx/dy = point cb - point ca (low 16 bits of x)
vl_delta_ab:
        LDX     vl_cb
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
        RTS
.endif

.ifref vl_pair_damp
.ifndef VL_PAIR_DAMP
.error "vl_pair_damp: define VL_PAIR_DAMP (the shift)"
.endif
; d = (v_b - v_a) >> VL_PAIR_DAMP per axis (16-bit velocities), old b += d,
; old a -= d
vl_pair_damp:
        SEC                             ; x: d = (xb - oxb) - (xa - oxa)
        LDA     vl_xf+VL_PAIR_B
        SBC     vl_oxf+VL_PAIR_B
        STA     vl_w0
        LDA     vl_xl+VL_PAIR_B
        SBC     vl_oxl+VL_PAIR_B
        STA     vl_w1
        SEC
        LDA     vl_xf+VL_PAIR_A
        SBC     vl_oxf+VL_PAIR_A
        STA     vl_val
        LDA     vl_xl+VL_PAIR_A
        SBC     vl_oxl+VL_PAIR_A
        STA     vl_val+1
        SEC
        LDA     vl_w0
        SBC     vl_val
        STA     vl_val
        LDA     vl_w1
        SBC     vl_val+1
        STA     vl_val+1
        JSR     vl_sd_shift
        CLC                             ; oxb += d (24 bits)
        LDA     vl_oxf+VL_PAIR_B
        ADC     vl_val
        STA     vl_oxf+VL_PAIR_B
        LDA     vl_oxl+VL_PAIR_B
        ADC     vl_val+1
        STA     vl_oxl+VL_PAIR_B
        LDA     vl_oxh+VL_PAIR_B
        ADC     vl_w2
        STA     vl_oxh+VL_PAIR_B
        SEC                             ; oxa -= d
        LDA     vl_oxf+VL_PAIR_A
        SBC     vl_val
        STA     vl_oxf+VL_PAIR_A
        LDA     vl_oxl+VL_PAIR_A
        SBC     vl_val+1
        STA     vl_oxl+VL_PAIR_A
        LDA     vl_oxh+VL_PAIR_A
        SBC     vl_w2
        STA     vl_oxh+VL_PAIR_A
        SEC                             ; y: d = (yb - oyb) - (ya - oya)
        LDA     vl_yf+VL_PAIR_B
        SBC     vl_oyf+VL_PAIR_B
        STA     vl_w0
        LDA     vl_yh+VL_PAIR_B
        SBC     vl_oyh+VL_PAIR_B
        STA     vl_w1
        SEC
        LDA     vl_yf+VL_PAIR_A
        SBC     vl_oyf+VL_PAIR_A
        STA     vl_val
        LDA     vl_yh+VL_PAIR_A
        SBC     vl_oyh+VL_PAIR_A
        STA     vl_val+1
        SEC
        LDA     vl_w0
        SBC     vl_val
        STA     vl_val
        LDA     vl_w1
        SBC     vl_val+1
        STA     vl_val+1
        JSR     vl_sd_shift
        CLC
        LDA     vl_oyf+VL_PAIR_B
        ADC     vl_val
        STA     vl_oyf+VL_PAIR_B
        LDA     vl_oyh+VL_PAIR_B
        ADC     vl_val+1
        STA     vl_oyh+VL_PAIR_B
        SEC
        LDA     vl_oyf+VL_PAIR_A
        SBC     vl_val
        STA     vl_oyf+VL_PAIR_A
        LDA     vl_oyh+VL_PAIR_A
        SBC     vl_val+1
        STA     vl_oyh+VL_PAIR_A
        RTS
.endif

.ifref vl_sd_shift
; val >>= VL_PAIR_DAMP (arithmetic), w2 = its sign byte
vl_sd_shift:
        LDY     #VL_PAIR_DAMP
@s:     LDA     vl_val+1
        CMP     #$80
        ROR     vl_val+1
        ROR     vl_val
        DEY
        BNE     @s
        LDA     #0
        BIT     vl_val+1
        BPL     @p
        LDA     #$FF
@p:     STA     vl_w2
        RTS
.endif

.ifref vl_damp
; vt -= vt >> (8 - Y) (floor), Y = 1..7. Keeps X.
vl_damp:
        LDA     vl_vt
        STA     vl_w0
        LDA     vl_vt+1
        STA     vl_w1
        LDA     #0
        BIT     vl_vt+1
        BPL     @p
        LDA     #$FF
@p:     STA     vl_w2
@s:     ASL     vl_w0
        ROL     vl_w1
        ROL     vl_w2
        DEY
        BNE     @s
        SEC
        LDA     vl_vt
        SBC     vl_w1
        STA     vl_vt
        LDA     vl_vt+1
        SBC     vl_w2
        STA     vl_vt+1
        RTS
.endif

.ifref vl_rest
vl_rest:
        VL_REST
        RTS
.endif

.ifref vl_ceiling
vl_ceiling:
        VL_CEILING
        RTS
.endif

.endif  ; _VERLET_ASM_LOADED_
