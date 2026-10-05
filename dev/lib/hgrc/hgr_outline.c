/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_outline.c — vector drawing.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"
#include "gfx.h"

void hgr_rect(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1)
{
    gfx_rect(x0, y0, x1, y1);
}
