/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_lores_vlin.c — LORES hgr_lores_vlin (see hgr_lores.c). */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_lores_vlin(unsigned char x, unsigned char y0, unsigned char y1,
                     unsigned char color)
{
    unsigned char y;
    if (x >= 40u || y0 >= 48u) return;
    if (y1 >= 48u) y1 = 47u;
    if (y0 > y1) return;
    hgr_lores_build();
    color &= 0x0Fu;
    for (y = y0; y <= y1; ++y) {
        unsigned char *p = hgr_lores_cell(x, y);
        if (y & 1u) *p = (unsigned char)((*p & 0x0Fu) | (color << 4));
        else        *p = (unsigned char)((*p & 0xF0u) | color);
    }
}
