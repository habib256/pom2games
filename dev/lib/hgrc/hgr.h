/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr.h — Apple II HGR/LORES runtime for cc65.
 * Derived from POM1 (Arnaud Verhille, GPL-3.0).
 * Uses the built-in video soft switches at $C050-$C057 and the standard
 * interleaved pages at $2000/$4000. Text and keyboard: ../apple2c.
 * Main code/stack/ZP, ROM visible, D=0. Init video before drawing.
 * Shared tables, parameters and cc65 scratch: non-reentrant, no IRQ calls.
 * Source/save-under buffers must stay outside the active video pages and
 * remain valid through deferred sprite restores. See ../ABI.md.
 */
#ifndef HGR_H
#define HGR_H

#ifdef __CC65__
#define HGR_FASTCALL __fastcall__
#else
#define HGR_FASTCALL
#endif

/* Optional 40x24 background of 7x8 tiles, one byte per tile ID. Tiles keep
 * all eight HGR bits, including palette phase. count is 1..256. Sources must
 * remain valid and outside both video pages. No pool or page state changes.
 * Restore uses tile coordinates, clips right/bottom, returns 1 on success.
 * Invalid context/ID/geometry returns 0 without touching the framebuffer. */
typedef struct {
    const unsigned char *map, *tiles;
    unsigned count;
} hgr_tilemap_t;
unsigned char hgr_tilemap_init(hgr_tilemap_t *ctx, const unsigned char *map,
                              const unsigned char *tiles, unsigned count);
unsigned char HGR_FASTCALL hgr_tile_restore(const hgr_tilemap_t *ctx,
    unsigned char page, unsigned char col, unsigned char row,
    unsigned char width, unsigned char height);

/* Pull in the Apple II text/keyboard base by default (a2_puts / apple2_getkey).
 * #define HGR_NO_APPLE2 before including hgr.h to skip. Zero bytes added. */
#ifndef HGR_NO_APPLE2
#include "apple2c.h"
#endif

/* ===========================================================================
 * Function chooser — pick the right helper for the job (no extra cost: the
 * decision is yours, the code that ships is just the one you call).
 * ---------------------------------------------------------------------------
 * Text:
 *   hgr_puts       — 16x16 doubled glyphs, OR-drawn (overdraws background)
 *   hgr_puts_color — same, in one of VIOLET/GREEN/ORANGE/BLUE
 *   hgr_puts8      — native 8x8, 3-4x denser, no doubling
 *   hgr_putu       — unsigned decimal, OR-drawn, variable width
 *   hgr_putu_field — unsigned decimal, FIXED-width HUD (erases its box)
 *   hgr_puti       — signed decimal (-32768..32767)
 *   hgr_putx       — hex (uppercase, no leading zeros)
 *   hgr_putu8      — small-font decimal twin of putu
 *
 * Rectangle fill / clear (HIRES):
 *   hgr_fill_pixrect    — fill pixels (x, y, w, h)         <- pick this
 *   hgr_clear_pixrect   — erase pixels (x, y, w, h)        <- pick this
 *   hgr_fill_rect       — byte-column fill (col0, ncols)   <- only if you
 *                              already think in 7-px columns
 *
 * Sprite blit (HIRES):
 *   hgr_blit            — pixel-precise position, ANY width  <- pick this
 *   hgr_blit7           — 7-px column snap, BYTE-aligned src <- only when
 *                              you control the sprite layout and want max speed
 *
 * Vector primitives: hgr_line uses a 280-pixel ASM kernel; rect/circle/ellipse
 * use dev/lib/gfx. The default HGR gfx_line selects the same ASM kernel.
 *
 * Double buffering:
 *   hgr_set_draw_page(p)    — pick where the next draws WRITE (1 or 2)
 *   hgr_show_page()         — flip the display to DISPLAY the current draw page
 *   HGR_FLIP_PAGE(p)        — macro: p = (p == 1) ? 2 : 1
 * =========================================================================== */

/* Zero-cost macro helpers (pure preprocessor, expand to nothing if unused). */
#define HGR_FLIP_PAGE(p)     ((p) = ((p) == 1u ? 2u : 1u))
#define HGR_PIX_TO_COL(x)    ((unsigned char)((x) / 7u))
#define HGR_PIX_TO_BIT(x)    ((unsigned char)((x) % 7u))
/* (x, y, w, h, val) wrapper around hgr_fill_rect — restores the
 * standard (x, y, w, h) argument order for byte-aligned fills. Still
 * byte-granular: pixel x is rounded down to its byte column, pixel w is
 * rounded UP to whole byte columns. Use hgr_fill_pixrect for pixel-
 * precise white blocks. Zero cost (macro). */
#define HGR_FILL_RECT_XY(x, y, w, h, val) \
    hgr_fill_rect((y), (h), HGR_PIX_TO_COL(x), \
                       (unsigned char)(((w) + 6u) / 7u), (val))

/* "Init forgotten" trap (read once, save your day): drawing functions
 * lazily build only the tables they need so the column / bit / row tables come
 * up on first use — but NONE of them set the display mode. If you call
 * hgr_clear() / hgr_plot() / etc. BEFORE hgr_init() (or
 * hgr_lores_init()), they happily write to the framebuffer, but the display
 * is still in TEXT mode (or whatever state the latch held at startup) —
 * and you see a blank screen. Same trap with hgr_set_draw_page(2):
 * primitives now write to page 2, but the display is still page 1 (no flip
 * until hgr_show_page()), and worse, the display mode hasn't moved. Pattern:
 * **always** call hgr_init() (or hgr_lores_init()) once before any
 * draw, even when you only mean to flip pages. */

/* Soft switches — each macro is a READ that selects that state (the read IS the
 * toggle; the value read is meaningless). The result is stored into hgr_ss_sink
 * rather than cast to void: cc65 -Oirs ELIDES a volatile read whose value is
 * discarded by (void), which silently turned these into no-ops. A store to a
 * global it cannot prove dead forces the load. (The full-mode initialisers
 * hgr_init / hgr_lores_init are in asm for the same reason.) */
extern volatile unsigned char hgr_ss_sink;
#define HGR_SS         ((volatile unsigned char*)0xC050)
#define hgr_graphics() (hgr_ss_sink = HGR_SS[0])  /* $C050 TEXT off->graphics */
#define hgr_text()     (hgr_ss_sink = HGR_SS[1])  /* $C051 TEXT on            */
#define hgr_full()     (hgr_ss_sink = HGR_SS[2])  /* $C052 MIXED off (full)   */
#define hgr_mixed()    (hgr_ss_sink = HGR_SS[3])  /* $C053 MIXED on (4 rows)  */
#define hgr_page1()    (hgr_ss_sink = HGR_SS[4])  /* $C054 page 1             */
#define hgr_page2()    (hgr_ss_sink = HGR_SS[5])  /* $C055 page 2             */
#define hgr_lores()    (hgr_ss_sink = HGR_SS[6])  /* $C056 RES latch = LORES  */
#define hgr_hires()    (hgr_ss_sink = HGR_SS[7])  /* $C057 RES latch = HIRES  */

#define HGR_PAGE1_ADDR   ((unsigned char*)0x2000) /* HIRES page-1 framebuffer (8 KB) */
#define HGR_PAGE2_ADDR   ((unsigned char*)0x4000) /* HIRES page-2 framebuffer (8 KB) */
#define HGR_LORES1 ((unsigned char*)0x0400) /* TEXT/LORES page-1 (shared, 1 KB) */
#define HGR_LORES2 ((unsigned char*)0x0800) /* TEXT/LORES page-2 (shared, 1 KB) */

/* graphics + hires + page 1 + full screen. */
void hgr_init(void);
/* Optional initializer for applications calling ASM kernels or reading the
 * row/column/mask/phase tables directly. Prepares every table without changing
 * display mode or draw page. Ordinary C drawing calls prepare their own tables. */
void hgr_build_tables(void);

/* BLANK-FIRST variant of hgr_init: clears the page-1 framebuffer
 * ($2000-$3FFF) while the display is parked on TEXT, THEN flips to HIRES.
 * The display has no display-enable bit and the framebuffer RAM is
 * indeterminate at power-on, so plain hgr_init shows uninitialized RAM until
 * the program's own clear lands — use this when your program cannot clear
 * immediately after init. (Page 2 is untouched; clear it via
 * hgr_set_draw_page(2) + hgr_clear(0) before showing it.) */
void hgr_init_clear(void);

/* Polite exit: TEXT + full screen + PAGE1, so the DOS prompt is visible.
 * Toggles only — a2_dos() (or returning from main) does it too:
 *     hgr_text_restore();
 *     a2_dos();                                    /- no-return -/           */
void hgr_text_restore(void);

/* Fill the current HIRES draw page with `fill` (0 = black). */
void hgr_clear(unsigned char fill);

/* Fast byte-aligned rectangle fill of the current HIRES draw page, via a
 * hand-written 6502 inner loop (hgr_byte_rect_asm.s). Fills `rows` scanlines from y0, byte columns
 * [col0, col0+ncols), with `val` (0 = erase). Horizontally byte-granular
 * (7px/byte, so col = x/7, ncols = how many 7px-wide bytes). This is the fast
 * way to erase the area behind text / a sprite without clearing the whole
 * screen — far cheaper than per-pixel hgr_unplot. The rectangle is clipped
 * to the screen. Example: erase a 16x16 digit drawn at x=123,y=88 ->
 * hgr_fill_rect(88, 16, 16, 8, 0). */
void hgr_fill_rect(unsigned char y0, unsigned char rows,
                        unsigned char col0, unsigned char ncols,
                        unsigned char val);

/* Current draw-page scanline y (0..191); NULL when y is out of range. */
unsigned char *hgr_row(unsigned char y);
/* Optional immutable addresses: page 1/2, y 0..191; NULL otherwise.
 * Independent of draw/display page, 384 bytes RODATA, no mutable tables. */
unsigned char * HGR_FASTCALL hgr_row_on_page(unsigned char page, unsigned char y);

/* Fill / erase a PIXEL-aligned rectangle [x, x+w) × [y, y+h) via a hand-written
 * 6502 inner loop (hgr_pixrect_asm.s) — unlike hgr_fill_rect these take pixel x/w,
 * not byte columns, so partial edge bytes are handled. fill = white, clear =
 * black. This is the fast way to draw/erase solid blocks (game tiles, sprites,
 * bars): one call replaces a per-pixel hgr_plot double loop (e.g. a 6×6
 * Snake cell = 1 call vs 36 plots). x:0..279, y:0..191; w (≤255) is clipped to
 * the right edge, h to the bottom. For full-width spans prefer hgr_fill_rect
 * (byte-aligned) or hgr_clear. */
void hgr_fill_pixrect(unsigned x, unsigned char y, unsigned char w, unsigned char h);
void hgr_clear_pixrect(unsigned x, unsigned char y, unsigned char w, unsigned char h);
/* Fill (set=1) / erase (set=0) a 6x6 block in the 8x8 grid cell (cx, cy).
 * cx*8/cy*8 done in asm, no clip — for 8px-grid games drawing one cell/call. */
void hgr_cell(unsigned char cx, unsigned char cy, unsigned char set);

/* Set a white pixel. x: 0..279, y: 0..191. Apple II interleaved HIRES layout. */
void hgr_plot(unsigned x, unsigned char y);

/* Clear a pixel (the inverse of hgr_plot) — lets a program erase a small
 * region without clearing the whole framebuffer. x: 0..279, y: 0..191. */
void hgr_unplot(unsigned x, unsigned char y);

/* Blit a 1-bit-per-pixel sprite at pixel (x, y). The bitmap is MSB-first (bit 7
 * = leftmost pixel), w pixels wide x h rows, each row padded to (w+7)/8 bytes,
 * top to bottom. A '1' bit is a sprite pixel; '0' is transparent. Three modes:
 *   HGR_SET   - OR  the pixels in (draw over black);
 *   HGR_CLEAR - clear the pixels (erase a known shape);
 *   HGR_XOR   - toggle the pixels: blit once to draw, blit AGAIN at the same
 *                spot to erase. Synchronize visible writes to avoid flicker.
 * Clipped to the screen on the right/bottom (keep x >= 0; off-screen-left is not
 * supported). HIRES is 7px/byte so this walks pixel by pixel; for solid blocks
 * hgr_fill_pixrect is far faster. Example (an 8x8 ball):
 *   static const unsigned char ball[8] = {0x3C,0x7E,0xFF,0xFF,0xFF,0xFF,0x7E,0x3C};
 *   hgr_blit(px, py, 8, 8, ball, HGR_XOR); */
#define HGR_SET    0u
#define HGR_CLEAR  1u
#define HGR_XOR    2u
void hgr_blit(unsigned x, unsigned char y, unsigned char w, unsigned char h,
                   const unsigned char *bitmap, unsigned char mode);

/* FAST byte-aligned blit for big solid sprites. The bitmap is pre-packed in the
 * framebuffer's 7px/byte layout (byte j, bit k = pixel j*7+k, bit 0 = leftmost,
 * bit 7 = 0), so whole bytes are SET/CLEAR/XOR'd in directly — ~7x fewer ops
 * than hgr_blit. Cost: the sprite snaps to a 7px column grid (x floored to
 * x/7), so move it in steps of 7 to keep XOR-erase aligned. `wbytes` = source
 * bytes per row = ceil(width/7). Same SET/CLEAR/XOR modes. Use this for a large
 * ball / paddle / tile; use hgr_blit when you need 1px positioning or
 * transparency at an arbitrary x. */
void hgr_blit7(unsigned x, unsigned char y, unsigned char wbytes,
                    unsigned char h, const unsigned char *src, unsigned char mode);

/* --- Pre-shifted sprite engine (the "Buzzard Bait" method) -----------------
 * hgr_blit  is pixel-precise but walks pixel-by-pixel (slow).
 * hgr_blit7 is byte-fast but snaps x to a 7px column grid (jumpy).
 * hgr_sprite gives BOTH: byte-aligned blit speed AND 1px-precise x.
 *
 * The trick (lifted from Sirius' 1983 arcade engine, see
 * POM1's sketchs/hgr/a2port_buzzard_bait/DISASSEMBLY.md S3): the sprite is baked
 * OFFLINE into 7 PRE-SHIFTED copies, one per sub-byte phase (x % 7 == 0..6).
 * At runtime the engine just selects the phase for x%7 and does a byte-aligned
 * blit at column x/7 -- zero per-pixel shifting; the inner loop is hgr_blit7.
 *
 * Cost: seven phase banks stored in the program. Build them with
 * dev/tools/assets/convert.py and wrap its data in hgr_sprite_t.
 * SET/CLEAR/XOR modes; XOR drawing twice at the same position restores the
 * original bytes, but the background shows through while drawn. Example:
 *     #include "ball.h"               // converter output: ball_data
 *     const hgr_sprite_t ball = {ball_data, BALL_STRIDE, BALL_HEIGHT};
 *     hgr_sprite(px, py, &ball, HGR_XOR);   // draw
 *     hgr_sprite(px, py, &ball, HGR_XOR);   // erase (same x,y)
 *
 * Data ABI (what the generator emits and this reads):
 *   stride = ceil((w + 6) / 7) bytes per row (uniform across the 7 phases;
 *            phase 6 spills one extra byte to the right).
 *   bits   = 7 contiguous phase blocks, each h*stride bytes, row-major,
 *            7px/byte (bit 0 = leftmost, bit 7 = 0). Phase p starts at
 *            offset p*(h*stride). Pixel (row,col) of phase p lives at packed
 *            bit (col+p): byte (col+p)/7, bit (col+p)%7. */
typedef struct {
    const unsigned char *bits;   /* 7 phase blocks, contiguous (h*stride apart) */
    unsigned char        stride; /* bytes per row per phase = ceil((w+6)/7)     */
    unsigned char        h;      /* rows                                         */
} hgr_sprite_t;

/* Blit a pre-shifted sprite bank at pixel (x, y). x is 1px-precise; clipped to
 * the right/bottom edges (keep x >= 0). mode is HGR_SET / HGR_CLEAR / HGR_XOR. */
void hgr_sprite(unsigned x, unsigned char y,
                     const hgr_sprite_t *spr, unsigned char mode);

/* Dedicated XOR sprite entry, equivalent to hgr_sprite(..., HGR_XOR).
 * Does not synchronize with the display. Caller must bound update time and
 * wait as appropriate; II/II+ have no readable VBL flag. */
void hgr_sprite_xor(unsigned x, unsigned char y, const hgr_sprite_t *spr);

/* --- Masked pre-shifted sprites + save-under (the SPRMASK family) ----------
 * hgr_sprite_xor is the fastest mover, but XOR is only self-erasing over
 * a background it also XORed -- over DECOR (text, coloured rects) the sprite
 * shows the background toggled through it. The masked engine draws OPAQUE
 * sprites over any background and puts the background back byte-exact:
 *
 *     dst[j] = (dst[j] & mask[j]) | data[j]
 *
 * Data ABI (what dev/tools/assets/convert.py emits, and what the
 * hgr_sprmask.s kernels read):
 *   stride = ceil((w + 6) / 7) bytes per row, uniform across the 7 phases
 *            (same rule as hgr_sprite_t).
 *   data   = 7 phase blocks, each h*stride bytes, row-major, 7px/byte
 *            (bit 0 = leftmost, bit 7 CLEAR). Phase p at offset p*(h*stride).
 *            These are the sprite's lit pixels, pre-shifted like a
 *            hgr_sprite_t bank.
 *   mask   = 7 phase blocks with the SAME geometry. A 1-bit KEEPS the
 *            background; mask = ~coverage (coverage = the sprite's footprint,
 *            optionally dilated by a --halo for a black outline). Bit 7 of
 *            every mask byte is ALWAYS 1, so the background byte's HIRES
 *            palette-group bit survives the draw (and data bit 7 is always 0,
 *            so the sprite never flips it). A hand-authored bank that wants to
 *            OWN the palette bit can clear mask bit 7 + set data bit 7 -- the
 *            kernel maths allows it; the generator never does. */
typedef struct {
    const unsigned char *data;   /* 7 phase blocks: pre-shifted pixels, bit7=0 */
    const unsigned char *mask;   /* 7 phase blocks: ~coverage, bit7=1 (KEEP)   */
    unsigned char        stride; /* bytes per row per phase = ceil((w+6)/7)    */
    unsigned char        h;      /* rows                                       */
} hgr_mspr_t;

/* --- Sprite engine: masked sprites with save-under on one or two pages ----
 * Up to HGR_SPR_MAX sprites. The static under-buffer pool always reserves
 * 2 * HGR_SPR_MAX * HGR_SPR_UNDER_BYTES bytes, even in single-buffer mode.
 * Initialize over clean backgrounds; draw the background on BOTH pages for
 * double buffering. The background under a drawn sprite must remain unchanged
 * until restoration. Larger ids draw on top; restore order is reversed.
 *
 * Double-buffer loop (include apple2frame.h and link APPLE2C_FRAME_SRCS):
 *     hgr_spr_move(0, x, y);
 *     hgr_spr_render();       // restore old sprites, draw on hidden page
 *     ...draw this page's HUD...
 *     a2_frame_wait();        // IIe VBL or delay fallback; initialize once
 *     hgr_spr_present();      // display it, select next draw page
 *
 * Single buffer: wait BEFORE render; writes remain visible and may tear.
 * hgr_spr_update() combines render + present immediately, without waiting.
 * Neither double buffering nor delay fallback alone guarantees no tearing. */
/* Build-time slot limit; use the same define in library and application.
 * Runtime count can be smaller. Default preserves the eight-slot ABI. */
#ifndef HGR_SPR_MAX
#define HGR_SPR_MAX          8u
#endif
#if HGR_SPR_MAX < 1 || HGR_SPR_MAX > 8
#error HGR_SPR_MAX must be between 1 and 8
#endif
#ifndef HGR_SPR_DAMAGE
#define HGR_SPR_DAMAGE 0
#endif
#if HGR_SPR_DAMAGE != 0 && HGR_SPR_DAMAGE != 1
#error HGR_SPR_DAMAGE must be 0 or 1
#endif
#define HGR_SPR_UNDER_BYTES  96u   /* compatibility pool capacity; external pool: 1..255 */

void hgr_spr_init(unsigned char double_buffered);
/* External pool: no compatibility pool (1536 bytes at the default slot limit)
 * is linked unless hgr_spr_init is
 * also called. count=1..HGR_SPR_MAX, capacity=1..255 bytes per sprite/page.
 * Requires count*capacity*(double_buffered ? 2 : 1) bytes. Returns 1 on
 * success, 0 on invalid configuration, preserving the previous engine.
 * Storage must remain resident and writable until reinitialization; initialize
 * over clean backgrounds. Main RAM, outside video pages. Not reentrant. */
unsigned char hgr_spr_init_pool(unsigned char double_buffered,
    unsigned char *pool, unsigned pool_bytes,
    unsigned char count, unsigned char capacity);
/* Returns 1 on success, 0 on invalid id/geometry or a still-drawn sprite.
 * For redefinition: hide, render/present once per page, then define. A
 * still-drawn sprite keeps its old definition if redefinition is attempted.
 * Invalid geometry on an undrawn slot deactivates it. NULL undefines a slot.
 * Shape/data/mask storage must stay valid and unchanged until both pages
 * have been restored. */
unsigned char hgr_spr_define(unsigned char id, const hgr_mspr_t *shape);
void hgr_spr_move(unsigned char id, unsigned x, unsigned char y);
void hgr_spr_hide(unsigned char id);
/* Keep unchanged lower layers; restore/redraw the suffix from the first change. */
void hgr_spr_render(void);
/* Display the engine page even after an application draw-page change. */
void hgr_spr_present(void);
/* Force redraw on page 1/2 or both (0), after safe background maintenance. */
void hgr_spr_invalidate(unsigned char page);
void hgr_spr_update(void);

/* UI RULE: native-size (x1) text must remain white. Only doubled (x2)
 * lettering may be colored; tint masks destroy thin small-font strokes.
 * Keep black padding between text and colored background graphics. */

/* Draw an ASCII string at pixel (x, y) using the built-in Beautiful Boot 8x8
 * font, pixel-doubled so the text is solid white (no NTSC colour artifacts) in
 * 16x16 cells on an 18px pitch. Renders into the current HIRES draw page; call hgr_init
 * + hgr_clear first. Non-printable chars render as a space. */
void hgr_puts(unsigned x, unsigned char y, const char *s);

/* Same Beautiful Boot font at its NATIVE 8x8 size (no pixel doubling): 7px glyph
 * cells on an 8px pitch, 8px tall. ~3-4x more text per line and faster than the
 * 16x16 hgr_puts — use it for dense HUDs / status lines. White into HIRES
 * draw page. Clips at y<=184 / x<=273. hgr_putu8 is the small-font number twin. */
void hgr_puts8(unsigned x, unsigned char y, const char *s);
void hgr_putu8(unsigned x, unsigned char y, unsigned value);

/* Draw `value` as unsigned decimal at (x, y), same 16x16 white cells / font as
 * hgr_puts (1-5 digits, no leading zeros). Handy for scores and counters. */
void hgr_putu(unsigned x, unsigned char y, unsigned value);

/* Fixed-width, right-aligned unsigned decimal with an opaque black field.
 * The field is `width` glyph cells wide (18px pitch); the call ERASES exactly
 * that box, then draws the digits flush-right in it. So an updating counter never
 * needs a separate clear_pixrect — a shrinking value leaves no stale digits and
 * the self-bounded wipe can't clip an adjacent label (the trap a hand-rolled
 * erase rectangle falls into). Values wider than the field overflow right, so
 * pick width >= the maximum digit count (e.g. width 5 for a 0..65535 score).
 * width is clamped to 1..14; width zero does nothing. Off-screen origins
 * (x>=280 or y>=192) are ignored. Page-aware (works while double buffering). */
void hgr_putu_field(unsigned x, unsigned char y, unsigned value,
                         unsigned char width);

/* Cached 16x16 numeric field, caller-owned (37 bytes on cc65).
 * Init requires a complete on-screen box, width 1..14. Owns a black field;
 * history is independent for each draw page. Keep the struct alive/immutable
 * except through these calls. Invalidate after clearing/changing its background.
 * putu returns changed cells, 0 if unchanged, 255 if value does not fit/null.
 * Overflow preserves both image and history. No conversion on unchanged value. */
#define HGR_HUD_INVALID 255u
typedef struct {
    unsigned x;
    unsigned char y, width, valid;
    unsigned value[2];
    char digits[2][14];
} hgr_hud_field_t;
unsigned char hgr_hud_init(hgr_hud_field_t *field, unsigned x,
                           unsigned char y, unsigned char width);
unsigned char hgr_hud_putu(hgr_hud_field_t *field, unsigned value);
/* page 0 invalidates both histories; 1/2 only that page. Other pages ignored. */
void hgr_hud_invalidate(hgr_hud_field_t *field, unsigned char page);

/* Compact opaque 8x8 numeric HUD, 8-pixel pitch, width 1..5. On cc65 the
 * caller-owned state is 19 bytes. Same return/cache/invalidation contracts
 * as the 16x16 HUD. Whole box must fit (y<=184, x+8*width<=280). */
typedef struct {
    unsigned x;
    unsigned char y, width, valid;
    unsigned value[2];
    char digits[2][5];
} hgr_hud8_field_t;
unsigned char hgr_hud8_init(hgr_hud8_field_t *field, unsigned x,
                          unsigned char y, unsigned char width);
unsigned char hgr_hud8_putu(hgr_hud8_field_t *field, unsigned value);
void hgr_hud8_invalidate(hgr_hud8_field_t *field, unsigned char page);

/* Signed decimal at (x, y): leading '-' then magnitude. OR-drawn (transparent,
 * no field erase) — use hgr_putu_field for fixed-width black-backed updates. */
void hgr_puti(unsigned x, unsigned char y, int value);

/* Unsigned hexadecimal at (x, y), uppercase, 1-4 digits, no leading zeros.
 * OR-drawn like hgr_putu (addresses, bit masks). */
void hgr_putx(unsigned x, unsigned char y, unsigned value);

/* --- Vector primitives (white, HIRES) -------------------------------------
 * Inclusive pixel endpoints (x:0..279, y:0..191), clipped to the screen. The
 * straight runs use the fast pixel-rectangle path; line/circle walk the LUT
 * plot. The Light Corridor demo hand-rolled all of these in raw asm — here they
 * are once, in the lib. */

/* Horizontal / vertical runs (inclusive). Fast: one STA run per scanline. */
void hgr_hline(unsigned x0, unsigned x1, unsigned char y);
void hgr_vline(unsigned x, unsigned char y0, unsigned char y1);

/* Bresenham line between two endpoints (both drawn). Rejects any endpoint
 * outside 280x192, including axes; no segment clipping. Axis spans are fast.
 * Diagonals OR bits and preserve palette; axes force white palette. */
void hgr_line(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1);

/* Rectangle OUTLINE through opposite corners (inclusive); interior untouched
 * (fill it with hgr_fill_pixrect for a solid box). */
void hgr_rect(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1);

/* Midpoint circle OUTLINE, centre (xc, yc), radius r; off-screen arcs clipped. */
void hgr_circle(unsigned xc, unsigned char yc, unsigned char r);

/* Ellipse OUTLINE inscribed in the (x0,y0)-(x1,y1) box (64-segment polyline).
 * Gained from the shared gfx layer (dev/lib/gfx); needs HGRC_GFX_SRCS at link. */
void hgr_ellipse(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1);

/* Draw a string in one of the four NTSC artifact COLOURS the HGR HIRES screen
 * can show (it has no per-pixel colour). Drawn in ONE tinted pass (hgr_text16_asm.s
 * hgr_blit_glyph ORs the colour's carrier bit per byte directly — no
 * white-then-recolorize round trip), and only the glyph itself is touched, so a
 * coloured label can sit right next to other content without bleeding a tint
 * over it. There is NO red on HIRES — orange is the warm tone. See hgr_puts
 * for layout. */
#define HGR_VIOLET  1u   /* mauve / purple */
#define HGR_GREEN   2u
#define HGR_ORANGE  3u   /* the closest thing HIRES has to "red" */
#define HGR_BLUE    4u
void hgr_puts_color(unsigned x, unsigned char y, const char *s, unsigned char color);

/* Tint an arbitrary PIXEL rectangle to one of the four artifact colours (the
 * graphics analogue of hgr_puts_color): draw a shape white, then recolour
 * [x..x+w) x [y..y+h). HIRES colour is byte-granular, so keep coloured shapes
 * ~1 empty cell apart. Black stays black, so an isolated shape tints cleanly. */
void hgr_colorize(unsigned x, unsigned char y, unsigned char w,
                       unsigned char h, unsigned char color);

/* ===========================================================================
 * LORES — 40×48 blocks of 16 colours (HGR low-resolution graphics)
 * ===========================================================================
 * Unlike HIRES, LORES has REAL per-block colour (it is not an NTSC artifact):
 * a 40-wide × 48-tall grid of 7px×4px coloured blocks. It shares the TEXT
 * page memory ($0400 page 1, Apple II row interleave): each text byte holds
 * TWO vertically-stacked blocks — the LOW nibble is the upper block (even
 * block-row), the HIGH nibble the lower one (odd block-row). So block (x, y)
 * with x:0..39, y:0..47 lives in nibble (y&1) of text-page byte
 * row(y>>1)+x. Colour is a 4-bit index 0..15 into the display's fixed palette
 * (the HGR_LO_* names below; same 16 colours as Apple II LORES). Mode is
 * selected by hgr_lores_init(). Renderer truth: GraphicsCard::renderLoRes. */

/* The fixed 16-colour LORES palette (GraphicsCard kApple2Palette order). */
#define HGR_LO_BLACK      0u
#define HGR_LO_MAGENTA    1u   /* dark red / magenta */
#define HGR_LO_DARKBLUE   2u
#define HGR_LO_PURPLE     3u
#define HGR_LO_DARKGREEN  4u
#define HGR_LO_GRAY1      5u   /* dark gray  */
#define HGR_LO_MEDBLUE    6u
#define HGR_LO_LIGHTBLUE  7u
#define HGR_LO_BROWN      8u
#define HGR_LO_ORANGE     9u
#define HGR_LO_GRAY2      10u  /* light gray */
#define HGR_LO_PINK       11u
#define HGR_LO_GREEN      12u  /* light green */
#define HGR_LO_YELLOW     13u
#define HGR_LO_AQUA       14u  /* aquamarine */
#define HGR_LO_WHITE      15u

/* Native 40-column graphics + LORES + page 1 + full screen. On IIe-class
 * machines, resets DHGR/80COL/80STORE and main RAMRD/RAMWRT before drawing. */
void hgr_lores_init(void);

/* Fill the whole 40×48 LORES draw page with one colour (low four bits).
 * Preserves the 64 screen-hole bytes used by peripheral firmware on each
 * page. Uses an 8-bit index for the inner stores. */
void hgr_lores_clear(unsigned char color);

/* Set / read one block. x:0..39, y:0..47, color:0..15 (a HGR_LO_* index).
 * Out-of-range plots are dropped; hgr_lores_getblock returns 0 off-screen. */
void hgr_lores_setblock(unsigned char x, unsigned char y, unsigned char color);
unsigned char hgr_lores_getblock(unsigned char x, unsigned char y);

/* Horizontal / vertical runs of blocks, both endpoints INCLUSIVE (Apple II
 * Applesoft HLIN/VLIN convention). Clipped to the 40×48 grid; an empty span
 * (x0>x1 / y0>y1) draws nothing. */
void hgr_lores_hlin(unsigned char x0, unsigned char x1, unsigned char y,
                     unsigned char color);
void hgr_lores_vlin(unsigned char x, unsigned char y0, unsigned char y1,
                     unsigned char color);

/* Fill a w×h block rectangle whose top-left is (x, y) with `color`. Clipped to
 * the grid (w/h past the edge are trimmed). */
void hgr_lores_fill_rect(unsigned char x, unsigned char y,
                          unsigned char w, unsigned char h, unsigned char color);

/* A II/II+ has no readable V-blank input. For
 * animation, draw on the hidden page and flip (below). This alone cannot
 * guarantee tear-free display; use apple2frame.h for IIe VBL synchronization. */

/* ===========================================================================
 * Double buffering — draw page vs display page (PAGE2)
 * ===========================================================================
 * The display has TWO framebuffers: page 1 (HIRES $2000 / LORES $0400) and page 2
 * (HIRES $4000 / LORES $0800). For full-screen animation you
 * draw the next frame into the HIDDEN page while the display shows the other, then
 * flip. Waiting for VBL before the flip on IIe avoids a mid-scan page change.
 *
 *   hgr_set_draw_page(page)  picks where EVERY drawing primitive writes (HIRES
 *                             and LORES alike); page is 1 or 2. Cheap but not
 *                             free — it re-derives the scanline tables, so set it
 *                             ONCE per frame, not per primitive. The per-pixel
 *                             plot/blit/fill hot paths are unchanged.
 *   hgr_show_page()          flips the display to display the CURRENT draw page
 *                             (the $C054/$C055 soft switch).
 *
 * Both pages share one mode — select it once (hgr_init / hgr_lores_init,
 * which also display page 1). The classic loop:
 *
 *     unsigned char draw = 2;
 *     hgr_init();
 *     for (;;) {
 *         hgr_set_draw_page(draw);
 *         hgr_clear(0);
 *         ...draw the frame...
 *         hgr_show_page();                  // freshly drawn page goes live
 *         draw = (draw == 1u) ? 2u : 1u;     // next frame -> the other page
 *     }
 */
void hgr_set_draw_page(unsigned char page);   /* 1 or 2 (out-of-range -> 1) */
unsigned char hgr_get_draw_page(void);         /* current draw page, 1 or 2 */
void hgr_show_page(void);                      /* display the current draw page */

#endif /* HGR_H */
