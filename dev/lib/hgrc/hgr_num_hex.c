/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_num_hex.c — HGR number formatting.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"
#include "gfx.h"

void hgr_putx(unsigned x, unsigned char y, unsigned value)
{
    char buf[5];
    gfx_hexstr(buf, value);
    hgr_puts(x, y, buf);
}
