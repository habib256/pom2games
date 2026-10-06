# Snake — TODO

Open work on [`src/snake.c`](src/snake.c), in suggested order. Each step is
checked headlessly with `../dev/tools/a2shot` (scripted keys, PNG captures,
`peek` of game variables, timing in video frames); the `FIXED_SEED` build
option exists for that (see [`README.md`](README.md)). Reuse the pieces that
already exist in `../dev/lib` rather than writing new ones: the C mirrors of
`../dev/lib/apple2/sound.asm`, `joy.asm` and `dos.asm` are
[`apple2game.h`](../dev/lib/apple2c/apple2game.h) and
[`apple2dos.h`](../dev/lib/apple2c/apple2dos.h) in `../dev/lib/apple2c`.

Measured state today:

- **Keyboard**: read once per tick and every 64 spins of the throttle; two
  turns can be queued, a reversal is refused.
- **Speed**: active-wait `throttle()` of `tick_spins` iterations, 3,565 at the
  start (~0.33 s per cell, a tick every 18-20 frames), −200 per apple down to
  365 after 16 apples. Calibrated for 1 MHz: faster on an accelerator card.
- **Random**: 16-bit Galois LFSR, seed mixed from the title poll count and the
  start key; an automatic start replays the same sequence.
- **Missing**: sound, joystick, speed menu, high score, obstacles — none of
  these exist in `snake.c`.
- The Makefile emits `build/snake.map` but no ld65 label file (`-Ln`), which
  the test harness `../dev/tools/a2test.py` needs for `peek` by name.

## Next up

- [ ] **Sound** on apple, bonus pickup, bonus spawn, death and win, with
  `a2_tone(flips, period)` (`apple2game.h`). Link `APPLE2C_GAME_SRCS`
  (`apple2game_asm.s`, assembled with `APPLE2C_AFLAGS`), for instance by
  adding it to `HGRC_EXTRA_SRCS` so the archive carries it. The CPU is busy
  during a tone, so keep the blips short (`a2_tone(0x30, 0x28)` lasts ~10 ms)
  or shorten the following `throttle()` by the same amount. Cost: 1 byte of BSS.
- [ ] **Joystick** steering with `a2_read_stick()` (`apple2game.h`, same object
  as above). It returns `A2_JOY_UP/DOWN/LEFT/RIGHT` = 1..4, the very values of
  `DIR_UP..DIR_RIGHT`, so the result feeds `set_dir()` directly. One read costs
  ~6 ms: call it once per tick (not inside the 64-spin keyboard poll) and
  recalibrate `tick_spins`, or accept the slower tick. Reuse MICRO-SOKOBAN's
  way of ignoring the game port when no stick is plugged in.
- [ ] **Starting speed** chosen on the title screen (for example `1` `2` `3`
  for three `tick_spins` presets; any other key keeps the default). `new_game()`
  currently resets `tick_spins` to 3,565, so the choice must live in its own
  variable that `new_game()` reads.

## Later

- [ ] **High score** kept across games and saved on the disk. Use
  `apple2dos.h`: `a2_dos_cmd("BLOAD HISCORE,A$...")` at start, a `BSAVE`
  built with `a2_dos_new/add/hex/run` after a record, guarded by
  `a2_disk_protected()`. Link `APPLE2C_DOS_SRCS` (`apple2dos_asm.s`, 256 + 41
  bytes of BSS). DOS stops the program on a missing file, so the Makefile must
  put an initial `HISCORE` on the disk (`$(DOS33) --bin HISCORE=...`). The two
  HUD rows are full (label at x 8-170, score field at x 184-272), so show the
  record on the title screen or the GAME OVER card rather than in the HUD.
  `dos33.py` reads files back from an image, which lets a test check the save.
- [ ] **Headless regression test** (`make test-snake`, wired into the root
  `make test` like `test-arkabreakout`): a `FIXED_SEED` build, scripted keys
  through `../dev/tools/a2test.py` on a2run / a2shot, `peek` of `score`,
  `slen` and `alive` through ld65 labels. Needs `-Ln build/snake.lbl` on the
  link line. Cover: a turn queue of two, the wrap at both edges, a wall death,
  the bonus cadence (every 4th apple, 36 ticks), pause and `Q` to DOS.
- [ ] **Pace independent of the CPU clock**, if accelerated machines matter:
  [`apple2frame.h`](../dev/lib/apple2c/apple2frame.h) (`APPLE2C_FRAME_SRCS`)
  gives `a2_frame_init()` / `a2_frame_wait()` — VBL on a //e, a bounded ROM
  `WAIT` fallback on a II+. The keyboard poll inside `throttle()` would then
  move to a per-frame loop.

## Ideas

- **Levels with obstacles**: every N apples, draw interior walls. The
  `occupied[][]` grid already drives `body_hits()`, `place_food()` and
  `place_bonus()`, so marking wall cells in it gives collisions and safe
  spawning for free; `redraw()` must draw them and the win condition
  (`slen == MAXLEN`) must subtract the wall cells.

## Done

- [x] **Direction queue**: the keyboard is also read during `throttle()`;
  up to two turns wait and are applied one per tick, reversals refused.
- [x] **Random seed** mixed from the title poll count and the start key;
  `SNAKE_FIXED_SEED` (`make FIXED_SEED=...`) pins it for a2shot playtests.
- [x] **Maximum length** `MAXLEN` covers the 33 × 20 playable cells; the last
  apple triggers YOU WIN.
- [x] **Pause** (`P` or `ESC`) and **quit to DOS** from the pause (`a2_dos()`,
  zero page restored by `crt0_apple2.s`).
- [x] **GAME OVER timing**: ~4 s hold then a ~5 s key window, instead of the
  upstream ~13 s deaf / ~30 s total.
- [x] **C runtime moved to `../dev/lib/hgrc`** and linked from an `ar65`
  archive shared with the C demos: 10,218 → 8,573 bytes, zero page 99 → 80 bytes.
