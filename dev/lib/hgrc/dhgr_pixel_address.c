/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void dhgr_pixel_address(unsigned x, unsigned char y)
{
    unsigned char byte = (unsigned char)(x / 7u);
    dhgr_addr = (unsigned char *)(HGR_ROW_ADDR(dhgr_base, y) + (byte >> 1));
    dhgr_aux = (unsigned char)((byte & 1u) ^ 1u);
    dhgr_mask = (unsigned char)(1u << (x % 7u));
}
