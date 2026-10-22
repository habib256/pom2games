/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_lores.c — 40x48 blocks of 16 real colours.
 *
 * LORES lives in the TEXT page ($0400), Apple II row interleave, two stacked
 * blocks per byte (low nibble = upper / even block-row, high = lower / odd).
 * The grid is tiny (40x48 = 1920 blocks) and the addressing is pure shifts +
 * masks (no x/7 per-pixel division as HIRES needs), so plain C is fast enough
 * — no asm fast path. A 24-entry text-row base table is built once on the
 * first lores call. The table state (hgr_lo_rowlo/hi, hgr_lo_base,
 * hgr_lo_ready) lives in hgr_init.c so a HIRES-only program does not pull
 * this file into the link.
 *
 * One archive member per entry point (hgr_lores_*.c), so a program links
 * only what it calls; this one holds the shared row table and cell address. */

#include "hgr.h"
#include "hgr_internal.h"

void hgr_lores_build(void)
{
    unsigned r, a;
    if (hgr_lo_ready) return;
    if (!hgr_lo_base) hgr_lo_base = 0x04u;   /* BSS default: page 1 */
    for (r = 0; r < 24u; ++r) {
        /* base + $80*(r&7) + $28*(r>>3); r>>3 is only 0,1,2 so add directly. */
        a = ((unsigned)hgr_lo_base << 8) + ((unsigned)(r & 7u) << 7);
        if ((r >> 3) == 1u)      a += 0x28u;
        else if ((r >> 3) == 2u) a += 0x50u;
        hgr_lo_rowlo[r] = (unsigned char)(a & 0xFFu);
        hgr_lo_rowhi[r] = (unsigned char)(a >> 8);
    }
    hgr_lo_ready = 1;
}

unsigned char *hgr_lores_cell(unsigned char x, unsigned char y)
{
    unsigned char r = y >> 1;        /* text row 0..23 */
    return (unsigned char *)(((unsigned)hgr_lo_rowhi[r] << 8)
                             | hgr_lo_rowlo[r]) + x;
}
