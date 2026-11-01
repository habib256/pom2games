# LANDER — a Verlet lunar lander

*[← dev](../../README.md)*

```sh
make -C dev/examples/lander          # build/LANDER.dsk (DOS 3.3, boots into the game)
make -C dev/examples/lander run      # in POM2, Apple II+ profile
make -C dev/examples/lander test     # 6502 physics == the Python model, then the disk
python3 dev/examples/lander/tools/lander.py   # the autopilot on the model
```

The demo of [`lib/physics`](../../lib/physics/README.md) and the starting
point for a new physics game: an Apple II+ 48 KB HGR program in assembly
(dev/lib only), 8.0 KB. The lander is **three Verlet points** (two legs and
the top) held by three links; the engine pushes them along the body, the
turn keys turn the legs' axis, and the ground is a height map with three
flat pads. Land on a pad slowly, level, and both legs on it: `LANDED ON PAD
x!`. Too fast, too tilted, the top touching the ground or a rest off the
pads: the links break and the three points fly apart (`CRASHED!`).

## Keys

| Key | Effect |
|---|---|
| `J` / ← and `L` / → | turn left / right (a press turns for 8 ticks; the key repeat keeps turning) |
| `K` / `I` / ↑ | engine (a press fires it for 20 ticks: the II+ keyboard has no key-up, its repeat keeps it on) |
| space | engine and turn off |
| `R` | start again |
| `ESC` | back to DOS |
| joystick (found at boot) | X turns, button 0 fires the engine |

HUD: `ALT` rows from the legs to the ground under the lander, `VS` vertical
speed in 1/16 px a tick (a landing needs 6 or less), `FUEL` (a unit every
two engine ticks).

## What it shows

* **Python first.** [`tools/lander.py`](tools/lander.py) is the physics and
  the rules (a `verlet.Points` subclass); it writes `src/landconst.inc`
  (constants, link tables without k8, normals, pads, heights) through
  `verlet.emit`. [`src/phys.inc`](src/phys.inc) transcribes it line by
  line; [`tests/test_lander.py`](tests/test_lander.py) runs both on six
  scripted flights (landings on pads A and C flown by the model's autopilot,
  a free fall and its debris, 1,500 ticks of random inputs that hit the
  walls, the ceiling and the end of the fuel, a rest off the pads, a tilted
  touch-down) and compares the whole state every few rows with
  `verlet.harness`: bit for bit.
* **The library switches** ([`src/physdefs.inc`](src/physdefs.inc)):
  `VL_Y_HIGH` (y in 16.8: the world is 536 rows, three screens) with
  `VL_GROUND_BASE` (the ground is the height + 280: rows 280..535),
  `VL_CON_FIXED_K` = 6 (links of gain 64, no product, no k8 table),
  `VL_THRUST` = 4 (`vl_thrust_perp` + `vl_push_all`: the engine, a pure
  translation), `VL_PAIR_DAMP` = 2 (the spin fades by a quarter a tick: the
  lander turns while a key is held), `VL_INTEGRATE_LEFTWALL`,
  `VL_CEILING_CLAMP`, the `VL_GROUND_TANGENT` hook (`vl_damp`: friction);
  the speed switches `VL_CON_SKIP_ZERO` (a link at rest returns at once) and `VL_CON_FAST` (square table, the link inline): exact, the same physics bit for bit.
  `VL_GROUND` = 3: the top is probed too.
* **A rest shape on the grid.** The triangle is 6-8-10 (legs 12 px apart,
  top 8 px above): every delta is a multiple of a quarter pixel, the links
  see no error at rest, and the lander falls without turning. With the
  rounding toward zero of `VL_CON_FIXED_K` the links leave a body flying
  free alone; with the floor of the product it slowly turned.
* **Landing rules that survive a resting leg.** A leg on the ground leaves
  it now and then (gravity a tick, the push back out): the verdict counts
  the ticks with a leg down and starts again only after a tick with both
  legs up.
* **Drawing only what changes.** Two HGR pages; each frame draws the
  hidden one: the lander of two frames ago is given back — its lines and
  debris are drawn with
  [`lib/hgr/hgr_plot_hist.asm`](../../lib/hgr/hgr_plot_hist.asm)
  (`HGR_PLOT_HIST_FAST`), which records the bits they lit, so an EOR
  restores the ground under them and nothing is redrawn —, the new one
  drawn (fast lines; each piece of debris a 3 × 3 cross sprite). The HUD
  and the message line keep, per page, the 40 characters it shows: a frame
  writes only those that differ (a private 8-row glyph store, ~150 cycles
  a character instead of `hgr_putc8`'s ~470). The camera is a zone: four
  overlapping static screens (tops 0, 120, 240, 360); near an edge the next
  one is set, and each page, when it is next drawn, has its rows 16-191
  cleared (~39,000 cycles: whole 256-byte pages, then the first of each
  1 KB but its two HUD rows) and its ground drawn again: two frames of
  65,000-128,000 cycles (the whole ground) instead of one of
  166,000-295,000; the HUD and the message stay.
* **The stick.** `read_stick_x` (X alone, the Monitor's PREAD scale:
  0..255, ~128 centred, 3.2 times the former `read_stick_fast` counts):
  dead zone `JOY_DEAD` = 38 (was 12).

## Measures

a2run, Apple II+ at 1.02 MHz:

| | Cycles |
|---|---|
| `phys_tick` coasting (3 integrations, pair damping, 3 passes of 3 links, 3 ground probes, ceiling, rules) | 5,429 median (12,222 before the speed switches: 81 % of the links are at rest) |
| … with the engine (`vl_thrust_perp` + `vl_push_all`) | 7,632 median (13,500) |
| … with the engine and a turn (`vl_turn_pair`) | not re-measured (14,334 before the speed switches) |
| a whole frame coasting (tick, input, erase, 3 lines, HUD characters that changed) | 13,297 median, 13,883 worst (~77 fps; 20,122 before the speed switches, 23,700 before the fast drawing) |
| a whole frame with the engine (+ the flame) | 16,814 median, 20,155 worst (22,656; 25,800) |
| a whole frame over the debris (three crosses) | 7,858 median, 17,682 worst (the message's first frames; 41,600 median, 52,000 worst before the fast drawing) |
| each of the two frames of a zone change | 63,066 median, 121,986 worst (69,830 / 128,199; 166,000-295,000 in one frame before the fast drawing) |

The game runs a tick a frame with no pacing: the constants were tuned at
~40 fps (it now runs ~1.9 times as fast). Left in a coasting frame: the
physics (5,400), the stick (~1,450: the RC time of a centred X), ~3,000 for the
lines, ~800 to erase, ~1,800 for the HUD (the numbers converted, compared,
1-3 characters written). `tests/test_lander_disk.py` asserts the median
and worst of each (measured + 5 %).

## Turning it into a game

* Change the world in `tools/lander.py` (`terrain()`, `PADS`, `START`) and
  the feel (`GRAVITY`, `THRUST_K`, `ROT_K`, `SPIN_DAMP`, `V_SAFE`,
  `TILT_MAX`), try it with `fly()` / `autopilot()`, then `make`: the
  constants follow; `make test` says whether `phys.inc` still agrees.
* More rules (score, a time limit, wind as a `vl_push_all` every tick,
  cargo on a pinned rope with `VL_PIN`) go into the model first, then into
  `phys.inc`, with a scenario in `tests/test_lander.py`.
* Levels: several height maps (one per world, 256 bytes each) and a
  `VL_HEIGHTS` per level (a pointer the ground reads: re-point it).
* Wider worlds: `hgr_line8` draws x 0..255; x is 16.8 in the library, so a
  horizontal camera is the same zone logic on x.

Files: `src/lander.s` (the game: input, events, camera, drawing, HUD),
`src/phys.inc` / `src/physdefs.inc` (the physics), `src/landconst.inc`
(generated), `tests/test_lander_disk.py` (the disk: boot, HUD, engine, a
landing on pad B, R, a free fall that crashes; the text on screen read back
from the glyph bytes; the cycles a frame costs coasting, with the engine,
over the debris and on a zone change).

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).
