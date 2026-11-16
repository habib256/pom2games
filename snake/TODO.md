# Snake — TODO

Open work on [`src/snake.c`](src/snake.c), in suggested order. Each step is
checked headlessly with `../dev/tools/a2shot` (scripted keys, PNG captures,
`peek` of game variables, timing in video frames); the `FIXED_SEED` build
option exists for that (see [`README.md`](README.md)). Reuse the pieces that
already exist in `../dev/lib` rather than writing new ones: the C mirrors of
`../dev/lib/apple2/sound.asm`, `joy.asm` and `dos.asm` are
[`apple2game.h`](../dev/lib/apple2c/apple2game.h) and
[`apple2dos.h`](../dev/lib/apple2c/apple2dos.h) in `../dev/lib/apple2c`.

What is done is in [CHANGELOG.md](CHANGELOG.md).

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
- **Memory**: the program ends at `$8BFD`, 2,306 bytes below the 256-byte C
  stack (`$9500-$95FF`, peak 37 bytes); `LOWBSS` ends at `$19B7`.
