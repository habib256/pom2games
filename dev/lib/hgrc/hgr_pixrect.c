/* hgr_pixrect.c — rectangle drawing.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

static void hgr_pixrect(unsigned x, unsigned char y,
                         unsigned char w, unsigned char h, unsigned char set)
{
    unsigned xr;
    hgr_build_tables();
    if (w == 0u || h == 0u || x > 279u || y > 191u) return;
    xr = x + (unsigned)w - 1u;                 /* rightmost pixel               */
    if (xr > 279u) xr = 279u;                  /* clip right edge               */
    if ((unsigned)y + h > 192u) h = (unsigned char)(192u - y);   /* clip bottom */
    hgr_r_x    = x;
    hgr_r_xr   = xr;
    hgr_r_y0   = y;
    hgr_r_rows = h;
    hgr_r_mode = set;
    hgr_pixrect_asm();
}

void hgr_fill_pixrect(unsigned x, unsigned char y, unsigned char w, unsigned char h)
{
    hgr_pixrect(x, y, w, h, 1u);
}

void hgr_clear_pixrect(unsigned x, unsigned char y, unsigned char w, unsigned char h)
{
    hgr_pixrect(x, y, w, h, 0u);
}
