# HALFPIPE — a Verlet skate half-pipe

*[← dev](../../README.md)*

```sh
make -C dev/examples/halfpipe          # build/HALFPIPE.dsk (DOS 3.3, boots into the game)
make -C dev/examples/halfpipe run      # in POM2, Apple II+ profile
make -C dev/examples/halfpipe test     # 6502 physics == the Python model, then the disk
python3 dev/examples/halfpipe/tools/halfpipe.py   # the pipe's segments, a pumping ride on the model
```

The demo of the [`lib/physics`](../../lib/physics/README.md) **segment
ground** (`verlet_seg.asm`): an Apple II+ 48 KB HGR program in assembly
(dev/lib only), 6.8 KB. The pipe is 20 line segments — two decks, two
vertical lips, two quarter pipes of six segments, a flat bottom in two, the
screen-edge walls — what a height map (one row per column) cannot hold.
The rider is **three Verlet points** (two wheels and the body, a 6-8-10
triangle of fixed-gain links). Pump to climb the walls, fly above the lips,
lean to turn in the air: a landing scores its air time and its full turns
(360, 720, 1080). Land upside down, or touch the pipe with the body, and
the links break (`CRASHED!`); a new run starts by itself after two or
three seconds.

## Keys

| Key | Effect |
|---|---|
| `K` / `I` / ↑ / space | pump (a press pumps for 16 ticks; the II+ keyboard has no key-up, its repeat keeps it on) |
| `J` / ← and `L` / → | lean left / right in the air (6 ticks a press) |
| `R` | a new run (score 0) |
| `ESC` | back to DOS |
| joystick (found at boot) | X leans, button 0 pumps |

HUD: `SCORE` (six BCD digits), `LAST` the points of the last landing,
`AIR` how high the last scored jump went above the lip (px). A landing
scores when the body went above the lip row: 10 points per 16 ticks in the
air (up to 90), 100 per full turn (up to 900).

## What it shows

* **Python first.** [`tools/halfpipe.py`](tools/halfpipe.py) is the physics
  and the rules (a `verlet.Points` subclass on a `verlet.SegmentGround`);
  it writes `src/pipeconst.inc` (constants, link tables, the segment tables
  of `SegmentGround.tables()`, the drawn ends, the start, the crash kicks)
  through `verlet.emit`. [`src/phys.inc`](src/phys.inc) transcribes it line
  by line; [`tests/test_halfpipe.py`](tests/test_halfpipe.py) runs both on
  four scripted rides (pumping up above the lips, 360s landed by a pilot
  that leans in the air and stops in time, an over-rotation that lands
  upside down and its debris, 1,500 ticks of random inputs) and compares
  the whole state — points, contacts and their segments, status, air,
  rotation, score — every few rows with `verlet.harness`: bit for bit.
* **The segment ground** ([`src/physdefs.inc`](src/physdefs.inc)):
  `VL_GROUND_SEGMENTS` = 20 with `VL_SEG_DEPTH` (4 px) and `VL_SEG_CACHE`
  (a wheel still on its segment, 2 px from its ends, skips the scan),
  `VL_GROUND` = 3 (the body is probed too: it touching is a crash),
  `VL_CON_FIXED_K` = 6, `VL_PAIR_DAMP` = 3 (the spin fades in the air),
  `VL_CEILING_CLAMP` (row 17, under the HUD).
* **Near-unit normals.** The quarters' segments run along the directions
  of integer normals whose length² is within 6 of 4096 ((63, 11), (58, 27),
  (50, 40) and their mirrors): a wheel rolling on a segment keeps its speed
  (a normal of length L scales it by L²/4096 a tick).
  `SegmentGround.from_polyline()` chains the segments on those tangents.
* **The pump in the tangent hook.** A polygon pipe brakes: each joint of a
  quarter turns by 10-15° and costs a rolling wheel 1 − cos of its speed
  (~17 % a quarter). `VL_GROUND_TANGENT` gives a wheel going up (its
  tangential speed and the normal's x of opposite signs: a curve or a lip,
  not the bottom) `PUMP_K` more speed a tick while the pump is on: timed
  well, the rider climbs; held all the time, it gets 15-30 px of air.
* **Tricks from an octant counter.** In the air the wheels' axis is
  followed by octant (signs and |dx| > |dy|, no angle): the octants turned
  add up, a landing counts (|rot| + 4) / 8 full turns. The landing test is
  one dot product: the body must be 3 px or more along the normal of the
  landing wheel's segment (`vl_sgi`), or the run ends.
* **Drawing only what changes.** Two HGR pages; each frame draws the
  hidden one: the rider of two frames ago is wiped (its box of bytes
  cleared, then the pipe segments crossing the box drawn again with
  `hgr_line8`), the new one drawn, the HUD digits rewritten only when they
  changed (per page).

## Measures

a2run, Apple II+ at 1.02 MHz:

| | Cycles |
|---|---|
| `phys_tick` in the air (3 integrations, pair damping, 3 passes of 3 links, 3 segment probes, ceiling, octant) | 12,936 |
| … both wheels on a curve (2 contacts, pump) | 16,421 |
| … both wheels on the bottom | 18,628 |
| a whole frame while pumping (input, tick, events, box wipe and pipe repair, rider) | 26,793 (38 fps) |

The game runs a tick a frame with no pacing: the constants were tuned at
~38 fps.

## Turning it into a game

* Change the pipe in `tools/halfpipe.py` (`pipe_points()`, `QUARTER`,
  `SEG_LEN`, `LIP_Y`, `BOTTOM_Y`) and the feel (`GRAVITY`, `PUMP_K`,
  `ROT_K`, `SPIN_DAMP`, `LAND_MIN`), try it with `ride()` and a pilot, then
  `make`: the constants and the segment tables follow; `make test` says
  whether `phys.inc` still agrees.
* A skate park: more segments (ramps, a funbox, a loop: `from_polyline`
  with `closed=True`), up to 128; a wider world than 256 px needs a camera
  (x is 16.8 in the library; `hgr_line8` draws x 0..255).
* More tricks: a grab (a key that shortens the body links: `VL_CON_VARIANTS`
  rows), a stall on the deck (the rider at rest on a deck segment: `vl_sgi`
  says which), combos in the score; a timer for a contest.
* A BMX: the same three points, a heavier body (`VL_CON_HEAVY_POINT`), a
  brake in the tangent hook (`vl_damp`).

Files: `src/halfpipe.s` (the game: input, events, drawing, HUD),
`src/phys.inc` / `src/physdefs.inc` (the physics), `src/pipeconst.inc`
(generated), `tests/test_halfpipe_disk.py` (the disk: boot, HUD and help
text, a minute of pump key presses that gets above a lip, the frame cost,
the rider put upside down — a crash and its message —, R; the text on
screen read back from the glyph bytes).

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).
