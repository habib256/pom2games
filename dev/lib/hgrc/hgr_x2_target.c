/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Bytewise x2 inflation. Each source byte produces two 7-bit output bytes
 * on each of two rows. Avoid the per-pixel loop miscompiled by cc65 -Oirs. */
#include "hgr_x2.h"

/* Spread four source bits into the even positions of an eight-bit byte. */
static const unsigned char spread[16] = {
    0, 1, 4, 5, 16, 17, 20, 21, 64, 65, 68, 69, 80, 81, 84, 85
};

void hgr_inflate_x2(const unsigned char *mono, unsigned char wbytes,
                    unsigned char h, unsigned char color, unsigned char *out)
{
    unsigned stride, dots;
    unsigned char row, col, bits, lo, hi, palette, left, right;
    unsigned char *bottom;
    if (!wbytes || !h) return;
#ifdef __CC65__
    if ((unsigned)wbytes * h > 16383u) return;
#endif
    stride = (unsigned)wbytes * 2u;
    left = color == HGR_X2_WHITE || color == HGR_X2_VIOLET || color == HGR_X2_BLUE;
    right = color == HGR_X2_WHITE || color == HGR_X2_GREEN || color == HGR_X2_ORANGE;
    palette = color == HGR_X2_BLUE || color == HGR_X2_ORANGE ? 128u : 0u;
    for (row = 0; row < h; ++row) {
        bottom = out + stride;
        for (col = 0; col < wbytes; ++col) {
            bits = *mono++;
            dots = spread[bits & 15u] | ((unsigned)spread[(bits >> 4) & 7u] << 8);
            if (left && right) dots |= dots << 1;
            else if (right) dots <<= 1;
            else if (!left) dots = 0u;
            lo = (unsigned char)(dots & 127u);
            hi = (unsigned char)(dots >> 7);
            if (lo) lo |= palette;
            if (hi) hi |= palette;
            *out++ = lo; *out++ = hi;
            *bottom++ = lo; *bottom++ = hi;
        }
        out = bottom;
    }
}
