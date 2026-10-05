/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/*
 * gfx_text_backend_hgr.c — Apple II HGR backend for the gfx_text cell façade (AXIS 3).
 *
 * Maps the card-neutral 8x8 cell model onto HGR's NATIVE 8x8 glyph blit
 * (hgr_puts8): cell (col,row) -> pixel (col*8, row*8). 280x192 / 8 = 35x24.
 *
 * Colour: the 8x8 cell path is white-only — HGR's per-pixel colour is the NTSC
 * artifact trick, available only on the 16x16 doubled glyphs (hgr_puts_color).
 * Levelling that into the cell model would be a lie (no 8x8 colour exists), so
 * gfx_cell_color is a documented no-op here; reach for hgr_puts_color when a
 * HGR program wants colour. This keeps the façade neutral without capping HGR.
 *
 * Build: compiled in a HGR program with -I dev/lib/hgrc (hgr.h) and
 *        -I dev/lib/gfx (gfx.h). Linked from gfx-hgr.lib.
 */
#include "gfx.h"
#define HGR_NO_APPLE2     /* prototypes only — no -I dev/lib/apple2c needed */
#include "hgr.h"          /* -I dev/lib/hgrc */

const unsigned char gfx_text_cols = 35u;   /* 280 / 8 */
const unsigned char gfx_text_rows = 24u;   /* 192 / 8 */

void gfx_cell_color(unsigned char color)
{
    (void)color;           /* 8x8 cells are white — see header note */
}

void gfx_cell_glyph(char ch, unsigned char col, unsigned char row)
{
    char buf[2];
    buf[0] = ch;
    buf[1] = 0;
    /* col*8 <= 272 and row*8 <= 184 satisfy hgr_puts8's x<=273 / y<=184. */
    hgr_puts8((unsigned)col * 8u, (unsigned char)(row * 8u), buf);
}
