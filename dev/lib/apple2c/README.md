# lib/apple2c — Apple II text + keyboard for C (cc65)

*[← dev](../../README.md)*

Text/keyboard base for Apple II C programs, independent of the graphics
mode. Output goes through COUT (`$FDED`) on the text page, input reads the keyboard latch
(`$C000`, acknowledged by `$C010`). The asm mirror is [`../apple2/`](../apple2/).

## Files

| File | Role |
|---|---|
| `apple2io.h` | the API (or `apple2c.h`) |
| `apple2io_asm.s` | the routines that call the ROM or read the keyboard |
| `apple2io_str.s` | `a2_puts`, `a2_print_hexword` |
| `apple2frame.h` + `apple2frame.s` | optional frame pacing: IIe VBL, bounded fallback delay |
| `apple2vbl.h` + `apple2vbl.s` (+ `apple2vbl_pal.s`) | ProDOS video clock: IIe VBL polling or IIc mouse VBL interrupt (CHROMABREAK, WARGALAGA II) |
| `apple2aux.h` + `apple2aux.s` / `apple2auxfetch.s` | 128 KB aux memory, whole pages: `aux_store(pages, aux_page)` from `aux_store_src`, `aux_fetch_pages(pages, aux_page, main_page)`, on `dev/lib/apple2/auxmem.asm` (see its README) (ROBOT SPACE STATION) |
| `apple2t80.h` + `apple2t80.s` / `apple2t80_ptr.s` | 80-column text written directly (//e 80-column card / //c, 65C02; see below) and a pointer cell on it (MB TRACKER) |
| `apple2vblgate.h` + `apple2vblgate.s` | at most one go a //e refresh, `a2_vbl_gate()` (the mouse read once a frame), 19 B, for programs without `apple2vbl.s` (MB TRACKER, ROBOT SPACE STATION) |
| `apple2c.h` | umbrella header |
| `apple2c.mk` | Makefile fragment: `APPLE2C_SRCS`, `APPLE2C_INCS`, `APPLE2C_GAME_SRCS`, `APPLE2C_DOS_SRCS`, `APPLE2C_VAPOR_SRCS`, `APPLE2C_FRAME_SRCS`, `APPLE2C_VBL_SRCS`, `APPLE2C_VBL_PAL_SRCS`, `APPLE2C_AUX_SRCS`, `APPLE2C_AUXFETCH_SRCS`, `APPLE2C_AUX_DEPS`, `APPLE2C_VBL_GATE_SRCS`, `APPLE2C_T80_SRCS`, `APPLE2C_T80_PTR_SRCS`, `APPLE2C_T80_PTR_AFLAGS`, `APPLE2C_AFLAGS` |
| `apple2game.h` + `apple2game_asm.s` | speaker, joystick, buttons (optional) |
| `apple2vapor.h` + `apple2vapor_asm.s` | vapor lock: frame sync through the floating bus on a II / II+ / //e (optional) |
| `apple2dos.h` + `apple2dos_asm.s` | DOS 3.3 commands: BLOAD, BSAVE… (optional) |

## API

| Apple II function | Effect |
|---|---|
| `a2_putc(c)` | one character (`'\r'` = new line) |
| `a2_puts(s)` | zero-terminated string |
| `a2_print_hex(b)` | byte in hexadecimal |
| `a2_print_hexword(w)` | 16-bit word in hexadecimal |
| `a2_dos()` | return to the DOS `]` prompt, ZP restored |
| `a2_home()` | clears the text screen |
| `a2_text()` | TEXT + full screen + page 1 |
| `a2_wait(a)` | Monitor `WAIT` pause (`a2_wait(A2_WAIT_FRAME)` ≈ one frame) |
| `apple2_iskeypressed()` | ≠ 0 if a key is waiting |
| `apple2_getkey()` | waits for a key, `& 0x7F`, upper case |
| `apple2_readkey()` | 0 or the key, without waiting |

### Sound, joystick, DOS (optional objects)

The same routines as the asm modules `../apple2/sound.asm`, `joy.asm` and
`dos.asm`, called from C. They are separate objects (`apple2game_asm.s`,
`apple2dos_asm.s`, assembled with `-I dev/lib/apple2`): a program that does not
use them pays nothing (ANIMALS only just fits under DOS).

`make test-tools` compiles the sound/joystick object with a C program and checks
in the emulator the directions, vertical priority on diagonals, the
three buttons and the number of speaker toggles (zero means 256).

| Function | Effect |
|---|---|
| `a2_tone(flips, period)` | `flips` speaker toggles, 12 + 5·period cycles each; a toggle is a half-period: 1.02 MHz / (2·(12 + 5·period)), i.e. ~2.4 kHz at `$28`, ~526 Hz at `$C0`, ~397 Hz at `$FF` |
| `a2_read_stick()` | reads the joystick (~6 ms): `A2_JOY_NONE/UP/DOWN/LEFT/RIGHT`, raw values in `a2_joy_x`, `a2_joy_y` |
| `a2_button(n)` | ≠ 0 while button n (0-2) is held down |
| `a2_dos_cmd("BLOAD HISCORE,A$1000")` | a complete DOS command |
| `a2_dos_new()`, `a2_dos_add(s)`, `a2_dos_hex(b)`, `a2_dos_run()` | build a command with computed addresses |
| `a2_disk_protected()` | 1 if the disk of DOS's last access (slot read from its IOB) is write-protected |

`a2_dos_*` give DOS back the zero page that `crt0_apple2.s` saved at
startup (exported as `apple2_zp_buf`, as in `exit.asm`). A
DOS error stops the program at the prompt: put the files on the
disk and test `a2_disk_protected()` before writing.

More opt-in objects (2026-10-31), each its own `.s` so a program that does
not call it links the same bytes:

| Object (`apple2c.mk`) | Function | Cost |
|---|---|---|
| `apple2rand.s` (`APPLE2C_RAND_SRCS`, deps `APPLE2C_RAND_DEPS`), `apple2rand.h` | `a2_rand16()`: one step of `../math/random.asm`'s Galois LFSR (taps `$B400`), the new state; `a2_rand_state` (`$ACE1` at load) to seed, never 0 | 27 B code, 2 B DATA |
| `apple2stick.s` (`APPLE2C_STICK_SRCS`, with `APPLE2C_GAME_SRCS`) | `a2_stick_present()`: `a2_read_stick()`, then 1 if both paddle timers ran out (a two-axis stick), 0 if either still runs | 17 B |
| `apple2dosbin.s` (`APPLE2C_DOSBIN_SRCS`, with `APPLE2C_DOS_SRCS`) | `a2_dos_bload(name, addr)`, `a2_dos_bsave(name, addr, len)`: `BLOAD NAME,A$hhhh` / `BSAVE NAME,A$hhhh,L$hhhh` | 95 B code, 22 RODATA, 5 BSS |

User: SNAKE (all three; its FIXED_SEED sequence is unchanged).

Macros: `puts_apple2(s)`, `println_apple2(s)`, `getchar_apple2()`, plus the
codes `KC_LEFT` `KC_RIGHT` `KC_UP` `KC_DOWN` `KC_RET` `KC_ESC`.

`a2_dos()` and returning from `main()` rely on
[`../../cc65/crt0_apple2.s`](../../cc65/crt0_apple2.s): it saves the zero
page at startup and puts it back before jumping to `$03D0`. While running,
Ctrl-RESET also goes through this path.

## Minimal program

```c
#include "apple2c.h"

void main(void) {
    a2_text();
    a2_home();
    puts_apple2("HELLO WORLD\r");
    apple2_getkey();
}                                   /* back to DOS */
```

    ca65 -t none -o crt0_apple2.o dev/cc65/crt0_apple2.s
    cl65 -t none -Oirs -I dev/lib/apple2c -c -o hello.o hello.c
    ...
    cl65 -t none -C dev/cc65/apple2_hgr_c.cfg -o hello.bin \
         crt0_apple2.o hello.o apple2io_str.o apple2io_asm.o      # crt0 first

Full example: [`../../examples/hello`](../../examples/hello).

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).

## Optional frame pacing

Link `APPLE2C_FRAME_SRCS`, then call `a2_frame_init()`: the result
reports `A2_FRAME_VBL` on IIe or `A2_FRAME_DELAY` on II/II+, IIc and IIgs.
`a2_frame_wait()` waits for the next VBL edge on IIe. A stuck signal
causes a bounded fallback to the delay, until the next `a2_frame_init`.
Each polling phase is limited to 6,144 reads, with a margin for
PAL/NTSC at 1 MHz: the bound counts reads, not time, and an
accelerator card can exhaust it before the VBL (fallback to the delay). Likewise,
the watchdog of `a2_cadence_wait` (4,096 reads) assumes 1 MHz. The stuck-signal test measures about 84,848 cycles, fallback
delay included, against 739,088 before.
`a2_frame_mode()` reads the current mode. No video or
interrupt switch is changed; the IRQ mask is preserved.

`a2_frame_set_delay(n)` sets the ROM WAIT argument (0 becomes 1). The default
80 represents about 17,093 CPU cycles, to which drawing adds. This
service therefore provides neither a compensated delay nor an exact rate on
machines without VBL. Polling assumes main ROM/RAM and main zero
page; the routines are not reentrant or callable from an IRQ.

With double buffering: draw, wait, then flip. With single buffering:
wait before drawing; the drawing can still overrun the VBL.
See the [HGR example](../../examples/hgr/README.md).

## Two-refresh deadlines

With an application IRQ available, link `APPLE2C_CADENCE_SRCS` and include
`apple2frame.h`. The handler calls `a2_cadence_tick` exactly once
per refresh. To present within the VBL, its period **and its phase** must
follow the video. The library installs no handler or peripheral
and does not force interrupts on.

```c
/* The IRQ source is already installed and active, synchronised to VBL. */
if (!a2_cadence_init(2)) return 1;
for (;;) {
    /* Keyboard, logic, then drawing into the hidden page. */
    hgr_spr_render();
    if (a2_cadence_wait() == A2_CADENCE_TIMEOUT) break;
    hgr_spr_present();
}
```

Two ticks nominally give 30 FPS NTSC / 25 FPS PAL. A late workload
skips the missed deadlines and waits for the next one on the initial
grid; the return value counts those losses. No burst catch-up. A stopped
clock produces $FFFF after a bounded wait and disables pacing; redo
`init` after repairing the source. IRQs must stay enabled during
`wait`, which preserves I. The tick preserves A/X/Y and modifies NZ; the IRQ return
must restore the flags. Reads of the 16-bit counter must be atomic.

The accepted period is 1..8; an invalid value keeps the previous schedule.
The counters wrap modulo 65536; call `wait` before falling 32767 ticks behind.
The [test_cadence.py](../../tests/test_cadence.py) test provides a complete VIA
integration in a temporary POM2 machine, restores its vector and its IRQ
state, and checks 1,000 presentations per standard with overloads.

Without an IRQ card, the [minimal HGR example](../../examples/minimal/README.md)
spreads its workload over two VBL intervals on IIe. Each step must stay
shorter than one refresh. On the models that fall back to WAIT, pacing remains
dependent on rendering cost and CPU speed.

## ProDOS video clock (//e and //c)

`apple2vbl.s` (`APPLE2C_VBL_SRCS`, with `APPLE2C_FRAME_SRCS` and
[`../mouse/`](../mouse/)) gives ProDOS games one refresh counter on both
machines, from C or assembly:

| Call / variable | Effect |
|---|---|
| `a2_vbl_init()` | `a2_frame_init`, then `A2_VBL_POLL` (1) on a //e with a VBL signal, else `A2_VBL_NONE` (0) |
| `a2_vbl_irq_init()` | after `mouse_init`: installs the mouse firmware's VBL interrupt (mode 9) with ProDOS `ALLOC_INTERRUPT`, `A2_VBL_IRQ` (2); 0 without a mouse or if refused; enables interrupts |
| `a2_vbl_close()` | mouse back to mode 1, `DEALLOC_INTERRUPT`, mode 0 |
| `a2_vbl_scan()` | //e: counts an edge picture → blank; call at most ~4,000 cycles apart while drawing (33 cycles with the JSR when nothing changed) |
| `a2_vbl_mode`, `a2_vbl_count`, `a2_vbl_beam` | mode, refreshes seen (both modes, modulo 256), last `$C019` bit 7 |
| `a2_vbl_hook` | called by the //c handler after the count (the page flip): A/X/Y free, no zero page, no C stack; none while 0 (BSS, cleared by the crt0) |
| `a2_vbl_measure()`, `a2_vbl_pal` | `apple2vbl_pal.s` (`APPLE2C_VBL_PAL_SRCS`): 1 on a 50 Hz machine (one or two frames, bounded; 0 without a clock) |

Repeated `a2_vbl_irq_init()` calls reuse the installed handler. Switching
back through `a2_vbl_init()` first removes that handler. If the mouse firmware
refuses mode 9 after allocation, initialization releases the new handler and
returns zero without changing the previous mode. `test_vbl_lifecycle.py`
checks these paths with controlled MLI/firmware replies on the 65C02.
The module is 149 bytes of code and 6 of DATA: the mode tests use `lsr`
(mode 2 alone has bit 1), `a2_vbl_init` relies on `a2_vbl_close` for mode 0
and on `a2_frame_init` for X = 0, the handler keeps the carry of
`mouse_serve_irq`, and the scan's blank test is an `asl`.

Typical start: `a2_vbl_init() || (mouse_init(), a2_vbl_irq_init())`. The
presentation stays in the game (when to flip, the stick read in the spare
time, the speaker): see `chromabreak/src/timing.s` (DHGR, flip in the hook
every other refresh) and `wargalagaii/src/timing.s` (HGR, refresh pairs,
late frames). Option `-D A2_VBL_SCAN_SEI=1`: an edge is read again under
SEI before it is counted, for programs whose own interrupt handlers call
`a2_vbl_scan` too (WARGALAGA II's music); +9 cycles only when the beam
changes. Default 0 (CHROMABREAK).

### One go a //e refresh, without the clock (`apple2vblgate.s`)

`a2_vbl_gate()` (`APPLE2C_VBL_GATE_SRCS`, `apple2vblgate.h`) returns nonzero
on the first call in the vertical blank after a call in the picture, else
0: the same picture → blank edge `a2_vbl_scan` counts, seen lazily (call it
more often than the blank lasts, ~4,500 cycles, to miss none), without
`apple2vbl.s`'s 155 bytes and `apple2frame.s`. `a2_vbl_armed = 0` makes the
next go wait for a call in the picture (a read made without the gate).
//e only (`$C019`; the caller checks the model). 18 B + 1 B of BSS, 35
cycles with the JSR, no zero page. The AppleMouse read once a frame (two
READMOUSE calls in a row lose part of the motion): MB TRACKER's `m_sample`
(`if (vbl_gate && !a2_vbl_gate()) return;`), ROBOT SPACE STATION's
`ui_latch` (its main loop's own read resets it).

## 80-column text (`apple2t80.s`, `apple2t80_ptr.s`)

`apple2t80.h`, `APPLE2C_T80_SRCS`: the 80-column text page written directly
on a //e with an 80-column card or a //c (65C02): 80STORE on, even columns
in aux `$0400-$07FF` (PAGE2 on while written), odd ones in main, ALTCHARSET
on (inverse lower case, MouseText), text page 1. cc65's `ptr1`/`ptr2`/
`tmp1`/`tmp2` and `popa` borrowed; no interrupt handler may toggle PAGE2.

| Call / variable | Effect |
|---|---|
| `t80_init()` | 80STORE, 80COL, ALTCHARSET, TEXT, full screen, page 1; both halves cleared to spaces, not the screen holes (the slots', the mouse firmware's); `t80_mode` 0 |
| `t80_x`, `t80_y`, `T80_AT(x, y)` | the cursor; nothing is written past column 79 |
| `t80_mode` | `T80_NORMAL` (0), `T80_INVERSE` (1: `@`-`_` and lower case inverse), `T80_RAW` (2: the bytes are screen codes) |
| `t80_putc(c)`, `t80_puts(s)`, `t80_fill(c, n)` | at the cursor, `t80_x` advanced up to 80; strings and fills clip at the right edge |
| `t80_scroll(down)`, `t80_sw` | columns 0 .. 2 `t80_sw` + 1 (39 at first: all 80) of the `t80_x` rows from `t80_y` one row up (0: the last row keeps its text, to be redrawn) or down (the first); `t80_y` left moved |
| `t80_ptr_x`, `t80_ptr_y`, `t80_ptr_on`, `t80_ptr_show()`, `t80_ptr_hide()` | `apple2t80_ptr.s` (`APPLE2C_T80_PTR_SRCS`): the cell shown inverse (an inverse one normal, MouseText `+`); move it between hide and show |

354 B code + 4 B (the row table in CODE: a program may reuse its RODATA at
the exit); the pointer 115 B + 4 B, and `apple2t80.s` assembled with
`$(APPLE2C_T80_PTR_AFLAGS)` (`-D T80_PTR=1`, +51 B) so that the text routines
draw under it (what they write there is kept for `t80_ptr_hide`, shown
flipped) and `t80_scroll` hides it meanwhile. MB TRACKER (its whole screen;
the mouse read with 80STORE off stays in the program: the firmware's screen
holes are in main).

`test_t80_bounds.py` checks long strings/fills at the right edge, inverse
text and zero/one-row scrolls, with and without the pointer. Zero rows
are a no-op; scroll ranges must fit in the 24-row page. Both memory banks
and the screen holes are checked.
