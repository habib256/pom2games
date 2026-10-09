/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_pixel.c — single-pixel plot/unplot via the asm col7/mask7 fast path. */

#include "hgr.h"
#include "hgr_internal.h"

/* Set / clear one white pixel via the assembly fast path (col7/mask7 LUTs +
 * the scanline-base table — NO per-pixel division). x:0..279, y:0..191.
 * Drop-in replacements for the old per-pixel-division versions; this is what
 * makes per-pixel games (Snake's 6x6 blocks, etc.) usable on the HGR. */
void hgr_plot(unsigned x, unsigned char y)
{
    if (x > 279u || y > 191u) return;
    hgr_build_rows();
    hgr_build_columns();
    hgr_build_masks();
    hgr_p_x = x;
    hgr_p_y = y;
    hgr_plot_asm();
}

void hgr_unplot(unsigned x, unsigned char y)
{
    if (x > 279u || y > 191u) return;
    hgr_build_rows();
    hgr_build_columns();
    hgr_build_masks();
    hgr_p_x = x;
    hgr_p_y = y;
    hgr_unplot_asm();
}
