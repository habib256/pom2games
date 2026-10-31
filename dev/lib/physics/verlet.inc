; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; verlet.inc -- lib/physics: integer Verlet points, sqrt-free constraints and
; a height-map ground (include it at the TOP, after math.inc)
; ============================================================================
; The 6502 side of dev/tools/verlet (the Python reference: design the physics
; there, the routines agree with it bit for bit). Split like lib/math:
;   verlet.inc        (this file) at the top: parameters, zero page, points,
;                     macros (VL_CLAMP_VAL, VL_CEILING, VL_REST, hook defaults);
;   verlet_hmap.asm, verlet_con.asm, verlet_rot.asm, verlet.asm at the END,
;                     in that order and before mul.asm: each routine is
;                     assembled only when referenced earlier (.ifref).
; README.md lists the routines, the parameters, the switches and the costs.
;
; Parameters (before the include):
;   VL_NPOINTS        points (required); VL_NCON constraints (lib con tier)
;   VL_GRAVITY, VL_VMAX_X, VL_VMAX_Y   (8.8) for vl_integrate
;   VL_GROUND         ground tier: the points 0..VL_GROUND-1 can touch it;
;                     VL_HEIGHTS (address, one row per pixel), VL_RADIUS,
;                     VL_PROBE, VL_SLOPE_MAX, VL_FAR, VL_BOUNCE, the tables
;                     vl_norm_x / vl_norm_y (program, dev/tools/verlet/emit)
;   VL_WRAP_MARGIN    for vl_wrap (lap length in the word vl_lap_len)
; Switches (undefined = off): VL_INTEGRATE_LEFTWALL, VL_CEILING_CLAMP,
;   VL_CON_VARIANTS, VL_CON_HEAVY_POINT/_SHIFT, VL_CON_MINLEN_POINT/VL_CON_MINLEN,
;   VL_PAIR_DAMP, .define VL_ROT_SEG / VL_MULTURN_SEG "segment";
;   VL_PIN (pinned points: vl_pin), VL_CON_FIXED_K = s (gain 2^s, no k8
;   table), VL_CON_MIN_ONLY (bit 7 of vl_con_b: the link only pushes),
;   VL_THRUST = n (vl_thrust_axis / _perp, vl_push, vl_push_all), VL_Y_HIGH
;   (y 16.8: vl_yu, vl_oyu; VL_GROUND_BASE = the row added to the heights).
;   VL_GROUND_SEGMENTS = n (verlet_seg.asm: a ground of n line segments,
;   walls and loops; VL_SEG_DEPTH; vl_sg_* tables from dev/tools/verlet/
;   segments.py; BSS vl_sgi), VL_GROUND_KIND = table (vl_ground_any: per
;   point, 0 = the height map, else the segments).
;   VL_CIRC = n (verlet_circ.asm: points 0..n-1 are circles, vl_rad; with
;   VL_CIRC_Q, VL_CIRC_BOUNCE, VL_CIRC_VMIN, VL_CIRC_HEAVY (vl_cheavy),
;   VL_CIRC_FRICTION, VL_CIRC_SLEEP (vl_still), VL_NBOX): +10 B zero page
;   (+4 without a ground: vl_vy, vl_vt), opens the 20-byte tier; BSS vl_rad,
;   vl_chits.
;
; Zero page (each slot skipped if the program defined the name first, the
; math.inc pattern: alias it onto the program's own scratch):
;   core 7 B          vl_val (2), vl_vx (2), vl_w0, vl_w1, vl_w2
;   +13 = 20 B        with VL_NCON, VL_GROUND or VL_ROTATE: vl_dx (2), vl_dy (2),
;                     vl_ca, vl_cb, vl_cur, vl_qx, vl_fcoef, vl_pen (2), vl_vn (2)
;   +13 = 33 B        with VL_GROUND: vl_vy (2), vl_vt (2), vl_nx, vl_ny,
;                     vl_tptr (2), vl_hxl, vl_hxh, vl_hgt, vl_hm2, vl_hp2
;   +4                with VL_THRUST: vl_tx (2), vl_ty (2) (the push vector)
; BSS (same rule): the points as a structure of arrays, VL_NPOINTS bytes
; each: vl_xf vl_xl vl_xh (x 16.8, 24 bits) vl_yf vl_yh (y 8.8) and the old
; positions vl_oxf vl_oxl vl_oxh vl_oyf vl_oyh, declared in that order (the
; offset vl_oxf - vl_xf moves a point's old position with the same X);
; with VL_Y_HIGH, vl_yu after vl_yh and vl_oyu after vl_oyh (y 16.8, 24 bits);
; vl_pin (VL_PIN: VL_NPOINTS bytes, non-zero = pinned, set by the program);
; vl_gnd (VL_GROUND bytes, 1 = in contact this tick); vl_turn (signed
; multiplier of vl_turn_pair / vl_shift_point); vl_con_row, vl_cidx
; (VL_CON_VARIANTS); vl_squashed (VL_CON_MINLEN_POINT). DATA: vl_lap_len
; (word, 0 = no wrap) with VL_WRAP_MARGIN.
; Program tables (dev/tools/verlet emit): vl_con_a, vl_con_b (points per
; constraint), vl_con_l2l / vl_con_l2h (rest length^2, quarter px), vl_con_k8.
; ============================================================================

.ifndef _VERLET_INC_LOADED_
_VERLET_INC_LOADED_ = 1

.ifndef _MATH_INC_LOADED_
.error "verlet.inc: include math.inc first (vl_ routines multiply through lib/math)"
.endif
.ifndef VL_NPOINTS
.error "verlet.inc: define VL_NPOINTS (number of points) before the include"
.endif
.assert VL_NPOINTS >= 1 .and VL_NPOINTS <= 51, error, "verlet.inc: VL_NPOINTS is 1..51 (5 N < 256)"

; the tiers
.ifdef VL_CIRC                  ; the contacts work in the 20-byte tier
.assert VL_CIRC >= 1 .and VL_CIRC <= VL_NPOINTS, error, "verlet.inc: VL_CIRC is 1..VL_NPOINTS"
.ifndef VL_ROTATE
VL_ROTATE = 1
.endif
.endif
.if .defined(VL_NCON) .or .defined(VL_GROUND) .or .defined(VL_ROTATE) .or .defined(VL_THRUST)
_VL_TIER2 = 1
.else
_VL_TIER2 = 0
.endif
.ifdef VL_GROUND
_VL_TIER3 = 1
.assert VL_GROUND >= 1 .and VL_GROUND <= VL_NPOINTS, error, "verlet.inc: VL_GROUND is 1..VL_NPOINTS"
.assert MUL_ACC, error, "verlet.inc: the ground needs MUL_ACC = 1 (lib/math)"
.else
_VL_TIER3 = 0
.endif

.segment "ZEROPAGE"
.ifndef vl_val
vl_val:   .res 2                ; signed 8.8 operand of the add/sub helpers
.endif
.ifndef vl_vx
vl_vx:    .res 2
.endif
.ifndef vl_w0
vl_w0:    .res 1                ; 24-bit scratch
.endif
.ifndef vl_w1
vl_w1:    .res 1
.endif
.ifndef vl_w2
vl_w2:    .res 1
.endif
.if _VL_TIER2
.ifndef vl_dx
vl_dx:    .res 2                ; point cb - point ca (vl_delta_ab)
.endif
.ifndef vl_dy
vl_dy:    .res 2
.endif
.ifndef vl_ca
vl_ca:    .res 1
.endif
.ifndef vl_cb
vl_cb:    .res 1
.endif
.ifndef vl_cur
vl_cur:   .res 1                ; current constraint / point
.endif
.ifndef vl_qx
vl_qx:    .res 1
.endif
.ifndef vl_fcoef
vl_fcoef: .res 1
.endif
.ifndef vl_pen
vl_pen:   .res 2
.endif
.ifndef vl_vn
vl_vn:    .res 2
.endif
.endif
.if _VL_TIER3
.ifndef vl_vy
vl_vy:    .res 2
.endif
.ifndef vl_vt
vl_vt:    .res 2                ; tangential speed (the ground hooks)
.endif
.ifndef vl_nx
vl_nx:    .res 1                ; ground normal, 64 = 1.0 (tangent = -ny, nx)
.endif
.ifndef vl_ny
vl_ny:    .res 1
.endif
.ifndef vl_tptr
vl_tptr:  .res 2                ; into the height map
.endif
.ifndef vl_hxl
vl_hxl:   .res 1                ; vl_height_at argument (world pixel)
.endif
.ifndef vl_hxh
vl_hxh:   .res 1
.endif
.ifndef vl_hgt
vl_hgt:   .res 1                ; ground row under the point
.endif
.ifndef vl_hm2
vl_hm2:   .res 1                ; and VL_PROBE pixels to each side
.endif
.ifndef vl_hp2
vl_hp2:   .res 1
.endif
.endif
.ifdef VL_THRUST
.ifndef vl_tx
vl_tx:    .res 2                ; the push vector (vl_thrust_axis / _perp)
.endif
.ifndef vl_ty
vl_ty:    .res 2
.endif
.endif
; VL_GROUND_SEGMENTS = n: the segment ground (verlet_seg.asm). No zero page
; of its own: its scan works in the ground tier's height-map scratch (vl_hxl,
; vl_hxh, vl_hgt, vl_hm2, vl_hp2, vl_tptr). BSS vl_sgi (below).
.ifdef VL_GROUND_SEGMENTS
.if .not _VL_TIER3
.error "verlet.inc: VL_GROUND_SEGMENTS needs VL_GROUND (the points that touch the ground)"
.endif
.assert VL_GROUND_SEGMENTS >= 1 .and VL_GROUND_SEGMENTS <= 128, error, "verlet.inc: VL_GROUND_SEGMENTS is 1..128"
.endif
; VL_CIRC = n: the circle contacts (verlet_circ.asm)
.ifdef VL_CIRC
.ifndef vl_qy
vl_qy:    .res 1                ; |dy| in Q units
.endif
.ifndef vl_crad
vl_crad:  .res 1                ; the radii sum R
.endif
.ifndef vl_cnx
vl_cnx:   .res 1                ; |n| (64 = 1.0)
.endif
.ifndef vl_cny
vl_cny:   .res 1
.endif
.ifndef vl_csnx
vl_csnx:  .res 1                ; n, signed
.endif
.ifndef vl_csny
vl_csny:  .res 1
.endif
.ifndef vl_csgn
vl_csgn:  .res 1                ; bit 7: dx < 0, bit 6: dy < 0 (boxes: 1, 0 outside)
.endif
.ifndef vl_cflag
vl_cflag: .res 1                ; bit 7/6: a/b pinned, 5/4: a/b heavy
.endif
.ifndef vl_cj
vl_cj:    .res 2                ; a share (push, impulse)
.endif
.ifndef vl_vy
vl_vy:    .res 2                ; (the ground's, else here: the boxes)
.endif
.ifndef vl_vt
vl_vt:    .res 2
.endif
.endif

.segment "BSS"
.ifndef vl_xf
vl_xf:    .res VL_NPOINTS
.endif
.ifndef vl_xl
vl_xl:    .res VL_NPOINTS
.endif
.ifndef vl_xh
vl_xh:    .res VL_NPOINTS
.endif
.ifndef vl_yf
vl_yf:    .res VL_NPOINTS
.endif
.ifndef vl_yh
vl_yh:    .res VL_NPOINTS
.endif
.ifdef VL_Y_HIGH
.ifndef vl_yu
vl_yu:    .res VL_NPOINTS        ; y bits 16..23 (y 16.8)
.endif
.endif
.ifndef vl_oxf
vl_oxf:   .res VL_NPOINTS
.endif
.ifndef vl_oxl
vl_oxl:   .res VL_NPOINTS
.endif
.ifndef vl_oxh
vl_oxh:   .res VL_NPOINTS
.endif
.ifndef vl_oyf
vl_oyf:   .res VL_NPOINTS
.endif
.ifndef vl_oyh
vl_oyh:   .res VL_NPOINTS
.endif
.ifdef VL_Y_HIGH
.ifndef vl_oyu
vl_oyu:   .res VL_NPOINTS
.endif
.endif
.ifdef VL_PIN
.ifndef vl_pin
vl_pin:   .res VL_NPOINTS        ; non-zero: the point is pinned
.endif
.endif
.if _VL_TIER3
.ifndef vl_gnd
vl_gnd:   .res VL_GROUND
.endif
.endif
.ifdef VL_GROUND_SEGMENTS
.ifndef vl_sgi
vl_sgi:   .res VL_GROUND             ; segment of the contact, $FF none (vl_seg_ground)
.endif
.endif
.if _VL_TIER2
.ifndef vl_turn
vl_turn:  .res 1
.endif
.endif
.ifdef VL_CIRC
.ifndef vl_rad
vl_rad:   .res VL_CIRC          ; radius (Q units), 0 = not a circle; set by the program
.endif
.ifdef VL_CIRC_HEAVY
.ifndef vl_cheavy
vl_cheavy: .res VL_CIRC         ; non-zero: a heavy point (set by the program)
.endif
.endif
.ifndef vl_chits
vl_chits: .res 1                ; contacts counted by vl_contact_all / _box
.endif
.ifdef VL_CIRC_SLEEP
.ifndef vl_still
vl_still: .res VL_CIRC          ; slow ticks in a row (vl_circ_sleep)
.endif
.endif
.endif
.ifdef VL_CON_VARIANTS
.ifndef vl_con_row
vl_con_row: .res 1              ; the variant (0..VL_CON_VARIANTS-1), set by the program
.endif
.ifndef vl_cidx
vl_cidx:  .res 1
.endif
.endif
.ifdef VL_CON_MINLEN_POINT
.ifndef vl_squashed
vl_squashed: .res 1             ; set (1) by a short link, cleared by the program
.endif
.endif
.ifdef VL_WRAP_MARGIN
.segment "DATA"
.ifndef vl_lap_len
vl_lap_len: .word 0
.endif
.endif

.segment "CODE"

; ----------------------------------------------------------------------------
; VL_CLAMP_VAL lim -- vl_val = clamp(vl_val, -lim, lim), signed; ends in RTS
; (the body of vl_clamp_vx / vl_clamp_vy). ~25 cycles.
; ----------------------------------------------------------------------------
.macro VL_CLAMP_VAL lim
        LDA     vl_val+1
        BMI     @neg
        LDA     #<(lim)
        CMP     vl_val
        LDA     #>(lim)
        SBC     vl_val+1
        BCS     @ok
        LDA     #<(lim)
        STA     vl_val
        LDA     #>(lim)
        STA     vl_val+1
@ok:    RTS
@neg:   LDA     vl_val
        CMP     #<(-(lim))
        LDA     vl_val+1
        SBC     #>(-(lim))
        BCS     @ok
        LDA     #<(-(lim))
        STA     vl_val
        LDA     #>(-(lim))
        STA     vl_val+1
        RTS
.endmacro

; ----------------------------------------------------------------------------
; VL_CEILING -- inline: no point above row >VL_CEILING_CLAMP (y = old y =
; the ceiling: no speed upwards). Rows as unsigned bytes (with VL_Y_HIGH: y
; signed 24 bits, the ceiling < 256 rows). X ends at $FF. ~16 cycles a point.
; ----------------------------------------------------------------------------
.macro VL_CEILING
        .assert <VL_CEILING_CLAMP = 0, error, "VL_CEILING_CLAMP: whole rows"
.ifdef VL_Y_HIGH
        .assert VL_CEILING_CLAMP < $10000, error, "VL_CEILING_CLAMP: < 256 rows"
        LDX     #VL_NPOINTS-1
:       LDA     vl_yu,X
        BMI     :+                      ; above row 0
        BNE     :++                     ; row 256 or below
        LDA     vl_yh,X
        CMP     #>VL_CEILING_CLAMP
        BCS     :++
:       LDA     #>VL_CEILING_CLAMP
        STA     vl_yh,X
        STA     vl_oyh,X
        LDA     #0
        STA     vl_yf,X
        STA     vl_oyf,X
        STA     vl_yu,X
        STA     vl_oyu,X
:       DEX
        BPL     :---
.else
        LDX     #VL_NPOINTS-1
:       LDA     vl_yh,X
        CMP     #>VL_CEILING_CLAMP
        BCS     :+
        LDA     #>VL_CEILING_CLAMP
        STA     vl_yh,X
        STA     vl_oyh,X
        LDA     #0
        STA     vl_yf,X
        STA     vl_oyf,X
:       DEX
        BPL     :--
.endif
.endmacro

; ----------------------------------------------------------------------------
; VL_REST -- inline: old position := position for every point (at rest).
; X ends at $FF. ~40 cycles a point.
; ----------------------------------------------------------------------------
.macro VL_REST
        LDX     #VL_NPOINTS-1
:       LDA     vl_xf,X
        STA     vl_oxf,X
        LDA     vl_xl,X
        STA     vl_oxl,X
        LDA     vl_xh,X
        STA     vl_oxh,X
        LDA     vl_yf,X
        STA     vl_oyf,X
        LDA     vl_yh,X
        STA     vl_oyh,X
.ifdef VL_Y_HIGH
        LDA     vl_yu,X
        STA     vl_oyu,X
.endif
        DEX
        BPL     :-
.endmacro

.endif  ; _VERLET_INC_LOADED_
