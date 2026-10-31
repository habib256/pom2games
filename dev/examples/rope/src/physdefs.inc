; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; physdefs.inc -- the rope's lib/physics setup and its variables
; ============================================================================
; Include at the top, after math.inc and ropeconst.inc (tools/rope.py writes
; it). phys.inc holds the code. The switches used: VL_PIN (the pin, point 0),
; VL_CON_FIXED_K (links of gain 2^6, no k8 table), VL_CON_HEAVY_POINT (the
; weight, point 8), VL_CEILING_CLAMP (the screen's top; the side walls
; are phys.inc's); the ground hook damps the tangential speed (friction).
; ============================================================================

VL_NPOINTS      = 9             ; 0 = the pin, 1..7 the rope, 8 = the weight
VL_NCON         = 8
VL_GRAVITY      = GRAVITY
VL_VMAX_X       = VMAX
VL_VMAX_Y       = VMAX
VL_GROUND       = 9
VL_HEIGHTS      = heights
VL_RADIUS       = RADIUS
VL_PROBE        = PROBE
VL_SLOPE_MAX    = SLOPE_MAX
VL_FAR          = FAR
VL_BOUNCE       = BOUNCE
VL_PIN          = 1
VL_CON_FIXED_K  = FIXED_K
VL_CON_HEAVY_POINT = 8
VL_CON_HEAVY_SHIFT = HEAVY
VL_CEILING_CLAMP = CEIL
.include "verlet.inc"

.macro VL_GROUND_TANGENT                ; friction: vt -= vt >> FRICTION
        LDY     #8 - FRICTION
        JSR     vl_damp
.endmacro

.segment "BSS"
; the state (tests/test_rope.py snapshots rp_px..rp_cut in this order)
rp_px:      .res 1              ; the pin: column
rp_py:      .res 1              ;          row
rp_mode:    .res 1              ; 0 swing, 1 floor
rp_cut:     .res 1              ; 1: the weight is free
rp_k:       .res 1              ; (loops)
in_mv:      .res 1              ; the tick's inputs: pin move (-1, 0, 1)
in_mode:    .res 1              ; wanted mode
in_cut:     .res 1              ; wanted cut
.segment "CODE"
