/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"

static void transfer(unsigned char bx, unsigned char y, unsigned char width,
                     unsigned char height, unsigned char *data,
                     unsigned char stride, unsigned char read)
{
    unsigned char row;
    if (bx >= 80u || y >= 192u || width > stride || !width) return;
    dhgr_count = width > 80u - bx ? 80u - bx : width;
    if (height > 192u - y) height = 192u - y;
    for (row = 0; row < height; ++row) {
        dhgr_byte_address(bx, y + row);
        dhgr_buffer = data;
        if (read) dhgr_read_block_asm(); else dhgr_write_block_asm();
        data += stride;
    }
}
void dhgr_read_block(unsigned char bx, unsigned char y, unsigned char width,
                     unsigned char height, unsigned char *data, unsigned char stride)
{
    transfer(bx,y,width,height,data,stride,1);
}
void dhgr_write_block(unsigned char bx, unsigned char y, unsigned char width,
                      unsigned char height, const unsigned char *data, unsigned char stride)
{
    transfer(bx,y,width,height,(unsigned char *)data,stride,0);
}
