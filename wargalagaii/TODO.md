# WARGALAGA II — work plan

Target: Apple //e enhanced and //c, 128 KB, 65C02, ProDOS, double-buffered
HGR everywhere, 30 fps NTSC (2 refreshes a frame; 25 in PAL, game 17 %
slower, accepted), with or without a Mockingboard, keyboard and joystick (no
mouse), 140 KB disk.
Reasons and memory map: [README](README.md). Rules taken from Warblade:
[docs/warblade-reference.md](docs/warblade-reference.md).

Project model: [CHROMABREAK](../chromabreak/README.md) for the ProDOS boot,
`/RAM`, the //e and //c timing, the joystick read during the wait;
[DIRTBIKE](../dirtbike/README.md) for the bit-exact Python oracle model, the
"rewrite only what changes" rendering and the lots.
Performance threshold: a measured 5 % gain is worth doing.

Legend: `[lib]` = to add or change in `dev/lib` (shared, with its test in
`dev/tests` and its line in the lib's README); `[game]` = specific to the
game, in `wargalagaii/src` or `tools`.

What is done (lots 0 to 11, bug hunts, requests from 2026-10-23 to
2026-10-30): see [CHANGELOG.md](CHANGELOG.md).

## Content

### Lot 3 — remaining

- [ ] Decimal conversion outside BCD: not useful yet (shop, records).

### Toward Warblade

The Warblade features of the original plan (lots 6 to 8). Each task says
what the game has today and what is still missing.

- [ ] `[game]` `tools/levels.py` → 25 packs of 4 levels (waves, paths,
      fire rate, the pack's alien drawing), 4th level bonus / kamikaze in
      turn, bosses on levels 25/50/75/100, loop mirrored and faster after
      100. **Exists**: all of it, but as formulas in `tools/model.py`
      (`level_kind`, `level_form`, `level_params`, `alien_combo`; 9
      formation shapes, two species a pack) and the `lv_*` tables of
      `tools/bonus.py`; **missing**: `tools/levels.py` itself (a table a
      level instead of formulas) and paths of its own for each pack: the 4
      entry curves and 4 dives of `tools/paths.py` serve every pack.
- [ ] Aux memory reserve: `WG2.AUX` loaded once at boot (drawings × tints,
      paths, music); copy of the current pack into main memory by
      `AUXMOVE` (`$C311`) during the "teleport". LZ4FH compression if
      needed (`dev/lib/apple2/lz4fh.asm`, tool `$(FHPACK)` of
      `dev/cc65/fhpack.mk`). **Exists**: `WG2.AUX` loaded once (packs,
      PT3, overlay, Meteor Storm, demo, walls, boss, rocks, texts, `LOW2`
      paths), the pack copied into `cur_alien` / `cur_big` by `pack_check`
      in 64-byte `aux_fetch` chunks between two levels; **missing**: one
      song only (no music of its own per pack or screen), paths copied once
      at boot, not per pack; LZ4FH serves only the title picture (not
      needed so far: aux `$0200-$1FDF` and `$BB00-$BFFF` are still free).
- [ ] Boss: composite sprite (32×24 or larger), weak points, rosette fire
      (angle table, like the TMS Galaga super boss). **Exists**: one boss
      drawing, 24 × 28 cells two-tone, moving a cell every 8 steps, a
      single core (cells 9-14) that takes hits while the claws swallow
      shots, a rosette of 5 bombs (dx −2..2) and an aimed bomb; **missing**:
      several weak points destroyed one by one, a rosette from an angle
      table, a different boss (or tint) for levels 25, 50, 75 and 100.
- [ ] Hurry-up: a ship that passes if the level drags. **Exists**: after
      1,800 steps (60 s) on a normal or big level, a saucer crosses the
      top, out of reach, and drops a bomb drifting toward the ship every
      12 steps; **missing**: Warblade's homing missiles (left aside in
      `docs/warblade-reference.md`); none on bonus, kamikaze or boss
      levels.
- **Accepted if**: an autopilot (`tools/autopilot.py`, model) finishes
  levels 1, 25 and 100; bench of the worst level within the budget
  (`make test-long` checks the first part since lot 6; the budget: see the
  Lot 6 deviations).
- [ ] Shop after each pack if ≥ 50 credits: ~12 items (speed, extra shot,
      double/triple, autofire, armour, life, time, rank mark, 2-3 weapons),
      prices after the reference; fixed **HGR** screen, slow routines
      allowed (text, digits, frames); arrows + RETURN, or joystick up/down
      + button 0. Overlay loaded at `$4000` like CHROMABREAK's `ENDING`
      (outside the game). **Exists**: all of it with 10 items (lot 7);
      **missing**: Warblade's new weapons (Quad, Super Triple, Plasma, Fire
      Balls, Laser Beam, War. I. Plasma), which need other shots, and Game
      Secret.
- [ ] Ranks: 6 colour marks; all 6 → next rank on leaving the shop; dark
      mark: lower rank. **Exists**: the marks dropped by big aliens, the
      dark mark, rank 0-99 changed on leaving the shop, RANK MARKER, rank
      and marks in the HUD, rank × 10,000 on the GAME BONUSES screen;
      **missing**: the rank kept in `HIGHSCORES`, Warblade's reward for the
      marks in rainbow order (Super Autofire).
- [ ] Meteor Storm: asteroids coming down, fire = speed up (slowing down is
      faster than speeding up), speed and distance gauges, crash = back to
      the game without losing a life, prize by speed. Same sprites and same
      rate as the game. **Exists**: all of it, rebuilt after Warblade's
      wiki in lot 11 (the icon ends the level, gauge beside the ship,
      vertical distance bar, rocks of three sizes, prize by percentage);
      **missing**: what the Lot 11 deviations list (gems and Gem Drop,
      Random bonus, rock variety, full-size prizes).
- [ ] Memory Station: grid of pairs, time = T gauge, larger grid after
      each success (+25,000), pirate flag = end. Fixed HGR screen, cursor
      by keyboard or joystick. **Exists**: all of it (lot 8): grids 3×3,
      5×3, 5×5 and 7×5, pairs of bonuses, the skull ends it; **missing**:
      rank marks among the pairs (Warblade gives them), grids larger than
      7×5 (later rounds repeat it); time counted per grid (see the Lot 8
      deviations).

### Waves

- [ ] Stretches without enemies: since 2026-10-30 an empty field brings the
      next wave within `ENTRY_FIRST` steps. Remaining: the teleport
      (`TELEPORT_T`, 60 steps, 2 s) and the wait for falling bonuses
      (objects still falling hold the end of the level).

## Deviations to validate

### Lot 6

- **Deviations to validate**:
  - **Music at 25 Hz** (`MUS_HZ` of `tools/sound.py`, the song's `SPEED`
    follows) instead of PT3's usual 50 Hz: half the CPU. Late frames,
    normal player, 600 frames (measured at lot 6): level 97 — without a
    card 96, PT3 50 Hz 206, 25 Hz 140; level 100 — 56 / 182 / 113; level 1
    (entry waves) — 78 / 114 / 104. A commercial PT3 module (50 Hz) would
    play at half tempo: set `MUS_HZ = 50` back to play one.
  - Worst level **over budget**: "cheater" bench (10 triple shots,
    autofire) up to 13 % late frames without a card; with the card up to
    30 % on a single start, ~23 % summed over the starts of
    `tests/test_long.py` (2026-10-30); peaks at 36,000 render cycles
    (divers in EOR). The game speed stays exact (logic by pairs of
    refreshes), only smoothness drops.
    `test-long` thresholds: 15 % / 28 % (the scene is chaotic, so each
    scene is played from several starts and summed).
  - 16 stars instead of 24, 7 divers at most, sway every 3 steps.

### Lot 7

- **Deviations to validate**:
  - 10 items instead of ~12: no new weapons (the game has three: single,
    double, triple; Quad, Plasma, lasers… would need other shots); EXTRA
    TIME, RANK MARKER, LESS SPEED kept.
  - AUTO FIRE buys autofire for the T gauge's maximum duration (90 s), not
    for good.

### Lot 8

- **Deviations to validate**:
  - The skull ends the station as soon as it is turned (Warblade's flag);
    ESC also leaves.
  - The station's time is counted **per grid** (not for the whole
    station).

### Lot 9

- **Deviations to validate**:
  - Title in HGR (no DHGR, decision 1) and menu text in English, like the
    game.
  - The demo has no hand-scripted inputs: it is the autopilot (always
    firing; levels 1, 3, 4, 8 and 25, no GAME OVER).
  - ESC in the game goes back to the title (no pause); a record can be
    made there.
  - `HIGHSCORES` is read once, rewritten after a record, or when leaving
    the title if the joystick changed (not on each press of J).

### Lot 10

- Deviations: the boss moves slowly (a cell every 8 steps: each move costs
  ~5,600 cycles); the demo lasts 2,550 steps.

### Lot 11

- Deviations to validate: no gems and no Gem Drop; 250 bill → 200 coin;
  point prizes divided (6-digit score); EXTRA covers 0-94 % (the wiki says
  nothing about 76-94); percentage shown at the top, not under the gauge;
  no Random bonus; 3 sizes × 2 frames of rocks, orange, instead of 49
  drawings.

### Modes and white shots

- Deviations to validate: a single record table for all modes (Warblade
  has one per mode); the mode is not shown in the game; disks already
  played start again with EASY only.

## Performance and lib

### Lot 2 — remaining

- **Remaining / to watch**:
  - Entry phase: up to ~16 aliens fly; in NTSC 3 late frames (out of
    ~1,600) when a wave arrives while the previous one settles, the game
    speed staying exact (foreseen by the README). PAL: none.
  - The worst case with 10 shots (28,000 + logic 3,400) exceeds the 28,060
    that keep 6,000 cycles for the music under IRQ (lot 4). Leads: skip
    the empty byte columns according to the shift, cheaper stars (~2,300
    cycles, ~1,500 planned), alien data read at a fixed address (the pack
    is copied into `cur_alien` since lot 6) with an `LDA abs,X`.
  - Promote the routines to `[lib]` `dev/lib/hgr/` once stable.

## Memory

- Remaining reserves: ZP `$B9-$CF`, `$F0-$FF`; `TXT6` (~77) and `TXT7`
  (120); aux `$0200-$1FDF`, `$BB00-$BFFF`, aux language card, ends of the
  `WG2.AUX` zones (see README, Memory).

## To check on hardware

Remaining:

- [ ] Validation on real machines (//e enhanced + Mockingboard, //c),
      according to `dev/lib/HARDWARE.md`.

- [ ] //c + Mockingboard 4c: detection wakes the card at `$C403` and may
      hide the slot 4 mouse ROM. Is the VBL interrupt of the mouse firmware
      (our //c clock) still usable? Otherwise: clock from the VIA's T1
      timer (regular, not locked to the VBL: possible tearing at the page
      flip).

### Bug hunt (2026-10-23) — open points

  - **Open, low risk**: on //c, `LDA $C070` (joystick) also acknowledges
    the VBL; an interrupt arriving during that access may be lost (one
    late frame) or, in theory, leave ProDOS facing an unclaimed IRQ. Not
    observed in 3,200 refreshes; to check on hardware (as for CHROMABREAK).
  - **Not tested**: //c with a Mockingboard 4c (two IRQ handlers, mouse +
    VIA): a2shot has no //c, the probe has no card.

## Known repository pitfalls

- Keyboard: read `$C000` then acknowledge with `BIT $C010`; on //e reading
  `$C010` also returns "key held" in bit 7.
- `ldx #191 … dex / bpl` never loops (191 > 127): `cpx #$FF / bne`.
- Lib options tested **by value** (`RWTS_SEI`, `DOS_SEI`,
  `MUL_INIT_BOOT`…): `=0` is the same as absent, set `=1` to enable; a few
  remain `.ifdef` (read the module's header).
- Assembler libs guarded by `.ifref`: include them **at the end** of the
  source, after their callers.
- Cycle-counted loops (speaker, wait): `.assert` that they do not cross a
  page (DIRTBIKE: `tone` straddling a page = notes 20 % too long). Fixed
  addresses of fast modules (CHROMABREAK: `spare.s`): a few bytes of shift
  have already cost a frame.
- Starting values: the CRT zeroes the BSS, **not `LOWBSS`**, which the
  application initialises itself (`dev/lib/ABI.md`); a variable that must
  start from a value goes in `DATA` (DIRTBIKE).
- Aux memory: with `RAMRD` on aux, the code itself is read from aux; a loop
  that reads aux data must exist at both addresses (CHROMABREAK copies its
  sprite loop into both banks). Prefer `AUXMOVE` between two levels.
- IRQ: the handler touches neither the cc65 ZP nor its stack, nor the
  graphics switches; the //c mouse firmware sends 60 IRQ/s (VBL clock);
  the Mockingboard 4c is detected before installing it.
- `PREAD` ($FB1E) counts in an 11-cycle loop: an IRQ in the middle
  (Mockingboard music tick ~1,570 cycles) adds ~140 to the reading. Mask it
  (`php / sei … plp`): the shop drifted downward (2026-10-31, `sh_pread`,
  test "stick centred with the music").
- `$C05E/$C05F` set the mouse on //c if IOUDIS is not set (CHROMABREAK):
  do not touch AN3 in HGR.
- POM2 rereads memory at the end of the frame ("beam racing"): a page flip
  too close shows a page being drawn
  (`dev/tools/a2shot/LETTRE_POM2_AFFICHAGE_MANETTE.md`).

## Decisions (questions closed on 2026-10-22)

1. HGR everywhere, fixed screens included; DHGR later.
2. PAL: the game runs 17 % slower, like CHROMABREAK; no per-second speeds.
3. Armour protects from enemy shots only; a collision kills.
4. 140 KB disk.
5. Without a Mockingboard: sound effects in the game, music outside the
   game only.
6. Few drawings (6 small, 2 big, 1 boss) × 4 precomputed HGR tints; other
   drawings later.
7. No mouse as an input; on //c, its firmware serves only as the VBL clock.
