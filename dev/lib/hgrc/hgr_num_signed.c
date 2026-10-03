/* hgr_num_signed.c — HGR number formatting.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_puti(unsigned x, unsigned char y, int value)
{
    char buf[7];                     /* '-' + up to 5 digits + NUL */
    char *dst = buf;
    unsigned mag;
    if (value < 0) { buf[0] = '-'; dst = buf + 1; mag = (unsigned)(-value); }
    else           { mag = (unsigned)value; }
    hgr_u_lo  = (unsigned char)(mag & 0xFFu);
    hgr_u_hi  = (unsigned char)(mag >> 8);
    hgr_u_ptr = dst;
    hgr_utoa();
    hgr_puts(x, y, buf);
}
