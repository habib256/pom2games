/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Native DHGR, IIe revision B + extended 80-column card / IIc.
 * Both pages ($2000-$5FFF main+aux). Code, stack, source and destination
 * buffers must be outside these windows, with valid non-null pointers and
 * the declared capacities. Main RAM/zero page, ROM visible and D=0 on entry.
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
/* Raw full 8K in each bank, including holes; IRQs masked for ~189000 cycles.
 * Prefer clear_rows for interrupt service and visible rows only. */
void dhgr_clear(unsigned char color);
/* Clear only visible rows, clipped to 192. Each row restores main RAMWRT
 * and the caller's IRQ mask (<1300 masked cycles); IRQs can run between rows.
 * Preserves holes and the display page. Main RAM/ZP; not callable from IRQ. */
void dhgr_clear_rows(unsigned char y, unsigned char rows, unsigned char color);

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
/* Flicker-free sprite compositor (optional family HGRC_DHGR_SPR_SRCS, see
 * README "Flicker-free sprites"). A colour group is 7 colour pixels = 4
 * interleaved bytes (aux, main, aux, main) at x/7: the compositor owns whole
 * groups. Each update rebuilds the dirty groups in a chunky canvas (one byte
 * per colour pixel): background, then the sprites back to front (slot 0
 * first), then writes every dirty screen byte once with its final value.
 * Fastcall, non-reentrant, never from an IRQ; draws on the draw page, main
 * RAM/ZP on entry and exit, displayed page unchanged, IRQs masked only around
 * each group's two auxiliary stores. Canvas and shapes outside $2000-$5FFF. */
#ifndef DHGR_SPR_MAX
#define DHGR_SPR_MAX 8u                 /* 1..8: compile the library alike */
#endif
#define DHGR_SHAPE_RECTS 0u             /* n x {x, y, w, h, colour} inside w x h */
#define DHGR_SHAPE_CHUNKY 1u            /* w*h colours, row by row */
#define DHGR_SHAPE_TILE 2u              /* w*h DHGR_NIB nibbles: opaque, unmirrored */
/* (CHUNKY and TILE need the library built without DHGR_SPR_RECTS_ONLY.) */
#define DHGR_NIB(c) ((((c) >> 1) | ((c) << 3)) & 15u)
#define DHGR_CLEAR 0x80u                /* transparent chunky pixel */
#define DHGR_SPR_PAL 16u                /* colours 16..19: the slot's palette */
#define DHGR_SPR_MIRROR 1u              /* drawn mirrored left-right */
#define DHGR_SPR_HIDDEN 2u
typedef struct {
    unsigned char kind, w, h, n;        /* n: rectangles (RECTS) */
    const unsigned char *data;
} dhgr_shape_t;
/* canvas: bytes of borrowed RAM (e.g. an idle ProDOS buffer) used only
 * inside dhgr_spr_update, at most 255 of them; groups: widest piece, 1..20
 * (a piece of n groups has min(bytes, 255) / (7*n) rows). 0 unless
 * min(bytes, 255) >= 7*groups. Forgets every slot, the damage and the
 * overlay (hide it first); area = full screen; background = black. Opt-in family
 * HGRC_DHGR_SPR_SRCS; options DHGR_SPR_MAX,
 * DHGR_SPR_CODE_SEGMENT, DHGR_SPR_RECTS_ONLY (README). */
unsigned char dhgr_spr_init(unsigned char *canvas, unsigned bytes, unsigned char groups);
/* Inclusive colour-pixel box the compositor owns, widened to whole groups;
 * nothing is drawn outside it. */
void dhgr_spr_area(unsigned char x0, unsigned char y0, unsigned char x1, unsigned char y1);
/* Background = one colour (default black). */
void __fastcall__ dhgr_spr_solid(unsigned char colour);
/* Background = 7 x cell_h cells from colour pixel ox (a multiple of 7), row
 * oy: paint(col, row) must cover its whole cell with dhgr_cv_rect (screen
 * coordinates; clipped to the piece). The cells must cover the area. */
void dhgr_spr_cells(unsigned char ox, unsigned char oy, unsigned char cell_h,
                    void (*paint)(unsigned char col, unsigned char row));
/* Background = a tile map: cell (col, row) at x = ox + 7 * col, y = oy +
 * cell_h * row shows *set[map[row * map_w + col]] (any shape kind; a NULL
 * entry draws nothing). The tiles must cover the area. Map and set are
 * borrowed; after changing them, invalidate the cells. */
void dhgr_spr_tiles(unsigned char ox, unsigned char oy, unsigned char cell_h,
                    const unsigned char *map, unsigned char map_w,
                    const dhgr_shape_t *const *set);
/* Slot id < DHGR_SPR_MAX: shape (NULL hides), top-left x, y in colour
 * pixels, flags. The shape and its data stay immutable while in a slot.
 * Returns 0 for a bad id. Nothing is drawn before dhgr_spr_update. */
unsigned char dhgr_spr_set(unsigned char id, const dhgr_shape_t *s,
                           unsigned char x, unsigned char y, unsigned char flags);
/* Colours 16..19 of slot id (copied); redraws it if they changed. */
void dhgr_spr_palette(unsigned char id, const unsigned char *four);
/* Redraw a colour-pixel box (background changed under it). */
void dhgr_spr_invalidate(unsigned char x, unsigned char y, unsigned char w, unsigned char h);
/* A byte-domain OR layer above everything (a pointer): bytes bx.. (0..79,
 * aux first) of rows y.., w*h <= 127 bit bytes (borrowed). In the area it
 * is recomposed with the sprites; outside, dhgr_cursor saves what it covers
 * in under (2 x the largest w*h used, the library's until hidden). w = 0
 * hides it. The screen outside the area may change only while it is
 * hidden. Applied by dhgr_spr_update. Built with DHGR_SPR_OVERLAY_INSIDE=1
 * only its part inside the area is drawn (under unused, no save-under code
 * linked). dhgr_spr_init forgets the cursor on screen (clear it first). */
void dhgr_spr_overlay(unsigned char bx, unsigned char y, unsigned char w, unsigned char h,
                      const unsigned char *bits, unsigned char *under);
/* The same cursor without the compositor, drawn at once in one pass over
 * old U new (each byte read once, written once): restore, save, OR. One
 * cursor at a time, shared with dhgr_spr_overlay: switch while hidden.
 * under: 2 x the largest w*h used. */
void dhgr_cursor(unsigned char bx, unsigned char y, unsigned char w, unsigned char h,
                 const unsigned char *bits, unsigned char *under);
/* Composite: each dirty screen byte written once with its final value. */
void dhgr_spr_update(void);
/* For paint callbacks (and chunky painters): fill a colour-pixel rectangle
 * of the current piece's canvas, clipped to it. */
void dhgr_cv_rect(unsigned char x, unsigned char y, unsigned char w, unsigned char h,
                  unsigned char colour);
#endif
