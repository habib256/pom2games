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
- **`duet.asm`** — two voices on the speaker (time sharing, 33 cycles
  per pass, self-modified counts), assembled under `.org DUET_BASE` in its
  own page: `DUET_PLAY` (A = melody, X = bass, Y = slices),
  `DUET_KEYS`, `DUET_SLICE`. ARKABREAKOUT ($1300) and CHROMABREAK ($0310).
- **`joy.asm`** — `read_stick`, `stick_dir`: joystick (two paddles);
  `read_stick_fast` (DIRTBIKE) returns as soon as both timers have
  run out (0.1-2.8 ms instead of 6 ms), on its own scale (~0..80, centre
  ~40): calibrate on the rest position. `joy_x`/`joy_y`/`joy_cnt` may
  be zero-page aliases.
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
  and MICRO-SOKOBAN.
- **`lz4fh.asm`** — `lz4fh_unpack`: fhpack/LZ4FH decompression into an aligned
  8 KB area (notably the HGR pages). Inputs `lz4fh_src/dst`, configurable
  scratch; code in RAM, stream validated at build time. A format error
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
| `stick_dir` | `joy.asm` | `joy_x`, `joy_y` | A = `JOY_NONE` (0, Z = 1) / `JOY_UP` / `JOY_DOWN` / `JOY_LEFT` / `JOY_RIGHT`; dead zone `JOY_LO`–`JOY_HI` (30–90, define before the include to change it); vertical wins | A | — |
| `dos_cmd_new` | `dos.asm` | — | command buffer emptied | A | — |
| `dos_cmd_add` | `dos.asm` | A = lo, Y = hi (ASCIIZ) | string appended | A, X, Y | — |
| `dos_cmd_hex` | `dos.asm` | A = byte | two hexadecimal digits appended | A, X | — |
| `dos_cmd_run` | `dos.asm` | buffer | DOS runs the command, with DOS's zero page put back meanwhile | all | — |
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

## PT3 extension: feasibility and proposed scope

PT3 music support can be added as an optional module, at no cost
to games that do not link it. The hardware is already covered by
`mockingboard.asm`, but **the repository does not contain a PT3 decoder yet**.
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
