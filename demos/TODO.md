# DEMO — TODO

Short roadmap for the five-demo disk, written 2026-10-06 against the sources in
`src/` and the `../dev` libraries. Every item points at the code that motivates
it.

## Next up

- [ ] **Automated smoke test.** `demos/` is the only disk folder with no
  `make test`: `arkabreakout`, `chromabreak` and `micro-sokoban` each drive
  their disk in `a2run` from the top-level `make test`, while DEMO.dsk is only
  rebuilt. A test should boot the disk, press `1`..`5`, let each demo run a
  few frames, press ESC (or any key for PRESHIFT / FONT) and check that the
  menu text is back on the text page. The return-to-BASIC path (`RTS` on the
  caller's stack, zero page and `MAXFILES` restored) is the part most worth
  guarding.
- [ ] **Screenshots.** The other game folders ship a `screenshots/` folder
  linked from their README; `demos/` has none. Capture one frame per demo with
  `../dev/tools/a2shot` and link them from `README.md`.

## Ideas

- [ ] **Frame cadence through `apple2frame`.** PRESHIFT paces itself with a
  fixed `a2_wait(A2_WAIT_FRAME)` and BOUNCES / ANIMALS flip pages as soon as
  the hidden page is drawn, so a IIe shows the same occasional tear line as a
  II+. `../dev/lib/apple2c/apple2frame.h` (`a2_frame_init` / `a2_frame_wait`,
  linked via `APPLE2C_FRAME_SRCS`) waits for the real VBL on a IIe and falls
  back to the same bounded delay elsewhere. Check the size first: ANIMALS sits
  just under DOS with `MAXFILES 1`.
- [ ] **A DHGR demo (IIe / IIc).** `../dev/lib/hgrc/dhgr.h` already offers
  560x192 points, 140-colour fills, masked sprites and text, with a worked
  example in `../dev/examples/dhgr`. A sixth entry would need a model check in
  the menu, since the disk otherwise targets the II+.
- [ ] **Generate the ANIMALS banks into a header.** `animals_gen_x2.py` prints
  C to stdout for pasting over the bank block in `animals.c`, and the banner
  it emits (`__main__`) still says `gen_x2.py` / `GEN2Animals.c`. Writing an
  `animals_sprites.h` from the Makefile, as PRESHIFT does with
  `preshift_sprites.h`, would remove the manual step and fix the banner.
- [ ] **Rebuild `preshift_sprites.h` from the `.txt` locally.** The header
  came from `preshift_sprites.txt` through POM1's
  `tools/build_preshift_sprites.py`, which is not in this repository.
  `../dev/tools/assets/convert.py` already bakes seven-phase HGR sprites, but
  from PNG/PPM only; teaching it the `#` / `.` text format (or converting the
  two sprites to PNG) would make the ball and ship editable here.
