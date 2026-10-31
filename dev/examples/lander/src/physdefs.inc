; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; physdefs.inc -- the lander's lib/physics setup and its variables
; ============================================================================
; Include at the top, after math.inc and landconst.inc (tools/lander.py
; writes it). phys.inc holds the code. The switches used: VL_Y_HIGH (a world
; of WORLD_H rows, y 16.8) with VL_GROUND_BASE, VL_CON_FIXED_K (links of gain
; 2^6, no k8 table), VL_THRUST (the engine), VL_PAIR_DAMP (the spin fades),
; VL_INTEGRATE_LEFTWALL and VL_CEILING_CLAMP; the ground hook damps the
; tangential speed (friction).
; ============================================================================

FLY     = 0                     ; lv_status
LANDED  = 1
CRASHED = 2

VL_NPOINTS      = 3             ; 0 = left leg, 1 = right leg, 2 = top
VL_NCON         = 3
VL_GRAVITY      = GRAVITY
VL_VMAX_X       = VMAX
VL_VMAX_Y       = VMAX
VL_GROUND       = 3             ; the top too: it touching is a crash
VL_HEIGHTS      = heights
VL_RADIUS       = RADIUS
VL_PROBE        = PROBE
VL_SLOPE_MAX    = SLOPE_MAX
VL_FAR          = FAR
VL_BOUNCE       = BOUNCE
VL_Y_HIGH       = 1
VL_GROUND_BASE  = GROUND_BASE
VL_CON_FIXED_K  = FIXED_K
VL_THRUST       = THRUST_SHIFT
VL_PAIR_DAMP    = SPIN_DAMP
VL_INTEGRATE_LEFTWALL = LEFT_WALL
VL_CEILING_CLAMP = CEIL
.include "verlet.inc"

.macro VL_GROUND_TANGENT                ; friction: vt -= vt >> FRICTION
        LDY     #8 - FRICTION
        JSR     vl_damp
.endmacro

.segment "BSS"
; the state (tests/test_lander.py snapshots lv_status..lv_pad in this order)
lv_status:  .res 1              ; FLY, LANDED, CRASHED
lv_fuel:    .res 1
lv_fsub:    .res 1              ; a fuel unit every 2 thrust ticks
lv_settle:  .res 1              ; ticks with a leg down
lv_contact: .res 1              ; a leg was down last tick
lv_timer:   .res 1              ; ticks since the crash (to 255)
lv_pad:     .res 1              ; landed: the pad (1..NPADS)
lv_vy:      .res 2              ; speed of the top before the tick
lv_tilt:    .res 2              ; y right leg - y left leg
lv_steep:   .res 1
in_thr:     .res 1              ; the tick's inputs: engine (0 / 1)
in_rot:     .res 1              ; turn (-1, 0, 1)
st_x:       .res 1              ; phys_reset: the legs' middle (px)
st_y:       .res 2              ; and their row
st_vx:      .res 2              ; speed (8.8)
st_vy:      .res 2
.segment "CODE"
