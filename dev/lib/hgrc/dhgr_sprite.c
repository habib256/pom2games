/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr.h"
#include "hgr_layout.h"
extern unsigned char dhgr_base;
extern unsigned char *dhgr_addr;
extern unsigned char dhgr_aux;

extern unsigned char *dhgr_buffer;
extern unsigned char dhgr_count;
extern const unsigned char *dhgr_sprite_mask;
void dhgr_sprite_asm(void);
static void byte_address(unsigned char bx, unsigned char y)
{
    dhgr_addr = (unsigned char *)(HGR_ROW_ADDR(dhgr_base, y) + (bx >> 1));
    dhgr_aux = (bx & 1u) ^ 1u;
}
void dhgr_sprite(unsigned char x, unsigned char y, unsigned char width,
                 unsigned char height, unsigned char stride,
                 const unsigned char *data, const unsigned char *mask)
{
    unsigned bits, shift, bank;
    unsigned char bx, n, row;
    if (x >= 140u || y >= 192u || !width || !height) return;
    bits = (unsigned)x * 4u;
    shift = bits % 7u;
    bx = (unsigned char)(bits / 7u);
    n = (unsigned char)(((unsigned)width * 4u + shift + 6u) / 7u);
    if (n > stride) return;
    if (n > 80u - bx) n = 80u - bx;
    bank = shift * (unsigned)stride * height;
    data += bank;
    mask += bank;
    if (height > 192u - y) height = 192u - y;
    for (row = 0; row < height; ++row) {
        byte_address(bx, y + row);
        dhgr_buffer = (unsigned char *)data;
        dhgr_sprite_mask = mask;
        dhgr_count = n;
        dhgr_sprite_asm();
        data += stride;
        mask += stride;
    }
}
