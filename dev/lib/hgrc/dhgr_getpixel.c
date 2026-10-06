/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
unsigned char dhgr_getpixel(unsigned x, unsigned char y)
{
    if (x >= DHGR_WIDTH || y >= DHGR_HEIGHT) return 0u;
    dhgr_pixel_address(x, y);
    return (unsigned char)((dhgr_read_asm() & dhgr_mask) != 0u);
}
