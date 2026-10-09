/* Boundary regressions with a bounds-checking framebuffer backend. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gfx.h"
const unsigned gfx_width = 560;
const unsigned char gfx_height = 192;
static unsigned char pixels[192][560];
static unsigned char reference[192][560];
void gfx_plot(unsigned x, unsigned char y)
{
    assert(x < gfx_width && y < gfx_height);
    pixels[y][x] = 1;
}
void gfx_hline(unsigned a, unsigned b, unsigned char y)
{
    unsigned x, lo = a < b ? a : b, hi = a > b ? a : b;
    for (x = lo; x <= hi; ++x) gfx_plot(x, y);
}
void gfx_vline(unsigned x, unsigned char a, unsigned char b)
{
    unsigned y, lo = a < b ? a : b, hi = a > b ? a : b;
    for (y = lo; y <= hi; ++y) gfx_plot(x, (unsigned char)y);
}
int main(int argc, char **argv)
{
    unsigned dx, dy, reverse, x, y, r;
    (void)argc;
    if (strcmp(argv[1], "circle") == 0) {
        for (r = 0; r <= 255; ++r) {
            gfx_circle(0, 0, (unsigned char)r);
            gfx_circle(279, 191, (unsigned char)r);
            gfx_circle(559, 95, (unsigned char)r);
        }
    } else {
        static const unsigned ends[] = {559, 1022, 1024, 32767, 32768, 65535};
        unsigned i;
        for (i = 0; i < sizeof(ends) / sizeof(ends[0]); ++i) {
            memset(pixels, 0, sizeof(pixels));
            gfx_ellipse(10, 20, ends[i], 100);
            memcpy(reference, pixels, sizeof(pixels));
            memset(pixels, 0, sizeof(pixels));
            gfx_ellipse(ends[i], 100, 10, 20);
            assert(memcmp(reference, pixels, sizeof(pixels)) == 0);
            assert(pixels[60][10]);
        }
        for (dx = 0; dx <= 8; ++dx) for (dy = 0; dy <= 8; ++dy)
        for (reverse = 0; reverse < 2; ++reverse) {
            memset(pixels, 0, sizeof(pixels));
            if (reverse) gfx_ellipse(10+dx, (unsigned char)(10+dy), 10, 10);
            else gfx_ellipse(10, 10, 10+dx, (unsigned char)(10+dy));
            for (y = 0; y < 192; ++y) for (x = 0; x < 560; ++x)
                if (pixels[y][x]) assert(x >= 10 && x <= 10+dx && y >= 10 && y <= 10+dy);
            if (dx == 0) for (y = 10; y <= 10+dy; ++y) assert(pixels[y][10]);
            if (dy == 0) for (x = 10; x <= 10+dx; ++x) assert(pixels[10][x]);
        }
    }
    puts("geometry boundaries OK");
    return 0;
}
