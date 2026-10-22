# lib/hgr — HGR text, sprites and tables (asm)

*[← dev](../../README.md)*

Assembler modules for native Apple II HGR video, derived from
[POM1](https://github.com/habib256/pom1) (GPL v3): pages `$2000`/`$4000`,
standard line interleave and NTSC colours.
The video soft switches and initialisation are in
[`../apple2/hgr.asm`](../apple2/hgr.asm).

**Mandatory rule for interface text: only ×2 enlarged characters may be
coloured. All normal-size (×1) text, including digits,
commands and menu cursors, must stay white.** Switching from white to an
HGR colour masks part of the small glyph's strokes and reduces its legibility.
For `hgr_putc8` / `hgr_puts8`, use the white attributes
`ht_cm_ev = $7F`, `ht_cm_od = $7F`, `ht_cbit = $00`.
Keep a black margin around text placed on a coloured background to avoid
colour fringes at the edges. This rule concerns text; sprites,
walls, crates and other graphic elements keep their colours.

| File | Contents | Used by |
|---|---|---|
| `hgr_scanline.inc` | `hgr_lo` / `hgr_hi`: address of each line 0..191 | arkabreakout, chess, logo, maze3d, micro-sokoban, wilderness |
| `hgr_scanline_ram.asm` | the same tables in RAM (segment `HGR_SCANLINE_SEGMENT`), built by `hgr_scanline_init` (~50 B, startup code): 384 B less in the file | dirtbike |
| `hgr_plot_tables.inc` | `hgr_col` / `hgr_mask`: byte and bit of columns 0..255, or 0..279 with `HGR_FULL_WIDTH_TABLES=1`; `HGR_PLOT_TABLES_RAM=1` reserves them in BSS and assembles `hgr_plot_tables_init` (39 B) | logo (RAM) |
| `hgr_div7_ram.asm` | `hgr_div7` / `hgr_mod7` (x/7, x mod 7, x = 0..255) in BSS, built by `hgr_div7_init` (28 B): 512 B less in the file | arkabreakout |
| `hgr_clear.asm` | `clear_hgr`: clears `$2000-$3FFF` (`HGR_CLEAR_LOOP`, no ZP) | logo |
| `hgr_flip.asm` | `hgr_draw_hidden` / `hgr_show_draw` / `hgr_set_draw_page`: double buffering by rewriting `hgr_hi` in place (`hgr_scanline.inc` in a writable segment) | maze3d, micro-sokoban |
| `hgr_text8.asm` | `hgr_putc8` / `hgr_puts8`: byte-aligned 8x8 text, colours. `HGR_TEXT8_HGR_ORDER` (font in HGR order: no more `ht_rev` or `rev7_tab`, −256 B), `HGR_TEXT8_NO_PUTS` | arkabreakout, dirtbike, maze3d |
| `hgr_sprite16.asm` | `hgr_spr16_x1/_x2/_x4`: TMS 16x16 sprites converted at run time | legacy TMS path |
| `hgr_sprite_packed.asm` | `hgr_sprite_packed`: pre-packed HGR rows, vertical repeat and masked edge | maze3d |
| `hgr_sprite_color.inc` | colour attributes shared by both blitters | sprite engines |
| `hgr_plot.asm` | `hgr_plot16`: OR/XOR pixel with clipping, 16-bit X, optional palette | logo |
| `hgr_line16.asm` | `hgr_line16`: Bresenham with signed 16-bit X, historical LOGO raster | logo |
| `hgr_xor.asm` | native rectangles and pre-shifted XOR glyphs, double buffering by the caller | arkabreakout |
| `hgr_sprite_update.asm` | `ds_present` / `ds_hide`: byte-wise transparent sprite, background save and restore | logo |
| `hgr_line.asm` | `hgr_line8`: fast OR line, native X 0..255, Y 0..191; `HGR_LINE_DIV7`/`HGR_LINE_MOD7` (caller's tables) replace the division loop; follows `hgr_select_page` if `hgr_pages.inc` is included | maze3d, dirtbike |
| `hgr_pages.inc` / `hgr_pages.asm` | drawing page chosen by patching operands: `HGR_HI_SITE` before each read of `hgr_hi`, `hgr_select_page` (A = 0 / ≠ 0) rewrites them to `hgr_hi` or `hgr_hi2` (~8 cycles per site, nothing per access); `hgr_pages_init` builds `hgr_hi2`. `HGR_PAGES_ORA` variant (no `hgr_hi2`): `HGR_LDA_HI_X` reads page-less offsets then a patched `ORA #page` (+2 cycles per read, ~4 per site). A site acts like a label (ends `@` scope); `hgr_wireframe.asm` and `hgr_span.asm` mark their reads too | dirtbike, light3dball |
| `hgr_span.asm` | `hgr_hspan` / `hgr_vspan`: spans by columns and byte masks, full HGR width | maze3d, light3dball (via `hgr_wireframe.asm`) |
| `hgr_wireframe.asm` | X-clipped outlines, per-page history and fast black erasure of old strokes | light3dball |
| `hgr_clear_rows.asm` | clearing of visible lines, screen, HUD and 160-line viewport | maze3d |
| `rev7.inc` | `rev7_tab`: TMS → HGR bit order | hgr_text8, hgr_sprite16 |
| `sprites/chess_cc65_pieces.asm` | chess pieces from cc65-Chess (F. Gebhart, O. Schmidt) | chess |

The legacy TMS blitter `hgr_sprite16.asm` clips at line 192 and at
byte column 40. An off-screen vertical origin does not wrap to the top,
and sprites at the right edge preserve the off-display bytes.

`hgr_puts8` walks the string up to the NUL, even beyond 256 characters.
It preserves the source pointer and X; the cursor keeps advancing past the
bottom of the screen, without writing outside the framebuffer.

The Beautiful Boot font (8x8) no longer lives here: `.include "bbfont.inc"` from
[`../font`](../font/README.md), which trims the master table to the wanted
character range (`BBFONT_FIRST` / `BBFONT_LAST`).

See each file's header for the detailed API and the zero page it
reserves.

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).

## Primitives extracted from Maze3D

The new modules use `hgr_lo/hi` and follow the page selected by
`hgr_flip.asm`. Code and tables must reside in RAM: lines, vertical
spans and viewport clearing modify their own instructions. Calls
are not reentrant. Inputs are assumed valid; no implicit clipping
is added. The headers specify the bounds and the clobbered registers.

`hgr_line8` works in native HGR coordinates on the first 256 pixels.
TMS coordinate adaptation and margins stay in Maze3D; this kernel
does not replace the 280-pixel C API `hgr_line`. Spans cover all 40
columns. Visible clearing preserves the memory holes and the other page;
the 160-line variant also preserves the HUD.

The pre-packed blitter takes a byte column, a line, a pointer,
a width (1..10 bytes), a source line count, a vertical
repeat and the mask of the last byte. It overwrites the background in the rectangle,
black pixels included, and keeps the pixels beyond the final edge,
even if the source's padding bits are non-zero.
Game-specific sizes, palettes and placements stay with the caller.
`hgr_sprite_color.inc` only shares the attributes; it imposes neither
the legacy TMS blitter nor the `rev7_tab` table.

Each module allocates its own scratch by default. The aliases described in the
headers let a caller's scratch be reused without growing
its zero page. Include only the families needed, after the calls.
The matching packer is `dev/tools/assets/pack_hgr_sprites.py`.

Standalone check: `python3 dev/tests/test_hgr_native.py` from the
root (also in `make test-hgr`). It uses the default scratch
allocations, tests both pages and the right edge of the spans, and
checks an 8192-byte LZ4FH decompression. The Maze3D tests keep
coverage of the seven sizes, visibility and complete scenes.

The two assembler blitters can be included together, in any
order: their shared `sp_*` variables are reserved only once.
They share this scratch and the colour attributes, so their calls are
sequential. `hgr_putc8` text cuts partial glyphs at the bottom of the screen
and keeps an off-screen position when returning to the initial column.
The matching regressions are in `test_asm_boundaries.py`: the
sprite edges cover 256 combinations of pages, widths, parities,
palettes, colours, backgrounds and padding bits.

## Wireframe outlines

`hgr_wireframe.asm` draws white horizontal and vertical strokes, then
erases old strokes in black. It fills no rectangle. Horizontal
spans clear full bytes directly with an unrolled sequence of
stores; the endpoint masks preserve the neighbouring pixels.

Include `hgr_scanline.inc` and `hgr_plot_tables.inc`, then the module, in a
writable segment. It includes `hgr_span.asm` itself. Each call uses
the page designated by `hgr_lo/hi`, compatible with `hgr_flip.asm`.

| Entry | Parameters and effect |
|---|---|
| `hgr_wire_span` | `wf_x0/y0/x1/y1`: draw a stroke with no clipping and no history |
| `hgr_wire_line` | Draw a stroke limited to `wf_clip_left..wf_clip_right`, then advance `wf_history` by four bytes if it is visible |
| `hgr_wire_rect` | Submit the four sides of the rectangle to the same clipping and the same history |
| `hgr_wire_erase` | `wf_history` at the start of the old history, `wf_count` strokes: erase them, advance the pointer and reset the count to zero |
| `hgr_wire_clear_span` | Erase a single stroke, with no history |

Coordinates must be ordered and valid: X 0..255, Y 0..191;
only horizontal and vertical strokes are accepted. Clipping is
horizontal, with no extra edge at the visibility limit. A window
with left > right draws nothing. Degenerate rectangles are accepted,
possibly with several records of the same stroke.

The caller reserves four bytes per visible stroke, i.e. up to sixteen per
rectangle, and computes the stroke count as `(final_pointer-start)/4`.
The module does not check the buffer capacity. Keep a separate history
for each page: restore the sprites, erase the old history of the
drawing page, reset the pointer to the start, then draw the new
outlines. Projection, object ordering and updating the visibility
window stay with the caller.

The background is monochrome; full horizontal bytes reset the
colour phase bit. To repair fixed scenery crossed by an old stroke,
define `HGR_WIRE_AFTER_HLINE` and/or `HGR_WIRE_AFTER_VLINE` before the include.
These routines are called after erasure with the endpoints in
`wf_x0/y0/x1/y1` and must preserve `wf_history` and `wf_count`.
Light3dball uses these hooks to restore the fixed edges of the corridor.

The module reserves its own scratch by default; `wf_*` aliases can
replace it before the include. `WF_COL_TABLE` and `WF_MASK_TABLE` allow
other X tables to be reused. All calls clobber A/X/Y and the
scratch; the code is non-reentrant and does not wait for video sync.

`python3 dev/tests/test_hgr_wireframe.py` checks the module alone on both
pages, with its default scratch, histories crossing a page
boundary, edges, empty windows and degenerate rectangles. Every
framebuffer byte is compared with a reference after drawing and erasing.
This test is also part of `make test-hgr`.

## Native kernels used by LOGO

`hgr_plot16` accepts a 16-bit X (0..279 on screen) and an 8-bit Y.
Off-screen pixels are ignored before any table access. `hp_mode=0`
composes with OR; other values use XOR, without modifying bit 7.
OR mode also preserves that bit, unless `HP_COLOR_TABLE` is defined:
`hp_color` then indexes the palette table supplied by the caller.
The optional hook `HP_OR_PLOT`, called with A = composed byte and Y = memory
column, may adjust A before the write; it must preserve Y and the
`hp_*` scratch. LOGO uses it to draw strokes under the visible sprite.

`hgr_line16` takes `h16_x0/y0` and `h16_x1/y1`. X is signed 16-bit,
Y unsigned 8-bit, with `|dx| <= 511`. The raster keeps LOGO's historical
tie-breaking: X step if `2*err >= -dy`, Y step if `2*err < dx`.
The endpoints and the scratch are modified. `HGR_LINE16_PLOT` lets the
plotter be replaced; the `hp_*` and `h16_*` aliases reuse existing
scratch. Include the tables with `HGR_FULL_WIDTH_TABLES=1` for these kernels.

The `hgr_sprite_update.asm` compositor handles one transparent sprite, on the
page designated by `hgr_lo/hi`. After `ds_init`, supply `ds_col/y/w/h`:
byte column 0..39, line 0..191, width 1..6, height 1..32, rectangle
entirely on screen. `ds_data` points to rows of **six bytes**,
with bit 7 always clear. `ds_color=0` keeps the background palette;
`ds_color=1` applies `ds_palette` (0 or 128) to the bytes that have foreground.
Composition uses OR, not XOR: a lit background does not punch holes in the sprite.

`ds_present` keeps two 192-byte background buffers. It makes a lit
byte of the new image visible before removing the old pixels,
composes the overlap directly, then restores the background left behind. An
identical rectangle uses a specialised loop. `ds_hide` restores the
background; after an external clear, call `ds_init` to invalidate the
save. The engine reserves eight ZP bytes; it is non-reentrant and
clobbers A/X/Y. The active mask must remain available between presentations.
External writes under the sprite must update the saved background,
or hide the sprite before those writes and then present it again.

This path avoids the phase in which the sprite was entirely erased. It works
on a single page, without VBL sync: tearing during the scan
remains possible. LOGO thus keeps its interpreter on HGR page 2 and its
80-column console, on II+ as on IIe.

`test_hgr_logo.py` compares lines and pixels against a reference, with the
default scratch and the LOGO adapter. `test_hgr_sprite_update.py` checks
coloured backgrounds, overlap, transitions without an empty frame,
erasure, HGR holes and the other page. These tests are part of
`make test-hgr`; `make -C logo test` also checks the real commands.

## Cursorless native glyphs

`hgr_glyph8.asm` is the kernel used by CHESS, LOGO and MICRO-SOKOBAN.
It reads eight rows at `hg_src` (ZP pointer, bit 0 on the left) and uses
`hgr_lo/hi` for the target page. Its entry points move no cursor; only those referenced before
the include are assembled (`.ifref`), together with their loops and masks:

| Entry | Coordinates | Write |
|---|---|---|
| `hgr_glyph8_store` | `hg_col`: byte 0..39; `hg_y`: line | One raw byte per row, palette included |
| `hgr_glyph8_or` | `hg_x`: 16-bit pixel 0..279; `hg_y`: line | Adds only the lit pixels |
| `hgr_glyph8_cell` | same coordinates | Replaces an eight-pixel cell, clears its palette, keeps neighbouring pixels |

All eight source bits are honoured, including the eighth pixel
in the next byte. Entry points reject off-screen coordinates and
truncate at the right/bottom without wrapping to the start of the line. Source and coordinates
are preserved; A/X/Y and the scratch are clobbered. The module is non-reentrant,
requires D=0 and touches no video soft switch. The `hg_*` aliases allow
the program's scratch to be reused.

`HG_COLOR_TABLE[hg_color]` replaces the palette of OR-lit bytes only.
`HG_OR_HOOK` receives and returns A=screen byte, Y=byte column; it preserves
Y and `hg_*`. `HG_HOOK_Y` and `HG_HOOK_MASK` receive the line and the lit
mask. LOGO uses this hook to keep text drawn under an emote.
Without a colour table, OR preserves the existing palette.

`HG_STORE_ONLY` omits the unaligned entry points. `HG_STORE_UNCLIPPED` removes
the STORE checks: the caller then guarantees `hg_col<40`, `hg_y<=184`.
CHESS and the MICRO-SOKOBAN titles use this contract for their fixed UI.
CELL and OR are always truncated.

`test_hgr_glyph8.py` covers both pages, the seven alignments, palettes,
empty cells and edges. `test_logo_glyphs.py` checks the real adapter
and its characters; the LOGO tests also check text under a sprite.

## Native XOR rectangles and glyphs

`hgr_xor.asm` works on the page 1 line tables and takes
`hx_page = 0` for `$2000`, or `$60` for `$4000`. Define
`HGR_XOR_DIV7` and `HGR_XOR_MOD7` as aliases of the 256-byte X tables.

- `hgr_xor_rect`: `hx_x/y/w/h` in pixels, non-zero width and height,
  `x+w <= 256`, `y+h <= 192`.
- `hgr_xor_sprite`: `hx_x/y` and `hx_data`, eight rows of two bytes with
  bit 7 clear. The pointer targets the variant already pre-shifted for `x % 7`.
  Both destination bytes must stay within the 40 visible columns.

The kernels preserve the background's colour phase bit. Drawing the same
object twice restores the original bytes exactly. They clobber A/X/Y and
their scratch, and do neither clipping nor video sync. For a game,
keep each page's history, erase all objects before
changing the scenery, then draw the new scene on the hidden page.
`dev/tests/test_hgr_xor.py` checks the raster, the seven alignments, both
pages, the extremities and full restoration, memory holes included.

For an incremental HUD with `hgr_text8.asm`, define `HGR_TEXT8_FILTER` as
the address of a callback. It reads `ht_a/ht_col/ht_sl/ht_page` before drawing:
C=1 skips the glyph but advances the cursor; C=0 draws normally. A/X/Y
are free; `ht_a`, the cursor, the font and the attributes must be
preserved. Arkabreakout's callback compares the characters with an
independent cache for each page, invalidated on every screen clear.
