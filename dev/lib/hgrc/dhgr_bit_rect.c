/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void dhgr_bit_rect(unsigned x, unsigned char y, unsigned width,
                     unsigned char height)
{
    unsigned end_bit, bottom, row;
    unsigned char first, last, first_mask, last_mask, cy, tail;
    if (x >= DHGR_WIDTH || y >= DHGR_HEIGHT || !width || !height) return;
    /* Subtract first to avoid 16-bit wrap for an arbitrary width. */
    if (width > DHGR_WIDTH - x) width = DHGR_WIDTH - x;
    end_bit = x + width;
    bottom = (unsigned)y + height;
    if (bottom > DHGR_HEIGHT) bottom = DHGR_HEIGHT;
    first = (unsigned char)(x / 7u);
    last = (unsigned char)((end_bit - 1u) / 7u);
    first_mask = (unsigned char)((0x7Fu << (x % 7u)) & 0x7Fu);
    tail = (unsigned char)(end_bit % 7u);
    last_mask = tail ? (unsigned char)((1u << tail) - 1u) : 0x7Fu;
    for (cy = y; cy < bottom; ++cy) {
        row = HGR_ROW_ADDR(dhgr_base, cy);
        dhgr_addr = (unsigned char *)row;
        dhgr_first = first;
        dhgr_last = last;
        dhgr_first_mask = first_mask;
        dhgr_last_mask = last_mask;
        dhgr_span_asm();
    }
}
