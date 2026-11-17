# WARGALAGA II — history

The finished lots and the bug hunts, moved out of [TODO.md](TODO.md) on 2026-11-16.

## Lot 0 — preparation (done, 2026-10-22)

- [x] Folder, README (machine, memory, timing, sound, controls), TODO.
- [x] Warblade reference checked, with sources (`docs/warblade-reference.md`).
- [x] Search for an existing "WarGalaga": none; POM1 has a TMS Galaga
      (TMS9918, hardware sprites), useful only for the dives.
- [x] Skeleton `Makefile` (includes `apple2.mk`, builds nothing).

## Lot 1 — V0.1: boot, clock, ship, shot (done, 2026-10-23)

Game in 65C02 assembler (`src/game.s`, `src/timing.s`) behind cc65's ProDOS
crt0; `src/game.cfg` = `apple2_dhgr_prodos_c.cfg` + segment
`SYSBSS` at `$0200-$03CF` (tables `hgr_lo/hi`).

- [x] `src/boot.s` / `boot.cfg`: `WG2.SYSTEM`, refuses an NMOS 6502 (test
      `INC A`), loads `WG2.SYS`; `src/startup.s` relocates it to `$6000`.
- [x] Link `crt0_prodos.s` + `none.lib`, libs `mli.s`, `video.s`, `mouse.s`,
      `apple2frame.s`.
- [x] `/RAM` claimed (`PD_VIDEO_DISCARD_RAM`) then reformatted on exit;
      128 KB checked through MACHID (`$BF98`), otherwise a message.
- [x] Double-buffered HGR: `hgr_scanline_ram.asm` (`$0200`), pages through
      patched operands (`hgr_pages.inc/.asm`), flip `$C054/$C055`.
- [x] Clock `src/timing.s` (derived from `chromabreak/src/timing.s`): //e =
      edges of `$C019` counted by `timing_scan` (called between the drawing
      phases), //c = VBL interrupt of the mouse firmware (mode 9, ProDOS
      `ALLOC_INTERRUPT`), otherwise `a2_frame_wait` delays. Bounded wait,
      fallback. Joystick (paddle 0) read during the wait, up to the deadline.
- [x] Fixed step: one logic step per pair of refreshes counted between
      two flips (`timing_refreshes`), remainder carried, at most 2 steps a frame.
- [x] 24 stars at 3 speeds, 1 dot each; erased only if their byte has not
      changed, set only on a black byte.
- [x] Ship 7 cells × 10 rows, 7 pre-shifts (`tools/sprites.py`), redrawn on
      a page only if it moved since that page.
- [x] Keyboard: ← → / J L (the direction holds while a key is down,
      `$C010` bit 7, so SPACE does not stop it), SPACE and Open
      Apple / button 0 fire (edge). **TAB** toggles keyboard / joystick
      until the lot 9 menu.
- [x] Single shot, 5 at most (starting B gauge), erase lists per page.
- [x] `tools/model.py` (logic oracle, started in this lot) and
      `tests/test_game.py` (`make test`, ~3 s).
- **Acceptance** (`make test`): volume; 1,000 frames in 2,000 refreshes,
  none late, NTSC and PAL; 300 steps identical to the model; arrows,
  SPACE, Open Apple, joystick; ESC and Ctrl-RESET → text, `/RAM` rebuilt,
  ProDOS launcher; II+ (NMOS) → message. Rendering measured: ~8,400 cycles
  with a moving ship, 5 shots, 24 stars (budget 28,060).
- [x] **//c in the test suite** (2026-10-24): the POM2 front end got the //c
      (`Machine::AppleIIc`, delivery 0849ee51); `tests/iic_probe.cpp` is
      ported to it (`dev/tools/a2shot/probe.hpp`) and its 13 variants run
      in `make test` (~18 s), CI included. The real machine remains.
- [x] `[lib]` `dev/lib/apple2c/apple2vbl.s` (2026-10-24): the clock shared
      by `src/timing.s` and `chromabreak/src/timing.s` (mode choice, //c
      mouse VBL interrupt, //e edge counting, `A2_VBL_SCAN_SEI=1` here);
      the page flip goes through a hook, the presentation and the joystick
      stay in each game. With it: `dev/lib/prodos/sysboot.s` (WG2.SYSTEM,
      byte for byte) and `dev/lib/prodos/file.asm` (HIGHSCORES, in the
      overlay; WG2.AUX keeps its resident loader: more room in main
      memory). Cost: +46 bytes of main memory (generic clock), hence
      RODATA/DATA/BSS shifted by 46 bytes; `make test-iic`: //c identical
      (109 late frames out of ~1,600 at the entry), //e 91 instead of 89
      (joystick 97 instead of 92), PAL 0. A pure table alignment effect:
      46 more bytes of padding (shift 92) give back 89/92. No padding kept
      (≈120 bytes free).

## Lot 2 — V0.2: sprites, formation, dives (done, 2026-10-23)

Code: `src/logic.s` (logic), `src/render.s` (drawing), `src/game.s`
(loop, inputs, tables). Row tables aligned at `$1000-$12FF`
(segment `ROWS`): `hgr_hi+R,X` for sprite row R, and `select_page`
rewrites only the high byte of each operand (`HI_LDA`); the lib's
`hgr_pages` is no longer used (it rewrites both bytes and does not handle
`+R`).

- [x] `tools/sprites.py`: drawings in 2-dot cells, `X` = a dot of the
      tint (violet, green, blue, orange), 7 pre-shifts, entry
      `2*décalage+image` (2 × shift + frame). **6 small aliens in 7×8
      cells** (8 rows and not 10: 20 % less per alien), 2 big ones in
      10×16, 2 frames each; `--png F` gives the sheet of all the drawings
      and tints. Written
      apart from `dev/tools/assets/pack_hgr_sprites.py` (cells and tints
      specific to the game); to merge if a second game needs it.
      **Boss not drawn yet** (lot 6). The game links only one drawing and
      one tint (`GAME_SMALL`): the aux memory reserve is in lot 6.
- [x] Drawing (`src/render.s`): routines unrolled by macro
      (`SPRITE_ROWS`). Measurements (`make test`): seated alien **STA 470**
      cycles, **EOR 593**, erase **322** (targets 650 / 400 met).
      Change of method during the lot: erasing what flies with zeros
      damaged the formation (redrawn on both pages: 47,000 cycles a
      frame); **what flies (divers, entering aliens, shots) is drawn
      and erased in EOR**, in exactly the reverse order of the drawing,
      which leaves the screen as it was without redrawing anything.
      Formation set in STA, ship in STA. Shots: one byte, the same pattern
      on 6 rows.
- [x] Formation 5 × 8, breathing by one cell; **one row every
      2 steps** (one a step = 16 aliens redrawn a frame, each change being
      drawn on both pages). A row unchanged since the page's last drawing
      is skipped in a few tests.
- [x] `tools/paths.py`: turtle (heading, speed, turn) sampled at each
      step, quantised into signed 4-bit Δx (cells) / Δy (rows) bytes,
      `$80` = end; 1 entry (loop) mirrored on the right, 4 dives
      (U-turn then: drift, zigzag, diagonal, loop), mirrored on the right
      half of the formation.
- [x] Waves: 5 waves of 4 pairs (one row each, from the centre toward
      the edges), then back to the place; a dive every 20 steps if
      fewer than 6 aliens fly; exit through the bottom → back from the top.
      Randomness: `dev/lib/math/random.asm`.
- [x] `tools/model.py`: bit-exact oracle; `tests/test_game.py`
      compares **2,000 steps** at each step (full state + randomness).
- **Acceptance** (`make test`, ~8 s): formation + divers bench +
  **10 shots** fired nonstop: **0 late frames out of 300**; seated
  formation: 0 late out of 1,000 frames NTSC and PAL; oracle green. Profile
  (`tools/profile.py`): average render 17,300 / worst 23,200 cycles without
  shots, 22,000 / 28,000 with 10 shots; logic ~3,000-3,600.

## Lot 3 — collisions, enemy shots, lives, score, HUD (done, 2026-10-23)

- [x] Collisions in logical coordinates, without reading the screen. Shot
      against seated aliens: `shot_frow` (the shot's row → the only
      formation row it can hit) then `col_of` (cell → column), one test;
      then the list of flying aliens (`fly_list`, built during the alien
      loop, in the model's order). Bomb and alien against the ship: reduced
      box (cells 1-5, rows 2-9 of the ship). First hit only, order set by
      the model.
- [x] Enemy bombs: 6 at most, one attempt every 12 steps by a random alien
      (seated or diving, visible, above row 150), 4 rows a step, blue,
      drawn in EOR like the shots.
- [x] Aliens hit: state `ST_BOOM` 8 steps (explosion in 2 frames, drawn
      like a flying alien), then dead; 50 points seated, 100 flying.
- [x] Ship: 3 lives; hit → explosion (24 visible steps), respawn
      in the centre at step 45, 60 steps of invulnerability (the ship
      blinks). Armour (0 at the start, max 2 in lot 5/7): absorbs a bomb
      and gives 60 steps of invulnerability; a collision with an alien
      still kills. No lives left: `GAME OVER` in the middle of the field;
      after 2 s, SPACE or Open Apple start a new game.
- [x] 6-digit BCD score (`SED`), 4-digit BCD credits (0 until
      lot 5).
- [x] HUD (rows 0-7): score, lives, armour, S and B gauges as segment
      bars, T, credits. **Deviation from the plan**: no `hgr_hud8` and no
      `hgr_text8`; a character = an 8-row byte column drawn by the same
      macro as the sprites (`glyph_sta`, ~230 cycles), `bbfont` font
      $20-$5F followed by 4 game glyphs. The HUD is recomputed only if its
      state (8 bytes) changed since the page's last drawing, and only the
      characters that differ are rewritten.
- **Acceptance** (`make test`, ~10 s): 2,000-step oracle with collisions,
  3 lives lost at steps 455, 923 and 1602 identical to the model then
  `GAME OVER`; second oracle with armour (1,500 steps); without a player:
  `GAME OVER`, 0 lives in the HUD of both pages, SPACE restarts; bench
  (10 shots that pass through thanks to the `nohit` test flag, bombs):
  0 late frames out of 300.
- **To watch**: entry phase, ~37 late frames out of ~1,600 in
  NTSC (1 in PAL; figure corrected by the bug hunt, ~45 on //c), exact
  speed; logic ~3,200-4,600 cycles. Gain of the
  lot: a seated alien that changes its starting byte now erases
  only the column it leaves.

## Bug hunt (2026-10-23, after lot 3)

- [x] **Screen invariant** (`tests/test_screen.py`, in `make test`): the
      page the 6502 has just drawn is compared byte for byte with a full
      drawing of the state in Python (HUD, formation, GAME OVER,
      ship, flights in EOR, shots, bombs, stars). 5 seeds × 210 frames
      (game, bombs, explosions, game over, restart): identical. A
      mutation (bombs removed from the reference) is detected.
- [x] **Stray writes** (a2shot `storewatch` on a game with an end and a
      restart): nothing in zero page outside the game, `$0200-$0FFF`,
      `$1300-$1FFF`, RODATA, `$8F24-$BEFF`, ProDOS page `$BF00`; in the
      code, only the 72 operands of `select_page`.
- [x] **Logic fuzz**: 3 seeds × 6,000 steps (armour 0, 1, 2) identical
      to the model.
- [x] **//c finally run** (`make test-iic`, optional: `tests/iic_probe.cpp`
      on the POM2 sources, like CHROMABREAK's `test-mouse`): //c ROMs
      16 KB and 32 KB, NTSC and PAL, with and without a joystick (`$C070`
      also acknowledges the //c VBL): clock by IRQ, exact speed,
      seated formation without delay, ESC returns control and the IRQ.
      During the entry: ~43 late frames on //c against ~21 on //e (cost
      of the interrupts).
- [x] **Fixed**: each new game replayed the same random sequence
      (fixed seed); the restart now seeds with the frame counter.
      The first game keeps `SEED` (tests); the lot 9 title will seed
      with the moment of the key press.
- Bench defects fixed along the way (not the game's): `until:X` twice in
  a row does not advance; a restart (clearing both pages, ~10
  refreshes) exceeded a 10-frame limit.
- **Second pass**:
  - **Fixed — missed VBL edges on //e**: `timing_scan` must run at
    least once per blank (~4,550 cycles). `aliens_pass` (40 aliens
    when several rows change) and the column erases of
    lot 3 ran up to ~6,200 cycles without scanning: about one
    refresh lost in 3,000, hence a slightly slower game and late frames
    **not counted**. Scan added every
    8 aliens, after each erased column, between shots and bombs, in the
    message. Permanent test `vbl_edges` (each counted edge ≤ 1.5
    refreshes after the previous one, entry and 10-shot bench).
    Consequence: the NTSC entry now shows its true late frames,
    **~37 frames out of ~1,600** (21 before: the missed edges hid some).
  - The page being drawn is never displayed: 300 samples
    during rendering on //e (a2shot) and on //c / //e (probe).
  - Ctrl-RESET with the VBL IRQ active on //c: back to the ProDOS launcher,
    clock released (`iic32-reset`, `iie-reset` in `make test-iic`).
  - Endurance: ~10,000 frames of random play (game over, restart, all the
    aliens dead), screen invariant checked every 25 frames.
  - Joystick in the middle of the entry phase: responds within 10
    refreshes (the reading cut by the deadline keeps the previous
    value, with no measurable harm).
- **Third pass** (independent review of the assembler + paths
  never run):
  - **Fixed — erases that overflowed**: `render_init` and
    `game_init` cleared whole pages (1,024 bytes for 773) and
    zeroed, behind their variables, the clock (after a
    restart, the //e fell back to delays; the //c kept its IRQ without a
    valid handler), `ram_unit` (`/RAM` never reformatted on
    exit) and the zero page saved by the crt0 (restored as zeros on
    exit). `zero_block` clears exactly N bytes; test: clock,
    `/RAM` and zero page intact after a restart. The exit test
    "/RAM rebuilt" passed wrongly: it looked only at the list
    of units.
  - **Fixed — fallback without a clock at 57 % speed**: two `WAIT(80)`
    on top of the drawing; now one `WAIT(60)` (88-101 %).
  - **Fixed — unbounded joystick read on //c**: without a joystick and
    without an interrupt, `joy_read_irq` spun forever; bound at
    255 counts (17 cycles a count, thresholds re-set: 45 / 124 out of 165).
  - **Fixed — boot**: `WG2.SYS` not found looped forever;
    message, a key, QUIT (parameters in the relocated page).
  - Now tested: 64 KB (MACHID), volume without `WG2.SYS`, //c interrupt
    that stops (with and without a joystick), fallback without a clock.
- **Fourth pass** (after lot 5; independent review of the
  assembler + tests):
  - **Fixed — bonuses almost never dropped**: the kind came
    from the low byte of a second draw, which is only the first shifted
    by one bit; after the "< 40" test, only coins and S came out
    (model and 6502 identical: the oracle could not see it; the oracle
    `bonus_effects` places the objects itself). The kind now comes from
    the high byte (uniform to 3 %). Test: ≥ 15 kinds dropped in 30 model
    games (5 before).
  - **Fixed — with the Mockingboard, the speaker also played** each
    sound effect. Test: no toggle of `$C030` with the card.
  - **Fixed**: `objects_erase` without `timing_scan` (6 objects + 6 bombs
    could exceed a blank); the shot sound went off without a shot (slots
    all taken); the "end of bonuses" skull spared shield and freeze;
    ×2 picked up under ×5 brought it back down to ×2 (the stronger is kept).
  - **Guard added**: an object dropped below row 184 would be drawn
    in the zero page (checked by forcing it); the rules cannot
    produce it (a shot hits nothing below row 179); permanent test
    `model_invariants` (everything the logic gives the drawing stays
    drawable, gauges within their bounds).
  - Ctrl-RESET and ESC in the middle of the music (T1 IRQ active on //e):
    back to the ProDOS launcher, which responds.
- **Remaining, outside lot 3**: when the 40 aliens are dead, nothing
  happens (next levels: lot 6). The ProDOS file buffers (lot 6)
  will have to avoid `$1000-$12FF` (row tables).

## Lot 4 — sound: Mockingboard or speaker (done, 2026-10-23)

`src/sound.s`, data `src/sound.inc` (`tools/sound.py`). `logic.s` only
raises event bits (`snd_ev`: shot, alien shot down, ship
hit, armour, game over), outside the state compared with the model.

- [x] Detection at boot (`mb_detect`), **before** the //c clock;
      `audio_slot` (0 = speaker).
- [x] `[lib]` `mockingboard.asm`: option **`MB_FAST_WRITE = 1`** (absolute
      operands patched by `mb_init`, ~55 cycles a write instead of
      ~110); default 0 identical byte for byte to the old code;
      `dev/tests/test_rgb_mockingboard.py` passes on both variants.
- [x] ~~Deviation from the plan — no PT3~~: **PT3 done in lot 6** (see
      below). The lot 4 home-made two-voice format was removed; the
      original A minor song (`tools/sound.py`) became a PT3 module.
- [x] Music on **the VIA's timer 1 IRQ at 60 Hz** (ProDOS handler
      `ALLOC_INTERRUPT`, `mus_irq`, its own zero page `mptr`, `mb_chip`
      kept): notes start on time whatever the number of frames
      a second, and at the same tempo in PAL. First version (advanced once
      a frame): each attack fell on a frame boundary and
      the rhythm limped with the frame rate — **heard by the user**
      (2026-10-23); test `tempo` (60 ticks per second of CPU during
      the entry, seated formation and PAL). Chip 1: music (A melody, B bass,
      decaying volume); chip 2: sound effects (voice A, tone or noise), written
      by `sound_frame`. Registers written only if they change.
- [x] Speaker: sound effects only (no music in the game), played
      **in the wait loops** of `timing.s` (//e: up to the VBL edge;
      //c: up to the flip by the IRQ), one `STA $C030` every
      `spk_period` 63-cycle turns (both loops have the same length:
      `spk_pad` on //c). Never a delayed frame: without free time, the effect
      falls silent. Wait bounds brought down to 8,192 turns (~0.5 s): the
      longer turn had taken the //c fallback to ~4 s.
- [x] Priorities: death > game over > armour > alien shot down > shot; an
      effect of the same rank restarts from the beginning. **S** turns the
      sound off / on.
- [x] Speaker music outside the game (`duet.asm`): no screen outside the game
      before lot 9 (title, shop).
- [x] AY silence before a disk access: no disk access in the game before
      lot 6.
- **Acceptance** (`make test`, `tests/test_audio.py`): speaker — nothing
  without an effect, a shot = toggles, all in the wait loops,
  nothing when S mutes; Mockingboard (a2shot `--mockingboard`, AY registers
  decoded from the VIA writes) — slot 4 found, music on chip 1
  (first note, melody advancing), shot on chip 2, silence on S and
  ESC, music back on S; frame rate with the card: 1,000 frames in
  2,000 refreshes, none late. `make test-iic`: effects on
  //c and //e, from the wait loops only.
- **To watch**: NTSC entry ~41-46 late frames out of ~1,600 with the
  card (sound ~1,100 cycles a frame). Lot 6: PT3 music, see below.

## Lot 5 — bonuses and gauges (done, 2026-10-23)

Logic: `tools/model.py` (kinds, weights, effects) → `tools/bonus.py` →
`src/bonus.inc` (constants `K_*`, `drop_table`); 6502: `drop`,
`pickups`, `take` (jump table) in `src/logic.s`.

- [x] 32 kinds of objects (≤ 6 at a time, 2 rows a step): coins
      10/50/100/200 (BCD credits, cap 9999), S, B, T, weapons single
      (malus) / double / triple (oblique shots ±1 cell a step), autofire
      (a volley every 4 steps, fire **held**: Open Apple or
      SPACE kept down), armour, life, skull (at random: single weapon, S−1,
      B−1 or end of the timed bonuses), letters E-X-T-R-A (all 5: a life),
      ×2 / ×5 (on the score), shield, freeze (the aliens stop and no longer
      fire; explosions go on), 6 rank marks + dark
      mark (kept for lot 7), icons of the 2 sub-games (kept for
      lot 8).
- [x] An alien shot down drops an object about one time in 6 (`DROP_RATE` 40/256),
      kind drawn from a table of 64 (weights in `model.py`).
- [x] Gauges: S = speed (1..5 → 2..6 cells a step), B = shots on
      screen (5..10), T = duration of the bonuses (30..90 s, 300 steps a notch); at
      the maximum (and armour 2, 4 lives), the icon pays 500 points (× the
      multiplier).
- [x] Objects drawn without pre-shift: they fall straight on a column of
      14 dots (2 bytes); icon = a `bbfont` letter + a bar in the
      category's colour (`tools/sprites.py`, 16 bytes), EOR.
- [x] HUD: S and B gauges in 5 segments, T in seconds, credits, EXTRA
      letters picked up ("-" otherwise).
- **Acceptance** (`make test`): new oracle `bonus_effects` — each
  kind falls on the ship (placed at once in the 6502 and the model),
  gauges pushed to the maximum, EXTRA twice, skulls, weapons, autofire,
  ×5, freeze: 964 steps identical to the model, 32 kinds taken (77 pickups);
  random oracle with fire held; screen invariant with objects (69
  samples out of 480).
- **To watch**: NTSC entry ~44 late frames out of ~1,600.

## Lot 6 — 100 levels, packs, boss (done, 2026-10-23)

Done (model `tools/model.py` = bit-exact oracle, tables
`tools/bonus.py` → `src/bonus.inc`):

- [x] Levels: kinds NORMAL / BIG / BONUS / KAMIKAZE / BOSS, parameters
      by tables (`lv_*`) + saturation by loop, 60-step teleport
      with "LEVEL n", mirrored loop after 100; `ESCAPE_Y = 224`.
- [x] `WG2.AUX`: 24 small + 8 big alien tables at aux `$2000`,
      loaded in 8 KB blocks (bitmap `$BF60-$BF63` freed during the
      READ), `pack_check` copies the current pack into `$1000-$1FFF`.
- [x] Big aliens (row 0, even slots, 2 HP, rank mark); 16×24 boss
      that jumps 7 cells every 8 steps, core cells 4-11, rosette and aimed
      bomb.
- [x] Hurry-up: a normal or big level that lasts more than 1,800 steps (60 s)
      brings out a saucer at the top (y 10), 2 cells a step, which bounces,
      out of reach, and drops an aimed bomb every 12 steps; it leaves
      at the end of the level. Tested: bit-exact oracle (level pushed to
      `level_t` = 1 740), screen invariant.
- [x] **PT3** (requested during the lot): Vince Weaver's player
      (pt3_lib 0.5, 0BSD) as `[lib]` **`dev/lib/apple2/pt3/`** (sources
      unchanged + relocatable `pt3_zp.inc` + `pt3.s`: decoding only, without
      IRQ or card writes). Song: `tools/pt3.py` writes
      `build/song.pt3` from the melody and bass of `tools/sound.py`
      (table 1, notes an octave higher: the Mockingboard at 1 MHz plays
      an octave and ~40 cents lower). Player + song **in aux memory
      at `$6000`** (zone `AUXM` of `game.cfg`, `build/game.bin.mus` appended to
      `WG2.AUX` after the packs): main memory keeps its room
      for lots 7-9. The timer 1 IRQ enters it through **trampolines at
      `$1FE0`** (same bytes in main and aux, RAMRD/RAMWRT); player ZP
      `$D0-$EF` (outside ProDOS's `$FA-$FF`). Chip 1: registers
      written if they change (R13 `$FF` = unchanged); chip 2: sound effects.
      The GROUiK player of A2FileCmd (pointed out by the user) was
      set aside: 4.8 KB + 613 bytes, and its adaptation puts engine and
      song at aux `$2000/$4000` (our packs).
- [x] Tick ~1,450-2,400 cycles (average 1,570): the IRQ does a
      `timing_scan` on entry and on exit, made **atomic** (`sei`)
      so as to count no edge twice.
- [x] `make test-long`: autopilot (levels 1, 25, 100 finished with
      3 lives) and worst levels (97, boss 25, boss 100) with and without a card.

## Bug hunt 5 (2026-10-23, after lot 6 and the PT3)

Independent review (subagent) + checks; each bug has its test,
checked failing before the fix.

- [x] **Speaker ~13 % too low on //e** (introduced by the PT3):
      atomic `timing_scan` (`php/sei/plp`, +9 cycles) took the turn of
      the wait loop to 72 cycles, `SPK_TURN` stayed at 63 and the //c
      (`spk_pad`) no longer matched. `SPK_TURN = 72`, `spk_pad` +9; pitch
      test in `test_audio.py` (half-periods = n × `SPK_TURN`).
- [x] **Stick skewed by the music** (//e and //c with a card): a PT3 tick
      in the middle of the paddle count stopped X but not the timer, reading
      too low (right read as "left" ~1 frame in 15). The reading is
      dropped if `mus_ticks` moved (no `sei`: on //c it
      would block the flip). Test `joystick` with the card (right,
      centre: constant values).
- [x] **Pack change**: a single `AUXMOVE` of 1,232 bytes under
      `sei`, ~50,000 cycles without IRQ or `timing_scan`: a music tick
      and VBL edges lost at each pack. `aux_fetch` copies 64 bytes
      at a time (`sei` per block, scan between two). Scene "level changes,
      Mockingboard" of `vbl_edges` (fails with blocks of 255).
- [x] **Dead stick without a video clock** (delays: //c whose IRQ stops,
      no mouse firmware): read before the WAIT (`joy_read_delay`, 17
      cycles a count like the other loops). Test `joystick_delay`.
- Checked without defect: IRQ and memory state (RAMRD/RAMWRT/ALTZP/80STORE),
  trampolines, ZP (crt0 saves the 256 bytes), size of `WG2.AUX`, PT3
  module (header, patterns, samples, loop), shared sound states, saucer
  (EOR/STA order, including above the big aliens), boss.

## Bug hunt 6 (2026-10-23)

Second independent review (bounds, rare branches, model = 6502);
long oracle on loops 1, 5, 250 and 255 (boss of level 100): identical.

- [x] **The boss's gifts lost** (a model rule too): life and 200
      coin fall from row 32, the end of the level came 40 steps after
      the boss and wiped them half-way. Falling objects
      now hold the end. Model test (ship underneath: the
      life taken), fails on the old model.
- [x] **Freeze (FREEZE) on a big-alien level**: the frozen loop did not
      list the seated big aliens, shots went through them (the
      model hit them). Oracle "frozen big aliens" (freeze at step 140
      of level 3), fails without the fix.
- [x] Big alien settling: missing from the list of targets that step
      (`home`), the model counted it. Fixed (`fly_add`).
- [x] "LEVEL n" right to the end: n on 16 bits, 5 digits
      (11-character message, GAME OVER centred in it); before, the
      hundreds were loop mod 10 (wrong after level 1,000). Test
      `messages` (2 … 25 601).
- [x] The loop saturates at 255 (255 + 1 gave 0: the game became
      easy again); oracle "loop 255" in `make test-long`.
- [x] The score stops at 999,999 (it went back to 0); test `score_cap`.
- [x] No more levels advancing behind GAME OVER (bonus / kamikaze emptied
      by themselves and loaded the next pack).

## Lot 7 — shop and ranks (done, 2026-10-23)

Done:

- [x] Rules in the model (`ITEMS`, `buy`, `shop_exit`) and in
      `logic.s` (`shop_room`, `shop_can`, `shop_buy`, `shop_exit`), tables
      by `tools/bonus.py` (BCD prices, names). The shop opens at the end of
      the teleport that follows the 4th level of each pack (4, 8 … 100)
      if one has ≥ 50 credits; the logic waits (`shop`), the next level
      comes on leaving. Test hook `noshop` (closed at once,
      nothing bought) for the scenes that cross a pack's end.
- [x] Screen (`src/shop.s`): overlay linked for `$4000` (zone `SHOPM`,
      `build/game.bin.shop`, 1.4 KB with the duet), stored at the end of
      `WG2.AUX` (aux `$7000`) and copied to page 2 when the shop
      opens (page 1 displayed): **no disk access in the game**. Credits,
      rank, 10 items with prices and "MAX" at the limit, gauges, marks
      (game icons), cursor; ← ↑ / → ↓ move, RETURN or SPACE
      buys (chime; refusal: small sound), ESC or LEAVE leaves; joystick
      (TAB mode): paddle 1 up / down, button 0.
- [x] Music: Mockingboard, the PT3 goes on; **speaker: the duet**
      (`dev/lib/apple2/duet.asm`, page-aligned in the overlay) plays
      the game's melody and bass in slices of 4 (~33 ms), a key
      cuts the slice (the lot 4 point "speaker music outside the game"
      is done for the shop; the title in lot 9).
- [x] Ranks: 6 marks → rank + 1 on leaving (marks reset to 0);
      dark mark → rank − 1; RANK MARKER gives the first missing
      mark. Rank 0-99.
- [x] Tests (`tests/test_shop.py`, `make test`): purchases by keyboard with
      the card (including a refusal), mark bought → rank + 1 through LEAVE, dark
      mark → rank − 1 through ESC, purchases by joystick, speaker music
      (voices toggling, an event every 0.233 s, cursor that
      responds), no shop under 50 credits; each final state ==
      model.

## Lot 8 — sub-games (done, 2026-10-23)

Done:

- [x] Entry: the icon caught (`subgame`) starts the sub-game **at the end of
      the teleport** that follows the level; then the shop (if it is
      a 4th level and ≥ 50 credits), then the next level (`teleported`
      in `logic.s` and the model).
- [x] **Meteor Storm** (`src/storm.s`, rules in the model's `storm_step`,
      step-exact oracle): in the game engine, same sprites, same
      frame rate. The rocks are aliens (slots 0-11, state
      `ST_ROCK`), drawn like flying aliens, with a
      rock drawing (2 frames, `WG2.AUX` after the big aliens, copied into
      `cur_alien` by `pack_check`). Fire held = faster (+1 a step, 0-63),
      released = slower (−2: slowing down is faster than speeding up); the
      field comes down 2 + speed / 8 rows a step (rocks, coins, and
      the stars on top of their own speed). A rock or a coin
      every 28 rows; 4,096 rows to cover; "METEOR STORM"
      during the first 60 steps. Its own HUD: SPEED and DIST in 8 segments,
      credits. Crash: the ship explodes, **no life lost**, end when
      the explosion ends. Crossing: a prize by the time taken (in
      slices of 128 steps, ~4 s: 32,000 → 2,000 points), multiplier
      included. Then teleport (LEVEL n).
      Code **resident at `$0800-$0FFF`** (zone `LOWM`, protected by the
      crt0): copied from `WG2.AUX` (aux `$8000`) at boot, 601 bytes.
      No late frames at full speed (with and without a card).
- [x] **Memory Station** (`src/memory.s`, in the shop's overlay):
      grids 3×3, 5×3, 5×5 then 7×5; pairs of bonuses (coins, S, B, T,
      life, armour, weapons 2-3, EXTRA letters, ×2) and **a skull** (the
      pirate flag) that ends the station. A pair: its bonus (`take`,
      like a caught icon); the grid finished: **+25,000** and the next
      grid; two different cards stay visible ~1 s. Time: T
      gauge (10 s per T level) per grid, the screen's clock (the game's
      logic waits). Cards = game icons (`?` face down). Arrows or
      I J K L, RETURN or SPACE, ESC leaves; joystick: paddles 0/1, button 0.
      Music: PT3 or duet, like the shop. Rules (`mem_deal`,
      `mem_turn`) against the model.
- [x] Tests (`tests/test_subgames.py`, `make test`): model (20 storms,
      deals of all sizes); **Meteor Storm oracle** step-exact from
      level 4 (crossing at full speed; crash without losing a life);
      Memory Station by keyboard (a mistake, 4 pairs, grid finished +25,000,
      skull on the 5×3 grid), by joystick (a pair, ESC, then the
      shop), time out. `test_screen`: storm screen == full redraw
      (HUD, rocks, message). Central message raised to 12 characters.

## Lot 9 — title, demo, records, integration (done, 2026-10-23)

Done:

- [x] **Title screen** (`src/front.s`, in the shop's overlay: segment
      `FRONT` after `DUET`, overlay raised to 8 KB, aux `$7000-$8FFF`; the
      shop copies only its part). Picture `tools/title.py` (WARGALAGA in
      font letters ×2 cells × 3 rows, II, the small aliens,
      stars) → `fhpack -c -9 -h` → **792 bytes**, decoded to page 1 by
      `lz4fh.asm` assembled in the overlay (`[lib]`: option `LZ4FH_HERE=1`,
      default identical). Under the picture, a panel (rows 11-23): menu
      (play, J keyboard / joystick, S sound, H help, ESC quit, best
      score), records, help. Music: PT3 or `duet` (the shop's
      `sh_tick`).
- [x] **Demo mode** (`src/demo.s`, resident at `$0A59` after Meteor Storm):
      a real game (level 1, `SEED`), `logic_step` takes each step
      from `src/demo.inc` (`tools/demo.py`: the autopilot's moves
      on the model, fire pressed and held, one-byte runs,
      ~320 bytes for 1,800 steps: levels 1 to 3, start of the 4th); shop and
      station closed (`noshop`); "DEMO" in the centre (message 4); a
      key, a button, the end of the script or GAME OVER: the title. Idle
      cycle: menu ~10 s, records ~8 s, demo.
- [x] **Records** `HIGHSCORES` (`tools/records.py`: format, rules, new
      file; 8 entries: initials, BCD score, level reached; the joystick):
      read once (defaults if it is missing or invalid), written after a
      record or a joystick change (created if missing); write-protected
      disk: "SCORES NOT SAVED", the table stays in memory. Initials
      by keyboard (letters, digits, `.`, ← / DELETE, RETURN) or by
      joystick (Y chooses, button confirms); 30 s without anything: what was typed.
- [x] **Choice of input device** at the title (J or TAB), kept in
      `HIGHSCORES`; TAB stays in the game.
- [x] Flow: boot → title; ESC in the game → title (record possible),
      ESC at the title → ProDOS; GAME OVER → title after the shot (past
      `OVER_WAIT`) or `OVER_END` = 240 frames.
- [x] Build: `HIGHSCORES` on the volume, `fhpack` (`dev/cc65/fhpack.mk`),
      `make test` including `tools/demo.py --check`. Root: `wargalagaii`
      in `IIE_PRODOS_GAMES` (`all`, `profile-iie-prodos` which walks the
      list) and in `TESTED` (`test-wargalagaii`), line and section of the
      root README, screenshots `screenshots/`.
- [x] Tests: `tests/test_front.py` (records rules; title = picture +
      menu, J, H; idle cycle; **whole demo == model** step-exact,
      1,801 steps; demo stopped by a key, by the button, without a record;
      record by keyboard, file written then read back; record by joystick on
      a write-protected disk, error `$2B` via `POM2_MEDIA_WRITE_DEFAULT`);
      `test_screen`: demo screen == full redraw. The other tests
      start through `tests/boot.py` (`front_skip` set in `_main`: the game
      at once, `SEED`); those that let the game end hold
      `over_wait` at 0 or give 9 lives.
- [x] Bench (`tools/profile.py`, //e NTSC): formation + divers + 10 shots:
      average render 21,145 (worst 27,672) + logic 3,759 (worst 4,493); boss
      (level 25): render 18,417 (worst 26,348) + logic 4,522 (worst 5,617),
      against 28,060; no late frames on these scenes, nor in Meteor
      Storm (lot 8). Nothing moved into a lib: no `bench-check` entry.
      Wave entry (already over the budget): 88 late frames out of
      1,600, against 78 before the lot; the code placement alone (padding
      bytes before `_main`) makes this number vary from 80 to 90: alignment
      noise, not the cost of the new tests.
- [x] Independent review (subagent, code only): nothing that crashes,
      blocks, overwrites or desynchronises the demo; six defects fixed:
      DELETE erased as uppercase (`$7F` → `$5F`, erased nothing), button
      still held after the last initial by joystick = "play"
      (`fr_btn` read again after the entry), initials timeout counted from the
      last input, SPACE held at GAME OVER skipped the title (keys
      locked until released), the "NOT SAVED" message cut short
      by a key (speaker), a short `HIGHSCORES` kept stale
      bytes (defaults if fewer than 64 bytes read).

## Bonus readability (2026-10-23)

Request: "the display of the bonuses must be greatly improved with
readability in mind". Before: a font letter (one-dot strokes, colour
fringes) and a colour square, 2 × 8; two T, two A, digits
for the weapons as for the marks.

- [x] Icons redrawn in `tools/sprites.py` (`ICON_SHAPES`), **7 cells
      × 13 rows** (`ICON_H` = `OBJ_H`, 8 before), drawn in 2-dot
      cells: white strokes without fringes. One shape per family, the colour
      says which: coins = disc with a cut-out `$` (green 10, orange 50, blue
      100, violet 200); gauges = blue pill S B T; weapons = violet pill
      (1, 2, 3 shots; autofire: dashes); multipliers = orange pill
      2, 5; EXTRA = white pill; shield = green bubble around the
      ship; armour = blue shield; life = orange heart; skull; freeze = snowflake;
      marks = medal (ribbon, disc of the colour, cut-out number),
      dark mark = empty medal; sub-games = the rock, the green `?` card.
- [x] `icon_src` by table (`icon_lo/hi`); the pickup box follows
      `OBJ_H` (model and 6502); demo script regenerated; title help.
- [x] Bug found along the way (lot 7): the shop's marks were
      placed every 3 columns, every other one on an odd column, where
      the colours swap (orange shown blue): step of 4 (test
      `marks_screen` of `tests/test_shop.py`).
- Cost: 5 more rows per object, on erase and draw; about
  520 cycles per visible object and per frame, counted on the code (not
  measured), so ~3,100 at worst with 6 objects on screen. No late
  frames on the bench, frame rate unchanged (90 late frames at the wave
  entry, within the 80-90 noise measured in lot 9).
- Preview: `screenshots/bonus.png` (all 32, in the order of `model.KINDS`).

## Bonus and malus effects made visible (2026-10-23)

Request: "implement the actions of all the bonuses and maluses". The 32
effects had existed since lot 5 (model and 6502, oracle
`bonus_effects`) but a pickup was silent and invisible: nothing said
what had been taken, nor which malus the skull had drawn.

- [x] **Name on pickup**: the message in the middle of the field (row 96)
      shows what the pickup did for `PICK_T` = 45 steps (1.5 s):
      "+50 CREDITS", "TRIPLE SHOT", "SCORE X5", "RANK MARK 3"…; a
      gauge, the armour or the lives already at the maximum: "BONUS POINTS"; the
      skull tells its malus ("SINGLE SHOT", "LESS SPEED", "LESS BULLET",
      "BONUS LOST"); the fifth letter: "EXTRA LIFE". Priority:
      GAME OVER, LEVEL n, METEOR STORM, then the pickup, then DEMO.
- [x] Logic state `pick_msg` / `pick_t` (model = oracle, `take` sets
      `pick_msg`, `pickups` arms `pick_t`); 36 texts of `model.PICK_TEXT`
      generated by `tools/bonus.py` in the `PICK` segment of LOWM ($0BCE,
      504 bytes: main memory has only ~380 left).
- [x] **Two sound effects**: `bonus` (rising arpeggio C-E-G-C) and `malus`
      (descending chromatic) for single weapon, dark mark and skull;
      priority between the armour and the explosion.
- **Acceptance**: `bonus_effects` extended (988 steps == model, the 36 texts
      seen); `pickup_feedback` (SHIELD + bonus sound, DARK MARK + malus sound, the
      message clears); the screen invariant knows the message.
- Cost: a message change rewrites 12 characters on each page (at
  pickup and 1.5 s later), not every frame.

## Bug hunt 7 — aux loading and build (2026-10-25)

- [x] `aux_load` now checks the cumulative size **before** each
      `AUXMOVE`. A `WG2.AUX` that was too long was rejected only after having
      written past its aux zone. Reproduction: 64 added bytes
      overwrote the sentinel placed just after the expected file.
      `tests/test_game.py` covers the empty file, truncated, too long by one
      byte or by an 8 KB block: sentinels and bitmap preserved, error
      message and return to the ProDOS launcher.
- [x] The generation of `song.pt3` accepts an absolute `BUILD`: the change
      of directory to `tools/` used to prefix its destination with
      `../`, which broke the isolated builds in `/tmp`.
- Validation: isolated build, `make test` and `tests/test_long.py` (loop 255,
      busiest levels with and without a Mockingboard). The images in
      `dist/` stay untouched.

## Lot 10 — the look of Warblade (2026-10-30)

Request: "Improve wargalaga" (boss, smoothness, bonus timers, rank
in the game), then "wargalaga must look much more like warblade".
References: screenshots from the archived official site
(warblade.as/bilder) — textured walls, HUD on the sides, mixed formations.
Mock-ups approved before code.

- [x] **10a frame**: field of 112 cells between two 4-byte walls
      (`model.FIELD_COL`, the `cell_byte` table shifts all the rendering at no
      cycle cost); walls `tools/walls.py` (a 64-row tile per quarter, in aux
      at $A200, via `iobuf`, one page a frame at the quarter change, without
      touching the HUD rows: `hud_cover`). 128-character HUD in
      their place (`tools/hud.py`, Python copy for the tests); HI = best
      record then the score. Memory: `icons` at $1C40 (LOWHI), shop
      names in the overlay, level records in aux (14 bytes).
- [x] **10b formations**: 9 shapes (`model.SHAPES`), masks per row,
      staggered by half a pitch, second species (`alien_combo2`, entries 28-41,
      `cur_alien2` in `iobuf`), two-tone aliens (`sprites.two_tone`).
- [x] **10c boss**: 24 × 28 cells two-tone, 7 shifts in aux ($AA00)
      copied on the boss level into `iobuf` and `cur_big`; drawn in STA with
      a one-cell margin (a copy, no erase); one cell every
      8 steps between cells 1 and 80; hit points doubled.
- [x] **Rank**: GAME BONUSES screen (title overlay): credits × 100,
      rank × 10,000, `perfects` × 5,000, added before the records.
- [x] **10d smoothness**: HUD — key comparison without writes, and only
      the score rewritten when it alone changes (the full fill costs
      ~4,000 cycles). `test-long`: level 97 70 late / 564 (77 before),
      boss 25: 21 / 589, boss 100: 46 / 576.

## Lot 11 — Warblade's Meteor Storm (2026-10-30)

Request: "In the original warblade you easily got to a meteor storm",
then "that's not what the meteor storm mode is in warblade.
Look it up" (option 2: complete rework). Source: Warblade wiki
(pages Meteor Storm, Bonuses), recorded in `docs/warblade-reference.md`.

- [x] **Entry**: the icon (weight 4/64, memory 3/64, 10 coin: 5/64;
      before 1, 1 and 10: an icon every ~16 levels) **ends the level
      on the spot** (`tk_meteor` → `ls_over`), except on a boss level
      (the storm waits for its end).
- [x] **Storm** (`storm.s`, model `storm_step`, step-exact oracle):
      rocks of three sizes (small: `cur_alien2`, row 1; medium;
      big: `cur_big`), each a little faster than the field (2, 1, 0);
      the field speeds up at the thirds of the distance (+1, +2) and with the gauge
      (+3/16 of the speed beyond the 8 red bars); 4,608 rows.
- [x] **Gauge** right of the ship: 26 bars (8 red, 18 green), STA
      like the ship; vertical **distance bar** in byte 35 of the
      field (rocks, objects and ship stay to the left).
- [x] **Objects**: silver 50/100/200, tablets 1,000/5,000/10,000 points
      (three new kinds, `p1k p5k p10k`).
- [x] **Percentage** = steps with fire held / steps flown, rounded; 101 %
      as long as the fire was never released. Prize (× multiplier): MEGA (101 %)
      500,000 + 5,000 credits; XTREME (100 %) 250,000 + 5,000; SUPER
      (95-99 %) 100,000 + 1,000; EXTRA 50,000; its name 60 steps. Crash:
      500 points per 256 rows flown, no life lost.
- [x] Memory: pickup texts in aux (`pick_fetch`), paths
      and routines at `$0200-$03CF` (`LOW2`), rocks at aux `$B100`. Remaining:
      LOWM 12 bytes, LOW2 94, main code ~150.
- [x] Smoothness: HUD — when only the score differs for the page, only
      row 0 is compared (~1,900 cycles per hit) and a VBL
      scan every 32 characters (the bench missed an edge). Storm at
      full speed: 8 late out of ~600 frames (2 at the start: the frame of
      the bar). `test-long` measures each scene from three starts (a
      single one: 93 to 157 late with the card, before as after this lot).

## Modes and white shots (2026-10-30)

Request: "The enemies' bullets and my bullets must be white otherwise
they will be mistaken for the coloured stars!!! The game is too hard. It
starts in easy mode to begin with, the harder modes must be earned".

- [x] Shots and bombs: two neighbouring dots on the 7 shifts (white;
      at shift 3 the shot had only one coloured dot left, the bomb was
      a blue dot).
- [x] Modes (`model.MODES`, `mode` in game.s): NORMAL = the game as before;
      HARD, ACE = one, two loop notches more; EASY = dives and
      bombs 1.5 times further apart, two divers fewer (1 at least),
      bombs and kamikazes one row slower (2 at least). The demo plays
      NORMAL (its script).
- [x] Title: line M MODE; a new player has only EASY; a game that
      beat the boss of level 25 (level 26 reached) in the hardest
      open mode opens the next one ("NOW OPEN:"). `HIGHSCORES` byte 2:
      bit 0 controls, bits 1-2 open modes, bits 3-4 chosen mode.

## Bonuses, joystick, waves (2026-10-30, continued)

Requests: "Improve the bonus sprites", "The joystick centre needs a dead
zone", "Why are there moments far too long
without enemies".

- [x] Bonuses: solid silhouettes, sign cut out in black. Gauges = blue
      tile with a white letter (the cut-out letter was mistaken for the blue
      coin), EXTRA letters = white tile, ×2/×5 = orange gem, weapons =
      violet cannon under its white shots; coins, medals, etc. unchanged.
- [x] Joystick: centre = rest position read by PREAD (×5/8) at the start
      of the game and on TAB, bounded 50..115, dead zone ±40 (`joy_calib`, in LOW2: main
      RAM was full). Test `stick_off_centre`.
- [x] Waves: between two waves, empty field → the next one within
      ENTRY_FIRST steps (the gap rose to 90 steps, 3 s, before level 12).
      Remaining: the teleport (60 steps) and the wait for falling bonuses.
- [x] Speaker wait loops: they had slipped across
      a page boundary (2 more cycles a turn: lower sounds); reordered,
      `.assert` at link time.

## Memory reorganised, music (2026-10-30, continued)

Requests: "Reorganise the program to optimise the use of memory
and exploit all the accessible memory reserves", then
"check the stability of the music playback. The S key turns off the
music but leaves the sound effects".

Free main RAM: 13 bytes → 1,945 (`$B657-$BDE4`).

- [x] Text page 1 (`$0400-$07FF`, never displayed in the game): the
      drawing records of `render.s` in 8 windows of 120 bytes between the
      card holes (`TXT0-7`), zeroed by `render_init`; `fail` does HOME
      before writing (−~750 bytes of BSS).
- [x] Page `$BE00` (C stack, unused: no C): the crt0's
      zero page save (−256).
- [x] Zero page `$83-$BA`: 25 bytes of hot variables outside the state and 24
      bytes of state (level, lives, ship, shop…): one byte and one
      cycle less per access (−346 of code). The tests read the state by
      zone (`tests/block.py`).
- [x] Startup code (`BOOT`: checks, loading of `WG2.AUX`,
      trampolines, row tables, messages) run from `$1700`, where
      `LOWBSS` will be afterwards; `WG2.SYS` copies it there (−~540).
- [x] `timing.s` linked first: its wait loops no longer move (the
      added code had put them across a page boundary: wrong sounds).
- [x] PT3 player at aux `$2000` (packs at `$3000`): facing HGR page 1,
      never a main code address; a test `until` landed in
      the music interrupt and read aux.
- [x] Music measured tick by tick: in the game ±0.7 ms; at the title, reading
      `HIGHSCORES` masks the interrupts ~0.8 s (Disk II driver): the
      note stayed held → `mus_hush` silences the chip before each disk
      access. Test `steadiness`.
- [x] S: music only (chip 1, the title and shop duet); the
      sound effects remain. Menu "S  MUSIC".
