/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_blit7.c — sprite clipping wrapper.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_blit7(unsigned x, unsigned char y, unsigned char wbytes,
                    unsigned char h, const unsigned char *src, unsigned char mode)
{
    unsigned char col;
    hgr_build_tables();
    if (wbytes == 0u || h == 0u || y > 191u || x > 279u) return;
    col = hgr_col7[x];                                      /* no runtime divide */
    if (col >= 40u) return;
    hgr_b_col    = col;
    hgr_b_stride = wbytes;                                  /* full source row     */
    if ((unsigned)col + wbytes > 40u) wbytes = (unsigned char)(40u - col);/* R clip */
    hgr_b_w      = wbytes;
    hgr_b_y      = y;
    hgr_b_h      = ((unsigned)y + h > 192u) ? (unsigned char)(192u - y) : h;
    hgr_b_mode   = mode;
    hgr_b_src    = src;
    hgr_blit7_run();
}
