# CUTROPE

A "Cut the Rope"-like for the Apple II+ 48 KB (HGR, DOS 3.3 disk,
assembly, `dev/lib` only). A candy hangs from one or more ropes; cut them
at the right moment, puff it with the air cushions, let a bubble carry it
and pop it, bounce it off trampolines, so that it lands in the frog's mouth, touching as many of the
three stars as it can on the way. 25 levels, chosen from a menu;
the stars won are kept on the disk.

    make              # ../dist/CUTROPE.dsk (+ dist/woz/CUTROPE.woz), boots into the menu
    make run          # in POM2 (Apple II+, an AppleMouse in slot 4)
    make test         # 6502 physics == the Python model, the disk in a2run, the mouse in a2shot
    make test-long    # every level's solution on the disk: cycles and cadence
    python3 tools/cutrope.py                   # the levels' solutions on the model
    python3 tools/cutrope.py --solve [N...]    # the solver: every schedule of each level
    python3 tools/design.py TEMPLATE           # level candidates by search (below)
    python3 tests/test_cutrope.py --no-disk --cycles   # phys_tick cycles per level
    python3 tests/test_cutrope_disk.py --fit   # refit the pace estimate

## How to play

The menu shows the levels five a row with their stars (`*` won, `.` not
yet, `---` locked: a level opens once the one before it is won) and the
stars won in all. I J K L, the arrows, a push of the stick or the mouse
choose; space, RETURN, button 0 or a click play; ESC quits to DOS.

| Keys | Joystick / mouse | Effect |
|---|---|---|
| `1` `2` `3` | | cut rope 1, 2, 3 (numbered as in the level's record) |
| `4` `5` | | puff air cushion 1, 2 |
| `6` | | pop the bubble that holds the candy |
| `I` `J` `K` `L` (or the arrows) | the stick's axes; the mouse | move the cursor (a cross); a key moves it 3 px a tick for 6 ticks (the II+ has no key-up), the stick 1-3 px a tick by its deflection, the mouse puts it where it points |
| space | button 0; the mouse's button | the "knife": while it is held (space holds it 8 ticks), every rope the cursor touches is cut, a cushion under the cursor puffs, the bubble under it pops |
| `R` | | restart the level |
| `N` | | the next level, after a win (after the last one: the menu) |
| `ESC` | | back to the menu |

The candy bounces off trampolines; it is lost when it touches spikes, leaves the field (the bottom,
the sides) or floats away in its bubble (to the top); `R` tries again, as
often as wanted. It is won when its centre enters the frog's 14 × 14 box.
The top line shows the level, the stars taken and the stars won in all;
the second line the keys, then the result. A snip sounds at a cut, a blip
at a star or when the bubble catches the candy, a puff and a pop, a short
jingle at the end. A better result is written to the disk when the level
is left (`N`, `R`, `ESC`).

**The mouse** (an AppleMouse II card in any slot, or the //c's): with its
button up the cursor goes where it points; held down, the cursor follows
it 3 px a step on each axis, up to 6 steps a tick (18 px), and the knife is
tried on every step's point: a quick swipe cannot jump over a rope (the
knife's reach is 2-2.8 px). The steps are tried before the tick, as cuts by
key, so the physics stays the model's; a long swipe costs a step's test
(~900 cycles) each, in the pace estimate.

## The levels

`tools/levels.py` holds them, data only, each with a solution (keys at
ticks: the candy into the frog with the three stars) that the tests replay
on the model and on the 6502, and the windows the solver found. Levels 1-3
are the prototype's; the others come from `tools/design.py`: a template
draws a level's skeleton at random (where the candy hangs, its ropes, a
bubble where the candy will pass, cushions aimed at where it will be when
they puff, spikes on the floor or none) and a plan of keys; the plan is
played on the model, the frog put where the candy ends (on a ledge), the
stars along its path. A candidate is kept when `tools/solve.py` finds that
the plan gives 3 stars, each of its keys can move 2 ticks either way and
still give 3 stars (a window of 5 ticks at least: 1/6 s), doing nothing or
cutting everything at once does not give 3 stars, and few of all the
schedules with as many keys give 3 stars (15 % with one key, 4 % with two,
2 % with three: the level asks for the timing). The templates: `swing`,
`two`, `three` (ropes), `bubble`, `swing_bubble`, `two_bubble`, `cushion`
(a puff swings the hanging candy), `drop_cushion`, `two_cushions`,
`bubble_cushion`, `tramp` (a trampoline where the candy lands),
`two_tramps` (the second where the first sends it), `tramp_cushion` (a
puff after the bounce), `two_tramp` (two ropes, then a trampoline); with
trampolines the candy must bounce on each before the frog.

| # | Name | What | Keys of the solution (tick) | 3-star windows (each key alone) |
|---|---|---|---|---|
| 1 | SWING | 1 rope (4 links) | 1 @45 | key 1 43-48 |
| 2 | LET GO | 1 rope (3 links) | 1 @59 | key 1 55-63 |
| 3 | TWO ROPES | 2 ropes (3 + 4 links) | 2 @6, 1 @105 | key 2 0-16, key 1 101-109 |
| 4 | BACKSWING | 1 rope (3 links) | 1 @73 | key 1 67-76 |
| 5 | SPIKES | 2 ropes (4 + 4 links), spikes | 1 @4, 2 @52 | key 1 0-11, key 2 44-62 |
| 6 | FIRST PUFF | 1 rope (3 links), 1 cushion, spikes | 4 @5, 1 @51 | key 4 0-9, key 1 45-61 |
| 7 | SLACK | 2 ropes (4 + 3 links) | 2 @10, 1 @71 | key 2 0-24, key 1 64-76 |
| 8 | SIDE WIND | 1 rope (3 links), 1 cushion, spikes | 1 @21, 4 @39 | key 1 17-34, key 4 35-45 |
| 9 | BUBBLE | 1 rope (4 links), bubble, spikes | 1 @44 | key 1 41-49 |
| 10 | HIGH PIN | 1 rope (4 links) | 1 @36 | key 1 32-39 |
| 11 | TUG | 2 ropes (3 + 3 links) | 1 @6, 2 @82 | key 1 0-9, key 2 77-87 |
| 12 | BLOW AND GO | 1 rope (3 links), 1 cushion, spikes | 4 @5, 1 @54 | key 4 0-12, key 1 46-60 |
| 13 | BALLOON | 1 rope (4 links), bubble, spikes | 1 @73 | key 1 53-96 |
| 14 | CROSSWIND | 1 rope (3 links), 2 cushions, spikes | 1 @18, 4 @36, 5 @48 | key 1 14-25, key 4 31-40, key 5 45-51 |
| 15 | LATE PUFF | 1 rope (3 links), 1 cushion, spikes | 1 @40, 4 @60 | key 1 37-42, key 4 57-65 |
| 16 | PUFF AND POP | 1 rope (3 links), bubble, 1 cushion, spikes | 1 @23, 4 @61, 6 @73 | key 1 16-37, key 4 49-64, key 6 70-113 |
| 17 | LEFT FIRST | 2 ropes (4 + 3 links), spikes | 1 @4, 2 @72 | key 1 0-10, key 2 70-76 |
| 18 | NUDGE | 1 rope (3 links), 1 cushion | 4 @14, 1 @58 | key 4 11-16, key 1 55-63 |
| 19 | RELAY | 1 rope (3 links), 2 cushions, spikes | 1 @29, 4 @44, 5 @56 | key 1 23-37, key 4 39-49, key 5 45-65 |
| 20 | DRIFT | 1 rope (4 links), bubble, spikes | 1 @80 | key 1 62-92 |
| 21 | LONG DROP | 1 rope (4 links) | 1 @38 | key 1 36-40 |
| 22 | QUICK PUFF | 1 rope (3 links), 1 cushion | 1 @37, 4 @46 | key 1 34-40, key 4 40-50 |
| 23 | DOUBLE SNAP | 2 ropes (4 + 4 links), spikes | 1 @9, 2 @51 | key 1 0-11, key 2 48-54 |
| 24 | STORM | 1 rope (3 links), 2 cushions, spikes | 1 @26, 4 @43, 5 @55 | key 1 23-35, key 4 38-47, key 5 44-62 |
| 25 | SKY FROG | 1 rope (4 links), bubble | 1 @72 | key 1 44-81 |

The bubble levels but PUFF AND POP are won by floating into the frog (the
pop is there to save a candy floating away); PUFF AND POP is won only by a
pop over the frog, after a puff has moved the bubble off the way up (a
one-off search, not a template of `design.py`: frogs below the bubble,
the same checks but 10 % of the 3-key schedules allowed). A
generated level keeps 7 links, bubble and cushions at most (TUG, first
with 4 + 4 links, took a star with all 8 links on at its third tick:
33,913 cycles, a frame late; it was replaced).

`python3 tools/cutrope.py --solve 5` plays every schedule of level 5 (as
many keys as its solution, `--depth`, `--step`, `--until`, `--horizon`),
prints how many win with how many stars, the 3-star ones grouped in
windows, and the stored solution's windows.

## What it shows

* **Python first.** [`tools/cutrope.py`](tools/cutrope.py) is the game's
  physics and rules (a `verlet.Points` subclass with `verlet.constrain`
  and `verlet.SegmentGround`), the level compiler, the sprites and the
  jingles; it writes `src/cutconst.inc` through `verlet.emit`.
  [`src/phys.inc`](src/phys.inc) transcribes it;
  [`tests/test_cutrope.py`](tests/test_cutrope.py) plays scripted runs
  (every level's solution, level 3's spikes, a level left swinging, the
  cursor sweeping across the ropes with the button held, random play,
  the bench, and two levels of its own for the bubble and the cushions:
  caught, floated, popped by key and by the cursor, floated away, puffed
  in the four directions, the button held on a cushion) on both and
  compares the whole state every row (points, pins, state, ropes on,
  stars, events, the bubble, the cushions' waits, the contact and its
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
* **The bubble** (one a level) catches the candy by the stars' test on its
  centre. Caught, the candy floats: after the integration its speed loses
  `v >> 3` on both axes and `BUOY` ($0030) is taken off its vy, so it rises
  at `BUOY − GRAVITY` and tends to ~0.8 px a tick (~24 px/s); still on a
  rope it pulls it up. Key 6, or the button with the cursor within 7 px of
  the candy, pops it; above row `BUB_TOP` (22) it has floated away: lost.
  Free, it is drawn with the stars (11 × 11 sprite); caught, round the
  candy.
* **The air cushions** (two a level) point right, down, left or up. A puff
  (key 4 / 5, or the button with the cursor within 6 px of one; then 10
  ticks before the next) changes the candy's speed, before the
  integration, when its pixel is ahead: along the axis 0-79 px, across at
  most 10 + along / 4 (a cone); the speed change `PUFF[along >> 3]`, from
  2 px a tick close to 0.44 far. A rope still on takes its share of it.
  The bellows are 8 lines drawn with the scenery; a puff, 3 short lines
  for 4 ticks.
* **Trampolines** are horizontal segments of kind 2 (`SEG_TRAMP`). The
  contact is the platforms' (`verlet_seg`: pushed out, the little bounce,
  the friction along); then the candy's old y is set so that it leaves
  upwards as fast as it came down (its vy taken before the contact, 2 px a
  tick at least, `TRAMP_MIN`): no energy lost, it comes back to the height
  it fell from, with its speed along kept, so a candy cut on the swing
  bounces on in arcs. A "boing" sounds (EV_BOING). Drawn as a platform on
  two 6-px legs.
* **Levels** are compiled records (`compile_level`, at most 252 bytes):
  rope count, the candy, 3 stars, the frog's box, the segment count, the
  bubble (x = 0: none), the cushions (x, y, direction); per
  rope its pin, link count, rest length² (`l2q`) and its inner points
  (8.8: the compiler relaxes a slack rope into the shape it hangs in, so
  that a level starts without a jolt); per segment its kind, its drawn
  line and its 14 bytes of `vl_sg_*` (`segments.py`). The model reads the
  same bytes (`Level`). On the disk they are the file LEVELS, level k in
  its k-th sector after DOS's 4-byte header (`--levels`), the bench last;
  `dos33patch.py --sectors` writes where those sectors lie into
  `lvl_t` / `lvl_s` when the disk is built, and [`disk.inc`](src/disk.inc)
  reads the chosen one through RWTS into `$0900` (DOS stays: ESC from the
  menu returns to it). CUTSAVE, one sector, keeps per level 0 (not won) or
  the stars + 1 behind the magic `CRS1`; a foreign or unreadable file is
  "nothing won". The menu is [`menu.inc`](src/menu.inc).
* **Drawing only what changes, as a stack.** The platforms, the spikes and
  the cushions and the frog are drawn once on both pages at a level's
  start (the frog with `pl_sprite`, its history then dropped). Each page's
  `hgr_plot_hist.asm` history is a stack: the stars and the free bubble at
  the bottom (drawn again only after a star is taken or the bubble catches
  the candy or pops), then the puffs, the ropes, the candy and its bubble,
  the cursor on top. A tick gives back (`pl_erase_to`, EOR) what lies above the
  stars and draws the ropes, the candy and the cursor again; once the end
  is on both pages, only the cursor. The counters and the message are
  rewritten only when they change, per page; the message (a 40-character
  line, ~20,000 cycles) only at a restart or once the picture is frozen.
* **30 ticks a second, flipped in the blank.** A tick every 2 video frames
  ([`vapor.asm`](../dev/lib/apple2/vapor.asm): `vapor_mark_both` after each
  clear, nothing drawn below row 190, `vapor_pace` waits for the tick's
  last frame from an estimate of its work). The estimate is a sum of what
  the tick did: a base, 2,950 a link (or a puff) drawn, 950 a digit, 900
  a knife test of the mouse, and a term per flag of `tkf` (the physics, a
  short sound, a blip, the jingle's tick, the stars drawn again, the
  message, the candy's bubble), fitted by least squares on 6,368 ticks
  (`--fit`: residuals −4,913 … 5,386, the tolerance is half a frame,
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
  timing (each level of `tools/levels.py` holds its solution; the tests
  replay them). `tools/design.py` and `tools/solve.py` do it now (see
  The levels).

## Measures

a2run, Apple II+ at 1.02 MHz (`make test` prints them):

| | Cycles |
|---|---|
| `phys_tick` (every rope on, 90 ticks, `--cycles`): SWING (4 links) | 5,548 median, 5,709 worst |
| … TWO ROPES (3 + 4 links, the slack one bobbing) | 8,684 / 8,738 |
| … SPIKES, DOUBLE SNAP (4 + 4 links) | 9,751 / 9,760, 9,720 / 9,764 |
| … one rope and a cushion (FIRST PUFF), a bubble (BALLOON) | 4,679 / 4,801, 5,718 / 6,054 |
| … the bench (10 + 6 + 6 links, 23 points) | 23,410 / 23,980 |
| a tick's work (main to `pace`: input with the stick, tick, events, a page drawn), SWING | 19,418 median, 25,633 worst |
| … TWO ROPES | 26,844 / 29,100 |
| … SPIKES (two ropes hanging, ~100 px of rope) | 29,937 / 30,824 |
| … PUFF AND POP (the bubble round the candy, a puff, the pop) | 7,540 / 17,905 |
| … FIRST PUFF | 14,490 / 21,040 |
| … STEPPING STONES (two trampolines) | 7,267 / 16,338 |
| … frozen (the cursor only; with the message ~24,400, with a jingle tick ~20,500) | 3,674 / 24,413 |
| … every level (`make test-long`) | the worst 30,824 (SPIKES) |
| a knife test of the mouse (`knife`: near over the ropes on) | 4 links ~930, 7 ~1,590, 8 ~1,810 |
| the flips (`make test-long`: the 25 solutions to their jingles, TWO ROPES and SPIKES hanging; 4,543 ticks) | 4,543 of 4,543 34,060 cycles apart (± 15: a poll is 13 cycles, `vapor_sync`'s once-in-256 wrap path 2 more), all on line 193 |
| **the bench, one 10-link rope and two of 6** | **69,216 median, 70,033 worst: 4-5 video frames, does not fit**; one 6-link rope cut: 52,242 / 53,359; the 10-link rope alone: 33,416 / 35,555 |

**The budget.** The asked case — one 10-link rope and two 6-link ropes,
~30,000 cycles a tick — does not fit: 70,000 (24,000 of physics in one
pass, ~250 px of rope lines to erase and draw, the rest fixed). What a tick
costs is ~4,400 + ~2,950 a link drawn (~1,000 of physics with its point,
~1,900 of line: ~90 cycles a pixel of a steep line, ~38 to erase it, 180 to
set it up) + 3,150 of physics base, the stick ~1,500. So the levels keep
**two ropes of 3-4 links, ~100 px of rope in all**: SPIKES is the worst
at 30,824 (the 34,060-cycle tick still holds every flip). A swipe of the
mouse adds up to 5 knife tests (~1,800 each with 8 links): such a tick may
take 3 frames; the estimate counts them, so it is paced, not late. The bench's
10-link rope alone (76 px; its two 6-link ropes cut) measures 33,870
median, 36,010 worst: it does not fit either (and needs two passes or a
soft gain to stay
stable): the 10-link case is a 20-Hz game (3 frames a tick) or a game
with cheaper rope drawing (TODO).

## Memory

| Range | What |
|---|---|
| `$0050-$00BF` | zero page (112 B): lib/math, lib/physics, hgr_plot_hist, text, the game's |
| `$0800-$08FF` | HELLO (DOS kept) |
| `$0900-$09FF` | LVBUF: the level's sector (`disk.inc`) |
| `$0A00-$0AFF` | SAVBUF: CUTSAVE's sector |
| `$1000-$17FF` | `mul_init`'s quarter squares (2 KB) |
| `$1800-$1DFF` | `hgr_plot_hist` histories (1.5 KB, 255 entries a page) |
| `$2000-$5FFF` | HGR pages 1 and 2 |
| `$6000-$8528` | CODE 9,513 B: the game, the menu, the disk, `phys.inc`, lib/physics, `hgr_plot_hist`, text, lines, sound, tune, RWTS, keys, stick, mouse (`dev/lib/mouse`), vapor, exit |
| `$8529-$8FA9` | RODATA + DATA 2,689 B: sprites 855 (candy, star, cursor, frog, bubble: 7 shifts each), the cushions' and puffs' lines 144, jingles, messages, `vl_sq_lo/hi` 362, font 512, HGR row tables 384, the disk's sector tables |
| `$8FAA-$95FC` | BSS 1,619 B: 23 points (230), pins, the link and segment tables, the game, the stars won |
| `$95FD-$95FF` | free (3 B: the next feature has to make room, e.g. the menu's picture ~75 B) |
| `$9600-$BFFF` | DOS 3.3 (ESC from the menu returns to it; its RWTS reads the levels) |

The file is 12,202 bytes (`CUTROPE`, BRUN at `$6000`); LEVELS 26 sectors
(the 25 levels and the bench), CUTSAVE one. The levels moved to the disk:
in memory they would take ~2.8 KB, more than is free.

## Tests

`make test` (~10 s): `tests/test_cutrope.py` (model == 6502: every level's
solution, the spikes, the cursor sweeping, random play, the bench, the
bubble and the cushions), then `tests/test_cutrope_disk.py` on the disk in
a2run: boot to the menu (read back from the glyph bytes); levels 1-3 won
from their solutions (traces and states == the model, the counters, "YUM!")
with `N`; SPIKES cut too early (LOST, == the model); `R`; the cursor moved
by I and swept by J with space held: a rope cut; the stick moves it,
button 0 cuts; `ESC`: the menu with 9 stars and the choice; CUTSAVE
written (`CRS1`, 4 4 4 0…); a second boot of that disk: the same menu,
PUFF AND POP and FIRST PUFF played from their solutions (== the model);
the cycles (medians and worst against `LIMITS`, measured + 5 %, and every
tick under 33,000), the cadence, the bench, and a run without the
floating-bus marker (unpaced, it still plays). Then
`tests/test_cutrope_mouse.py` in a2shot with an AppleMouse (AppleWin's
model): the menu follows the pointer, a click plays, the cursor goes where
it points, one 45-px swipe with the button cuts the rope, a move without
it does not. `make test-long` plays every level's solution on the disk
(cycles and cadence).

Files: `src/cutrope.s` (the game: input, the mouse, events, drawing,
pace), `src/menu.inc` (the menu), `src/disk.inc` (the levels and the
stars on the disk),
`src/phys.inc` / `src/physdefs.inc` (the physics and rules),
`src/cutconst.inc` (generated), `tools/cutrope.py` (the model),
`tools/levels.py` (the levels), `tools/solve.py` (the solver),
`tools/design.py` (the level search), `tests/harness.cfg`
(the harness's snapshots in the HGR pages), `TODO.md`.

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../LICENSE).
