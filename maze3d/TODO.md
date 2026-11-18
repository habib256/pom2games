# Maze 3D — roadmap

Validate every gameplay change with `../dev/tools/a2shot` (screenshots,
memory reads, cycle and frame counts) and `make test`
(`tests/check_generation.py` on 100 seeds, then seed entry, rendering,
joystick, configuration, profiles, ergonomics and a full playthrough). A scripted run must still reach the
shop, beat the dragon and win; exits without the relic, and the last one
before the dragon's death, must stay shut.

What is done is in [CHANGELOG.md](CHANGELOG.md).

## Ideas

- Show a message when the title, the texts or the state file cannot be
  read (disk removed or damaged): `fm_bload` returns the error and the
  game goes on with what is in memory. `fm_bload_retry` and a
  `FM_RETRY_HOOK` (ARKABREAKOUT's pattern) need a text routine that works
  while the drawn page is hidden.
