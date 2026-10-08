# Maze 3D — Apple II+ / DOS 3.3

A wire-frame first-person dungeon crawler in the Wizardry mould, for a
48 KB Apple II+. Three 11x7 floors are generated at run time, drawn in
double-buffered HGR with depth shading, and defended by goblins, orcs, dark
mages and a final dragon. Find each floor's relic, spend your gold between
floors, slay the dragon, and leave your best run on the disk so the next
player can replay the very same dungeon.

Apple II port of the POM1 sketch `sketchs/gen2/game_maze3d` (HGR_Maze3D,
VERHILLE Arnaud) from [POM1](https://github.com/habib256/pom1).

    make            # -> ../dist/MAZE3D.dsk  (bootable 5.25" DOS 3.3 image)
    make run        # boot it in POM2 as an Apple II+
    make test       # generation, rendering, menus and disk saves in the emulator

## Features

- **Generated dungeons.** Each floor is an 11x7 maze carved by a
  backtracking DFS, then enriched with three extra loops, a 2x2 chamber
  holding the floor's relic, and three hidden caches of gold (sometimes a
  potion too). `make test` verifies on 100 seeds that every floor is fully
  connected, that the relic sits in the chamber, that exactly three caches
  exist, and that the eight monsters stand on valid cells.
- **Fast HGR rendering.** Fdraw-inspired native line drawing, masked byte
  spans and an unrolled viewport clear. The default view reaches ten cells;
  the configuration menu offers 4, 6, 8 or 10. Packed sprites are generated
  at build time in seven sizes, from 1 to 64 pixels, and visible monsters
  are drawn far to near, with walls stopping the visibility scan.
- **Double-buffered 3D view.** Every full screen (3D view, map, combat,
  title, help, win/lose) is drawn on the hidden HGR page and shown with a
  single page flip: the previous picture stays up until the next one is
  complete.
- **Joystick controls.** Move and turn with the stick; buttons open the map
  and drink potions. In combat the stick selects all four actions, with
  attack and guard also on the buttons. Held controls never repeat a turn.
- **Turn-based combat** with four actions: `A` attack, `G` guard, `P` drink
  a potion, `F` flee. Each monster has a trait: the goblin may steal a coin,
  the dark mage's magic ignores your armour, the orc and the dragon announce
  a heavy strike one turn ahead.
- **Three floors and a shop.** Regular foes get tougher on floors 2 and 3;
  the dragon guards the last exit. Between floors a shop sells healing,
  attack, defence and potions.
- **Progress you can see.** Every visited cell reveals all four surrounding
  walls, including boundaries with unexplored cells. Known walls remain on
  the map. A compact heading (`F1 N`) shows floor and compass; short objectives
  track the relic, dragon and stairs; the HUD
  shows HP/30, potions and gold above a compact command reminder.
  ATK, DEF, LVL and XP are available on the help screen (`H`).
  Combat keeps a centred foe name and portrait, HP, potions, gold and four
  actions; secondary statistics stay on the help screen. Combat shows damage,
  action outcomes, a low-health warning at 8 HP or below, and a persistent
  next-attack bonus after guarding. Shop statistics update after purchases;
  feedback explains refused purchases and potions. A narrator comments on
  your stride.
- **Three profiles and manual saves.** Each profile has its own dungeon
  checkpoint. Press `ESC`, then `W` to save the current dungeon, including
  combat and shop progress. Movement, waiting and quitting do not save.
  Restart the disk, select the profile and press `C` to continue.
- **A2FC title.** The original HGR Maze3D picture from A2FC DEMO is stored
  with lossless LZ4FH compression; narrator text loads when play begins.
- **Shareable seeds.** `S` on the title screen lets you enter a dungeon
  seed as four hexadecimal digits, with correction.
- **Best run on disk.** A completed run earns a score; the best score and
  its maze seed are saved to `MAZESCORE` on the disk, and `R` on the title
  screen replays that exact dungeon.
- **Sound** for walls, hits, level-ups, stairs, victory and death, on the
  Apple II speaker.

## How to play

| Key               | Action                                        |
|-------------------|-----------------------------------------------|
| I or up arrow     | step forward                                  |
| K or down arrow   | step backward                                 |
| J or left arrow   | turn left                                     |
| L or right arrow  | turn right                                    |
| M                 | toggle map / 3D view                          |
| H                 | help screen                                   |
| P                 | drink a potion (+10 HP, up to 30)             |
| A / G / P / F     | attack / guard / potion / flee (combat)       |
| R (title screen)  | replay the seed of the best run               |
| S (title screen)  | enter a four-digit hexadecimal dungeon seed   |
| 1 / 2 / 3 (title) | select a saved profile                        |
| C (title)         | continue the selected saved dungeon            |
| N (title)         | start a new dungeon in the selected profile    |
| ESC               | open the configuration menu                   |

An Apple II+ only has left and right arrows; up and down work on a //e.
Lower-case letters are accepted. In the configuration menu, `S` toggles
sound, `D` cycles viewing depth, `R` / Return / Escape resumes, and `Q`
returns to the DOS prompt without saving the game. Press `W` in this
menu to save explicitly; `GAME SAVED` confirms completion. This menu also works from the title,
seed editor, map, help, combat and shop. Settings and the selected profile
are remembered on disk.

**Joystick.** Up/down steps forward/backward; left/right turns. Button 0
opens or closes the map and button 1 drinks a potion. In combat, up attacks,
down flees, left guards and right drinks a potion; button 0 attacks and
button 1 guards. Return the stick to centre or release a button before
repeating its action. The dead zone filters small movements; the vertical
axis takes priority on diagonals. Keyboard controls remain available,
including `H` for help and `ESC` for pause, save and settings. Title, shop
and menus use the keyboard.

**The quest.** You start in the top-left corner facing a dark corridor; the
exit `E` is in the bottom-right corner. Each floor's exit stays shut until
you have picked up the relic in the 2x2 chamber `R`. On floor 3 the exit also
demands the dragon's death. Caches `$` hold gold and sometimes a potion.
Eight monsters roam each floor; walking into one starts a fight.

**Combat.** `A` hits. `G` guards: the next blow you take is halved and your
next attack is strengthened. `P` drinks a potion. `F` flees with a 50 %
chance; a failed escape costs you a free hit, a successful one puts you back
on the previous cell. Each kill gives experience; every level-up adds 1 ATK,
heals 8 HP (up to 30) and adds 1 DEF every other level.

**Shop (between floors).** `H` heals 10 HP for 8 gold (maximum 30 HP),
`A` adds 1 ATK for 12 gold, `D` adds 1 DEF for 12 gold, `P` buys a potion
for 6 gold (nine at most). `C` descends to the next floor, `ESC` opens the configuration menu. Gold
is capped at 99.

**The map** reveals a wall as soon as either adjacent cell has been visited,
so all four walls surrounding the player are known without visiting the
neighbouring cells. Open passages remain open, and unexplored boundaries
remain hidden. It shows the chamber `R`, the caches
`$`, the relic `*`, the monsters you have seen from the corridors, the floor
number and the hexadecimal seed. The stairs `E` appear from the start of
each floor, even in unexplored areas or when a seen monster stands there.
The surrounding walls remain hidden until explored, and the relic/dragon
requirements still lock access. HP/30, potions, gold, the current objective
and event message also appear below the map.

**Seeds, score and record.** The key you press on the title screen is mixed
into the seed, so each key starts a different dungeon; `R` reuses the seed of
the best run instead. Press `S` to enter a seed from `0001` to `FFFF`
(the seed is displayed on the map and victory screen). Type four digits
`0`–`9`, `A`–`F`, then press Return to start. Lower case works too; the
left arrow, Backspace or Delete erases a digit, and Escape opens the
configuration menu without losing the typed digits. Incomplete seeds and `0000` stay in the editor until corrected;
zero would lock the random generator. Editing does not change the seed.
The same seed reproduces the initial floor; later floors and combat rolls
also depend on the actions taken during play. On victory the score is 100, plus 10 per cache found
and 5 per level gained, minus one point per four moves. A new record is
written to `MAZESCORE` on the disk; a write-protected disk still plays but
keeps no new record. The title screen shows the best score, the victory
screen shows score, best and seed.

## Build and run

Requirements: cc65 (`brew install cc65`), python3 and a C++ compiler for
the bundled fhpack compressor. Everything else, DOS
3.3 system tracks included, lives in [`../dev`](../dev/README.md); the build
rules come from `../dev/cc65/apple2.mk`.

    make            # assemble, link, write ../dist/MAZE3D.dsk
    make run        # boot the disk in POM2 (/Applications/POM2.app; or make run POM2=path/to/POM2)
    make test       # generation, seed editor, rendering, configuration and profiles
    make clean      # remove build/ (the disk stays)
    make distclean  # remove build/ and the disk

The disk carries `HELLO`, `MAZE3D`, `MAZETEXT`, `MAZESCORE`, `MAZETITLE`,
`MAZESTATE`, `MAZEPREFS` and `MAZESAVE1`–`MAZESAVE3`. `HELLO` loads the
record and preferences, then runs the game. The game decompresses the title
and loads the small state helper; narrator text is deferred until play.

**Continuing a game.** Select `1`, `2` or `3` on the title. `SAVED` means
`C` can resume that profile; `EMPTY` means no live checkpoint exists. Saving a new
game replaces only that profile. Saves preserve the entire floor, monsters,
player statistics, position, combat phase and random generator. Victory and
death leave the last manual checkpoint available; the best score remains. A write-protected
disk still plays, but cannot save changes. Wait for `GAME SAVED` before resuming or powering off.

## Tests

[`tests/check_generation.py`](tests/check_generation.py) boots the disk in
`../dev/tools/a2shot` (headless POM2 core; `a2run`, the portable equivalent,
works too with `--a2shot`) and generates 100 floors by poking a seed into the
PRNG at `$56/$57`, pressing a key, then reading the grid (`$1000`, 77 bytes)
and the monster table (`$10A0`, 32 bytes). For each seed it checks:

- only the start cell carries the DFS visited flag;
- exactly one relic, three caches and one 2x2 chamber, the relic in the
  chamber's bottom-right cell and the chamber open inside;
- no relic or cache on the start or exit cell;
- no passage through the outer wall, and at least 79 passages (a spanning
  tree of 77 cells plus three loops);
- all 77 cells reachable from the start;
- eight monsters inside the grid, none on the start, exit, relic or caches,
  each of type goblin, orc or dark mage, with at most three per cell.

`tests/check_seed_entry.py` also drives the title and seed editor with real
keystrokes: repeated seeds, lower case, invalid and excess characters,
early Return, correction, menu/resume, boundary seeds, rejection of zero,
and agreement with record replay.

`check_rendering.py` checks both HGR pages, rasterised lines, all sprite
sizes and palettes, preserved HUD/padding pixels, and monster visibility
through ten cells. `check_configuration.py` exercises seven menu contexts.
`check_profiles.py` writes actual DOS checkpoints, exports and reboots disks,
and checks independent profiles, combat continuation, absence of idle/quit saves, corrupt saves and
write protection.

`check_joystick.py` checks movement, held-input suppression, map and potion
buttons, all combat actions against their keyboard equivalents, idle RNG
and pause/resume with a held direction.

`check_ergonomics.py` checks all four map boundaries, open passages, retained
wall knowledge, objectives and rendered HUD/feedback text in the emulator.
Refused combat potions must leave the enemy phase unchanged.
`check_playthrough.py` completes seed `BEEF` through real keyboard input:
three floors, eight caches, shops, the dragon, victory and score 163
persisted in the exported DOS disk.

Build a2shot once with `make` in `../dev/tools/a2shot`.

## Under the hood

### Files

    src/maze3d.s               the game (ca65), BRUN at $6000
    src/narrator.asm           original narrator lines (all 96 retained)
    src/ux.inc                objectives, feedback and narrator decoder
    tools/pack_narrator.py     lossless five-bit text -> MAZETEXT at $1100
    src/sprites_trollkind.asm  goblin, orc (SCROLL-O-SPRITES)
    src/sprites_characters.asm dark mage (SCROLL-O-SPRITES)
    src/maze3d.cfg             ld65 config: ZP $50-$FF, state at $1000, text at $1100, code at $6000
    src/hello.bas              BLOAD record/preferences, BRUN MAZE3D
    src/save.inc              resident profile, checkpoint and preference code
    ../dev/lib/apple2/lz4fh.asm shared LZ4FH title decompressor
    tools/pack_sprites.py      build-time HGR sprite packing
    tests/check_generation.py  100 generated floors checked in the emulator
    tests/check_seed_entry.py  seed editor and record replay regression tests
    ../dist/MAZE3D.dsk         the disk image

### Memory map

| Range           | Content                                                  |
|-----------------|----------------------------------------------------------|
| `$0050-$00FF`   | zero page (game, text, sprite scratch); restored on exit |
| `$0800-$0FFF`   | HELLO, the Applesoft greeting program kept by DOS        |
| `$1000-$104C`   | GRID, the 77 maze cells (bit 0 north open, bit 1 east open, bit 2 cache, bit 3 relic, bit 4 chamber, bit 6 monster seen, bit 7 visited) |
| `$1050-$109C`   | DFS stack during generation; packed checkpoint between turns                                    |
| `$10A0-$10FF`   | monsters: 8 columns, 8 rows, 8 types, 8 HP               |
| `$1100-$1FFF`   | `MAZETEXT` at $1100-$1ADF (packed narrator and UX); title buffer before play             |
| `$1B93-$1E2F`  | `MAZESTATE`, resident save/resume helper                  |
| `$1F10-$1F17`  | `MAZEPREFS`, selected profile, sound and viewing depth     |
| `$1F00-$1F07`   | `MAZESCORE`, the record file                             |
| `$2000-$3FFF`   | HGR page 1                                               |
| `$4000-$5FFF`   | HGR page 2                                               |
| `$6000-...`     | `MAZE3D`, 13,016 bytes of code/data; BSS ends at $9505             |
| `$9600-$BFFF`   | DOS 3.3                                                  |

### The record file

`MAZESCORE` is eight bytes at `$1F00`:

| Offset | Content                                              |
|--------|------------------------------------------------------|
| 0-2    | magic `MZ3`                                          |
| 3      | format version, `1`                                  |
| 4      | best score                                           |
| 5-6    | seed of the best run (low byte, high byte)           |
| 7      | check byte: score XOR seed low XOR seed high XOR `$A5` |

At start the file is validated; a bad magic, version or check byte resets it
to the empty record (`MZ3 01 00 00 00 A5`, the file the Makefile writes to
the disk). A new record is saved with `BSAVE MAZESCORE,A$1F00,L$0008`
issued through `../dev/lib/apple2/dos.asm`, which swaps the zero page back to
DOS for the duration of the command. `disk_protected` skips the save on a
write-protected disk.

### Double buffering

Every drawing routine addresses the screen through the `hgr_hi` scanline
table. `set_draw_page` flips the table's 192 high bytes between `$2x` and
`$4x` (EOR `$60`, about 3.5k cycles), so the whole renderer moves to the
other page without knowing it. `vdp_display_off` points the table at the
hidden page, `vdp_display_on` shows it through the `$C054/$C055` soft
switches. The HUD, which is not redrawn on every step, is rebuilt on both
pages when it changes.

### Text and sprites

The game keeps its own 8x8 font (64 glyphs, ASCII `$20-$5F`, 512 bytes) in
TMS9918 bit order, bit 7 leftmost. `hgr_text8` renders it with `ht_rev = 1`:
each glyph row passes through `rev7_tab`, dropping the blank rightmost
column to fit 7 HGR pixels. Monster sprites start as 16x16 TMS-format patterns. The build converts them
to native seven-pixel HGR bytes in seven sizes. The runtime blitter copies
packed rows, applies colour phase and masks the last byte, avoiding runtime
bit-stream packing. Small distant silhouettes preserve visibility down to
one pixel; nearby clusters are byte-aligned and drawn in depth order.

### Shared libraries (`../dev`)

| Module                       | Role                                                   |
|------------------------------|--------------------------------------------------------|
| `lib/hgr/hgr_scanline.inc`   | `hgr_lo` / `hgr_hi` scanline address tables             |
| `lib/hgr/hgr_sprite_color.inc`     | shared sprite colour attributes                 |
| `lib/hgr/rev7.inc` | TMS-to-HGR bit-order table |
| `lib/hgr/hgr_text8.asm`      | byte-aligned 8x8 text (`HGR_TEXT8_NO_PUTS`, `ht_rev`)  |
| `lib/hgr/hgr_sprite_packed.asm` | prepacked row blitter with vertical repetition |
| `lib/hgr/hgr_line.asm` | native 8-bit-X line kernel; game retains virtual coordinate mapping |
| `lib/hgr/hgr_span.asm` | native byte/mask horizontal and vertical spans |
| `lib/hgr/hgr_clear_rows.asm` | visible-row, HUD and fast viewport clears |
| `lib/apple2/lz4fh.asm` | title decompression with game scratch aliases |
| `tools/assets/pack_hgr_sprites.py` | shared build-time sprite packing |
| `lib/apple2/hgr.asm`         | `hgr_init_clear`                                       |
| `lib/apple2/sound.asm`       | speaker tones                                          |
| `lib/apple2/exit.asm`        | `apple2_zp_save` / `apple2_exit`, clean return to DOS  |
| `lib/apple2/dos.asm`         | DOS commands from machine code, `disk_protected`       |
| `tools/dos33.py`             | builds the bootable disk                               |
| `tools/a2test.py`, `a2shot`  | the headless test harness                              |

## Differences from the POM1 original

The GEN2 card is the Apple II video subsystem on the Apple-1 bus, so the HGR
layout, map, HUD and combat presentation provide the basis of this port. What this
port changes:

- Apple II keyboard: the latch at `$C000` is cleared through `$C010`;
  lower case folds to upper case; the arrow keys alias IJKL.
- Soft switches at `$C050-$C057` instead of the GEN2's `$C250-$C257`.
- **Double buffering** between HGR pages 1 and 2. The original showed a
  black page while redrawing.
- ESC opens configuration; `Q` returns to the DOS prompt: the zero page is saved at start and
  restored on exit, so BASIC and DOS keep their pointers.
- One 12.7 KB binary BRUN at `$6000`, zero page at `$50`, maze state at
  `$1000`. The narrator's lines live in `MAZETEXT` on the disk, loaded at
  `$1100`, which frees about 2 KB of code space.
- A record file on the disk, `MAZESCORE`, and `R` to replay its seed.
- Gameplay added in this port: three floors, the relic chamber, caches,
  loops in the maze, the shop, guard/potion/flee, monster traits, the
  progressive map, the score, and sound.
- An inherited bug fixed: returning from the help screen (`H`) left
  "PRESS ANY KEY..." in the HUD instead of the statistics.

Planned work: see [`TODO.md`](TODO.md).

## Credits and licence

Game and port: VERHILLE Arnaud, 2026. Licence: GPL-3.0 (see
[`LICENSE`](../LICENSE) at the repository root), the same as the upstream
POM1 sketch.

Goblin, orc and dark mage sprites come from SCROLL-O-SPRITES by Quale
(May 2013, CC-BY-3.0). The dragon is an original sprite.

The HGR line optimisation is inspired by Fdraw; title compression uses
Peter Ferrie’s fhpack/LZ4FH. Their Apache-2.0 notices and source provenance
are kept in [`assets`](assets/README.md).

## Measured performance

Apple II+ emulator cycle counts, one 3D render including the page flip,
compared with the previous four-cell renderer. The new renderer uses depth
ten and scans all visible monsters.

| Scene | Previous cycles | Current cycles | Reduction |
|-------|----------------:|---------------:|----------:|
| Ordinary view | 168,034 | 157,580 | 6% |
| Long corridor | 263,634 | 210,601 | 20% |
| Nearby monster cluster | 478,675 | 242,706 | 49% |

The title shrinks from 8,192 to 3,249 bytes, with a byte-for-byte
decompression check during the build. Boot to the title input drops from
34,659,406 to 31,130,597 cycles (about 10%). These are emulator CPU-cycle
measurements with the same DOS boot; real disk timing depends on the drive.

Reproduce the current cycle counts with
`python3 tests/benchmark_rendering.py` from the `maze3d` directory.

At the shared-library extraction revision, the change added 17 bytes to the 13,025-byte baseline,
used no additional zero-page bytes and added at most 0.21% to the three
render benchmarks. Game coordinate mapping, monster placement and save
format remain in Maze3D. Shared modules are also exercised independently
by `python3 ../dev/tests/test_hgr_native.py`.
