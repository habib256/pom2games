# Snake — TODO

Open work on [`src/snake.c`](src/snake.c), in suggested order. Each step is
checked headlessly with `../dev/tools/a2shot` (scripted keys, PNG captures,
`peek` of game variables, timing in video frames); the `FIXED_SEED` build
option exists for that (see [`README.md`](README.md)). Reuse the pieces that
already exist in `../dev/lib` rather than writing new ones: the C mirrors of
`../dev/lib/apple2/sound.asm`, `joy.asm` and `dos.asm` are
[`apple2game.h`](../dev/lib/apple2c/apple2game.h) and
[`apple2dos.h`](../dev/lib/apple2c/apple2dos.h) in `../dev/lib/apple2c`.

Measured state today (2026-10-24):

- **Keyboard**: read once per frame (vapor lock) or every 64 spins; two
  turns can be queued, a reversal is refused. **Joystick** once per tick when
  one answers on the game port; only a change of its direction steers.
- **Speed**: `tick_spins` sets the pace: 3,565 at the slow start (title `1`
  or any key), 2,565 and 1,565 for `2` and `3`, −200 per apple, −300 per
  level, down to 365. With the vapor lock a tick is `(spins + 101) / 146`
  frames (25 to 3; 5/6 of that on 50 Hz), exact; without a floating bus the
  spin throttle (a tick of 3,565 spins = 24.6 frames at 1 MHz, tones and
  stick taken off it).
- **Random**: 16-bit Galois LFSR, seed mixed from the title poll count and the
  start key; an automatic start replays the same sequence.
- **Memory**: the program ends at `$9146`, 953 bytes below the 256-byte C
  stack (`$9500-$95FF`, peak 37 bytes); `LOWBSS` ends at `$19B7`.

## Done

- [x] **Pace independent of the CPU clock** (2026-10-24): a vapor lock
  (`dev/lib/apple2/vapor.asm`, `apple2vapor.h`): the floating bus shows the
  beam reaching a marker at the start of HGR line 191, once a frame, on a II,
  II+ or //e. A frame measured at start tells 50 Hz from 60 (and none: //c,
  IIgs keep the spin). Ticks of whole frames; the keyboard is read once a
  frame. (The //e VBL alone, through `apple2frame.h`, would have left the II+
  CPU-timed.)
- [x] **Levels with obstacles** (2026-10-24): five levels of ten apples; walls
  as segments (`wall_segs`) marked in `occupied[][]`, so collisions and the
  apple / bonus placement avoid them for free; a `LEVEL n` card and jingle,
  a fresh 3-cell snake, each level 300 spins faster, `level + 1` cells per
  apple, YOU WIN after level 5. Room made by a 256-byte C stack: the shared
  `apple2_hgr_c.cfg` now ends `RAM` where `__STACKSIZE__` puts the stack.
- [x] **Sound** (2026-10-24): blip per apple, chirp for the bonus gem, chime
  when taken, thud at GAME OVER, arpeggio for YOU WIN (`a2_tone`); the tone
  time is taken off the next throttle.
- [x] **Joystick** (2026-10-24): `a2_read_stick()` once per tick, detected on
  the title and after each game (open paddle timers = nothing plugged in, as
  in MICRO-SOKOBAN); a direction change steers, a held or drifting stick does
  not fight the keyboard.
- [x] **Starting speed** (2026-10-24): `1` `2` `3` on the title (3,565 / 2,565
  / 1,565 spins), kept in `speed_spins` for every new game.
- [x] **High score** (2026-10-24): `HISCORE` (2 bytes) `BLOAD`ed before the
  title, shown there and as `NEW RECORD` on the GAME OVER card, `BSAVE`d unless
  the disk is write-protected. The DOS buffers live in `LOWBSS` (new switch
  `DOS_LOWBSS` of `dev/lib/apple2/dos.asm`): `$6000-$8DFF` was 86 bytes short.
- [x] **Headless regression test** (2026-10-24): `make test` (in the root
  `make test` too), `tests/test_snake.py` on the shipped disk in a2run, labels
  from `-g -Ln build/snake.lbl`.
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
