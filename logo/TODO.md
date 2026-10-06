# LOGO — planned work

Grounded in `src/`, the Makefile and `doc/`. Each item says where it comes
from.

## Next up

- **`make test` with the shared harness.** There is no `test` target (the
  other programs have one) and `ld65` is run without `-Ln`, so there is no
  `build/logo.lbl` for `a2test.labels()`. Proposal: add
  `-Ln $(BUILD)/logo.lbl` to the link line and a `tests/test_logo.py` that
  uses `../dev/tools/a2test.py` with `iie=True` (a2shot, the only emulator
  with 80 columns; a2run has none, see `dev/README.md`): boot `LOGO.dsk`,
  wait for the banner, check `text_screens()` for the `?` prompt in
  80 columns, type `REPEAT 4 [FD 40 RT 90]\r`, `peek:2000:8192` and assert
  that `hgr_visible()` holds set pixels around (128, 96), then `COLUMNS 40`,
  `BYE\r` and check the `]` DOS prompt. A second run without `iie` covers the
  ][+ 40-column path (`scr_boot` with `MACHID != $06`).
- **Screenshots.** `logo/` has none; `chromabreak/` and `arkabreakout/` keep
  theirs in `screenshots/` and link them from the README. Capture the split
  screen after `DEMO`, `FS` with a figure, `EDIT` and a `DEM2` bubble with
  a2shot `shot:` (`--iie`, 560x384 PNG) and add them to `README.md`.

## Later

- **V-blank sync on the //e.** `hgr_emote_vsync` (`src/logo.s`) is a stub
  because a ][+ has no VBL flag, so emote redraws are not synchronised (the
  upstream comment describes the BIRDFLY strobe this sync removed). On a //e
  `$C019` bit 7 is clear during VBL (`dev/lib/apple2c/apple2frame.h`);
  `scr_iie` already tells the two machines apart, so the sync can poll
  `$C019` on a //e and stay a stub on a ][+.
- **Stale comments in the HGR code.** The GEN2 HGR subsystem header in
  `src/logo.s` (before `trace_turtle_lines`) says `SETSHAPE` keeps the
  triangle and `sprite_mode` stays 0, while `cmd_setshape` a few hundred
  lines below loads the shapes and sets `sprite_mode = 1`. The header of
  `src/hgr_logom2.asm` says the backend uses columns 0..255 only, while
  `line_xy16` / `plot_set_x16` and the `SETXY` / move clamps cover 0..279.
- **Dead code.** `src/logo.s` carries two `.if 0` blocks: the pre-pagination
  `help_msg_unused_remove` text and the retired TURTL / BOAT directional
  sprite code. They are skipped by the assembler but weigh on the 186 KB
  source.
- **Apple II notes for the manual.** `doc/APPLE-1_LOGO-2.6-MANUAL.md` is the
  Apple-1 / TMS9918 manual: `BYE` returns to Wozmon, the screen is 256 x 192,
  `HELP` has 8 pages, `SETSHAPE` lists `TURTL` and `BOAT` (removed from
  `shape_table`, see the comment in `src/logo.s`) and the storage table says
  12 user variables where `MAX_VARS = 6`. The README carries the Apple II
  deltas for now; an addendum section (or a short Apple II chapter) in both
  manuals would be the right home.

## Ideas

- **Save and load procedures.** `HELP 9` says "Saving is in RAM only --
  power-cycle wipes it" and the manual lists files among what V2.6 does not
  have. DOS 3.3 is resident ($9600-$BFFF): a `SAVE` / `LOAD` of the procedure
  table through RWTS (as MICRO-SOKOBAN does for its saves) would make the
  editor worth keeping work in.
- **HOME at the HGR centre.** `cmd_home` places the turtle at (128, 96), the
  centre of the 256-wide TMS screen; the HGR screen is 280 wide, so the
  centre is (140, 96) and `DEM2` already uses `SETXY 140 46`. Moving HOME
  shifts every manual example and `DEMO` scene by 12 pixels, so it is a
  deliberate choice, not a fix.
- **`WAIT N` timing.** `HELP 7` says "pause N seconds", the manual's
  reference card says about 0.6 s per unit. Measure it on the Apple II
  (a2shot `until:` cycle counts) and make the two texts agree.
