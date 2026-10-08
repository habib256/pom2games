/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/*
 * gfx_ellipse.c — card-neutral 64-segment polyline ellipse. See gfx.h.
 *
 * The biggest gain of the former gfx_draw.c split: this TU carries 128 bytes of
 * cos/sin LUT + drags the cc65 16-bit soft-multiply (because of the
 * /64 inside ((int)cos * rx) / 64). A line/rect/circle-only program now
 * skips both costs entirely.
 *
 * Drawn by stepping the parametric angle from 0..63/64 * 2π, plotting each
 * 64-segment chord through gfx_line (which itself routes straight runs to
 * the card's fast hline/vline path).
 */
#include "gfx.h"

/* cos/sin * 64 for parametric angle i/64 * 2π (upstream ellipse.s scale). */
static const signed char kEllipseCos64[64] = {
    64, 64, 63, 61, 59, 56, 53, 49, 45, 41, 36, 30, 24, 19, 12, 6,
    0, -6, -12, -19, -24, -30, -36, -41, -45, -49, -53, -56, -59, -61, -63, -64,
    -64, -64, -63, -61, -59, -56, -53, -49, -45, -41, -36, -30, -24, -19, -12, -6,
    0, 6, 12, 19, 24, 30, 36, 41, 45, 49, 53, 56, 59, 61, 63, 64
};
static const signed char kEllipseSin64[64] = {
    0, 6, 12, 19, 24, 30, 36, 41, 45, 49, 53, 56, 59, 61, 63, 64,
    64, 64, 63, 61, 59, 56, 53, 49, 45, 41, 36, 30, 24, 19, 12, 6,
    0, -6, -12, -19, -24, -30, -36, -41, -45, -49, -53, -56, -59, -61, -63, -64,
    -64, -64, -63, -61, -59, -56, -53, -49, -45, -41, -36, -30, -24, -19, -12, -6
};

static unsigned gfx_clamp_x(signed int v)
{
    if (v < 0) return 0;
    if (v >= (int)gfx_width) return (unsigned)(gfx_width - 1u);
    return (unsigned)v;
}
static unsigned char gfx_clamp_y(signed int v)
{
    if (v < 0) return 0;
    if (v >= (int)gfx_height) return (unsigned char)(gfx_height - 1u);
    return (unsigned char)v;
}

void gfx_ellipse(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1)
{
    signed int xc = (((signed int)x0 + (signed int)x1) >> 1);
    signed int yc = (((signed int)y0 + (signed int)y1) >> 1);
    signed int rx = (signed int)((x1 > x0 ? x1 - x0 : x0 - x1)) >> 1;
    signed int ry = (signed int)((y1 > y0 ? y1 - y0 : y0 - y1)) >> 1;
    unsigned char i;

    /* A zero integer radius collapses to a line inside the original box.
     * Forcing a radius of one draws outside point and one-pixel boxes. */
    if (rx == 0 && (x0 == x1 || y0 != y1)) {
        gfx_line(gfx_clamp_x(xc), gfx_clamp_y(y0),
                 gfx_clamp_x(xc), gfx_clamp_y(y1));
        return;
    }
    if (ry == 0) {
        gfx_line(gfx_clamp_x(x0), gfx_clamp_y(yc),
                 gfx_clamp_x(x1), gfx_clamp_y(yc));
        return;
    }

    for (i = 0; i < 64U; ++i) {
        unsigned char j = (unsigned char)((i + 1U) & 63U);
        signed int ax = xc + ((signed int)kEllipseCos64[i] * rx) / 64;
        signed int ay = yc + ((signed int)kEllipseSin64[i] * ry) / 64;
        signed int bx = xc + ((signed int)kEllipseCos64[j] * rx) / 64;
        signed int by = yc + ((signed int)kEllipseSin64[j] * ry) / 64;
        gfx_line(gfx_clamp_x(ax), gfx_clamp_y(ay),
                 gfx_clamp_x(bx), gfx_clamp_y(by));
    }
}
