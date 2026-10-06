/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void dhgr_plot(unsigned x, unsigned char y, unsigned char set)
{
    if (x >= DHGR_WIDTH || y >= DHGR_HEIGHT) return;
    dhgr_pixel_address(x, y);
    dhgr_bits = set ? dhgr_mask : 0u;
    dhgr_write_asm();
}
