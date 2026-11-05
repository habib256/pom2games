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

Mutable HGR rows and their native builder live in `hgr_build_rows.s`;
`hgr_row.s` and `hgr_show_page.s` are separate members. Plain drawing
clients omit the page manager and its 50-byte LORES state. Display-only
clients omit all mutable tables. The builder takes 6,921 cycles cold,
19 warm, with no C-stack use; `hgr_row(191)` takes 52 cycles and returns
NULL for every input above 191 without initializing tables. Display takes
29/30 cycles, treats every nonzero page flag as page 2 and retains the
soft-switch sink write. `hgr_set_draw_page` still shifts initialized HGR
and LORES tables synchronously. `test_hgr_rows.py` checks cold bases,
all 256 row inputs, page normalization and display truth values
on II+ and IIe.

`hgr_set_draw_page.s` normalizes the page argument and updates both table
families without a C software stack. Selecting the same page takes 79
cycles instead of 246. A page-2/page-1 round trip takes 4,666 cycles
instead of 5,018, or 5,615 instead of 8,904 with LORES tables already built.
`hgr_lores_state.s` owns the independent 50-byte LORES state: default-page
LORES clients omit HGR rows and page management, saving 388 RAM bytes and
391–420 loaded bytes in the point/read/clear benchmark clients. Explicit
page selection still imports both table families. The row test checks all
256 page arguments before and after LORES initialization, including
synchronous row updates and preservation of the displayed page.

The independent column, mask and phase builders fill seven pixels at a
time, with one pointer advance per byte column. Their code totals 130
bytes instead of 184. Cold calls take 4,040–4,044 / 4,520–4,524 /
4,440–4,444 cycles instead of 7,029 / 8,434 / 6,749 in the alignment fixture;
warm calls retain their constant-time guard. They clobber A/X/Y and ptr1
only. `test_hgr_x7_tables.py` checks every byte of all tables at all 256
alignments, boundary guards, warm no-rebuild and IIe boundary alignments.
The optional folded builder uses a seven-byte mask lookup and fills the
last 24 positions by copying positions 4..27, adding 36 to their columns
(256 = 36×7+4). This removes per-pixel subroutine calls and takes 74 code
bytes / 10,327–10,350 cycles instead of 77 / 15,084. It clobbers only
A/X/Y and tmp1, with no extra RAM or zero page. When all three tables are
used, it saves 56 code bytes, two BSS bytes and initialization time versus
the independent builders. Programs needing fewer tables can still save
RAM by leaving the option off. See the [option table](../ABI.md#speedram-options).

Costs measured by `make bench` (cycles at 1.02 MHz): clearing a page
46 000 (self-modifying loop from `HGR_CLEAR_LOOP`, lib/apple2), page flip
via `hgr_flip_rows` (unrolled loop, one EOR per line), 8x8 text
`hgr_puts8` 7 751 for "APPLE II" (glyph shifted across two bytes per
line), 16x16 text `hgr_puts` through the colour blitter with the white
carriers `$7F/$7F` (a single blitter, ~5 times faster than the old
pixel-by-pixel drawing). The C wrappers read `hgr_col7` / `hgr_phase7` /
`hgr_mask7` instead of dividing by 7, and the line tables are computed
without multiplication.

Warm point calls, including C arguments, take 247 cycles for
`hgr_plot(139,40)` and 256 for `hgr_unplot(279,191)` (previously 271/277).
Resolving the row before the column avoids two temporary bytes and saves
14 code bytes; the allocated zero page is unchanged. The aligned sprite
loops also save 6 code bytes by omitting a carry that cannot occur within
a visible scanline. Pre-shift selection skips the height × stride product
for phase zero without growing the code.

The preshifted-sprite C entries are now native, separate archive members.
They share descriptor/coordinate validation; XOR-only clients omit the
general entry. After the entry conversion and the faster phase product
below, loaded clients save 142 bytes for XOR alone, 119 for the general
entry, or 87 when both are used. C-stack peaks fall from 5 to 3
bytes for XOR and 6 to 5 for the general entry. Calling setup and the XOR
kernel directly reduces the XOR hardware-stack peak from 10 to 8 bytes.
RAM and zero page are unchanged. A 7×16 XOR now takes 1,986 / 2,107 / 2,187
cycles at phases 0/3/6, compared with 2,080 / 2,468 / 2,546 before the entry
and phase-product changes; a clipped XOR falls from 1,070 to 695. An empty general-entry call takes 204 instead of
207 cycles; the dedicated XOR rejection falls from 208 to 169.

Phase offsets use the smaller of stride/height as the multiplier. Below
ten, repeated additions keep the low result in A and start with one copy;
otherwise eight shift/add steps form the product. Both loops take at most
eight iterations, and phase zero still skips the product. The setup code
grows from 151 to 190 bytes (+39), with no extra RAM or stack. Representative
setup calls fall from 563 to 297 cycles (stride 2, height 16, phase 3) and
6,210 to 530 (255×255, phase 6). A one-row case costs four extra cycles
(228 → 232). The arithmetic keeps the original dimensions before clipping.
`test_preshift_setup.py` checks 64,260 combinations normally; `--full` or
`make test-preshift-setup-full` checks all 910,350 nonzero dimension/phase/
placement combinations, including 16-bit pointer wrap and preserved tmp4.

Rows are built even for rejected calls; columns and phases are built only
for a valid descriptor and coordinates. `test_preshift_bounds.py` compares
1,304 paired frames and 160 cold calls per configuration, including every
byte stride/height, all seven phases and modes, both pages and screen
holes. It supports II+ and IIe with normal/folded table builders. The
internal `hgr_xs_run` entry remains available with its existing contract.

`hgr_blit7.s` implements the C entry directly. It clips against the space
remaining to the right/bottom, keeping the original source stride, and
loads the existing sprite parameter block without stack locals. Isolated
clients save 92 loaded bytes; their C-stack peak falls from 9 to 7 bytes,
with unchanged RAM, zero page and hardware stack. A 4-byte × 8-row SET
sprite takes 1,525 cycles instead of 1,646; a one-byte clipped XOR takes
434 instead of 578. Lazy row/column initialization still occurs for
rejected calls. `test_hgr_blit7.py` covers 2,164 warm and 18 cold cases,
all visible x coordinates and byte dimensions, all modes (including the
existing CLEAR fallback), source row stride, both pages, palette bits
and screen holes. It supports IIe and folded-table variants.

Recolouring alternates even/odd column bodies, selecting parity once per
row. With the native wrapper, `hgr_colorize(7,32,140,16,HGR_ORANGE)`
takes 8,612 cycles. The earlier kernel/carrier pass reduced 11,571 to
8,947 cycles and saved 48 bytes: the shared assembly carrier selector
saved 54 loaded bytes and the rectangle loop grew by 6. RAM,
zero page, clipping and byte-granular colouring are unchanged. The selector
also saves 54 bytes in coloured-text clients. `test_hgr_color.py` checks
all 256 selector inputs, rectangles and tinted text on both pages under
NMOS 6502 and 65C02; invalid colours preserve the carrier parameters.

The 16×16 text kernel skips blank source rows, stores only two alternating
carriers and reuses three cc65 scratch bytes. It walks the destination
columns once and assembles the final two cells with two rotations instead
of repeated right shifts. This saves **30 code bytes and 5 zero-page bytes**.
With the native entries, white/orange `"APPLE II"` takes 14,720/14,839
cycles at phase zero.
A fully filled glyph at phase six also saves 8.1 %;
tables, other RAM and stack peaks are unchanged. `test_hgr_text16.py`
checks all 256 source row patterns and all 96 built-in glyphs under five
carriers, seven phases, both column parities and both drawing pages.

The doubled-text entries in `hgr_text.s` prepare arguments directly, share
one rendering path and retain the white fallback for every color outside
1..4. They save **201 loaded bytes for white / 214 for color** in isolated
clients. C-stack peaks fall **10 → 3 / 11 → 5**, and an empty white string
takes **278 instead of 627 cycles**. RAM and zero page remain unchanged.
The fitting count uses fifteen cells for x=0..8, one for x=256..264, and
bounded subtractions for the middle range, retaining the x index for
column/phase lookup. Tables are still built before coordinate rejection.
`test_hgr_text16_entry.py` checks both C entries over all 65,536 x values,
256 y values, all 256 colors and 240 cold calls, on both CPUs and with
normal/folded tables. Its assembly sink verifies the exact string/font,
position/count and carriers; the rendering oracle checks actual pixels.
The independent `hgr_text16_cells` helper remains available and tested
for all 265 room values, but is no longer linked by these text entries.

`hgr_putu` and `hgr_putu8` share native decimal preparation while retaining
separate archive entries for the two fonts. Six bytes are reserved on the
C stack; the three coordinate bytes move to its new top, freeing their old
slots for the buffer. The text call consumes the coordinates, then the
number entry releases the six-byte buffer. No static buffer or extra RAM
is introduced. Isolated clients save **41 loaded bytes**, C-stack peak
**14 → 9**, with unchanged hardware-stack peaks. Printing 65535 takes
**11,319 / 6,226 cycles** in doubled/native-size text (11,429 / 6,318 before).
`test_hgr_unsigned_entry.py` checks all 65,536 values per font, every x/y
argument bit, caller guards, all 256 stack alignments per entry and real
rendering at decimal boundaries, phases and edges on both CPU models.

`hgr_puti` uses a native seven-byte local buffer and relocates the coordinates
once, like the unsigned entries. The existing text-source pointer retains
the buffer start while the conversion pointer advances past a negative sign.
Unsigned two's-complement negation handles −32768. Its isolated client saves
**74 loaded bytes**, C-stack peak **15 → 10**, with unchanged RAM, zero page
and hardware-stack peaks. Printing −32768 takes **12,325 cycles** (12,469
before), zero **2,622** (2,728), and −1 **3,432** (3,583). The exhaustive entry
test checks all 65,536 signed strings and 1,024 stack alignments, including
both pointer page crossings, on II+/IIe. The pixel test checks 272 scenes
per CPU: signs, zero, decimal boundaries, clipped strings and both pages.

Decimal entries reserve their local frame directly after saving the value
and release it through `addysp`. This follow-up saves another eight bytes
per isolated client and 11–31 cycles on measured warm calls, without
changing stack peaks. The doubled-font unsigned cold call rises from
26,664 to 26,697 cycles (+0.12%); its existing cycle reference is retained.

`hgr_putx` also uses a native local frame. It reserves the converter's
pointer argument, coordinates and five-byte buffer together; the converter
consumes two bytes, text consumes three, then the entry releases five.
The high value byte stays in X and the low byte in cc65 scratch. The shared
hex converter leaves its destination in ptr1 for the text call. Isolated
clients save **38 loaded bytes**, C-stack peak **13 → 10**, with unchanged
RAM, zero page and hardware-stack peaks. FFFF takes **8,682 instead of
8,826 cycles**, zero **2,647 instead of 2,781**, rejected origins **582
instead of 716**. The entry test checks all 65,536 hexadecimal strings,
1,024 stack alignments and 96 rendering scenes on II+/IIe.

`hgr_putu_field` prepares its decimal buffer and both rendering calls in
assembly. The consumed value slots hold the clamped width and digit count,
so these survive the erase call's scratch clobbers. It still erases
`width*18-2` pixels before printing, aligns on the right when the value fits,
and preserves the historical overflow behavior. Invalid origins and zero
width are rejected before allocation. Isolated clients save **157 loaded
bytes**, C-stack peak **17 → 15** (rejections **13 → 5**), with unchanged
RAM and zero page. Padded/overflow/clipped fields take **12,654 / 13,439 /
3,276 cycles**, previously 13,022 / 13,660 / 3,639. The combined warm HUD
saves 144 bytes and falls **29,029 → 28,372 cycles**.
The entry test checks 131,584 calls, all scalar domains, both rendering
argument lists, scratch lifetime and 512 stack positions on II+/IIe.
The 1,144-scene pixel oracle passes on both CPUs with normal/folded tables,
covering all widths, decimal boundaries, overflow, invalid/clipped origins,
pages and palette. The erase path preserves the conversion pointer used
for the following text call; no global formatting buffer is introduced.

`hgr_text8.s` prepares the 8×8 string entry directly from the cc65
arguments. The exact fitting count is `(281-x)>>3` for validated x≤273;
only one high difference bit needs to join the low-byte shifts. The string
pointer survives all lazy builders in the existing text state. Isolated
clients save 74 loaded bytes and their C-stack peak falls from 5 to 3.
Empty/rejected calls also reduce the hardware peak from 7 to 6; RAM and
zero page stay unchanged. `"APPLE II"` now takes 7,751 / 8,498 / 8,389 cycles
at phases 0/3/6. An empty string takes 287 instead of 461, and a final
screen-edge glyph takes 1,090 instead of 1,246. All row/column/phase tables
are still initialized before coordinate rejection.

`test_hgr_text8_entry.py` uses an assembly sink to inspect the actual
kernel arguments for all 65,536 x values and 256 y values, plus 30 cold
calls. It checks clipping, fitting counts, string/font pointers and lazy
tables with normal/folded builders on II+ and IIe. The real glyph tests
and integration tests separately verify the rendered pixels and palette.

The 8×8 kernel uses X for the glyph row and omits a redundant upper-byte
mask: an eight-bit row shifted by at most six fits in fourteen bits.
Together with the shared glyph-address helper, this saves 11 code bytes
and 6.1..6.7 % of the cycles for `"APPLE II"` at phases 0/3/6. RAM, zero
page and stack peaks are unchanged. `glyph_addr` itself saves 3 bytes and
takes 54 instead of 61 cycles including JSR/RTS; it preserves X/Y and
handles unaligned font bases. Its test checks 147,456 calls per CPU model,
including incoming carries and 16-bit address wraparound. The 8×8 rendering
test also covers all 256 source row patterns and the screen edges.

The pixel-rectangle kernel shares edge-mask setup for single-byte and
multi-byte rectangles, omits redundant seven-bit masks, and skips interior
counter setup for a single byte. It saves 42 code bytes without changing
RAM, zero page or stack peaks. With the native C-ABI wrappers, the
140×16 fill takes 4,845 cycles and `hgr_cell(1,4,1)` takes 708. `test_hgr_rects.py` checks 752
C/native fills and clears per CPU model: every edge phase, widths of
1..40 bytes, clipping, both pages, palette clearing and untouched holes.

Byte rectangles (`hgr_fill_rect`) traverse rows backwards with Y as the
offset and pair counter. An odd width enters at the second store; pairs
take 19 instead of 21 cycles. The kernel saves seven code bytes without
changing RAM, zero page or stack peaks. With the native wrapper, a 40×16-byte fill takes 7,097 cycles,
and 39×16 takes 6,985.
`test_hgr_byte_rects.py` checks 2,204 fills per CPU model: all 820 valid
column/width pairs, all 256 fill bytes, clipped/empty rectangles, both
pages, palette bits and untouched screen holes.

The recoloring wrapper is native too (`hgr_colorize.s`), retaining the
same byte-granular effect, clipping and rejected colors. It saves 180
loaded bytes in isolated clients: a one-byte call takes 450 instead of
788 cycles, a clipped call 797 instead of 1,167. The C-stack peak falls
from 10 to 5 bytes and hardware peak from 7 to 6, with unchanged other RAM
and zero page. Cold tests cover the normal and folded table builders;
invalid geometry/colors preserve carrier parameters, and lazy table
initialization still precedes rejection.

The public rectangle/cell wrappers now use native argument loading and
clipping in `hgr_rect.s`, `hgr_pixrect.s` and `hgr_cell.s`. Their isolated
clients save 78, 226 and 25 loaded bytes respectively. A one-byte fill
improves from 406 to 309 cycles; a clipped pixel rectangle from 1,041 to
665. C-stack peaks fall from 5/13/3 to 4/4/2 bytes, and the pixel wrapper's
hardware peak from 9 to 6. Other RAM and zero page are unchanged. Arguments
remain on the software stack through the kernel, then a tail cleanup
avoids an extra hardware-stack byte. `test_hgr_rect_cold.py` verifies valid,
empty and invalid first calls on both pages and CPUs, including all lazy
tables and screen holes. Empty/invalid calls still initialize the same
table families as before.

The packed MSB-first bitmap kernel ends each row before preparing
another source bit and shares the SET/CLEAR/XOR destination store. A
sentinel bit in the source shift register replaces the eight-bit countdown,
and the source-byte index uses `ptr2`'s unused high byte. Those kernel
changes saved 14 code bytes and one zero-page byte.

The native C entry in `hgr_sprites.s` saves another 193 loaded bytes in
isolated clients. It computes the full source stride as
`((width-1)>>3)+1` after rejecting width zero, and clips against remaining
screen space. Its C-stack peak falls from 10 to 7 bytes (8 to 7 on rejected
calls), with unchanged RAM, zero page and hardware stack. Mixed 16×8
bitmaps now take 5,686–6,071 cycles across modes and phases 0/3/6; the
bottom/right-clipped XOR takes 930 instead of 1,206. Empty/invalid calls
retain the same lazy row/column/mask initialization.

`test_hgr_bitmap.py` checks 2,190 warm and 40 cold cases per configuration:
all seven phases, every byte width and 256 source byte values, source
boundaries, full stride under clipping, empty/solid patterns, both pages,
palette and untouched screen holes. Cold calls additionally check the
CLEAR fallback for other mode values and all initialized tables. The
test supports II+ and IIe with normal or folded tables.

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
  clips them to 280×192 and sends the inclusive endpoints to the kernel in
  one pass, including widths above 255 pixels.
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
  preserves the 64 bytes reserved for peripheral firmware. Its native
  kernel takes 5,444..5,561 cycles in the C benchmarks, about 89 % less
  than the former C loop, with 212 fewer loaded bytes in isolated clients.
  Native lazy row-table construction and point writes save
  356 loaded bytes versus the original C implementation in isolated point
  clients; the first/warm point takes 831/204 cycles. Native point reads
  take 149 cycles versus 318 after the table-only pass and save 59 more
  loaded bytes in reader clients. Tables, RAM and zero page are unchanged.
- LORES horizontal/vertical spans and rectangles share a native kernel.
  Fully covered pairs of block rows are written as whole bytes; the
  unmatched edge nibbles are masked. A 40×48 rectangle takes 12,382 cycles
  instead of 280,648 and its isolated client saves 308 loaded bytes.
  Horizontal/vertical lines take 1,175/2,036 cycles and save 92/120 bytes.
  Each wrapper remains an independent archive member; unused wrappers and
  the C cell-address helper are not linked. RAM and zero page are unchanged.
- `hgr_lores_init` returns to native 40-column mode after a DHGR or
  80-column display, with `80STORE` off and reads/writes in main
  RAM. Model detection avoids these soft switches on the Apple II+.

`make test-hgr` compiles and runs the routines in **a2run**, on Linux and
macOS. Its 21 steps compare both video pages with a Python model:
256/280-pixel rectangles, limits, pixels, SET/CLEAR/XOR sprites and seven
phases, white/coloured text, numbers, cells, colourising. Four additional scenes check `gfx` cell text on
page 2, the cursor and the numeric conversions. Thirty-eight minimal
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

The common colour/monochrome rectangle preparation is native. It rejects
empty/offscreen calls before changing the span parameters, clips the
17-bit sum `x+width` to the screen, then produces the inclusive endpoint.
Height is clipped independently, and the argument slots are released before
tail-calling the span kernel. Isolated helper clients save **142 loaded
bytes**, C-stack peak **9 → 5** (rejections **7 → 5**), with unchanged RAM
and zero page. A small rectangle takes **1,023 instead of 1,291 cycles**;
the last pixel with width 65535 takes **671 instead of 988**. The public
colour rectangle, including its native entry, saves 312 bytes and takes
**11,809 instead of 12,267
cycles**; with native monochrome forwarding and axis preparation, a line saves
466 bytes and takes **2,208 instead of
2,796**. The helper’s hardware-stack peaks also fall by one or two bytes.
`test_dhgr_bit_rect_entry.py` checks 328,704 calls on both CPU models:
all x values with one-pixel/maximal widths, every width at both screen
edges, all y/height pairs, rejected parameter state, scratch/caller guards
and 1,024 stack placements. The fixture passes on the original C entry;
real colour/mono tests cover both pages/banks, edges, holes and GFX callers.

`dhgr_fill_bits` also uses a native entry. It turns zero/nonzero into
four identical 0/127 pattern bytes, reads the height and advances the
software stack by one byte. The remaining five argument bytes pass directly
to `dhgr_bit_rect`, including for rejected geometry. Isolated clients save
**63 loaded bytes**, C-stack peak **12 → 6**, hardware peaks **9 → 7**
(rejections **7 → 5**), with unchanged RAM and zero page. A small set/clear
takes **1,071 / 1,072 cycles** instead of 1,244 / 1,245; the last pixel
**721 instead of 890**. The line client saves another 50 bytes and its
C-stack peak falls **20 → 14**. `test_dhgr_fill_bits_entry.py` compares
133,120 calls on both CPUs: every argument bit, all 256 truth values,
raw forwarding, all four pattern bytes even on invalid geometry, scratch
clobbers, caller guards and 1,024 stack placements. The C reference passes
this same fixture.

The native colour entry clips width in colour pixels, then expands its
four argument bytes into the helper's five-byte bit-coordinate frame.
Height stays in X while two shifts with carry produce each 16-bit x/width;
only one extra stack byte is reserved. Invalid x leaves the pattern alone,
while valid x still prepares the pattern for empty/offscreen rectangles.
This follow-up saves **75 loaded bytes**, C-stack peak **12 → 5** (invalid x
**7 → 4**), hardware peak **9 → 7**, with unchanged RAM and zero page.
The small/last-pixel colour cases take **1,143 / 898 cycles** instead of
1,355 / 1,124. `test_dhgr_fill_color_entry.py` checks 67,840 calls on both
CPUs: all 65,536 x/width pairs, all y/height/color bytes, call ordering,
clipped bit coordinates, scratch/caller guards and 1,024 stack placements.
The same fixture passes against the original C entry.

Horizontal and vertical DHGR lines have separate native archive entries.
They sort the endpoints, clip the far edge and form a six-byte rectangle
frame before tail-calling the monochrome fill. The horizontal entry expands
its arguments by one byte, the vertical by two; no local frame or new RAM
is needed. Isolated horizontal/vertical clients save **188 / 248 loaded
bytes**, C-stack peaks **14 / 12 → 6**, hardware peaks **9 → 7** (rejections
**7 → 5**), with unchanged zero page. Forward/reversed short horizontal
lines take **1,191 / 1,213 cycles** instead of 1,323 / 1,478; vertical
lines **2,983 / 2,992** instead of 3,123 / 3,164.
`test_dhgr_axes_entry.py` compares 527,104 calls on both CPUs: both full
16-bit horizontal endpoint domains against three anchors, all vertical
x values and y pairs, byte selectors, clipped/modular extents, scratch/caller
guards and 2,048 stack placements. It also passes against the C reference.
Minimal clients verify that using one axis does not link the other.

DHGR state and its four page functions occupy independent archive members.
Draw-page selection takes **25 / 31 cycles** for pages 1 / 2 and **23** for
an invalid selector (previously 93 / 95 / 78), without C-stack use.
Flip retains the old displayed page in Y across two internal calls that
preserve Y, then tail-calls selection: **211 → 88 cycles**, C-stack peak
**2 → 0**, hardware peak **8 → 6**. The two queries retain their original
24 / 25 / 18-cycle paths. Isolated page clients save **63–105 loaded bytes**;
other measured DHGR clients save **41–111**. Clearing rows before mode
initialization saves **409 loaded bytes and 9 zero-page bytes** because it
no longer imports the mode manager. RAM is unchanged. Code placement shifts
some rendering timings: block writing rises **6,615 → 6,678 cycles** and
the colour rectangle **11,790 → 11,809**; the old cycle references remain
in the regression gate. `test_dhgr_pages.py` checks 131,328 state combinations
on both CPU models, initial state, invalid selectors, flip ordering and the
real show/query register contracts. Minimal clients exclude unused page
functions. The full benchmark has **392 cases**, with 78 changed and 314
identical in this pass.

The full-clear and compact-text C entries are now native. `dhgr_clear`
forwards color to pattern preparation and tail-calls clearing without a
local slot: **39 loaded bytes saved**, **112,456 → 112,391 cycles**, C-stack
peak **1 → 0**, hardware peak **11 → 9**. `dhgr_puts_small` stores the two
coordinates, loads the pointer, releases its three argument bytes directly
and tail-calls the string kernel. Its isolated client saves **37 loaded
bytes**; "APPLE II" takes **13,186 instead of 13,220 cycles**, an empty
string **159 instead of 216**, and the last cell **1,499 instead of 1,555**.
C-stack peak falls **4 → 3**; hardware peaks fall by two bytes, including
empty/rejected calls **6 → 4**. RAM and zero page are unchanged.
`test_dhgr_thin_entries.py` checks **132,352 calls per CPU**: all pointers,
x/y pairs and colors, call ordering, callee coordinate changes, scratch
clobbers, guards and 1,024 stack placements. The original C passes the same
fixture. Eight new cases bring the benchmark to **400 cases**; ten change
and 390 remain identical.

The block transfer controller now uses the caller's six argument bytes
throughout. After validation, the width slot stores stride and the byte-x
slot stores a column plus the read/write flag. Each row loads its address
directly from the immutable row tables, with no extra local frame or
per-row argument push. Read and write have separate native archive entries;
a block-only client does not import the byte-address C-ABI helper.
Isolated clients save **323 loaded bytes**, C-stack peak **18 → 6**
(rejections **16 → 6**), hardware peak **11 → 9**; empty/rejected calls fall
to **4 hardware-stack bytes**. RAM and zero page are unchanged.
Reading/writing 8×8 bytes takes **5,664 / 5,328 instead of 6,990 / 6,678
cycles**. Single-byte calls take **500 / 487 instead of 1,132 / 1,115**;
192-row strips **52,440 / 53,592 instead of 71,731 / 72,115**.
`test_dhgr_transfer_entry.py` verifies **526,336 calls per CPU**, including
all bx/width, width/stride and y/height pairs, all pointers, every row's
address/bank/count/buffer, rejection and zero-height side effects, hostile
scratch registers and 2,048 stack placements. The C reference passes the
same fixture. Eighteen new cases bring the benchmark to **418 cases**:
21 improve and 397 remain identical.

The sprite controller is native too. It validates the full color-pixel
extent against stride before right clipping, computes the bank from the
original height, then clips the visible rows. An eight-step product gives
`height * stride`; phase zero skips it. The total phase offset is formed
once and added once to each pointer. Row addresses and pointer advances use
only the nine argument bytes, including the fastcall mask saved on entry.
Isolated clients save **320 loaded bytes** (226 in the partial/opaque
fixtures that already link other runtime helpers), C-stack peak **18 → 9**
(rejections **16 → 9**), with unchanged RAM, zero page and hardware peaks.
The small sprite takes **1,205 instead of 2,272 cycles**; partial/opaque
14×8 sprites **10,442 / 8,331 instead of 12,210 / 10,105**. Phase-0/6
8-row cases fall **5,839 / 6,525 → 4,062 / 4,435**, and a height-255 sprite
clipped to one row **1,999 → 987**.
`test_dhgr_sprite_entry.py` checks **787,456 calls per CPU**: all x/width,
width/stride and y/height pairs, all data/mask pointers, every height/stride
product at all seven phases, every row address/bank/count/pointer, rejected
state, scratch clobbers, guards and 1,024 stack placements. The original C
passes the same fixture. Fourteen new cases bring the benchmark to **432**;
17 improve and 415 remain identical.

DHGR point address/mask calculation is a separate archive member shared
by plotting and readback. A read-only client no longer links the writer.
The wrappers pass coordinates through existing scratch and release their
arguments directly; readback preserves A/X while incrementing the stack
pointer twice. Isolated readers save **99 loaded bytes**, writers **8**,
with unchanged RAM, zero page and measured stack peaks. Auxiliary/main-bank
reads take **279 / 259 instead of 285 / 265 cycles**; writes of a set bit
**305 / 277 instead of 318 / 293**. Offscreen reads/writes improve too.
The shared locator body is unchanged. `test_dhgr_points.py` checks
**694,336 calls on each IIe/IIc**: every pixel on both pages, all selector
bytes, every invalid 16-bit x and y byte, bank/IRQ restoration, video holes,
byte return values and 2,048 stack placements. It passes before and after
the change. Twenty-one new cases bring the benchmark to **453**; all improve
and the previous 432 remain identical.

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
  Reading/writing an 8×8-byte block takes 5,664/5,328 cycles including C
  arguments. Keeping the bank in A during pointer advances and removing
  a nested setup call saves 15 code bytes and two bytes at the measured
  hardware-stack peak, shared with the masked-sprite kernel. RAM and zero
  page are unchanged. Tests check widths 1..80, all 256 masks, both banks
  and pages, pointer page crossings and both IRQ masks.
- `dhgr_sprite`: x in **colour pixels**, banks precomputed for the seven
  bit shifts, mask 1 = keep the scenery. Each bank holds
  `stride * height` bytes. Saving then restoring a block gives save-under.
- `dhgr_puts`: opaque white/black text, 8×8 glyphs in **colour pixels**,
  four DHGR bits per font dot, to avoid an artifact tint.
  `"APPLE II"` takes 32,246 cycles at x=0, including C arguments, instead
  of 44,259 (−27.1 %). Alternating auxiliary/main writes retains the page
  column in Y; the row counter uses cc65 scratch and the temporary row
  buffer is six bytes. Fresh pair bytes are stored directly; only one
  possible gap needs zeroing. The kernel saves 19 loaded bytes and three BSS bytes,
  without changing zero page or stack peaks. IRQ masking remains per row,
  with main RAMRD/RAMWRT restored between rows. Tests cover all 255 non-NUL
  input bytes, empty strings, seven phases, both pages/banks and IRQ masks,
  plus right/bottom clipping and untouched pixels and screen holes.
- `dhgr_puts_small` (optional family `HGRC_DHGR_SMALL_TEXT_SRCS`): small opaque white font, **4×5 colour
  pixel** glyphs, five-column advance. Accepts every DHGR alignment,
  converts lower case to upper case and keeps the neighbouring pixels.
  An incomplete cell at the right or bottom edge is not drawn.
  The `dhgr_small_text` benchmark (`"APPLE II"`) takes **13,253 cycles**,
  including the C arguments and calls (previously 14,483). The renderer
  prepares the column, ink-table base and edge masks once per glyph, and
  skips auxiliary reads for fully covered bytes: 4 fewer code bytes and
  2 fewer BSS bytes, with unchanged tables and zero-page use.
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
| `HGRC_DHGR_SPR_SRCS` | Flicker-free sprite compositor and save-under cursor (opt-in, not in `HGRC_ALL_SRCS`) |

`HGRC_DHGR_SRCS` keeps the historical set of primitives, transfers and
8×8 text. `dhgr_internal.h` centralises the private parameters and prototypes of the
banked primitives. When compiling manually, `dhgr_state.c` provides
only the state; the four page functions have their own assembly files.
Use the family lists above to include their dependencies. The assembler kernels for masked writing, reading,
clearing and scanlines are separate objects. The pixel address and the
colour pattern are shared, while each read, point, rectangle
and clear API keeps its own object. The small-font parameters are
separate from the native wrapper: an assembler HUD does not pull in `dhgr_puts_small`.

Selecting families is not enough to eliminate every unneeded function
if their objects are passed directly to ld65. Building an ar65 archive and
placing it after the application objects lets ld65 extract only the
referenced members and their dependencies. ChromaBreak follows this rule with
`platform.lib`, including for the Apple II, ProDOS and mouse modules. Its test
checks the link map to exclude generic pixels, rectangles and transfers,
8×8 text and unused text wrappers. The library tests also check
59 minimal consumers of the archive.

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

### Flicker-free sprites (compositor)

`dhgr_spr_*` (in [`dhgr.h`](dhgr.h)) composes sprites over a background
without erasing anything on screen: each update rebuilds the changed area
in a borrowed buffer, then writes **each changed screen byte once, with its
final value**. Nothing is drawn twice, nothing blinks, on one page (no
double buffering needed). The family is opt-in: add `HGRC_DHGR_SPR_SRCS` to
`HGRC_EXTRA_SRCS` (or to the program's own library sources), next to the
DHGR state and tables (`HGRC_DHGR_SRCS`). Programs that do not ask for it
keep the same archive and binary.

**Group alignment.** Seven colour pixels are 28 dots, exactly four bytes
(aux, main, aux, main) at bank offsets 2g and 2g+1, group g = x/7; a
pixel's four dots are its colour's nibble `DHGR_NIB(c)` = `((c>>1)|(c<<3))&15`
at every position. The compositor therefore works in whole groups: a chunky
**canvas** (one byte per colour pixel, the nibble) of a few groups by a few
rows is packed with a fixed shuffle, `b0 = n0|(n1&7)<<4`,
`b1 = n1>>3|n2<<1|(n3&3)<<5`, `b2 = n3>>2|n4<<2|(n5&1)<<6`,
`b3 = n5>>1|n6<<3`, computed with one 16-byte table `n<<4` and a carry
(~77 cycles a group). A piece holds at most 255 canvas bytes, so one index
register addresses it: rectangles are filled by an unrolled
`sta canvas+k,y` sequence (5 cycles a byte, strips of 8 columns) whose
operands are patched with the canvas address at the first update after
`dhgr_spr_init` (or after an overlay window reloaded the code). A RECTS
shape lying wholly inside the piece is painted without any clipping, one
inside horizontally with its rows clipped only; its rectangles must lie
inside its `w`×`h`.

**Update.** `dhgr_spr_set` / `dhgr_spr_palette` / `dhgr_spr_invalidate` /
`dhgr_spr_overlay` only record. `dhgr_spr_update` collects the damage as
group/row rectangles (each changed slot's old and new boxes, the
invalidations, the overlay's old and new boxes) clipped to the **area**
(`dhgr_spr_area`, widened to whole groups: the compositor never writes
outside it), merges overlapping ones into their bounding box until none
overlap (each entry absorbs every entry it overlaps, scanning them again
after each absorption; an earlier entry absorbs it instead and takes its
place: O(n²) compares, where the first version restarted from the first
entry after each merge, O(n³): 11,000 cycles a frame in the action demo),
and cuts each into canvas pieces. For each piece: background, then
every slot crossing it back to front (slot 0 first), the overlay's bits, and
the write. The write masks IRQs only around each group's two auxiliary
stores (about 30 cycles); RAMWRT is main again before each `plp`.

| Call | Use |
|---|---|
| `dhgr_spr_init(canvas, bytes, groups)` | Borrow `bytes` of main RAM (outside $2000-$5FFF, at most 255 used) only inside `dhgr_spr_update`; pieces of at most `groups` (1..20) groups, a piece of n groups `min(bytes, 255) / (7*n)` rows. Forgets slots, damage, overlay; area = screen, background = black. 0 unless `min(bytes, 255) >= 7*groups` |
| `dhgr_spr_area(x0, y0, x1, y1)` | Inclusive colour-pixel box owned by the compositor, widened to groups. Off-screen/reversed boxes are empty. Set it before invalidating |
| `dhgr_spr_solid(c)` | One-colour background |
| `dhgr_spr_tiles(ox, oy, cell_h, map, map_w, set)` | Tile map: cell (col, row) at `ox+7*col`, `oy+cell_h*row` shows `*set[map[row*map_w+col]]` (any shape kind; NULL draws nothing). Swap a `set` entry (an open door) and invalidate its cells |
| `dhgr_spr_cells(ox, oy, cell_h, paint)` | C callback `paint(col, row)` covering its whole 7×`cell_h` cell with `dhgr_cv_rect` (screen coordinates, clipped to the piece) |
| `dhgr_spr_set(id, shape, x, y, flags)` | Slot `id < DHGR_SPR_MAX`; NULL shape or `DHGR_SPR_HIDDEN` hides, `DHGR_SPR_MIRROR` mirrors. Unchanged arguments do nothing |
| `dhgr_spr_palette(id, four)` | Colours 16..19 of the slot's RECTS shapes (body, lights...) |
| `dhgr_spr_invalidate(x, y, w, h)` | Redraw a box whose background changed |
| `dhgr_spr_overlay(bx, y, w, h, bits, under)` | Byte-domain OR layer above everything (a pointer): recomposed in the area, saved/restored outside it (`under`: 2 × the largest w×h used, w×h ≤ 127). With `DHGR_SPR_OVERLAY_INSIDE` only its part in the area is drawn |
| `dhgr_cursor(bx, y, w, h, bits, under)` | The same save-under cursor without the compositor, drawn at once |
| `dhgr_spr_present()` | `DHGR_SPR_DOUBLE`: at the next VBL edge, show the draw page and draw on the other one (below) |

Shapes (`dhgr_shape_t {kind, w, h, n, data}`, immutable while used):
`DHGR_SHAPE_RECTS` (n × {x, y, w, h, colour} inside the shape's w×h,
colours 16..19 from the slot palette: compact, mirrored by
`x' = w - x - rw`), `DHGR_SHAPE_CHUNKY`
(w×h colours, `DHGR_CLEAR` transparent, mirrorable) and `DHGR_SHAPE_TILE`
(w×h `DHGR_NIB` nibbles, opaque, copied straight, not mirrored).

**Once-per-byte rule.** Every byte of a piece is stored once; pieces of the
merged rectangles are disjoint; the save-under cursor runs one pass over
old ∪ new outside the area (each byte read once — the saved copy where the
old cursor was, else the screen — saved if the new cursor covers it, then
written once). `dev/tests/test_dhgr_spr.py` checks it with a2shot
`storewatch` on every update: the stored (bank, address) set equals the
model's damage, each stored once with its final value; aux stores run with
IRQs masked, main ones not.

**Canvas borrowing.** The canvas is touched only inside `dhgr_spr_update`
(and `dhgr_cv_rect` in a paint callback): 255 bytes are enough (2 groups ×
18 rows, 4 groups × 9 rows), so the start of an idle ProDOS I/O buffer
does. Smaller canvases work (more pieces, a little slower); the test also
runs a 70-byte one.

**Costs** (`dev/bench`, //e, call included; a 10×12 RECTS drone of
Robot Space Station moved one pixel in a room of 7×8 RECTS tiles):

| Case | Cycles | First version |
|---|---:|---:|
| `dhgr_spr_move` (tile map, 2 groups × 12 rows rewritten) | 15,939 | 20,241 |
| `dhgr_spr_move_wide` (same, 3 groups) | 20,667 | 26,184 |
| `dhgr_spr_move_cells` (C `paint` callback) | 18,776 | 22,843 |
| `dhgr_spr_move_solid` (one-colour background) | 11,025 | 14,341 |
| `dhgr_spr_move_chunky` (6×5 CHUNKY ship over TILE tiles) | 9,380 | 10,461 |
| `dhgr_spr_overlay_move` (4×6-byte pointer moved, room recomposed under it) | 13,196 | 20,412 |
| `dhgr_cursor_move` (4×6-byte save-under cursor, one byte and one row) | 9,003 | 9,019 |
| `dhgr_spr_double_move` (`DHGR_SPR_DOUBLE`, one pixel a frame: this move and the previous one rewritten) | 16,697 | — |
| `dhgr_spr_vbl_move` (`DHGR_SPR_VBL`, started at a VBL edge: composed, then written after the next edge) | 21,871 | — |

Robot Space Station erased and redrew the same drone in 35,000-45,000
cycles before it moved to the compositor (2026-10-31: a drone turn went
from 5.0 / 8.0 / 11.4 to 4.1 / 4.2 / 6.3 frames on the //e in missions
1 / 4 / 7). Time of `dhgr_spr_move`: about 4,500 cycles pack + write (24
groups), 6,500 painting (21 rectangles, 290 bytes stored), the rest tiles
walk and bookkeeping. `dhgr_spr_overlay_move` no longer runs the
save-under pass while the pointer stays inside the area.

Code (6502), the core every program links: calls 252 B (`dhgr_spr_set`,
`dhgr_spr_invalidate`, `dhgr_spr_solid`), init + update 872 B, write 304 B
(with the 16-byte table and the 51-byte patch list), canvas painters 532 B:
1,960 B (2,120 B before the 2026-10-31 size pass, 2,473 B in the first
version; the 1.8 KB target is not reached). Members linked when called:
`dhgr_spr_palette` 53 B, `dhgr_spr_area` 64 B, bitmap shapes 392 B
(`dhgr_cv_bitmap.s`: its row loops no longer recompute the canvas row,
`dhgr_spr_move_chunky` −6 %), cells/tiles + `dhgr_cv_rect` 406 B (see the
cell background row setup below), overlay 420 B (`dhgr_spr_overlay.s`: the overlay's damage and OR hooks, called
through `JMP`s that `dhgr_spr_overlay` installs), save-under cursor 750 B
(`dhgr_spr_cursor.s`, also the overlay's part outside the area),
`dhgr_spr_present` 111 B (`dhgr_spr_present.s`). The size pass: one
clipping loop for both axes in piece coordinates and one rectangle loop for
the unclipped and clipped paths (its row offsets patched once per shape),
the area clip as a loop over the four fields, one initialisation loop,
palette and area in members of their own. BSS: 270 B with
`DHGR_SPR_MAX=8` (246 B with 7), plus 63 + 4 + 13 + 14 + 16 + 4 B in the
members. No new zero page: cc65's `ptr1`-`ptr4`/`tmp1`-`tmp4` and the
`aux_read` stub.

| Option (`HGRC_DEFINES` / `-D`) | Effect |
|---|---|
| `DHGR_SPR_MAX` | Slots 1..8 (default 8); BSS −24 B per slot removed. Same value for the program's C and the library |
| `DHGR_SPR_PACK_TABLES` | Accepted, no effect: the single 16-byte table is now the default (faster than the nine tables of the first version) |
| `DHGR_SPR_CODE_SEGMENT` | All code and tables in segment `DHGRSPRCODE` (place it in an overlay window; BSS stays resident). The code is self-modifying and re-patched on every call, so a reloaded overlay is fine |
| `DHGR_SPR_RECTS_ONLY` | No bitmap shapes: `dhgr_cv_bitmap.s` is not linked (−392 B) |
| `DHGR_SPR_OVERLAY_INSIDE` | The overlay is drawn only inside the area (no save-under part, `under` unused): `dhgr_spr_cursor.s` is not linked (−764 B). Robot Space Station draws the pointer's rows outside the room with its own save-under code |
| `DHGR_SPR_DOUBLE` | Two pages (below): +198 B code and +106 B BSS in the update (+86 B in `dhgr_spr_cursor.s` when the overlay leaves the area), `dhgr_spr_present` 111 B, apple2vbl linked. Not with `DHGR_SPR_VBL` |
| `DHGR_SPR_VBL` | One page, the write timed after a VBL edge (below): +260 B code in the update, apple2vbl linked |

**Two pages (`DHGR_SPR_DOUBLE`).** For games that can give up page 2
(Robot Space Station cannot: its overlays live there). Every update draws
on the draw page, which is hidden, then `dhgr_spr_present()` shows it at
the next VBL edge and draws on the other page: nothing is ever stored into
the shown page. The hidden page last received the frame before the shown
one, so an update writes what changed since **that page** was drawn: its
own damage (merged first) joins the damage the other page received
meanwhile (a list kept for the page that has not had it, 22 rectangles,
widened when full), and is kept in turn for the other page. Updates
without a present in between keep adding to that list. The slots' boxes
stay single: the old box of a moving sprite is in the previous frame's
damage. Start with the shown page and the draw page different
(`dhgr_draw_page(2)` after `dhgr_init`) and invalidate the area: both pages
converge after two updates. The overlay's part outside the area is saved
per page: page 1 in `under`, page 2 from `under + 254` (`under`: 254 + 2 ×
the largest w×h). `dhgr_cursor` stays a one-page call. `dhgr_spr_present`
waits for the edge with dev/lib/apple2c/apple2vbl (link `APPLE2C_VBL_SRCS`,
`APPLE2C_FRAME_SRCS` and the mouse): mode 1 (//e) polls `$C019` (the
picture, then the blank: a fresh edge, the flip ~20 cycles after it), mode
2 (a mouse's VBL interrupt: //c, //e with an AppleMouse) waits for the
handler to count a refresh (interrupts enabled), mode 0 calls
`a2_frame_wait` (bounded VBL poll or delay); each wait is bounded (~45,000
cycles) and flips anyway. The edge it waited for is counted in
`a2_vbl_count`. The [action demo](../../examples/dhgr_action/README.md)'s
frame (five 6×6 enemies and a ship over a tile arena): 63,000-67,000
cycles of work on the //e, a frame every 4 refreshes (15 frames/s).

**VBL-timed write (`DHGR_SPR_VBL`).** For one-page games: when an update's
damage is a single piece that the write can finish ahead of the beam, the
piece is composed first, then the update waits for the next VBL edge and
writes it: each row is stored before the beam starts it (no tear). The
condition, k rows from row y: `LAT + k × (95 + 165 × groups) ≤ 4,550 + 65
× (y + k − 1)` (LAT 100 cycles on the //e, 1,200 on the //c; the 95/165
figures include page crossings): 15 rows of a 2-group sprite at row 20, 12
at row 0. Several pieces, too many rows, the overlay crossing the piece or
no clock: the plain order, no wait. The clock is apple2vbl (`a2_vbl_mode`
1: `$C019` polled by the update itself; 2: the mouse VBL interrupt's count;
0: the plain order). The wait costs up to a refresh: a game that updates
once a frame loses nothing, one that updates several times a frame should
not use it. `test_dhgr_spr.py` checks with `storewatch`'s cycle stamps that
every store of a waiting update comes before the beam reaches its row
(rows 19-191 on the //e, least lead 1,310 cycles). Robot Space Station's
PLAY window has 227 B free after the size pass (162 before): the 260 B of
the option do not fit there.

Contract: fastcall cc65 ABI, non-reentrant, never from an IRQ; main
RAM/ZP on entry and exit; draws on the draw page, display unchanged (but
`dhgr_spr_present`).
The screen outside the area may change only while the overlay is hidden;
change a cursor's w×h only while it is hidden. Background changes inside
the area need `dhgr_spr_invalidate`.

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
- `python3 dev/tests/test_dhgr_spr.py` (in `make test-dhgr`): the
  compositor on //e and //c, seven canvas/option builds (one with
  `DHGR_SPR_OVERLAY_INSIDE`; `double`: `DHGR_SPR_DOUBLE`, both pages
  against a two-page model, the shown page equal to the whole frame
  composed afresh after each present, no store into it; `vbl`:
  `DHGR_SPR_VBL`), 61 or 62 scripted updates each against the model plus
  the storewatch write-once check, a VIA IRQ run, and the VBL timing run
  (each store of a waiting update before the beam reaches its row).
- `python3 dev/tests/test_dhgr_action.py` (`make test-dhgr-action`): the
  [action demo](../../examples/dhgr_action/README.md) on //e and //c.
- `make test-dhgr`: 21 historical checks + 48 additional checks,
  two pages/banks, two backends, sprites, blocks, text, transitions and II+ rejection.
  The POM2 IIe core in `a2shot` is required (macOS arm64 or Linux x86_64).
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

The public `hgr_line.s` entry validates both endpoints and prepares the
existing kernel parameters directly. Axis calls reuse the caller's stack
slots and tail-call the horizontal/vertical routines. Together with the
separate native axis entries, isolated line clients save **238 loaded bytes**
compared with the former C line and axis entries. Diagonal C-stack peak falls
**6 → 5**, reversed horizontal **13 → 5**, vertical **11 → 5**. RAM and zero
page stay unchanged. Short lines take **709 cycles** (811 before both passes),
reversed horizontal **1,083** (1,445), forward/reverse diagonal **20,927 /
20,835** (21,009 / 21,005). The long vertical through `hgr_line` takes
**11,738 instead of 11,618 (+1.03 %)**; this layout-sensitive cost remains
an explicit tradeoff, and existing cycle references are not relaxed.
The entry test checks 131,584 coordinate cases, exact axis/core arguments,
rejected-call table state and a caller stack guard. Both the entry test and
464-line rendering oracle support II+/IIe with normal/folded tables.

`hgr_hline.s` and `hgr_vline.s` are separate archive members. A client using
only one axis no longer loads the other. Compared with `hgr_geom.c`, isolated
horizontal/vertical clients save **235 / 269 loaded bytes**. Reversed spans
use **4 / 3 C-stack bytes**, down from 7 / 5; RAM, zero page and rendered
hardware-stack peaks are unchanged. The reversed full-width horizontal
falls **1,175 → 918 cycles**, and a clipped one **1,181 → 912**. The full-height
vertical falls **11,401 → 11,302**, reversed **11,485 → 11,311**. Sorting uses
the complete coordinate widths before clipping, so a reversed endpoint at
65535 still clips correctly. Rejected spans do not construct tables.
The axis entry test checks 524,544 parameter cases on both CPUs; 126 cold
rendering cases check both pages, palettes, screen holes and table contents
with normal/folded builders on II+/IIe.

## HGR rectangles: full bytes in pairs

`hgr_fill_rect` (byte columns, `hgr_byte_rect_asm.s`) and the pixel
rectangles and spans (`hgr_fill_pixrect`, `hgr_clear_pixrect`, `hgr_hline`,
`hgr_vline`, `hgr_fill_span`, through `hgr_pixrect_asm.s`) count their full
bytes once per call, as pairs and an odd byte, and each scanline stores them
two at a time (21 cycles a pair) instead of comparing the column after every
byte: `hgr_rect` (140×16 pixels) 6,117 → 5,213 cycles, `hgr_byte_rect`
(40 columns × 16 lines, a new bench case) 9,266 → 7,824, `hgr_span` (a
280-pixel line) 1,096 → 993. +21 and +28 bytes of code; `ptr2`, already
imported by the pixel kernel, holds its two counts, the byte kernel uses
`tmp3`/`tmp4`. `test_hgr.py`, `test_gfx_outlines.py` and `test_hgr_lines.py`
check the pixels, clipping, holes and both pages.

## DHGR clearing with IRQ servicing

`dhgr_clear_rows(y, rows, color)` fills the visible lines of the drawing
page, clips at 192 and preserves the memory holes. Each line restores
main RAMWRT and the caller's IRQ mask; enabled IRQs can
be serviced between lines. The measured kernel takes 688 cycles a line
(712 before), under a tested bound of 1,300: a line never crosses a page
and starts at most at offset $D0, so four passes (one a pattern byte) store
through five page-aligned operands, Y walking the line two bytes at a time,
five cycles a byte; only the page byte of those operands is patched, while
RAMWRT is main. 117 bytes of code (129 before). X counts the four turns
of each pattern pass; the row's high address byte is passed in A directly
to the operand patches. This removes 12 code bytes without changing RAM,
zero page or stack peaks in that kernel change.
The public entry now validates and clips the two argument bytes directly,
prepares the pattern, then releases the arguments before tail-calling the
row kernel. No local frame is needed. Isolated clients save another
**94 loaded bytes**, C-stack peak **5 → 2**, hardware peak **11 → 9**, with
unchanged RAM and zero page. Including C arguments, one visible line takes
**929 instead of 1,090 cycles**, 16 lines **11,549 instead of 11,725**,
and all 192 lines **136,214 instead of 136,555**. Empty/rejected calls need
only two C-stack bytes and leave the pattern untouched.
`test_dhgr_clear_rows_entry.py` checks 67,072 calls on both CPU models:
all y/count pairs, all colors, exact forwarded arguments, scratch clobbers,
caller guards and 1,024 stack placements. The fixture also passes on the
original C entry.
A test with a Mockingboard VIA timer also checks that periodic IRQs
are actually serviced during both page clears, with checks on
banks, memory guards and pixels. Servicing remains non-reentrant. Use small
slices so that input is also handled between calls.

`dhgr_clear(color)` fills both banks of the drawing page, holes included,
in 112,391 cycles instead of 187,309: each 256-byte page is two passes
(even bytes, odd bytes) of one pattern byte through eight absolute stores,
five cycles a byte, whose page operand is patched while RAMWRT is main (a
write under RAMWRTON would land in the auxiliary copy of the code). IRQs
are masked one page at a time, about 1,750 cycles, instead of the whole
clear (eleven refreshes). 97 bytes of code, one less than before; same
zero page (`ptr1`, `tmp1`). `test_dhgr.py` and `test_dhgr_clear_rows.py`
check the sixteen colours on both pages and banks, holes and display
switches included.

The interior of a coloured span (`dhgr_fill_rect`, `dhgr_hline`,
`dhgr_vline`, `dhgr_fill_bits` through `dhgr_span_asm.s`) is prepared once
per call for each bank: first page column, number of byte pairs, odd last
column, and the two pattern bytes in column order. Each scanline then runs
one pair loop per bank (27 cycles for two bytes, no compare) and the odd
byte, instead of a byte loop that reloaded the pattern and compared the
column at every store: `dhgr_rect` (70×16 pixels) 15,034 → 12,267 cycles,
`dhgr_span` (a 560-dot line) 3,279 → 2,796; +50 bytes of code and 6 of
BSS. `test_dhgr_spans.py` covers single and adjacent edges, odd and even
interiors in both banks, the full width and clipping.

The host reference `hgr_inflate_x2` (`hgr_x2.c`) and the target version
(`hgr_x2_target.s` + `hgr_inflate_x2_asm.s`) compute the enlarged strides
without 8-bit truncation; `hgr_x2_target.c` remains the cc65 C reference.
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

`HGRC_VECTOR_SRCS` and the default archive use `gfx_line_hgr.s`, which
routes diagonals to the assembler `hgr_line`. The axis-aligned lines of `gfx_line`
keep their historical span clipping; `hgr_line` rejects any
off-screen endpoint, axis-aligned lines included. Valid diagonal pixels are identical.
For DHGR or an external backend, use `HGRC_GENERIC_VECTOR_SRCS`
(`gfx_line.s` + `gfx_rect.s`), with exactly one explicit backend.
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

Both HUD initializers use font-specific native entries and a shared
bounds/store routine. They reject large origins before adding the cell
extent, then check the whole box and write only x/y/width/valid; history
bytes stay intact.
Isolated initialization clients save **287 / 160 loaded bytes** for the
16×16/8×8 formats. A valid origin takes **301 / 290 cycles** instead of
870 / 563; C-stack peaks fall **10 / 8 → 5**, hardware peaks **8 / 7 → 5**,
with unchanged RAM and zero page. HUD update clients save **239 / 134 bytes**.
Code placement changes some composed render timings by up to +0.54%; the
existing cycle references remain in force. `test_hgr_hud_init.py` compares
268,288 calls on both CPUs: all x/y/width domains, exact box edges, NULL,
untouched histories/guards, a state pointer crossing a page and 2,048 stack
placements. The same fixture passes against the original C entries.

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
It also sweeps every valid one-cell horizontal origin (265/273 positions
for 16×16/8×8) and all field widths, including cached +1/+2 and overflow.
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
five digits costs at most 6,663 cycles over the benchmark's seven phases,
against 15,819 for the 16×16 format. Prepare both pages before animating.

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
Both controllers reuse the digit count returned by conversion/compaction
and finish the origin's division by seven in eight bits after reducing it
below 56. This saves 24 code bytes per format without adding RAM or tables.
The 16×16 single-digit update takes 3,940 cycles; an unchanged value still
takes 312 cycles in either format.

The 16×16 kernel writes its second byte column directly to both scanlines:
that column always lies wholly inside the 16/18-pixel cell. Its other
columns retain their edge masks. Two rotations assemble the upper glyph
bits, and the three edge writers expand in place instead of calling
single-use subroutines. This saves 42 code bytes and one BSS byte, with
unchanged zero page and measured stack peaks. Five changed digits take
15,032..15,888 cycles across the seven phases, about 17 % less than before.

The compact kernel counts the source offset in X and uses the existing
`tmp1` scratch byte, removing 18 code bytes and two BSS counters. A single
digit update takes 2,282 cycles. Glyph arguments (`hgr_glyph_params`, five
zero-page bytes), string traversal (`hgr_text_params`, five bytes), and
font lookup (`hgr_text_addr`, two bytes plus 26 code bytes) are separate
archive members. A HUD8-only client therefore saves 44 code bytes,
seven zero-page bytes and two BSS bytes in total. A HUD16-only client
saves five zero-page bytes. Clients combining HUD and text share these
members without duplicating the parameter blocks.

The tests check 168 updates with decimal carry and wrap and 70 digits placed
against the right and bottom edges, in all seven phases. The same oracle
runs on a2run and POM2 IIe. The examples prepare both HUD
histories before their loop, to move this cost to load time.

The masked sprite kernels keep their phase-block product in existing
cc65 scratch, reusing the full-height byte after copying it into X. Their
clipped row address cannot carry into its high byte. Generic column loops
run backwards, with Y as offset and counter, while the narrow unrolled
paths retain their specialisation. Together this saves eight code bytes
and two zero-page bytes, with unchanged RAM and stack peaks. Generic
7-byte × 8-row draw/save/restore/save-and-draw calls take
2,885/1,791/1,802/3,232 cycles (4.9..8.2 % less). The native tests cover
all four entries, large strides and heights, products crossing 255, every
phase, both pages and save-under guards on NMOS and 65C02.

Three further passes share the save-under row tail, skip the unused
height/stride product in phase zero and keep its low byte and the cached
block in registers. They save another 25 loaded bytes per masked-sprite
client without changing RAM, zero page or stack peaks. At that stage, generic
draw and save-and-draw took 2,836 and 3,183 cycles. A height-255 phase-zero
sprite clipped to one row took 399 instead of 5,251 cycles. Draw still consumes
the one-call block hint, while save and restore preserve it. The full setup
oracle checks 1,827,868 calls on each CPU, including every nonzero stride
and height, all seven phases and all 256 hint values. Small timing tradeoffs
and the full-suite results are recorded in the benchmark history.

Both masked and preshifted setup now clip by comparing the source dimensions
with the screen space remaining (`40-column`, `192-y`). This saves another
14 code bytes per kernel and handles all byte-sized dimensions without
overflow branches. Masked setup also reads its persistent stride directly,
saving two more code bytes. Full source dimensions remain available for
phase offsets. RAM, zero page and stack peaks are unchanged. The masked
height-255 phase-zero case now takes 389 cycles; the clipped preshifted XOR
takes 678 instead of 695. Generic masked draw/save/restore/save-and-draw take
2,841/1,783/1,794/3,188 cycles, slightly above the preceding layout. Exhaustive
setup tests cover all nonzero dimensions and seven phases on both CPUs.

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

The native initializer scans three 256-byte blocks and a 192-byte tail.
It keeps `count-1` in A and compares each ID directly through the map
pointer; a count of 256 skips the scan because every byte is valid.
The original pointers remain in the argument slots until validation succeeds,
then the six-byte context is committed. Isolated clients save **127 loaded
bytes**, C-stack peak **10 → 6**, hardware peak **7 → 5**, with unchanged
RAM and zero page. A complete scan takes **13,145 instead of 129,734 cycles**
(−89.9%); the 256-ID shortcut takes **317 instead of 478**. The combined
background scene saves 101 loaded bytes and costs nine more cycles (+0.13%);
its earlier cycle reference is retained.
`test_tilemap_init.py` checks 69,120 calls on II+/IIe: all counts, an invalid
ID at every map position, the 64 following bytes excluded from validation,
all ID bytes and count boundaries, all map alignments, NULL combinations,
context/map guards and 1,024 stack placements. The fixture also passes on
the original C implementation.

The application restores all its old/new dirty regions before
drawing the affected layers, and keeps a separate history per page.
This optional backend is used with the masked blitter `hgr_ms_run` (explicit
internal contract in `hgr_internal.h`) to avoid the save-under pool.
The historical engine keeps its saved-background restoration.
The restorer keeps no redundant context-pointer copy or high count byte.
It adds the destination column to each row pointer once, then uses Y=0
for all eight scanline stores. Row low bytes plus valid columns cannot
cross a 256-byte boundary. These passes save **11 loaded bytes and 3 RAM
bytes**, with unchanged zero-page and stack requirements. A full-page
restore takes **271,192 instead of 278,943 cycles**; the game's scheduling
must still budget that work. An eight-tile region with two masked draws
costs **6,623 cycles**, down from 6,703 before these passes.
`test_tilemap.py` checks both pages, clipped/full regions, palette and memory
holes, the 256-count path and atomic rejection on 6502 and 65C02.
The `HGRC_TILEMAP_SRCS` family is extracted only when it is called.

The `HGRC_HEADERS` dependencies also include the `apple2c` headers,
included transitively by `hgr.h`, so that C consumers are recompiled when
the platform contract changes.

### Small drawing setup costs

Measured with cc65 2.18 `-Oirs` after table initialization, using emulator
checkpoints around a single call (including argument setup and checkpoint
return overhead):

| Call | Before | After | Linked fixture size reduction |
| --- | ---: | ---: | ---: |
| `dhgr_fill_bits(3,4,16,1,0)` | 1,680 cycles | 1,428 cycles (1,511 since the pair kernel) | 29 B |
| `dhgr_fill_bits(3,4,16,1,255)` | 1,684 cycles | 1,429 cycles (1,512 since the pair kernel) | 29 B |
| `hgr_blit7(14,10,2,3,bits,HGR_SET)` | 796 cycles | 787 cycles | 6 B |
| `hgr_cell(34,23,1)` | 936 cycles | 903 cycles | 15 B |

The span kernel of 2026-11-03 (pairs prepared once per call, above) costs
these 16-dot spans 83 more cycles of setup; wide fills and long spans gain
15–18 %, and a one-byte interior costs the same per line as before.
Monochrome fill sets its four identical pattern bytes directly. The byte
blit relies on the already-checked pixel coordinate to bound its column.
The cell kernel shifts in the accumulator and shares the high byte of
`x` and `x+5`, since `x` is a multiple of eight. `test_hgr.py` checks the
full 35×24 cell grid on both pages, invalid byte coordinates and screen holes;
`test_dhgr.py` and `test_dhgr_extended.py` cover the monochrome drawing paths.

Tile backgrounds accept the full byte range of map IDs (0..255). Pointer
lookup preserves the ninth bit of `2*id`, including pointers spanning a CPU
page; high IDs no longer alias IDs 0..127. The lookup uses existing `ptr1`
scratch and removes the per-piece patching of two pointer-table loads:
`dhgr_spr_cells.s` CODE shrinks from 395 to 388 bytes, with unchanged BSS
and no new zero-page allocation. `test_dhgr_spr.py` exercises a 256-entry
set with deliberately different shapes across the two halves.

### Cell background row setup

The first cell top is recovered from the division remainder instead of
repeatedly adding the cell height. Callback backgrounds skip tile-map
pointer setup and advancement altogether; tile-map advancement uses Y
rather than a stack save to preserve A. CODE is now 406 bytes (18 more
than the 388-byte full-ID version above), with unchanged BSS and ZP.

With `test_dhgr_spr.py --quick --cycles`, the base IIe/IIc fixture measured:

| Update | Before | After |
| --- | ---: | ---: |
| Full callback background, rows 8..183 | 2,188,186 | 2,137,067 |
| Drone over callback cells | 47,993 | 47,095 |
| Eight sprites over callback cells | 535,812 | 522,546 |
| Eight sprites moved | 491,543 | 479,605 |
| Full tile background | 1,616,850 | 1,614,324 |
| Drone over tiles | 31,345 | 31,386 |

These are whole-update cycles, including code-placement effects: the full
solid-background case changes from 975,240 to 976,825 despite not using
this module's background path. This is a speed/size tradeoff for callback
backgrounds, not a universal speedup. Tests also cover cell heights 5, 7,
13, 31, 191 and 255 with partial rows and late invalidation.

### Text pen advancement

Native text advances with increments; doubled text reuses the bit-wrap
carry when adding its column offset. This removes duplicated column
updates: `hgr_text8_asm.s` CODE is 141 B (was 157), and
`hgr_text16_asm.s` CODE is 318 B (was 331). No RAM/ZP is added.

A warmed cc65 `-Oirs` fixture rendering `"APPLE II"` at x=3 measured
9,363 → 9,249 cycles for native text and 20,341 → 20,419 for doubled
text. These whole-call results include linked-code placement effects;
this is not a universal speedup. `test_hgr.py` checks multi-character
advancement at all seven bit phases, both pages and the right edge;
`test_hgr_glyphs.py` checks all 96 glyphs at all phases on both pages.

Native x2 inflation reuses its five-byte caller frame and existing cc65
scratch. The 16-bit doubled stride replaces the consumed source-pointer
arguments. `test_hgr_x2_bytes.py` compares every byte/color pair and all
pointer alignments with a pixel oracle; `--reference` selects the C version.
`test_hgr_x2_entry.py` verifies every dimension pair, both full pointer domains,
the exact extent boundary, hostile scratch and 1,536 stack placements.

`hgr_blit_x2.s` validates the 64-byte source limit with a bounded product,
then reuses the original arguments for the byte blitter after inflation.
Its C reference remains available. `test_hgr_blit_x2_entry.py` checks all
size pairs, full x/source words, colors/modes and 2,048 stack placements,
including a backend that destroys every scratch register.
