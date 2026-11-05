/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Portable reference; hgrc.mk selects gfx_line_hgr.s.
 * Portable HGR reference; target generic backends select gfx_line.s instead.
 * Keep historical clipping for axis spans, reject off-screen diagonals. */
#include "gfx.h"
#define HGR_NO_APPLE2
#include "hgr.h"

void gfx_line(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1)
{
    if (y0 == y1) { gfx_hline(x0, x1, y0); return; }
    if (x0 == x1) { gfx_vline(x0, y0, y1); return; }
    hgr_line(x0, y0, x1, y1);
}
