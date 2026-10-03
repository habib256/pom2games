/* hgr_num_small.c — HGR number formatting.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_putu8(unsigned x, unsigned char y, unsigned value)
{
    char buf[6];
    hgr_u_lo  = (unsigned char)(value & 0xFFu);
    hgr_u_hi  = (unsigned char)(value >> 8);
    hgr_u_ptr = buf;
    hgr_utoa();
    hgr_puts8(x, y, buf);
}
