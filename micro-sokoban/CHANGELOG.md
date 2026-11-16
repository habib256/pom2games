# MICRO-SOKOBAN — changelog

Finished work, moved out of [TODO.md](TODO.md) on 2026-11-16.

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
