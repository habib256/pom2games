; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; physdefs.inc -- the catapult's lib/physics setup and its variables
; ============================================================================
; Include at the top, after math.inc and catconst.inc (tools/catapult.py
; writes it). phys.inc holds the code. The switches used: VL_CIRC (points
; 0..6 are circles: verlet_circ.asm) with VL_CIRC_BOUNCE / _VMIN, _HEAVY
; (the projectile), _FRICTION (on the boxes), _SLEEP (targets asleep until
; hit, a group at a time); VL_PIN (the arm's base, the aimed projectile, sleepers),
; VL_CON_FIXED_K (the arm, a 24-px link: gain 2^4), VL_THRUST (the arm's
; release: vl_thrust_perp + vl_push on the tip); the ground hook damps the
; tangential speed (friction).
; ============================================================================

AIM     = 0                     ; cp_phase
SWING   = 1
FLY     = 2
OVER    = 3
PROJ    = 0
BASE    = 7
TIP     = 8

VL_NPOINTS      = 9             ; 0 projectile, 1..6 targets, 7 base, 8 tip
VL_NCON         = 1
VL_GRAVITY      = GRAVITY
VL_VMAX_X       = VMAX
VL_VMAX_Y       = VMAX
VL_GROUND       = 7             ; the circles
VL_HEIGHTS      = heights
VL_RADIUS       = RAD << CQ
VL_PROBE        = PROBE
VL_SLOPE_MAX    = SLOPE_MAX
VL_FAR          = FAR
VL_BOUNCE       = GBOUNCE
VL_PIN          = 1
VL_CON_FIXED_K  = FIXED_K
VL_THRUST       = THRUST
VL_AXIS_A       = BASE
VL_AXIS_B       = TIP
VL_CIRC         = 7
VL_CIRC_Q       = CQ
VL_CIRC_BOUNCE  = CBOUNCE
VL_CIRC_VMIN    = CVMIN
VL_CIRC_HEAVY   = CHEAVY
VL_CIRC_FRICTION = CFRICTION
VL_CIRC_SLEEP   = CSLEEP
VL_CIRC_SLEEP_TICKS = CSLEEP_TICKS
VL_NBOX         = NBOX
.include "verlet.inc"

.macro VL_GROUND_TANGENT                ; friction: vt -= vt >> GFRICTION
        LDY     #8 - GFRICTION
        JSR     vl_damp
.endmacro

.segment "BSS"
; the state (tests/test_catapult.py snapshots cp_phase..cp_down in this order)
cp_phase:   .res 1              ; AIM, SWING, FLY, OVER
cp_shots:   .res 1              ; shots left
cp_score:   .res 1              ; targets down
cp_timer:   .res 2              ; ticks of the swing / the shot
cp_power:   .res 1              ; 0..PMAX
cp_stop:    .res 1              ; 0..NSTOP-1
cp_down:    .res 6              ; target k down (scored)
cp_k:       .res 1              ; (loops)
cp_was:     .res 6              ; the targets' pins before the contacts
in_power:   .res 1              ; the tick's inputs
in_stop:    .res 1
in_fire:    .res 1
.segment "CODE"
