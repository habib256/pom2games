/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void dhgr_fill_bits(unsigned x, unsigned char y, unsigned width,
                    unsigned char height, unsigned char set)
{
    unsigned char i;
    for (i = 0; i < 4; ++i) dhgr_pattern[i] = set ? 0x7F : 0;
    dhgr_bit_rect(x, y, width, height);
}
