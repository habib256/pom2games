# ChromaBreak

A brick-breaker for the **enhanced Apple //e and the Apple //c (128 KB, 65C02)** under
ProDOS 8: double hi-res in 16 colours, 60 sectors, six capsules, enemies, two-voice
music on the built-in speaker, and an AppleMouse II to steer the paddle. Bootable
140 KB disk: [`CHROMABREAK.po`](../dist/CHROMABREAK.po) (ProDOS 8 2.4.3).

Version 1.1 in preparation. Last published release: 1.0, with
[notes](../docs/releases/chromabreak-1.0.md) and the
[disk](https://github.com/habib256/pom2games/releases/tag/chromabreak-1.0).

ChromaBreak is a separate profile from [`arkabreakout`](../arkabreakout/README.md),
which targets the 48 KB Apple II+ under DOS 3.3 in HGR.

## Screenshots

The title and the sector screenshots are POM2 captures (//e profile, colour monitor
rendering) taken during the demo mode; the other screens are raw 560 × 384 renders from
a2shot.

![Title screen](screenshots/title.png)

![Sector 1, PRISM: an S capsule falls, a coil enemy enters through the right gate](screenshots/game.png)

| Help page | High scores |
|:--:|:--:|
| ![Help page: capsules, tiles and points](screenshots/help.png) | ![High score table](screenshots/records.png) |

| New high score | Game over |
|:--:|:--:|
| ![Initials entry](screenshots/initials.png) | ![Game over screen](screenshots/game-over.png) |

## Features

- DHGR 560 × 192, 16 colours, two video pages (main and auxiliary RAM); collisions on the
  140 colour columns.
- **30 frames per second NTSC, 25 PAL**, held in every tested scenario, including ten
  sprites on screen at Expert speed.
- **60 hand-drawn sectors**, from PRISM to OMEGA: geometric patterns, figures (INVADERS,
  HEART, GHOST, MUSHROOM, ROCKET, APPLE, SKULL, CASTLE, PACMAN, ROBOT...), mazes and
  fortresses, with one-, two- and three-hit tiles and steel.
- **Six capsules** in the Arkanoid manner: Enlarge, Slow, Catch, Disrupt (three balls),
  Laser, Pierce.
- **Two enemies**, a coil and a "TIE" fighter, that slip around the tiles.
- Combos up to ×8, an extra life every 5 000 points, six-digit score.
- A paddle that also **moves up**, to mid-field, with spin on the rebound.
- **Mouse, keyboard, joystick or Apple paddles**; the keyboard works with no mouse card.
- **Two-voice music**: a title theme, ten sector endings and a victory fanfare, on the
  one-bit speaker.
- Three difficulty levels, five high scores and the furthest sector saved on the disk.
- A help page (`?`), an attract/demo mode, a sector selector, and a finale with fireworks
  after sector 60.
- All on-screen text in English, in Michael Pohoreski's **Beautiful Boot** font.

## How to play

Boot the disk. The title shows "PLAY — CLICK / SPACE / ENTER": one gesture starts a game
with the ball already launched. Pick the difficulty with `1`, `2` or `3` first if you
like. After 15 s without a key, click or mouse motion, the demo mode plays by itself.

### Controls

| Input | Action |
|---|---|
| Click, Space or Enter (title) | Play, ball launched at once |
| `1` / `2` / `3` (title) | Relax / Arcade / Expert |
| `H` (title) | The five high scores; Escape returns |
| `?` (title) | Help page: capsules, tiles and points; any key or click returns |
| Mouse, horizontal | Paddle position |
| Mouse, vertical | Paddle height (absolute, from the floor up to mid-field) |
| Click, Space or Enter (in game) | Release an attached ball; fire with the Laser capsule |
| `M` / `K` / `J` | Choose mouse / keyboard / joystick or paddles; `K` and `J` also start a game from the title. Once chosen, the joystick stays selected from one game to the next and after a demo |
| Joystick X or paddle 0 | Paddle position (absolute) |
| Joystick Y or paddle 1 | Paddle height (absolute) |
| Button 0 or 1 (or an Apple key) | Same as the click: release the ball, fire the laser |
| `A` / `D`, left / right arrows | Move the paddle sideways (keyboard) |
| `W` / `X`, up / down arrows | Move the paddle up / down (keyboard) |
| `S` | Stop the keyboard motion |
| `P` | Pause / resume (sound stops while paused) |
| Escape | Menu (below); `Q` there quits cleanly to ProDOS |
| Ctrl-RESET | Clean return to ProDOS |

In POM2, put the pointer over the Apple II screen; relative capture toggles with
Ctrl+Alt+G and is also released by the middle click. A held click does not fire repeated
launches. Starting with Space or Enter keeps the mouse (or the joystick if it was chosen).

**Escape menu** (in game, on the title or on the end screens): Escape or `R` resumes the
game as it was (or returns to the title); the arrows or `A`/`D` pick a sector you have
already reached, shown with its name (from the title the menu opens on the furthest one);
Enter or Space starts a game on that sector. `S` toggles the sound, `T` returns to the
title, `Q` quits to ProDOS.

### Difficulty

| Mode | Lives | Paddle width | Start / max speed | Speed-up | Capsule |
|---|---:|---:|---:|---|---|
| Relax | 5 | 26 | 2 / 4 | every 10 tiles | every 4 tiles |
| Arcade | 3 | 22 | 3 / 6 | every 8 tiles | every 5 tiles |
| Expert | 2 | 18 | 4 / 7 | every 6 tiles | every 6 tiles |

Widths in DHGR colour pixels; speeds in sub-steps per frame. The keyboard moves the
paddle four columns or three lines per frame. The point of impact on the paddle selects
one of eight angles.

### Paddle, spin and scoring

The paddle rises up to mid-field (line 100) and never passes through tiles: under a tile
of the bottom row it stops six lines lower (line 112, where an attached ball sits); at
that row's height it is stopped by the first tile on its way, even on a large mouse move.
A paddle that slides under a low ball, or rises towards it, bounces it too: the
ball/paddle contact is checked every frame, before the ball's sub-steps.

Paddle motion puts spin on the rebound: a sideways slide drags the angle its way (one
zone, two from eight pixels per frame); a rising paddle steepens the bounce, a sinking
one flattens it.

Consecutive hits raise the multiplier every three tiles, up to ×8; a paddle contact or a
lost life resets it to ×1. A hit on a resistant tile scores 10 points; a destruction
scores 10 times the displayed multiplier. An extra life is granted every 5 000 points, up
to five lives. The score shows six digits and stops at 650 000; the sixty sectors are
worth at most 235 750 points, enemies excluded.

### Capsules

A capsule is a 5 × 6 coloured block with a white top and a black letter. The HUD shows the
name of the active bonus. A new life or a new sector clears the bonus; otherwise it lasts
until another capsule is taken. A paddle that rises past a falling capsule in one go
still collects it.

| Capsule | HUD | Effect |
|---|---|---|
| **E** orange | ENLARGE | Paddle widened by eight colour pixels |
| **S** pink | SLOW | Ball slowed to two sub-steps per frame |
| **C** red | CATCH | The ball sticks where it met the paddle |
| **D** purple | DISRUPT | Three balls fanning out |
| **L** blue | LASER | Two red cannons on the paddle, two shots; holding the click repeats |
| **P** light blue | PIERCE | Red, larger balls (4 × 7) that destroy resistant tiles in one hit |

A life is lost only when the last ball falls. Lasers take one hit point and are absorbed by
steel; the piercing ball still bounces on steel. Extra balls stay in play when another
bonus is taken, except Catch. Resistant tiles flash briefly on impact; a destruction
throws two shards of the tile's colour (four shards at most on screen), which vanish
without a trace on either video page.

### Enemies

Enemies arrive regularly (every 6 s in Relax, 4.5 s in Arcade, 3 s in Expert, two at
most) through two gates at the top or from the sides just under the tiles. Both are 4 × 6
pixels in changing colours, never to be confused with a ball. The first is a coil: top
and bottom bars around a narrow white core. The second is a "TIE" fighter: two coloured
vertical wings framing a white core, open at the top and bottom. They do not pass through
tiles: blocked downwards, they slide along the tiles until they find a way. Under the
grid, the coil wanders (new heading every 16 frames) while the TIE undulates (20 points
down, 12 up, every 32 frames); both leave through the bottom. A ball (which bounces), a
laser or the paddle destroys them for 100 points, with two shards. A lost life or a new
sector clears them. No enemy arrives during multiball, and the D capsule blows up those
present.

### Sectors, music and finale

A cleared sector shows "SECTOR nn CLEAR" in the centre, on the hidden page presented at
once, with a two-voice ending of a little over two seconds while the next sector is built
behind. There are **ten endings**, one per sector of each decade: the roots climb the
scale (C, D minor, E minor, F, G, A minor), then D, E and A major, the last going from
minor to major; the tenth sector of a decade gets a longer fanfare (3.3 s). Each ending
has its own bass cadence.

Each decade also has its own dark background pattern from level 1 onwards (stars, dotted
grid, hatching, masonry, lozenges, crosses), limited to the field above line 100 so that
the paddle always moves over black.

On arrival at the title a theme plays in **two voices** (about 5 s: the I-vi-IV-V chord
progression in rising arpeggios over a root/fifth bass, then a short closing phrase while
the bass climbs to the dominant). A key interrupts it; it does not replay after the demo,
after the help page or with the sound off.

After the sixtieth sector the finale "ENDING" is loaded from the disk at `$4000`: a
VICTORY logo in relief, "ALL 60 SECTORS CLEARED", the final score and mode, "THANK YOU FOR
PLAYING", a fanfare, then fireworks (rings of eight sparks that grow and fade to grey) in
the free bands above and below the texts, for about 20 s or until a key, before the
initials entry.

### Demo mode

After 15 s without a key, click or mouse motion on the title, a **demo** plays by itself,
silently and without recording any score: the pilot follows the ball with a varying
offset, relaunches it and fires the laser. The HUD shows "DEMO", and each demo takes the
next sector. A key or click, a lost ball or 60 s return to the title. Delays are counted
in video refreshes, and 50/60 Hz is detected at start-up, so it is 15 s in NTSC and PAL
alike, and the demo lasts 60 s of game frames in both.

### High scores and progress

The five best scores are kept in `HIGHSCORES` with three initials and the mode played. At
the end of a qualifying game, type A–Z, correct with the left arrow, confirm with Enter;
Escape skips the entry. A missing file is created on save; a corrupt one yields an empty
table. If the disk is write-protected or unavailable, "SAVE FAILED" appears and the score
stays visible in memory. The file is format 2 (byte 4), with scores in tens of points; a
file from version 1.0 (format 1, scores in points) is read with its records and
progress, then rewritten as format 2 on the next save.

**Progress** is saved in the same file (byte 5, zero in older files): the furthest sector
reached. It is written to the disk as soon as a new sector is reached, during the "SECTOR
nn CLEAR" banner (the demo records nothing), and bounds the sector selector in the menu. A
write-protected disk keeps the progress in memory for the session.

### Hardware

- **Apple //e enhanced** with the extended 80-column card (64 KB auxiliary), DHGR enabled,
  and an AppleMouse II card in any free slot. Without a mouse card, the keyboard works
  immediately.
- **Apple //c** with its built-in mouse: the ROM mouse interrupts stay active; the renderer
  only masks the brief video bank accesses.
- The game is 65C02 code. On an original (unenhanced, 6502) //e, the `CHROMA.SYSTEM` loader
  detects it first, prints "CHROMABREAK NEEDS A 65C02 CPU" and returns to ProDOS on a key
  (tested in POM2 with the `apple2e_unenh` ROM and an NMOS 6502). An original //e fitted
  with a 65C02 passes this test; without the enhanced ROM, it has not been tried.
- **RGB cards**: the game always selects the mixed DHGR mode of the Le Chat Mauve Féline,
  the //c RGB adapter and Video-7, where bit 7 of each byte selects 7 monochrome 560 dots
  (0) or 140 colour (1). Text is written with bit 7 clear, so it is pin-sharp on those
  cards; composite output ignores the bit and the picture is unchanged. See "Chat Mauve
  mode" below.

The game has been tested in emulation only (POM2, with the real //e and //c ROMs). Reports
from real hardware are welcome.

## Build and run

Prerequisites: cc65 (`ca65`, `ld65`, `cl65`, `ar65`), Python 3, and POM2 for `run`.

    make -C chromabreak            # builds ../dist/CHROMABREAK.po
    make -C chromabreak run        # POM2, //e enhanced + AppleMouse card
    make -C chromabreak run-iic    # POM2, //c with its native built-in mouse

The Makefile includes the shared [`../dev/cc65/apple2.mk`](../dev/cc65/apple2.mk), which
provides the tool variables (all overridable, e.g. `make POM2=... DIST=...`) and the
`run`, `clean` and `distclean` targets. `run` launches POM2 with `--preset iie --slot
4=mouseaw` (POM2's `mouse` card works as well); `run-iic` uses `--preset iic --slot
4=iicmouse`.

Targets: `all` (default), `run`, `run-iic`, `test`, `test-mouse`, `test-records`, `clean`,
`distclean`.

The build generates several sources from Python tools, and rebuilds them when their
inputs change:

| Tool | Generates | From |
|---|---|---|
| `tools/pack_levels.py` | `build/levels.bin`, `src/levels.inc` | `src/levels.txt` (checks every tile is reachable from below, boards and names distinct) |
| `tools/generate_layout.py` | `src/layout.inc`, `src/collision_tables.h` | `src/layout.h` (one screen geometry for C, assembly and the hit tables) |
| `tools/generate_sprite_tables.py` | `src/sprite_tables.inc`, `src/bg_tiles.inc` | round-sprite masks, shaded piercing ball, background tiles |
| `tools/generate_fine_font.py` | `src/fine_font.inc` | the shared Beautiful Boot font in `dev/lib/font`, via `dev/tools/fonts.py` |
| `tools/generate_music.py` | `src/music_aux.inc`, `src/music_offsets.inc`, `src/music_fanfare.inc` | the tunes, written in just intonation |
| `tools/seed_records.py` | `build/HIGHSCORES` | an empty, checksummed table |

The ProDOS volume (`CHROMABREAK`, 280 blocks) is assembled by
[`dev/tools/prodos/build_volume.py`](../dev/tools/prodos/README.md) from `PRODOS`,
`CHROMA.SYSTEM`, `CHROMA.SYS`, `HIGHSCORES` and the `ENDING` overlay.

## Tests

    make -C chromabreak test
    make -C chromabreak test-mouse   POM2_SRC=/path/to/pom2
    make -C chromabreak test-records POM2_SRC=/path/to/pom2

**`tests/test_game.py`** (`make test`) needs nothing beyond the build. It checks the link
map (the unused DHGR drawing, transfer and text modules of the library are excluded, the
library's small font is no longer embedded), the 60 distinct boards through
`pack_levels.py`, and the ProDOS image: volume name, 280 blocks, the five files and their
types, the boot block, the round trip of each file, more than 150 free blocks. Then, on
macOS with a2shot built (`make -C dev/tools/a2shot`), it boots the disk on an emulated
//e and checks the DHGR title, the keyboard fallback without a mouse card, at least
25 fps, pause, the keyboard controls, the direct start with Space, Enter and `K`, the
three difficulty settings, every one of the 60 sector transitions through the real
collision and level-loading code, the victory and replay, and the return to ProDOS text
by Escape/`Q` and by RESET. `--image-only` stops after the image checks.

**`tests/test_mouse.py`** (`make test-mouse`, optional) needs a built POM2 source tree
(`build/libpom2_core_test.a`) and its Apple ROMs; it compiles `tests/playtest.cpp` against
the POM2 core and runs the real firmware. It covers twelve profiles, two entries (click,
and Space then RESET) on six machines: the `applewin` and `mame` AppleMouse cards on the
//e, the native //c mouse with the 16 KB and 32 KB ROMs (and the two built-in serial
ports, whose ACIA status the //c ROM reads on every interrupt), and the PAL timings of
the //e and //c. It checks click/Space, the X/Y axes, pause, eight rebounds, tiles,
capsules, background restoration, solid paddles and the round white ball silhouette in
all seven DHGR phases, launch sounds and silence while paused, Escape/RESET and the
restoration of `/RAM`; frame intervals during mouse motion, the HUD cells, the vertical
paddle (mid-field, tiles above and beside, rebound, contact while sliding or rising, spin,
catch point), the enemies (tiles, sliding, ball, laser, paddle, exit, arrival, multiball,
restored backgrounds), the Chat Mauve mode (POM2's Féline card or //c adapter in mixed
mode, bit 7 of every byte of both pages and banks, back to 140 colour on exit), the demo
mode (15 s measured in emulated time, 50 Hz detection, silence, exit by key or lost ball)
and the transitions from both pages: no write to the displayed page.

**`make test-records`** runs the same harness with `--records-only`: the ProDOS writes and
the reload of the five entries, their sorting, initials and modes, a missing or corrupt
file, the write-protected disk, the format 1 to 2 conversion; the help page on the four
machines (capsules, tiles and enemies drawn, return to the title by a key then by a click
that starts no game, VBL clock intact) and `?` with the `ENDING` file missing; the music
(each note of the theme and the ten endings must carry its bass and melody, each at its
share of the speaker level, and last its slices; muted, a tune is silent and as long);
328 640 collisions against the round-ball model, the 65 536 score conversions, every
Beautiful Boot glyph at both alignments in both banks and pages, the 6502 message, and
the C stack margin.

The collision scenarios inject the initial state of each case; they are not a complete
campaign played end to end without intervention. The images under test are temporary
copies.

## Under the hood

### Memory layout

| Address | Bank | Contents |
|---|---|---|
| `$0310`–`$03CF` | main | Two-voice player (129 bytes) and the table of the ten endings, copied by `CHROMA.SYS` |
| `$0800`–`$0FFF` | main | Table image (`src/payload.s`): scanlines, bytes, phases, dot masks and background tiles, 1 784 bytes in a 2 KB zone; the font doubling tables are computed at start-up at `$0F00` |
| `$0A00`– | aux | The bank of sixty boards (3 480 bytes: two tiles per byte, then the names), followed by the Beautiful Boot font and the tunes |
| `$1000`–`$1FFF` | main | ProDOS file buffers, sprite backgrounds and metadata (`LOWBSS`) |
| `$2000`–`$5FFF` | main + aux | The two DHGR pages |
| `$4000`–`$5FFF` | main | The `ENDING` overlay (finale and help page), loaded into page 2 memory when needed |
| `$6000`–`$BDFF` | main | Game code, data and BSS |
| `$BE00`–`$BEFF` | main | C stack: 256 bytes, 18 used at most (measured) |
| `$BF00` | main | ProDOS global page |

`game.c` is compiled with `-Ors` (size); the critical routines are assembly.

### ProDOS start-up

The disk boots the small `CHROMA.SYSTEM` loader. Using 6502 instructions only, it first
checks for a 65C02 (an `INC A` that an NMOS 6502 executes as a NOP); on an original //e it
prints the message and QUITs to ProDOS. Otherwise it relocates itself to `$0800`, resolves
the boot volume's name with `ONLINE` and loads `CHROMA.SYS`, which copies the duet player
to page 3, the table image to `$0800`, the level bank and font to auxiliary `$0A00`, and
relocates the game image to `$6000`.

The game uses the auxiliary RAM directly, without checking `/RAM` and without a dialog.
On exit the ProDOS runtime restores the text screen, the mouse, the zero page, the RESET
vector and the system bitmap, then calls `QUIT`; the ProDOS RAM disk is recreated empty.

The help page and the finale live in the `ENDING` overlay, loaded at `$4000` by
`records.c`; the help page costs seven bytes of code in main memory. If the file cannot
be read, the title stays on screen. cc65 places every string literal in `RODATA`, hence
in main memory, even under a `#pragma rodata-name`: the overlay's texts are named arrays.

### Sectors

The boards are drawn as ASCII art in `src/levels.txt`: a name of at most ten letters,
then 8 rows of 12 tiles (`.` empty, `1`–`3` hits, `#` steel). `tools/pack_levels.py`
checks that every tile is reachable from below through non-steel tiles, that boards and
names are distinct, and packs the bank that `CHROMA.SYS` copies to auxiliary `$0A00`. The
game copies one board and its name at the start of each level (`level_fetch`).

### Rendering and frame rate

The presentation waits for two video refreshes: 30 fps NTSC, 25 fps PAL. The //e follows
the vertical blank during rendering; the //c uses the VBL mode of its mouse firmware and a
ProDOS interrupt handler, released on Escape or RESET. A new board is built on the hidden
page, shown complete once, then copied to the other page with the sprite backgrounds. The
waits have a bounded fallback if synchronisation disappears.

Sprites and text use an assembly engine with scanline and phase tables. The sprite
drawing loop is copied to the same address in both banks; its parameters and masks stay
in zero page. Backgrounds are saved per page and restored in reverse order. The HUD is
prepared once for both pages, each keeping its own history of displayed characters, and
redraws only the changed characters, one per frame; preparing the HUD and drawing a
character happen on different frames. A sliding paddle erases only the bands it uncovers,
and its seven DHGR alignments are cached, with constant colours. Collision tests reuse
empty zones during a ball's move; the cache is reset per ball and per frame. Impacts only
change a tile's slots or clear its surface. Capsules have per-row masks in zero page,
recomputed only when the column or type changes. The round 4-pixel sprites (red ball,
enemies) have precomputed masks for the seven alignments, like the white ball. Enemies
(`src/enemies.s`) move and test their contacts in assembly.

Tiles are bevelled in 12 alternating hues, with rounded corners, lit top and left edges,
shaded right and bottom, and a white highlight; resistant tiles carry one or two black
slots, steel a diagonal highlight. The frame is in two blues, the paddle cyan with a white
highlight, a blue shadow and rounded silver ends; the ball is a white rounded 3 × 6. With
Laser each end of the paddle carries a red 1 × 3 cannon (cannon and shot share a sprite);
shots are 1 × 4 with a white head on a yellow body. Piercing balls are shaded 4 × 7
spheres (pink left edge, red core, purple right edge) drawn one line higher, whose
collision silhouette stays 3 × 6; their per-pixel colours account for the one-dot shift
between the pixel window and the colour cell (`tools/generate_sprite_tables.py`).

The score is counted in tens of points (every gain is a multiple of ten): sixteen bits
reach 650 000, and the HUD's sixth digit is a fixed zero. It is also kept in BCD (65C02
decimal mode) so the HUD reads its digits without binary conversion, and HUD messages
are stored already aligned on their 10 cells.

**Frozen addresses.** The frame rate depends on the addresses of the assembly modules and
their tables: a taken branch or an indexed read that crosses a page costs one more cycle,
and a few bytes of shift have already cost a frame in the heavy scenes. `game.c` and
`records.c` are linked before them; `src/spare.s` separates them with a few spare bytes
(58 of code, 49 of constant data, 13 of variables) and three link-time assertions. When
one of the two C files changes size, adjust the spare by as much: nothing moves after
them and the frame rate needs no new measurement. `sound.s` keeps its size the same way
(27 bytes spare since the player moved to page 3).

### Text and the Chat Mauve mode

All text uses the 7 × 7 **Beautiful Boot** font with the HGR technique: its strokes are at
least two HGR dots wide, and each HGR dot becomes two DHGR dots, so a stroke covers four
dots, a full NTSC colour cycle: it stays white on a colour monitor, where a 560-dot text
would be unreadable. A cell is 14 dots, one whole auxiliary byte and one main byte; text
is placed every 7 dots (40 cells per line) and written without reading video memory
(`src/finetext.s`). Its planes, `src/fine_font.inc`, are generated by
`tools/generate_fine_font.py` from the shared `dev/lib/font`.

The game always selects the mixed DHGR mode of the RGB cards (Le Chat Mauve Féline, the
//c RGB adapter, Video-7), where bit 7 of each byte selects 7 monochrome 560 dots (0) or
140 colour (1). Every graphics byte keeps bit 7 set (clears to `$80`, masks that preserve
it); only text writes it clear and is then displayed in pin-sharp 560 dots. The HUD is a
monochrome band and each text line starts with a black monochrome byte, so that no
neighbouring colour cell bleeds. These cards have nothing readable, so no detection is
possible or needed: in composite the bit is ignored in DHGR, and the Eve falls back to
140 colour; the picture is unchanged. The lock is set at start-up (with IOUDIS on the //c,
otherwise `$C05E/$C05F` would set the mouse) and reset to 140 colour on exit.

### Music and sound

The speaker plays distinct sounds for the launch, rebounds, steel, hits and destructions,
bonuses, sectors and a lost life. Effects are spread over several frames; the mouse
interrupts stay active. Pause silences the sounds.

**Two voices on one bit.** The theme, the ten endings and the fanfare have a melody and a
bass on the single speaker bit (`src/duet.inc`, the MICRO-SOKOBAN engine). Two square
waves share the speaker by time division: at each turn of the loop (33 cycles) the player
looks at the bass, then at the melody. While both are at the same level the speaker rests
there; when they differ it flips at both looks and follows the bass for 13 cycles, the
melody for 20, at 31 kHz. That carrier is inaudible: what remains is the sum of the two
waves, the melody a little louder. Every path through a turn takes 33 cycles, so a
half-period is a whole number of turns: `tools/generate_music.py` writes the tunes in just
intonation, in the scale of C whose periods are whole (C4 = 60 turns, a fifth of a
semitone under concert pitch), with the nearest counts for the sharps of D, E and A
major. Notes that would fall between two counts (F5, D6, C7) do not exist: the melodies
are written around them, and the fanfare ends on C6 instead of C7. An event is three bytes
(melody, bass, duration in slices of 8.3 ms). The player (129 bytes) and the table of the
ten endings are copied to page 3 (`$0310` to `$03CF`) by `CHROMA.SYS`: its loop counts
cycles and must not straddle a page, and the game loses no byte to it. Interrupts are
masked during a note and served between two notes (on the //c, the sixty mouse interrupts
per second blurred the two voices). With the sound off, a tune is silent but keeps its
duration.

### Input

In keyboard play the mouse is not polled (about 1 300 cycles saved per frame); `M` reads
it again before handing control back. Joystick and paddles (`J`): both analog timers
start together (`$C070`) and are counted inside the wait that precedes each presentation
(`timing.s`, a 23-cycle loop, one count for two of the paddle's). Reading stops at the
vertical blank (//e) or at the toggling interrupt (//c); an unfinished axis keeps its
previous value, so the frame rate never depends on the controller, even at full scale
(tested on the twelve profiles). On the //c the `$C070` access also acknowledges the VBL
interrupt: if it falls during that very access, the frame is shown one refresh later. The
mouse is not polled in this mode. The mouse height is absolute: the firmware bounds the
pointer to the paddle's travel (the Makefile passes `MOUSE_Y_LOW/HIGH/START` from
`layout.h`).

References: [ProDOS interrupts](https://prodos8.com/docs/techref/adding-routines-to-prodos/)
and the [Apple IIc technical notes on VBL](https://mirrors.apple2.org.za/Apple%20II%20Documentation%20Project/Computers/Apple%20II/Apple%20IIc/Documentation/Apple%20IIc%20Technical%20Notes.pdf).

### Shared libraries (`../dev`)

| Library | Used for |
|---|---|
| [`dev/lib/hgrc`](../dev/lib/hgrc/README.md) | DHGR pages, clear and layout tables (`dhgr_clear_asm`, `dhgr_layout.inc`); the unused drawing and text modules are excluded at link time |
| [`dev/lib/prodos`](../dev/lib/prodos/README.md) | ProDOS MLI, `crt0_prodos`, file I/O for `HIGHSCORES` and `ENDING` |
| [`dev/lib/mouse`](../dev/lib/mouse/README.md) | AppleMouse II and native //c mouse driver; VBL mode 9 and the ProDOS interrupt handler on the //c |
| [`dev/lib/apple2c`](../dev/lib/apple2c/README.md) | Keyboard and the VBL frame pacing (`apple2frame`) |
| [`dev/lib/gfx`](../dev/lib/gfx/README.md) | `gfx_u16_digits` (65C02): the decimal digits of the HUD and score screens |
| [`dev/lib/font`](../dev/lib/font/README.md) | The Beautiful Boot master glyphs, from which `fine_font.inc` is generated |
| [`dev/tools/prodos`](../dev/tools/prodos/README.md) | ProDOS 8 2.4.3 image, boot block and volume builder |

## Releases

- **1.0**: [release notes](../docs/releases/chromabreak-1.0.md),
  [disk and tag](https://github.com/habib256/pom2games/releases/tag/chromabreak-1.0).
- **1.1** (in preparation): the paddle rising diagonally under a bottom-row tile, or
  widened between a tile and a wall, no longer leaves the field (the machine used to
  freeze); the score reaches 650 000 on six digits and an extra life comes every 5 000
  points, with `HIGHSCORES` in format 2 and format 1 files converted; `?` with the
  `ENDING` file missing keeps the title on screen; the demo lasts 60 s in PAL as in NTSC;
  the mouse height is absolute (no travel lost after a lost life); the joystick chosen
  with `J` stays the control after a game over and after a demo; a paddle that rises past
  a capsule in one go collects it; "V1.1" on the title.

## Credits and licence

Code and boards: **VERHILLE Arnaud**, GPL-3.0 (see the `LICENSE` at the repository root).
Beautiful Boot font: **Michael Pohoreski**. ProDOS keeps its own credits and rights.
