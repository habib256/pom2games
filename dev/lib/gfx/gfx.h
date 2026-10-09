/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* gfx.h — shared 2D geometry, text cells and number formatting (cc65).
 * Derived from POM1 (GPL-3.0).
 * Algorithms call a backend selected at link time: gfx_plot, gfx_hline,
 * gfx_vline and the screen dimensions. The Apple II HGR backend lives in
 * gfx_backend_hgr.c; there is no per-pixel function-pointer dispatch.
 * x is unsigned, y is unsigned char. Drawing shares the backend's state and
 * scratch: not reentrant or callable from IRQ. Main RAM/ZP, D=0; see ../ABI.md.
 * Units are backend pixels. Rectangles/spans clip; diagonal lines reject
 * off-screen endpoints. Circles clip their plotted points.
 */
#ifndef GFX_H
#define GFX_H

/* ===========================================================================
 * Backend contract — each card supplies these (gfx_backend_<card>.c).
 * ===========================================================================
 * The shared algorithms below call ONLY these. Keep the set minimal so a new
 * card (a future framebuffer board) is a handful of one-line wrappers. */

/* Set one pixel (already clipped to the screen by the caller / by gfx_plot
 * itself — both existing backends bounds-check). x:0..width-1, y:0..191. */
void gfx_plot(unsigned x, unsigned char y);

/* Inclusive horizontal/vertical runs, dispatched to the selected backend's
 * byte/span primitives. gfx_line/gfx_rect use these for straight edges. */
void gfx_hline(unsigned x0, unsigned x1, unsigned char y);
void gfx_vline(unsigned x, unsigned char y0, unsigned char y1);

/* Filled rectangle through opposite corners, inclusive. HGR and DHGR
 * backends sort and clip both corners, including full-width rectangles. */
void gfx_filled_rect(unsigned x0, unsigned char y0,
                     unsigned x1, unsigned char y1);

/* Clear the current draw page. HGR: raw fill byte (0x00 black, 0x7F lit).
 * DHGR color: LORES color 0..15; DHGR mono: zero off, nonzero all bits on.
 * Pass zero to clear to black on every backend. */
void gfx_clear(unsigned char color);

/* Screen extent: HGR 280x192, DHGR color 140x192, DHGR mono 560x192.
 * Constants belong to the backend selected at link time. */
extern const unsigned      gfx_width;
extern const unsigned char gfx_height;

/* ===========================================================================
 * Shared geometry (gfx_line/rect/circle/ellipse.c) — shared by HGR/DHGR backends.
 * ===========================================================================
 * All endpoints inclusive. */

/* Bresenham line. Axes use clipped gfx_hline/gfx_vline spans. Diagonals reject
 * off-screen endpoints. Link exactly one implementation: gfx_line_hgr.c for
 * HGR (ASM kernel), gfx_line.c for generic/DHGR (C fallback through gfx_plot). */
void gfx_line(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1);

/* Rectangle OUTLINE through opposite corners (interior untouched). Up to four
 * spans via gfx_hline / gfx_vline, with no repeated corner pixels. A point or
 * flat rectangle uses one span. Clipping preserves the original edges. */
void gfx_rect(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1);

/* Midpoint circle OUTLINE, centre (xc, yc), radius r; 8-way symmetry, every
 * point clipped to [0,gfx_width) x [0,gfx_height) before plotting. Off-screen
 * unsigned centres are accepted; circles wholly outside draw nothing.
 * Each visible point is plotted once, including axes, diagonals and r=0. */
void gfx_circle(unsigned xc, unsigned char yc, unsigned char r);

/* Ellipse inscribed in the (x0,y0)-(x1,y1) bounding box, drawn as a 64-segment
 * polyline using successive points on the ellipse. An integer radius of zero
 * collapses to a line (or a point), staying inside the bounding box. X corners
 * accept the full 0..65535 range, in either order. Chord endpoints are clamped
 * to the screen; wholly off-screen boxes draw nothing. Scaled offsets round
 * toward zero on both host C and cc65. */
void gfx_ellipse(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1);

/* ===========================================================================
 * Shared integer -> ASCII (gfx_num_dec/hex.c) — STRING BUILDERS only.
 * ===========================================================================
 * These produce NUL-terminated strings without drawing. Render them through
 * the chosen native text API. gfx_utoa/gfx_itoa use portable C division;
 * hgr_putu_field retains an assembler conversion for frequently updated HUDs. */

/* Unsigned decimal, no leading zeros. `buf` must hold >= 6 bytes (65535 + NUL).
 * Returns the digit count written (excluding the NUL). */
unsigned char gfx_utoa(char *buf, unsigned value);
/* Optional 65C02 kernel (HGRC_65C02_NUM_SRCS): exactly five decimal digits.
 * Shared six-byte buffer, overwritten on the next call; not reentrant.
 * Bounded conversion preserves caller decimal/IRQ flags. */
const char *__fastcall__ gfx_u16_digits(unsigned value);

/* Signed decimal: leading '-' then magnitude. `buf` >= 7 bytes (-32768 + NUL). */
unsigned char gfx_itoa(char *buf, int value);

/* Unsigned hex, uppercase, no leading zeros (1..4 digits). `buf` >= 5 bytes. */
unsigned char gfx_hexstr(char *buf, unsigned value);

/* ===========================================================================
 * Positioned HGR text (gfx_text.c + gfx_text_backend_hgr.c).
 * ===========================================================================
 * One shared 8x8-cell cursor, white text, 35 columns x 24 rows. The supplied
 * cell backend is HGR-only, writes to the current HGR draw page and is in the
 * default archive. DHGR geometry backends do not implement these cell calls;
 * use dhgr_puts for DHGR text instead. For doubled/color HGR use hgr_puts_color.
 */
extern const unsigned char gfx_text_cols;
extern const unsigned char gfx_text_rows;

/* Backend cell primitives (gfx_text_backend_<card>.c). gfx_cell_glyph draws ONE
 * printable 8x8 glyph at cell (col,row) in the current text colour; the shared
 * layer guarantees col<gfx_text_cols, row<gfx_text_rows and ch>=0x20. */
void gfx_cell_glyph(char ch, unsigned char col, unsigned char row);

/* Reserved text color hook; the supplied HGR backend ignores the value.
 * Native 8x8 HGR text stays white. Use hgr_puts_color for doubled color text. */
#define GFX_TEXT_DEFAULT 0u
void gfx_cell_color(unsigned char color);

/* Move the text cursor to cell (col,row); clamped into the grid. */
void gfx_gotoxy(unsigned char col, unsigned char row);

/* Draw one character at the cursor and advance. '\n' = next row / column 0,
 * '\r' = column 0, other control chars (<0x20) are skipped. Advancing past the
 * right margin wraps to column 0 of the next row; on the last row it wraps
 * to column 0 of that same row, without scrolling. */
void gfx_putc(char ch);

/* Draw a NUL-terminated string from the cursor (gfx_putc per character). */
void gfx_text(const char *s);

/* Numbers AT THE CURSOR — build via gfx_utoa / gfx_itoa / gfx_hexstr then
 * gfx_text. Decimal has no leading zeros; hex is uppercase, no leading zeros. */
void gfx_putu(unsigned value);
void gfx_puti(int value);
void gfx_putx(unsigned value);

#endif /* GFX_H */
