#!/usr/bin/env python3
"""Compare colored span edges/interiors against a per-pixel oracle on IIe."""
import tempfile
from pathlib import Path

from test_dhgr import color_pixel
from test_hgr import build, a2test


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


if __name__ == '__main__':
    main()
