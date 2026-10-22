/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void dhgr_bit_rect(unsigned x, unsigned char y, unsigned width,
                     unsigned char height)
{
    unsigned char rows;
    if (x >= DHGR_WIDTH || y >= DHGR_HEIGHT || !width || !height) return;
    /* Subtract first to avoid 16-bit wrap for an arbitrary width. */
    if (width > DHGR_WIDTH - x) width = DHGR_WIDTH - x;
    rows = (unsigned char)(DHGR_HEIGHT - y);
    if (height < rows) rows = height;
    dhgr_span_x = x;
    dhgr_span_end = x + width - 1u;
    dhgr_span_asm(((unsigned)rows << 8) | y);
}
