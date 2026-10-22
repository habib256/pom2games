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
that rejects repeated writes, then compares 54 cc65 scenes against the expected
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
`gfx_filled_rect` handles the full width. The backend choice remains explicit
at link time.


The HGR archive selects `gfx_line_hgr.c`: diagonals use the 280-pixel
assembler kernel of `hgr_line`. The C fallback `gfx_line.c` remains intended
for the generic/DHGR backends. Both files define the same symbol:
pick one implementation at link time. No function pointer is added.
The two HGR APIs are compared on 464 lines; the fallback is tested in both
DHGR modes, on both pages and banks, rejected inputs included.
