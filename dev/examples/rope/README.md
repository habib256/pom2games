# ROPE — a pinned Verlet rope

*[← dev](../../README.md)*

```sh
make -C dev/examples/rope          # build/ROPE.dsk (DOS 3.3, boots into the toy)
make -C dev/examples/rope run      # in POM2, Apple II+ profile
make -C dev/examples/rope test     # 6502 physics == the Python model, then the disk
python3 dev/examples/rope/tools/rope.py   # the model, in a few lines of text
```

A toy for the rope side of [`lib/physics`](../../lib/physics/README.md):
an Apple II+ 48 KB HGR program in assembly (dev/lib only), 5.3 KB. A pin
runs along the top of the screen; from it hang seven rope points and a
weight on eight links of 11 px. Move the pin and the rope swings; lower it
(floor mode) and the rope lies down on a hilly floor and drags along it;
cut the weight and it flies off on its own, to bounce and slide on the
floor; put it back and it hangs again.

## Keys

| Key | Effect |
|---|---|
| `J` / ← and `L` / → | move the pin (a press moves it for 6 ticks, 2 px a tick; the key repeat keeps it going) |
| `M` | swing (the pin at row 28) / floor (the pin goes down to row 128) |
| space | cut the weight off / put it back under the rope's end |
| `R` | start again |
| `ESC` | back to DOS |
| joystick (found at start) | X, once moved off its rest position, places the pin; button 0 cuts |

## What it shows

* **Python first.** [`tools/rope.py`](tools/rope.py) is the physics (a
  `verlet.Points` subclass); it writes `src/ropeconst.inc` (constants,
  link tables, ground normals, the floor) through `verlet.emit`.
  [`src/phys.inc`](src/phys.inc) transcribes it line by line;
  [`tests/test_rope.py`](tests/test_rope.py) runs both on four scripted
  runs (a swing to both ends of the rail, the floor with the pin dragging
  the rope, the weight cut in flight and put back, 1,500 ticks of random
  moves, mode and cut flips) and compares the whole state with
  `verlet.harness`: bit for bit.
* **The library switches** ([`src/physdefs.inc`](src/physdefs.inc)):
  `VL_PIN` (the pin is point 0: the program moves it, x = ox and y = oy,
  so it has no speed of its own: a kinematic move; a link to it moves only
  the rope end, by the whole correction), `VL_CON_FIXED_K` = 6 (links of
  gain 64, no product, no k8 table), `VL_CON_HEAVY_POINT` = 8 with shift 2
  (the weight moves 3/5 of what a rope point would), `VL_CEILING_CLAMP`,
  `VL_GROUND` = 9 with the `VL_GROUND_TANGENT` hook (`vl_damp`: friction).
  Two link passes a tick: the 88 px of rope stretch to ~91 at rest.
* **Pins and ground together.** In floor mode every rope point is probed
  against the height map (`vl_ground`): the links pull the points lying on
  the floor along when the pin moves, the floor pushes them back up.
  Swinging, only the weight is probed (it can be cut and fall).
* **Cutting a link.** A cut runs the passes over the first 7 links
  (`vl_constrain` in a loop instead of `vl_con_pass`). Putting the weight
  back places it under the rope's end at rest: a link only pulls what is
  within 45 px (q is clamped to 180 quarter pixels).
* **Walls.** The model clamps every point to x 4..251 after the passes
  (a point carried past 255 or below 0 included): the ground probe then
  never reads outside the 256-byte height map.
* **Drawing only what changes.** The floor is drawn once on both pages.
  [`src/plot.inc`](src/plot.inc) plots lines that remember the bits they
  lit (only the dark ones, with their addresses) in a history per page;
  each frame erases the hidden page's history with EOR — the floor under
  the rope comes back as it was, nothing is redrawn — then draws the rope,
  the pin and the weight.

## Measures

a2run, Apple II+ at 1.02 MHz:

| | Cycles |
|---|---|
| `phys_tick` swinging (8 integrations, 2 passes of 8 links with a pin and a heavy end, the weight's ground probe, walls, ceiling) | 21,050-21,140 |
| … on the floor (8 ground probes, 3-4 in contact) | 28,300-35,300 |
| … on the floor, the pin dragging the rope | 26,800-31,500 |
| a whole frame swinging (tick, input, erase, ~150 pixels plotted) | ~49,000 (20.7 fps) |
| a whole frame on the floor | ~61,000 (16.8 fps) |

The toy runs a tick a frame with no pacing (the constants are tuned for
that rate). Where the time goes: ~21,000 cycles of links (18 constraint
calls at ~1,130 cycles with a pinned or heavy end), ~2,700 of integration,
~110 cycles a plotted pixel and ~40 an erased one.

## Turning it into a game

* Change the rope in `tools/rope.py` (`LINK`, the number of points `N`,
  `HEAVY`, `GRAVITY`), try it with `python3 tools/rope.py`, then `make`:
  the constants follow; `make test` says whether `phys.inc` still agrees.
* A bridge: pin both ends (`vl_pin`), walk a load across it.
* Hanging cargo under the lander: the rope's pin is the lander's bottom
  point (move it with the lander, x = ox) — two pinned chains in one
  point set, the links of each listed in `vl_con_a` / `vl_con_b`.
* Faster: one link pass and a stiffer gain (`FIXED_K`), or fewer points;
  draw the rope as points rather than lines.

Files: `src/rope.s` (the toy: input, drawing, text lines), `src/plot.inc`
(lines with an erase history), `src/phys.inc` / `src/physdefs.inc` (the
physics), `src/ropeconst.inc` (generated), `tests/test_rope_disk.py` (the
disk: boot, the pin moved, the floor, a cut, R, frames per second; the
text on screen read back from the glyph bytes).

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).
