# LOGO — planned work

Grounded in `src/`, the Makefile and `doc/`. Each item says where it comes
from.

## Next up

- **Screenshots.** `logo/` has none; `chromabreak/` and `arkabreakout/` keep
  theirs in `screenshots/` and link them from the README. Capture the split
  screen after `DEMO`, `FS` with a figure, `EDIT` and a `DEM2` bubble with
  a2shot `shot:` (`--iie`, 560x384 PNG) and add them to `README.md`.

## Later

- **V-blank sync on the //e.** The saved-background byte compositor removes
  the fully erased emote phase on II+ and IIe. A model-aware `$C019` sync could
  still reduce scanout tearing on the IIe; the II+ has no VBL flag.
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
