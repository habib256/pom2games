/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_line.c — vector drawing.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"
extern unsigned hgr_l_x0, hgr_l_x1;
extern unsigned char hgr_l_y0, hgr_l_y1;
void hgr_line_asm(void);

void hgr_line(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1)
{
    if (x0 > 279u || x1 > 279u || y0 > 191u || y1 > 191u) return;
    if (y0 == y1) { hgr_hline(x0, x1, y0); return; }
    if (x0 == x1) { hgr_vline(x0, y0, y1); return; }
    hgr_build_rows();
    hgr_build_columns();
    hgr_build_masks();
    hgr_l_x0 = x0; hgr_l_x1 = x1;
    hgr_l_y0 = y0; hgr_l_y1 = y1;
    hgr_line_asm();
}
