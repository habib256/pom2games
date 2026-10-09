/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_colorize.c — rectangle drawing.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_colorize(unsigned x, unsigned char y, unsigned char w,
                       unsigned char h, unsigned char color)
{
    unsigned right;

    /* hgr_colorize_asm() indexes hgr_rowlo/hgr_rowhi by scanline; those
     * tables are zero-init BSS until hgr_build_rows() fills them. Every other
     * drawing entry point builds them first, so colorize must too — otherwise,
     * as the first hgrc call, each scanline base reads $0000 and writes land in
     * low RAM. Both builders are idempotent. */
    hgr_build_rows();
    hgr_build_columns();

    if (w == 0u || h == 0u || y > 191u || x > 279u) return;
    if (!hgr_set_carrier(color)) return;
    if ((unsigned)y + h > 192u) h = (unsigned char)(192u - y);

    right = x + (unsigned)w - 1u;
    if (right > 279u) right = 279u;
    hgr_z_col0  = hgr_col7[x];               /* tables: no runtime divide */
    hgr_z_ncols = (unsigned char)(hgr_col7[right] - hgr_col7[x] + 1u);
    hgr_z_y0    = y;
    hgr_z_rows  = h;
    hgr_colorize_asm();
}
