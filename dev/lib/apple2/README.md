# lib/apple2 — Apple II equates + shared primitives (asm)

*[← dev](../../README.md)*

Assembly primitives for the Apple II: hardware equates, text, keyboard,
timing, sound, joystick and DOS commands. `hgr.asm` initialises native
video; `exit.asm` restores the zero page to hand control back to DOS cleanly.

**Neighbours:** [`../apple2c/`](../apple2c/) is the C mirror;
[`../hgr/`](../hgr/) provides HGR text and sprites.

## Files

- **`apple2.inc`** — hardware + ROM + DOS equates, the `APPLE2_PREAMBLE`
  (`BRUN` program) and `APPLE2_PREAMBLE_CALL` (program launched by `CALL`, which
  leaves the stack alone) macros.
- **`zp.inc`** — the 8 shared ZP bytes (`tmp`, `tmp2`, `print_ptr_*`,
  `mul_*`, `prng_*`), at the start of the ZEROPAGE segment.
- **`print.asm`** — `print_str_ax`: ASCIIZ string via COUT.
- **`print_num.asm`** — `print_byte_dec`: byte as three digits via COUT
  (`byte_to_dec` conversion from `lib/math/dec.asm`, included by the file).
- **`kbd.asm`** — `wait_key` (blocking), `poll_key` (non-blocking) and
  `kbd_upcase` (lower case → upper case folding).
- **`delay.asm`** — `delay_ms_a`: ~A milliseconds at 1.0205 MHz.
- **`hgr.asm`** — `hgr_init`, `hgr_init_clear`, `hgr_page1/2`, `text_restore`,
  `native_video` (on IIe/IIc, resets the 80STORE/80COL/RAMRD/
  RAMWRT/DHGR switches to native video before any mode change; nothing on II+),
  and the `HGR_CLEAR_LOOP` macro (8 KB from page X with byte A, eight
  self-modified absolute STAs per pass, ~46,000 cycles, no zero page) shared
  by `hgr_init_clear`, `clear_hgr` (lib/hgr) and `hgr_clear` (C).
- **`exit.asm`** — `apple2_zp_save`, `apple2_exit`, `apple2_return`;
  on IIe/c, turns off RAMRD/RAMWRT, 80STORE, 80 columns and DHGR before
  restoring the RESET vector and the zero page in main memory.
  Entry assumes code and stack in the main bank; the extended
  switches are not touched on II/II+. The text window and the cursor are
  kept: restore its width if the program changed it for 80 columns.
  `APPLE2_EXIT_HOOK` (defined before the include) names a routine called
  after the restore, before returning to DOS (also on Ctrl-RESET).
- **`sound.asm`** — `tone`: square-wave beep on the speaker.
- **`auxmem.asm`** — 128 KB //e / //c (65C02): `aux_store`,
  `aux_fetch_pages`, `aux_fetch_chunked` and the `AUXMOVE` macro; see
  [Auxiliary memory](#auxiliary-memory-auxmemasm).
- **`duet.asm`** — two voices on the speaker (time sharing, 33 cycles
  per pass, self-modified counts), assembled under `.org DUET_BASE` in its
  own page: `DUET_PLAY` (A = melody, X = bass, Y = slices),
  `DUET_KEYS`, `DUET_SLICE`. ARKABREAKOUT ($1300) and CHROMABREAK ($0310).
- **`mb_irq.asm`** — Mockingboard music on the VIA's timer 1 interrupt
  (ProDOS `ALLOC_INTERRUPT` or an own `$03FE`/`$FFFE` vector): `mb_irq_start`,
  `mb_irq_stop`, shadowed AY writes `mb_put` / `mb_forget`, `mb_hush` before
  disk I/O; see [Mockingboard music service](#mockingboard-music-service-mb_irqasm).
  WARGALAGA II (extracted from it, byte-identical).
- **`aysong.asm`** — the AYS song player (`ays_init`, `ays_tick`, `ays_stop`,
  `ays_mute`, `ays_pos`, `ays_set_pos`), 3 or 6 voices, bit-exact with
  `dev/tools/audio/aysong.py`; format in [AYSONG_FORMAT.md](AYSONG_FORMAT.md);
  see [AYS song player](#ays-song-player-aysongasm).
- **`vapor.asm`** — `vapor_mark`, `vapor_sync`, `vapor_count`: the vapor
  lock, a frame sync through the floating bus on a II, II+ or //e (SNAKE).
  See [Vapor lock](#vapor-lock-frame-sync-on-a-ii--ii).
- **`joy.asm`** — `read_stick`, `stick_dir`: joystick (two paddles);
  `read_stick_fast` (DIRTBIKE) returns as soon as both timers have
  run out (0.1-2.8 ms instead of 6 ms), on its own scale (~0..80, centre
  ~40): calibrate on the rest position. `joy_x`/`joy_y`/`joy_cnt` may
  be zero-page aliases. `stick_key` turns the stick and its buttons into
  one-shot key events (CHESS); `joy_buttons` gives held and newly pressed
  buttons.
- **`rwts.asm`** — `rwts_read`, `rwts_write`, `rwts_cmd`, `rwts_read_tslist`,
  `rwts_find_file`: DOS 3.3 sectors directly through RWTS (without reading the
  catalog at run time: `dev/tools/dos33patch.py` writes the T/S lists
  or the sectors into the program after the disk is built; DOS's IOB, boot
  drive, `RWTS_RETRIES` attempts, zero page kept with `RWTS_KEEP_ZP`,
  interrupts masked during each access with `RWTS_SEI`, for
  programs that enable them, such as the //c mouse),
  with no zero page of its own. The IOB address is requested from `$03E3` on the first
  call and then kept: `$03E3` reads it from the file manager's memory,
  which a game may later reclaim (DIRTBIKE). Used by DIRTBIKE
  and MICRO-SOKOBAN. `rwts_sectors` (A = 1 read / 2 write, X = count)
  reads or writes a save file's data sectors listed in the program's
  `RWTS_SEC_T` / `RWTS_SEC_S` tables (`dos33patch.py --sectors`), pages from
  `rwts_page` up (45 B); `rwts_write_tslist` writes a file in place through
  its T/S list, bounded by `rwts_count` (66 B). DIRTBIKE's `hof_read` /
  `hof_save` / `hof_sector` stay its own: 57 B against 16 + 45 with
  `rwts_sectors` (+4 B of resident RAM it does not have).
- **`initials.asm`** — `ini_key`: high-score initials entry, one key at a
  time (letters, ←/→ and DELETE, ↑/↓ cycle the letter, RETURN/ESC end:
  C = 1); `INI_LEN` (3), `INI_CHARS`/`INI_CHARS_N` (default A-Z without a
  table), `INI_DELETE`. The stick comes in through `stick_key` and a
  `STICK_KEYS` table of KC_* codes. 117 B. DIRTBIKE (hof.inc: its
  38-letter ring `hof_chars`, `ini_buf`/`ini_pos` = `last_ini`/`hpos`, its
  stick path through `stick_menu`; −15 B). Candidates: MICRO-SOKOBAN
  (score_hof.inc), ARKABREAKOUT (records.inc).
- **`tune.asm`** — `tune_start`/`tune_stop`/`tune_tick`/`tune_play`: one
  voice, one ~1/60 s tick per call (a `tone` slice, the note's last tick
  silent, rests through WAIT), events `.byte ticks, half_period, toggles`,
  0 = end; loops or plays once. `TUNE_MUTE` (a byte, 0 = notes silent,
  tempo kept), `TUNE_REST_WAIT` (79). 2 B ZP `tune_ptr`, 3 B BSS, 116 B.
  From DIRTBIKE's title.inc, which uses it (`TUNE_MUTE = snd_on`, byte for
  byte the same code). `dev/tools/audio/tune.py` encodes the events from
  note text; DIRTBIKE's `tools/music.py` keeps its songs.
- **`savehdr.asm`** — `magic_check` / `magic_put`: a save file's leading
  magic (A/Y = the data, X = the magic's last byte in the program's
  `MAGIC_TABLE`, `MAGIC_LEN` = 4) compared after a load (C = 0 equal) or
  written before a save; 24 + 19 B, a 9-byte site instead of 28 / 20.
  No user: MAZE3D tried it and went back (its score check runs from
  resident CODE before the overlay holding the other sites is loaded:
  +38 B of scarce main RAM).
- **`lz4fh.asm`** — `lz4fh_unpack`: fhpack/LZ4FH decompression into an aligned
  8 KB area (notably the HGR pages). Inputs `lz4fh_src/dst`, configurable
  scratch; code in RAM (`LZ4FH_HERE=1`: in the caller's current segment,
  an overlay, instead of `CODE`), stream validated at build time. A format error
  drops into the Monitor, as in the upstream decoder. Provenance and
  Apache-2.0 licence kept in `lz4fh-NOTICE.txt` / `lz4fh-LICENSE.txt`.
- **`dos.asm`** — `dos_cmd_*`, `disk_protected`: DOS 3.3 commands (BLOAD,
  BSAVE…) from a BRUN program; assumes `exit.asm`. Additions are
  bounded to `DOS_CMD_MAX-1` characters; the two hexadecimal digits are
  added together or rejected. An overflow returns carry=1 and prevents
  the partial command from running until the next `dos_cmd_new`.
  `DOS_SEI = 1` masks IRQs during `dos_cmd_run` (RWTS does not tolerate
  interrupts: programs that do `CLI`, the //c mouse). `disk_protected`
  reads the slot of DOS's last access from its IOB (`$B7E9`, 48 KB DOS).

`sound.asm`, `joy.asm` and `dos.asm` were taken out of MICRO-SOKOBAN so the other games (sounds,
joystick, saving in their `TODO.md`) share the same code; their C
mirror is in [`../apple2c/`](../apple2c/) (`apple2game.h`, `apple2dos.h`).

**Include after the callers.** The legacy primitives are wrapped in `.ifref`: a routine
is only assembled if the code preceding the include references it. Games
therefore put the `.include`s at the end of the source (LOGO too, which exports `wait_key` to
another module). A C object that aliases a routine to an import
(`hgr_init = _hgr_init`) skips it (`.ifndef`), see `../hgrc/hgr_mode_clear_asm.s`.

## Routines

| Routine | Module | Input | Output | Clobbers | ZP |
|---|---|---|---|---|---|
| `print_str_ax` | `print.asm` | A=lo, X=hi (ASCIIZ) | — | A, Y | `print_ptr_*` |
| `print_byte_dec` | `print_num.asm` | A = byte | "DDD" | A, X, Y | — |
| `wait_key` | `kbd.asm` | — | A = key & $7F, upper case | A | — |
| `poll_key` | `kbd.asm` | — | A = key or 0, Z updated | A | — |
| `kbd_upcase` | `kbd.asm` | A = key | A = upper case, Z/N updated | A | — |
| `delay_ms_a` | `delay.asm` | A = ms (0 → 256) | — | A, X, Y | — |
| `hgr_init` | `hgr.asm` | — | GRAPHICS + HIRES + PAGE1 + full screen | A | — |
| `hgr_init_clear` | `hgr.asm` | — | same, page 1 cleared before the switch (`HGR_CLEAR_ROUTINE` to replace it) | A, X, Y | — |
| `hgr_page1` / `hgr_page2` | `hgr.asm` | — | displayed page | A | — |
| `text_restore` | `hgr.asm` | — | TEXT + full screen + PAGE1 | A | — |
| `native_video` | `hgr.asm` | — | IIe/IIc (ROM `$FBB3` = `$06`): RAMRD/RAMWRT main, 80STORE, 80COL and DHGR off; called by `hgr_init`, `hgr_init_clear` and `text_restore` | A | — |
| `apple2_zp_save` | `exit.asm` | — | copies $00-$FF (256 B of BSS, or `apple2_zp_buf` defined by the program before the include), RESET → `apple2_exit` | A, X | — |
| `apple2_exit` | `exit.asm` | — | RESET vector and ZP restored (text window and cursor `$20-$29` kept), text screen, `JMP $03D0` | all | — |
| `apple2_return` | `exit.asm` | — | same restore, then `RTS` to the BASIC `CALL` (program launched by `BLOAD` + `CALL`) | all | — |
| `tone` | `sound.asm` | A = toggles (0 → 256), X = half-period (0 → 256); 12 + 5·X cycles per toggle, pitch 1.02 MHz / (2·(12 + 5·X)): ~2.4 kHz at `$28`, ~526 Hz at `$C0`, ~397 Hz at `$FF` | — | A, X, Y | — |
| `read_stick` | `joy.asm` | — | `joy_x`, `joy_y` = 0 (left / up) … ~60 (centre) … ~120; ~6 ms; an open axis (timer never finishes) is centred at 60; C = 1 if both are (nothing plugged in) | A, X, Y | — |
| `read_stick_fast` | `joy.asm` | — | `joy_x`, `joy_y` = counts of 35 cycles (33-34 once the other axis has finished), ~40 at centre; stops as soon as both timers have finished; C = 1 after 255 passes (nothing plugged in) | A, X, Y | — |
| `vapor_mark` | `vapor.asm` | — | `VAPOR_BYTE` ($80) in the first 24 bytes of HGR line 191 (page `VAPOR_PAGE`, 1) | A, X | — |
| `vapor_sync` | `vapor.asm` | marker on the shown page, HGR on | C = 0: the beam is on line 191 (VBL next); C = 1 after 65536 polls (~0.8 s): no floating bus or no marker | A, X, Y | — |
| `vapor_count` | `vapor.asm` | same | A = low, X = high: one frame in 13-cycle polls (~1303 NTSC, ~1553 PAL at 1 MHz); C = 1, 0 on failure | A, X, Y | — |
| `stick_dir` | `joy.asm` | `joy_x`, `joy_y` | A = `JOY_NONE` (0, Z = 1) / `JOY_UP` / `JOY_DOWN` / `JOY_LEFT` / `JOY_RIGHT`; dead zone `JOY_LO`–`JOY_HI` (30–90, define before the include to change it); vertical wins | A | — |
| `stick_key` | `joy.asm` | `STICK_KEYS` (optional 6-byte table: UP, DOWN, LEFT, RIGHT, B0, B1) | one-shot events: X = 1..4 (`stick_dir`), 5 = button 0, 6 = button 1, each on its own edge (a press; a change to a non-centre direction, so releasing a button under a held direction fires nothing); button 0 > button 1 > direction, the loser fires on the next call; A = `STICK_KEYS[X-1]` (A = X without a table), or A = 0 / Z = 1 when nothing new; no stick (C = 1 from the reader): no button read. State `stick_key_last` (1 B, zero it at start) + `stick_key_btn` (2 B, no init needed), BSS or caller's ZP. 50 B with the table + `read_stick` + `stick_dir`; `STICK_KEY_FAST` (`read_stick_fast`), `STICK_KEY_REPEAT = n` (held direction every n calls, +20 B, +1 B BSS): chess | A, X, Y | — |
| `joy_buttons` | `joy.asm` | — | A = buttons held (bit 0 = 0, bit 1 = 1, Z from A), X = newly pressed; state `joy_btn_last` (1 B); 25 B; reads the buttons even without a stick | A, X, Y | — |
| `dos_cmd_new` | `dos.asm` | — | command buffer emptied | A | — |
| `dos_cmd_add` | `dos.asm` | A = lo, Y = hi (ASCIIZ) | string appended | A, X, Y | — |
| `dos_cmd_hex` | `dos.asm` | A = byte | two hexadecimal digits appended | A, X | — |
| `dos_cmd_run` | `dos.asm` | buffer | DOS runs the command, with DOS's zero page put back meanwhile | all | — |
| `dos_cmd_line` | `dos.asm` | A = lo, Y = hi (ASCIIZ) | `dos_cmd_new` + `dos_cmd_add` + `dos_cmd_run` (8 B, `.ifref`; a 7-byte site instead of 13): arkabreakout, maze3d | all | — |
| `disk_protected` | `dos.asm` | — | C = 1 if the disk of DOS's last access is write-protected (slot × 16 read from DOS's IOB, `$B7E9`) | A, X | — |

## apple2.inc — public symbols

| Symbol | Address | Role |
|---|---|---|
| `KBD` / `KBDSTRB` | `$C000` / `$C010` | keyboard latch (bit 7 = key) / acknowledge |
| `SPKR` | `$C030` | speaker |
| `TXTCLR` `TXTSET` | `$C050` `$C051` | graphics / text |
| `MIXCLR` `MIXSET` | `$C052` `$C053` | full screen / 4 lines of text |
| `LOWSCR` `HISCR` | `$C054` `$C055` | page 1 / page 2 |
| `LORES` `HIRES` | `$C056` `$C057` | low / high resolution |
| `BUTN0-2`, `PADDL0-1`, `PTRIG` | `$C061-$C070` | joystick |
| `TEXT1` `HGR1` `HGR2` | `$0400` `$2000` `$4000` | video memory |
| `COUT` `CROUT` `PRBYTE` `PRHEX` | `$FDED` `$FD8E` `$FDDA` `$FDE3` | Monitor output |
| `HOME` `VTAB` `RDKEY` `BELL` `WAIT` `SETTXT` | … | other Monitor routines |
| `CH` `CV` | `$24` `$25` | text cursor |
| `DOSWARM` `SOFTEV` | `$03D0` `$03F2` | return to DOS / RESET vector |
| `STORE80OFF/ON` `RAMRDOFF` `RAMWRTOFF` `COL80OFF/ON` `DHIRES_ON/OFF` | `$C000-$C00D`, `$C05E-$C05F` | IIe/IIc switches (DHGR, `native_video`) |
| `KC_LEFT` `KC_RIGHT` `KC_UP` `KC_DOWN` `KC_RET` `KC_ESC` `KC_SPACE` | 7 bits | codes returned by `kbd.asm` |

The key codes have the `KC_` prefix on purpose: games often have their
own `KEY_*`.

## Zero page

On the Apple II, the zero page belongs to the Monitor (`$20-$4F`), DOS and Applesoft (`$50-$FF`): the
pool simply occupies the start of the ZEROPAGE segment, which
`dev/cc65/apple2_hgr.cfg` places at `$50`. COUT, HOME and RDKEY therefore keep
working. A program that returns to DOS calls `apple2_zp_save` first
thing, and exits through `apple2_exit`. In between, Ctrl-RESET also goes through
`apple2_exit`: otherwise DOS would take over with the game's zero page,
including on Applesoft's CHRGET routine (`$B1-$C8`).

## Sound, joystick, DOS

```asm
        LDA #$30                ; short high beep: $30 toggles, period $28
        LDX #$28
        JSR tone

        JSR read_stick          ; joystick -> joy_x / joy_y
        JSR stick_dir           ; A = JOY_UP.. or 0
        BEQ @centre
        LDA BUTN0               ; button 0: bit 7 = 1 while it is held down
        BMI @feu

        JSR dos_cmd_new         ; "BSAVE SCORE,A$1000,L$04"
        LDA #<str_bsave         ; .byte "BSAVE SCORE,A$1000,L$", 0
        LDY #>str_bsave
        JSR dos_cmd_add
        LDA #$04
        JSR dos_cmd_hex         ; appends "04"
        JSR disk_protected      ; write-protected disk: DOS would stop the game
        BCS @pas_de_sauvegarde  ; on WRITE PROTECTED, so skip
        JSR dos_cmd_run
```

During `dos_cmd_run`, DOS gets back the zero page saved at startup by
`apple2_zp_save` (mandatory before the first command); the program's own
is set aside in 256 bytes of BSS and then put back. A program that
uses only a range of the zero page can define `DOS_ZP_START` and
`DOS_ZP_LEN` before the include: only that range is then saved for
the program, while DOS always keeps its full snapshot. The length must
be 1 to 256 and the range must stay within `$00–$FF`; the assembler rejects
invalid configurations. A DOS error (missing
file…) stops the program at the prompt: the `Makefile` puts every file read
on the disk, and `disk_protected` is tested before writing. MICRO-SOKOBAN
uses this for its level packs (`BLOAD`), `MICROSAVE` and `MICROHOF`.

`DOS_CMD_MAX` sets the size of the command buffer (40 bytes by default).
`dos_cmd_run` keeps the buffer and its length: the command can be repeated,
or text and hexadecimal digits appended to it after it has run.
With `DOS_CMD_WORKBSS = 1`, this buffer and its index live in the program's
`WORKBSS` segment rather than `BSS`, to free up room next to the code.
With `DOS_LOWBSS = 1`, the buffer and the page-zero copy (`DOS_ZP_LEN`
bytes, 256 by default) go to `LOWBSS` (`$1000-$1FFF` in
`dev/cc65/apple2_hgr_c.cfg`): SNAKE sets it (`HGRC_AFLAGS += -D DOS_LOWBSS=1`)
because its `$6000` area is full. Default 0: `BSS`, binaries unchanged.

## Example

```asm
.include "apple2.inc"
.include "zp.inc"

.segment "CODE"
main:   APPLE2_PREAMBLE
        JSR apple2_zp_save
        LDA TXTSET
        JSR HOME
        LDA #<msg
        LDX #>msg
        JSR print_str_ax
        JSR wait_key
        JMP apple2_exit

msg:    .byte "HELLO!", $0D, 0

.include "print.asm"
.include "kbd.asm"
.include "exit.asm"
```

    ca65 -t none -I dev/lib/apple2 -o hello.o hello.s
    ld65 -C dev/cc65/apple2_hgr.cfg -o hello.bin hello.o      # BRUN at $6000
    python3 dev/tools/dos33.py --master dos33_master.dsk --out HELLO.dsk \
        --bas HELLO=hello.bas --bin HELLOBIN=hello.bin@0x6000

Full example: [`../../examples/hello`](../../examples/hello).

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).

## Vapor lock: frame sync on a II / II+

The II and II+ have no VBL flag, and the //e's `$C019` is not on a //c or a
IIgs the same way. But a soft switch that drives no data (`$C050-$C05F`)
reads back the **floating bus**: the byte the video scanner fetched on that
cycle. `vapor.asm` puts a marker in HGR line 191 and polls `TXTCLR` until the
beam reads it: one lock a frame, on the last line shown, within one 13-cycle
poll (2026-10-24, from SNAKE; `dev/tests/test_vapor.py`).

- **Where the marker goes.** The scanner also fetches memory in blanking
  (MAME's `scanner_address`): the horizontal blanking of lines 255 and 261
  (in VBL; 311 on PAL) reads bytes 16-39 of line 191, that of line 63 its
  bytes 24-39. So only bytes 0-23 carry the marker, and two reads 9 cycles
  apart must both see it: on line 191 they always do, in those blankings the
  second falls past it, and a lone `$80` elsewhere cannot fake a lock. Mark
  the shown page again after each clear; draw nothing in `$3FD0-$3FE7`.
- **The poll is 13 cycles at most**: a 17-cycle one (a first counting loop)
  missed one frame in eight, its first hit too late for the second read.
- **PAL and accelerators.** `vapor_count` measures a frame in polls: ~1303 on
  a 1 MHz NTSC machine, ~1553 on PAL (20280-cycle frames, ratio 1.19), several
  times more with an accelerator card. A program can tell 50 Hz from 60 (a
  ratio of 1.1-1.3) and keep the same pace in seconds.
- **No floating bus** (//c, IIgs) or no marker: `vapor_sync` gives up after
  65536 polls, long enough for an accelerated frame; test once at start and
  keep another pace (SNAKE falls back to its spin loop).
- **Checked on** a2run (which now emulates the floating bus, NTSC) and POM2
  (II+ NTSC and PAL, enhanced //e): a lock every 17030 / 20280 cycles, at the
  same point of the frame within 6 cycles.

## RGB Le Chat Mauve / Video-7

[`rgb.asm`](rgb.asm), extracted from A2FileCmd's video routines, arms the
COL140 register with two AN3 pulses while 80COL is 1. The routines are self-contained,
with no zero page and no framebuffer copy; include them after the callers.

- `rgb_col140`: on IIe/c, arms COL140 and DHGR without changing the displayed page,
  the text/graphics mode, MIXED or the RAM banks. Call it after the
  existing DHGR initialisation. Returns A=1, X=0; on II/II+, A=0 and no
  switch is touched.
- `rgb_hgr`: HGR page 1, full screen, main banks on IIe/c.
  Also works on II/II+. Does not clear the screen.
- `rgb_dhgr`: colour DHGR page 1, full screen, main banks,
  80STORE off. The caller checks that extended auxiliary RAM is present
  before this call. On II/II+, returns A=0 without changing the video.

The mode entry points return A=1, X=0 on success. All of them clobber A and
X; Y and the IRQ mask are preserved. Code and stack must be in the main
bank. Program the RGB register on entering the mode, without repeating the
pulses on page or MIXED changes. Exit to text
is still handled by `text_restore` / `dhgr_text_restore`.

## Mockingboard: two AYs and a polled timer

[`mockingboard.asm`](mockingboard.asm) extracts A2FileCmd's card detection and
AY access (`src/mb_probe.s`, helpers from `src/plugins/duet.s`).
It uses only 6502 instructions, three zero-page bytes
(`mb_ptr`, `mb_probe_old`, each of which can be aliased), and a small resident state.
It depends neither on the file manager nor on a music player.

| Entry | Contract |
|---|---|
| `mb_detect` | Searches slots 7..1, except 3; initialises both AYs; A=slot or 0. |
| `mb_init` | A=slot 1..7 except 3; initialises the VIA directions and resets both AYs; A=slot, or 0 if invalid. |
| `mb_write` | X=AY register 0..15, A=value; `mb_chip` selects the first (0) or second (1) chip. |
| `mb_silence` | Sets the three volumes to zero on both AYs; keeps `mb_chip`. |
| `mb_timer_start` | A=low byte, X=high byte of the T1 reload value. Free-running timer, T1 IRQ masked. |
| `mb_tick` | A=1 if an expiry is observed and acknowledged; otherwise A=0. Never blocks. |
| `mb_stop` | Silences the six voices, disables polling, restores the saved ACR and T1 IRQ enable bit. |

Option `MB_FAST_WRITE = 1` (define it before the include; default 0, byte-identical
to the code without the option): `mb_write` stores to absolute `$Cn00`/`$Cn01`
(`$Cn80`/`$Cn81`) operands that `mb_init` patches for the slot, instead of
rebuilding `mb_ptr` and storing through it: about 55 cycles a write instead of
about 110, same contract. WARGALAGA II uses it (music and effects every
frame); `dev/tests/test_rgb_mockingboard.py` runs its Mockingboard checks on
both variants.

`mb_init` selects the first chip. Operations before initialisation or
after a detection that found no card are harmless. A register outside 0..15 is
ignored. Return values are tested in A (`CMP #0`), without assuming the
state of the Z flag. Every entry point may clobber A/X/Y; the hardware
transactions preserve the IRQ mask. Call with D=0, main code/stack/ZP
and ROM visible. No language card or auxiliary bank switching is done.

The program must own both AYs and the first VIA's T1 timer:
no other player or IRQ handler may use them at the same time.
A new detection or an initialisation with a valid slot automatically
restores the previous timer and silences its voices before starting again.
An invalid slot keeps the current session. Call `mb_stop` before
quitting. The timer's previous counter and period are not restored;
missed expiries are merged in the IFR flag. The other
IER bits are not changed by the polling service.

On //c, detection wakes the Mockingboard 4c at `$C403`. This wake-up can
hide the slot 4 mouse ROM: detect the Mockingboard **before** initialising
the mouse. The module provides the hardware access; no PT3 player is linked.

```asm
        JSR mb_detect
        CMP #0
        BEQ sans_carte
        LDX #7                  ; mixer: tone channels on, noise off
        LDA #$38
        JSR mb_write
        LDX #8                  ; voice A volume
        LDA #8
        JSR mb_write
        ; Also program voice A's period registers 0/1.
        ; ...
        JSR mb_stop             ; before handing control back
sans_carte:
        ; ...
.include "mockingboard.asm"
```

`make test-hardware` runs the ASM modules on the 6502 core with a simulated
RGB/VIA/AY bus and traces the accesses: RGB pulse order,
II+/IIe/IIc paths, slots, no card, 4c wake-up, two AYs, six volumes,
IRQ mask and timer state. Tests on physical cards are still to be done.

## Mockingboard music service (`mb_irq.asm`)

[`mb_irq.asm`](mb_irq.asm) (2026-10-31, extracted from WARGALAGA II's
`src/sound.s`, which stays byte-identical) calls the program's tick routine
on the interrupt of the first VIA's timer 1, free running at `MB_IRQ_HZ`:
the music keeps its tempo whatever the frame rate. It needs
`mockingboard.asm` (anywhere in the program). `.ifref` routines, included
after the callers; several includes are fine (each assembles what was
referenced before it: WG includes it four times so every routine stays
where it was). 65C02 or NMOS: the CPU the source is assembled for picks
the instructions. A music program's ProDOS / DOS choice is an option.

| Entry | Contract |
|---|---|
| `mb_irq_start` | Card required (`mb_detect` ≠ 0), after `mb_forget`. Patches the handler for `mb_irq_slot`, hooks the interrupt (ProDOS `ALLOC_INTERRUPT`, or the vector at `MB_IRQ_VECTOR`, the old one kept for the chain), T1 free running at `MB_IRQ_PERIOD`, its IRQ enabled, `CLI`. `mb_irq_n` ≠ 0 = installed (ProDOS: the interrupt number; 0: the MLI refused, timer left off). `mb_irq_rts` is its final `RTS`. |
| `mb_irq_stop` | Both chips silent, T1 and its interrupt off (`mb_stop`), the interrupt released (`DEALLOC_INTERRUPT` / the old vector back). Harmless if never started. |
| `mb_put` | X = register 0..15, A = value, `mb_chip` = chip: written only if `mb_shadow` differs. Keeps X. |
| `mb_forget` | Every shadow `$FF`: the next `mb_put` of each register writes. |
| `mb_hush` | If `mb_irq_slot` ≠ 0, under SEI: chip 1's three volumes to 0 and its shadows forgotten (both chips with `MB_IRQ_HUSH_BOTH`). Before disk I/O: ProDOS's Disk II driver masks interrupts ~1 s, a note would hang. |
| `mb_irq_handler` | The interrupt routine: `CLD`; not timer 1 → not ours (ProDOS `SEC`/`RTS`, vector: on to the old vector); else T1 acknowledged, [`jsr _a2_vbl_scan`], `inc mb_irq_ticks`, [nothing more if the `MB_IRQ_GATE` byte is 0], `mb_chip` saved, the tick, `mb_chip` restored, [`_a2_vbl_scan`]. |

Tick modes: by default `mb_chip = 0`, then `jsr MB_IRQ_TICK`, which writes
what it wants (`mb_put`, either chip). With `MB_IRQ_FRAME = addr` the
handler calls the tick, then flushes the 14-byte frame at `addr` to chip 1
through the shadows inline (R13 whenever it is not `$FF`: PT3's frame in
WG). The handler owns the chip(s) its tick writes; the main program writes
only the other one (`mb_write` masks interrupts, `mb_chip` is restored).

Options (before the first include): `MB_IRQ_PRODOS` (1 default; 0 = own
vector), `MB_IRQ_VECTOR` (`$03FE` default: the ROM's handler saved A at
`$45`, the handler keeps X/Y and returns with `LDA $45`/`RTI`; or `$FFFE`
with the language card's RAM banked in: raw entry, A/X/Y saved; the program
enables LC writes around `mb_irq_start`/`mb_irq_stop`), `MB_IRQ_HZ` (50) /
`MB_IRQ_PERIOD` (latch, default `1020484 / MB_IRQ_HZ - 2`), `MB_IRQ_TICK`
(required), `MB_IRQ_FRAME`, `MB_IRQ_GATE`, `MB_IRQ_SCAN`,
`MB_IRQ_HUSH_BOTH`, `MB_IRQ_SPLIT` (the handler only where the program
references `mb_irq_handler`). Storage, aliased if defined first: `mb_shadow`
(32 B: chip 1 at 0..15, chip 2 at 16..31), `mb_irq_n`, `mb_irq_ticks` (not
cleared: BSS), `mb_irq_old` (vector mode), `mb_irq_ptr` (2 ZP: `mb_ptr` if
mockingboard.asm came first), `mb_irq_slot` (default `mb_slot`). Code, hook
mode: 169 B (ProDOS, 65C02) to 203 B (vector, NMOS); handler overhead ~60
cycles + the tick.

```asm
MB_IRQ_PRODOS = 0               ; a DOS 3.3 program: the $03FE vector
MB_IRQ_TICK = ays_tick          ; the song player below
        jsr mb_detect
        cmp #0
        beq no_card
        jsr mb_forget
        lda #<song
        ldy #>song
        jsr ays_init
        jsr mb_irq_start        ; 50 ticks a second from here
        ...
        jsr mb_hush             ; before a disk access
        ...
        jsr mb_irq_stop         ; before quitting
.include "mb_irq.asm"           ; first: aysong.asm then writes through mb_shadow
.include "aysong.asm"
.include "mockingboard.asm"
```

`dev/tests/test_mb_irq.py` (a2shot, Mockingboard in slot 4): 60 ticks at
50 Hz, the AY writes decoded from the VIA stores, registers kept across the
interrupts, the stop, the vector given back, `mb_hush`; `$03FE` on the //e
(NMOS and 65C02 builds) and the //c (Mockingboard 4c), `$FFFE` on the //e
and the II+ (a2shot's II+ ROM sends IRQs to the monitor, `$FF59`, so the
`$03FE` path is not testable there); then the AYS demo played by `ays_tick`
under the interrupt, its AY bus writes equal to the Python model's. The
ProDOS mode is WARGALAGA II's (`make -C wargalagaii test`).

## AYS song player (`aysong.asm`)

[`aysong.asm`](aysong.asm) plays an AYS song ([AYSONG_FORMAT.md](AYSONG_FORMAT.md));
`dev/tools/audio/aysong.py` encodes songs (text, JSON or dataclasses; `--asm`
for `.byte` tables) and its `Player.tick()` gives the same registers tick
for tick. NMOS 6502 (`AYSONG_CPU65C02 = 1`: a few 65C02 forms). `.ifref`,
include after the callers, after `mb_irq.asm` if the program has it.

| Entry | Contract |
|---|---|
| `ays_init` | A/Y = song (low/high). Registers reset (0, R7 = `$3F`, R13 = `$FF`), every voice off with instrument 1, mute 0, order 0 row 0. Call with the tick stopped or under SEI. |
| `ays_tick` | One tick: the row when due, effects, instrument macros, the frame in `ays_regs` (chip 1 at 0..13, chip 2 at 16..29), then the registers that differ from `ays_out` through `AYSONG_WRITE` (R13 when not `$FF`). |
| `ays_stop` | Every voice off, no more rows (the next ticks write silence). |
| `ays_mute` | A = mask, bit v = voice v silent (volume 0; it keeps playing). |
| `ays_pos` | A = order index, X = the next row to be read. |
| `ays_set_pos` | A = order index, X = row (masks interrupts itself): voices off until their next note, the rows before skipped (instrument prefixes kept); the next tick reads the row. Also a restart after `ays_stop`. |

All clobber A/X/Y; D = 0; one song at a time. Options: `AYSONG_VOICES`
(3 default: one chip; 6: both chips; a 6-voice song under a
3-voice player plays its first chip), `AYSONG_CPU65C02`,
`AYSONG_FAST_PERIODS` (a 96-note period table, 192 B, instead of the 12-note
table and shifts with a per-voice cache: ~25 cycles less a tick on average,
~230 at note starts), `AYSONG_WRITE` (a macro: X = register, A = value,
Y = chip; keep X; default `sty mb_chip`/`jsr mb_write`). Zero page: 5 bytes
at `ays_zp` (define it first to place them). BSS: `ays_regs` and `ays_out`
16 B a chip (`ays_out` = `mb_shadow` when `mb_irq.asm` came first, so
`mb_hush` / `mb_forget` make the player write again), 22 B of song state,
19 B a voice (16 with the fast periods).

Measured (`dev/tests/test_aysong.py`, a2run, `mb_write` to a card with
`MB_FAST_WRITE`): code + tables 1,091 B (3 voices; 1,169 B for 6; 65C02 −4
B; fast periods +112 B). Cycles a tick, 3 voices (demo): mean ~1,320,
~950 without writes, ~90 a register written; the worst row ticks (a new
pattern, three notes, ten writes) ~3,600 (fast periods: ~3,370); 6 voices:
mean ~1,190, worst ~5,300. The first tick after `ays_init` / `mb_hush`
writes all 13 registers (~1,200 cycles of writes).

MB TRACKER builds it with `AYSONG_VOICES = 6`, `AYSONG_CPU65C02 = 1` and
`mb_irq.asm`'s `MB_IRQ_HUSH_BOTH = 1`: its interrupt tick measured in the
tracker (`mbtracker/tests/test_mbt.py`, a 6-voice song) costs 5,309 cycles
on the first tick (both chips written), then at most ~3,400, mean ~1,900.
PT3 modules convert to AYS with `dev/tools/audio/pt3import.py` (what maps,
what is reported lost: its docstring; `dev/tests/test_pt3_import.py` checks
`pt3play.py`, its Python PT3 player, against `pt3/` under a2run).

## PT3 decoder: `pt3/` (WARGALAGA II, 2026-10-23)

[`pt3/pt3.s`](pt3/pt3.s) is Vince Weaver's pt3_lib 0.5 decoder, used under
its 0BSD option ([`pt3/pt3_lib-NOTICE.txt`](pt3/pt3_lib-NOTICE.txt): upstream
revision, what changed). `pt3_lib_core.s` and `pt3_lib_init.s` are unchanged;
`pt3_zp.inc` puts its 32 zero-page bytes at `PT3_ZP` (outside ProDOS's
`$FA-$FF`); `pt3.s` keeps decoding only: `pt3_init_song`, then `pt3_tick`
fills `AY_REGISTERS..+13` for one AY (R13 `$FF` = unchanged) and loops.
No IRQ installation, slot patching or AY writes: the program owns those
(the policy below). The 1.77 MHz conversion is off unless
`PT3_FREQ_CONVERSION = 1`. Include it from a module of its own (its labels
are many). Size: ~1.7 KB code, 448 bytes of tables, ~570 bytes of init.
Measured in WARGALAGA II: 1 450-2 400 cycles a tick (mean 1 570) for a
two-voice song. That game links it with its song for aux `$6000` and calls
it through bank-switching trampolines from its timer 1 handler
(`wargalagaii/src/music.s`, `sound.s`).

## PT3 extension: feasibility and proposed scope (2026-10-22 notes)

PT3 music support can be added as an optional module, at no cost
to games that do not link it. The hardware is already covered by
`mockingboard.asm`; the decoder is now `pt3/` (above).
The preferred base, after examining A2FileCmd, is its **corrected ca65 port
of the GROUiK / French Touch player** (`src/plugins/ppt3/`), a translation of
S.V. Bulba's ZX player with Ivan Roshin's table generators,
published under GPL-3.0-or-later. A2FileCmd keeps the ACME original, tests
the identity of the unadapted port, separates decoding from AY writes and adds
checks on reads, stack, command stream duration as well as
frequency corrections. Its documented report compares 400 songs
over 3,000 ticks: 394 give the same registers as its corrected pt3_lib,
with six explained differences; this result does not demonstrate a CPU gain.

Do not copy its AUX driver as is: its trampoline forces LORES, masks
IRQs during decoding and puts the engine at AUX `$2000` and the song at
AUX `$4000`. Those areas belong to our games' DHGR pages. Plan a
main RAM placement or an AUX one outside video, move the constants and measure
the cost of the protections. Its current image costs 4,813 bytes plus 613
bytes of variables/tables, excluding song and driver. This makes the choice of
GROUiK relevant for reusing the already-tested adaptation, without presuming
that it is smaller or faster. Vince Weaver remains an alternative.

[Vince Weaver's player](https://github.com/deater/dos33fsprogs/tree/1871fc43b57cc8cf4b2353ae115d0ca84a1a33ea/music/pt3_lib)
is a ca65/6502 base: its decoder produces the AY registers separately
from writing them to the hardware. Its licence offers 0BSD or GPL-2.0-only;
choose the 0BSD option for an adaptation in this GPL-3.0 repository.

Proposed architecture: a singleton decoder with initialisation of a
resident song, decoding of one tick, pause/resume, loop and stop; cc65
wrappers; then an AY output using the existing backend. The
envelope register R13 must not be rewritten when the decoder returns `$FF`:
that marker keeps the current envelope. The upstream player duplicates three
voices across the two AYs; this does not provide six independent voices.

The [upstream README](https://github.com/deater/dos33fsprogs/blob/1871fc43b57cc8cf4b2353ae115d0ca84a1a33ea/music/pt3_lib/README.pt3_lib)
claims about 3 KB plus the song, 26 ZP bytes and typically 10–15 %
of the CPU at 50 Hz. These are upstream estimates, not measurements in our games.
It requires a song aligned on 256 bytes and contains self-modifying code.
Its fixed ZP addresses will have to become ld65 allocations; its compiled
song address will have to be adapted to the chosen API. The conversion of
Spectrum/Mockingboard AY frequencies and the music timing must be
explicit: a 50 Hz music tick must not depend on the game's FPS.

Keep IRQs under the application's responsibility, like the existing
frame pacing. Do not import the upstream player's IRQ installation, slot patches or
//c ROM workarounds. `mb_tick` polling can serve
a first example, but merges missed expiries. For steady
music in game, the player will have to use dedicated scratch,
preserve the interrupted context and share the timers with frame pacing and
the mouse according to an explicit policy. Graphics calls stay out of IRQs.

Before integrating into a game: measure the maximum cycles per tick, the ZP,
both stacks and the song's place in the ld65 map; compare the AY
frames against a reference and test end/loop/pause, R13, no card, DOS/ProDOS
exit and interrupts during DHGR rendering. The current
`test_game_cadence.py` test validates a simple AY service during play, without
demonstrating the CPU budget of a PT3 decoder. Start with a standalone
II+/IIe example before choosing a game and adding the //c path.

## Auxiliary memory (`auxmem.asm`)

128 KB //e / //c, 65C02. Include it after the callers (`.ifref`), in the
segment the code goes in; it can be included again (another segment, or
first at the top of the source for the `AUXMOVE` macro): each routine is
assembled once, where it is first both referenced and not yet defined.
Entry: main RAMRD/RAMWRT, main zero page and stack (ALTZP off), 80STORE
off; exit the same, the I flag restored. Not for an IRQ handler.

| Routine | Input | Effect | Cost |
|---|---|---|---|
| `aux_store` | A = pages (0 = 256), X = first aux page, Y = first main page | main → aux, RAMWRT aux, interrupts masked for the whole copy | 35 B; ~14 cycles a byte; ZP `auxmem_src`/`auxmem_dst` (2+2, define them first to alias) |
| `aux_fetch_pages` | A = pages, X = first aux page, Y = first main page | aux → main; RAMRD aux hides the code in main RAM, so the page loop runs from a 16-byte stub copied to the zero page at each call (`auxmem_zcopy`); interrupts masked one page at a time (~3,600 cycles) | 36 B + 16 B template; 16 ZP bytes (`AUXMEM_ZP = addr` to place/alias them) |
| `aux_fetch_chunked` | A/Y = aux source (low/high); `auxmem_fdst`, `auxmem_flen` | aux → main any length through the ROM's AUXMOVE (`$C311`), `AUXMEM_FETCH_CHUNK` bytes (64) at a time under SEI; `AUXMEM_FETCH_SCAN = 1`: `jsr _a2_vbl_scan` between chunks | 109 B (112 with the scan); ~36 cycles a byte; consumes `auxmem_fdst`/`auxmem_flen`, scratch `auxmem_fsrc` (2) and `auxmem_fn` (1), BSS unless defined first |
| `AUXMOVE first, last, dest, dir [, jmp]` | constants or labels; `dir` = `AUX_TO_MAIN` / `MAIN_TO_AUX` | macro: the ROM's AUXMOVE of first..last (inclusive) to dest; `jmp` = tail call | 28 B (`$3C-$3F`, `$42/$43`); the ROM leaves I alone |

C: `apple2aux.h` (dev/lib/apple2c): `aux_store(pages, aux_page)` (a macro
over `aux_store_packed(pages | aux_page << 8)`: one argument in A/X, no C
stack) from the main page `aux_store_src` (`$20` at first), in
`$(APPLE2C_AUX_SRCS)` (`apple2aux.s`, on cc65's `ptr1`/`ptr2`), and
`aux_fetch_pages(pages, aux_page, main_page)` in `$(APPLE2C_AUXFETCH_SRCS)`
(`apple2auxfetch.s`; its C entry costs 9 B, assembly callers `jsr
aux_fetch_pages` directly). Make both objects depend on
`$(APPLE2C_AUX_DEPS)`. ProDOS files go straight into aux with
`prodos_load_aux` (dev/lib/prodos, on `aux_store`).

Users: ROBOT SPACE STATION (`aux_store` for the text bank and the overlays at
boot, `aux_fetch_pages` for its overlay switches: `src/overlay.s`, 11 B),
WARGALAGA II (`AUXMOVE` ×3, `aux_fetch_chunked` with `AUXMEM_FETCH_SCAN = 1`
as its `aux_fetch`, included in place so that `pack_check` falls into it:
byte-identical; `aux_store` under `prodos_load_aux` at boot).
`dev/tests/test_prodos_file.py` (`make test-tools`) runs `aux_store` (via
`prodos_load_aux`), `aux_fetch_pages`, `aux_fetch_chunked` and `AUXMOVE`
on an enhanced //e.

### Pattern: an aux trampoline at the same address in both banks

Code that must run with RAMRD/RAMWRT aux for a while (a player whose song
and code live in aux, called from an IRQ) can be entered through a short
trampoline copied to the **same address in main and aux** (WARGALAGA II,
`src/sound.s`: `tramp_install` puts its `TRAMP` segment at `$1FE0` of both
banks, AUXMOVE main → aux after a main copy):

```asm
tr_tick:
        sta $C005                ; RAMWRT aux
        sta $C003                ; RAMRD aux: the next fetch comes from the
        jsr pt3_tick             ; aux copy, the same bytes, so it goes on
        sta $C002                ; RAMRD main (the next fetch: main again,
        sta $C004                ; the same bytes)
        rts
```

Switching RAMRD swaps the bytes under the PC; since both copies are equal,
execution continues seamlessly. Rules: interrupts masked (or the caller is
the IRQ handler) while the banks are switched; zero page and stack stay
main (no ALTZP), so the aux code can use them; the called code and its data
live in aux at their run addresses; the trampoline's bytes must be
identical in both banks (install it again after anything overwrites
either copy). This is a pattern to
copy, not a library routine: its address, the entries and the ZP are the
program's.
