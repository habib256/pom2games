# DEMO — five Apple II demos on one disk

Five graphics demos from [POM1](https://github.com/habib256/pom1)'s GEN2 card
(VERHILLE Arnaud), ported to the Apple II and gathered on a single bootable
DOS 3.3 disk, `../dist/DEMO.dsk`. The disk boots into a BASIC menu; pick a
number, watch, press ESC, pick the next one. Runs on an Apple II+ with 48 KB
or any later model.

| Key | Program | What you see | Technique | Size |
|:---:|---|---|---|---:|
| 1 | `BOUNCES` | One 48x48 and three 16x16 coloured balls bounce in a frame and collide with each other; a bounce counter sits in the HUD | XOR sprites blitted a whole byte at a time (`hgr_blit7`), pre-tinted once at startup; vector frame (`hgr_rect` / `hgr_line`); double buffering on HGR pages 1 and 2 with incremental redraw | 11.1 KB |
| 2 | `ANIMALS` | Eight SCROLL-O-SPRITES "Fauna" animals (dog, octopus, bat, lion, rabbit, spider, cat, snake), each in its own hue, drifting on sine paths | x2 colour sprites baked offline into 7 pre-shifted phases for 2-pixel-smooth motion; erase by byte-column fill, draw with an OR blit; double buffering | 12.8 KB |
| 3 | `LIFE` | Conway's Game of Life on a 40x40 grid, 7x4 pixels a cell; six seeds: Gosper glider gun + R-pentomino, pulsar, pentadecathlon, die hard, acorn, four colliding gliders | B3/S23 rules over two swapped cell grids with a dead border, pure 6502 assembly | 1 531 B |
| 4 | `PRESHIFT` | An 11x11 ball bouncing pixel-precisely under a static 21x9 ship, on a green floor | The Buzzard Bait pre-shifted sprite engine: 7 phases per sprite baked offline, so a 1-pixel-precise blit is "pick phase x%7, blit bytes at x/7"; single buffer, XOR erase and draw inside one frame pause | 4.1 KB |
| 5 | `FONT` | All 256 CP437 glyphs of the Beautiful Boot 8x8 font, 16 by 16, IBM PC order `$00`-`$FF` | HGR mixed mode: the glyph grid fills the top 160 scanlines, the four text lines carry the captions; pure assembly | 2 975 B |

Keys inside a demo: **ESC** returns to the menu from BOUNCES, ANIMALS and
LIFE; in LIFE **any other key** switches to the next seed; PRESHIFT and FONT
return to the menu on **any key**. ESC at the menu exits to the DOS prompt.

## How to run

Boot `../dist/DEMO.dsk` in any Apple II emulator, or on a real machine
through a floppy emulator. With [POM2](https://github.com/habib256/pom2)
installed as `/Applications/POM2.app`:

    make run        # boots the disk in POM2 with the Apple ][+ preset

Point `make run POM2=path/to/POM2` at another install. The disk ships
pre-built in `../dist/`, so nothing needs compiling just to watch the demos.

## Build

Prerequisites: cc65 (`brew install cc65`) and python3. Everything else,
including the DOS 3.3 system tracks, lives in `../dev`.

    make            # -> ../dist/DEMO.dsk  (bootable 5.25" DOS 3.3 image)
    make run        # build, then boot it in POM2
    make clean      # remove build/ (the disk stays)
    make distclean  # remove build/ and the disk

The Makefile includes `../dev/cc65/apple2.mk` (tool variables, library paths,
the `run` / `clean` / `distclean` targets and the `dos33.py` disk command),
`../dev/lib/apple2c/apple2c.mk` and `../dev/lib/hgrc/hgrc.mk`. The three C
demos compile with `cl65 -t none -Oirs`, link against `src/demo_c.cfg` and
the shared `build/hgrc/hgrc.lib`; the two assembly demos link against
`../dev/cc65/apple2_hgr.cfg`. All five load at `$6000` and `dos33.py` writes
them, plus `HELLO` from `src/hello.bas`, onto a fresh DOS 3.3 master.

Folder contents:

    src/hello.bas            the BASIC menu (HELLO)
    src/bounces.c            BOUNCES
    src/animals.c            ANIMALS, sprite banks included
    src/animals_gen_x2.py    bakes the ANIMALS banks (prints C to paste into animals.c)
    src/preshift.c           PRESHIFT
    src/preshift_sprites.h   its two sprite banks, generated from preshift_sprites.txt
    src/preshift_sprites.txt the ball and ship as ASCII art
    src/life.s               LIFE
    src/font.s               FONT
    src/demo_c.cfg           ld65 config for the C demos
    ../dist/DEMO.dsk         the disk

`preshift_sprites.h` was produced from the `.txt` by POM1's
`tools/build_preshift_sprites.py`, which is not part of this repository, so the
generated header is checked in. New seven-phase banks can be made here from a
PNG or PPM with `../dev/tools/assets/convert.py --mode hgr --kind sprite`.

## Under the hood

### The menu

`HELLO` is a short Applesoft program. It starts with `MAXFILES 1`, which
leaves DOS a single file buffer and moves its HIMEM from `$9600` up to
`$9AA6`: those 1.2 KB are what lets ANIMALS fit. It then sets `HIMEM: 4096` so
its own strings stay below `$1000`, out of the demos' way. Each choice runs
`BLOAD name` followed by `CALL 24576` (`$6000`); when the demo ends, the menu
redraws itself. ESC restores `MAXFILES 3` and `END`s.

`CALL` rather than `BRUN` because a `BRUN` from a running BASIC program does
not return cleanly. Every demo therefore ends with a plain `RTS` on the
caller's stack, after putting the zero page and the text screen back:

- C demos: `src/demo_c.cfg` sets `__EXIT_RTS__ = 1`, so the `_exit` of
  `../dev/cc65/crt0_apple2.s` returns instead of jumping to DOS.
- Assembly demos: `APPLE2_PREAMBLE_CALL` and `apple2_zp_save` on entry,
  `apple2_return` on exit (`../dev/lib/apple2/exit.asm`).

Ctrl-RESET still drops to the DOS prompt with the zero page restored.

### Memory map (C demos, from `src/demo_c.cfg`)

    $0050-$00FF  zero page: C runtime + hgrc, saved on entry and restored on exit
    $0800-$0FFF  the BASIC menu (program, variables, strings) -- never touched
    $1000-$1FFF  BSS, LOWBSS (large tables) and the zero-page save area
    $2000-$5FFF  HGR pages 1 and 2 (double buffering)
    $6000-$96A5  the BLOADed program (BOUNCES 11.1 KB, ANIMALS 12.8 KB, PRESHIFT 4.1 KB)
    $96A6-$9AA5  C argument stack (1 KB, grows down from $9AA6)
    $9AA6-$BFFF  DOS 3.3 with MAXFILES 1

LIFE and FONT follow the same layout through `apple2_hgr.cfg`: code at
`$6000`, zero page from `$50`. LIFE keeps its two 42x42 cell grids at `$1000`
and `$1700`.

### One archive, three different link sets

The C demos share `build/hgrc/hgrc.lib`, an `ar65` archive of
`../dev/lib/hgrc` (native HGR routines, `hgr.h`), `../dev/lib/gfx` (vector
primitives) and `../dev/lib/apple2c` (keyboard, `a2_wait`). `ld65` extracts
only the members a demo actually calls, together with their zero-page blocks,
so each binary carries a different slice of the same library:

| Demo | Pulls from the archive |
|---|---|
| BOUNCES | `hgr_blit7` (C + asm), `hgr_rect` / `hgr_line` through `hgr_geom`, `hgr_outline` and the `gfx_line` / `gfx_rect` / `gfx_backend_hgr` layer, `hgr_pixel`, `hgr_pixrect`, 16x16 text (`hgr_text`), 8x8 text (`hgr_text8`) with `hgr_font`, `hgr_num_field` + `hgr_utoa` for the counter, page flip and clear kernels |
| ANIMALS | `hgr_blit7`, `hgr_rect` byte-column fill (`hgr_byte_rect_asm`), `hgr_text8` + `hgr_font`, page flip and clear kernels — 14 members in all |
| PRESHIFT | `hgr_preshift` (C + asm, `hgr_sprite` / `hgr_sprite_xor`), `hgr_colorize`, `hgr_pixrect`, `hgr_carrier`, the `hgr_blit7` kernel, clear and mode kernels |

All three also take `apple2io_asm` (keyboard strobe, Monitor `WAIT`). The
assembly demos include their helpers straight from `../dev/lib/apple2`
(`hgr.asm`, `kbd.asm`, `exit.asm`, `print.asm`); FONT takes all 256 glyphs
from `../dev/lib/font/bbfont.inc` (`BBFONT_FIRST = $00`, `BBFONT_LAST = $FF`)
and LIFE clears the screen with `clear_hgr` from `../dev/lib/hgr`.

### Sprite baking

- ANIMALS: `animals_gen_x2.py` holds the eight 16x16 mono masters from POM1's
  `sprites_fauna_hgr.asm`, doubles each pixel to a full NTSC colour clock in
  the chosen hue (a byte-for-byte port of `hgr_inflate_x2`), then bakes the
  seven even shifts (0, 2, ..., 12 px) within a 14-pixel period, trimmed to
  each phase's bounding box. Run `python3 src/animals_gen_x2.py` and paste
  the output over the bank block in `animals.c`. At run time the demo blits
  phase `(x % 14) / 2` at byte column `2 * (x / 14)`; nothing is inflated on
  the Apple II.
- PRESHIFT: `preshift_sprites.txt` describes the ball and ship as `#` / `.`
  art; the generated `preshift_sprites.h` holds each as an `hgr_sprite_t`
  (`ball_ps`, 3 bytes wide, 11 rows; `ship_ps`, 4 bytes wide, 9 rows) with
  seven pre-shifted phases.

### What changed from the Apple-1 / GEN2 originals

- **No V-blank signal on a II/II+.** BOUNCES and ANIMALS flip pages as soon
  as the hidden page is drawn (a tear line may show for one frame). PRESHIFT
  replaces the GEN2 wait-for-V-blank with a one-frame pause (`a2_wait`, the
  Monitor `WAIT` routine), which keeps the ball's speed; its erase + redraw
  pair is the all-assembly XOR path, short enough to stay flicker-free.
- **Apple II keyboard and a return path to the menu** instead of Wozmon.
  BOUNCES, which ran forever, now stops on ESC. LIFE swallows the key that
  chose it from the menu before polling.
- **LIFE** moved its grids from `$0200` / `$0900` (DOS vectors and the BASIC
  menu on an Apple II) to `$1000` / `$1700`.
- **FONT** sent its captions to the Apple-1 terminal; here they use the four
  text lines of the mixed screen and the grid moves up above them (row pitch
  10 scanlines, last row ends at 157).
- **Captions** in BOUNCES and ANIMALS are trimmed to 34 characters, the width
  `hgr_puts8` really shows, and mention ESC.
- **C runtime** is the native `hgr_*` API of `../dev/lib/hgrc` instead of the
  GEN2 one, with `../dev/lib/apple2c` for input and timing.

## Origins

Each demo ports one sketch from POM1's `sketchs/gen2/` folder:

| Demo | POM1 original |
|---|---|
| BOUNCES | `demo_bounces/GEN2Bounces.c` |
| ANIMALS | `demo_sprite_animals/GEN2Animals.c` (itself the HGR take on the TMS9918 demo) |
| LIFE | `demo_life/HGR_Life.asm` |
| PRESHIFT | `demo_preshift/main.c` |
| FONT | `demo_hgr_bbfont_show/HGR_BBFontShow.asm` |

## Credits and licence

Demos and ports: VERHILLE Arnaud, [GPL-3.0](../LICENSE). Animal sprites:
SCROLL-O-SPRITES "Fauna" by Quale (CC-BY-3.0). Font: Beautiful Boot by
Michael Pohoreski, completed with the CP437 symbols in `../dev/lib/font`.
Pre-shifted sprite method: Buzzard Bait (Sirius Software, 1983).

Planned improvements: see [`TODO.md`](TODO.md).
