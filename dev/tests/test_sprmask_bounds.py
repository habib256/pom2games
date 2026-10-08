#!/usr/bin/env python3
"""Exercise clipping in all four ASM masked-sprite kernels directly."""
from pathlib import Path
import tempfile
import test_hgr

CASES = [(7, 255), (14, 254), (140, 240), (256, 220)] + [(x, 255) for x in range(273, 280)]


def check(work):
    source = work / 'sprmask_bounds.c'
    entries = ','.join('{%du,%du}' % case for case in CASES)
    source.write_text('''#include "hgr.h"
#include "hgr_internal.h"
static unsigned char data[7u*255u], mask[7u*255u], under[255u];
static hgr_mspr_t sprite;
static const struct {unsigned x; unsigned char stride;} cases[] = {''' + entries + '''};
int main(void) {
    unsigned i;
    unsigned char page, mode, c, scene=0;
    for (i=0; i<sizeof(data); ++i) {
        mask[i]=(unsigned char)(0x80u|((i*7u+3u)&127u));
        data[i]=(unsigned char)(((i*13u+1u)&127u)&~mask[i]);
    }
    sprite.data=data; sprite.mask=mask; sprite.h=1u;
    hgr_init();
    for (page=1; page<=2; ++page) {
        for (mode=0; mode<4; ++mode) {
            for (c=0; c<sizeof(cases)/sizeof(cases[0]); ++c) {
                hgr_set_draw_page(1u); hgr_clear(42u);
                hgr_set_draw_page(2u); hgr_clear(42u);
                hgr_set_draw_page(page);
                for (i=0; i<sizeof(under); ++i) under[i]=0xCCu;
                sprite.stride=cases[c].stride;
                hgr_ms_x=cases[c].x; hgr_ms_y=191u;
                hgr_ms_spr=&sprite; hgr_ms_under=under;
                switch (mode) {
                    case 0: hgr_ms_run(); break;
                    case 1: hgr_ms_save_run(); break;
                    case 2: hgr_ms_restore_run(); break;
                    case 3: hgr_msu_run(); break;
                }
                for (i=0; i<sizeof(under); ++i)
                    ((volatile unsigned char *)0x1001)[i]=under[i];
                *(volatile unsigned char *)0x1000=scene++;
                apple2_getkey();
            }
        }
    }
    for (;;) {}
    return 0;
}
''')
    disk = test_hgr.build(work, source)
    scenes = [(page, mode, x, stride) for page in (1, 2) for mode in range(4) for x, stride in CASES]
    steps = ['wait:1100']
    for _ in scenes:
        steps += ['peek:1000:256', 'peek:2000:16384', 'key: ', 'wait:60']
    result = test_hgr.a2test.run(disk, steps)
    for index, (page, mode, x, stride) in enumerate(scenes):
        state, actual = result.dumps[2*index:2*index+2]
        assert state[0] == index, 'fixture did not reach scene'
        expected = bytearray([42]*16384)
        saved = bytearray([0xCC]*255)
        col, phase = divmod(x, 7)
        for j in range(40-col):
            src = phase*stride+j
            mask = 0x80 | ((src*7+3)&127)
            bits = ((src*13+1)&127) & (255^mask)
            addr = (page-1)*8192+test_hgr.offset(191)+col+j
            if mode in (0, 3): expected[addr] = (42&mask)|bits
            if mode == 2: expected[addr] = 0xCC
            if mode in (1, 3): saved[j] = 42
        if actual != expected:
            addr = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
            raise AssertionError(f'page {page}, kernel {mode}, x={x}, stride={stride}: '
                                 f'${0x2000+addr:04X}={actual[addr]:02X}, expected {expected[addr]:02X}')
        assert state[1:] == saved, ('save-under wrote beyond clipped width', page, mode, x, stride)
    print(f'Masked ASM sprites: {len(scenes)} scenes, four kernels, large strides, seven phases, both pages and save-under bounds OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='sprmask-bounds-') as tmp:
        check(Path(tmp))
