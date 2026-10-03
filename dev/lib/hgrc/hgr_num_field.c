/* hgr_num_field.c — HGR number formatting.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

static unsigned char hgr_slen(const char *s)
{
    unsigned char n = 0u;
    while (s[n]) ++n;
    return n;
}

void hgr_putu_field(unsigned x, unsigned char y, unsigned value,
                         unsigned char width)
{
    char buf[6];
    unsigned char len;
    unsigned dx;
    if (width == 0u) return;
    if (width > 14u) width = 14u;
    hgr_u_lo  = (unsigned char)(value & 0xFFu);
    hgr_u_hi  = (unsigned char)(value >> 8);
    hgr_u_ptr = buf;
    hgr_utoa();
    len = hgr_slen(buf);
    /* Erase the field box: (width-1) full pitches + one 16px cell, 16px tall. */
    hgr_clear_pixrect(x, y,
                           (unsigned char)((unsigned)(width - 1u) * 18u + 16u), 16u);
    /* Flush-right: blank the leading (width-len) cells; overflow if len>=width. */
    dx = (len < width) ? (x + (unsigned)(width - len) * 18u) : x;
    hgr_puts(dx, y, buf);
}
