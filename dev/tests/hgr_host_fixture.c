/* Regression checks for the host x2 converter and bounded blit wrapper. */
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "hgr_host.h"

static unsigned calls;
static unsigned char drawn_w, drawn_h;
void hgr_blit7(unsigned x, unsigned char y, unsigned char w,
               unsigned char h, const unsigned char *data, unsigned char mode)
{
    (void)x; (void)y; (void)mode;
    assert(data != NULL);
    drawn_w=w; drawn_h=h; ++calls;
}

static void inflate(unsigned char w, unsigned char h, unsigned char color)
{
    unsigned width=(unsigned)w*7u, stride=(unsigned)w*2u;
    unsigned size=stride*(unsigned)h*2u, row, pixel;
    unsigned char *source=malloc((unsigned)w*h+1u);
    unsigned char *actual=malloc(size+2u), *expected=calloc(size+2u,1);
    assert(source && actual && expected);
    memset(source,0x7F,(unsigned)w*h+1u);
    memset(actual,0xA5,size+2u);
    expected[0]=expected[size+1]=0xA5;
    for(row=0;row<(unsigned)h*2u;++row) {
        for(pixel=0;pixel<width*2u;++pixel) {
            unsigned char lit = color==HGR_X2_WHITE ||
                (pixel%2u==0u && (color==HGR_X2_VIOLET || color==HGR_X2_BLUE)) ||
                (pixel%2u==1u && (color==HGR_X2_GREEN || color==HGR_X2_ORANGE));
            if(lit) expected[1u+row*stride+pixel/7u] |=
                (1u<<(pixel%7u)) | ((color==HGR_X2_BLUE || color==HGR_X2_ORANGE)?128u:0u);
        }
    }
    hgr_inflate_x2(source,w,h,color,actual+1);
    assert(memcmp(actual,expected,size+2u)==0);
    free(source); free(actual); free(expected);
}

int main(void)
{
    static const unsigned char widths[]={0,1,3,18,19,36,64,127,128,129,255};
    static const unsigned char heights[]={0,1,2,128,255};
    unsigned wi, hi, color, w, h;
    static unsigned char source[65025];
    for(wi=0;wi<sizeof widths;++wi)
        for(hi=0;hi<sizeof heights;++hi)
            for(color=0;color<=HGR_X2_ORANGE;++color)
                inflate(widths[wi],heights[hi],color);
    for(w=0;w<256u;++w) for(h=0;h<256u;++h) {
        unsigned expected = w && h && w*h<=HGR_X2_MAX_BYTES/4u;
        calls=0;
        hgr_blit_x2(0,0,source,w,h,HGR_X2_WHITE,0);
        assert(calls==expected);
        if(expected) assert(drawn_w==w*2u && drawn_h==h*2u);
    }
    puts("HGR host x2: full byte-width/height range, pixel colours, canaries and scratch cap OK");
    return 0;
}
