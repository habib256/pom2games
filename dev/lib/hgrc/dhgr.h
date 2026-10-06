/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Native DHGR, IIe revision B + extended 80-column card / IIc.
 * Both pages ($2000-$5FFF main+aux). Code, stack, source and destination
 * buffers must be outside these windows. Main RAM/zero page on entry.
 * Drawing preserves IRQ state, returns RAMRD/RAMWRT main, 80STORE off,
 * and never changes the displayed page. Non-reentrant; initialize first.
 */
#ifndef DHGR_H
#define DHGR_H

#define DHGR_WIDTH 560u
#define DHGR_COLOR_WIDTH 140u
#define DHGR_HEIGHT 192u

/* Same color numbers as Apple II LORES, converted to DHGR bit patterns. */
#define DHGR_BLACK       0u
#define DHGR_MAGENTA     1u
#define DHGR_DARKBLUE    2u
#define DHGR_VIOLET      3u
#define DHGR_DARKGREEN   4u
#define DHGR_GRAY1       5u
#define DHGR_BLUE        6u
#define DHGR_LIGHTBLUE   7u
#define DHGR_BROWN       8u
#define DHGR_ORANGE      9u
#define DHGR_GRAY2      10u
#define DHGR_PINK       11u
#define DHGR_GREEN      12u
#define DHGR_YELLOW     13u
#define DHGR_AQUA       14u
#define DHGR_WHITE      15u

/* Full screen; successful init selects draw/display page 1 without clearing. */
#define DHGR_CAP_EXTENDED 1u
#define DHGR_CAP_AUX_VIDEO 2u
/* Probe preserves video state and scratch RAM. Revision/jumper cannot be
 * detected in software. Init returns 0 on unsupported RAM/model, 1 on success. */
unsigned char dhgr_capabilities(void);
unsigned char dhgr_init(void);
void __fastcall__ dhgr_draw_page(unsigned char page);
void __fastcall__ dhgr_show_page(unsigned char page);
unsigned char dhgr_get_draw_page(void);
unsigned char dhgr_get_display_page(void);
/* Show the draw page, then draw into the previously displayed page.
 * Caller controls VBL timing; this function does not wait for synchronization. */
void dhgr_flip(void);
/* Defined by the selected gfx DHGR backend: 0..15 color, 0/1 mono. */
void dhgr_set_color(unsigned char color);
void dhgr_fill_bits(unsigned x, unsigned char y, unsigned width,
                    unsigned char height, unsigned char set);
void dhgr_hline(unsigned x0, unsigned x1, unsigned char y, unsigned char set);
void dhgr_vline(unsigned x, unsigned char y0, unsigned char y1, unsigned char set);
/* Interleaved 7-bit bytes, aux/main/aux/main; byte coordinates 0..79.
 * Packed rows with stride bytes; caller provides stride*height bytes.
 * Clipped transfers leave off-screen buffer bytes unchanged. */
void dhgr_read_block(unsigned char bx, unsigned char y, unsigned char width,
                     unsigned char height, unsigned char *data, unsigned char stride);
void dhgr_write_block(unsigned char bx, unsigned char y, unsigned char width,
                      unsigned char height, const unsigned char *data, unsigned char stride);
/* Mask bit 1 preserves background. Data/mask contain seven pre-shift banks,
 * each stride*height bytes. x is a 140-column COLOR coordinate. */
void dhgr_sprite(unsigned char x, unsigned char y, unsigned char width,
                 unsigned char height, unsigned char stride,
                 const unsigned char *data, const unsigned char *mask);
/* White/black opaque text: color cells, 8x8 glyphs, width 8 color pixels.
 * Each glyph bit is expanded to four DHGR bits to avoid artifact tint. */
void dhgr_puts(const char *s, unsigned char x, unsigned char y);
/* Compact opaque white text: 4x5 glyphs; five color pixels per character, five rows tall.
 * ASCII space..underscore, lowercase folds to uppercase. Arbitrary x alignment;
 * surrounding pixels and interrupt state are preserved; clips at right/bottom. */
#define DHGR_SMALL_ADVANCE 5u
#define DHGR_SMALL_HEIGHT 5u
#define DHGR_SMALL_FONT_STRIDE 6u
void dhgr_puts_small(const char *s, unsigned char x, unsigned char y);
/* String in A/X, starting at dhgr_small_x/y, advancing the shared cursor. */
void __fastcall__ dhgr_small_string(const char *s);
extern const unsigned char dhgr_small_font[64u*DHGR_SMALL_FONT_STRIDE];
/* Fast one-cell entry for incremental HUDs. Coordinates use the draw page. */
extern unsigned char dhgr_small_x, dhgr_small_y;
void __fastcall__ dhgr_small_char(unsigned char ch);
void dhgr_text_restore(void);
void dhgr_clear(unsigned char color);

/* Raw 560x192 bits, displayed monochrome on a monochrome monitor.
 * On a color monitor, adjacent bits produce NTSC artifact colors.
 * Out-of-range writes are ignored; out-of-range reads return zero. */
void dhgr_plot(unsigned x, unsigned char y, unsigned char set);
unsigned char dhgr_getpixel(unsigned x, unsigned char y);

/* A color pixel occupies four consecutive bits. Colors are masked to 0..15.
 * Coordinates are 140x192. Rectangles clip to the screen. */
void dhgr_plot_color(unsigned char x, unsigned char y, unsigned char color);
void dhgr_fill_rect(unsigned char x, unsigned char y,
                    unsigned char width, unsigned char height,
                    unsigned char color);
#endif
