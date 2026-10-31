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
(dev/lib only), 6.8 KB. The lander is **three Verlet points** (two legs and
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
  `VL_CEILING_CLAMP`, the `VL_GROUND_TANGENT` hook (`vl_damp`: friction).
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
  hidden one: the lander of two frames ago is wiped (its box of bytes
  cleared, then the ground segments under the box drawn again with
  `hgr_line8`), the new one drawn, the HUD digits rewritten
  (`hgr_text8`). The camera is a zone: four overlapping static screens
  (tops 0, 120, 240, 360); near an edge the next one is drawn on both pages
  (158,000 cycles for the empty sky, 287,000 with the whole ground: a
  short pause, the price of a static camera).

## Measures

a2run, Apple II+ at 1.02 MHz:

| | Cycles |
|---|---|
| `phys_tick` coasting (3 integrations, pair damping, 3 passes of 3 links, 3 ground probes, ceiling, rules) | 12,222 |
| … with the engine (`vl_thrust_perp` + `vl_push_all`) | 13,307 |
| … with the engine and a turn (`vl_turn_pair`) | 14,334 |
| a whole frame coasting (tick, input, box wipe and ground repair, 3 lines, HUD) | ~23,800 (~43 fps) |
| a whole frame with the engine (+ the flame) | ~26,000 (~39 fps) |

The game runs a tick a frame with no pacing: the constants were tuned at
~40 fps.

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
from the glyph bytes).

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).
