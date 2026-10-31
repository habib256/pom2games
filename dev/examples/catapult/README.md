# CATAPULT — knock six balls off their boxes

*[← dev](../../README.md)*

```sh
make -C dev/examples/catapult          # build/CATAPULT.dsk (DOS 3.3, boots into the game)
make -C dev/examples/catapult run      # in POM2, Apple II+ profile
make -C dev/examples/catapult test     # 6502 physics == the Python model, then the disk
python3 dev/examples/catapult/tools/catapult.py   # a sweep of shots on the model
```

The demo of the circle contacts of [`lib/physics`](../../lib/physics/README.md)
(`verlet_circ.asm`), Angry Birds-like: an Apple II+ 48 KB HGR program in
assembly (dev/lib only), 8.9 KB. A catapult on a hill: its arm is a 24-px
Verlet link pinned at its base; pull it back (the power), choose the
launch angle, fire: the arm swings round its base and lets the ball go at
the angle's stop with the tip's speed. Six balls wait on static boxes: one
on a pillar, a column of two on a platform, a pyramid of three in a cup.
A ball 8 px under its starting row is down. Three shots a round.

## Keys

| Key | Effect |
|---|---|
| `J` / ← and `L` / → | power 0..15 (the arm is pulled back 2° a step) |
| `I` and `K` (↑ ↓ on a //e) | launch angle 25°..65°, steps of 10° |
| space | fire; when the round is over, a new round |
| `R` | a new round |
| `ESC` | back to DOS |
| joystick (found at start) | X, once moved off its rest position, sets the power; button 0 fires |

Counters: `POWER`, `ANGLE`, `SHOTS` left, `DOWN` (of 6). A short line
shows the launch direction while aiming; a click sounds each tick with a
contact.

## What it shows

* **Python first.** [`tools/catapult.py`](tools/catapult.py) is the
  physics and the rules (a `verlet.Points` subclass and
  `verlet.contact`); it writes `src/catconst.inc` (constants, the arm's
  link, normals, boxes, targets, the arm's pull and stop tables, the hill)
  through `verlet.emit`. [`src/phys.inc`](src/phys.inc) transcribes it;
  [`tests/test_catapult.py`](tests/test_catapult.py) plays four scripted
  rounds of three shots on the model (short into the hill, onto the
  pillar, the column, the cup, long against the right wall, random aiming)
  and replays them on the 6502 with `verlet.harness`: the points, the pins
  and sleep counters, the phase, shots, score, timer and the targets down,
  bit for bit.
* **The arm** ([`src/physdefs.inc`](src/physdefs.inc)): `VL_PIN` (the base),
  `VL_CON_FIXED_K` = 4 (a 24-px link with a pinned end: gain 2⁴ = 1/(2·l2q)
  corrects it in one pass; 2⁶, right for 9-14 px links, overshoots 4
  times), `VL_THRUST` = 1 with `VL_AXIS_A`/`_B` = base/tip: at the
  release `vl_thrust_perp` + `vl_push` give the tip ARM·turn/512 px a tick
  across the arm, turn = 50 + 4·power. While it swings, the ball is the
  tip (same position and old position: the same speed); the arm crossing
  the stop direction (a cross product's sign) lets it go.
* **Circle contacts** (`VL_CIRC` = 7, Q = 5: radii in eighths of a pixel,
  5 px): `vl_contact_all` once a tick (21 pairs, ~52 cycles each apart),
  `vl_contact_box` (5 boxes) and `vl_ground` for each awake ball;
  `VL_CIRC_BOUNCE` = 64 above `VL_CIRC_VMIN` = $30 (a quarter of the
  closing speed back, slower contacts stop), `VL_CIRC_HEAVY` = 1 (the
  projectile weighs three targets), `VL_CIRC_FRICTION` = 3 on the boxes,
  ground friction in the tangent hook.
* **Sleep** (`VL_CIRC_SLEEP` = $28): the targets start asleep (`vl_pin` =
  $80): skipped by the integration and the boxes, pinned in a pair, so a
  stack stays put at no cost until a ball hits it faster than $28 (0.16 px
  a tick). One woken target wakes its group (pillar, column, pyramid): a
  sleeper is pinned, and one woken under another would leave it floating.
  A ball slow for 16 ticks sleeps again; the shot ends when the projectile
  and every target sleep (or after 500 ticks). The threshold is above 2g:
  with one pass of equal masses a ball resting on an awake one keeps a
  speed of ~2g and would never sleep under it.
* **Drawing only what changes.** The hill, the boxes and the post are
  drawn once on both pages; the arm, the balls (20-point rings) and the
  aim mark are plotted with `src/plot.inc` (a copy of the rope's: lines
  and points that remember the bits they lit) and erased by EOR two frames
  later, the scenery under them intact. The counters and the message are
  rewritten only when they change, per page.

## Measures

a2run, Apple II+ at 1.02 MHz, over the four test rounds:

| | Cycles |
|---|---|
| `phys_tick` aiming | 480-1,190 |
| … swinging (the arm, 2 link passes, the cross product) | 3,310-3,530 |
| … flying, no contact (1,402 ticks) | 4,730-16,530, mean 5,900, 90 % under 8,200 |
| … flying with contacts (433 ticks) | 7,500-37,500, mean 19,900, 90 % under 31,200 |
| a whole frame aiming (input, erase and plot ~180 pixels, counters) | ~37,500 (27.2 fps) |
| a whole frame over the first 5 s of a shot | ~40,500 (25.2 fps) |

One contact costs ~2,300-3,600 cycles (`lib/physics`), a ball on a box
~2,600-3,800; the peaks (~37,000) come from the pyramid tumbling in its
cup: three balls touching each other, the cup's floor and its posts, 6-8
contacts in one tick. The drawing, not the physics, sets the frame rate.

## Turning it into a game

* Levels: `BOXES`, `TARGETS` and `GROUP` in `tools/catapult.py` (boxes in
  pixels 0..255, edges included; targets placed exactly on them, a column
  10 px apart, a pyramid 8.75 px up: q² > R², no contact at rest), `make`.
* Other projectiles: a radius per circle (`vl_rad`, units of 1/8 px, a
  pair's sum ≤ 127), heavier ones (`vl_cheavy`); the restitution is one
  constant for every pair (`VL_CIRC_BOUNCE`).
* Planks and towers of blocks: two circles and a link make a plank
  (`VL_CON_FIXED_K`), its ends contact like balls; box-to-box contacts are
  not in the library.
* Faster frames: keep the sleeping balls out of the erase and redraw
  (a history per object, redrawn only when it moved or a neighbour did).

Files: `src/catapult.s` (the game: input, events, drawing, counters),
`src/plot.inc` (lines and points with an erase history), `src/phys.inc` /
`src/physdefs.inc` (the physics), `src/catconst.inc` (generated),
`tests/test_catapult_disk.py` (the disk: boot, the counters, power and
angle keys, a shot that knocks down what the model's does, a round to its
end, a new round, frames per second; the text read from the glyph bytes).

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).
