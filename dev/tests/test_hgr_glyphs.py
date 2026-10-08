#!/usr/bin/env python3
"""Check every built-in 8x8 glyph at all seven HGR bit phases on both pages."""
import tempfile
from pathlib import Path

from test_hgr import build, a2test, fonts, text


def main():
    with tempfile.TemporaryDirectory(prefix='hgr-glyphs-') as directory:
        work = Path(directory)
        source = work / 'glyphs.c'
        source.write_text('''#include "hgr.h"
#include "apple2io.h"
int main(void) {
    unsigned char page, phase, c;
    char s[2];
    s[1] = 0;
    hgr_set_draw_page(1); hgr_clear(42);
    hgr_set_draw_page(2); hgr_clear(42);
    for (page=1; page<=2; ++page) {
        hgr_set_draw_page(page);
        for (phase=0; phase<7; ++phase) {
            hgr_clear(170);
            for (c=32; c<128; ++c) {
                s[0] = c;
                hgr_puts8((unsigned)((c-32)%24)*11+phase,
                          ((c-32)/24)*9, s);
            }
            *(volatile unsigned char *)0x1000 = (page-1)*7+phase;
            apple2_getkey();
        }
    }
    for (;;) {}
    return 0;
}
''')
        disk = build(work, source)
        steps = ['wait:1100']
        for _ in range(14):
            steps += ['peek:1000:1', 'peek:2000:16384', 'key: ', 'wait:100']
        result = a2test.run(disk, steps)
        font = bytes(fonts.glyphs(0x20, 0x7F))
        pages = [bytearray([42]) * 8192, bytearray([42]) * 8192]
        for scene in range(14):
            assert result.dumps[scene * 2] == bytes([scene]), 'glyph fixture checkpoint'
            page, phase = divmod(scene, 7)
            pages[page] = bytearray([170]) * 8192
            for c in range(32, 128):
                text(pages[page], font, (c-32) % 24 * 11 + phase,
                     (c-32) // 24 * 9, chr(c), 1)
            assert result.dumps[scene * 2 + 1] == pages[0] + pages[1], (
                'glyph pixels, palette, screen holes or other page changed', page, phase)
    print('HGR glyphs: 96 characters, seven phases, both pages,')
    print('1,344 glyphs match the per-pixel oracle; palette and holes preserved.')


if __name__ == '__main__':
    main()
