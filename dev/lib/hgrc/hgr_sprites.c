/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_sprites.c — sprite clipping wrapper.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_blit(unsigned x, unsigned char y, unsigned char w, unsigned char h,
                   const unsigned char *bitmap, unsigned char mode)
{
    /* NO stack locals: store straight to the zero-page params, and run the clips
     * on hgr_b_w / hgr_b_h IN zp. cc65 -Oirs aggressively reuses a stack local's
     * slot as scratch while evaluating a 16-bit sub-expression (x+w>280), which
     * silently clobbered a local computed earlier (it ate the stride). zp params
     * are not scratch targets, so this side-steps the whole class of bug. stride
     * is derived from the FULL w (source row length); hgr_b_w is the clipped
     * pixel count to draw. */
    hgr_build_tables();
    if (y > 191u || w == 0u || h == 0u || x > 279u) return;

    hgr_b_col    = hgr_col7[x];              /* tables: no runtime divide/shift */
    hgr_b_mask   = hgr_mask7[x];
    /* stride = ceil(w/8), done with 8-bit ops only. The obvious (w+7)/8 makes
     * cc65 do a 16-bit divide whose high byte it leaves as garbage ($01), so
     * (8+7)=$010F /8 came out 33 — the (unsigned char) cast truncates too late. */
    hgr_b_stride = (unsigned char)((w >> 3) + ((w & 7u) != 0u));/* full source row */
    hgr_b_y      = y;
    hgr_b_mode   = mode;
    hgr_b_src    = bitmap;
    hgr_b_w      = w;
    hgr_b_h      = h;
    if ((unsigned)y + h > 192u) hgr_b_h = (unsigned char)(192u - y);  /* bottom clip */
    if ((unsigned)x + w > 280u) hgr_b_w = (unsigned char)(280u - x);  /* right clip  */
    hgr_blit_run();
}
