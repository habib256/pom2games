/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_num_field.c — HGR number formatting.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "gfx.h"

void hgr_putu_field(unsigned x, unsigned char y, unsigned value,
                         unsigned char width)
{
    char buf[6];
    unsigned char len;
    /* Reject off-screen origins before the right-alignment addition can
     * wrap a 16-bit coordinate back onto the screen. */
    if (width == 0u || x >= 280u || y >= 192u) return;
    if (width > 14u) width = 14u;
    len = gfx_utoa(buf, value);
    /* width <=14: width*18-2 fits in one byte. */
    hgr_clear_pixrect(x, y, (unsigned char)((width << 4) + (width << 1) - 2u), 16u);
    if (len < width) {
        width -= len;
        x += ((unsigned)width << 4) + ((unsigned)width << 1);
    }
    hgr_puts(x, y, buf);
}
