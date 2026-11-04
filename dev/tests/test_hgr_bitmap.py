#!/usr/bin/env python3
"""MSB-first HGR bitmaps: source/destination byte boundaries and clipping."""
import argparse
from pathlib import Path
import tempfile

from test_hgr import build, a2test, pixel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    boxes = [(28+phase, 63, width, 3, 0)
             for phase in range(7) for width in (1, 7, 8, 9, 14, 15, 16, 17)]
    boxes += [(x, 127, width, 3, 0)
              for x in (252, 255, 256, 272, 273, 279) for width in (1, 8, 16, 255)]
    boxes += [(0, 0, 255, 255, 0), (279, 191, 255, 255, 0),
              (0, 0, 0, 1, 0), (0, 0, 1, 0, 0), (280, 0, 8, 8, 0),
              (65535, 0, 8, 8, 0), (0, 192, 8, 8, 0), (0, 255, 8, 8, 0)]
    boxes += [(28+phase, 7, 16, 8, pattern)
              for phase in range(7) for pattern in (1, 2)]
    boxes += [(28+phase, 31, 16, 128, 3) for phase in range(7)]
    cases = [(*box, mode) for box in boxes for mode in range(3)]
    with tempfile.TemporaryDirectory(prefix='hgr-bitmap-') as directory:
        work = Path(directory)
        source = work / 'bitmap.c'
        source.write_text('''#include "hgr.h"
void painted(void);
static unsigned char data[6400];
static unsigned char all_bytes[256];
static const unsigned char empty[16]={0};
static const unsigned char solid[16]={255,255,255,255,255,255,255,255,
                                     255,255,255,255,255,255,255,255};
static const struct {unsigned x; unsigned char y,w,h,pattern;} cases[]={'''
                          + ','.join('{%du,%du,%du,%du,%du}' % box for box in boxes) + '''};
int main(void) {
    unsigned i, start;
    unsigned char page,mode;
    const unsigned char *bitmap;
    for (i=0; i<sizeof(data); ++i) data[i]=(unsigned char)((i*73u+19u)^(i>>3));
    for (i=0; i<256; ++i) all_bytes[i]=(unsigned char)i;
    hgr_init();
    for (page=1; page<=2; ++page) {
        for (i=0; i<sizeof(cases)/sizeof(cases[0]); ++i) {
          for (mode=0; mode<3; ++mode) {
            hgr_set_draw_page(1); hgr_clear(0xA5);
            hgr_set_draw_page(2); hgr_clear(0xDA);
            hgr_set_draw_page(page);
            start=(unsigned)mode*127u;
            bitmap=cases[i].pattern == 1 ? empty :
                   cases[i].pattern == 2 ? solid :
                   cases[i].pattern == 3 ? (const unsigned char *)all_bytes :
                   (const unsigned char *)(data+start);
            hgr_blit(cases[i].x,cases[i].y,cases[i].w,cases[i].h,bitmap,mode);
            painted();
          }
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
            for index, (x, y, width, height, pattern, mode) in enumerate(cases):
                pages = [bytearray([0xA5])*8192, bytearray([0xDA])*8192]
                stride = (width+7)//8
                for row in range(min(height, max(0, 192-y))):
                    for col in range(min(width, max(0, 280-x))):
                        address = (index % 3)*127 + row*stride + col//8
                        value = (0 if pattern == 1 else 255 if pattern == 2 else
                                 row*stride + col//8 if pattern == 3 else
                                 ((address*73+19) ^ (address >> 3)) & 255)
                        if value & (128 >> (col % 8)):
                            pixel(pages[page], x+col, y+row, mode != 1,
                                  mode='xor' if mode == 2 else 'set')
                assert result.dumps[frame] == pages[0]+pages[1], (
                    page+1, x, y, width, height, pattern, mode)
                frame += 1
    print(f'HGR bitmaps: {frame} SET/CLEAR/XOR cases, seven phases,')
    print('all 256 source bytes, source boundaries/stride, clipping, both pages, palette and holes OK.')


if __name__ == '__main__':
    main()
