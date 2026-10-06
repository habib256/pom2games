# ARKABREAKOUT — roadmap

Goal: a fast, original brick-breaker for the Apple II+ 48 KB, HGR 280 × 192,
6502 at 1 MHz, on a self-contained DOS 3.3 disk.

**Direction:** recover as much of [CHROMABREAK](../chromabreak/README.md) as
possible without DHGR, on a 48 KB II+, by **storing the boards on disk and
loading them on demand**. Everything below is ordered towards that.

## Where we stand (measured on the current build)

| Item | Value |
|---|---|
| Binary (`build/game.bin`, BRUN at `$6000`) | **7 670 B**: CODE 3 798 B, RODATA 3 872 B |
| BSS after the binary | 333 B, `$7DF6-$7F42` |
| Free below DOS (`$7F43-$95FF`) | **5 821 B** (region limit `$6000-$95FF` = 13 824 B) |
| LOWBSS `$1000-$1FFF` | 544 B used (`bricks`, two dirty lists, `paddle_map`), **3 552 B free** |
| HGR pages | `$2000-$5FFF`; page 2 memory is idle whenever a static screen shows on page 1 |
| Boards today | `src/levels.inc`: 12 boards × 96 B + 24 B pointer table = **1 176 B** of RODATA |
| Other RODATA | font 512 B, `div7`/`mod7` 512 B, scanline tables 384 B, title 384 B, capsule glyphs 342 B |
| Disk (`../dist/ARKABREAKOUT.dsk`) | ARKABREAKOUT 31 sectors, HELLO 2, **463 sectors free** (≈115 KB) |
| Update rate | ≈32/s idle, ≈29/s in play (keyboard and paddle), `tests/test_game.py` |
| Idle time per update | the loop ends on `WAIT #100` (keyboard) / `#88` (paddle): ≈26 400 / ≈20 600 cycles by the Monitor formula in `apple2.inc`; at 29 updates/s (≈35 200 cycles) that leaves roughly 9 000 cycles of real work per update — **most of each frame is spare CPU** to confirm with the worst-frame measurement below |

ChromaBreak for comparison: 60 boards packed two tiles per byte (48 B) plus a
10-letter name each, **3 480 B** in auxiliary RAM; six capsules, two enemies,
three difficulties, combo ×8, two-voice music (player of 129 B in page 3,
theme + ten sector endings + fanfare ≈ 580 B of 3-byte events), help page and
ending in a 8 KB overlay loaded at `$4000`, five records with initials and
progression on disk, mouse / keyboard / joystick, 65C02 only.

## Storing the boards on disk

Two ways exist in the repository; both keep DOS resident and both have been
exercised by other games.

| | A. `BLOAD` through `dev/lib/apple2/dos.asm` | B. RWTS via `$03D9`, as `../micro-sokoban/src/fast_disk.inc` |
|---|---|---|
| How | Build the DOS command text, `dos_cmd_run` sends it through COUT; DOS loads the file | Find the file in the catalog once, cache its T/S list, read sectors with DOS's own IOB into the hidden HGR page, copy |
| Resident cost | ≈150 B of code (estimate from the source) + 40 B command buffer + a zero-page snapshot (43 B with `DOS_ZP_START/LEN` set to the game's `$50-$7A`, 256 B by default) + a few bytes per filename | several hundred bytes (catalog walk, T/S cache, IOB setup, copy) + 20 B of cache per file + a page-3 or BSS zero-page copy |
| Granularity | one file per call, any size; a pack of several boards | one sector per call: a single board can be fetched on its own |
| Errors | DOS handles them: FILE NOT FOUND stops the program at the BASIC prompt, WRITE PROTECTED likewise unless `disk_protected` is checked first | handled by the game (`disk_error`), never leaves the game |
| Writes | `BSAVE` whole file | one sector at a time, catalog and VTOC untouched |
| Disk layout | plain DOS files, `$(DOS33) --bin NAME=file@addr` in the Makefile, readable with `dos33.read_file()` in tests | custom allocation / interleave for speed (`tools/build_disk.py`), the loader and the image form one unit |

**Choice: start with A.** It fits in a few hundred bytes, the library is
shared and documented, the Makefile already produces `--bin` files, and a
pack switch only happens between sectors, where a DOS load is invisible.
Move to B later only if sector-by-sector loading (Escape menu with free
sector choice), record writes on fragile disks or load time call for it.

**Pack format.** Reuse ChromaBreak's `levels.txt` / `tools/pack_levels.py`
conventions (ASCII boards, `.` `1`-`3` `#`, reachability and uniqueness
checks): 48 B per board (two tiles per byte, 15 = steel) + 10 B name = 58 B.
Six packs of ten boards (one per decade, matching ChromaBreak's jingles) make
580 B each, three sectors; `LEVELS1`…`LEVELS6` `BLOAD`ed at `$1800` in the
free part of LOWBSS. `load_level` then unpacks one board into `bricks`
(nibble split, ≈40 B of code) instead of copying from `level_ptr`.

**Budget after the move (estimates).** RODATA loses 1 176 B, the loader adds
roughly 250-300 B of code and BSS, the pack buffer lives in LOWBSS: about
**6.7 KB** free below DOS for new features, and the board count is no longer
bound by main memory (115 KB free on the disk).

## What ChromaBreak has, and what it would cost here

HGR gives 6 colours, 280 × 192, no 65C02, no VBL. The rendering model stays
"white XOR sprites over coloured bricks", which rules out coloured sprites and
patterned backgrounds but keeps everything else reachable.

| ChromaBreak feature | Portable? | Cost and notes |
|---|---|---|
| 60 named sectors | **Yes** | 3 480 B on disk via the packs above; names shown in the HUD need a wider banner than today's `SCORE xxxxx LIVES n SECTOR nn` |
| Six-digit score (CB caps at 650 000; 60 boards yield up to 235 750) | **Yes, required with 60 boards** | `score` is 5 ASCII digits (max 99 990): one more digit, HUD shift, `update_best`/tests adjusted |
| Difficulties Relax / Arcade / Expert (lives 5/3/2, start speed 2/3/4, cap 4/6/7, ramp every 10/8/6, capsule every 4/5/6) | **Yes** | Today: 3 lives, width 28, speed 2 + sector/4 capped at 5, ramp every 12, capsule every 5. Five 3-byte tables + keys `1`/`2`/`3` at the title ≈ 100 B. Speed 7 costs 7 sub-steps per update (each ≤ 1 px/axis, so no tunnelling, only CPU) |
| Combo multiplier up to ×8, reset on paddle contact or lost life | **Yes** | ≈ 80 B + a HUD field |
| Capsules E / S / C | **Already there** (W / S / C) | — |
| Capsule D, three balls | Yes | Per-ball state (position, fractions, direction, speed) ×3, `old_bx/old_by` per page per ball, `ball_step` ×3 per sub-step, no enemies while extra balls fly (as CB). ≈ 400-600 B of code; CPU fits the spare budget. Already listed as "multiball" |
| Capsule L, double laser | Yes | Two 1×4 shots, cannon marks on the paddle, cooldown, brick damage path = `damage`. ≈ 300 B |
| Capsule P, piercing ball | Yes | One flag in `damage` (destroy in one hit, bounce on steel) + a distinct ball look (CB's red sphere is impossible in white XOR: use a bigger white ball). < 100 B + glyph |
| Three more capsule glyphs | Yes | 112 B each pre-shifted (7 alignments × 16 B) = 336 B |
| Two enemies (4×6, gates, slide along bricks, 100 pts, killed by ball / laser / paddle) | Yes, in white | `enemies.s` is 65C02 (`ply`, `.setcpu "65C02"`): rewrite in NMOS 6502. Two shapes × 84 B pre-shifted; grid probes reuse `point_hit`. ≈ 600-800 B code; CPU fits the spare budget |
| Two-voice music: title theme, ten sector endings, fanfare | Yes | `duet.inc` player (129 B, 33 cycles per turn) uses only NMOS opcodes; it needs a page it cannot straddle: page 3 `$0300-$03CF` is free under DOS 3.3 too (do not also use it for an RWTS zero-page copy), or `.align` it in main memory. Tunes ≈ 580 B, can ride in a disk pack or the overlay. Playback is blocking: fine at title / sector clear / ending |
| Prioritised sound effects spread over frames | Yes | Today 4 pitches through `tone`; a priority/length table like `sound.s` ≈ 50 B (its `stz`/`bra` need NMOS equivalents) |
| Help page (`?`) | Yes | Text through `hgr_puts8` + the capsule glyphs. As in CB, put it in an overlay `BLOAD`ed at `$4000` (HGR page 2 memory) while the title shows on page 1: zero resident bytes beyond the call |
| Ending: VICTORY, fanfare, fireworks | Yes | Same `$4000` overlay; fireworks as 1-px XOR `rectangle` calls |
| Five records with initials + saved progression | Yes | Write path needed: `BSAVE` through `dos.asm` guarded by `disk_protected` (or RWTS sector write later). Initials screen ≈ 200 B, table ≈ 150 B, file 5 × ~10 B + progression byte. "SAVE FAILED" when protected. Already listed as "high score saved on disk" |
| Escape menu: resume, sector select among reached, sound toggle, title, quit | Yes | ≈ 250 B; depends on progression + the loader (pack switch on selection) |
| Demo mode after 15 s idle | Yes | Reuse `tests/pilot.c` steering (target = ball_x offset by zone) ≈ 80 B; no 50/60 Hz detection on a II+: count updates instead |
| Paddle spin (sliding paddle drags the angle a zone) | Yes | ≈ 40 B, needs the previous `pad_x` |
| Brick flash on impact, coloured shards (max 4) | Partly | Flash: redraw white one frame through the dirty lists, cheap. Shards: white 1-px XOR particles only; cosmetic, low priority |
| Vertical paddle (height to mid-field, blocked by bricks) | Possible | Paddle 1 is already read by `read_stick` (`joy_y`); collisions and brick blocking change substantially. Low priority |
| Mouse (AppleMouse II, //c built-in) | Not planned | Outside the II+ 48 KB / DOS 3.3 profile; `dev/lib/mouse` targets the ProDOS //e///c build |
| Bevelled 12-hue bricks, per-decade backgrounds, coloured enemies/sprites, Chat Mauve, BCD score, VBL-locked 30/25 Hz, 65C02 check | No | DHGR, 65C02 or VBL specific; a patterned background would show through XOR sprites |

## Next up

1. **Level loader** — boards on disk, loaded on demand.
   `tools/pack_levels.py` (adapted from ChromaBreak) writes `build/levelsN.bin`
   packs from an ASCII `src/levels.txt`; the Makefile adds them to the disk with
   `$(DOS33) --bin LEVELSn=…@0x1800`; `src/game.s` includes `dos.asm`
   (`DOS_ZP_START = $50`, `DOS_ZP_LEN = 43`), loads the pack of the current
   decade when `level / 10` changes, and `load_level` unpacks one board from
   `$1800`. Tests: `test_game.py` loops over every board (legal cells,
   `remaining` matches) and reads each pack back with `dos33.read_file()`.
   Start with today's 12 boards to prove the path, then drop `levels.inc`.
2. **Sixty sectors and a six-digit score** — import ChromaBreak's
   `levels.txt` (reachability and uniqueness checks come with the packer),
   sector names in a reworked HUD, `subtitle` and victory text updated,
   `test_campaign.py` extended to 60 sectors (watch the 180 s timeout).
3. **Difficulties and combo** — `1`/`2`/`3` at the title with CB's tables,
   multiplier up to ×8 in the HUD; session best per run as today.
4. **Reclaim the idle time** — replace the fixed `WAIT` with a per-update
   budget counted from the simulation (same ≈29 updates/s, but the spare
   ≈26 000 cycles become usable), and measure the worst frames (banner
   updates, sounds, collisions) with `until:` cycle counts in a2run.
5. **Overlay at `$4000` + jingles** — help page and ending `BLOAD`ed into HGR
   page 2 memory; `duet.inc` player in page 3 with the ten sector endings and
   the fanfare, title theme interrupted by a key.
6. **Records and Escape menu** — five entries with initials and difficulty,
   progression byte, `BSAVE` guarded by `disk_protected`, resume / sector
   select / sound / title / quit.

## Later

- Enemies rewritten for the NMOS 6502, white pre-shifted sprites, gates and
  brick sliding as in ChromaBreak.
- Capsules D (three balls), L (double laser) and P (piercing ball), after
  measuring the CPU and memory budget left by the steps above.
- Demo mode after 15 s on the title, silent, no record.
- Paddle spin on rebounds; brick flash on impact.
- Switch the disk path to RWTS (`fast_disk.inc` style) if per-sector loading
  or robust record writes become necessary.
- Paddle sensitivity setting independent of the calibration.
- Balance duration, difficulty and capsules through manually played campaigns;
  finishing pass (screens, presentation) after play feedback.
- Check colours and fringes on a real composite monitor.
- Comfort tests on a physical Apple II+ paddle and keyboard; long interactive
  sessions in POM2 and on real hardware.

## Ideas

- Vertical paddle on paddle 1 (CB's mid-field paddle), once collisions allow it.
- Several campaigns on the disk: 463 free sectors hold far more than 60 boards.
- Level editor, or at least the packer as a validation tool (`make assets`).
- A best score per difficulty in the records file.

## Done

Kept as history; everything below is in the current build and covered by
`make test`.

**First complete version.** 12 original boards, three lives, score and
progressive difficulty; normal, resistant and steel bricks; rebound aimed by
the impact point; speed ramp with a cap, +1 every 12 destroyed bricks; a bonus
life every 1 000 points, reserve capped at five; session best kept across
replays; capsules wide / slow / catch; title, pause, defeat, replay and
victory; all 12 boards cleared by a deterministic pilot without touching the
progression.

**Readable HGR display.** Full-screen HGR with a top banner (score, lives,
sector); 12 × 8 grid with a 21-pixel horizontal step; coloured bricks, white
ball, paddle and small text; two HGR pages with object restoration and
deferred brick updates; W/S/C capsules pre-shifted for the seven alignments;
×2 title, bright brick edges, resistance notches and hatched steel; explicit
READY/PAUSE banner and paddle-aware hints.

**6502 engine.** ca65 with the shared libraries; fractional positions on both
axes, no floats; rebound angle from the paddle contact zone (eight symmetric
zones adapted to both widths, up to ≈68°); sub-steps, grid collisions and
separate axis resolution; short sounds with a bounded cost; cadence measured
(≈32 updates/s idle, ≈29 in play on keyboard and paddle); paddle timer cost
compensated by a shorter wait.

**Controls.** Proportional paddle with button launch; A/D and arrows with
continuous movement and S to stop; space to launch, P to pause, Escape to
quit; keyboard sensitivity with + and -; optional two-end paddle calibration
at the title.

**Playable milestones.** Prototype (ball, paddle, board, rebounds, lost life);
engine (collisions, drawing, cadence, paddle); full game (boards, score,
capsules, sounds, progression); first finish (screens, instructions, bootable
disk).

**Integration and validation.** `arkabreakout/` with sources, boards,
Makefile, README and TODO; `dist/ARKABREAKOUT.dsk` in the global build; 48 KB
II+ memory compatibility with DOS preserved; binary tests on a2run's NMOS 6502:
walls, ceiling, maximum speed, resistant and steel bricks, capsules, boards,
defeat/replay, victory, pause, DOS exit, frozen pages, paddle and calibration,
capsule erasure on seven alignments, diagonal contacts with bricks and both
walls, paddle centring on width changes, full campaign to victory; title and
playfield screenshots reviewed with the POM2 core; full repository `make test`
on rebuilt disks; first user feedback: the game works.
