# Maze 3D — roadmap

Validate every gameplay change with `../dev/tools/a2shot` (screenshots,
memory reads, cycle and frame counts) and `make test`
(`tests/check_generation.py` on 100 seeds, then seed entry, rendering,
joystick, configuration, profiles, ergonomics and a full playthrough). A scripted run must still reach the
shop, beat the dragon and win; exits without the relic, and the last one
before the dragon's death, must stay shut.

What is done is in [CHANGELOG.md](CHANGELOG.md).

## Ideas

- Swap the private 8 px font (TMS bit order, 512 bytes) for the shared
  Beautiful Boot font in `../dev/lib/font` and define `HGR_TEXT8_HGR_ORDER`:
  drops `ht_rev` and the 256-byte `rev7_tab` from the text path. A graphic
  choice: the current font is part of the game's look.
