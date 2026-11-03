/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void dhgr_fill_bits(unsigned x, unsigned char y, unsigned width,
                    unsigned char height, unsigned char set)
{
    /* All four byte phases are identical in monochrome: decide once. */
    dhgr_pattern[0] = dhgr_pattern[1] = dhgr_pattern[2] = dhgr_pattern[3] =
        set ? 0x7F : 0;
    dhgr_bit_rect(x, y, width, height);
}
