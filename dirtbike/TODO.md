# DIRTBIKE — next lots

Finished lots are in [CHANGELOG.md](CHANGELOG.md).

## Lot 2 — playability
- Tune the handling by hand in POM2: traction, lean, suspension
  softness, bounce (model first, then `make test`).
- Ghost: record each tick's inputs (replayable bit for bit, like the
  demo); race against the record's ghost.
- More tricks (landing on one wheel); combo multiplier.
- Flag visible from the right edge (x > 255: a 16-bit vertical line).
- Still some room: ~135 bytes in `$6000-$91FF`, about twenty per
  text page band (TXT5, TXT6).

## Lot 3 — content
- More detailed bike and rider (legs, handlebar, fork); crash
  animation.
- Scenery: start/finish flags, distant hills.

## Performance (threshold: 5 %)
Lot 1 bis: pixel scrolling. ~36,000 cycles per frame on the bumps
(28 fps) and 34,000 on the flat (30 fps), against 48,000 in lot 1 (byte
scrolling). Breakdown on the bumps: ground ~12,700, physics ~9,700,
bike ~8,600.
- Physics: constraint squares in 8×8 instead of 16×8; `height_at`
  called 7 times per tick.
- Bike: erase marks computed while drawing.
- Steady frame rate: VBL on the //e; on the II+, sync through the floating
  bus: `dev/lib/apple2/vapor.asm` exists since 2026-10-24 (SNAKE,
  marker on HGR line 191, tested on a2run and POM2 NTSC/PAL/IIe).
- Memory: ~135 bytes free in `$6000-$91FF`, ~30 in `$1000-$1FFF`,
  zero page full (1 byte).
