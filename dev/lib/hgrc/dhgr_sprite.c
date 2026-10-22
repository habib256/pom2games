/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"

void dhgr_sprite(unsigned char x, unsigned char y, unsigned char width,
                 unsigned char height, unsigned char stride,
                 const unsigned char *data, const unsigned char *mask)
{
    unsigned bank;
    unsigned char bx, n, row, shift, cell;
    if (x >= 140u || y >= 192u || !width || !height) return;
    shift = dhgr_cellphase[x];
    bx = dhgr_cellbyte[x];
    /* Bytes covered: ceil((4*width + shift) / 7); 4*140 dots are 80 bytes. */
    cell = width;
    n = 0;
    if (cell >= 140u) { cell -= 140u; n = 80u; }
    n += dhgr_cellbyte[cell];
    shift += dhgr_cellphase[cell];
    if (shift) n += shift > 7u ? 2u : 1u;
    shift = dhgr_cellphase[x];
    if (n > stride) return;
    if (n > 80u - bx) n = 80u - bx;
    bank = (unsigned)stride * height;
    while (shift--) { data += bank; mask += bank; }
    if (height > 192u - y) height = 192u - y;
    for (row = 0; row < height; ++row) {
        dhgr_byte_address(bx, y + row);
        dhgr_buffer = (unsigned char *)data;
        dhgr_sprite_mask = mask;
        dhgr_count = n;
        dhgr_sprite_asm();
        data += stride;
        mask += stride;
    }
}
