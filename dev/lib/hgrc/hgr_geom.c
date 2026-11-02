/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_geom.c — vector drawing.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"
#include "gfx.h"

void hgr_hline(unsigned x0, unsigned x1, unsigned char y)
{
    if (x1 < x0) { unsigned t = x0; x0 = x1; x1 = t; }
    if (x0 > 279u || y > 191u) return;
    if (x1 > 279u) x1 = 279u;
    hgr_r_x = x0;
    hgr_r_xr = x1;
    hgr_r_y0 = y;
    hgr_r_rows = 1u;
    hgr_fill_span();
}

void hgr_vline(unsigned x, unsigned char y0, unsigned char y1)
{
    if (y1 < y0) { unsigned char t = y0; y0 = y1; y1 = t; }
    if (x > 279u || y0 > 191u) return;
    if (y1 > 191u) y1 = 191u;
    hgr_r_x = x;
    hgr_r_xr = x;
    hgr_r_y0 = y0;
    hgr_r_rows = (unsigned char)(y1 - y0 + 1u);
    hgr_fill_span();
}
