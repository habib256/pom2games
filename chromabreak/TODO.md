# ChromaBreak — TODO

Version 1.1 is the last published release (2026-10-25). Everything so far has been
validated in emulation only (POM2 with the real //e and //c ROMs, a2shot).

What is done is in [CHANGELOG.md](CHANGELOG.md).

## Next up

1. **Validate on real hardware.** Enhanced //e with an AppleMouse II card, and a //c with
   its built-in mouse (`dev/lib/mouse`, VBL mode 9 and the ProDOS interrupt handler).
   On the same machines:
   - joystick and Apple paddles (`J`): axis range and centring with real controllers,
     since `src/timing.s` counts the `$C070` timers with a 23-cycle loop, one count for
     two of the paddle's. Issue #3 (a real //e, probably PAL: the paddle jerky, then
     unplayable) is fixed in emulation (the stick read on every frame, see Done);
     waiting for the reporter's confirmation on their machine, the issue stays open;
   - the rendering of capsules, enemies and Beautiful Boot text on a real colour
     monitor (`src/finetext.s`: each HGR dot becomes two DHGR dots so strokes stay
     white), and the Chat Mauve mode on a real Féline or //c RGB adapter (bit 7 of every
     byte, lock set with IOUDIS on the //c);
   - the two-voice music on the real speaker (`src/duet.inc`: 31 kHz carrier, 13/20-cycle
     time division), on //e and //c.

## Later

- **Late frames while a capsule falls.** The campaign (`make test-long`) counts frames
  that take more than two refreshes: 0.9 % on the //e (worst 4 refreshes), 1.6 % on the
  //c (worst 6, since the flip waits for an even refresh), about two thirds of them with a
  capsule on screen (its fall and redraw are the first suspects). Profile them with
  `CHROMA_PROFILE` before deciding; the test fails above 3 %.

- **Mockingboard sound** (asked in issue #3: "with a little music for Mocking behind it
  will be fine"). The sound effects first (bounces, bricks, steel, capsules, laser,
  enemies, lost life), then the music if there is room: today both play on the
  speaker (`src/sound.s`, `src/duet.inc`). `dev/lib/apple2/mockingboard.asm` and its
  PT3 player exist; to measure first: the RAM left (`src/spare.s`), the frame budget
  with the AY register writes, the detection of the card on //e (slot 4, after the
  mouse) and on the //c (Mockingboard 4c), and keeping the speaker without a card.

- An original //e with a 65C02 but without the enhanced ROM passes the `CHROMA.SYSTEM`
  CPU test (`src/boot.s`) but has never been tried; decide whether to detect the ROM or
  document it as unsupported.
- The //c+ is not validated by the shared mouse driver (`dev/lib/mouse/README.md`).
- Frozen addresses (`src/spare.s`): 38 bytes of code, 60 of constant data and none of
  variables separate the C files from the assembly modules, and `src/sound.s` keeps 27.
  When a spare runs out or a `dev` library changes size, the module addresses move:
  record the new ones in the asserts, run `make test` on every profile and compare the
  worst frame (`CHROMA_PROFILE`).

## Ideas

Not committed; noted because the code already suggests them.

- Let the campaign also report the real maximum score of the sixty sectors: the README
  states 235 750 points from the tiles, enemies excluded; the pilot ends near 150 000
  (it does not play for the score).
- Move some of the records checks (`make test-long`) that need no mouse firmware (music events,
  Beautiful Boot glyphs, score conversions, 6502 message) to the a2shot path of
  `tests/test_game.py`, so `make test` covers them without a POM2 source tree.
