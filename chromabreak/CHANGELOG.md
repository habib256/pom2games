# ChromaBreak — changelog

Finished work, moved out of [TODO.md](TODO.md) on 2026-11-16.

## Done

### After 1.1

- [x] The sixty sectors played end to end by a pilot that only moves and clicks the host
      mouse (`records-campaign` in `tests/playtest_probe.cpp`, `make test-long`, //e and
      //c, ~2.5 min each): enemies on, no state written. Checked on the way: every sector
      saved as reached, extra lives, the ×8 combo, the ENDING overlay's finale, then the
      record entry; frame lengths counted (see Later). About 3 h 20 of play, ~150 000
      points, one to four lives lost.

### 1.1 (2026-10-25)

- [x] Issue #3: the stick is read on every frame. It was read "until the next blank"
      even inside one, so on a PAL //e it went unread for up to 77 frames in a row; on
      the //c the mouse's VBL interrupt made reads short. Full read unless the
      presentation blank is next, interrupts masked on the //c; the playtest sweeps the
      stick in play: 240/240 fresh reads on all twelve profiles (was 78/240 PAL //e).

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
