# Snake — Apple II+ / DOS 3.3

The classic Snake, written in **C with cc65** for a **48 KB Apple II+** on the
native 280×192 hi-res (HGR) screen. It is the Apple II port of POM1's
`sketchs/gen2/game_snake_telemetry` sketch (GEN2Snake, VERHILLE Arnaud), and
the reference C program of the shared [`../dev/lib`](../dev/README.md)
libraries: a whole game in one 8,573-byte `BRUN` file.

| | |
|---|---|
| Machine | Apple II+ 48 KB or any later model, DOS 3.3 |
| Disk | [`../dist/SNAKE.dsk`](../dist/) — boots straight into the game |
| Source | [`src/snake.c`](src/snake.c), one file |
| Binary | `SNAKE`, 8,573 bytes, `BRUN` at `$6000` |
| Libraries | [`../dev/lib/hgrc`](../dev/lib/hgrc/README.md) (HGR runtime), [`../dev/lib/apple2c`](../dev/lib/apple2c/README.md) (keyboard, DOS exit) |

## How to play

The snake lives on a grid of **33 × 20 cells** (8×8 pixels each, drawn as
6×6 blocks). The **top and bottom walls kill**; the **left and right edges are
open**, so the snake wraps from one side to the other.

| Key | Action |
|---|---|
| `I` `J` `K` `L`, arrow keys | steer up / left / down / right |
| `P` or `ESC` | pause / resume |
| `Q` (while paused) | back to the DOS `]` prompt |
| any key | start from the title; restart after GAME OVER |

Keys are folded to upper case, so `i j k l` work too. A II+ keyboard only has
left and right arrows; up and down arrows exist from the //e on (a II+ sends
the same codes with `Ctrl-K` / `Ctrl-J`).

- **Apple** (solid red disk — HGR's orange, the warmest tint it has): **5 points**,
  the snake grows by one cell and **speeds up**.
- **Bonus gem** (solid green block): appears **every 4th apple** for **36 ticks**,
  worth **20 points**, no growth — pure risk/reward.
- **Speed**: about three cells per second at the start; each apple shortens the
  delay until it stops shrinking after 16 apples. The delay is a CPU spin
  calibrated for a 1 MHz 6502, so an accelerator card makes the game faster.
- **Turns**: two quick turns can be queued and are applied on two successive
  moves; a direct reversal is refused.
- **HUD**: the score sits top-right in white; the `HGR Snake` label top-left
  cycles violet → green → orange → blue with every apple.
- **YOU WIN** when all 660 cells are filled.
- The title screen starts the game on its own after ~4 s. After GAME OVER the
  banner holds for ~4 s, then any key restarts during a ~5 s window, after which
  a new game starts anyway.
- The apple sequence depends on *when* you press a key on the title screen
  (the 16-bit LFSR seed is mixed with the poll count and the key). An automatic
  start always plays the same sequence.

## Build & run

    make            # -> ../dist/SNAKE.dsk  (bootable 140 KB DOS 3.3 image)
    make run        # boot it in POM2 (Apple ][+ preset)
    make clean      # remove build/ (the disk stays)
    make distclean  # remove build/ and the disk

Prerequisites: [cc65](https://cc65.github.io/) (`brew install cc65`) and
python3. Everything else — DOS 3.3 system tracks included — is in `../dev`.
`make run` uses the installed POM2 (`/Applications/POM2.app`, or
`make run POM2=path/to/POM2`).

**Deterministic runs** for playtests and screenshots: build with a fixed seed.

    make clean
    make FIXED_SEED=0xACE1      # defines SNAKE_FIXED_SEED, ignores key timing

`make clean` first: the object rules do not track `CFLAGS`, so a seed change
alone does not trigger a rebuild. (A seed of 0 is replaced by `0xACE1`: an LFSR
must not start at zero.)

The disk holds two files: `HELLO` (`10 PRINT CHR$(4);"BRUN SNAKE"`, from
[`src/hello.bas`](src/hello.bas)) and `SNAKE`. [`../dev/tools/dos33.py`](../dev/tools/dos33.py)
writes it from the DOS 3.3 master tracks in `../dev/tools/dos33_system.bin`.

## Under the hood

### The C runtime

[`hgr.h`](../dev/lib/hgrc/hgr.h) is the whole API: `hgr_*` functions and
`HGR_*` constants over the Apple II's own soft switches (`$C050-$C057`) and the
interleaved page at `$2000`. It pulls in [`apple2c.h`](../dev/lib/apple2c/apple2c.h)
for the keyboard latch (`$C000` / `$C010`) and the clean exit to DOS. Snake
calls thirteen functions of it:

| Call | Used for |
|---|---|
| `hgr_init`, `hgr_clear` | switch to HGR page 1, clear it |
| `hgr_cell(cx, cy, set)` | the snake: fills or erases the 6×6 block of an 8×8 grid cell in **one asm call** (no per-pixel `hgr_plot` loop — `hgr_plot` is not even linked) |
| `hgr_fill_pixrect`, `hgr_colorize` | the apple (five pixel rows forming a disk, tinted `HGR_ORANGE`) and the bonus (a filled block tinted `HGR_GREEN`) |
| `hgr_fill_rect` | the two 1-pixel walls, whole byte columns at a time; the black bands behind the PAUSED / GAME OVER cards |
| `hgr_putu_field(184, 0, score, 5)` | the score: a fixed 5-glyph field that erases exactly its own box, so no flicker and no bleed into the label |
| `hgr_puts_color`, `hgr_clear_pixrect` | the `HGR Snake` label and every title / pause / game-over line, in one of the four NTSC artifact colours |
| `apple2_readkey`, `apple2_getkey` | keyboard without / with waiting, upper-cased, arrows as control codes |
| `a2_home`, `a2_dos` | `Q` from the pause: clear the text screen, restore the zero page, `JMP $03D0` |

Text is the **Beautiful Boot 8×8 font** (ASCII `$20-$7F`, see
[`../dev/lib/font`](../dev/lib/font/README.md)) pixel-doubled to 16×16 cells on
an 18-pixel pitch, drawn by one tinted pass of `hgr_blit_glyph`. The font covers
lower case, which is why the in-game label reads `HGR Snake` in mixed case.
Sprites are drawn *filled*: HGR colour is a byte-pattern artifact that keeps
only about half the pixels, so a hollow outline would dissolve into dots.

### What gets linked

`make` compiles every hgrc, gfx and apple2c source into one `ar65` archive,
`build/hgrc/hgrc.lib` (~240 KB), and `ld65` extracts only the members Snake
references — `build/snake.map` lists them. 22 members come out of the archive:

| Family | Members |
|---|---|
| Core asm kernels | `hgr_init`, `hgr_mode_asm`, `hgr_clear_asm`, `hgr_rows_asm`, `hgr_byte_rect_asm`, `hgr_pixrect_asm` + `hgr_pixrect_params`, `hgr_cell_asm`, `hgr_colorize_asm`, `hgr_carrier_params`, `hgr_text16_asm` + `hgr_text_params`, `hgr_utoa_asm` |
| Rectangles / cells (C wrappers) | `hgr_rect`, `hgr_pixrect`, `hgr_cell`, `hgr_colorize`, `hgr_carrier` |
| Text ×2 and numbers | `hgr_font`, `hgr_text`, `hgr_num_field` |
| apple2c | `apple2io_asm` (keyboard, `a2_home`, `a2_dos`) |

Left on the shelf: single pixels (`hgr_pixel`), 8×8 text, bitmap / pre-shifted
sprites and the sprite engine, lines and circles (`gfx`), LORES and DHGR. The
`gfx` directory is on the include path but nothing from it is linked. The
other 39 members are cc65's own `none.lib` helpers (16-bit arithmetic,
stack ops, `zerobss`, `copydata`).

### Memory map

From [`../dev/cc65/apple2_hgr_c.cfg`](../dev/cc65/apple2_hgr_c.cfg) and
`build/snake.map`:

| Range | Contents |
|---|---|
| `$0050-$009F` | C zero page: 80 bytes (the cfg allows `$50-$FF`; `$00-$4F` stays the Monitor's) |
| `$0800-$0FFF` | `HELLO` (Applesoft), never touched |
| `$1000-$1889` | `LOWBSS`, 2,186 bytes: the snake ring buffers `sx[660]` / `sy[660]`, the `occupied[24][35]` grid and the game state (not zeroed at start — `new_game()` initialises them) |
| `$2000-$3FFF` | HGR page 1 (page 2 at `$4000-$5FFF` is reserved by the cfg, unused here) |
| `$6000-$817C` | the `BRUN` file: `STARTUP` 163 + `ONCE` 12 + `CODE` 7,456 + `RODATA` 901 + `DATA` 41 bytes |
| `$817D-$877F` | `BSS` 1,279 bytes, then `ZPSAVE` 260 bytes (the zero page and RESET vector saved by `crt0_apple2.s`) |
| `$8E00-$95FF` | C argument stack, 2 KB, growing down from `$9600` |
| `$9600-$BFFF` | DOS 3.3 |

Startup is [`../dev/cc65/crt0_apple2.s`](../dev/cc65/crt0_apple2.s), linked
first so its `__STARTUP__` / `_exit` replace `none.lib`'s: it saves the zero
page and points RESET at `_exit`, so both `Q` and `Ctrl-RESET` return to a
clean DOS prompt.

### Differences from the Apple-1 / GEN2 original

- The POM1 telemetry side channel (`$C440-$C443`) is gone: on an Apple II that
  is slot 4's I/O space, where a Mockingboard lives.
- The GEN2 card's `$C250` switches become the Apple II's `$C050`; there is no
  V-blank to wait for on a II+, so the pace is a plain CPU spin.
- Apple II keyboard with arrow keys; the per-frame video-mode re-assert (a POM1
  renderer workaround) is removed.
- Title screen says `APPLE II`; pause and exit to DOS are additions.

## The reference C consumer of dev/lib

Snake is the smallest complete program built on the shared libraries and the
one quoted in [`../dev/lib/hgrc/README.md`](../dev/lib/hgrc/README.md): its
size table tracks the Snake binary (10,218 → 8,573 bytes, zero page 99 → 80
bytes) as the library gained its asm kernels and archive linking. The
[`Makefile`](Makefile) shows the canonical layout:

```make
include $(DEV)/cc65/apple2.mk        # tools, paths, run/clean/distclean, $(DOS33)
include $(APPLE2C)/apple2c.mk        # APPLE2C_SRCS (keyboard, text, DOS exit)
include $(HGRC)/hgrc.mk              # HGRC_ALL_SRCS, the archive's family lists
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS)   # apple2c rides in the same archive
OBJS := $(BUILD)/crt0_apple2.o $(BUILD)/snake.o     # crt0 FIRST
all: $(DISK)
...
include $(HGRC)/hgrc_build.mk        # after `all`: builds $(HGRC_LIB)
```

Link with `-C $(A2_HGR_C_CFG)` and `$(HGRC_LIB)` after the objects; put the
binary on a disk with `$(DOS33) --bin SNAKE=$(BIN)@$(LOAD)`. Planned work is in
[`TODO.md`](TODO.md).

## Credits & licence

- Game, port and libraries: **VERHILLE Arnaud** (habib256). Original:
  `GEN2Snake.c` in [POM1](https://github.com/habib256/pom1), for the Apple-1
  with Uncle Bernie's GEN2 HGR card.
- Font: **Beautiful Boot** by Michael Pohoreski (`apple2_hgr_font_tutorial`).
- Licence: [GPL-3.0](../LICENSE), the same as the upstream sketch.
