# LOGO — Apple II / DOS 3.3

**APPLE-1 LOGO V2.6, GEN2 HGR edition, running on an Apple II+ or //e.**

A turtle-graphics LOGO interpreter on the Apple II HGR screen, with the console
in 80 columns on a //e (40 on a ][+). It is the Apple II port of the LOGO from
[POM1](https://github.com/habib256/pom1) (VERHILLE Arnaud): the shared
interpreter `sketchs/tms9918/tool_logo/TMS_Logo_16k.asm` built the way
`sketchs/gen2/tool_logo_gen2` builds it (`CODETANK_BUILD` + `LOGO_GEN2`,
renamed `LOGO_HGR` here), imported from GitHub at commit `e2a4748`
(2026-09-11). The interpreter itself is unchanged; the console, keyboard,
screen handling and exit were rewritten for the Apple II.

    make            # -> ../dist/LOGO.dsk  (bootable 5.25" DOS 3.3 image)
    make run        # boot it in POM2 as an Apple //e

## Highlights

- **Turtle graphics on HGR**: `FD` `BK` `RT` `LT` `PU` `PD` `HOME` `CS` `SETXY`
  `SETH` on the full 280 x 192 screen, with the MIT-LOGO long names
  (`FORWARD`, `RIGHT`, `CLEARSCREEN`, ...) as aliases.
- **Colour**: `SETPC 0..15` tints the trail, the turtle, the sprite and the
  bitmap text at once (see *Colour on HGR* below).
- **Three screens, one display**: text, split (turtle + 4 console lines) and
  full graphics, by command (`TS` / `SS` / `FS`) or hotkey (Ctrl-T / Ctrl-S /
  Ctrl-L), even while a program runs.
- **40 or 80 columns**: the //e 80-column firmware is started by LOGO itself;
  `COLUMNS 40` / `COLUMNS 80` switch the console width.
- **Control flow and variables**: `REPEAT N [...]`, `REPEAT FOREVER [...]`
  (ESC or Ctrl-G aborts), `IF` / `IFELSE` with `< > = <= >= <>`, `STOP`,
  `MAKE` / `:NAME` (6 globals), `RANDOM N`, single-level arithmetic in
  arguments.
- **Procedures**: `TO NAME :p1 :p2 ... END`, up to 2 parameters, 10
  procedures of 224 bytes, 16 nested frames, free tail recursion.
- **Dynamic turtle**: `SETSHAPE "NAME` replaces the triangle with a 16 x 16
  shape (`BIRD1`, `BIRD2`, `HEART` and 12 emotes: `NORMAL` `HAPPY` `SUPER`
  `SAD` `UPSET` `ANGRY` `GRUMPY` `PERV` `SICK` `SLEEP` `PIRATE` `SHADES`);
  `SETSHAPE "ARROW` goes back to the triangle.
- **Bitmap text**: `LABEL "TEXT` at the turtle, `SAY "TEXT` in a speech
  bubble, `LIST [NAME]` to dump a procedure on the screen, `EDIT NAME` for the
  full-screen procedure editor (`HELP 9` lists its keys).
- **Built-in help and demos**: `HELP` (9 topic pages), `DEMO` (turtle
  slideshow: STAR, ROSETTE, FLOWER, SPIRAL, BIRDFLY, ...) and `DEM2` (the
  narrated story of the GEN2 card, told with the emotes and `SAY` bubbles).

## Quick start

Boot `LOGO.dsk`. The screen comes up split: the turtle above, the `?` prompt
in the 4 bottom lines. Then type, for example:

    PRINT "HELLO
    REPEAT 4 [FD 40 RT 90]
    SETPC 3
    REPEAT 36 [FD 5 RT 10]
    FS
    SETSHAPE "BIRD1
    SAY "HELLO, APPLE II.
    SS
    DEMO
    HELP
    BYE

A procedure with a parameter and a recursive spiral (from `HELP 8`):

    TO SQUARE :S
      REPEAT 4 [FD :S RT 90]
    END
    SQUARE 50
    TO SPIRAL :S :A
      IF :S > 100 [STOP]
      FD :S
      RT :A
      SPIRAL :S + 2 :A
    END
    CS SPIRAL 4 90

Keys at the prompt and while a program runs:

| Key                | Effect                                            |
|--------------------|---------------------------------------------------|
| Ctrl-T / `TS`      | text screen (full console)                        |
| Ctrl-S / `SS`      | split screen: turtle + 4 console lines (default)  |
| Ctrl-L / `FS`      | full graphics (typing goes on, unseen)            |
| ← or DEL           | erase the last character (Wozmon's `_` works too) |
| ESC or Ctrl-G      | abort a `REPEAT FOREVER` or a procedure           |
| `BYE`, Ctrl-RESET  | back to the DOS prompt, cleanly                   |

A drawing command (turtle, `LABEL`, `SAY`, `LIST NAME`) issued in text mode
switches to the split screen by itself; `HELP` switches to the text screen;
`EDIT` takes the whole screen while it runs, then restores the previous mode.

## Build and run

Requirements: cc65 (`brew install cc65`) and python3. Everything else,
including the DOS 3.3 system tracks, is in `../dev`.

    make            # -> ../dist/LOGO.dsk
    make test       # II+ and IIe commands, exact sprite rasters and transitions
    make run        # POM2, Apple //e preset (make run POM2=path/to/POM2)
    make clean      # remove build/ (the disk stays)
    make distclean  # remove build/ and the disk

The Makefile includes the shared rules of `../dev/cc65/apple2.mk` with
`LOAD = 0x4000` and `APPLE2_PRESET = iie`. The disk boots, `HELLO` does
`BRUN LOGO`, and LOGO starts on the split screen.

Machines:

- **Apple //e or //c with an 80-column card**: 80-column console.
- **//e without the card, Apple ][ / ][+**: 40-column console. `COLUMNS 80`
  then answers `? BAD ARG`.

## Under the hood

### Memory map

    $0050-$0092  zero page (saved on entry, restored by BYE and Ctrl-RESET)
    $0400-$07FF  text page (40 or 80 columns)
    $0800-$0FFF  HELLO program, kept by DOS
    $1000-$1E55  PROCBSS: control stack, variable and procedure tables
    $2000-$3FFF  HGR page 1: the turtle screen
    $4000-$8E27  CODE: the BRUN file (20,008 bytes, 19.5 KB), then
                 LINEBUF ($8E28-$8E91) and BSS ($8E92-$9248)
    $9600-$BFFF  DOS 3.3

### Why HGR page 2 is unused

The //e 80-column firmware sets 80STORE. From then on the PAGE2 soft switch no
longer picks which HGR page is displayed: it selects main or auxiliary RAM for
`$0400-$07FF` and `$2000-$3FFF`. The turtle therefore always draws on page 1,
and the `$4000-$5FFF` range that would have been page 2 holds the interpreter
instead (`src/logo.cfg`). `scr_set` also sets AN3 so the //e shows plain HGR,
never double hi-res.

### How LOGO starts the 80-column firmware

`scr_boot` (`src/screen.asm`) runs before any output. It reads `MACHID`
(`$FBB3`): anything but `$06` is a ][ / ][+ and the Monitor's 40-column `COUT`
is used as is. On a //e it checks `RD80COL` (`$C01F`); if 80 columns are not
already on (no `PR#3` before `BRUN`), it calls the firmware entry `$C300`,
then `$03EA` so DOS reconnects its I/O hooks. If `RD80COL` is still off there
is no 80-column card and the console stays in 40 columns. `COLUMNS 80` /
`COLUMNS 40` send the firmware's Ctrl-R / Ctrl-Q characters through `COUT`.
`BYE` keeps the current width, so the DOS prompt comes back in 40 or 80
columns.

The interpreter prints through `ECHO`, which `src/a2logo.inc` maps onto
`COUT`: Wozmon's `ECHO` and the Monitor's `COUT` share the same contract
(character with bit 7 set, registers preserved), so the Apple-1 code runs
unchanged.

### Colour on HGR

`SETPC 0..15` is the TMS9918 palette index of the original. On HGR the
backend maps it onto the byte's palette bit (`pen_hi_tbl` in
`src/hgr_logom2.asm`): 0-3 and 10-15 give the green/violet family, 4-9 the
blue/orange family; the actual hue of a pixel depends on its column parity, so
thin coloured lines alias exactly as on real hardware. White (15) stays white.

### Modules

    src/logo.s            the interpreter (TMS_Logo_16k.asm from POM1, adapted);
                          includes screen.asm, a2logo.inc, tms9918.inc and the
                          dev/lib/apple2 print.asm, kbd.asm, exit.asm
    src/screen.asm        Apple II screen: TS / SS / FS, 40 / 80 columns, BYE
    src/a2logo.inc        Apple-1 names mapped onto the Apple II (ECHO = COUT)
    src/hgr_logom2.asm    adapter to dev/lib/hgr plot, line and clear kernels;
                          signed X clipping and the full 280 columns
    src/emote_hgr.asm     TMS masks -> doubled HGR bytes; saved-background
                          composition through dev/lib/hgr/hgr_sprite_update.asm
    src/text_bitmap.asm   adapter to dev/lib/hgr/hgr_glyph8.asm, byte-wise OR
                          with palette and saved-background updates; includes
                          ../dev/lib/font/bbfont.inc (256 glyphs)
    src/bubble.asm        the SAY speech bubble
    src/buffer_editor.asm the EDIT procedure editor
    src/math.asm          sine table, LFSR random, decimal output
    src/sprite_helpers.asm, src/sprites_emotes.asm, src/tms9918.inc
    src/logo.cfg          ld65 configuration (memory map above)
    src/hello.bas         HELLO: 10 PRINT CHR$(4);"BRUN LOGO"
    ../dist/LOGO.dsk      the disk image

Build flags: `-D CODETANK_BUILD` (the full feature set: LABEL, SAY, LIST,
EDIT, DEM2), `-D LOGO_HGR` (the HGR paths) and `-D LOGO_SPRITE_CACHE`
(the plot hook that preserves trails beneath emotes).
`logo.o` is linked first; its CODE segment starts with `jmp main`.

Libraries: `../dev/lib/apple2` (soft-switch equates, keyboard, printing,
zero-page save and exit to DOS), `../dev/lib/hgr` (scanline, column and mask
tables, screen clear, clipped plotting, lines, glyphs and sprite composition), `../dev/lib/font` (the 8x8 Beautiful Boot font),
`../dev/tools/dos33.py` (disk image).

The glyph core replaces the per-pixel loop. On seven alignments of “A”,
the emitter takes 1,601–2,319 cycles instead of 5,328; a space takes 831
instead of 1,758. These are emitter measurements with an inactive sprite
hook, not whole-command timings. All 1,043 font/palette/edge cases match
the reference; glyphs clip at the right and bottom without wrapping.

### What differs from the Apple-1 / GEN2 original

- Console on the Apple II text screen through `COUT`, 40 or 80 columns, and
  the `TS` / `SS` / `FS` / `COLUMNS` commands and hotkeys (`src/screen.asm`).
  On the Apple-1 the console was the terminal and the turtle the GEN2 card;
  here they share one display, the Apple Logo way.
- Apple II keyboard (`../dev/lib/apple2/kbd.asm`), `_` cursor and backspace at
  the prompt.
- `BYE` and Ctrl-RESET return to DOS with the zero page restored
  (`../dev/lib/apple2/exit.asm`).
- Emotes are prepared as HGR byte masks while the old image remains visible.
  The new foreground appears before the old background is restored; overlap
  is composed directly. Trails and their palette bits survive beneath sprites.
  `SETPC` refreshes coloured emotes, and identical frames avoid HGR writes.
  Turning an emote keeps its bitmap unchanged. This removes the fully erased
  animation phase on II+ and IIe. Rendering uses one page without VBL sync,
  so scanout tearing remains possible.
- The shared signed-X line walker also fixes the old freeze when a triangle
  vertex crosses the left edge (for example `SETXY 0 80`).
- `RT` and `LT` were added as aliases of `TR` and `TL` (the `HELP 8` / `HELP 9`
  examples use them; the command table did not know them).
- Three upstream bugs fixed: `EDIT` drew its text diagonally (the glyph
  blitter did not restore `pix_x` / `pix_y`); `LIST NAME` never returned
  (`find_proc` re-read the line from the start and redrew the listing
  forever); the `RT` alias above.

## Documentation

- [APPLE-1 LOGO V2.6 manual (English)](doc/APPLE-1_LOGO-2.6-MANUAL.md): the
  language reference, tutorials and limits. It describes the Apple-1 / TMS9918
  version: on the Apple II `BYE` returns to DOS, the screen is 280 x 192,
  `HELP` has 9 pages, and the `TS` / `SS` / `FS` / `COLUMNS` commands exist.
- [Manuel APPLE-1 LOGO V2.6 (français)](doc/APPLE-1_LOGO-2.6-MANUEL.md).
- [Upstream README](doc/UPSTREAM_README.md): the POM1 origin, builds and
  internals of the TMS9918 version.
- `HELP` and `HELP 1` to `HELP 9` inside LOGO.
- Planned work: [`TODO.md`](TODO.md).

## Credits and licence

APPLE-1 LOGO V2.6 and this Apple II port: VERHILLE Arnaud, 2026. The emote
shapes come from SCROLL-O-SPRITES by Quale (CC-BY 3.0). Part of
[pom2games](https://github.com/habib256/pom2games); licence GPL-3.0 (see the
`LICENSE` file at the repository root).

## Sprite validation and timing

`make test` boots the real disk on II+ (40 columns) and IIe (80 columns).
It verifies commands, all seven HGR bit alignments, 8x8 and 16x16 patterns,
edge clipping, all sixteen pen settings, background restoration, identical
frames, transition checkpoints, `SAY`, screen modes, `BYE` and Ctrl-RESET.
The shared compositor is also tested independently on both HGR pages.

Cycle counts measured with a2run from command entry to the next REPL,
starting at `PU CS SETXY 128 96 SETSHAPE "BIRD1`:

| Command | Previous pixel renderer | Byte renderer | Speedup |
|---|---:|---:|---:|
| `SETSHAPE "BIRD2` | 81,033 | 41,706 | 1.94× |
| `SETXY 129 96` | 80,421 | 41,117 | 1.96× |
| `PD SETH 90 FD 8` (from `fd_common`) | 83,260 | 69,350 | 1.20× |

These are interpreter command costs, including parsing after the command
entry; keyboard pacing and intentional `WAIT` delays are excluded.
Sprites use foreground OR with an exact saved background, rather than XOR
inversion on illuminated scenery.
