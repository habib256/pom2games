/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"

/* Interleaved byte coordinate: auxiliary first, then main, across 80 bytes. */
void dhgr_byte_address(unsigned char bx, unsigned char y)
{
    dhgr_addr = (unsigned char *)(HGR_ROW_ADDR(dhgr_base, y) + (bx >> 1));
    dhgr_aux = (bx & 1u) ^ 1u;
}
