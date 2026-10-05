/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_num_unsigned.c — HGR number formatting.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_putu(unsigned x, unsigned char y, unsigned value)
{
    char buf[6];                     /* up to 5 digits + NUL */
    hgr_u_lo  = (unsigned char)(value & 0xFFu);
    hgr_u_hi  = (unsigned char)(value >> 8);
    hgr_u_ptr = buf;
    hgr_utoa();                     /* asm bin->dec (no cc65 software /10 + %10) */
    hgr_puts(x, y, buf);
}
