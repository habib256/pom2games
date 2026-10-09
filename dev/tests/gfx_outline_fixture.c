/* Each outline must visit every visible pixel exactly once. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "gfx.h"
const unsigned gfx_width = 560;
const unsigned char gfx_height = 192;
static unsigned char pixels[192][560], expected[192][560];
void gfx_plot(unsigned x, unsigned char y)
{
    assert(x < gfx_width && y < gfx_height);
    assert(pixels[y][x] == 0); /* Also pins the result for a toggling backend. */
    pixels[y][x] = 1;
}
void gfx_hline(unsigned a, unsigned b, unsigned char y)
{
    unsigned x, lo = a < b ? a : b, hi = a > b ? a : b;
    if (lo >= gfx_width || y >= gfx_height) return;
    if (hi >= gfx_width) hi = gfx_width - 1;
    for (x = lo; x <= hi; ++x) gfx_plot(x, y);
}
void gfx_vline(unsigned x, unsigned char a, unsigned char b)
{
    unsigned y, lo = a < b ? a : b, hi = a > b ? a : b;
    if (x >= gfx_width || lo >= gfx_height) return;
    if (hi >= gfx_height) hi = gfx_height - 1;
    for (y = lo; y <= hi; ++y) gfx_plot(x, (unsigned char)y);
}
static void mark(int x, int y)
{
    if (x >= 0 && x < 560 && y >= 0 && y < 192) expected[y][x] = 1;
}
static void circle(unsigned cx, unsigned cy, unsigned r)
{
    int x = (int)r, y = 0, error = 1 - (int)r;
    int xc = (int)cx, yc = (int)cy;
    memset(expected, 0, sizeof(expected));
    memset(pixels, 0, sizeof(pixels));
    do {
        mark(xc+x, yc+y); mark(xc-x, yc+y);
        mark(xc+x, yc-y); mark(xc-x, yc-y);
        mark(xc+y, yc+x); mark(xc-y, yc+x);
        mark(xc+y, yc-x); mark(xc-y, yc-x);
        ++y;
        if (error < 0) error += 2*y + 1;
        else { --x; error += 2*(y-x) + 1; }
    } while (y <= x);
    gfx_circle(cx, (unsigned char)cy, (unsigned char)r);
    assert(memcmp(pixels, expected, sizeof(pixels)) == 0);
}
int main(void)
{
    static const unsigned centres[][2] = {
        {0,0}, {279,191}, {559,95}, {560,192}, {65535,255}, {5,255}, {280,100}
    };
    static const unsigned xs[] = {0,1,559,560,65535};
    static const unsigned ys[] = {0,1,191,192,255};
    unsigned c, r, a, b, d, e, x, y, lo, hi, top, bottom;
    for (c=0; c<sizeof(centres)/sizeof(centres[0]); ++c)
        for (r=0; r<=255; ++r) circle(centres[c][0], centres[c][1], r);
    for (a=0; a<5; ++a) for (b=0; b<5; ++b)
    for (d=0; d<5; ++d) for (e=0; e<5; ++e) {
        lo = xs[a] < xs[b] ? xs[a] : xs[b];
        hi = xs[a] > xs[b] ? xs[a] : xs[b];
        top = ys[d] < ys[e] ? ys[d] : ys[e];
        bottom = ys[d] > ys[e] ? ys[d] : ys[e];
        memset(pixels, 0, sizeof(pixels));
        gfx_rect(xs[a], (unsigned char)ys[d], xs[b], (unsigned char)ys[e]);
        for (y=0; y<192; ++y) for (x=0; x<560; ++x)
            assert(pixels[y][x] == (x>=lo && x<=hi && y>=top && y<=bottom &&
                   (x==lo || x==hi || y==top || y==bottom)));
    }
    puts("GFX outlines: 1792 circles and 625 rectangles match their pixels, without duplicate writes.");
    return 0;
}
