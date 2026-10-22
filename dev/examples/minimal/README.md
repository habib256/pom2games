# Three minimal integrations

Build from the repository root:

```sh
make -C dev/examples/minimal
make test-minimal
make test-dhgr
```

The files stay in `build/`, without adding a disk to `dist/`. The programs are
compiled for NMOS 6502; no 65C02 kernel is required.

| Image | Machine / system | Behaviour |
|---|---|---|
| `build/hgr-single.dsk` | II/II+/IIe/IIc, DOS 3.3 | One page, animated band, counter; drawing is visible while it runs |
| `build/hgr-double.dsk` | II/II+/IIe/IIc, DOS 3.3 | Two pages, draw then wait then present |
| `build/dhgr-prodos.po` | IIe with compatible auxiliary video RAM / IIc, ProDOS 8 | Two DHGR pages, explicit claim of the auxiliary memory and cleanup via `game_shutdown` |

ESC ends the program. The DOS CRT restores the video and the zero page; the
ProDOS CRT calls `game_shutdown`, restores its system state then MLI QUIT.
The `DEMO.SYSTEM` loader relocates its small code to `$0800` and loads
`DEMO.BIN` at `$6000`, its link address. The volume name is resolved through
ONLINE.

The ProDOS example chooses **PRESERVE_RAM**: if `/RAM` is installed, it shows
a refusal in text then returns to ProDOS after a key. This refusal is
expected, including for an empty RAM disk. To test the animation, use a
ProDOS without `/RAM` installed. The emulated test checks both paths; it
removes the `/RAM` entry only in its temporary machine. An application that
chooses `PD_VIDEO_DISCARD_RAM` explicitly accepts the destruction of the files.

## Integration contracts

Code, C stack, ZP and sources stay in main RAM, ROM visible, D=0. No drawing
primitive is called from an IRQ. The routines share their cc65 scratch. The
video pages are not used as application storage. HGR prepares its tables on
demand; `gfx_line` picks the ASM kernel here. DHGR initialises its
capabilities before drawing and uses eight-line clears, which hand control
back to the program between slices.

Double-buffered HGR uses an 8×8 HUD and, on the IIe, splits the drawing then
the HUD between two VBL waits. The POM2 test follows 1,000 frames in NTSC and
1,000 in PAL: intervals of 34,050..34,070 and 40,550..40,570 cycles
respectively, including the 65535 → 0 counter, with no missed refresh. That
is two refreshes per frame, nominally 30/25 FPS. This split requires each
step to stay under one refresh. The II/II+/IIc fallback adds a delay to the
rendering; its frame rate depends on the workload. Single buffering exposes
the writes. The DHGR example keeps its simple wait.

## Reproducible memory report

`build/memory.json` is computed from each `.map`, `.lbl` and `.bin`. It
separates the linked segments, the ZP, the reserved C stack and the video
pages. With the compiler used for this check:

| Example | Binary | Linked main segments | ZP | Reserved C stack | Video used |
|---|---:|---:|---:|---:|---:|
| HGR single | 8,152 | 9,763 | 64 | 2,048 | 8,192 |
| HGR double | 8,182 | 9,793 | 64 | 2,048 | 16,384 |
| DHGR ProDOS | 5,295 | 5,618 | 35 | 256 | 32,768 main+aux |

The main segments include the resident binary, BSS and the CRT's saved state.
The HGR file reserves the whole `$2000–$5FFF` window, even though single
buffering only uses page 1. The hardware stack `$0100–$01FF` and the host
system's memory are not counted in these columns. The reserved stack is not a
measure of its actual depth in use. Another cc65 may change the sizes; the
locally produced JSON is the reference for the build.

The tests check the pixels of the animated band, the drawing pages, the
presentation on the IIe, the return to the system and the `/RAM` refusal.
[Hardware validation](../../lib/HARDWARE.md) remains separate from the
emulated tests.

The HGR counters now use a 19-byte differential field, with one history per
page. The JSON also counts all code segments, including ONCE/INIT/LOWCODE;
the stack in use is measured separately in the benchmarks, without confusing
its observed depth with its reservation.

The HGR fields and their tables are prepared on each page during loading,
before the first animated frame. The opaque HUD kernel avoids linking the
parameters of the general enlarged text for these examples. The pre-shifted
digit bank comes on top of the general font used by the titles; the sizes
above include both banks.
