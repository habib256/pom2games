# dev — Apple II libraries and tools

Libraries and tools for two profiles with cc65: **Apple II+ 48 KB /
DOS 3.3** and **Apple //e enhanced 128 KB / ProDOS**. Derived from [POM1](https://github.com/habib256/pom1) (GPL v3), they
use the Apple II's native video. Every game in the repository shares them.

    dev/
      lib/apple2/      asm : hardware, text, keyboard, HGR, DOS exit,
                       sound, joystick, DOS commands
      lib/apple2c/     C   : text, keyboard, sound, joystick, DOS; frame
                       pacing, ProDOS video clock (//e VBL, //c mouse IRQ)
      lib/prodos/      ProDOS 8 MLI and cleanup after DHGR; .SYSTEM shim
                       (sysboot.s); whole-file load/save (file.asm, file.s)
      lib/mouse/       AppleMouse II: polling, firmware IRQ and VBL,
                       optional ZP/mailbox context for legacy clients
      lib/audio/       optional PWM player, 8 kHz speaker samples
      lib/perspective/ HGR plane over 280 pixels and native two-axis corridor
      lib/math/        asm : exact products (quarter squares), square root,
                       division, LFSR for fixed-point physics
      tools/prodos/    ProDOS disk image (.po) builder/reader
      lib/font/        Beautiful Boot 8x8 font: one master table, sliced
                       on demand (asm, C, Python tools)
      lib/hgr/         text, TMS/pre-packed sprites, lines, spans,
                       clears and HGR tables in assembly
      lib/hgrc/        C HGR runtime: hgr.h, hgr_* functions
      lib/gfx/         C geometry (lines, rectangles, circles) for hgrc
      cc65/            ld65 configs (asm and C), Apple II crt0 and apple2.mk,
                       the Makefile fragment shared by every program
      tools/dos33.py   builds a bootable DOS 3.3 image (.dsk) and reads back
                       the files of an existing image (save tests)
      tools/dos33patch.py  writes into a program on the disk where its
                       files are (T/S lists, sectors of a save), so it can
                       read them through RWTS once DOS is released ($(DOS33PATCH))
      tools/hgr_tables.py  HGR layout, divide/modulo 7 and runtime offsets
      tools/fonts.py   the Beautiful Boot font on the Python side (derived tables)
      tools/a2test.py  test harness: ld65 labels, a2run/a2shot launch,
                       memory dump decoding, test disk
      tools/a2profile.py  a2shot `pcprof` response: cycles per address, per
                       routine (ld65 labels), per region, per group; table
      tools/re6502/    6502 reverse engineering: 6502/65C02 opcodes, code
                       tracer, da65 info, physical sectors; cli.py (physics/)
      tools/build_dhgr_font.py  binary image of the relocated small DHGR font
                       (lib/hgrc, DHGR_SMALL_FONT_EXTERNAL)
      tools/assets/    PNG/PPM -> HGR/DHGR bank converter, masks, previews
      tools/audio/     PCM WAV -> PWM clips; 6502 player generator;
                       notes.py: note names -> tone/duet counts, duet.asm
                       tunes in just intonation (the games' music tools)
      tools/perspective.py  configurable fixed-camera tables
      tools/dos33_system.bin  DOS 3.3 system tracks (0-2) from the Apple master disk
      tools/a2shot/    headless, scripted runs with PNG captures
      tools/a2run/     the same thing in portable C, with disk writes
      tests/           Python tests for the libraries: HGR, sprite engine,
                       DHGR, frame pacing, examples, assets (make test, make test-dhgr)
      bench/           cycle and size measurements, regression budgets
      examples/hello/  asm + C starter program on one disk
      examples/hgr/    animated HGR starter: sprites, counter, keyboard, pacing
      examples/dhgr/   DHGR 560×192 / 16 colours, Apple IIe 128 KB or IIc
      examples/perspective/ HGR grid + audio effect; disk in build/

## Getting started

The [ASM/C integration contracts](lib/ABI.md) specify memory,
calling conventions, banks and interrupts.

    cd examples/hello
    make            # -> ../../../dist/HELLO.dsk (HELLOASM at boot, then BRUN HELLOC)
    make run        # in POM2, Apple ][+ profile

Copy `examples/hello` to start a text program, or
[`examples/hgr`](examples/hgr/README.md) for an animation with sprites,
a counter, keyboard and double buffering. To put the new folder next to
`micro-sokoban/`, set `DEV ?= ../dev` and `DIST ?= ../dist` in its `Makefile`
so the disk joins the others in `dist/`.

Every `Makefile` starts with `include $(DEV)/cc65/apple2.mk`, which provides the
tool variables (`CA65`, `CL65`, `PYTHON`, `POM2`, `A2RUN`…), the library
paths (`APPLE2`, `HGR`, `FONT`, `HGRC`, `GFX`, `APPLE2C`), `A2_INCS` and
`A2_ASM_DEPS` for the assembler, the `$(DOS33)` command that builds the
disk, and the `run` (`APPLE2_PRESET`, `APPLE2_RUN_FLAGS`), `clean`,
`distclean` and `$(A2RUN)` targets. The program's `Makefile` keeps only its
compile rules and its `$(DISK)` rule.

Assembly libraries are included **after** the code that calls them: a
routine is only assembled if it was referenced before the include (`.ifref`),
so a game only pays for what it uses.

`pom2games` depends on no other folder: cc65 and python3 are all you need
to build the disks (plus libslirp for a2shot). `make run` launches the installed
POM2 (`/Applications/POM2.app`, or `make run POM2=path/to/POM2`).

The full ProDOS profile is [`chromabreak`](../chromabreak/README.md):
`crt0_prodos.s`, `apple2_dhgr_prodos_c.cfg`, the
[`prodos`](lib/prodos/README.md) and [`mouse`](lib/mouse/README.md) libraries.
It starts from a SYS file and quits with the MLI QUIT call.

## Apple II hardware

- Keyboard: read `$C000`, then touch `$C010` to acknowledge the key.
- Video: soft switches `$C050-$C057`, text and two independent HGR pages.
- No readable V-blank flag on II/II+: draw on the hidden page,
  then flip the display.
- Zero page shared with the Monitor and DOS: saved/restored by
  the startup and exit routines.

## Handing control back

Two ways to quit, depending on how the program was launched:

- **`BRUN` (a game)**: `APPLE2_PREAMBLE` then `apple2_exit`, which returns to the DOS
  prompt. In C: the default `crt0_apple2.s`.
- **`BLOAD` + `CALL` from a BASIC menu**: `APPLE2_PREAMBLE_CALL` (the caller's
  stack is left untouched) then `apple2_return`, which does an `RTS` back to
  BASIC. In C: `__EXIT_RTS__ = 1` in the ld65 config. A `BRUN` from a BASIC program, on the other hand, does
  not return cleanly: that is why the menu uses `CALL`.

In both cases, Ctrl-RESET returns to the DOS prompt with the zero page restored.

## Memory map (Apple II+ 48 KB, DOS 3.3)

    $0000-$004F  Monitor / DOS           — left alone (COUT works)
    $0050-$00FF  program ZEROPAGE        — restore it if returning to DOS
    $0100-$01FF  6502 stack
    $0200-$02FF  input buffer            — free while running
    $0300-$03FF  DOS / Monitor vectors   — do not touch ($03F2 = RESET)
    $0400-$07FF  text page 1
    $0800-$0FFF  BASIC greeting program (HELLO) — kept by DOS, do not overwrite
    $1000-$1FFF  free (LOWBSS)
    $2000-$3FFF  HGR page 1
    $4000-$5FFF  HGR page 2
    $6000-$95FF  the BRUN binary (13.8 KB max), then BSS / C stack
    $9600-$BFFF  DOS 3.3

## Tests in Python

[`tools/a2test.py`](tools/a2test.py) gathers what every test script used to
redo: `labels(fichier.lbl)` reads the ld65 symbols and provides
`peek()` / `poke()` / `until()`; `run(disque, étapes, iie=, wp=, emulator=,
pad_until=)` launches a2run, or a2shot with `--iie` (raw keys are
escaped for it), and returns a `Result` with `.dumps` (one `bytes` per `peek:`),
`.data`, `.mem(adresse, n)`, `.cycles` (one per `until:`), `.spk`,
`.text_screens()`; `hgr_offset(y)`, `hgr_visible(page)`, `page_dump()` and
`build_disk()` round it out.
`tools/dos33.py` also reads an image back: `catalog()`, `read_file()`,
`replace_file()` (game saves). The MICRO-SOKOBAN,
ARKABREAKOUT, CHROMABREAK, Maze3D, `tests/` and `bench/` scripts use it.

## a2shot

Boots a disk on an emulated Apple II+ (the POM2 core, no window, no
wall clock, hence deterministic) and runs a script:

    cd tools/a2shot && make
    ./a2shot --disk ../../../dist/CHESS.dsk \
        wait:900 shot:menu.png key:2 wait:60 shot:board.png peek:0800:2

| Step              | Effect                                             |
|-------------------|----------------------------------------------------|
| `wait:N`          | runs N frames (17,030 cycles each)                 |
| `until:ADR:N`     | runs until PC = ADR (N frames at most, otherwise fails) and prints the cycle counter |
| `until:A,B:N`     | stops at any of the given addresses; useful for questions with several entry points |
| `key:TEXTE`       | types the text (`\r` RETURN, `\e` ESC, `\<` `\>` arrows), three frames per key |
| `press:TEXTE`     | queues the keys without running (for an exact `until:`) |
| `shot:F.png`      | captures the screen at 560×384 (HGR and DHGR)      |
| `peek:ADR[:LEN]`  | dumps memory (bus read)                            |
| `poke:ADR:OCTET` | writes one byte to memory (hexadecimal values) |
| `load:F@ADR`      | writes a whole binary file from ADR on (bus writes, below $C000) |
| `watch:ADR[:MEM:LEN]` | prints the registers each time PC reaches ADR, and optionally LEN bytes at MEM (hexadecimal addresses, decimal length, 4096 at most, not past $FFFF) |
| `unwatch`         | disables all `watch:` traces                       |
| `joy:X,Y`, `btn:N,0\|1` | joystick                                     |
| `reset`           | presses RESET                                      |
| `pc`              | prints the PC                                      |

`--iie` boots an Apple //e enhanced (65C02, 80-column card and auxiliary
memory) instead of the ][+: this is what allows testing LOGO in 80 columns.

a2shot boots a **copy** of the disk: POM2 writes modified images back, and
a test must not alter the disk it is checking.

`--stdin` accepts additional steps, one per line. Each response
ends with `a2shot:done`, flushed to stdout immediately; EOF ends
the session. `a2test.Session(disque, cwd=...)`, used with `with`, exposes
`step(étape) -> Result` and keeps the log in `.out`. The driver can
thus examine the displayed question before supplying the answer; a timeout
or an emulator stop raises an exception.

a2shot is self-contained: `sdk/` holds the POM2 core SDK (`core.hpp` and
`lib/darwin-arm64/` and `lib/linux-x86_64/libpom2_core.a`, without debug
symbols; provenance in `sdk.mk`) and `roms/` the Apple ][+,
Apple //e (+ character ROM) and Disk II ROMs, copied from POM2 (`--roms DIR` to use others). Only
libslirp (`brew install libslirp`, `apt install libslirp-dev`) and zlib come
from the system.
DOS 3.3 takes about 900 frames to launch an 8-12 KB game.

## a2run

As a library (`-DA2RUN_LIB`, `a2run.h`): `a2run_main()` boots a disk
and plays a script, then the caller drives `cpu`, `ram` and `kbd_latch`
itself (`arkabreakout/tests/pilot.c` plays the campaign with the joystick).

The portable equivalent of a2shot (Linux and macOS, C99 + zlib, without the POM2
core): an NMOS 6502 (validated by Klaus Dormann's functional test
suite), 48 KB, keyboard, speaker, joystick and a nibble-level Disk II,
for reading **and writing**. Same ROMs (`a2shot/roms`), same
script syntax, plus a few steps for tests:

    cd tools/a2run && make
    ./a2run --disk ../../../dist/MICRO-SOKOBAN.dsk \
        wait:900 shot:titre.png key:" " wait:30 key:LLK spk dsk:apres.dsk

| Step              | Effect                                             |
|-------------------|----------------------------------------------------|
| `wait:N`, `until:`, `key:`, `press:`, `shot:`, `peek:`, `joy:`, `btn:`, `reset`, `pc` | as in a2shot (`\^` `\v`: up/down arrows) |
| `text`            | prints the 40×24 text page                         |
| `poke:ADR:VAL`    | writes one byte to RAM                             |
| `spk`             | number of speaker toggles since the last `spk`     |
| `spklog:F.txt`    | from then on, writes the cycle of each toggle, one per line (pitch, tempo) |
| `dsk:F.dsk`       | writes the disk as the program left it (saves)     |
| `load:F@ADR`      | copies a whole binary file into RAM at ADR (hex)   |
| `regs:A:X:Y`      | sets the registers (hex) for the next `go:` or `call:` |
| `go:ADR`          | jumps: PC = ADR, the stack is left as it is        |
| `call:ADR:N`      | JSR ADR from the current PC, runs until it returns (N frames at most) and prints `cycles=` (counter), `elapsed=` (cycles of the call) and the registers |

Without `--disk` there is no card in slot 6: the ROM falls into
Applesoft and a2run stops at its prompt after 8 frames (a DOS boot takes
~1,100). Library tests load their code there instead of building a disk:

    ./a2run load:fixture.bin@6000 go:6000 until:6123:100 peek:2000:16
    a2test.run(None, a2test.bin_steps(binary) + [L.until('done')])

a2shot has `load:` but not yet `go:`/`call:`: the POM2 facade cannot set
the registers (request: `a2shot/LETTRE_POM2_REGISTRES.md`).

The disk given to `--disk` is never modified; `--wp` presents it
write-protected (save tests). DOS 3.3 takes about
400 frames to launch a game. No language card, no 80 columns: for
LOGO on //e, a2shot remains the tool.

Licence: GPL v3, like the POM1 sources these libraries derive from.

## Tests: two tiers

Each program has two targets (convention from `cc65/apple2.mk`):

- `make test`: the **fast** tier (one to two minutes), the reflex of the
  development loop: `make -C <jeu> test` after each change;
- `make test-long`: what is too slow for that (full campaigns,
  every level, long runs); the target may be empty.

At the root, `make test` runs the fast tiers and the fast checks
of `dev/` (`make test-dev`: libraries, tools, examples,
`bench-check`), `make test-long` the long tiers, `make test-all` both.
`make test-changed [BASE=<ref>] [LONG=1]` tests only the programs that
the working tree touches (sources in the folder, or a rebuilt disk image
that differs from BASE's: see `tools/test_changed.py`), plus
`make test-dev` if `dev/` changed.

## Assets and measurements

- [HGR/DHGR PNG/PPM conversion](tools/assets/README.md): banks, masks, previews and sizes.
- [Benchmarks and regression budgets](bench/README.md): `make bench`, `make bench-dhgr`.
- `make test-assets` and `make bench-check` are part of `make test` (`make test-dev`).
- `make test-dhgr` checks both pages, both banks and both backends.

## Frame pacing and animated example

The optional [`lib/apple2c/apple2frame.h`](lib/apple2c/apple2frame.h) service
waits for the next VBL on IIe, or uses a delay loop on II/II+ and
IIc. Waits are bounded; the service configures no interrupts.
Link `APPLE2C_FRAME_SRCS` and call `a2_frame_init()` before the loop.
The delay adds to the drawing time; it does not guarantee a fixed
rate. See the [HGR example](examples/hgr/README.md) for the per-model contracts.

`make test-frame` and `make test-hgr-example` are part of `make test`.
The sprite engine tests are part of `make test-hgr`.

## Fixed-sector DOS disks

`tools/dos33.py` exposes `Dos33Image.blank()` for a custom loader:
empty catalog, tracks 0–2 reserved, without copying the standard DOS boot.
`reserve_sectors(start, count)` reserves linear sectors in DOS order
before files are added. `write_fixed(start, data, capacity)` writes a
module into those sectors; `capacity` is a byte count that is a multiple of 256.
Unused capacity is filled with zeros. Overflows, overlaps,
unreserved sectors and writes to the catalog/VTOC track are rejected
before any mutation. `save()` writes the reservation bitmap to the disk.

Pinball keeps its own placement recipe and loader, but uses this public
API. Files added afterwards cannot reuse its tracks.
`make test-tools` checks the HGR tables, sector placement/reservation
and the standalone mouse context; this target is part of `make test`.

The [three minimal integrations](examples/minimal/README.md) provide
DOS/ProDOS images and a computed memory budget. The [hardware register](lib/HARDWARE.md)
separates the physical tests still to be done from the emulated validations.

## Shared resource audit

`make audit-libs`, from the root, checks the actual dependencies of the
15 projects with ca65/cc65 and make's build graph. Build
the software and the minimal examples first so the generated resources
are available. See [the inventory and sharing opportunities](lib/USAGE.md).
