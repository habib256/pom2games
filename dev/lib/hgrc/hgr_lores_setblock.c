/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_lores_setblock.c — LORES hgr_lores_setblock (see hgr_lores.c). */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_lores_setblock(unsigned char x, unsigned char y, unsigned char color)
{
    unsigned char *p;
    if (x >= 40u || y >= 48u) return;
    hgr_lores_build();
    p = hgr_lores_cell(x, y);
    color &= 0x0Fu;
    if (y & 1u) *p = (unsigned char)((*p & 0x0Fu) | (color << 4));  /* lower block */
    else        *p = (unsigned char)((*p & 0xF0u) | color);         /* upper block */
}
