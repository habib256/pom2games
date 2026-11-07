/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/*
 * Portable reference; hgrc.mk selects native rectangle/clear members.
 * gfx_backend_hgr_rect_ref.c — gfx_filled_rect + gfx_clear forwarders for the
 * Apple II HGR backend.
 *
 * Split from gfx_backend_hgr_ref.c so a HGR program that only draws
 * lines/circles/ellipses never references gfx_filled_rect or
 * hgr_clear, keeping ld65 dead-strip symmetric with the TMS side.
 */
#include "gfx.h"
#define HGR_NO_APPLE2
#include "hgr.h"          /* -I dev/lib/hgrc */
#include "hgr_internal.h"

void gfx_filled_rect(unsigned x0, unsigned char y0,
                     unsigned x1, unsigned char y1)
{
    if (x1 < x0) { unsigned t = x0; x0 = x1; x1 = t; }
    if (y1 < y0) { unsigned char t = y0; y0 = y1; y1 = t; }
    /* Clip before computing inclusive dimensions: x1 may be 65535 and
     * y1 may be 255. The kernel accepts full-width inclusive endpoints. */
    if (x0 >= 280u || y0 >= 192u) return;
    if (x1 >= 280u) x1 = 279u;
    if (y1 >= 192u) y1 = 191u;
    hgr_r_x = x0;
    hgr_r_xr = x1;
    hgr_r_y0 = y0;
    hgr_r_rows = (unsigned char)(y1 - y0 + 1u);
    hgr_fill_span();
}

void gfx_clear(unsigned char color) { hgr_clear(color); }
