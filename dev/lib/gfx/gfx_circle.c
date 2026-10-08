/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/*
 * gfx_circle.c — card-neutral midpoint circle outline. See gfx.h.
 *
 * 8-way symmetry, every plotted point clipped to [0,gfx_width) x
 * [0,gfx_height) (int coords so a centre±radius that runs off an edge is
 * dropped, not wrapped — a uchar/unsigned cast of a negative coord would
 * alias back into a valid pixel).
 *
 * Split from the former gfx_draw.c so a line-only program skips the symmetry loop.
 */
#include "gfx.h"

static void gfx_plot_clip(int x, int y)
{
    if (x >= 0 && x < (int)gfx_width && y >= 0 && y < (int)gfx_height)
        gfx_plot((unsigned)x, (unsigned char)y);
}

void gfx_circle(unsigned xc, unsigned char yc, unsigned char r)
{
    int cx, cy = (int)yc;
    int x = 0, y = (int)r;
    int d = 1 - (int)r;
    /* Reject circles wholly to the right before narrowing an unsigned
     * centre to cc65's signed 16-bit int. Otherwise e.g. 65535 becomes -1
     * and its right-hand arc paints the left edge of the screen. Subtract
     * only after comparing, so neither unsigned subtraction nor addition
     * can wrap. Centres just beyond the edge still have visible arcs. */
    if (xc >= gfx_width && xc - gfx_width >= (unsigned)r) return;
    cx = (int)xc;
    while (x <= y) {
        gfx_plot_clip(cx + x, cy + y);
        gfx_plot_clip(cx - x, cy + y);
        gfx_plot_clip(cx + x, cy - y);
        gfx_plot_clip(cx - x, cy - y);
        gfx_plot_clip(cx + y, cy + x);
        gfx_plot_clip(cx - y, cy + x);
        gfx_plot_clip(cx + y, cy - x);
        gfx_plot_clip(cx - y, cy - x);
        if (d < 0) { d += (x << 1) + 3; }
        else       { d += 2 * (x - y) + 5; --y; }
        ++x;
    }
}
