#!/usr/bin/env python3
"""Signed HGR formatting against decimal strings and a pixel oracle."""
import argparse
from pathlib import Path
import tempfile
from test_hgr import build, a2test, fonts, text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    positive = (0, 1, 9, 10, 99, 100, 999, 1000, 9999, 10000, 32767)
    values = positive + tuple(-n for n in positive if n) + (-32768,)
    cases = [(x, y, n) for n in values for x in (0, 6, 250) for y in (0, 176)]
    cases += [(0, 177, -32768), (0, 255, -32768), (280, 0, -32768),
              (65535, 0, -32768)]
    with tempfile.TemporaryDirectory(prefix='hgr-signed-') as directory:
        work = Path(directory)
        source = work/'signed.c'
        source.write_text('''#include "hgr.h"
void painted(void);
static const struct {unsigned x; unsigned char y; int value;} cases[]={'''
            + ','.join('{%du,%d,%d}' % case for case in cases) + '''};
int main(void) {
    unsigned i;
    unsigned char page;
    for(page=1;page<=2;++page) {
      for(i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
        hgr_set_draw_page(1);hgr_clear(0xA5);
        hgr_set_draw_page(2);hgr_clear(0xDA);
        hgr_set_draw_page(page);
        hgr_puti(cases[i].x,cases[i].y,cases[i].value);
        painted();
      }
    }
    for(;;){}
    return 0;
}
''')
        marker = work/'marker.s'
        marker.write_text('.export _painted, resume\n.code\n_painted: nop\nresume: rts\n')
        disk = build(work, source, extra_sources=(marker,))
        labels = a2test.labels(work/'test.lbl')
        steps = []
        for _ in range(2*len(cases)):
            steps += [labels.until('_painted'), 'peek:2000:16384', labels.until('resume')]
        result = a2test.run(disk, steps, iie=args.iie)
        font = bytes(fonts.glyphs(32, 127))
        frame = 0
        for page in range(2):
            for x, y, value in cases:
                pages = [bytearray([0xA5])*8192, bytearray([0xDA])*8192]
                text(pages[page], font, x, y, str(value), 2)
                assert result.dumps[frame] == pages[0]+pages[1], (page, x, y, value)
                frame += 1
    print(f'HGR signed: {frame} scenes, signs/zero, decimal boundaries, -32768/32767,')
    print('clipping, both pages, palette and untouched holes OK.')


if __name__ == '__main__':
    main()
