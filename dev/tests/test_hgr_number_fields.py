#!/usr/bin/env python3
"""Erased and right-aligned unsigned fields against a pixel/string oracle."""
import argparse
from pathlib import Path
import tempfile
from test_hgr import build, a2test, fonts, rect, text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    cases = [(x, y, value, width) for width in (*range(16), 255)
             for value in (0, 9, 10, 99, 100, 999, 1000, 65535)
             for x in (0, 6) for y in (0, 176)]
    cases += [(x, y, 65535, 5) for x in (250, 279, 280, 65535)
              for y in (176, 184, 191, 192, 255)]
    cases += [(x, 176, value, width) for x in (250, 279)
              for value in (0, 42) for width in (5, 14)]
    with tempfile.TemporaryDirectory(prefix='hgr-fields-') as directory:
        work = Path(directory)
        source = work/'fields.c'
        source.write_text('''#include "hgr.h"
void painted(void);
static const struct {unsigned x; unsigned char y; unsigned value;
    unsigned char width;} cases[]={'''
            + ','.join('{%du,%d,%du,%d}' % case for case in cases) + '''};
int main(void) {
    unsigned i;
    unsigned char page;
    for(page=1;page<=2;++page) {
      for(i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
        hgr_set_draw_page(1);hgr_clear(0xA5);
        hgr_set_draw_page(2);hgr_clear(0xDA);
        hgr_set_draw_page(page);
        hgr_putu_field(cases[i].x,cases[i].y,cases[i].value,cases[i].width);
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
            for x, y, value, width in cases:
                pages = [bytearray([0xA5])*8192, bytearray([0xDA])*8192]
                if width and x < 280 and y < 192:
                    width = min(width, 14)
                    rect(pages[page], x, y, x+(width-1)*18+15, y+15, set=False)
                    digits = str(value)
                    origin = x+max(0, width-len(digits))*18
                    text(pages[page], font, origin, y, digits, 2)
                assert result.dumps[frame] == pages[0]+pages[1], (page, x, y, value, width)
                frame += 1
    print(f'HGR unsigned fields: {frame} scenes, all widths 1..14, zero/clamped widths,')
    print('right alignment, overflow, invalid/clipped origins, both pages and palette/holes OK.')


if __name__ == '__main__':
    main()
