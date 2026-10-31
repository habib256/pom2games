# lib/physics — integer Verlet physics (asm)

*[← dev](../../README.md)*

Points, distance constraints without a square root and a height-map ground
for the 6502, taken out of DIRTBIKE (2026-10-31) so that other
physics-based games can start from them. Every result is **exact** and
matches the Python package [`dev/tools/verlet`](../../tools/verlet/__init__.py)
bit for bit: design and tune the physics in Python (fast, scriptable, a
solver can search it), generate the constants and tables with
`verlet.emit`, then run the same physics on the 6502.

Units: x is 16.8 (24 bits: world pixels on a long track), y 8.8 (screen
rows, growing downwards) or 16.8 with `VL_Y_HIGH` (a world taller than one
screen); velocities and deltas are signed 8.8, the velocity of a point
being `pos - old pos`. Shifts round down (Python `>>`), except the
heavy-point share and the fixed gain (toward zero).

## Setup

```asm
MUL_TABLES = $0800              ; lib/math, MUL_ACC = 1 if there is a ground
MUL_ACC    = 1
.include "math.inc"
VL_NPOINTS = 3                  ; parameters and switches (below)
VL_NCON    = 3
VL_GRAVITY = $0030
VL_VMAX_X  = $1200
VL_VMAX_Y  = $0800
...                             ; optional: alias vl_* onto your own variables
.include "verlet.inc"           ; AT THE TOP: zero page, points, macros
...
; at the END, after the callers (.ifref), in this order:
.include "verlet_circ.asm"      ; (circle contacts: first; then sqrt.asm below)
.include "verlet_seg.asm"       ; (a segment ground: before verlet_hmap.asm)
.include "verlet_hmap.asm"
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "mul.asm"
```

`apple2.mk` adds `-I $(PHYSICS)` to `A2_INCS` and tracks the files in
`A2_ASM_DEPS`. The program provides the tables (`dev/tools/verlet/emit.py`
writes them from the model, see `dirtbike/tools/physconst.py`):
`vl_con_a`, `vl_con_b` (points of each constraint; bit 7 of `vl_con_b` =
minimum only with `VL_CON_MIN_ONLY`), `vl_con_l2l` / `vl_con_l2h` (rest
length², quarter pixels: `verlet.l2q`), `vl_con_k8` (gain: `verlet.k8`;
not with `VL_CON_FIXED_K`), and with a ground `vl_norm_x` / `vl_norm_y` (31
normals for slopes −15..15 at 64 = 1.0: `verlet.normals`). Each routine is
assembled only when the program references it before the include; an alias
counts as a reference.

## Routines

Cycles measured in a2run (`call:`) on DIRTBIKE-like states, the JSR
included.

| File | Routine | Effect | Cost |
|---|---|---|---|
| `verlet.asm` | `vl_integrate` | point X: `vx = clamp(x−ox, ±VL_VMAX_X)`, `vy = clamp(y−oy+VL_GRAVITY, ±VL_VMAX_Y)`, old := pos, pos += v | ~310 c |
| | `vl_integrate_all` | every point, X = N−1..0 | ~320 c/point |
| | `vl_add_xv` `vl_sub_xv` `vl_add_yv` `vl_sub_yv` | point X ± the signed 8.8 `vl_val` (x sign-extended to 24 bits), keep X | ~30 c |
| | `vl_clamp_vx` / `vl_clamp_vy` | `vl_val = clamp(vl_val, ±VMAX)` | ~25 c |
| | `vl_delta_ab` | `vl_dx`/`vl_dy` = point `vl_cb` − point `vl_ca` (16 bits) | ~60 c |
| | `vl_pair_damp` | `VL_PAIR_DAMP` = n: the relative speed of points `VL_PAIR_B`/`VL_PAIR_A` (1/0) fades by 1/2ⁿ, their common speed stays | ~470 c |
| | `vl_damp` | `vl_vt −= vl_vt >> (8−Y)`, Y = 1..7: friction in a ground hook | ~70 c |
| | `vl_wrap` | `vl_lap_len` > 0 and point `VL_WRAP_POINT` (0) at `vl_lap_len + VL_WRAP_MARGIN` px or beyond: every point moves back a lap, then the `VL_WRAP_AFTER` hook | ~20 c / ~170 c |
| | `vl_rest` / `VL_REST` | old := pos for every point (routine / inline macro) | ~40 c/point |
| | `vl_ceiling` / `VL_CEILING` | no point above `VL_CEILING_CLAMP` (y = old y = it) | ~16 c/point |
| `verlet_con.asm` | `vl_con_pass` | the `VL_NCON` constraints once, in order | ~1,450 c/link |
| | `vl_constrain` | constraint `vl_cur` (see below) | 1,000-1,500 c |
| | `vl_heavy` | the heavy-point share (`VL_CON_HEAVY_*`) | ~90 c |
| | `vl_quarter_abs` | A/X signed → `A = min(|d >> 6|, 180)` | ~60 c |
| | `vl_square` | A = 0..180 → A/Y = A² from the quarter-square table | ~40 c |
| | `vl_push` / `vl_push_all` | (`VL_THRUST`) point X / every point but the pinned ones += the push vector `vl_tx`/`vl_ty` (a speed change) | 125 c / 397 c (3 points) |
| `verlet_rot.asm` | `vl_turn_pair` | turn the axis `VL_AXIS_A`→`VL_AXIS_B` (0→1): B += `vl_turn`·(−dy, dx) >> 8, A −= the same | ~650 c |
| | `vl_thrust_axis` / `vl_thrust_perp` | (`VL_THRUST` = n) `vl_tx`/`vl_ty` = the axis (or its perpendicular (−dy, dx)) · `vl_turn` >> (8 + n): with a link of rest length L, L·`vl_turn`/2⁸⁺ⁿ px | 561 c / 620 c (n = 4) |
| | `vl_shift_point` | point `VL_SHIFT_POINT` and its old position += `vl_turn`·axis >> 8 (a move, no speed) | ~580 c |
| | `vl_axis`, `vl_mul_turn` | the axis delta; `vl_val = (A/X · vl_turn) >> 8` | |
| `verlet_hmap.asm` | `vl_height_at` | A = `VL_HEIGHTS[vl_hxh:vl_hxl]` (16-bit index, no wrap), keeps X | ~30 c |
| | `vl_ground` | point X (< `VL_GROUND`) against the ground (below) | ~270 c far, ~400 c near, 2,100-3,100 c in contact |
| `verlet_seg.asm` | `vl_seg_ground` | point X (< `VL_GROUND`) against `VL_GROUND_SEGMENTS` line segments (below); `vl_sgi,X` = the segment | 22 segments: 660 c far, 920 c in a box, 2,640 c flat / 2,840 c wall / 4,210 c 45° / 5,100-5,570 c on a loop in contact |
| | … with `VL_SEG_CACHE` | the point's last segment first | 2,100 c flat / 2,230 c wall / 3,620 c 45° or loop; 6,540 c at a joint |
| | `vl_ground_any` | (`VL_GROUND_KIND`) `vl_ground` or `vl_seg_ground` by the table byte of point X | +9 c |
| `verlet_circ.asm` | `vl_contact_pair` | (`VL_CIRC`) A = the radii sum R: circles `vl_ca`, `vl_cb` pushed apart, a closing speed turned by an impulse (below); C = 1 in contact | 52 c apart, ~475 c near, 2,270 c (separating) - 3,270 c (glancing, closing) in contact |
| | `vl_contact_all` | every pair of the `VL_CIRC` circles (radius 0: left out); `vl_chits` += contacts | ~100 c a pair apart; 6 pairs, 3 in contact: 9,300 c |
| | `vl_contact_box` | point X against the `VL_NBOX` static boxes (closest point, or out through the nearest face); C = 1 in contact | ~60 c a box apart, 2,550 c (inside) - 3,800 c (a corner) in contact |
| | `vl_circ_sleep` | (`VL_CIRC_SLEEP`) point X asleep after 16 slow ticks (`vl_pin,X` = $80) | ~60 c |

A whole DIRTBIKE tick (3 points, 2 constraint passes, 2 ground probes, the
bike's own code) is ~14,400 cycles.

The switches below measured on a 3-point body (link 12 px, a little
stretched), against the plain code: `vl_constrain` 1,155 c → 986 c with
`VL_CON_FIXED_K` (−169, −15 %, −34 B, no k8 table), +27 c with `VL_PIN`
and no pin (1,130 c with a pinned end), +13 c with `VL_CON_MIN_ONLY`, +42 c
with `VL_Y_HIGH`; `vl_integrate` 295 c → 323 c (`VL_Y_HIGH`), +7 c
(`VL_PIN`, a pinned point ~17 c); `vl_ground` in contact (flat) 2,211 c →
2,281 c, far 276 c → 299 c (`VL_Y_HIGH`). Code: `VL_PIN` +101 B,
`VL_CON_MIN_ONLY` +12 B, `VL_Y_HIGH` +80 B, `vl_thrust_perp` +
`vl_push_all` 162 B.

**Pins** (`VL_PIN`): `vl_pin,X` non-zero (the program sets the table; BSS
is not cleared) pins point X: `vl_integrate` and `vl_push_all` leave it
alone, a link with one pinned end moves the other end by the whole
correction 2c (infinite mass; the heavy point does not apply), both ends
pinned move nothing. The program moves a pinned point itself (x = ox: at
rest). `vl_ground`, `vl_turn_pair`, `vl_shift_point`, `vl_push` ignore
pins.

**Thrust** (`VL_THRUST` = n): `vl_thrust_perp` / `vl_thrust_axis` compute
the push vector once from the axis `VL_AXIS_A`→`VL_AXIS_B` and `vl_turn`
(signed), `vl_push` / `vl_push_all` add it to positions (not to old
positions: a speed change). Pushing every point is a pure translation (a
lander's engine, a boat's propeller); pushing one point turns the body.

**Constraints** (`dev/tools/verlet/constraint.py`): for points a, b at
rest length L, `q = min(|delta >> 6|, 180)` per axis (quarter pixels),
`d8 = clamp((qx² + qy² − l2) >> 3, ±4095)`, `f = clamp((d8·k8) >> 8, ±127)`
≈ (|ab| − L)/L, half per point, times the stiffness; `c = (delta·f) >> 8`,
a += c, b −= c. No square root: the error grows with the stretch, the
links are springs whose stiffness is `k8`. Ranges: |b − a| < 128 px per
axis, a link up to 45 px. With `VL_CON_VARIANTS` = V, the row of the tables
is `vl_cur·V + vl_con_row` (DIRTBIKE: the rider's rest lengths per lean
level, V = 17). With `VL_CON_FIXED_K` = s every link has the gain 2ˢ and
`f = clamp((q² − l2) / 2¹¹⁻ˢ, ±127)` rounded toward zero, without d8 and
the product: a dead band the same on both sides of the rest length (with
the floor of the product, a link a hair short pushes while one a hair long
does not, and a body flying free slowly turns). s = 6 suits links of
9-14 px in two passes (rigid gain 2⁶ = 64 ≈ `k8(11.3 px)`). A rest shape on
the quarter-pixel grid (deltas multiple of 64, e.g. a 6-8-10 triangle) has
no force at all: it falls without turning. `VL_CON_MIN_ONLY`: a link
flagged in bit 7 of `vl_con_b` does nothing while q² ≥ l2 (a minimum
distance: ragdoll limbs, bodies that must not overlap).

**Ground** (`dev/tools/verlet/ground.py`): one row per world pixel. The
slope `h[x+p] − h[x−p]` (p = `VL_PROBE`, a byte difference: keep it
within ±127) clamped to ±`VL_SLOPE_MAX` picks the normal; a point within
`VL_RADIUS` of the ground line is pushed out along it, its speed split
into `vl_vn` (normal) and `vl_vt` (tangent, forward along the ground), a
negative vn bounces (`vn = −vn·VL_BOUNCE/256`), then the speed is rebuilt
(old pos = pos − speed). `vl_gnd,X` = 1 in contact. Ground further than
`VL_FAR` below: no test. The flat ground takes the `mul_dir` short cuts
(×0, ×±64). With `VL_Y_HIGH`, y is signed 24 bits and the ground row is
the height + `VL_GROUND_BASE` (a 16-bit row, default 0): the height map
still holds bytes, the ground lies within rows BASE..BASE+255 of a taller
world (`HeightMap(base=...)`).

Hooks: macros the program defines before `verlet_hmap.asm` (empty
otherwise): `VL_GROUND_ENTER` (A = 0, X = the point, after `vl_gnd,X = 0`),
`VL_GROUND_TANGENT` (in contact, after the bounce, before the rebuild:
change `vl_vt` — traction, brake, `JSR vl_damp`; `vl_cur` = the point, old
position still the tick's), `VL_GROUND_AFTER` (after the rebuild, X = the
point, `vl_vt` final), `VL_WRAP_AFTER` (in `vl_wrap`, after the move). Use
unnamed labels in hooks (or names the routine does not use).

**Segment ground** (`verlet_seg.asm`, `dev/tools/verlet/segments.py`):
the world ground is a list of line segments, so vertical walls, ceilings,
overhangs and loops work (the height map holds one row per column, slopes
up to ±75°). Segment k starts at (x0, y0) (sub-pixel: 16.8 / 8.8), has an
integer normal (nx, ny) (64 = 1.0, pointing to the free side: on the left
of the direction p0 → p1 as seen on the screen) and runs along the tangent
(−ny, nx) for `smax` (8.8); a box in whole pixels rejects it quickly. For
the point's pixel inside a box, `d = (dx·nx + dy·ny) >> 6` (dx, dy = point −
start, 8.8) is a candidate when `−VL_SEG_DEPTH ≤ d < best` (best starts at
`VL_RADIUS`) and `s = (dy·nx − dx·ny) >> 6` lies in 0..smax; the deepest
wins (the first of the scan n−1..0 on a tie), then the resolve is
`vl_ground`'s (push by `VL_RADIUS − d` along the normal, vn / vt, bounce,
the same three hooks, rebuild; `vl_nx`/`vl_ny` = the segment's normal in
the hooks). No end caps: a joint is taken by the neighbour segment; a
point deeper than `VL_SEG_DEPTH` behind a line ignores it (a thin wall seen
from behind). `VL_SEG_CACHE` = m: a point still within its last segment
(`vl_sgi,X`), m or more from its ends, is taken without the scan (set
`vl_sgi` to $FF at start: BSS is not cleared). Limits: 1..128 segments, a
box at most 88 px a side (dx, dy, d, s stay 16-bit: `segments.py` checks,
split longer segments), boxes in pixels 0..65535 (rows 0..255, or 0..32767
with `VL_Y_HIGH`).

Choose the normals: a contact decomposes and rebuilds the speed through
the normal, so a normal of length L scales the speed by L²/4096 each tick
in contact (the 45° normal (45, −45) loses 1.1 % a tick; (50, −40), 4,100,
gains 0.1 %): `segments.near_normal()` picks the integer normal within a
few units of 4096 nearest the direction (within 2°), and
`SegmentGround.from_polyline()` places each segment's end on its exact
tangent (8.8 corners) so the joints meet. A joint where the ground turns
by θ costs a rolling point 1 − cos θ of its speed (the part into the next
segment is removed, as at a landing): a 16-segment loop (22.5°) keeps
~28 % of the speed a lap, 7-segment quarters (≤ 15°) ~83 % a quarter. A
game pumps it back (a tangent hook: dev/examples/halfpipe), or uses more
segments (the cost of a scan is ~30 cycles a segment out of its box).

**Circle contacts** (`verlet_circ.asm`, `dev/tools/verlet/contact.py`):
points 0..`VL_CIRC`−1 are circles of radius `vl_rad,X` (BSS, set by the
program) in units of 2^Q/256 px (`VL_CIRC_Q` = Q, 4..6, default 5: an
eighth of a pixel); a pair's radii add up to R ≤ 127 units (Q = 5: 15.9
px). For a pair a, b: d = b − a (x 24 bits, y 17 bits — the borrow is the
sign — or 24 with `VL_Y_HIGH`, so no wrap at 256 px or rows), a whole-pixel
test first (|Δ px| mod 256 > ⌈R⌉: out, ~52 cycles), then q = |d| >> Q per
axis, q² = qx² + qy² (quarter squares) against R², s = `isqrt16`(q²), the
penetration R − s and the normal n = q · ⌈2¹⁴/s⌉ >> 8 (64 = 1.0, exactly
64 on an axis: `mul_dir`'s short cuts; (0, −64) for s = 0). Each point
and its old position move by half of (pen·|n|) >> (6 − Q) along n (no
speed from the push); then the relative speed along n, vn = (v_b − v_a)·n
>> 6, if closing (vn < 0) gets the impulse j = m + (m·e >> 8), m = −vn,
e = `VL_CIRC_BOUNCE` when m > `VL_CIRC_VMIN` (else j = m: inelastic), half
each, through the old positions. A pinned point does not move (the other
takes all); `VL_CIRC_HEAVY` = n: a point flagged in `vl_cheavy` takes
half − half>>n against a light one. Error: no approximation of the root —
the distance is within a unit (Q = 5: 1/8 px), the normal within 1/64 per
component; a linearised push ((q² − R²)/2R², the constraint code's) would
be 2.7 times too weak at half the radius, which a fast hit reaches.
`vl_contact_box`: static boxes `vl_box_x0`/`y0`/`x1`/`y1` (program
tables, whole pixels, edges included, the point at x < 256 px, y < 256
rows): the closest point of each box gives q, s, n and the whole push to
the point; the centre inside (or within a unit) leaves through the nearest
face (top, left, right, bottom first on ties) to exactly r from it; the
speed splits into vn, vt like the ground's, a closing vn bounces (above
VMIN) or stops, `VL_CIRC_FRICTION` = f takes vt >> f, then the speed is
rebuilt. Keep VMAX ≤ $2000 (vn in 16 bits). **Sleep** (`VL_CIRC_SLEEP` =
v, with `VL_PIN`): `vl_circ_sleep` puts a free point slow on both axes
(≤ v) for `VL_CIRC_SLEEP_TICKS` (16) ticks in a row to sleep: `vl_pin,X` =
$80, at rest; `vl_integrate`, `vl_push_all`, `vl_contact_box` skip it, a
pair treats it as pinned, and a closing speed above v wakes it (pin 0).
A gentle contact leaves it asleep: a sleeping ball is the ground of an
awake one, a resting stack stays asleep. With one pass of equal masses a
ball resting on another keeps ~2g of speed: choose v above it. Waking a
whole stack when one of it wakes (a sleeper under nothing would float) is
the program's rule (dev/examples/catapult: per group).

## Zero page and variables

Each slot is allocated by `verlet.inc` unless the program defined the name
first (the `math.inc` pattern: alias `vl_val = val` onto its own scratch;
DIRTBIKE aliases all of them, so its addresses and the tests' snapshot
block did not move).

| Tier | When | Zero page |
|---|---|---|
| 7 B | always | `vl_val` (2), `vl_vx` (2), `vl_w0`, `vl_w1`, `vl_w2` |
| +13 = 20 B | `VL_NCON`, `VL_GROUND` or `VL_ROTATE` defined | `vl_dx` (2), `vl_dy` (2), `vl_ca`, `vl_cb`, `vl_cur`, `vl_qx`, `vl_fcoef`, `vl_pen` (2), `vl_vn` (2) |
| +13 = 33 B | `VL_GROUND` defined | `vl_vy` (2), `vl_vt` (2), `vl_nx`, `vl_ny`, `vl_tptr` (2), `vl_hxl`, `vl_hxh`, `vl_hgt`, `vl_hm2`, `vl_hp2` |
| +4 | `VL_THRUST` defined (it also opens the 20-byte tier) | `vl_tx` (2), `vl_ty` (2) |
| +10 (+4) | `VL_CIRC` defined (it also opens the 20-byte tier) | `vl_qy`, `vl_crad`, `vl_cnx`, `vl_cny`, `vl_csnx`, `vl_csny`, `vl_csgn`, `vl_cflag`, `vl_cj` (2); without a ground also `vl_vy` (2), `vl_vt` (2) |

BSS: the points as a structure of arrays, `VL_NPOINTS` bytes each, in this
order: `vl_xf vl_xl vl_xh vl_yf vl_yh [vl_yu] vl_oxf vl_oxl vl_oxh vl_oyf
vl_oyh [vl_oyu]` (10 N bytes, 12 N with `VL_Y_HIGH`); `vl_pin` (`VL_PIN`);
`vl_gnd` (`VL_GROUND` bytes); `vl_turn` (tier 2); `vl_con_row`,
`vl_cidx` (`VL_CON_VARIANTS`); `vl_squashed` (`VL_CON_MINLEN_POINT`);
`vl_rad`, `vl_chits`, `vl_cheavy` (`VL_CIRC_HEAVY`), `vl_still`
(`VL_CIRC_SLEEP`) with `VL_CIRC`. DATA:
`vl_lap_len` (word, 0 = no wrap) with `VL_WRAP_MARGIN`.

## Parameters and switches

Parameters: `VL_NPOINTS` (1..51), `VL_NCON`, `VL_GRAVITY`, `VL_VMAX_X`,
`VL_VMAX_Y`; ground: `VL_GROUND` (the first points that can touch it),
`VL_HEIGHTS` (address), `VL_RADIUS`, `VL_PROBE`, `VL_SLOPE_MAX`, `VL_FAR`
(whole rows), `VL_BOUNCE` (0..127); `VL_WRAP_MARGIN`, `VL_WRAP_POINT` (0);
`VL_AXIS_A`/`VL_AXIS_B` (0/1), `VL_SHIFT_POINT`; `VL_PAIR_A`/`VL_PAIR_B`
(0/1).

Switches (undefined = off, the plain code; their values matter, so `= 0`
is not "off"):

| Switch | Effect | DIRTBIKE |
|---|---|---|
| `VL_INTEGRATE_LEFTWALL` = wall | `vl_integrate`: a point left of the wall (16.8, whole px < 256, x taken unsigned) stops there (x = ox = wall); +32 B | `LEFT_WALL` (16 px) |
| `VL_CEILING_CLAMP` = row | the ceiling of `VL_CEILING` / `vl_ceiling` (whole rows) | `CEILING` (row 8) |
| `VL_CON_VARIANTS` = V | rest length and gain per variant row: `vl_cur·V + vl_con_row` (+ `vl_con_nl`, N bytes) | 17 lean levels |
| `VL_CON_HEAVY_POINT` = p, `VL_CON_HEAVY_SHIFT` = n | a link whose b is p moves p by c − c′ and a by c + c′, c′ = c >> n toward zero: p weighs (2ⁿ+1)/(2ⁿ−1) of a | rider, n = 3 (9/7) |
| `VL_CON_MINLEN_POINT` = p, `VL_CON_MINLEN` = l2q | a link whose b is p with qx²+qy² < l2q sets `vl_squashed` | the rider squashed: a crash |
| `VL_PAIR_DAMP` = n | assembles `vl_pair_damp` | `SPIN_DAMP` (4) |
| `.define VL_ROT_SEG "SEG"` | `vl_shift_point`, `vl_axis` in that segment | `TXTC4` (text page) |
| `.define VL_MULTURN_SEG "SEG"` | `vl_mul_turn` in that segment | `TXTC7` |
| `VL_PIN` | `vl_pin` (N B): pinned points (above) | — (lander, rope) |
| `VL_CON_FIXED_K` = s | every link's gain 2ˢ, shifts, no k8 table: −169 c a link | — (lander, rope) |
| `VL_CON_MIN_ONLY` | links flagged in bit 7 of `vl_con_b` only push | — |
| `VL_THRUST` = n | assembles `vl_thrust_axis`/`_perp`, `vl_push`, `vl_push_all` (+4 B zero page) | — (lander) |
| `VL_Y_HIGH`, `VL_GROUND_BASE` = row | y 16.8 (`vl_yu`, `vl_oyu`), the ground base row: +80 B, +28 c an integration | — (lander) |
| `VL_GROUND_SEGMENTS` = n, `VL_SEG_DEPTH` = 8.8 | the segment ground `vl_seg_ground` (`verlet_seg.asm`; needs `VL_GROUND`): the `vl_sg_*` tables (14 B a segment, 16 with `VL_Y_HIGH`), `vl_sgi` (`VL_GROUND` B BSS), no zero page of its own (the ground tier's height-map scratch): 803 B, 835 B with `VL_Y_HIGH` | — (halfpipe) |
| `VL_SEG_CACHE` = m (8.8) | `vl_seg_ground` tries the point's last segment first: +270 B | — (halfpipe) |
| `VL_GROUND_KIND` = table | assembles `vl_ground_any`: per point, 0 = the height map, else the segments (both grounds in one program) | — |
| `VL_CIRC` = n, `VL_CIRC_Q` = 4..6 (5) | circle contacts (`verlet_circ.asm`; needs `isqrt16` — `sqrt.asm`, `sqrt_init` — and `MUL_ACC`): 941 B pairs, 1,039 B boxes (`VL_NBOX`), 1,762 B both, + 256 B reciprocals | — (catapult) |
| `VL_CIRC_BOUNCE` = e, `VL_CIRC_VMIN` = 8.8 | restitution e/256 of a closing speed above VMIN (pairs and boxes) | — (catapult) |
| `VL_CIRC_HEAVY` = n | `vl_cheavy` (n B): heavy circles against light ones | — (catapult) |
| `VL_CIRC_FRICTION` = f | boxes: vt −= vt >> f | — (catapult) |
| `VL_CIRC_SLEEP` = v, `VL_CIRC_SLEEP_TICKS` (16) | `vl_circ_sleep`, `vl_still`; sleepers are `vl_pin` = $80 (`VL_PIN`); every switch together: 2,252 B | — (catapult) |

`dev/lib/ABI.md` lists them with the other library options. The DIRTBIKE
switches and hooks are in `dirtbike/src/physics.inc`.

## DIRTBIKE, the first user

`dirtbike/src/physics.inc` keeps the bike: the order of a tick (integrate,
brake in the air, spin damping, turn, rider shift, constraints, ground,
constraints again, held brake, ceiling, crash tests, wrap), the ground
hooks (traction, brake, engine brake, rolling loss, spokes, spin) and the
crash tests. `dirtbike/tools/physics.py` is a `verlet.Points` subclass in
the same way. The move was checked in two steps: the generic routines
reordered by hand first (`make test` green), then the library in their
place: `build/dirtbike.bin`, `build/menu.bin`, `dirtbike.lbl` and
`dist/DIRTBIKE.dsk` byte-identical to the reordered build. The Python side
was compared every tick with the frozen model over the 30 solutions and
the test scripts (46,735 ticks, full state), and `tools/solver.py` runs as
fast as before.

## What other games need

| Game | Covered | Still needed |
|---|---|---|
| Ski, sled, mountain bike, buggy (a chassis on a hilly height map) | everything DIRTBIKE uses | its own tick and hooks |
| Ragdoll / stuntman falling down stairs | points, links (up to 45 px), heavy points, ground, squash alarm, minimum-only links (`VL_CON_MIN_ONLY`: joints that only push), pins | joint angle limits; several bodies (one point set today) |
| Rope, chain, bridge, hanging cargo | `vl_integrate_all`, `vl_con_pass`, `VL_PIN`, fixed-gain links (`VL_CON_FIXED_K`), a heavy end, a floor: [`dev/examples/rope`](../../examples/rope/README.md) | a rope's own self-contact (links crossing: `VL_CIRC` on the rope points) |
| Lunar lander, jetpack | points, links, ground, `VL_THRUST` (`vl_thrust_perp` + `vl_push_all`), `VL_Y_HIGH` + `VL_GROUND_BASE`, `vl_pair_damp` against the spin: [`dev/examples/lander`](../../examples/lander/README.md) | — |
| Half-pipe, loop, skate park | the segment ground (`VL_GROUND_SEGMENTS`: walls, overhangs, loops), a pump in the tangent hook, `vl_turn_pair` in the air: [`dev/examples/halfpipe`](../../examples/halfpipe/README.md) | moving segments (platforms, a rotating loop); curved segments or speed-keeping joints (a polygon loses 1 − cos θ a joint) |
| Marble, rolling ball | points, ground, tangent hook, marbles against each other and against blocks (`VL_CIRC`, `vl_contact_box`), sleep | a rolling hook (angular speed from `vl_vt`), friction between marbles (pairs are frictionless), boxes beyond x 255 |
| Catapult, Angry Birds-like | a pinned arm released by `vl_thrust_perp`, circle contacts (pairs, static boxes, restitution, a heavy projectile, sleep): [`dev/examples/catapult`](../../examples/catapult/README.md) | bodies that are not circles (a plank: two circles and a link, or box-box contacts), moving boxes, waking a whole stack in the library, a second contact pass for tall stacks |
| Boat on waves | points, ground hooks, `VL_THRUST` (the propeller) | a moving height map (`VL_HEIGHTS` re-pointed or rebuilt each tick) and buoyancy instead of a hard push |

## Tests

`dev/tests/test_verlet.py` (in `make test-hgr`): configuration 1 (3
points, every switch, ground hooks) runs 1,130 single calls from random and
edge states — clamps and sign edges of `vl_integrate`, q = 180 / d8 ±4095
/ f ±127 / negative heavy rounding / squash alarm / variants in
`vl_constrain`, `vl_ground` on every slope −15..15 (and beyond the clamp),
the flat short cut, far above and below — and compares each with
`dev/tools/verlet`; configuration 2 is a 5-point rope (`VL_NPOINTS = 5`,
`VL_NCON = 4`, no ground, no switch, the library's own 20-byte zero page)
for 300 ticks; configuration 3 (4 points, `VL_Y_HIGH` with a ground base,
`VL_PIN`, `VL_CON_FIXED_K`, `VL_CON_MIN_ONLY`, `VL_THRUST`) runs 1,020
single calls the same way (y across the 256-row boundaries and above row
0, each pin case of a link, the ground far above and below in 24 bits);
configuration 4 is a pinned 8-point rope of fixed-gain links (its end
pinned for a while) for 320 ticks; configuration 5 a 3-point lander in a
16.8 world, its thrust and turns from an autopilot run on the model, 850
ticks down to the ground; then each switch, left out and defined. `dev/tools/verlet/
harness.py` is the generic driver (input script, tick label, snapshot
blocks) for a game's own model-vs-6502 test.

`dev/tests/test_verlet_seg.py` (in `make test-halfpipe-example`): 22
segments (a floor, a 45° slope, a vertical wall and a ceiling in one
polyline, a 76° slope, a lone plank, a closed 16-segment loop at x
570..630: 16-bit boxes) and 632 single `vl_seg_ground` calls placed along
every segment (around its ends, both sides, deep behind it, far away, the
hooks) == `segments.py`; 3 points riding the loop for 600 ticks, one of
them going round; the same with `VL_Y_HIGH` + `VL_SEG_CACHE` (rows
270..430, a wall across row 256, points above row 0, `vl_sgi` inputs) and
with the cache alone; `VL_GROUND_KIND` (60 calls, height map and segments);
the switch errors; `--cycles` prints the costs above.

`dev/tests/test_verlet_contact.py` (`make test-verlet-contact`):
configuration A (4 circles, y 8.8, Q = 5, restitution, VMIN, heavy points,
pins, friction, sleep, 3 boxes) runs 1,460 single calls — 700
`vl_contact_pair` (head-on, glancing, a resting stack, coincident centres,
fast and deep hits, the fast path far apart, across the 256-px and
256-row wraps and at the 128-px edge, radii up to R = 127, every pin, sleep
and heavy case: 20 wakes), 150 `vl_contact_all` (clusters of 4, a radius
0), 450 `vl_contact_box` (faces, corners, inside, within a unit, far,
beyond x 255) and 160 `vl_circ_sleep` — and compares points, pins, sleep
counters, `vl_chits` and C with `contact.py`; configuration B (`VL_Y_HIGH`,
Q = 6, no switch) 1,300 calls the same way; configuration C a stack of 3
on a box and a ball rolling into it, 300 ticks; then the switches and the
code sizes; `--cycles` prints the costs above.

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).
