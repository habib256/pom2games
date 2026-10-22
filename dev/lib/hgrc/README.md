# lib/hgrc — C HGR runtime (cc65), Apple II version

*[← dev](../../README.md)*

C runtime for native Apple II HGR video, derived from
[POM1](https://github.com/habib256/pom1) (Arnaud Verhille, GPL-3.0).
The API is declared in `hgr.h`: `hgr_*` functions, `HGR_*` constants.
The soft switches are at `$C050-$C057`, the pages at `$2000` and `$4000`.
The text/keyboard base is [`../apple2c`](../apple2c/).

Used by [`../../../snake`](../../../snake/) and
[`../../../light3dball`](../../../light3dball/). The vector drawing functions go through
[`../gfx`](../gfx/).

**Mandatory rule: ×1 text is always white; only ×2 enlarged lettering
may be coloured.** Use `hgr_puts8` for small white text and reserve
`hgr_puts_color` for ×2 titles. Colouring small glyphs removes
strokes and degrades their legibility. Leave a black margin if the text
sits next to coloured scenery. See also the rule in [`../hgr`](../hgr/README.md).

## Building as an archive

The assembler kernels are split: initialisation (mode, initial clear,
LORES, line-table switching), clearing, byte rectangles,
pixel rectangles, cells, pixels, colourising, ×1 text, ×2 text,
decimal conversion, bitmap sprites, aligned sprites and preshifted sprites.
The C wrappers follow the same split. The font and the shared
parameters are defined only once, in their own objects.

Compile `HGRC_ALL_SRCS` into an `ar65` archive, then link the program against
that archive. `ld65` extracts only the objects it needs: unused
families take up neither code nor zero page. The per-program exclusion flags
have been removed. The three C demos share a single archive.
Linking all the `.o` files directly would instead pull in every family.

Three objects carry the mode switches: `hgr_mode_asm.s` (`hgr_init`,
`hgr_text_restore`), `hgr_mode_clear_asm.s` (`hgr_init_clear`) and
`hgr_lores_init_asm.s` (`hgr_lores_init`); `hgr_flip_rows` is in
`hgr_rows_asm.s`. Like the other archive members, each one is linked only
if the program calls one of its entry points.

Costs measured by `make bench` (cycles at 1.02 MHz): clearing a page
46 000 (self-modifying loop from `HGR_CLEAR_LOOP`, lib/apple2), page flip
via `hgr_flip_rows` (unrolled loop, one EOR per line), 8x8 text
`hgr_puts8` ~9 000 for "APPLE II" (glyph shifted across two bytes per
line), 16x16 text `hgr_puts` through the colour blitter with the white
carriers `$7F/$7F` (a single blitter, ~5 times faster than the old
pixel-by-pixel drawing). The C wrappers read `hgr_col7` / `hgr_phase7` /
`hgr_mask7` instead of dividing by 7, and the line tables are computed
without multiplication.

## Integration

`$(DEV)/cc65/apple2.mk` provides `HGRC`, `GFX`, `APPLE2C`, `BUILD`, the tools
and the `$(DISK)` rule; then include `hgrc.mk` and `../apple2c/apple2c.mk`.
The shared rules in `hgrc_build.mk` build `$(BUILD)/hgrc/hgrc.lib`
(`$(HGRC_LIB)`). Example:

```make
DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
DISK := $(DIST)/GAME.dsk
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS)

all: $(DISK)

# Provide the compile rules for crt0_apple2.o ($(A2_CRT0)) and main.o.
$(BUILD)/game.bin: $(BUILD)/crt0_apple2.o $(BUILD)/main.o $(HGRC_LIB)
	$(CL65) -t none -C $(A2_HGR_C_CFG) -o $@ $^

$(DISK): $(BUILD)/game.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin GAME=$(BUILD)/game.bin@$(LOAD)

# After the first target, so that "all" stays the default target.
include $(HGRC)/hgrc_build.mk
```

`HGRC_BUILD`, `HGRC_CFLAGS` and `HGRC_ASMFLAGS` can be customised.
Objects encode their directory and extension in the archive member
name. `config.json` records the options, tools and sources; changing
the flags invalidates the objects without a prior clean. An identical
build leaves the objects and the archive untouched.
The `HGRC_*_SRCS` lists remain available for building an archive
with a subset of families. See the Makefiles of Snake, the demos and
the [HGR example](../../examples/hgr/Makefile).

## Measured size

Historical before/after comparison for the first split, with cc65 2.18 and `-Oirs`, on
the same game sources (size of the `.bin` file and ZEROPAGE segment of the
`.map` file). This historical measurement includes the IIe video transitions and the assembler
kernels for text, clearing and page flipping. The zero page
includes the program's C runtime.

| Program | Binary before → after | Zero page before → after |
|---|---:|---:|
| Snake | 10 218 → 8 573 bytes | 99 → 80 bytes |
| Bounces | 12 263 → 11 348 bytes | 99 → 79 bytes |
| Animals | 13 139 → 13 121 bytes | 99 → 51 bytes |
| Preshift | 4 611 → 4 247 bytes | 99 → 60 bytes |

Animals mostly gains zero page: the abscissa check and the
restoring of the IIe video soft switches had cost it 76 bytes, which the
assembler kernels took over. The other programs also benefit from
excluding routines that were previously linked for nothing.

## Limits and verification

- `gfx_filled_rect` accepts two inclusive corners, puts them in order,
  clips them to 280×192 and splits widths above 255 pixels.
- `hgr_fill_pixrect` / `hgr_clear_pixrect` keep an 8-bit width;
  zero draws nothing. These functions reset the palette bit to zero
  in the bytes they touch, even at the edges of the rectangle.
- `hgr_colorize` and `hgr_blit7` reject off-screen abscissas before
  any conversion to an 8-bit column.
- `hgr_blit` reads only the bytes needed for the drawn pixels, including
  when the last line ends exactly on a byte boundary.
- `hgr_sprite_xor` also clips wide source lines, up to
  a stride of 255 bytes, without overflowing the 8-bit column computation.
- The four ASM kernels of `hgr_sprmask.s` also clip strides
  up to 255 bytes when called directly. `test_sprmask_bounds.py` checks
  both pages, the seven phases and the limits of the save buffer;
  the C engine keeps its 40-byte stride limit.
- `hgr_lores_clear` fills the 960 visible bytes of the drawing page and
  preserves the 64 bytes reserved for peripheral firmware.
- `hgr_lores_init` returns to native 40-column mode after a DHGR or
  80-column display, with `80STORE` off and reads/writes in main
  RAM. Model detection avoids these soft switches on the Apple II+.

`make test-hgr` compiles and runs the routines in **a2run**, on Linux and
macOS. Its 21 steps compare both video pages with a Python model:
256/280-pixel rectangles, limits, pixels, SET/CLEAR/XOR sprites and seven
phases, white/coloured text, numbers, cells, colourising. Four additional scenes check `gfx` cell text on
page 2, the cursor and the numeric conversions. Sixteen minimal
programs also check that the archive excludes unused kernels and zero-page
blocks. This test is part of `make test` and of CI.

×2 sprite enlargement is available on cc65 with
[`hgr_x2.h`](hgr_x2.h). `hgr_inflate_x2` converts a monochrome source
into a buffer supplied by the caller; `hgr_blit_x2` converts and draws
on demand with an internal 256-byte buffer. These functions are in
`HGRC_X2_SRCS` and the shared archive, extracted only if they are called.
For an animation, convert once at startup, then use `hgr_blit7`
on every frame. Place the sprite at `x = 14*n` to keep its hue.
Banks can also be prepared before compilation.

## DHGR (Apple IIe / IIc)

The [`dhgr.h`](dhgr.h) API provides 560×192 points, 140×192 colours,
segments, rectangles, block transfers, masked sprites and white text.
The DHGR objects are in `HGRC_ALL_SRCS` and the archive; they are extracted
only when a DHGR function is called. `HGRC_DHGR_SRCS` can also be linked
directly. The line-address computation is shared
with HGR in `hgr_layout.h`.

- `dhgr_capabilities()`: bits `DHGR_CAP_EXTENDED` and `DHGR_CAP_AUX_VIDEO`.
  The probe keeps the display and the bytes used in the video holes.
- `dhgr_init()`: returns 1 if the ROM model and auxiliary RAM are suitable,
  0 otherwise. A II/II+ is rejected without touching the IIe soft switches.
  Revision B and the DHGR jumper of a IIe cannot be detected in software.
- `dhgr_draw_page(1/2)` and `dhgr_show_page(1/2)` are independent.
  `dhgr_flip()` shows the drawing page and selects the previously shown page
  for the next drawing. VBL sync belongs to the caller.
- `dhgr_read_block` / `dhgr_write_block`: coordinates in interleaved bytes
  0..79, auxiliary/main order; `stride >= width`. Off-screen parts
  are not transferred. The buffer belongs to the caller.
- `dhgr_sprite`: x in **colour pixels**, banks precomputed for the seven
  bit shifts, mask 1 = keep the scenery. Each bank holds
  `stride * height` bytes. Saving then restoring a block gives save-under.
- `dhgr_puts`: opaque white/black text, 8×8 glyphs in **colour pixels**,
  four DHGR bits per font dot, to avoid an artifact tint.
- `dhgr_puts_small` (optional family `HGRC_DHGR_SMALL_TEXT_SRCS`): small opaque white font, **4×5 colour
  pixel** glyphs, five-column advance. Accepts every DHGR alignment,
  converts lower case to upper case and keeps the neighbouring pixels.
  An incomplete cell at the right or bottom edge is not drawn.
- `dhgr_small_char`: same font, one character per fast call; set
  `dhgr_small_x` and `dhgr_small_y` for a banner updated progressively.
  Auxiliary accesses are brief and preserve the interrupt state.
  By default, the tables are linked with the library. The assembler option
  `DHGR_SMALL_FONT_EXTERNAL=1` relocates them to `$0800` (or to
  `DHGR_SMALL_FONT_BASE`): the application must then copy the **1,653 bytes**
  of data there before rendering. `dev/tools/build_dhgr_font.py --out font.bin`
  produces a 2 KB image ready to load; `--base` and `--capacity` choose
  its location and size. The base must match the one
  used to assemble the engine.
- `dhgr_small_string`: fast string at coordinates `dhgr_small_x/y`, also used
  by `dhgr_puts_small`. The assembler option `DHGR_SMALL_USE_PROGRESS=1`
  calls the application entry point `dhgr_small_progress` between characters
  to track the VBL; this callback must preserve `ptr4`. No callback is
  required by default. The single-character call stays independent of this tracking.

`dhgr_small_font` exposes the glyphs for enlarged titles: 64 ASCII
characters starting at 32, six bytes per glyph (`DHGR_SMALL_FONT_STRIDE`). The
constants `DHGR_SMALL_ADVANCE` and `DHGR_SMALL_HEIGHT` describe the cell.
The tables `dhgr_row_lo/hi` and `dhgr_color_byte` can be shared with a
sprite engine; the two line tables are contiguous and the column indices
include the bound 140. `dhgr_small_layout.inc` defines their layout
with assembly-time assertions, and `dhgr_layout.inc` centralises the
addressing and masking formulas.

The DHGR objects are split so that the archive links only the functions used.
Consumers that compile the sources directly can choose:

| Make family | Contents |
|---|---|
| `HGRC_DHGR_STATE_SRCS` | Video state, initialisation, auxiliary trampoline and pages |
| `HGRC_DHGR_PIXEL_SRCS` | Monochrome points and pixel reads |
| `HGRC_DHGR_CLEAR_SRCS` | Clearing only, without rectangles or pixel reads |
| `HGRC_DHGR_FILL_SRCS` | Clearing and colour/monochrome rectangles |
| `HGRC_DHGR_CORE_SRCS` | The three previous families |
| `HGRC_DHGR_TRANSFER_SRCS` | Blocks and sprites, with shared addressing |
| `HGRC_DHGR_SMALL_TEXT_SRCS` | Small font and fast strings |

`HGRC_DHGR_SRCS` keeps the historical set of primitives, transfers and
8×8 text. `dhgr_internal.h` centralises the private parameters and prototypes of the
banked primitives. When compiling manually, `dhgr.c` now provides
the state and the pages: use the family lists above to include
their dependencies. The assembler kernels for masked writing, reading,
clearing and scanlines are separate objects. The pixel address and the
colour pattern are shared, while each read, point, rectangle
and clear API keeps its own object. The small-font parameters are
separate from the C wrapper: an assembler HUD does not pull in `dhgr_puts_small`.

Selecting families is not enough to eliminate every unneeded function
if their objects are passed directly to ld65. Building an ar65 archive and
placing it after the application objects lets ld65 extract only the
referenced members and their dependencies. ChromaBreak follows this rule with
`platform.lib`, including for the Apple II, ProDOS and mouse modules. Its test
checks the link map to exclude generic pixels, rectangles and transfers,
8×8 text and unused text wrappers. The library tests also check
sixteen minimal consumers of the archive.

### Memory contract and transitions

| State | Convention |
|---|---|
| Video pages | `$2000–$3FFF` and `$4000–$5FFF`, each in main and auxiliary |
| Code, C stack, buffers, sources | Outside `$2000–$5FFF`, in main RAM |
| Entry | Main `RAMRD/RAMWRT`, `ALTZP` off, main ROM |
| Primitive exit | Main `RAMRD/RAMWRT`, `80STORE` off, displayed page kept |
| Interrupts | I state kept; banked accesses protected, non-reentrant routines |
| Auxiliary read | Small executable trampoline of **9 zero-page bytes**, installed by init |

The mode keeps `80COL` on and `80STORE` off: `PAGE2` thus selects
the displayed page. `RAMWRT` allows auxiliary writes; the trampoline
reads with `RAMRD` without losing access to the main code. The primitives
cannot be called from an interrupt. Clearing blocks IRQs
for about 189 000 cycles; prefer blocks/segments in animation.

`hgr_init`, `hgr_init_clear` and `hgr_text_restore` put the IIe soft switches
back into native HGR/text state. `dhgr_text_restore` prepares the ROM text routines.
The C CRT also restores these soft switches on return and on Ctrl-RESET.
An HGR initialisation does not automatically change the HGR **drawing** page:
use `hgr_set_draw_page(1)` if you also want to reset that choice.

### gfx backends

Link **a single** backend, in addition to the `gfx` algorithms needed:

| Backend | Coordinates | `dhgr_set_color` |
|---|---|---|
| `HGRC_DHGR_COLOR_BACKEND` | 140×192 colour pixels | LORES colour 0..15 |
| `HGRC_DHGR_MONO_BACKEND` | 560×192 bits | 0 = off, other = on |

The backend is still chosen at link time. Monochrome mode produces
artifact colours on a colour monitor. Lines/circles/rectangles
share the generic `gfx` algorithms for DHGR; horizontal/vertical segments use byte
accesses with endpoint masking.

### Tools and verification

- [Asset converter](../../tools/assets/README.md): PNG/PPM, HGR/DHGR,
  sprites, masks, seven phases, preview and memory report.
- The host ×2 conversion declarations are in `hgr_host.h`.
- [Measurements and budgets](../../bench/README.md): CPU cycles, code, ROM, RAM and ZP.
- `make test-hgr`: 21 primitive checks, four `gfx` text scenes,
  24 sprite-engine scenes and sixteen minimal link edits.
- `make test-dhgr`: 21 historical checks + 48 additional checks,
  two pages/banks, two backends, sprites, blocks, text, transitions and II+ rejection.
  The POM2 IIe core in `a2shot` is required (macOS arm64).
- `make test` includes HGR, assets, HGR budgets and MICRO-SOKOBAN on Linux/macOS.

See the [animated demo](../../examples/dhgr/README.md).

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).

## Sprite engine and presentation

`hgr_spr_render()` restores then draws the sprites without waiting or displaying.
`hgr_spr_present()` shows the rendered page and selects the other drawing
page when double buffering; when single buffering, it does nothing.
`hgr_spr_update()` keeps the immediate render + present behaviour.
`hgr_get_draw_page()` returns the current drawing page (1 or 2).
The program must wait between render and present if it wants to synchronise the
flip; see [`apple2frame.h`](../apple2c/apple2frame.h) and the [HGR example](../../examples/hgr/README.md).

With the default eight slots, the static pool reserves 1,536 bytes even when single buffering.
This reservation belongs only to the compatibility object
`hgr_spr_init`. `hgr_spr_init_pool(dbuf, pool, size, count, capacity)`
uses a pool supplied by the caller and does not link that object. It needs
`count * capacity * (dbuf ? 2 : 1)` bytes; count is 1..8 and capacity
1..255 bytes per sprite/page. The HGR example uses this API for three
sprites. An invalid configuration returns zero and keeps the old
engine; backgrounds must be clean before a valid reinitialisation.
`hgr_spr_define()` returns 1 if the definition is accepted, 0 otherwise.
Null pointers, zero dimensions, stride > 40, height > 192 and
`stride * height > capacity` are rejected (96 with the compatibility pool,
1..255 with the external pool). A redefinition still drawn on
a page is rejected, keeping the old definition; hide and restore
each page before redefining. The shape data must stay valid
during these restorations. Do not modify the background under a drawn sprite.

`make test-hgr` adds 24 engine scenes: overlaps, seven phases,
two pages, right/bottom edge, hiding, redefinition and invalid geometries.
The comparisons also cover palette bits and video holes.
The same 24 scenes are run with a 24-byte external pool,
memory guards and invalid configurations. The link map checks
that the compatibility pool is absent.

## HGR tables and lines

The line, column, mask and phase tables are separate objects,
built on demand in RAM. A clear alone pulls in no table;
an aligned blitter reserves neither the masks nor the phases. The initialiser
`hgr_build_tables` remains available to prepare all the tables.
Page selection prepares only the lines. `hgr_row(y)` follows the drawing
page and returns NULL off screen. The masked and XOR sprite kernels
also prepare the X tables when called directly.

`hgr_line` uses an assembler Bresenham for diagonals over 280 pixels,
with the same pixel choices as the old C API. Axis-aligned lines keep the
fast spans. Off-screen endpoints are rejected; no implicit segment
clipping is added. `gfx_line` selects this kernel on HGR and the C fallback
on the generic/DHGR backends. `test_hgr_lines.py` compares 464 lines via `hgr_line` and `gfx_line` against the expected pixels on
both pages, including reversed directions, ties and X >= 256.

## DHGR clearing with IRQ servicing

`dhgr_clear_rows(y, rows, color)` fills the visible lines of the drawing
page, clips at 192 and preserves the memory holes. Each line restores
main RAMWRT and the caller's IRQ mask; enabled IRQs can
be serviced between lines. The measured kernel takes 1 177 cycles, under a
tested bound of 1 300. A test with a Mockingboard VIA timer also checks that periodic IRQs
are actually serviced during both page clears, with checks on
banks, memory guards and pixels. Servicing remains non-reentrant. Use small
slices so that input is also handled between calls. The historical full
clear keeps its behaviour and performance.

The host reference `hgr_inflate_x2` (`hgr_x2.c`) and the target version
(`hgr_x2_target.c`) compute the enlarged strides without 8-bit truncation.
The target transforms each byte with a 16-byte table, with no per-pixel
loop and no division. Reserve `4*wbytes*h` bytes of output, not
overlapping the source; the target rejects sizes above
65535 bytes. `hgr_host.h` remains a compatible include of `hgr_x2.h`.
`hgr_blit_x2` checks the
source size before doubling the dimensions, so as to respect its fixed
buffer even for inputs above 127. `test_hgr_host.py` checks the
colours and memory guards with ASan/UBSan, as well as all 65 536 dimension
pairs of the wrapper. `test_hgr_x2.py` runs the cc65 code and checks
the six colours, 510-byte strides, memory guards, invalid
sizes and clipped drawings on page 2. Both tests are part
of `make test-hgr`.


## Choosing the gfx implementation

`HGRC_VECTOR_SRCS` and the default archive use `gfx_line_hgr.c`, which
routes diagonals to the assembler `hgr_line`. The axis-aligned lines of `gfx_line`
keep their historical span clipping; `hgr_line` rejects any
off-screen endpoint, axis-aligned lines included. Valid diagonal pixels are identical.
For DHGR or an external backend, use `HGRC_GENERIC_VECTOR_SRCS`
(`gfx_line.c` + rectangles), with exactly one explicit backend.
Do not link both `gfx_line` implementations directly.

The [minimal examples](../../examples/minimal/README.md) provide the three
integrations: HGR single/double buffering and DHGR ProDOS, with a memory report
computed from the link maps. The shared contracts and units are
in [ABI.md](../ABI.md). The [hardware validation](../HARDWARE.md) protocol
separates emulated results from the physical trials still to be carried out.


## HUD with per-page history

`hgr_hud_field_t` is a state supplied by the caller, 37 bytes on cc65.
`hgr_hud_init(&field,x,y,width)` accepts a box entirely on screen,
width 1..14 cells of 16×16, pitch 18; an invalid input keeps the old
field. `hgr_hud_putu(&field,value)` returns the number of redrawn cells,
0 for an unchanged value, `HGR_HUD_INVALID` (255) if the value does not fit
or the pointer is null. Unlike the historical field, it rejects
numeric overflow without modifying the image or the history.

The digits are white on a black box whose contents the field owns.
Switching to a shorter value clears the cells that have become empty.
Pages 1 and 2 have their own history. After a clear or an external write
into the box, call `hgr_hud_invalidate(&field,page)`; page 0 invalidates
both. Do not overlay this field on a region of saved sprites without
also managing their background. The state must stay valid while it is in use.

The animated example uses this format; the two minimal HGR examples use
its compact 8×8 variant described below.
`test_hgr_hud.py` compares 168 updates over the seven phases, coloured backgrounds,
both pages, values that get shorter and geometry/overflow rejections.
The old fields remain available for drawing without history.


## Sizing the sprite metadata

`HGR_SPR_MAX` is a compile-time limit of 1..8 (8 by default). Passing the
same `-D HGR_SPR_MAX=N` to the program and to its archive sizes the private
arrays and the historical pool. The build signature invalidates the archive if this
flag changes. The engine still accepts a runtime count less than or equal
to this limit. Both page histories remain available.

A two-slot engine reserves 42 bytes of array state against 132 with eight slots:
**90 bytes saved**, independently of the external pool. The 24
regression scenes are also run with this configuration. The three-ball
example compiles program and archive with a three-slot limit, i.e.
75 bytes of metadata saved. The other programs keep the default.

## Incremental rendering and robust presentation

The engine keeps unchanged sprites at the start of the layer list.
From the first modified sprite (position or visibility) on, it restores the
following layers in reverse order, then redraws them in the original order.
This conservative strategy preserves backgrounds when sprites overlap,
without extra collision tables. A completely unchanged page
restores and redraws no sprite. Borrowed shapes remain immutable.
An invisible off-screen move does not force a redraw.

`hgr_spr_present` explicitly selects the engine's page before showing it,
even if the application changed its own page after `render`. It then selects
the other page for the next render. No video state is added when single buffering.
`hgr_spr_invalidate(1/2)` forces the next render of that page; 0 targets both,
other values are ignored. Invalidation does not allow modifying a background
under drawn sprites: hide them and restore the pages before that change.
Histories remain separate per page. The render controller, the
moves and the presentation are in ASM; stride×height is prepared at
definition time. Restorations recompute neither phases nor drawing
pointers; visible widths of two/four bytes use unrolled loops.

`test_sprengine_dirty.py` compares the pixels of both pages and the cost of
still frames, upper/lower layer changes, hiding
and clipping. On POM2 IIe, it also checks the page actually displayed
after the application changes the drawing page.

## Opaque HUD kernel

The compact path `hgr_hud8_init/putu/invalidate` uses a 19-byte
`hgr_hud8_field_t` structure, width 1..5, 8×8 cells, pitch 8.
The whole box must fit on screen: y≤184, x+8×width≤280.
The same cache, return-value, opaque background and overflow rules apply.
Its separate object lets only the format in use be linked. Changing all
five digits costs at most 7 850 cycles over the benchmark's seven phases,
against 22 235 for the 16×16 format. Prepare both pages before animating.

The minimal example uses this format. With IIe double buffering, it spreads drawing
and HUD over two VBL intervals; each step fits in one refresh.
Its POM2 test follows 1 000 presentations per standard, including counter
overflow: two refreshes per frame, i.e. nominally 30/25 FPS.
For a load that may exceed one interval, use the `a2_cadence_*`
scheduler and an IRQ source already owned by the application. See the
contracts in [apple2frame.h](../apple2c/apple2frame.h).

The engine compiled with `-DHGR_SPR_DAMAGE=1` propagates changes through
intersections of old/new boxes, in saved bytes rather than
visible pixels. It can keep isolated still layers,
but adds 43 bytes of BSS to the eight-slot default plus assembler
comparison work. The scene with four large isolated sprites, of which only the first
moves, goes from 31 031 to 14 662 cycles (+437 bytes loaded).
The option stays off by default; decide based on representative scenes.
The tests also check chains of four layers and padding bytes.

The digits of the differential field use a dedicated assembler kernel:
it replaces the background and writes the white glyph in the same pass over the lines.
It also clears the two spacing pixels of the inner cells, keeps
the neighbouring pixels and resets the palette of the bytes it touches.
The 16×16 format uses the existing font and a 16-byte LUT. The 8×8
format uses a space/digits bank preshifted for the seven phases: 1,386 bytes
loaded, pointer tables included. It avoids the mutable LUTs and the general
font when only the HUD is linked. The digit controllers are in ASM;
+1/+2 steps reuse the cached characters with carry propagation. The field's invalidation
rules are unchanged. The kernel no longer imposes general enlarged text
or the pixel-rectangle parameters on a HUD-only client.

The tests check 168 updates with decimal carry and wrap and 70 digits placed
against the right and bottom edges, in all seven phases. The same oracle
runs on a2run and POM2 IIe. The examples prepare both HUD
histories before their loop, to move this cost to load time.

## Optional explicit addressing

`hgr_row_on_page(page,y)` returns an address for page 1/2 and line
0..191, or NULL if an input is invalid. It changes neither the drawing page,
nor the displayed page, nor the historical tables. The immutable offsets take
384 bytes of RODATA, in a separate archive member; no mutable line array
is linked by this access alone. It is not an automatic substitute
for the existing kernels that read `hgr_rowhi`.

In assembler, `hgr_fixed_rowlo/hi` expose the offsets (HI without video base).
OR HI with $20/$40 to form the addresses. The data alone
imports no C runtime. `hgr_rowptr_on_page` also offers an
entry point A=page, Y=line, result in A/X, NULL for an invalid input; this kernel
shares cc65's tmp2 and the C wrapper's member, so it requires the cc65 runtime.
The native walk and the C wrapper are measured separately: the cost of repeated
C calls does not make a scanline optimisation.

## Real consumer dependencies

The cc65/ca65 `.d` files track transitive includes, including those
of `HGRC_EXTRA_SRCS`. For two-step C compilation, the dependency is
reassigned from the generated assembler to the final object. The tests modify a
nested header and an assembler include located outside the library,
then check the rebuild, the binary change and the following no-op.

## Background rebuilt from a tilemap

`hgr_tilemap_init` validates a borrowed context: a 40×24 map of 960 IDs,
1..256 tiles of 7×8 pixels, eight HGR bytes per tile with their palette.
`hgr_tile_restore(&bg,page,col,row,width,height)` rebuilds a region
in tile coordinates, clipped at right/bottom, without changing the drawing
page or the display. Validation of all IDs precedes any write;
a rejection leaves the image intact. Map and bank must stay valid outside
video memory; an invalid initialisation keeps the old context.

The application restores all its old/new dirty regions before
drawing the affected layers, and keeps a separate history per page.
This optional backend is used with the masked blitter `hgr_ms_run` (explicit
internal contract in `hgr_internal.h`) to avoid the save-under pool.
The historical engine keeps its saved-background restoration.
An eight-tile region with two masked draws costs 9 546 cycles in
the benchmark; the cost of a whole page remains to be budgeted for each game.
The `HGRC_TILEMAP_SRCS` family is extracted only when it is called.

The `HGRC_HEADERS` dependencies also include the `apple2c` headers,
included transitively by `hgr.h`, so that C consumers are recompiled when
the platform contract changes.
