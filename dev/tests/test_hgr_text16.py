#!/usr/bin/env python3
"""Doubled HGR glyphs: every source byte, carrier, alignment and built-in glyph."""
import argparse
from pathlib import Path
import tempfile

from test_hgr import build, a2test, fonts, offset, pixel, text
from test_hgr_color import CARRIERS


def native_mask(image, x, y, rows):
    for row, bits in enumerate(rows):
        for bit in range(8):
            if bits & (1 << bit):
                for dy in range(2):
                    for dx in range(2):
                        pixel(image, x+2*bit+dx, y+2*row+dy, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-text16-') as directory:
        work = Path(directory)
        source = work / 'text16.c'
        source.write_text('''#include "hgr.h"
#include "hgr_internal.h"
void painted(void);
static unsigned char patterns[256];
static const unsigned char blank[8]={0};
static void background(unsigned char page) {
    hgr_set_draw_page(1); hgr_clear(0xA5);
    hgr_set_draw_page(2); hgr_clear(0x5A);
    hgr_set_draw_page(page);
}
static void glyph(unsigned x, unsigned char y, const unsigned char *bits) {
    hgr_g_col=(unsigned char)(x/7u); hgr_g_bit=(unsigned char)(x%7u);
    hgr_g_y=y; hgr_g_glyph=bits; hgr_blit_glyph();
}
int main(void) {
    unsigned i;
    unsigned char page,color,phase,parity,c;
    char s[2];
    s[1]=0;
    for (i=0; i<256; ++i) patterns[i]=(unsigned char)i;
    hgr_init(); hgr_build_tables();
    for (page=1; page<=2; ++page)
      for (color=0; color<5; ++color)
        for (phase=0; phase<7; ++phase)
          for (parity=0; parity<2; ++parity) {
            background(page);
            if (!hgr_set_carrier(color)) {
                hgr_z_ce=127; hgr_z_co=127; hgr_z_hi=0;
            }
            for (c=0; c<32; ++c)
                glyph(14u+phase+parity*7u+(c%8u)*28u,(c/8u)*40u,patterns+c*8u);
            glyph(258u+phase,176,patterns+248);
            glyph(264,176,blank);
            painted();
            background(page);
            for (c=32; c<128; ++c) {
                s[0]=c;
                hgr_puts_color(7u+phase+parity*7u+((c-32u)%12u)*21u,
                               ((c-32u)/12u)*22u,s,color);
            }
            painted();
          }
    for (;;) {}
    return 0;
}
''')
        marker = work / 'marker.s'
        marker.write_text('.export _painted, resume\n.code\n_painted: nop\nresume: rts\n')
        disk = build(work, source, extra_sources=(marker,))
        labels = a2test.labels(work / 'test.lbl')
        steps = []
        for _ in range(2*5*7*2*2):
            steps += [labels.until('_painted'), 'peek:2000:16384', labels.until('resume')]
        result = a2test.run(disk, steps, iie=args.iie)
        font = bytes(fonts.glyphs(32, 127))
        frame = 0
        for page in range(2):
            for color in range(5):
                even, odd, high = CARRIERS.get(color, (127, 127, 0))
                for phase in range(7):
                    for parity in range(2):
                        for family in ('native', 'public'):
                            mask = bytearray(8192)
                            if family == 'native':
                                for c in range(32):
                                    native_mask(mask, 14+phase+parity*7+(c%8)*28,
                                                (c//8)*40, range(c*8, c*8+8))
                                native_mask(mask, 258+phase, 176, range(248, 256))
                            else:
                                for c in range(32, 128):
                                    text(mask, font, 7+phase+parity*7+((c-32)%12)*21,
                                         ((c-32)//12)*22, chr(c), 2)
                            pages = [bytearray([0xA5])*8192, bytearray([0x5A])*8192]
                            for y in range(192):
                                for col in range(40):
                                    address = offset(y)+col
                                    if mask[address]:
                                        pages[page][address] |= (mask[address] &
                                            (odd if col & 1 else even)) | high
                            assert result.dumps[frame] == pages[0]+pages[1], (
                                page+1, color, phase, parity, family)
                            frame += 1
    print(f'HGR 16x16: {frame} scenes, all 256 source row patterns and 96 built-in glyphs;')
    print('five carriers, seven phases, both parities/pages, blank rows, right/bottom edges and holes OK.')


if __name__ == '__main__':
    main()
