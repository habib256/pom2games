#!/usr/bin/env python3
"""Byte rectangles: every column/width pair, fill bytes and clipped edges."""
import argparse
from pathlib import Path
import tempfile

from test_hgr import build, a2test, offset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    cases = [((col*19+width*7) % 192, width % 3+1, col, width,
              (col*47+width*11) & 255)
             for col in range(40) for width in range(1, 41-col)]
    cases += [(value % 192, 1, 0, value % 40+1, value) for value in range(256)]
    cases += [(y, 255, col, 255, 0x81) for y in (0, 7, 63, 127, 191)
              for col in (0, 1, 38, 39)]
    cases += [(0, 0, 0, 40, 0xFF), (0, 192, 0, 0, 0xFF),
              (192, 1, 0, 40, 0xFF), (255, 255, 0, 40, 0xFF),
              (0, 192, 40, 1, 0xFF), (0, 192, 255, 255, 0xFF)]
    with tempfile.TemporaryDirectory(prefix='hgr-byte-rects-') as directory:
        work = Path(directory)
        source = work / 'byte_rects.c'
        source.write_text('''#include "hgr.h"
void painted(void);
static const struct { unsigned char y,rows,col,width,value; } cases[]={'''
                          + ','.join('{%d,%d,%d,%d,%d}' % case for case in cases) + '''};
int main(void) {
    unsigned i;
    unsigned char page;
    for (page=1; page<=2; ++page) {
        for (i=0; i<sizeof(cases)/sizeof(cases[0]); ++i) {
            hgr_set_draw_page(1); hgr_clear(0xA5);
            hgr_set_draw_page(2); hgr_clear(0x5A);
            hgr_set_draw_page(page);
            hgr_fill_rect(cases[i].y,cases[i].rows,cases[i].col,
                          cases[i].width,cases[i].value);
            painted();
        }
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
        for _ in range(2*len(cases)):
            steps += [labels.until('_painted'), 'peek:2000:16384', labels.until('resume')]
        result = a2test.run(disk, steps, iie=args.iie)
        frame = 0
        for page in range(2):
            for y, rows, col, width, value in cases:
                pages = [bytearray([0xA5])*8192, bytearray([0x5A])*8192]
                for row in range(y, min(y+rows, 192)):
                    for column in range(col, min(col+width, 40)):
                        pages[page][offset(row)+column] = value
                assert result.dumps[frame] == pages[0]+pages[1], (
                    page+1, y, rows, col, width, value)
                frame += 1
    print(f'HGR byte rectangles: {frame} fills, all 820 column/width pairs,')
    print('all 256 bytes, clipping and empty inputs; palette, holes and both pages OK.')


if __name__ == '__main__':
    main()
