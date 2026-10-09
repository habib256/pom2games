#!/usr/bin/env python3
"""Actual cc65 x2 conversion: pixel oracle, wide strides, guards and blits."""
from pathlib import Path
import tempfile
import test_hgr

SIZES = [(1, 128), (1, 255), (3, 16), (8, 8), (128, 1), (255, 2)]


def inflated(w, h, color):
    stride = w * 2
    out = bytearray(stride * h * 2)
    for row in range(h):
        for x in range(w * 7):
            if not (((row * w + x // 7) * 13 + 7) & (1 << (x % 7))):
                continue
            for side in (0, 1):
                if color != 1 and color not in ((2, 4) if side == 0 else (3, 5)):
                    continue
                px = x * 2 + side
                bits = (1 << (px % 7)) | (128 if color in (4, 5) else 0)
                for dy in (0, 1):
                    out[(row * 2 + dy) * stride + px // 7] |= bits
    return out


def check(work):
    entries = ','.join('{%du,%du}' % size for size in SIZES)
    source = work / 'x2.c'
    source.write_text('''#include "hgr.h"
#include "hgr_x2.h"
static unsigned char source[510];
unsigned char output[2042];
unsigned char scene;
static const struct {unsigned char w,h;} sizes[] = {''' + entries + '''};
int main(void) {
    unsigned i;
    unsigned char c, color;
    for (i=0; i<sizeof(source); ++i) source[i]=(unsigned char)(i*13u+7u);
    hgr_init();
    for (c=0; c<sizeof(sizes)/sizeof(sizes[0]); ++c) {
        for (color=0; color<6u; ++color) {
            for (i=0; i<sizeof(output); ++i) output[i]=0xA5u;
            hgr_inflate_x2(source,sizes[c].w,sizes[c].h,color,output+1);
            scene=c*6u+color;
            apple2_getkey();
        }
    }
    for (i=0; i<sizeof(output); ++i) output[i]=0xA5u;
    hgr_inflate_x2(source,0u,255u,1u,output+1);
    hgr_inflate_x2(source,255u,0u,1u,output+1);
    hgr_inflate_x2(source,255u,255u,1u,output+1);
    scene=36u; apple2_getkey();
    for (color=0; color<6u; ++color) {
        hgr_set_draw_page(1u); hgr_clear(42u);
        hgr_set_draw_page(2u); hgr_clear(42u);
        hgr_blit_x2(14u,180u,source,3u,16u,color,HGR_SET);
        scene=37u+color; apple2_getkey();
    }
    hgr_set_draw_page(2u); hgr_clear(42u);
    hgr_set_draw_page(1u);
    hgr_blit_x2(0u,0u,source,255u,255u,1u,HGR_SET);
    hgr_blit_x2(65535u,0u,source,3u,16u,1u,HGR_SET);
    hgr_blit_x2(0u,192u,source,3u,16u,1u,HGR_SET);
    scene=43u;
    for (;;) {}
    return 0;
}
''')
    disk = test_hgr.build(work, source)
    labels = test_hgr.a2test.labels(work / 'test.lbl', strip=True)
    steps = ['wait:1100']
    for scene in range(44):
        steps += [labels.peek('scene'),
                  labels.peek('output', 2042) if scene < 37 else 'peek:2000:16384']
        if scene < 43:
            steps += ['key: ', 'wait:60']
    data = test_hgr.a2test.run(disk, steps).data
    pos = 0
    for scene in range(44):
        assert data[pos] == scene, ('fixture did not finish', scene, data[pos])
        pos += 1
        size = 2042 if scene < 37 else 16384
        actual = data[pos:pos + size]
        pos += size
        if scene < 36:
            w, h = SIZES[scene // 6]
            pixels = inflated(w, h, scene % 6)
            expected = b'\xA5' + pixels + b'\xA5' * (2041 - len(pixels))
        elif scene == 36:
            expected = b'\xA5' * size
        else:
            expected = bytearray([42]) * size
            if scene < 43:
                pixels = inflated(3, 16, scene - 37)
                for row in range(12):
                    start = 8192 + test_hgr.offset(180 + row) + 2
                    expected[start:start + 6] = bytes(v | 42 for v in pixels[row * 6:row * 6 + 6])
        assert actual == expected, ('x2 pixels or guards', scene)
    assert pos == len(data)
    print('cc65 x2: 36 conversions, six colours, 510-byte strides, guards, invalid sizes and clipped page-2 blits OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='hgr-x2-') as tmp:
        check(Path(tmp))
