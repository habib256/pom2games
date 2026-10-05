/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_geom.c — vector drawing.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"
#include "gfx.h"

void hgr_hline(unsigned x0, unsigned x1, unsigned char y)
{
    unsigned len;
    if (x1 < x0) { unsigned t = x0; x0 = x1; x1 = t; }
    if (x0 > 279u || y > 191u) return;
    if (x1 > 279u) x1 = 279u;
    len = x1 - x0 + 1u;                          /* 1..280 */
    while (len) {
        unsigned char chunk = (len > 255u) ? 255u : (unsigned char)len;
        hgr_fill_pixrect(x0, y, chunk, 1u);
        x0  += chunk;
        len -= chunk;
    }
}

void hgr_vline(unsigned x, unsigned char y0, unsigned char y1)
{
    if (y1 < y0) { unsigned char t = y0; y0 = y1; y1 = t; }
    if (x > 279u || y0 > 191u) return;
    if (y1 > 191u) y1 = 191u;
    hgr_fill_pixrect(x, y0, 1u, (unsigned char)(y1 - y0 + 1u));
}
