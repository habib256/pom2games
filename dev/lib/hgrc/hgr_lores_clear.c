/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_lores_clear.c — LORES hgr_lores_clear (see hgr_lores.c). */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_lores_clear(unsigned char color)
{
    /* Both nibbles = colour. Each 128-byte region has 120 visible bytes
     * followed by eight screen holes, which hold peripheral firmware state.
     * Fill both halves of four pages, leaving all 64 mailbox bytes intact. */
    unsigned char v = (unsigned char)((color & 0x0Fu) | (color << 4));
    unsigned base;
    unsigned char *p0, *p1, *p2, *p3;
    unsigned char i, half;
    if (!hgr_lo_base) hgr_lo_base = 0x04u;   /* BSS default: page 1 */
    base = (unsigned)hgr_lo_base << 8;
    for (half = 0u; half < 2u; ++half) {
        p0 = (unsigned char *)(base);
        p1 = (unsigned char *)(base + 0x100u);
        p2 = (unsigned char *)(base + 0x200u);
        p3 = (unsigned char *)(base + 0x300u);
        for (i = 0u; i < 120u; ++i) {
            p0[i] = v;
            p1[i] = v;
            p2[i] = v;
            p3[i] = v;
        }
        base += 0x80u;
    }
}
