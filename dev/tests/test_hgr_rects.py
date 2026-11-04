#!/usr/bin/env python3
"""Pixel rectangles: edge masks, interior pairs, clipping and native modes."""
import argparse
from pathlib import Path
import tempfile

from test_hgr import build, a2test, rect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    # Every left/right bit combination, within one byte or across edges.
    boxes = [(14+phase, 40, width, 3) for phase in range(7) for width in range(1, 8)]
    boxes += [(14+left, 63, 8+right-left, 3) for left in range(7) for right in range(7)]
    boxes += [(x, 127, width, 3) for x in (252, 255, 256, 273, 279)
              for width in (1, 7, 14, 255)]
    boxes += [(0, 0, 255, 192), (1, 7, 255, 255), (0, 191, 255, 255),
              (279, 191, 255, 255), (0, 0, 0, 1), (0, 0, 1, 0),
              (280, 0, 1, 1), (65535, 0, 255, 255),
              (0, 192, 1, 1), (0, 255, 255, 255)]
    cases = [(x, y, w, h, mode, 0) for x, y, w, h in boxes for mode in (0, 1)]
    # Native calls include all 1..40 byte widths and noncanonical true modes.
    cases += [(0, 64, 7*columns, 2, mode, 1)
              for columns in range(1, 41) for mode in (0, 1, 255)]
    with tempfile.TemporaryDirectory(prefix='hgr-rects-') as directory:
        work = Path(directory)
        source = work / 'rects.c'
        source.write_text('''#include "hgr.h"
#include "hgr_internal.h"
void painted(void);
static const struct {unsigned x; unsigned char y; unsigned w;
    unsigned char h,mode,native;} cases[]={'''
                          + ','.join('{%d,%d,%d,%d,%d,%d}' % case for case in cases) + '''};
int main(void) {
    unsigned i;
    unsigned char page;
    hgr_build_tables();
    for (page=1; page<=2; ++page) {
        for (i=0; i<sizeof(cases)/sizeof(cases[0]); ++i) {
            hgr_set_draw_page(1); hgr_clear(0xA5);
            hgr_set_draw_page(2); hgr_clear(0xDA);
            hgr_set_draw_page(page);
            if (cases[i].native) {
                hgr_r_x=cases[i].x;
                hgr_r_xr=cases[i].x+cases[i].w-1;
                hgr_r_y0=cases[i].y;
                hgr_r_rows=cases[i].h;
                hgr_r_mode=cases[i].mode;
                hgr_pixrect_asm();
            } else if (cases[i].mode) {
                hgr_fill_pixrect(cases[i].x,cases[i].y,cases[i].w,cases[i].h);
            } else {
                hgr_clear_pixrect(cases[i].x,cases[i].y,cases[i].w,cases[i].h);
            }
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
            for x, y, width, height, mode, native in cases:
                pages = [bytearray([0xA5])*8192, bytearray([0xDA])*8192]
                if width and height and x < 280 and y < 192:
                    rect(pages[page], x, y, x+width-1, y+height-1, set=bool(mode))
                assert result.dumps[frame] == pages[0]+pages[1], (
                    page+1, x, y, width, height, mode, native)
                frame += 1
    print(f'HGR rectangles: {frame} C/native fills and clears; all edge phases,')
    print('1..40 byte widths, clipping, palette bits and screen holes OK on both pages.')


if __name__ == '__main__':
    main()
