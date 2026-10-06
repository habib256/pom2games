/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void dhgr_fill_rect(unsigned char x, unsigned char y,
                    unsigned char width, unsigned char height,
                    unsigned char color)
{
    unsigned right;
    if (x >= DHGR_COLOR_WIDTH) return;
    right = (unsigned)x + width;
    if (right > DHGR_COLOR_WIDTH) right = DHGR_COLOR_WIDTH;
    dhgr_prepare_pattern(color);
    dhgr_bit_rect((unsigned)x * 4u, y, (right - x) * 4u, height);
}
