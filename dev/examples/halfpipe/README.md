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
(dev/lib only), 8.4 KB. The pipe is 20 line segments — two decks, two
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
| `K` / `I` / ↑ / space | pump (a press pumps for 12 ticks, 0.4 s; the II+ keyboard has no key-up, its repeat keeps it on) |
| `J` / ← and `L` / → | lean left / right in the air (4 ticks a press) |
| `R` | a new run (score 0) |
| `ESC` | back to DOS |
| joystick (found at boot) | X leans, button 0 pumps |

HUD: `SCORE` (six BCD digits), `LAST` the points of the last landing,
`AIR` how high the last scored jump went above the lip (px). A landing
scores when the body went above the lip row: 10 points per 12 ticks (0.4
s) in the air (up to 90), 100 per full turn (up to 900).

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
  `VL_CEILING_CLAMP` (row 17, under the HUD); the speed switches `VL_CON_SKIP_ZERO` (a link at rest returns at once) and `VL_CON_FAST` (square table, the link inline): exact, the same physics bit for bit; `VL_SEG_BUCKETS`
  (the scan tries only the segments of the wheel's 8-px column: 1-6 of
  the 20, the same result).
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
  hidden one: the rider of two frames ago is given back — its lines and
  wheels are drawn with
  [`lib/hgr/hgr_plot_hist.asm`](../../lib/hgr/hgr_plot_hist.asm)
  (`HGR_PLOT_HIST_FAST`), which records the bits they lit, so an EOR
  restores the pipe under them and no segment is redrawn —, the new one
  drawn (fast lines, each wheel a 3 × 3 cross sprite). The HUD (when a
  number changed) and the message line keep, per page, the characters
  they show: only those that differ are written (a private 8-row glyph
  store, ~150 cycles a character instead of `hgr_putc8`'s ~470): "AIR!"
  after "360!" is 3 characters, not 40.
* **30 ticks a second, flipped in the blank.** The page is shown in the
  vertical blank, a tick every 2 video frames
  ([`vapor.asm`](../../lib/apple2/vapor.asm): `vapor_mark_both` puts the
  floating-bus marker on row 191 of both pages; nothing is drawn below
  row 190; `vapor_pace` waits for the tick's last frame from an estimate
  of its cycles: 16,500 in the air, 21,000 with a point on the pipe, + the
  growl and the chimes). Without a floating bus (`vapor_pace_init` fails:
  a real //c, a IIgs) it runs a tick a frame, unpaced. The feel was tuned
  unpaced at ~40 ticks a second: [`tools/halfpipe.py`](tools/halfpipe.py)
  derives every constant with a time in it (`TUNED_HZ` 40 → `TICK_HZ`
  30): `GRAVITY` × (40/30)² (12 → 21), the kicks × 40/30, `AIR_MIN` 8 → 6,
  the scoring unit 16 → 12 ticks (`AIR_UNIT`, a loop instead of 4 shifts),
  `PUMP_HOLD` 16 → 12, `AGAIN_T` 110 → 83. Two are fitted on the model
  rather than scaled: the pump (× (40/30)² = 36 made the jumps ~17 px
  higher — the wheels touch more ticks of a swing at 30 Hz —;
  `fit_pump()` picks the `PUMP_K` whose jumps, 40 s of pumping, peak on
  average where they did at 40 Hz: 30, rows 71.0 against 71.3) and the
  lean (a spin faded by 1/8 a tick cannot keep both its start and its
  steady speed: `fit_turn()` picks `ROT_K` 8, within 12 % of the tuned
  spin over the first second held, and `LEAN_HOLD` 4, within 6 % for a
  press). `VMAX` stays 6 px a tick (`per_s` says 8): it is the tunnelling
  bound (`RADIUS` + `VL_SEG_DEPTH`: a point moving more than that across a
  segment in a tick passes it), never reached — the rider goes up to ~4 px
  a tick at 30 Hz (3.1 at 40), no point left the pipe in the model's
  rides.
* **The stick.** `read_stick_x` (X alone, the Monitor's PREAD scale:
  0..255, ~128 centred, 3.2 times the former `read_stick_fast` counts):
  dead zone `JOY_DEAD` = 38 (was 12).

## Measures

a2run, Apple II+ at 1.02 MHz:

| | Cycles |
|---|---|
| `phys_tick` in the air (3 integrations, pair damping, 3 passes of 3 links, 3 segment probes, ceiling, octant) | 5,799 (12,936 before the speed switches) |
| … both wheels on a curve (2 contacts, pump) | 9,961 (16,421) |
| … both wheels on the bottom | 12,038 (18,628) |
| a tick's work riding (input, tick, events, erase, rider; main to `pace`; 1,500 ticks of pumping) | 16,921 median, 28,331 worst (16,297 median at 40 Hz unpaced; 22,756 / 55,184 before the speed switches; 24,500 / 77,000 before the fast drawing) |
| the flips (the same 1,500 ticks) | 1,485 of 1,488 34,060 cycles apart (± 13), all on line 193 (the vertical blank); left out: the 9 ticks of landings that score (the chime, 20,000-60,000 cycles: 3 frames) |

Before the pacing the game ran ~59 ticks a second (a flip every 1.02
video frames on average, torn). Left in a tick: the physics (~8,200, up
to ~18,300 on the bottom), the stick (~1,450: the RC time of a centred X),
~3,300 for three lines, ~1,100 for the two wheels, ~1,100 to erase, then
the wait; the ticks of a landing that scores add a chime of ~20,000 cycles
(`tone`) and the message's changed characters.
`tests/test_halfpipe_disk.py` asserts the median and worst (measured
+ 5 %), the cadence (≥ 98 % of the flips 34,060 cycles apart, every flip
on lines 192-261) and a run without the marker (unpaced, it still
plays).

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
text, a minute of pump key presses that gets above a lip, the rider put
upside down — a crash and its message —, R; the text on screen read back
from the glyph bytes; the cycles a tick's work costs and the cadence of
the flips, 1,500 ticks of pumping; a run unpaced).

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).
