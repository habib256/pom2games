#!/usr/bin/env python3
"""Check every built-in 8x8 glyph at all seven HGR bit phases on both pages."""
import argparse
import tempfile
from pathlib import Path

from test_hgr import build, a2test, fonts, text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-glyphs-') as directory:
        work = Path(directory)
        source = work / 'glyphs.c'
        source.write_text('''#include "hgr.h"
#include "hgr_internal.h"
#include "apple2io.h"
void hgr_blit_glyph8(void);
static unsigned char patterns[256];
static const unsigned char blank[8]={0};
static void native(unsigned x, unsigned char y, const unsigned char *bits) {
    hgr_g_col=(unsigned char)(x/7u); hgr_g_bit=(unsigned char)(x%7u);
    hgr_g_y=y; hgr_g_glyph=bits; hgr_blit_glyph8();
}
int main(void) {
    unsigned i;
    unsigned char page, phase, c;
    char s[2];
    s[1] = 0;
    for (i=0; i<256; ++i) patterns[i]=(unsigned char)i;
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
    for (page=1; page<=2; ++page) {
        hgr_set_draw_page(page);
        for (phase=0; phase<7; ++phase) {
            hgr_clear(170);
            for (c=0; c<32; ++c)
                native(7u+phase+(c%16u)*14u,64u+(c/16u)*16u,patterns+c*8u);
            native(266u+phase,184,patterns+248);
            native(272,184,blank);
            *(volatile unsigned char *)0x1000 = 14+(page-1)*7+phase;
            apple2_getkey();
        }
    }
    for (;;) {}
    return 0;
}
''')
        disk = build(work, source)
        steps = ['wait:1100']
        for _ in range(28):
            steps += ['peek:1000:1', 'peek:2000:16384', 'key: ', 'wait:100']
        result = a2test.run(disk, steps, iie=args.iie)
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
        for scene in range(14, 28):
            assert result.dumps[scene * 2] == bytes([scene]), 'native glyph checkpoint'
            page, phase = divmod(scene-14, 7)
            pages[page] = bytearray([170]) * 8192
            for c in range(32):
                text(pages[page], bytes(range(256)), 7+phase+(c%16)*14,
                     64+(c//16)*16, chr(c+32), 1)
            text(pages[page], bytes(range(256)), 266+phase, 184, chr(63), 1)
            assert result.dumps[scene * 2 + 1] == pages[0] + pages[1], (
                'native row pattern, palette, holes or other page changed', page, phase)
    print('HGR glyphs: 96 characters, seven phases, both pages,')
    print('1,344 glyphs match the per-pixel oracle; palette and holes preserved.')
    print('Native 8x8: all 256 source row patterns, blank glyphs and right/bottom edges OK.')


if __name__ == '__main__':
    main()
