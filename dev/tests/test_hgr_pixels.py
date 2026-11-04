#!/usr/bin/env python3
"""C and native HGR point kernels: every visible coordinate and both pages."""
from pathlib import Path
import tempfile

from test_hgr import build, a2test, offset


def main():
    with tempfile.TemporaryDirectory(prefix='hgr-pixels-') as directory:
        work = Path(directory)
        source = work / 'pixels.c'
        source.write_text('''#include "hgr.h"
#include "hgr_internal.h"
void checkpoint(void);
int main(void) {
    unsigned x;
    unsigned char page, y;
    hgr_init();
    hgr_set_draw_page(1); hgr_clear(0xA5);
    hgr_set_draw_page(2); hgr_clear(0xDA);
    for (page=1; page<=2; ++page) {
        hgr_set_draw_page(page);
        for (y=0; y<192; ++y) for (x=0; x<280; ++x) hgr_plot(x,y);
        checkpoint();
        for (y=0; y<192; ++y) for (x=0; x<280; ++x)
            if (((x ^ y) & 7u) < 3u) hgr_unplot(x,y);
        checkpoint();
        for (y=0; y<192; ++y) for (x=0; x<280; ++x) {
            hgr_p_x=x; hgr_p_y=y; hgr_plot_asm();
        }
        checkpoint();
        for (y=0; y<192; ++y) for (x=0; x<280; ++x) {
            hgr_p_x=x; hgr_p_y=y; hgr_unplot_asm();
        }
        checkpoint();
        hgr_plot(280,0); hgr_unplot(280,0);
        hgr_plot(512,0); hgr_unplot(512,0);
        hgr_plot(65535,191); hgr_unplot(65535,191);
        hgr_plot(0,192); hgr_unplot(0,192);
        hgr_plot(279,255); hgr_unplot(279,255);
        checkpoint();
    }
    for (;;) {}
    return 0;
}
''')
        marker = work / 'marker.s'
        marker.write_text('.export _checkpoint, resume\n.code\n_checkpoint: nop\nresume: rts\n')
        disk = build(work, source, extra_sources=(marker,))
        labels = a2test.labels(work / 'test.lbl')
        steps = []
        for _ in range(10):
            steps += [labels.until('_checkpoint'), 'peek:2000:16384', labels.until('resume')]
        result = a2test.run(disk, steps)
        expected = bytearray([0xA5] * 8192 + [0xDA] * 8192)
        for index, actual in enumerate(result.dumps):
            page, stage = divmod(index, 5)
            for y in range(192):
                start = page * 8192 + offset(y)
                expected[start:start+40] = bytes([0x80 if stage >= 3 else 0xFF]) * 40
                if stage == 1:
                    for x in range(280):
                        if ((x ^ y) & 7) < 3:
                            expected[start+x//7] &= 255 ^ (1 << (x % 7))
            assert actual == expected, (page+1, stage, 'pixel, palette bit, hole or other page changed')
    print('HGR pixels: C/ASM drawing across all 280×192 coordinates on both pages;')
    print('off-screen calls, palette bits, holes and the other page preserved.')


if __name__ == '__main__':
    main()
