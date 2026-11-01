# CUTROPE

A "Cut the Rope"-like prototype for the Apple II+ 48 KB (HGR, DOS 3.3 disk,
assembly, `dev/lib` only). A candy hangs from one or more ropes; cut them
at the right moment so that it swings into the frog's mouth, touching as
many of the three stars as it can on the way.

    make              # ../dist/CUTROPE.dsk (+ dist/woz/CUTROPE.woz), boots into the game
    make run          # in POM2 (Apple II+)
    make test         # 6502 physics == the Python model, then the disk in a2run
    python3 tools/cutrope.py                       # the levels' solutions on the model
    python3 tests/test_cutrope.py --no-disk --cycles   # phys_tick cycles per level
    python3 tests/test_cutrope_disk.py --fit       # refit the pace estimate

## How to play

| Keys | Joystick | Effect |
|---|---|---|
| `1` `2` `3` | | cut rope 1, 2, 3 (numbered left to right in the levels) |
| `I` `J` `K` `L` (or the arrows) | both axes | move the cursor (a cross); a key moves it 3 px a tick for 6 ticks (the II+ has no key-up), the stick 1-3 px a tick by its deflection |
| space | button 0 | the "knife": while it is held (space holds it 8 ticks), every rope the cursor touches is cut |
| `R` | | restart the level (a new game once the candies are gone) |
| `N` | | the next level, after a win (after level 3: level 1 again) |
| `ESC` | | back to DOS |

The candy is lost when it touches spikes or leaves the field (the bottom,
the sides); a loss costs one of the 5 candies. It is won when its centre
enters the frog's 14 × 14 box. The top line shows the level, the stars
taken and the candies left; the second line the keys, then the result. A
snip sounds at a cut, a blip at a star, a short jingle at the end.

The three levels (`LEVELS` in `tools/cutrope.py`):

1. **SWING** — one rope of 4 links; the candy starts beside the pin and
   swings. Cut it on the way right (3 stars: ticks 43-48 of the level, a
   win for 39-51 and a second window a swing later).
2. **TWO ROPES** — a short taut rope (3 links) and a slack one (4 links,
   1.3 × the distance): the candy bobs between them. Cut the right one
   (key 2) early, while the bobbing still has its energy: the candy swings
   far enough left for the first star (cut later than tick ~22 and it
   never gets there); then cut the left one on the way back (ticks
   101-109) through the two other stars into the frog.
3. **SPIKES** — the candy in a V over a floor of spikes, the frog on a
   ledge on the right. Cut the left rope, then the right one when the
   candy swings up (ticks 44-62 for three stars); too early and it drops
   on the spikes.

## What it shows

* **Python first.** [`tools/cutrope.py`](tools/cutrope.py) is the game's
  physics and rules (a `verlet.Points` subclass with `verlet.constrain`
  and `verlet.SegmentGround`), the level compiler, the sprites and the
  jingles; it writes `src/cutconst.inc` through `verlet.emit`.
  [`src/phys.inc`](src/phys.inc) transcribes it;
  [`tests/test_cutrope.py`](tests/test_cutrope.py) plays 12 scripted runs
  (the three solutions, level 3's spikes, a level left swinging, the
  cursor sweeping across the ropes with the button held, random play on
  each level, the bench) on both and compares the whole state every row
  (points, pins, state, ropes on, stars, events, the contact and its
  segment) with `verlet.harness`: bit for bit.
* **The ropes** ([`src/physdefs.inc`](src/physdefs.inc)): point 0 is the
  candy, then each rope's pin and inner points; a rope of n links from its
  pin P is (P, P+1) … (P+n−1, 0). `VL_PIN` (the pins, the unused points
  and the points of a cut rope), `VL_CON_FIXED_K` = 5, `VL_CON_HEAVY_POINT`
  = 0 with shift 1 (the candy weighs 3 rope points), `VL_CEILING_CLAMP`,
  the speed switches `VL_CON_SKIP_ZERO` and `VL_CON_FAST`. One link pass a
  tick (below).
* **Cutting.** A cut pins every point of the rope where it is: it is no
  longer integrated, linked or drawn — the rope disappears (Cut the Rope
  fades the pieces out too). The loose halves are left out on purpose:
  they would cost their integration, links and lines every tick for no
  play, and a cut must make a tick cheaper, not dearer (two ropes of 4
  links are the budget, below). The cursor's test (`near` in
  `phys.inc`, the model's `near()`) runs only while the button is held:
  for each link a box test (the cursor within `CUT_R` = 2 px of the
  link's box, on whole pixels), then `|dx·uy − dy·ux| ≤ 2 (|dx| + |dy|)`
  (the distance to the line within 2-2.8 px: the L1 length is above the
  true one) with two `mul_s16s8`. The cursor moves at most 3 px a tick per
  source, so a sweep never steps over a link.
* **Spikes and platforms** are `verlet_seg.asm` segments (the candy alone
  touches them: `VL_GROUND` = 1). Each level has its own: `phys_load`
  copies its rows into the `vl_sg_*` tables in BSS (8 slots, 14 B each);
  the slots it does not use get a box starting at x = $FFFF, which no
  pixel reaches. A contact with a segment of kind 1 loses the candy; a
  platform holds it, with friction in the tangent hook (`vl_damp`). A
  spike segment's line is the teeth's tips; the teeth are drawn 4 px under
  it.
* **Stars** are a distance test on the candy's pixel (`|dx|, |dy| ≤ 6`, then
  `dx² + dy² ≤ 36` from a 7-byte table), no circle contacts.
* **Levels** are compiled records (`compile_level`, 48-122 bytes): ropes,
  rope count, the candy, 3 stars, the frog's box, the segment count; per
  rope its pin, link count, rest length² (`l2q`) and its inner points
  (8.8: the compiler relaxes a slack rope into the shape it hangs in, so
  that a level starts without a jolt); per segment its kind, its drawn
  line and its 14 bytes of `vl_sg_*` (`segments.py`). The model reads the
  same bytes (`Level`).
* **Drawing only what changes, as a stack.** The platforms, the spikes and
  the frog are drawn once on both pages at a level's start (the frog with
  `pl_sprite`, its history then dropped). Each page's
  `hgr_plot_hist.asm` history is a stack: the stars at the bottom (drawn
  again only after one is taken), then the ropes and the candy, the cursor
  on top. A tick gives back (`pl_erase_to`, EOR) what lies above the
  stars and draws the ropes, the candy and the cursor again; once the end
  is on both pages, only the cursor. The counters and the message are
  rewritten only when they change, per page; the message (a 40-character
  line, ~20,000 cycles) only at a restart or once the picture is frozen.
* **30 ticks a second, flipped in the blank.** A tick every 2 video frames
  ([`vapor.asm`](../dev/lib/apple2/vapor.asm): `vapor_mark_both` after each
  clear, nothing drawn below row 190, `vapor_pace` waits for the tick's
  last frame from an estimate of its work). The estimate is a sum of what
  the tick did: a base, 2,950 a link drawn, 950 a digit, and a term per
  flag of `tkf` (the physics, a snip, a blip, the jingle's tick, the stars
  drawn again, the message), fitted by least squares on 1,592 ticks
  (`--fit`: residuals −3,627 … 2,864, the tolerance is half a frame,
  8,515). The jingle starts 5 ticks after the end (the frozen picture and
  the message first): a tick of it (`tune_tick`, ~17,000 cycles) a game
  tick. Without a floating bus (`vapor_pace_init` fails: a real //c, a
  IIgs) it runs unpaced.

## The physics constants and how they were tuned

All in `tools/cutrope.py`, at 30 ticks a second:

| Constant | Value | Why |
|---|---|---|
| `GRAVITY` | `$0016` (0.086 px/tick², ~78 px/s²) | the candy falls 150 px in ~2 s; a 50-px rope swings in ~3 s |
| `VMAX` | `$0600` (6 px a tick) | under `RADIUS` + `DEPTH`: the candy cannot cross a segment in a tick |
| `FIXED_K` | 5 (gain 2⁵) | rigid in one pass for 16-px links; the links are 12-15 px (stiffness (L/16)², 0.59-0.89) |
| `PASSES` | 1 | the budget (two passes: +700 cycles a link) |
| `HEAVY` | 1 | the candy = 3 rope points, the most `VL_CON_HEAVY_POINT` gives |
| `RADIUS`, `DEPTH`, `BOUNCE` | `$0380`, `$0400`, 24 | the candy's 7-px disc, a little bounce on a platform |
| `FRICTION` | 3 | on a platform the candy slides to rest in ~1 s (into the frog when it lands near it) |
| `STAR_R`, `CUT_R` | 6, 2 px | candy 3.5 + star 2.5; the knife's reach |
| `CEIL`, `LOST_Y` | rows 18, 187 | under the text lines; the candy's sprite stays above row 191 |

How they were found, on the model (an energy probe: Σ m(v²/2 − g y) over
the free points, 300 ticks, and the stretch of a hanging rope):

* **One pass blows up unless the links are few and soft.** A 9-link rope
  of 7.5-px links with `FIXED_K` = 7 (stiffness 0.87) gains energy until
  the candy hits the ceiling, even hanging straight down; so does any
  rope of 6+ links at stiffness ~1 in one pass (the Gauss-Seidel sweep of
  a long chain likely has negative modes there, which the Verlet step
  amplifies; two passes square them). Stable in one pass: stiffness ≤ ~0.5
  for 8-10 links (a rubber rope: +12-37 % at rest), or ≤ ~1.1 for 4-5 links
  (+2-9 %). The levels use 3-4 links of 12-15 px with `FIXED_K` = 5: the
  rope stretches 2-9 %, a little like Cut the Rope's.
* **`FIXED_K` = 6 explodes** with two ropes on the candy even in two passes
  when one is slack; 5 is stable in every level configuration tried (1-2
  passes, slack 1.0-1.3).
* **A light rope whips.** With equal masses the rope's 8 points outweigh the
  candy and a swing throws it up to the ceiling; `HEAVY` = 1 (3×) and fewer
  links (less rope mass) keep the candy in charge.
* **Slack ropes start in their hanging shape.** A parabola of the right
  length but unequal links gave the first tick a jolt (+55 to +230 in the
  energy probe, from −40); `sag_points` relaxes it (exact lengths, pin and candy
  fixed) and stores 8.8 points.
* **Levels by search.** The cut windows come from running the model over
  every cut tick (and every pair for two ropes): the frog and the stars
  were placed on the trajectories so that the three stars need the right
  timing (`SOLUTIONS` holds one per level; the tests replay them).

## Measures

a2run, Apple II+ at 1.02 MHz (`make test` prints them):

| | Cycles |
|---|---|
| `phys_tick` (every rope on, 90 ticks, `--cycles`): level 1 (4 links) | 5,838 median, 5,967 worst |
| … level 2 (3 + 4 links, the slack one bobbing) | 9,049 / 9,097 |
| … level 3 (4 + 4 links) | 10,112 / 10,130 |
| … the bench (10 + 6 + 6 links, 23 points) | 24,249 / 24,856 |
| a tick's work (main to `pace`: input with the stick, tick, events, a page drawn), level 1 | 19,568 median, 25,806 worst |
| … level 2 | 27,079 / 29,353 |
| … level 3 (two ropes hanging, ~100 px of rope) | 30,195 / 31,117 |
| … frozen (the cursor only; with the message 24,427, with a jingle tick ~20,500) | 3,713 / 24,427 |
| the first ticks of a level printed the message (43,000-49,000: 3 frames) until the restart took it over | — |
| the flips (930 ticks: the solutions to their jingles, levels 2 and 3 hanging) | 930 of 930 34,060 cycles apart (± 13), all on line 193 |
| **the bench, one 10-link rope and two of 6** | **70,010 median, 70,842 worst: 4-5 video frames, does not fit**; one 6-link rope cut: 52,834 / 53,946; the 10-link rope alone: 33,870 / 36,010 |

**The budget.** The asked case — one 10-link rope and two 6-link ropes,
~30,000 cycles a tick — does not fit: 70,000 (24,000 of physics in one
pass, ~250 px of rope lines to erase and draw, the rest fixed). What a tick
costs is ~4,400 + ~2,950 a link drawn (~1,000 of physics with its point,
~1,900 of line: ~90 cycles a pixel of a steep line, ~38 to erase it, 180 to
set it up) + 3,150 of physics base, the stick ~1,500. So the levels keep
**two ropes of 3-4 links, ~100 px of rope in all**: level 3 is the worst
at 31,117 (the 34,060-cycle tick still holds every flip). The bench's
10-link rope alone (76 px; its two 6-link ropes cut) measures 33,870
median, 36,010 worst: it does not fit either (and needs two passes or a
soft gain to stay
stable): the 10-link case is a 20-Hz game (3 frames a tick) or a game
with cheaper rope drawing (TODO).

## Memory

| Range | What |
|---|---|
| `$0050-$00C0` | zero page (113 B): lib/math, lib/physics, hgr_plot_hist, text, the game's |
| `$0800-$0FFF` | HELLO (DOS kept) |
| `$1000-$17FF` | `mul_init`'s quarter squares (2 KB) |
| `$1800-$1DFF` | `hgr_plot_hist` histories (1.5 KB, 255 entries a page) |
| `$2000-$5FFF` | HGR pages 1 and 2 |
| `$6000-$7AE4` | CODE 6,885 B: the game ~1,640, `phys.inc` ~1,120, `verlet_seg` 800, `verlet_con` 606, `verlet.asm` 533, `hgr_plot_hist` 947, text, lines, sound, tune, keys, stick, vapor, exit |
| `$7AE5-$84A7` | RODATA 2,499 B: 4 level records 361, sprites 624 (candy, star, cursor, frog: 7 shifts each), jingles 38, messages, `vl_sq_lo/hi` 362, font 512, HGR row tables 384 |
| `$84A8-$8ABA` | BSS 1,555 B: 23 points (230), pins, the link and segment tables, the game |
| `$8ABB-$95FF` | free (2,885 B) |
| `$9600-$BFFF` | DOS 3.3 (ESC returns to it) |

The file is 9,384 bytes (`CUTROPE`, BRUN at `$6000`).

## Tests

`make test` (~2 s): `tests/test_cutrope.py` (the 12 runs, model == 6502)
then `tests/test_cutrope_disk.py` on the disk in a2run: boot (the two text
lines read back from the glyph bytes); level 1 keyed at its tick (`press:`
before the tick's input): the candy's trace every 5 ticks and the end
state == the model, the frog, 3 stars, "YUM!"; N, level 2's two cuts: the
stars == the model; N, level 3 cut too early: on the spikes, LOST, 4
candies, == the model; R; the cursor moved by I and swept by J with space
held: rope 2 cut; the stick moves it, button 0 cuts; the cycles (medians
and worst against `LIMITS`, measured + 5 %), the cadence (every flip
34,060 cycles apart and in the vertical blank), the bench (reported), and
a run without the floating-bus marker (unpaced, it still plays). The game
also boots and plays in a2shot (POM2's II+ core: paced, level 1 won with
three stars).

Files: `src/cutrope.s` (the game: input, events, drawing, pace),
`src/phys.inc` / `src/physdefs.inc` (the physics and rules),
`src/cutconst.inc` (generated), `tools/cutrope.py`, `tests/harness.cfg`
(the harness's snapshots in the HGR pages), `TODO.md`.

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../LICENSE).
