# lib/gfx — shared geometry (cc65)

*[← dev](../../README.md)*

The vector layer from [POM1](https://github.com/habib256/pom1)
(`dev/lib/gfx`, GPL-3.0): lines, rectangles, circles, ellipses and numbers, on
an HGR or DHGR backend. The HGR backend (`gfx_backend_hgr*.c`) calls
[`../hgrc`](../hgrc/). Dimensions and colours depend on the chosen backend.

Compile with `-I dev/lib/hgrc -I dev/lib/apple2c -I dev/lib/gfx`, preferably
into an `ar65` archive so that only the functions actually called get linked
(see [`../hgrc/hgrc_build.mk`](../hgrc/hgrc_build.mk)).

## Apple II DHGR

Two explicit backends: `gfx_backend_dhgr_color.c` (140×192, LORES colour
0..15) or `gfx_backend_dhgr_mono.c` (560×192, bit 0/1). Link exactly one
backend with `HGRC_GENERIC_VECTOR_SRCS` and the DHGR library. The current
colour is set with `dhgr_set_color`. Coordinates are those of the chosen
backend; native blocks and sprites keep their own API in `dhgr.h`.
Rectangles are inclusive, sorted and clipped before their dimensions are computed.

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).

## Archive and text

`HGRC_ALL_SRCS` includes the decimal and hexadecimal conversions, `gfx_text.c`
and the HGR text backend: `gfx_utoa`, `gfx_itoa`, `gfx_hexstr`, `gfx_gotoxy`,
`gfx_text`, `gfx_putu`, `gfx_puti` and `gfx_putx` link without any manual addition.
Text uses a 35×24 HGR grid of white 8×8 glyphs on the current drawing
page. Calls wrap at the right edge; the last line does not scroll.
`gfx_cell_color` has no effect with this backend.
There is no cell-based DHGR text backend; use `dhgr_puts`.

The three numeric text entries live in separate archive members (`gfx_putu.c`,
`gfx_puti.c`, `gfx_putx.c`). Plain strings no longer pull in the numeric
formatters; unsigned and hexadecimal text pull in only their own conversion.
With cc65 2.18 `-Oirs`, the minimal archive fixtures in `test_hgr.py` shrink
from 3,051 to 2,689 bytes for plain text, 3,040 to 2,801 for hexadecimal,
and 3,058 to 2,841 for plain text plus an unsigned integer. The test also
checks the excluded archive members and renders all three numeric formats.

The cc65 hexadecimal converter uses `gfx_num_hex.s`; `gfx_num_hex.c` is the
host reference. Both produce uppercase text without leading zeroes and return
the digit count. `test_gfx_hex.py` checks every 16-bit input, the terminating
NUL, return length and buffer guards, including page-crossing buffers.
The assembly member now occupies **68 bytes** (71 before this nibble pass,
168 for the original C code and constant data). A four-digit counter selects
the upper/lower nibble of each byte directly, switching bytes once instead
of shifting the full 16-bit value between digits. The ASCII adjustment has
C=0 on both paths, so no extra CLC is needed. No lookup table, extra scratch,
RAM, zero page or stack is introduced.
With cc65 2.18 `-Oirs`, the exhaustive fixture takes **131,796,307 cycles**
instead of 138,079,027 before this pass (238,118,920 for the original C),
including the unchanged C loop and buffer initialization. Its linked binary
shrinks 705 → **702 bytes**. The full sweep has identical cycle counts on
NMOS 6502 and 65C02 (`--iie`); every value, NUL, return length and buffer
guard is checked on both.

`gfx_u16_digits` returns five ASCII digits, with leading zeros, for an
unsigned value from 0 to 65535. Its static buffer is reused on the next
call. The assembler kernel `gfx_u16_digits.s` is **65C02-only**; the
optional family `HGRC_65C02_NUM_SRCS` selects it without changing the
6502 conversions used on the Apple II+. It preserves the flags, including
the interrupt and decimal-mode states.

Diagonal segments reject off-screen endpoints; they do not perform full
line clipping. Axis-aligned lines go through the clipped spans. Filled rectangles sort and clip
their corners; circles clip the plotted points. An off-screen centre
is still accepted: arcs near the edge are visible, and circles entirely
to the right of or below the screen are discarded before the drawing loop. X
coordinates are checked before their signed 16-bit conversion.
Circles do not redraw the points shared by the symmetries on the axes and
diagonals; radius zero draws a single point. Rectangles do not redraw
their corners: a point, a horizontal line or a vertical line
uses a single span. Each outline pixel is therefore written exactly once.
Clipping keeps the original edges: a rectangle that overflows does not create
a new edge at the screen border.
`test_gfx_outlines.py` checks 1,792 circles and 625 rectangles with a backend
that rejects repeated writes, then compares 158 cc65 scenes against the expected
pixels on both HGR pages, memory holes included. It is part
of `make test-hgr`.

Measurements from 9 October 2026, cc65 `-Oirs`, HGR on a2run NMOS 6502, warm
tables, arguments and calls included, markers excluded as in `dev/bench`:

| Call | Before (cycles) | After (cycles) |
|---|---:|---:|
| `gfx_circle(140,96,0)` | 8 159 | 1 043 |
| `gfx_circle(140,96,16)` | 89 287 | 86 439 |
| `gfx_circle(140,96,64)` | 340 085 | 339 096 |
| `gfx_circle(5,255,63)` (invisible) | 131 648 | 685 |
| `gfx_rect(10,20,10,20)` | 5 897 | 1 508 |
| `gfx_rect(10,20,50,20)` | 6 097 | 2 018 |

Ellipses with an integer radius of zero reduce to a segment or
a point within their box, without spilling around very narrow shapes.
Boxes entirely to the right of or below the screen are discarded before
the points are computed, without drawing a stray line on the edge.
X corners accept the full 0..65535 range, even for a partially
visible box, without overflowing the centre or the products on cc65.
Offsets are rounded towards zero, including when negative:
the cc65 output matches the host C output. Segment endpoints are clamped
to the screen limits; this behaviour is not full geometric
clipping. Each vertex is computed once and then shared
between its two neighbouring segments.
Low-level HGR primitives may have 8-bit widths;
`gfx_filled_rect` and the HGR spans send inclusive endpoints to the shared
kernel, handling the full width in one pass. The backend choice remains explicit
at link time.

The shared span setup removes the former 255-pixel subdivision and its repeated
clipping/table preparation. Measurements with cc65 2.18 `-Oirs`, a2run NMOS
6502, warm tables, arguments and calls included, markers excluded:

| Call | Before (cycles) | After (cycles) | Linked file reduction |
|---|---:|---:|---:|
| `hgr_hline(7,20,10)` | 1,458 | 568 | 451 B |
| `hgr_hline(0,279,10)` | 3,101 | 1,096 | 451 B |
| `hgr_vline(10,0,191)` | 12,333 | 11,343 | 451 B |
| `gfx_filled_rect(7,10,20,13)` | 1,729 | 865 | 432 B |
| `gfx_filled_rect(0,0,279,191)` | 133,192 | 118,252 | 432 B |

These isolated-client file reductions include compiler helpers no longer
linked; savings in a larger program depend on its other calls. The low-level
`hgr_fill_pixrect(7,10,14,4)` remains at 1,092 cycles and 2,063 loaded bytes.

Since the pair kernel of 2026-11-03 (`hgr_pixrect_asm.s` stores the full
bytes of a line two at a time, counted once per call; see the HGR C
runtime's README), the same calls measure 596, 992, 11,394, 913 and 93,920
cycles, and `hgr_fill_pixrect(7,10,14,4)` 1,141 cycles for 2,091 loaded
bytes: a call with at most one full byte a line pays 30 to 50 cycles of
setup, a wide fill gains 10 to 21 %.


The HGR archive selects `gfx_line_hgr.c`: diagonals use the 280-pixel
assembler kernel of `hgr_line`. The C fallback `gfx_line.c` remains intended
for the generic/DHGR backends. Both files define the same symbol:
pick one implementation at link time. No function pointer is added.
The two HGR APIs are compared on 464 lines; the fallback is tested in both
DHGR modes, on both pages and banks, rejected inputs included.

Decimal conversion shares the `hgr_utoa` kernel. The signed wrapper lives in
`gfx_num_signed.s`, so unsigned-only clients omit it. With cc65 2.18 `-Oirs`,
the isolated `gfx_utoa(65535)` fixture shrinks by 42 bytes with unchanged
cycles; the signed fixture grows by 3 bytes for the cross-object jump.
`hgr_putu_field(10,20,123,5)` reuses the returned digit count: 44 fewer linked
bytes and 135 fewer cycles (14,835 to 14,700). `test_gfx_decimal.py` checks
all 131,072 signed/unsigned inputs, lengths, NULs and buffer guards.

The ellipse sine and cosine samples share an 80-byte table (one period plus
one quarter), saving 48 bytes over two separate 64-byte tables. With cc65
2.18 `-Oirs`, CODE stays at 911 bytes and the generated instructions are
unchanged apart from table addresses. `test_gfx_boundaries.py` verifies all
64 chord endpoints for ordinary, reversed, degenerate and large boxes at
140-, 280- and 560-pixel screen widths.
