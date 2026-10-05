/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Link exactly one DHGR backend. Mono coordinates are 560x192. */
#include "gfx.h"
#include "dhgr.h"
const unsigned gfx_width = 560u;
const unsigned char gfx_height = 192u;
static unsigned char pen;
void dhgr_set_color(unsigned char set) { pen = set != 0; }
void gfx_plot(unsigned x,unsigned char y) { dhgr_plot(x,y,pen); }
void gfx_hline(unsigned x0,unsigned x1,unsigned char y) { dhgr_hline(x0,x1,y,pen); }
void gfx_vline(unsigned x,unsigned char y0,unsigned char y1) { dhgr_vline(x,y0,y1,pen); }
void gfx_filled_rect(unsigned x0,unsigned char y0,unsigned x1,unsigned char y1)
{
    unsigned t; unsigned char b;
    if (x1<x0) { t=x0; x0=x1; x1=t; }
    if (y1<y0) { b=y0; y0=y1; y1=b; }
    if (x0>=560u || y0>=192u) return;
    if (x1>=560u) x1=559u;
    if (y1>=192u) y1=191u;
    dhgr_fill_bits(x0,y0,x1-x0+1u,y1-y0+1u,pen);
}
void gfx_clear(unsigned char color) { dhgr_clear(color ? DHGR_WHITE : DHGR_BLACK); }
