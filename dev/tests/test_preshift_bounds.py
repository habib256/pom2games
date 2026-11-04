#!/usr/bin/env python3
"""Pre-shift sprite strides/heights: both XOR APIs against a clipped oracle."""
from pathlib import Path
import tempfile
import test_hgr

DEV = test_hgr.DEV
CASES = [(7,255), (14,254), (140,240), (256,220), (279,217),
         (279,216), (1,255), (9,255), (10,255), (12,255),
         (256,255), (279,255), (14,255)]
CASES = [(x, stride, 1, 191) for x, stride in CASES]
CASES += [(28 + phase, 3, 16, 7) for phase in range(7)]
CASES += [(28 + phase, 2, 255, 0) for phase in range(7)]
CASES += [(273, 3, 255, 189), (279, 3, 255, 191),
          (28, 0, 255, 0), (28, 3, 0, 0), (280, 3, 16, 0), (0, 3, 16, 192)]


def check(work):
    source = work / 'preshift_bounds.c'
    entries = ','.join('{%du,%du,%du,%du}' % case for case in CASES)
    source.write_text('''#include "hgr.h"
static unsigned char bank[7u*3u*255u];
static hgr_sprite_t sprite;
static const struct {unsigned x; unsigned char stride,h,y;} cases[] = {''' + entries + '''};
int main(void) {
    unsigned i;
    unsigned char c;
    for (i=0; i<sizeof(bank); ++i) bank[i]=(unsigned char)((i*13u+1u)&0x7Fu);
    sprite.bits=bank;
    hgr_init();
    for (c=0; c<sizeof(cases)/sizeof(cases[0]); ++c) {
        sprite.stride=cases[c].stride;
        sprite.h=cases[c].h;
        hgr_set_draw_page(1u); hgr_clear(42u);
        hgr_sprite(cases[c].x,cases[c].y,&sprite,HGR_XOR);
        hgr_set_draw_page(2u); hgr_clear(42u);
        hgr_sprite_xor(cases[c].x,cases[c].y,&sprite);
        *(volatile unsigned char *)0x1000=c;
        apple2_getkey();
    }
    for (;;) {}
    return 0;
}
''')
    disk = test_hgr.build(work, source)
    steps = ['wait:1100']
    for _ in CASES:
        steps += ['peek:1000:1', 'peek:2000:16384', 'key: ', 'wait:60']
    result = test_hgr.a2test.run(disk, steps)
    for index, (x, stride, height, y) in enumerate(CASES):
        assert result.dumps[2*index] == bytes([index]), 'fixture did not reach scene'
        expected = bytearray([42]*8192)
        col, phase = divmod(x,7)
        for row in range(min(height, 192-y)):
            for j in range(min(stride, 40-col)):
                expected[test_hgr.offset(y+row)+col+j] ^= ((phase*stride*height+row*stride+j)*13+1)&127
        actual = result.dumps[2*index+1]
        assert actual[:8192] == expected, ('general XOR', CASES[index])
        assert actual[8192:] == expected, ('fast XOR', CASES[index])
    print('Pre-shift sprites: strides/heights through 255, all phases, x>=256,')
    print('clipping, empty/off-screen sprites and both pages match the oracle.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='preshift-bounds-') as tmp:
        check(Path(tmp))
