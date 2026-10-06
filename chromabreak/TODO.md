# ChromaBreak — TODO

Version 1.1 is in preparation; 1.0 is the last published release. Everything so far has
been validated in emulation only (POM2 with the real //e and //c ROMs, a2shot).

## Next up

1. **Redo the three POM2 screenshots.** `screenshots/title.png` still shows "V1.0" while
   the title now prints `V1.1  BY ARNAUD VERHILLE` (`src/game.c`, `credit[]`), and
   `game.png` / `game-sector-2.png` show a five-digit score (00310) while the HUD has
   printed six digits since the score cap moved to 650 000 (`src/game.c`,
   `number(value,points_text,5); points_text[5]='0'`). Same method as before: POM2,
   `--preset iie --slot 4=mouseaw`, colour monitor rendering, captured during the demo
   mode (1231 × 908). The 1.0 release notes point at the `chromabreak-1.0` tag's copies,
   so they are not affected.
2. **Publish 1.1.** Write `docs/releases/chromabreak-1.1.md` on the model of
   `chromabreak-1.0.md` (the 1.1 fixes are listed in the README's "Releases" section),
   tag `chromabreak-1.1` with the disk attached, then update the "Version 1.1 in
   preparation" line at the top of `README.md`. Depends on item 1, since the notes embed
   the screenshots from the tag.
3. **Play a full campaign with an autopilot, without state injection.** The sixty
   transitions of `tests/test_game.py` poke `remaining=1` and clear `_bricks`, and
   `tests/playtest.cpp` sets `enemy_hold=1` and injects each collision case: nothing yet
   plays the game end to end. The demo pilot already exists (`src/game.c`, `demo_input`:
   follows the ball with a varying aim, relaunches, fires the laser); driving it from
   a2shot or the POM2 harness over all sixty sectors would exercise, in real play, the
   extra life every 5 000 points, the ×8 combo, the progress save on every "SECTOR nn
   CLEAR", the ENDING overlay load and the 650 000 cap path, with the real frame budget
   (enemies, capsules and shards all active).
4. **Validate on real hardware.** Enhanced //e with an AppleMouse II card, and a //c with
   its built-in mouse (`dev/lib/mouse`, VBL mode 9 and the ProDOS interrupt handler).
   On the same machines:
   - joystick and Apple paddles (`J`): axis range and centring with real controllers,
     since `src/timing.s` counts the `$C070` timers in the VBL wait with a 23-cycle
     loop, one count for two of the paddle's;
   - the rendering of capsules, enemies and Beautiful Boot text on a real colour
     monitor (`src/finetext.s`: each HGR dot becomes two DHGR dots so strokes stay
     white), and the Chat Mauve mode on a real Féline or //c RGB adapter (bit 7 of every
     byte, lock set with IOUDIS on the //c);
   - the two-voice music on the real speaker (`src/duet.inc`: 31 kHz carrier, 13/20-cycle
     time division), on //e and //c.

## Later

- An original //e with a 65C02 but without the enhanced ROM passes the `CHROMA.SYSTEM`
  CPU test (`src/boot.s`) but has never been tried; decide whether to detect the ROM or
  document it as unsupported.
- The //c+ is not validated by the shared mouse driver (`dev/lib/mouse/README.md`).
- Frozen addresses (`src/spare.s`): 58 bytes of code, 49 of constant data and 13 of
  variables separate the C files from the assembly modules, and `src/sound.s` keeps 27.
  When a spare runs out or a `dev` library changes size, the module addresses move:
  record the new ones in the asserts, run `test-mouse` on every profile and compare the
  worst frame (`CHROMA_PROFILE`).

## Ideas

Not committed; noted because the code already suggests them.

- Let the autopilot campaign (Next up, 3) also report the real maximum score of the
  sixty sectors: the README states 235 750 points from the tiles, enemies excluded.
- Move some of the `test-records` checks that need no mouse firmware (music events,
  Beautiful Boot glyphs, score conversions, 6502 message) to the a2shot path of
  `tests/test_game.py`, so `make test` covers them without a POM2 source tree.

## Done

### 1.1 (in preparation)

- [x] A paddle rising diagonally under a bottom-row tile, or widened by ENLARGE between a
      tile and a wall, stays under the tiles and inside the field (it used to leave the
      field and freeze the machine).
- [x] Score on six digits up to 650 000 (counted in tens of points), extra life every
      5 000 points; `HIGHSCORES` format 2, format 1 files converted on load.
- [x] `?` with the `ENDING` file missing keeps the title on screen; demo of 60 s in PAL as
      in NTSC.
- [x] Mouse height absolute (the firmware bounds the pointer to the paddle's travel): no
      travel lost after a lost life.
- [x] The joystick chosen with `J` stays the control after a game over (button or Space)
      and after a demo.
- [x] A paddle that rises past a capsule in one go collects it.
- [x] "V1.1" on the title.

### 1.0 — sixty sectors, enemies, music, help page

- [x] Sixty boards in ASCII art (`levels.txt`), packed two tiles per byte into an
      auxiliary-RAM bank; sector selector in the Escape menu, bounded by the saved
      progress (furthest sector, in `HIGHSCORES`).
- [x] Escape menu: resume, sector choice, sound toggle, back to title, quit to ProDOS.
- [x] Two Arkanoid-style enemies, a coil and a TIE fighter: gates, sliding around tiles,
      destroyed by ball, laser or paddle, exit through the bottom; colours distinct from
      the balls; none during multiball.
- [x] Capsules as 5 × 6 blocks with the black letters E S C D L P; laser cannons on the
      paddle; piercing ball as a shaded red 4 × 7 sphere (cached round masks); shots with
      a white head.
- [x] Vertical paddle up to mid-field, blocked by tiles along its whole path;
      ball/paddle contact checked every frame; spin from the paddle motion; Catch keeps
      the impact point.
- [x] Beautiful Boot text with the HGR technique (one HGR dot = two DHGR dots): white on a
      colour monitor, 40 cells; 37-cell HUD on lines 1–7 with the sector or bonus name
      right-aligned; logo in relief from the same glyphs.
- [x] Bevelled tiles with rounded corners and resistance slots, steel with a diagonal
      highlight, two-tone frame, no bottom line; a dark background pattern per decade
      above the paddle zone, from level 1.
- [x] "SECTOR nn CLEAR" with a two-voice ending per sector of each decade (ten tunes, the
      tenth a 3.3 s fanfare); title theme (I-vi-IV-V) cut short by a key; theme and tunes
      in auxiliary RAM.
- [x] Two-voice music engine on the one-bit speaker: 129-byte player in page 3, just
      intonation, interrupts served between notes (the //c mouse IRQs blurred the voices).
- [x] Finale after sector 60: `ENDING` overlay at `$4000`, VICTORY, fanfare, fireworks.
- [x] Help page (`?` on the title): capsules, tiles, points; code in the `ENDING` overlay,
      seven bytes in main memory.
- [x] Demo mode after 15 s idle (50/60 Hz detected), silent autopilot, no records.
- [x] Chat Mauve mode always on: 560-dot monochrome text, graphics with bit 7 set, RGB
      lock (IOUDIS on the //c).
- [x] Joystick and Apple paddles (`J`): absolute axes, buttons 0/1, read during the VBL
      wait at no frame cost.
- [x] Original //e (6502): clear message and return to ProDOS instead of a crash.
- [x] Difficulty selection on the title redraws only the underline; version and author on
      the title, "65C02" in the subtitle.
- [x] Memory: game table image at `$0800`, font doubling computed at `$0F00`, C stack
      brought down to 256 bytes (18 used, margin checked by the playtest); frozen module
      addresses with the spares and asserts of `spare.s`.
- [x] Cheaper HUD: BCD score, pre-aligned messages, static locals; piercing-ball scenario
      tested at full frame rate.
- [x] //c test bench with the built-in serial ports plugged (the ROM polls the ACIAs on
      every IRQ).
- [x] Frame rate 30/25 fps kept on the twelve profiles with the diagonal paddle and the
      enemy scenario.

### Screen layout, English text and menus

- [x] Compact top HUD, 180-line play area, paddle at y=184, tile rows from y=14 with
      consistent collisions.
- [x] Every screen, level name, difficulty and message in English.
- [x] Title: PLAY and the launch keys in one frame, the three difficulties on one line
      with the selection underlined, keyboard commands, records and exit grouped below.
- [x] Records table with aligned columns and the full mode name; game over, score and
      initials entry recentred; initials cursor adapted.
- [x] (Superseded) 4 × 5 white small font with five-column advance and `dhgr_puts_small`
      in the DHGR library; replaced by the Beautiful Boot text above.

### Rendering optimisation (validated at 30 Hz NTSC / 25 Hz PAL)

- [x] Sprite backgrounds saved per bank; identical drawing loop in main and auxiliary RAM;
      unrolled pixels, parameters and masks in zero page; backgrounds aligned on 32 bytes.
- [x] Masks of the white ball, shots, capsules and shards precomputed for the seven DHGR
      alignments; capsules with per-row masks recomputed only on column or type change.
- [x] Multiball loop in assembly, physics state in zero page, every sub-step kept; empty-zone
      cache per ball reset before each move; 328 640 positions compared with the
      collision model.
- [x] Shared desired HUD with a drawing history per page; faster white glyphs; score
      conversion bounded at 1 043 cycles and validated for 65 536 values, copied straight
      to the HUD.
- [x] Paddle: only the uncovered bands erased, cached seven phases for two width
      families, drawn straight from the cache, constant colours and rounded ends.
- [x] Balls, capsules, shots and shards driven in assembly; shards computed in assembly;
      flash restored on both pages.
- [x] Presentation on a fresh VBL after a long load; one board drawing, full presentation,
      then hidden main/aux copy.
- [x] Maximal scenario (ten objects at Expert speed) at a regular frame rate on //e and //c,
      NTSC and PAL; levels, font, silhouettes, bonuses, records and ProDOS errors
      revalidated afterwards.

### First release of the DHGR profile (twelve boards)

- [x] Enhanced //e 128 KB profile, distinct from the II+ 48 KB / DOS 3.3 `arkabreakout`;
      bootable ProDOS 2.4.3 disk and standalone SYS loader; shared ProDOS MLI, runtime
      and AppleMouse II libraries; `/RAM` check and pre-launch dialog removed.
- [x] DHGR 16 colours on two pages: coloured bevelled tiles, multicolour title, sober frame,
      cyan paddle with silver rounded ends and shadow, round white ball; normal and wide
      paddles and the ball checked in the seven DHGR phases.
- [x] Twelve boards of the game's own, eight angles, resistance, steel, six capsules
      (multiball, double laser, piercing ball with steel kept), combos up to ×8 reset on
      paddle contact or lost life, extra lives, limited coloured shards and a brief flash
      on resistant tiles.
- [x] Relax, Arcade and Expert: distinct lives, width, speed and progression; start 50 %
      faster, speed-up every eight tiles up to six sub-steps.
- [x] One-click/Space/Enter start with the ball launched; keyboard via `K`; mouse by
      default; native //c mouse with ROM IRQs active and banks masked briefly.
- [x] Distinct sounds sequenced without blocking the mouse IRQs; silence while paused.
- [x] //e VBL and //c VBL IRQ: regular NTSC/PAL frame rate and clean-up on exit; regular
      NTSC frame rate restored with the full AppleMouse firmware (MAME).
- [x] C rendering replaced by assembly and a differential score; only the paddle edges
      updated, no divisions on impact.
- [x] Five records on ProDOS with initials and difficulty, reloaded after a reboot;
      missing/corrupt file and write-protected disk handled.
- [x] Tests: ProDOS image, keyboard, transitions, firmware of both POM2 mice, start-up and
      mouse on the 16 and 32 KB //c ROMs; disk, images and manual updated; project,
      title and disk renamed ChromaBreak.
