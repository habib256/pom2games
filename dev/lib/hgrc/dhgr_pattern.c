/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
static unsigned char color_bits(unsigned char color)
{
    color &= 15u;
    return (unsigned char)(((color >> 1) | (color << 3)) & 15u);
}

void dhgr_prepare_pattern(unsigned char color)
{
    unsigned pattern;
    unsigned char i;
    pattern = (unsigned)color_bits(color) * 0x1111u;
    for (i = 0; i < 4u; ++i)
        dhgr_pattern[i] = (unsigned char)((pattern >> ((i * 7u) & 3u)) & 0x7Fu);
}
