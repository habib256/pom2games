# DIRTBIKE

Side-view motocross for the Apple II+ 48 KB (HGR, DOS 3.3 disk), inspired by
Brad Quick's *Dirt Bike* on the Macintosh and by the PHYSICS demo. You race
against the clock on 30 tracks of 3 laps each, from very easy to very hard,
and jumps and flips score points. The game is in English. You have to work
the throttle and lean the bike to land on its wheels: if the rider touches
the ground, you crash. Best times and scores are kept on the disk.

    make             # ../dist/DIRTBIKE.dsk (empty hall of fame)
    make run         # in POM2 (Apple II+)
    make test        # 30 tracks rideable, physics, brake and points 6502 ==
                     # model, joystick and keyboard, exact loading, title,
                     # demo, save

## Controls

| Joystick (paddles) | Keyboard | Effect |
|---|---|---|
| X left / right, analog (paddle 0's dial) | ← → or J / L | lean back / forward |
| button 0 (paddle 0's) | A / ↑ full throttle, Z / ↓ half throttle | throttle; on the keyboard, once released, it drops back to zero in ~1 s and the bike slows down |
| button 1 (paddle 1's) | SPACE | brake (it cuts the throttle) |
| | H | help page (title, menu) |
| | R | restart the track |
| | S | sound off / on |
| | ESC | in a race: the main menu, ESC again: the race resumes (from the track menu: the title page) |
| | Ctrl-RESET | the title page |

The keyboard always steers. The joystick (or a pair of paddles) steers too
when it is the device chosen in the main menu (option 3: JOYSTICK, PADDLES,
KEYBOARD in turn): a fresh disk picks the joystick if the game port answers
at boot; the choice is written to `DIRTHOF` when leaving the menu
(`inp_pref`, 0: the joystick, 1: the keyboard, 2: the paddles) and restored
at boot if something is still plugged in. The joystick's position at boot
is taken as its centre; the **paddles** (2026-10-24, asked by players) lean
from the middle of paddle 0's travel (`PDL_MID`, 40 counts: a dial has no
rest position), with the same levels, and in the menus a dial moves the
marker one step each time it turns 16 counts past the last step, or past
where it was when the menu opened (`stick_calib`: a calibration on the dials'
current position), paddle 1 up / down, paddle 0 left / right: a dial left
aside, even at its end, neither scrolls nor gives a step on entry. **Analog lean**:
`stick_lean` (`src/input.inc`, mirrored in `tests/test_input.py`) gives 0
within 6 steps of `read_stick_fast` from the centre (dead zone), then
1 + (|d| − 6) / 4, at most 8, with the sign of d: level 8 from 34 steps on
(~80 % of the travel, ±42 at full deflection), 4 at half travel. Each level
moves the rider along the bike (`LEAN_BACK`, `LEAN_FWD` in `tools/physics.py`):
0.5 px per level up to level 4 (2 px: fine control of a wheelie), then 1 px
per level up to 6 px, on both sides. Before (2026-10-22), 4 levels of 1 px,
4 px on both sides: with the throttle on and the rider back, the front rose to
−20° in 16 to 19 ticks and never reached −45° at 9 px/tick; now −20° in 10
ticks, −45° in 16. Forward of the middle, the rider **is moved** (`FWD_K`,
`_shift`): his point and his previous position move together along the wheel
axis, with no velocity. Before, changing the rest lengths pulled him into
place in one tick: a stick flick from one end to the other (10 px) yanked
the front wheel up (~4 px/tick), drove the rear wheel down and threw the bike
into the air, where the forward lean flipped it over; at 6 px, the linear
correction (it overshoots when a link is much longer than its rest length)
crushed a rider link on the next tick. Hence the forward side capped at 4 px.
The back side keeps this kick: it is what lifts the front. In the air, the
rotation per level (`AIR_TURN`) stays at most 4 (45° in 10 ticks, as before).
The keyboard gives level 8, like the stick pushed all the way. **Buttons**:
button 0 (the trigger on most Apple joysticks, the Open Apple key on the //e)
is the throttle, held for most of the race; button 1, the brake. Both
together: the brake wins. The Y axis is only used in menus. Without a
joystick (the two paddle timers never time out), the game reads nothing from
the game port: the button inputs float and would read "pressed" on a II+. On
the keyboard, lean lasts 6 frames after each keypress, throttle and brake 20
(the initial auto-repeat delay of the //e: a held SPACE braked for 6 frames,
then nothing until the repeat, and never on a II+); SPACE cuts the keyboard
throttle, A / Z cut the brake.

**Brake** (2026-10-22, model `tools/physics.py`, checked by
`tests/test_physics.py`). It removes `BRAKE` from the tangential speed of each
wheel on the ground, down to zero (never past it: no reverse). A wheel in the
air does not brake the bike: the brake only stops its spin, and while it is
still spinning, its angular momentum passes to the frame (1 rotation unit per
tick per wheel, nose down for a wheel that was rolling forward). Before, it
was odd:
1. the throttle won: full-throttle traction (8 × 31 per tick) drowned the
   brake (2 × 32); and on the keyboard the throttle stays held 20 frames
   after A: SPACE right after the throttle did not brake, the bike still
   accelerated (throttle and brake held: 13.5 px/tick, forever);
2. it was weak: ~0.6 g of the game's gravity, less than the engine; from
   13 px/tick to a stop: 120 ticks (4 s) and ~670 px;
3. a stopped, braked bike rolled back: the second constraint pass (the
   rider's weight) moved the wheels the brake had just stopped (~1 to 2 px
   in 10 s on the flat, ~85 px in 200 ticks on a 1/2 slope);
4. on the keyboard, SPACE only braked for 6 frames per keypress;
5. in the air or in a wheelie, held, it turned the bike by 4 steps per tick
   (`GYRO_BRAKE`, as much as a maximum lean) for as long as it was held:
   +150° in a 20-tick jump, and a braked wheelie tipped onto the front
   (+48°, rear wheel up).

Now: the brake cuts the throttle (`phys_tick`); `BRAKE` = $40 (~1 g): from
13 px/tick to a stop in 72 ticks (2.4 s) and ~430 px, decreasing steadily
(12.9 → 10.1 → 7.5 → 5.1 → 2.9 → 0.9 → 0 px/tick every 12 ticks, on the
flat); a wheel that the brake stops within the tick stays where the tick
found it (x and previous x: static friction): the bike stops and stays
stopped, uphill as well as downhill. In the air, each wheel's spin (`spin`,
its speed at the last contact) loses `AIR_SPIN_BRAKE` = $0600 per braked
tick: a wheel at full speed stops in 3 ticks, and the bike turns by ~12° in
all (maximum lean for 20 ticks: ~145°), nothing more after that; its speed
does not change. A braked wheelie sets down gently (the rear wheel brakes on
the ground).

**Title and demo** (`src/title.inc`, image `tools/title.py`). The game opens
on a title page (file `TITLE`, LZ4FH, 1.8 KB), with the port credit ("APPLE
II PORT: VERHILLE ARNAUD", on a black band at the bottom) and "PRESS ANY KEY"
blinking under the subtitle; a key or the button leads to the menu, H to the
help page. The title music plays once: when it ends (~13 s), a demo starts:
the 3 laps of one of tracks 5, 19, 10, 26, 22, 30 (in turn, 35 to 45 s)
replayed bit for bit from the solver's solution, stored at the end of the
track file and copied to `$1000-$1FFF` on loading, then the two pages of the
hall of fame, then the title.

**Menu.** The 30 tracks in two columns: arrows (or I J K L) or joystick to
choose (one step per push, the stick returns to the centre for the next one;
held, it repeats), RETURN, SPACE or a button to start. Only tracks already
finished (those with a time in the hall of fame, hence saved on the disk) can
be chosen, plus the first one not yet finished; the others show their number
and dashes. A game then chains the tracks: after the finish (and the
initials for a record), a key starts the next one; ESC returns to the menu;
after track 30, a congratulations page (and the record flourish). Below the
list: the record and the reference time, the one found by the solver.

**Race.** Countdown "3, 2, 1, GO!" (you can already work the throttle). Its
frames last as long as in the race (a wait of ~2 video frames): shorter, they
flipped pages almost every video frame, and POM2's "beam racing" rendering,
which rereads memory at the end of the frame, showed the page being redrawn
(the bike flickered; see `dev/tools/a2shot/LETTRE_POM2_AFFICHAGE_MANETTE.md`).

**Main menu** (ESC in a race, `src/mainmenu.inc`): back to the race (0, only
during an unfinished race), title page, help, input device (joystick, if it
answered at boot, or keyboard only), hall of fame, quit to BASIC. Arrows
(I / K) and RETURN, or the digits 0 to 5; ESC: back to the race, otherwise
the title page. Resuming (`race_resume`) rereads the track, which `TITLE`
overwrote, redraws both pages and restarts after a countdown, with the bike
and the clock where they were. With the joystick, up / down move the marker,
one step per push; a button selects, and closes the help and the hall of
fame. Its code and texts are an overlay of the `TITLE` file: linked to run at
`$9C00` (`build/menu.bin`, stored by `tools/titlefile.py`), it arrives with
`TITLE` in the load buffer, over the loaded track (reloaded before every race
anyway). "QUIT TO BASIC" leaves the marker "QU" at `$8000` and reboots the
disk: HELLO sees it, clears it and stops ("DIRTBIKE: BYE!") instead of
restarting the game; you are back in BASIC with DOS 3.3.
After a crash, the bike restarts from standstill, after "1, GO!", at the
start of the last stretch of flat ground where it rode on both wheels
(`note_safe`: a single ground height under the bike, give or take one wheel
on each side; the start, so as to have the whole straight to build up speed
again). Each lap has 6 to 22 of them, never more than ~820 pixels apart. The
clock kept running during the crash, the lap and the score remain, only the
pending points are lost (R restarts the race).

**Sound.** No engine noise. A short looping tune on the title page, a jingle
at the finish, extended with a flourish for a record. A thud when landing a
jump, a beep for points, an arpeggio for a flip, two dull thuds for a crash,
beeps for laps and the countdown (`tone`, lib `apple2/sound.asm`: the note
blocks the game for as long as it lasts). Silent in the demo; S mutes it.

The tunes are written as notes in `tools/music.py` (3 bytes per note:
duration in 1/60 s ticks, half-period, and the number of alternations that
fill one tick). `music_tick` (`src/title.inc`) plays a one-tick slice in place
of the `tick_wait` delay: the title page blinks and responds to keys during
the music. The title tune sits at the head of the `TITLE` file, before the
text pages and the LZ4FH image, and plays from the load buffer: it costs no
RAM. `tick_wait` stops as soon as it ends: the demo starts on the last note.
The jingles stay in the program.

**Points** (`src/tricks.inc`, model `tools/tricks.py`). A jump of at least
12 ticks (0.4 s) scores 10 points per tick in the air; each flip (a full
turn, forward or backward, counted in 45° sectors of the wheel axis) scores
1000 points × the number of turns squared (4000 for a double, 9000 for a
triple). A wheelie (rear wheel on the ground, front wheel in the air) of at
least 15 ticks scores 10 points per tick when it ends. Points wait 20 ticks on
the wheels before being added to the score ("JUMP +nnn", "FLIP +nnnn",
"WHEELIE +nnn"): a crash loses them.

**Finish line.** A flag (2-pixel pole and pennant, `draw_flag`) marks the
line, which is also the lap line. It is marked like the bike
(`bk_top`/`bk_bot`): the ground renderer gives it its sky back when it
scrolls. It is drawn point by point across the whole width (x from 0 to 279,
clipped at the right edge): back when it went through `hgr_line8` (8-bit x),
it only existed below 244 and flickered at that limit when the camera
wobbled by one pixel. The lap number (1 to 3) is written under its pennant.

**Status bar.** At the top: the clock on the left, the score on the right
and, in the middle, the messages (tricks, laps, countdown, CRASH, FINISH,
DEMO), centred on 14 characters. The bar only redraws the characters that
change, page by page: a shorter message erases what is left of the previous
one on both pages.

**Tracks.** Each track is a loop (length a multiple of 7, at most 3760
pixels): 400 flat pixels at the start, a flat 300-pixel straight before the
line, and the loop starts again. For the screen and the bike, the array
repeats the first 336 pixels after the end; 128 pixels past the line, the
bike and the camera move back together by one lap (`phys_wrap`, identical in
the model): nothing changes for the physics or the image. "LAP 2", "FINAL
LAP"; after the line on the 3rd lap, the bike brakes to a stop on the start
straight. The two arrays of a track (height and pattern per pixel) already
fill the 8 KB freed from DOS: laps rather than a track twice as long.

**Hall of fame** (`src/hof.inc`). For each track, the best time and the best
score, each with three initials. After a record, you type your initials
(letters, or joystick up/down and left/right, RETURN or a button); the game
then rewrites the two sectors of the `DIRTHOF` file through RWTS. On a
write-protected disk, it says so and carries on. `make` recreates an empty
hall of fame.

## How it works

**Physics** (`src/physics.inc`, model `tools/physics.py`). The bike is made
of three Verlet points: rear wheel, front wheel and rider, linked by the
wheelbase (rigid, 24 px) and two wheel-rider links (the suspension). The
rider weighs a little more than a wheel (9/7: in a link, the wheel takes
`c + c >> 3` of the correction, the rider `c - c >> 3`, `c >> 3` rounded
toward zero: rounded down, the stopped bike rolled back on its own; at 3
times, the bike became uncontrollable in the whoops). On each tick:
1. gravity, then clamped velocities: 18 px/tick along the track, 8
   vertically; traction pushes up to 13.5 px/tick;
2. rotation of the wheel axis: a wheel in the air that the brake stops
   gives its spin to the frame (1 unit per tick while it is spinning); in
   the air, lean and throttle (nose up) turn it too. In the air or on one
   wheel, rotation is damped (`>> 4` per tick: no more endless spinning);
3. distance constraints without square roots. Lean moves the rider along
   the bike (`LEAN_BACK` / `LEAN_FWD`: up to 6 px on both sides, 8 levels;
   rest-length tables per level in `physconst.inc`; forward of the middle
   he is moved, with no velocity, `fwd_k`): on the ground, it is his weight
   that lifts or sets down the front, no more direct rotation (the bike no
   longer rides upright);
4. wheel contact with the ground, following the normal derived from the
   slope `h[x+2] - h[x-2]`: bounce, then traction (rear wheel), brake,
   engine braking with the throttle off (rear wheel, `vt -= vt >> 7`) and
   rolling resistance (`vt -= vt >> 7`): with the throttle off, speed drops
   by ~30 % in ~1.5 s and by half in ~3 s on the flat. The brake cuts the
   throttle;
5. the constraints once more, after the ground: the wheelbase stays between
   ~18 and 27 px (it used to drop to 1 px, the bike folded up); firm
   suspension (stiffness 0.9; 1.2 then 1.0 made the game a little too easy):
   big landings taken well get through; a wheel that the brake stopped
   returns to where the tick found it (see **Brake**);
6. crash if the rider gets close to the ground, if his head (drawn at
   rider + 3 × (dy/8, −dx/8), the wheel axis turned upward) goes below the
   ground, if a rider-wheel link drops below half its length (rider
   crushed) or if the bike goes onto its back (one wheel on the ground, the
   front behind the rear: a looped wheelie).

The wheelie: throttle and rider back lift the front; releasing the throttle,
leaning forward or braking sets it down; pushing too hard loops it. The
squares in the constraints are read from the quarter-squares table
(x² = 4·⌊x²/4⌋ + (x & 1)) instead of a multiplication: the physics costs
~14,400 cycles per frame.

Positions are in fixed point: x in 16.8 (world pixels), y in 8.8. Products
go through `dev/lib/math` (quarter squares, 2 KB built at boot at `$0800`,
shortcuts for ×0 / ±1.0 normals). The asm reproduces the Python model bit
for bit: `tests/test_physics.py` checks it, points included, on a 545-tick
script (crash and tumbles included) and on the full 3 laps of tracks 1, 19
(a flip, wheelies) and 30 taken from `tests/solutions.txt`.

**Tracks** (`tools/tracks.py`). Tracks 1 to 3 are written by hand; the
others are drawn from a vocabulary of elements (bumps, hills, ramps, gaps,
tables, steps, drops, whoops, stairs) whose size and severity grow with the
number, from a seed fixed per track. Each one is proven rideable:
`tools/solver.py` searches for a path in the physics model (beam search over
lean, full or half throttle and brake; failing that, a beam that keeps all
speeds, for crests that must be taken braking, then a beam 1.5 times wider
(track 12 after the brake rework); each tick leaning back costs it a little,
otherwise the demo rider stayed sitting back; a finish only counts if the
bike then holds for 90 ticks, braked as the game does after the line: the
demos crashed under "FINISH !") and `tests/solutions.txt` keeps it;
`make test` replays it (`tools/trackcheck.py`). The paths (3 laps) last from
20 s to 41 s. A new seed must also fit within the renderer's limits
(`POOL_MAX`, 256 patterns: `make` checks it).

**Format** (`tools/track.py`, `tools/packtrack.py`). For each world pixel,
the game keeps the ground height and the number of the "pattern" of the
7-pixel window starting there, i.e. what an HGR byte shows when the camera
puts that pixel at a byte boundary. A track has at most 165 patterns, whose
partial bytes share a pool (783 bytes at most). Each track is a file
`T01`..`T30`: a header and two LZ4FH streams (from 596 bytes to 2.3 KB,
56 KB in all).

**Loading** (`src/loader.inc`). Once started, the game keeps only DOS's
RWTS disk driver (`$B700-$BFFF`). The chosen track is read sector by sector
into the freed area, then decompressed: heights at `$9600`, patterns at
`$A600`. The position of each file's sector list is written into the game
after the disk is built (`dev/tools/dos33patch.py`, called by the Makefile).
`tests/test_tracks.py` checks that memory after loading matches the Python
compilation exactly.

**Rendering** (`src/render.inc`). Double-buffered HGR, pixel scrolling. A
screen column is computed with a few table lookups (pattern, height, partial
bytes), whatever the camera offset. Each page remembers what it shows, and
only the lines that change are rewritten. Runs of at least 4 lines of sky or
ground go through an unrolled writer (`STA line,Y` for each line, 5 cycles
per line) generated at boot for each page. Line accesses read the table of
the page being drawn, selected by patching the operands; there is no longer
a table rewritten every frame. The bike is drawn with OR using a home-made
Bresenham and unrolled sprites. The lines it covered are repainted two
frames later; those that were in the white ground have nothing to erase. The
HUD only rewrites the characters that change.

**Timing.** The clock counts ticks (30 per second), so a time does not
depend on the display speed (25 to 30 frames per second). Races (3 laps)
last from 20 s to 41 s. The messages under the status bar are only written
on the first frames, then 2 frames out of 8 (the ground renderer does not
touch the sky).

**Memory.** `$0200-$03CF`: input buffer and user page, useless here (neither
BASIC nor DOS commands): `hgr_lo` / `hgr_hi`, computed at boot
(`dev/lib/hgr/hgr_scanline_ram.asm`: 384 bytes less in the file).
`$0400-$07FF`: text page 1, never displayed (the game does not return to
DOS); its eight 120-byte bands (segments `TXT0`-`TXT7`) hold renderer tables,
the HUD buffers and routines (the menu, the display of a track in the menu,
`do_shift` and `mul_turn` from the physics: `TXTC4`, `TXTC5`, `TXTC7`, copied
at boot); the screen holes (`$x78-$x7F`, `$xF8-$xFF`, where RWTS and cards
keep their state) are left alone. `$0800-$0FFF`: multiplication tables (where
the HELLO program used to sit). `$1000-$1FFF`: line writers, renderer and
pattern tables, demo inputs, hall of fame. `$6000-$91FF`: the game (code,
data, BSS; ~25 bytes free). `$9200-$95FF`: the startup code (segment `INIT`:
init, renderer, HGR line and multiplication tables, joystick detection,
reading the hall of fame) and the images of the text-page routines, the end
of the file, run once then overwritten by the track's pattern pool (`pool`)
on the first load; ~200 bytes remain there.
The `TITLE` file carries the title tune, the text pages (help,
congratulations: `tools/pages.py`), the main menu (at `$9C00`) and the image
(`tools/titlefile.py`): reread on demand, it costs no RAM.
The game variables (BSS) are in a band of the text page (`TXT6`).
`$9600-$B5FF`: the track (in place of DOS; the title and the hall of fame
also pass through there). `$B700-$BFFF`: RWTS. The game's zero page
(`$50-$FB`) is almost full.

## Tools

| File | Role |
|---|---|
| `tools/physics.py` | reference model; `python3 tools/physics.py` rides it at full throttle |
| `tools/physconst.py` | generates `src/physconst.inc` (constants and tables) from the model |
| `tools/tracks.py` | the 30 tracks: names, elements, seeds |
| `tools/track.py` | compilation into 7-pixel patterns; `track1`, the physics test track |
| `tools/solver.py` | finds a path per track (`--all tests/solutions.txt` after a track or physics change) |
| `tools/trackcheck.py` | replays the solutions, checks the format limits |
| `tools/packtrack.py` | `T01`..`T30` files (LZ4FH) and menu data |
| `tools/tricks.py` | points model (jumps, flips), replayed by the physics test |
| `tools/title.py` | the title image (`OUT.hgr [aperçu.png]`) |
| `tools/hof.py` | the empty `DIRTHOF` file |
| `tools/music.py` | the tunes: `src/music.inc` (jingles) and `build/tune.bin` (title) |
| `tools/titlefile.py` | the `TITLE` file: tune, pages, main menu (`$9C00`), image |
| `tools/pages.py` | help and congratulations pages: `src/pages.inc` and `build/pages.bin` (in `TITLE`) |
| `tests/test_input.py` | joystick and paddles (analog lean, buttons, menus, no joystick) and device choice, in a2run |
| `tools/sprites.py` | generates `src/sprites.inc`: wheel (4 spoke positions × 7 shifts), head |
| `tools/autopilot.py` | simple autopilot (tuned for the old speed; the physics test now replays the solutions) |
| `tools/profile.py` | a2shot profile: cycles per frame and per routine (`dev/tools/a2profile.py`) |

The `dev/lib` libraries used are `apple2` (HGR, keyboard, joystick, LZ4FH,
RWTS), `hgr` (tables, 8×8 text, lines, pages), `math` and `font`; `fhpack`
compresses the tracks and the title.
