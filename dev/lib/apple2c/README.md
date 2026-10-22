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
| `apple2c.h` | umbrella header |
| `apple2c.mk` | Makefile fragment: `APPLE2C_SRCS`, `APPLE2C_INCS`, `APPLE2C_GAME_SRCS`, `APPLE2C_DOS_SRCS`, `APPLE2C_FRAME_SRCS`, `APPLE2C_AFLAGS` |
| `apple2game.h` + `apple2game_asm.s` | speaker, joystick, buttons (optional) |
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
