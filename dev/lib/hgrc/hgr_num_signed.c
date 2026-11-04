/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_num_signed.c — HGR number formatting.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_puti(unsigned x, unsigned char y, int value)
{
    char buf[7];                     /* '-' + up to 5 digits + NUL */
    if (value < 0) {
        buf[0] = '-';
        hgr_u_ptr = buf + 1;
        /* Unsigned negation keeps the magnitude bits for -32768. */
        value = (int)(0u - (unsigned)value);
    } else hgr_u_ptr = buf;
    hgr_u_lo = (unsigned char)value;
    hgr_u_hi = (unsigned char)((unsigned)value >> 8);
    hgr_utoa();
    hgr_puts(x, y, buf);
}
