/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/*
 * gfx_ellipse.c — card-neutral 64-segment polyline ellipse. See gfx.h.
 *
 * The biggest gain of the former gfx_draw.c split: this TU carries 128 bytes of
 * cos/sin LUT + drags the cc65 16-bit soft-multiply for scaled radii.
 * A line/rect/circle-only program now
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

static unsigned gfx_clamp_x(unsigned v)
{
    if (v >= gfx_width) return (unsigned)(gfx_width - 1u);
    return v;
}

/* The radius is at most 32767. Split the scaled product so neither
 * multiplication exceeds 16 bits, including boxes ending at 65535.
 * For ordinary screen-sized radii, keep the original single multiply.
 * centre +/- offset stays inside the unsigned bounding box. */
static int gfx_ellipse_offset(unsigned radius, signed char c)
{
    unsigned magnitude, offset;
    magnitude = (unsigned)(c < 0 ? -(int)c : (int)c);
    if (radius < 512u)
        offset = (radius * magnitude) >> 6;
    else
        offset = (radius >> 6) * magnitude +
                 (((radius & 63u) * magnitude) >> 6);
    /* Apply the sign after division: cc65 optimizes signed /64 into an
     * arithmetic shift, rounding negative products down instead of to zero. */
    return c < 0 ? -(int)offset : (int)offset;
}
static unsigned char gfx_clamp_y(signed int v)
{
    if (v < 0) return 0;
    if (v >= (int)gfx_height) return (unsigned char)(gfx_height - 1u);
    return (unsigned char)v;
}

void gfx_ellipse(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1)
{
    unsigned xc, rx, ax;
    signed int yc, ry, ay;
    unsigned char i;

    /* Reject invisible boxes before clamping points or doing signed math. */
    if ((x0 >= gfx_width && x1 >= gfx_width) ||
        (y0 >= gfx_height && y1 >= gfx_height)) return;

    if (x1 < x0) { unsigned t = x0; x0 = x1; x1 = t; }
    rx = (x1 - x0) >> 1;
    xc = x0 + rx;
    yc = (((signed int)y0 + (signed int)y1) >> 1);
    ry = (signed int)((y1 > y0 ? y1 - y0 : y0 - y1)) >> 1;

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

    ax = gfx_clamp_x(xc + rx);
    ay = gfx_clamp_y(yc);
    for (i = 0; i < 64U; ++i) {
        unsigned char j = (unsigned char)((i + 1U) & 63U);
        unsigned bx = gfx_clamp_x(xc + gfx_ellipse_offset(rx, kEllipseCos64[j]));
        unsigned char by = gfx_clamp_y(yc + gfx_ellipse_offset((unsigned)ry, kEllipseSin64[j]));
        gfx_line(ax, (unsigned char)ay, bx, by);
        ax = bx;
        ay = by;
    }
}
