# MICRO-SOKOBAN — TODO

Status on 2026-10-07: **no open task**. Controls and technical details are in
the [README](README.md); level sources and solutions in
[levels/README.md](levels/README.md).

## Next up / ideas

None of these is started. Each is grounded in a comment, a release note or a
known limit; the resident budget (about 380 bytes free, 230 in `BOOTCODE`)
means any addition must first free memory.

- **Real-hardware check.** Every release note says the tests validate
  emulated execution only; the two-voice title music "has not yet been heard
  on real hardware" (1.2 notes), and the disk timings are POM2 cycles, not a
  physical Disk II. Boot the image on an Apple II+ or //e, listen to the duet
  and the game sounds, and time the boot.
- **Refresh the header comment of `src/micro_sokoban.s`.** It still says the
  packs are "up to 4 KB" and "BLOADed", that "H or ESC = menu", and lists
  T / O / F / Q as HELP keys. The packs are at most 2 KB and read through
  RWTS, H opens HELP, and those letters are menu keys.
- **Freeze deadlocks.** The DEADLOCK warning covers dead squares only; a crate
  frozen against another (a 2 × 2 block, for example) is not detected, while
  `tools/solver.py` already has the freeze rule. Worth porting only if it fits
  the budget.
- **Partial recovery of a records file.** A file with one unreadable sector is
  dropped whole (empty profile, rewritten at the next save); the records of
  its readable sectors could be kept instead.
- **More collections.** The build pipeline is generic (`COLLS` in the
  Makefile, `PREFIX:HUD:FILE` arguments of `tools/micro_sokoban_levels.py`),
  but the SOK2 file, the fingerprints and the demo table are sized for the
  four current collections, so a fifth one means a new save format.

## Constraints and known limits

- Apple II+ 48 KB, HGR, DOS 3.3; keyboard and joystick.
- No scrolling: every level fits in 20 × 12 cells, clear of the HUD corners.
  Levels too tall are turned when that lets them fit; the others are left out.
  Their original numbers are kept.
- The DEADLOCK alert detects the dead squares computed from the goals,
  including corners and wall edges without a goal. Blocks between crates
  (a 2 × 2 freeze, for example) stay outside this detection; the solver
  detects them.
- Undo/Redo keeps the last 1024 moves in memory only. The history starts empty
  after a reboot, a profile change or a tutorial replayed during a game
  (position and counters are given back). If the start of the level has been
  forgotten, RESTART reloads the level instead of rewinding it.
- A records file with one unreadable sector is dropped whole (empty profile,
  rewritten at the next save): the records in the sectors still readable are
  not recovered.
- With the same number of solved levels, the ranking compares the total of
  best moves; the result therefore depends on the levels chosen.

## Done

### 1.0 — first release

- **Display**: blue walls, white player with a marker under the feet on a
  goal; crates off goal filled orange, crates and goals green. Small text
  white, colour reserved for ×2 titles; HUD with moves, pushes,
  collection/original number and best result.
- **HGR rendering**: whole screens drawn on the hidden page then shown; only
  the changed tiles are redrawn during moves.
- **Gameplay**: Undo/Redo on keyboard and joystick, stick auto-repeat,
  RESTART undoable with Redo, 16-bit move and push counters, crates-left
  counter and a DEADLOCK sound alert that can be switched off.
- **Levels**: 454 Microban I to IV levels (150, 122, 92 and 90), XSB
  conversion with rotation/filtering, thirteen packs of at most 2 KB, grid
  selection, solved levels marked and a summary at the end of a collection.
- **Solutions**: one checked solution per level, A* solver plus YASS for 33
  levels; `make test` plays all 454 in the real game.
- **Tutorial**: five lessons with hints, offered on the first game and
  replayable; completion saved per profile, no effect on the ranking.
- **Menu and help**: PLAY / RESUME, TUTORIAL, PROFILES, RESTART, GO TO LEVEL,
  OPTIONS, HALL OF FAME, HELP and QUIT TO DOS.
- **Profiles**: ten independent profiles, creation/renaming on keyboard or
  joystick, unique names; selecting the active profile keeps the game and the
  history without reading the disk.
- **Records and ranking**: per-level records (moves, then pushes), automatic
  saving; ranking by solved levels descending, then total of best moves
  ascending on 32 bits; HOF3 format and migration of the old HOF1/HOF2.
- **Save and resume**: independent SOK2 files per profile, 1830 bytes of
  records and a 134-byte position; per-collection fingerprints, position
  CRC-8, save on menu/HELP or after about six seconds without input; invalid
  position ignored, write-protected disk respected.
- **Title**: progress and active profile, version, corridor animation, then
  the ranking for ten seconds and a seven-level demo; the presentation is
  interrupted by a key or a button, nothing saved.
- **Sounds**: step, push onto a goal, impossible move, undo, dead square and
  victory; game/menu/demo sounds set separately, game and menu on by default,
  demo silent by default.
- **Loading and disk**: shared `../dev` libraries, LZ-packed program loaded at
  `$6000`, RWTS reads with cached sector lists, optimised DOS allocation and
  writes limited to the changed sectors.

### 1.1 — music, solutions, monochrome

- **Title music** (one voice) on the Apple II speaker, controlled by MENU
  SOUND, stopped when leaving the title.
- **Solution playback**: solutions read from `MICROSOL`, SOLUTION entry
  conditioned by CHEAT MODE, no progress recorded while watching.
- **Monochrome tiles**: crates on goal with a hollow green frame and a white
  check mark; the seven tiles stay distinct without colour.
- **Title presentation**: white centred credits ("APPLE II PORT BY" /
  "VERHILLE ARNAUD"), white profile and version labels on black panels,
  animation at about 1.6 s per step that finishes with the crate on its goal
  before the Hall of Fame.
- **Navigation and resume fixes**: cancelling GO TO LEVEL from the title
  without starting a game, RESTART from the title with zero counters,
  PLAY / RESUME keeping the saved position.
- **Display and exit fixes**: menus and solutions return on the right HGR
  page; two-byte end of the text tables (a string address ending in `$FF`
  accepted); QUIT TO DOS and Ctrl-RESET restore the zero page and reload
  HELLO, so LIST and RUN relaunches work.

### 1.2 — two voices and COLOR MODE

- **Two-voice title music**: melody over a walking bass, ten bars (24 s),
  `title_duet` loop of constant duration at `$6003`; the corridor animation
  steps between two beats.
- **COLOR MODE** (OPTIONS, off by default) gives crates on goals their filled
  green body, using a spare bit of the options byte.
- **Memory**: the DOS zero-page copy moved to page 2, the ranking and the RWTS
  zero-page copy to page 3, to free the resident (13 bytes were left).
- **Tests** listen to the music (both voices, tempo, a key cutting a note) and
  check the colour-mode tile and its option across a reboot.

### 1.3 — in preparation

- **A game left and found again**: the tutorial replayed from the menu gives
  the current level back; SOLUTION restores the position and the Undo/Redo
  history, even on a write-protected disk (solution read outside the
  history); renaming another profile does not change the active one; a
  profile created during a game starts with the tutorial.
- **Joystick**: after a rewind the stick waits to be recentred before moving
  the player; the game port (axes and buttons) is ignored without a joystick.
- **Display and counters**: the tiles under "SAVING" (III:054, IV:036) are
  redrawn after the save; moves and pushes stop at 65535; the write-protect
  test follows the slot DOS booted from.
- **Damaged files**: an unreadable, missing or impossibly long records file
  or ranking counts as empty and the game goes on; a failed write shows
  "IO ERR" (seven characters) without quitting; a short file no longer lets
  old bytes be read as records; `MICROHOF` is made consistent with its ten
  profiles at startup (active profile, initials, rows without a profile or
  duplicated, HOF2 included).
- **Wait screens**: SUCCESS, BRAVO and HELP ignore a key typed ahead or
  repeating; the keyboard must rest a quarter of a second.
- **Memory**: the start-only code (reading and checking `MICROHOF`,
  migrations) leaves the resident for the `BOOTCODE` segment, run at `$1000`
  before the first level pack (290 bytes freed).
- **Shared with `../dev`**: the HUD font is generated by `tools/hud_font.py`
  from the Beautiful Boot master in `dev/lib/font`; the Makefile uses
  `dev/cc65/apple2.mk`, the tests the `dev/tools/a2test.py` harness; the
  private copies of `print_str_ax`, `clear_hgr` and the scanline tables are
  gone.

## Verification

`make test` builds the disk and checks in a2run the exit to BASIC, the HGR
pages and monochrome silhouettes, the menu texts, resume, the tutorial, the
options, the profiles, the ranking, the returns to a game (tutorial,
SOLUTION, profiles, joystick, "SAVING", counters, typed-ahead keys), the
damaged files (impossible length, missing or short file, inconsistent
ranking) and the solutions of the 454 levels. The tests also cover corrupted
saves, migrations, write-protected disks and writes that change nothing.

Screenshots and joystick scenarios use the shared a2run/a2shot tools. The
disk timings in POM2 are described in the README; they measure the emulated
processor and are not measurements on a physical machine.
