/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_lores_getblock.c — LORES hgr_lores_getblock (see hgr_lores.c). */
#include "hgr.h"
#include "hgr_internal.h"

unsigned char hgr_lores_getblock(unsigned char x, unsigned char y)
{
    unsigned char v;
    if (x >= 40u || y >= 48u) return 0u;
    hgr_lores_build();
    v = *hgr_lores_cell(x, y);
    return (unsigned char)((y & 1u) ? (v >> 4) : (v & 0x0Fu));
}
