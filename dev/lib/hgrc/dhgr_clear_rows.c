/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void dhgr_clear_row_asm(void);

void dhgr_clear_rows(unsigned char y, unsigned char rows, unsigned char color)
{
    if (y >= 192u || !rows) return;
    if (rows > 192u - y) rows = 192u - y;
    dhgr_prepare_pattern(color);
    do {
        dhgr_addr = (unsigned char *)HGR_ROW_ADDR(dhgr_base, y);
        dhgr_clear_row_asm();
        ++y;
    } while (--rows);
}
