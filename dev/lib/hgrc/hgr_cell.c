/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_cell.c — rectangle drawing.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_cell(unsigned char cx, unsigned char cy, unsigned char set)
{
    hgr_build_rows();
    hgr_build_columns();
    hgr_build_masks();
    hgr_c_cx  = cx;
    hgr_c_cy  = cy;
    hgr_c_set = set;
    hgr_cell_asm();
}
