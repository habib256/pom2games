/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_lores_hlin.c — LORES hgr_lores_hlin (see hgr_lores.c). */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_lores_hlin(unsigned char x0, unsigned char x1, unsigned char y,
                     unsigned char color)
{
    unsigned char *base, keep, val, x;
    if (y >= 48u || x0 >= 40u) return;
    if (x1 >= 40u) x1 = 39u;
    if (x0 > x1) return;
    hgr_lores_build();
    base = hgr_lores_cell(0u, y);              /* row base; cell adds x below */
    color &= 0x0Fu;
    if (y & 1u) { keep = 0x0Fu; val = (unsigned char)(color << 4); }
    else        { keep = 0xF0u; val = color; }
    for (x = x0; x <= x1; ++x)
        base[x] = (unsigned char)((base[x] & keep) | val);
}
