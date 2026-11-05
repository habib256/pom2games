#!/usr/bin/env python3
"""Compare colored span edges/interiors against a per-pixel oracle on IIe."""
import tempfile
from pathlib import Path

from test_dhgr import PATTERNS, color_pixel, pixel
from test_hgr import build, a2test


def check_rows():
    """Keep bank setup live across tall spans, including empty interiors."""
    cases = [(0, 0, 560, 192), (559, 0, 65535, 255)]
    for x in range(14):
        for width in (1, 6, 41):
            cases.append((x, (x*13+width) % 192, width, 255))
    with tempfile.TemporaryDirectory(prefix='dhgr-span-rows-') as directory:
        work = Path(directory)
        source = work / 'rows.c'
        source.write_text('''#include "dhgr_internal.h"
void painted(void);
unsigned char irq_after;
static const unsigned xs[]={'''+','.join(str(c[0]) for c in cases)+'''};
static const unsigned widths[]={'''+','.join(str(c[2]) for c in cases)+'''};
static const unsigned char ys[]={'''+','.join(str(c[1]) for c in cases)+'''};
static const unsigned char heights[]={'''+','.join(str(c[3]) for c in cases)+'''};
int main(void) {
    unsigned char page, color, i;
    if (!dhgr_init()) return 1;
    for (page=1; page<=2; ++page) for (color=0; color<16; ++color) {
        dhgr_draw_page(1); dhgr_clear(6);
        dhgr_draw_page(2); dhgr_clear(9);
        dhgr_draw_page(page); dhgr_show_page(3-page);
        if (color & 1) { asm("sei"); } else { asm("cli"); }
        for (i=0; i<sizeof(ys); ++i) {
            dhgr_prepare_pattern((color+i)&15);
            dhgr_bit_rect(xs[i],ys[i],widths[i],heights[i]);
        }
        asm("php"); asm("pla"); asm("sta _irq_after");
        painted(); asm("cli");
    }
    for (;;) {} return 0;
}
''')
        marker = work / 'marker.s'
        marker.write_text('.export _painted, resume\n.code\n_painted: nop\nresume: rts\n')
        disk = build(work, source, extra_sources=(marker,))
        labels = a2test.labels(work / 'test.lbl')
        steps = []
        for _ in range(32):
            steps += [labels.until('_painted'), labels.peek('_irq_after', 1),
                      'peek:C013:2', 'peek:C018:8', 'peek:2000:16384',
                      'poke:C003:0', 'peek:2000:16384', 'poke:C002:0',
                      labels.until('resume')]
        result = a2test.run(disk, steps, iie=True)
        for frame in range(32):
            page, color = divmod(frame, 16)
            pages = [[bytearray(PATTERNS[initial][1-bank::2])*4096
                      for bank in (0, 1)] for initial in (6, 9)]
            for index, (x, y, width, height) in enumerate(cases):
                pattern = PATTERNS[(color+index)&15]
                for row in range(y, min(y+height, 192)):
                    for bit in range(x, min(x+width, 560)):
                        pixel(pages[page], bit, row,
                              (pattern[(bit//7)&3] >> (bit%7))&1)
            irq, state, flags, main, aux = result.dumps[frame*5:frame*5+5]
            assert irq[0]&4 == (4 if color&1 else 0), ('IRQ mask', page, color)
            assert not any(v&128 for v in state) and not flags[0]&128, 'bank state leaked'
            assert bool(flags[4]&128) == (page == 0), 'display page changed'
            assert main == pages[0][0]+pages[1][0], ('main', page, color)
            assert aux == pages[0][1]+pages[1][1], ('aux', page, color)
    print('DHGR spans: 1,408 tall rectangles, every bit/bank phase, full-height and')
    print('clipped rows, empty interiors, both pages/banks, holes/display and IRQ masks OK.')


def main():
    # Single byte, adjacent edges, long interiors of every phase, full width
    # and right clipping. Each case gets its own scanline on both pages.
    spans = [(0, 1), (1, 1), (1, 4), (2, 20), (3, 30),
             (0, 140), (139, 255), (7, 2), (6, 2), (8, 1)]
    with tempfile.TemporaryDirectory(prefix='dhgr-spans-') as directory:
        work = Path(directory)
        source = work / 'spans.c'
        source.write_text('''#include "dhgr.h"
static const unsigned char starts[] = {'''
                          + ','.join(str(x) for x, _ in spans) + '''};
static const unsigned char widths[] = {'''
                          + ','.join(str(w) for _, w in spans) + '''};
int main(void) {
    unsigned char page, color, i;
    if (!dhgr_init()) return 1;
    for (page=1; page<=2; ++page) {
        dhgr_draw_page(page);
        dhgr_clear(15);
        for (color=0; color<16; ++color)
            for (i=0; i<10; ++i)
                dhgr_fill_rect(starts[i], color*10+i, widths[i], 1, color);
    }
    *(volatile unsigned char *)0x1000 = 1;
    for (;;) {}
    return 0;
}
''')
        disk = build(work, source)
        result = a2test.run(disk, ['wait:6000', 'peek:1000:1', 'peek:C013:2',
                                  'peek:2000:16384', 'poke:C003:0',
                                  'peek:2000:16384', 'poke:C002:0'], iie=True)
        assert result.dumps[0] == b'\x01', 'span fixture did not finish'
        assert not any(value & 128 for value in result.dumps[1]), 'bank state leaked'
        banks = [bytearray([127]) * 8192, bytearray([127]) * 8192]
        for color in range(16):
            for i, (x, width) in enumerate(spans):
                for pixel in range(x, min(x + width, 140)):
                    color_pixel(banks, pixel, color * 10 + i, color)
        assert result.dumps[2] == banks[0] * 2, 'main-bank span/page mismatch'
        assert result.dumps[3] == banks[1] * 2, 'aux-bank span/page mismatch'
    print('DHGR spans: 320 colored rows, 16 colors, both pages/banks,')
    print('single/adjacent edges, all interior phases, full width and clipping OK.')
    check_rows()


if __name__ == '__main__':
    main()
