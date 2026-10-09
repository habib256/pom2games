/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_rect.c — rectangle drawing.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_fill_rect(unsigned char y0, unsigned char rows,
                        unsigned char col0, unsigned char ncols,
                        unsigned char val)
{
    hgr_build_rows();
    if (rows == 0u || ncols == 0u || y0 > 191u || col0 >= 40u) return;
    if ((unsigned)y0   + rows  > 192u) rows  = (unsigned char)(192u - y0);
    if ((unsigned)col0 + ncols >  40u) ncols = (unsigned char)(40u  - col0);
    hgr_f_y0   = y0;
    hgr_f_rows = rows;
    hgr_f_col0 = col0;
    hgr_f_cols = ncols;
    hgr_f_val  = val;
    hgr_fill_rect_asm();
}
