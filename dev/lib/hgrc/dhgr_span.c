#include "dhgr.h"
void dhgr_hline(unsigned x0, unsigned x1, unsigned char y, unsigned char set)
{
    unsigned t;
    if (x1 < x0) { t = x0; x0 = x1; x1 = t; }
    if (x0 >= 560u) return;
    if (x1 >= 560u) x1 = 559u;
    dhgr_fill_bits(x0, y, x1 - x0 + 1u, 1u, set);
}
void dhgr_vline(unsigned x, unsigned char y0, unsigned char y1, unsigned char set)
{
    unsigned char t;
    if (y1 < y0) { t = y0; y0 = y1; y1 = t; }
    if (y0 >= 192u) return;
    if (y1 >= 192u) y1 = 191u;
    dhgr_fill_bits(x, y0, 1u, (unsigned char)(y1 - y0 + 1u), set);
}
