; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; verlet_rot.asm -- lib/physics: turn and slide along an axis of two points
; ============================================================================
; Include at the END (after the callers, verlet_hmap.asm, verlet_con.asm;
; before verlet.asm and mul.asm). dev/tools/verlet/points.py is the reference.
; The axis is point VL_AXIS_B - point VL_AXIS_A (defaults 1 and 0).
;
;   vl_axis         vl_dx/vl_dy = the axis (vl_ca/vl_cb set, vl_delta_ab)
;   vl_mul_turn     vl_val = (A/X signed * vl_turn) >> 8 (floor)
;   vl_turn_pair    turn the axis: B += vl_turn (-dy, dx) >> 8, A -= the same
;                   (clockwise on screen for vl_turn > 0). ~650 cycles.
;   vl_shift_point  point VL_SHIFT_POINT and its old position += vl_turn *
;                   axis >> 8 (a move, no speed: DIRTBIKE's rider leaning).
;                   ~600 cycles.
;   vl_thrust_axis  (VL_THRUST = n) the push vector vl_tx/vl_ty = axis *
;                   vl_turn >> (8 + n); vl_dx/vl_dy = the axis. ~470 c (n = 4)
;   vl_thrust_perp  the same along the perpendicular (-dy, dx) of the axis
;                   (vl_dx/vl_dy = it): with a link of rest length L, the push
;                   is L * vl_turn / 2^(8 + n) px; vl_push / vl_push_all
;                   (verlet.asm) add it to the points (a speed change).
; vl_turn is signed (-128..127). Segments: .define VL_ROT_SEG "SEG" puts
; vl_shift_point and vl_axis there, .define VL_MULTURN_SEG "SEG" vl_mul_turn
; (DIRTBIKE: text-page runs copied at boot); default CODE.
; ============================================================================

.ifndef _VERLET_ROT_ASM_LOADED_
_VERLET_ROT_ASM_LOADED_ = 1

.ifndef _VERLET_INC_LOADED_
.error "verlet_rot.asm: include verlet.inc at the top first"
.endif
.ifndef VL_AXIS_A
VL_AXIS_A = 0
.endif
.ifndef VL_AXIS_B
VL_AXIS_B = 1
.endif

.segment "CODE"

.ifref vl_turn_pair
; turn the axis: B += turn * perp, A -= turn * perp, perp = (-dy, dx)
vl_turn_pair:
        JSR     vl_axis
        SEC                             ; -dy
        LDA     #0
        SBC     vl_dy
        TAY
        LDA     #0
        SBC     vl_dy+1
        TAX
        TYA
        JSR     vl_mul_turn
        LDX     #VL_AXIS_B
        JSR     vl_add_xv
        LDX     #VL_AXIS_A
        JSR     vl_sub_xv
        LDA     vl_dx
        LDX     vl_dx+1
        JSR     vl_mul_turn
        LDX     #VL_AXIS_B
        JSR     vl_add_yv
        LDX     #VL_AXIS_A
        JMP     vl_sub_yv
.endif

.if .referenced(vl_thrust_axis) .or .referenced(vl_thrust_perp)
.ifndef VL_THRUST
.error "vl_thrust_*: define VL_THRUST (the extra shift, 0..7)"
.endif
.assert VL_THRUST >= 0 .and VL_THRUST <= 7, error, "VL_THRUST is 0..7"
; tx, ty = (-dy, dx) * turn >> (8 + VL_THRUST)
vl_thrust_perp:
        JSR     vl_axis
        SEC                             ; (dx, dy) := (-dy, dx)
        LDA     #0
        SBC     vl_dy
        STA     vl_tx
        LDA     #0
        SBC     vl_dy+1
        STA     vl_tx+1
        LDA     vl_dx
        STA     vl_dy
        LDA     vl_dx+1
        STA     vl_dy+1
        LDA     vl_tx
        STA     vl_dx
        LDA     vl_tx+1
        STA     vl_dx+1
        JMP     vl_thrust_vec
; tx, ty = (dx, dy) * turn >> (8 + VL_THRUST)
vl_thrust_axis:
        JSR     vl_axis
vl_thrust_vec:
        LDA     vl_dx
        LDX     vl_dx+1
        JSR     vl_mul_turn
        JSR     vl_thrust_shr
        STA     vl_tx
        STX     vl_tx+1
        LDA     vl_dy
        LDX     vl_dy+1
        JSR     vl_mul_turn
        JSR     vl_thrust_shr
        STA     vl_ty
        STX     vl_ty+1
        RTS
; A/X = vl_val >> VL_THRUST (arithmetic)
vl_thrust_shr:
        LDA     vl_val+1
.repeat VL_THRUST
        CMP     #$80
        ROR     A
        ROR     vl_val
.endrepeat
        TAX
        LDA     vl_val
        RTS
.endif

.if .match({VL_ROT_SEG}, "")
.segment VL_ROT_SEG
.endif

.ifref vl_shift_point
.ifndef VL_SHIFT_POINT
.error "vl_shift_point: define VL_SHIFT_POINT (the point it moves)"
.endif
.assert vl_oxf - vl_xf = vl_oyf - vl_yf, error, "vl_shift_point: vl_ox*, vl_oy* at the same offset from vl_x*, vl_y*"
.assert VL_SHIFT_POINT + vl_oxf - vl_xf < 256, error, "vl_shift_point: old point out of X range"
; the point (and its old position: no speed) += turn * axis
vl_shift_point:
        JSR     vl_axis
        LDA     vl_dx
        LDX     vl_dx+1
        JSR     vl_mul_turn
        LDX     #VL_SHIFT_POINT
        JSR     vl_add_xv
        LDX     #VL_SHIFT_POINT + (vl_oxf - vl_xf)
        JSR     vl_add_xv
        LDA     vl_dy
        LDX     vl_dy+1
        JSR     vl_mul_turn
        LDX     #VL_SHIFT_POINT
        JSR     vl_add_yv
        LDX     #VL_SHIFT_POINT + (vl_oxf - vl_xf)
        JMP     vl_add_yv
.endif

.ifref vl_axis
; dx/dy = point VL_AXIS_B - point VL_AXIS_A
vl_axis:
        LDA     #VL_AXIS_A
        STA     vl_ca
        LDA     #VL_AXIS_B
        STA     vl_cb
        JMP     vl_delta_ab
.endif
.segment "CODE"

.if .match({VL_MULTURN_SEG}, "")
.segment VL_MULTURN_SEG
.endif

.ifref vl_mul_turn
; val = (A/X (lo/hi, signed) * vl_turn) >> 8
vl_mul_turn:
        STA     mul_x
        STX     mul_x+1
        LDA     vl_turn
        STA     mul_y
        JSR     mul_s16s8
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
        RTS
.endif
.segment "CODE"

.endif  ; _VERLET_ROT_ASM_LOADED_
