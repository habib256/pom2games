; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; physdefs.inc -- CUTROPE's lib/physics setup and its variables
; ============================================================================
; Include at the top, after math.inc and cutconst.inc (tools/cutrope.py
; writes it). phys.inc holds the code. The switches used: VL_PIN (the
; ropes' pins, the points a level does not use, the points of a cut rope),
; VL_CON_FIXED_K (links of gain 2^5, no k8 table), VL_CON_HEAVY_POINT (the
; candy, point 0), VL_CEILING_CLAMP (under the two text lines),
; VL_GROUND_SEGMENTS (the level's platforms and spikes, copied into the
; vl_sg_* tables of BSS at each load; the slots it does not use have a box
; that holds no pixel) with the friction hook; the speed switches
; VL_CON_SKIP_ZERO and VL_CON_FAST (exact).
; ============================================================================

VL_NPOINTS      = NPTS          ; 0 = the candy, then each rope's pin and points
VL_NCON         = NCON
VL_GRAVITY      = GRAVITY
VL_VMAX_X       = VMAX
VL_VMAX_Y       = VMAX
VL_GROUND       = 1             ; the candy alone touches the segments
VL_RADIUS       = RADIUS
VL_BOUNCE       = BOUNCE
VL_GROUND_SEGMENTS = NSEG
VL_SEG_DEPTH    = DEPTH
VL_PIN          = 1
VL_CON_FIXED_K  = FIXED_K
VL_CON_SKIP_ZERO = 1            ; (speed, exact: f = 0 returns at once)
VL_CON_FAST     = 1             ; (speed, exact: square table, inline links)
VL_CON_HEAVY_POINT = 0
VL_CON_HEAVY_SHIFT = HEAVY
VL_CEILING_CLAMP = CEIL
.include "verlet.inc"

.macro VL_GROUND_TANGENT                ; friction: vt -= vt >> FRICTION
        LDY     #8 - FRICTION
        JSR     vl_damp
.endmacro

.segment "BSS"
; the state (tests/test_cutrope.py snapshots cr_state..cr_cool in this order)
cr_state:   .res 1              ; PLAY, WON, LOST
cr_on:      .res 1              ; ropes still on (bit r)
cr_stars:   .res 1              ; stars taken (bit s)
cr_nstar:   .res 1              ; their count
cr_ev:      .res 1              ; this tick's events (EV_*)
cr_bub:     .res 1              ; the bubble: BUB_NONE, BUB_FREE, BUB_CAUGHT
cr_cool:    .res NCUSH          ; ticks before each cushion puffs again
in_cut:     .res 1              ; the tick's inputs: ropes cut by key (bit r)
in_cx:      .res 1              ;   the cursor (px)
in_cy:      .res 1
in_btn:     .res 1              ;   the button held (0 / 1)
; the level (phys_load)
cr_nrope:   .res 1
cr_nseg:    .res 1
rope_l0:    .res NROPE          ; first link of each rope
rope_n:     .res NROPE          ; its links
star_x:     .res 3
star_y:     .res 3
frog_x:     .res 1
frog_y:     .res 1
bub_x:      .res 1              ; the bubble's centre
bub_y:      .res 1
cr_ncush:   .res 1
cu_x:       .res NCUSH          ; the cushions: centre, direction (0 R 1 D 2 L 3 U)
cu_y:       .res NCUSH
cu_dir:     .res NCUSH
seg_kind:   .res NSEG           ; 0 platform, 1 spikes, 2 trampoline
seg_x0:     .res NSEG           ; the drawn line (whole px)
seg_y0:     .res NSEG
seg_x1:     .res NSEG
seg_y1:     .res NSEG
; lib/physics tables, filled by phys_load
vl_con_a:   .res NCON
vl_con_b:   .res NCON
vl_con_l2l: .res NCON
vl_con_l2h: .res NCON
vl_sg_x0f:  .res NSEG           ; (this order: the level record's)
vl_sg_x0l:  .res NSEG
vl_sg_y0f:  .res NSEG
vl_sg_y0h:  .res NSEG
vl_sg_nx:   .res NSEG
vl_sg_ny:   .res NSEG
vl_sg_sl:   .res NSEG
vl_sg_sh:   .res NSEG
vl_sg_bx0l: .res NSEG
vl_sg_bx0h: .res NSEG
vl_sg_bx1l: .res NSEG
vl_sg_bx1h: .res NSEG
vl_sg_by0:  .res NSEG
vl_sg_by1:  .res NSEG
; scratch
cr_r:       .res 1
cr_k:       .res 1
cr_p:       .res 1
cr_l:       .res 1
cr_end:     .res 1
cr_q:       .res 2
cr_dx:      .res 1              ; near(): a link's delta, the cursor from a
cr_dy:      .res 1
cr_ux:      .res 1
cr_uy:      .res 1
cr_c:       .res 3              ; the cross product
cr_lim:     .res 2
cr_vin:     .res 2              ; the candy's vy before the ground contact
cr_tx:      .res 1              ; within(): the target
cr_ty:      .res 1
.segment "ZEROPAGE"
lvp:        .res 2              ; the level record
.segment "CODE"
