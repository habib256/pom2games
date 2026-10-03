/* hgr_circle.c — vector drawing.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"
#include "gfx.h"

void hgr_circle(unsigned xc, unsigned char yc, unsigned char r)
{
    gfx_circle(xc, yc, r);
}
