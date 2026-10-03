/*
 * gfx_backend_hgr_rect.c — gfx_filled_rect + gfx_clear forwarders for the
 * Apple II HGR backend.
 *
 * Split from gfx_backend_hgr.c so a HGR program that only draws
 * lines/circles/ellipses never references hgr_fill_pixrect or
 * hgr_clear, keeping ld65 dead-strip symmetric with the TMS side.
 */
#include "gfx.h"
#define HGR_NO_APPLE2
#include "hgr.h"          /* -I dev/lib/hgrc */

void gfx_filled_rect(unsigned x0, unsigned char y0,
                     unsigned x1, unsigned char y1)
{
    unsigned width;
    unsigned char chunk, height;
    if (x1 < x0) { unsigned t = x0; x0 = x1; x1 = t; }
    if (y1 < y0) { unsigned char t = y0; y0 = y1; y1 = t; }
    /* Clip before computing inclusive dimensions: x1 may be 65535 and
     * y1 may be 255. The low-level HGR API accepts at most 255 pixels. */
    if (x0 >= 280u || y0 >= 192u) return;
    if (x1 >= 280u) x1 = 279u;
    if (y1 >= 192u) y1 = 191u;
    width = x1 - x0 + 1u;
    height = (unsigned char)(y1 - y0 + 1u);
    while (width) {
        chunk = width > 255u ? 255u : (unsigned char)width;
        hgr_fill_pixrect(x0, y0, chunk, height);
        x0 += chunk;
        width -= chunk;
    }
}

void gfx_clear(unsigned char color) { hgr_clear(color); }
