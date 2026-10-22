/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_lores_rect.c — LORES hgr_lores_fill_rect (see hgr_lores.c). */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_lores_fill_rect(unsigned char x, unsigned char y,
                          unsigned char w, unsigned char h, unsigned char color)
{
    unsigned xr, yb, yy;
    if (w == 0u || h == 0u || x >= 40u || y >= 48u) return;
    xr = (unsigned)x + w; if (xr > 40u) xr = 40u;   /* one past right column   */
    yb = (unsigned)y + h; if (yb > 48u) yb = 48u;   /* one past bottom block-row */
    for (yy = y; yy < yb; ++yy)
        hgr_lores_hlin(x, (unsigned char)(xr - 1u), (unsigned char)yy, color);
}
