#!/usr/bin/env python3
"""Large pre-shift sprite strides: fast XOR must match clipped general XOR."""
from pathlib import Path
import tempfile
import test_hgr

DEV = test_hgr.DEV
CASES = [(7,255), (14,254), (140,240), (256,220), (279,217),
         (279,216), (1,255), (9,255), (10,255), (12,255),
         (256,255), (279,255), (14,255)]


def check(work):
    source = work / 'preshift_bounds.c'
    entries = ','.join('{%du,%du}' % case for case in CASES)
    source.write_text('''#include "hgr.h"
static unsigned char bank[7u*255u];
static hgr_sprite_t sprite;
static const struct {unsigned x; unsigned char stride;} cases[] = {''' + entries + '''};
int main(void) {
    unsigned i;
    unsigned char c;
    for (i=0; i<sizeof(bank); ++i) bank[i]=(unsigned char)((i*13u+1u)&0x7Fu);
    sprite.bits=bank; sprite.h=1u;
    hgr_init();
    for (c=0; c<sizeof(cases)/sizeof(cases[0]); ++c) {
        sprite.stride=cases[c].stride;
        hgr_set_draw_page(1u); hgr_clear(42u);
        hgr_sprite(cases[c].x,191u,&sprite,HGR_XOR);
        hgr_set_draw_page(2u); hgr_clear(42u);
        hgr_sprite_xor(cases[c].x,191u,&sprite);
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
    for index, (x, stride) in enumerate(CASES):
        assert result.dumps[2*index] == bytes([index]), 'fixture did not reach scene'
        expected = bytearray([42]*8192)
        col, phase = divmod(x,7)
        for j in range(40-col):
            expected[test_hgr.offset(191)+col+j] ^= ((phase*stride+j)*13+1)&127
        actual = result.dumps[2*index+1]
        assert actual[:8192] == expected, ('general XOR',x,stride)
        assert actual[8192:] == expected, ('fast XOR wrote outside clipped row',x,stride)
    print('Pre-shift sprites: strides 216..255, all phases, x>=256, bottom edge and both pages OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='preshift-bounds-') as tmp:
        check(Path(tmp))
