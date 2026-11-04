#!/usr/bin/env python3
"""Carrier ABI and byte-granular HGR recoloring, including tinted text."""
import argparse
from pathlib import Path
import tempfile

from test_hgr import build, a2test, fonts, offset, text

COLORS = (0, 1, 2, 3, 4, 5, 255)
CARRIERS = {1: (0x55, 0x2A, 0), 2: (0x2A, 0x55, 0),
            3: (0x2A, 0x55, 128), 4: (0x55, 0x2A, 128)}
BOXES = [(0, 0, 1, 1), (7, 7, 1, 1), (0, 8, 7, 3), (7, 15, 7, 3),
         (0, 22, 14, 2), (7, 30, 14, 2), (6, 40, 2, 3), (13, 63, 2, 3),
         (14, 64, 21, 3), (21, 127, 21, 3), (252, 128, 28, 3),
         (255, 135, 255, 3), (256, 160, 255, 3), (279, 191, 255, 255),
         (0, 176, 255, 255), (0, 0, 0, 1), (0, 0, 1, 0),
         (280, 0, 1, 1), (65535, 0, 255, 255), (0, 192, 1, 1), (0, 255, 255, 255)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    boxes = [(*box, color) for color in COLORS for box in BOXES]
    letters = [(14+phase, 100, color) for color in COLORS for phase in range(7)]
    with tempfile.TemporaryDirectory(prefix='hgr-color-') as directory:
        work = Path(directory)
        source = work / 'color.c'
        source.write_text('''#include "hgr.h"
#include "hgr_internal.h"
void selected(void); void painted(void);
unsigned char records[256][4];
static const struct {unsigned x; unsigned char y,w,h,c;} boxes[]={'''
                          + ','.join('{%d,%d,%d,%d,%d}' % box for box in boxes) + '''};
static const struct {unsigned x; unsigned char y,c;} letters[]={'''
                          + ','.join('{%d,%d,%d}' % letter for letter in letters) + '''};
static void background(unsigned char page) {
    hgr_set_draw_page(1); hgr_clear(0xA5);
    hgr_set_draw_page(2); hgr_clear(0x5A);
    hgr_set_draw_page(page);
}
int main(void) {
    unsigned color;
    unsigned char page,i;
    for (color=0; color<256; ++color) {
        hgr_z_ce=0x96; hgr_z_co=0x69; hgr_z_hi=0xC3;
        records[color][0]=hgr_set_carrier((unsigned char)color);
        records[color][1]=hgr_z_ce;
        records[color][2]=hgr_z_co;
        records[color][3]=hgr_z_hi;
    }
    selected();
    for (page=1; page<=2; ++page) {
        for (i=0; i<sizeof(boxes)/sizeof(boxes[0]); ++i) {
            background(page);
            hgr_colorize(boxes[i].x,boxes[i].y,boxes[i].w,boxes[i].h,boxes[i].c);
            painted();
        }
        for (i=0; i<sizeof(letters)/sizeof(letters[0]); ++i) {
            background(page);
            hgr_puts_color(letters[i].x,letters[i].y,"A",letters[i].c);
            painted();
        }
    }
    for (;;) {}
    return 0;
}
''')
        marker = work / 'marker.s'
        marker.write_text('.export _selected, _painted, resume\n.code\n'
                          '_selected: rts\n_painted: nop\nresume: rts\n')
        disk = build(work, source, extra_sources=(marker,))
        labels = a2test.labels(work / 'test.lbl')
        steps = [labels.until('_selected'), labels.peek('_records', 1024)]
        for _ in range(2*(len(boxes)+len(letters))):
            steps += [labels.until('_painted'), 'peek:2000:16384', labels.until('resume')]
        result = a2test.run(disk, steps, iie=args.iie)
        expected = b''.join(bytes((1, *CARRIERS[color])) if color in CARRIERS
                            else bytes((0, 0x96, 0x69, 0xC3)) for color in range(256))
        assert result.dumps[0] == expected, 'carrier return value/parameters/invalid input'
        font = bytes(fonts.glyphs(32, 127))
        frame = 1
        for page in range(2):
            for x, y, width, height, color in boxes:
                pages = [bytearray([0xA5])*8192, bytearray([0x5A])*8192]
                if color in CARRIERS and width and height and x < 280 and y < 192:
                    even, odd, high = CARRIERS[color]
                    for row in range(y, min(y+height, 192)):
                        for col in range(x//7, min(x+width-1, 279)//7+1):
                            addr = offset(row)+col
                            pages[page][addr] = (pages[page][addr] & (odd if col & 1 else even)) | high
                assert result.dumps[frame] == pages[0]+pages[1], ('rectangle', page+1, x, y, width, height, color)
                frame += 1
            for x, y, color in letters:
                pages = [bytearray([0xA5])*8192, bytearray([0x5A])*8192]
                glyph = bytearray(8192)
                text(glyph, font, x, y, 'A', 2)
                even, odd, high = CARRIERS.get(color, (127, 127, 0))
                for row in range(y, y+16):
                    for col in range(40):
                        addr = offset(row)+col
                        if glyph[addr]:
                            pages[page][addr] |= (glyph[addr] & (odd if col & 1 else even)) | high
                assert result.dumps[frame] == pages[0]+pages[1], ('text', page+1, x, color)
                frame += 1
    print('HGR color: all 256 selectors, invalid-input preservation;')
    print('294 rectangles and 98 tinted/white glyphs, both parities/pages, clipping, palette and holes OK.')


if __name__ == '__main__':
    main()
