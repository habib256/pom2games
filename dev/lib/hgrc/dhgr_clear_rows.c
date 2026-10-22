/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void __fastcall__ dhgr_clear_rows_asm(unsigned rows_y);

void dhgr_clear_rows(unsigned char y, unsigned char rows, unsigned char color)
{
    if (y >= 192u || !rows) return;
    if (rows > 192u - y) rows = 192u - y;
    dhgr_prepare_pattern(color);
    dhgr_clear_rows_asm(((unsigned)rows << 8) | y);
}
