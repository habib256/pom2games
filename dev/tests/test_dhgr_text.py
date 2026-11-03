#!/usr/bin/env python3
"""Standard 8x8 DHGR text (dhgr_puts) against a per-pixel oracle: every
color phase, both pages and banks, lower case and unknown glyphs, the
stops at the right edge and at the bottom."""
import sys
import tempfile
from pathlib import Path

from test_dhgr import DEV, PATTERNS, color_pixel
from test_hgr import build, a2test
sys.path.insert(0, str(DEV / 'tools'))
import fonts

# (string, x, y): the seven phases (page 2 one pixel further, the other
# byte parity), then the edge cases.
CALLS = [('AZ?~ 0', 17 * phase, 10 + 8 * phase) for phase in range(7)]
CALLS += [('X', 132, 100), ('X', 133, 110), ('Y', 0, 184), ('Y', 0, 185),
          ('ab', 60, 150), ('\\x01Z\\x7fQ', 20, 170), ('WRAP', 120, 160)]


def model(banks, x, y, text):
    """What dhgr_puts(text, x, y) leaves on a page: opaque white glyphs."""
    for ch in text:
        if x >= 133 or y >= 185:
            return
        code = ord(ch)
        if code < 32 or code >= 128:
            code = ord('?')
        for row_index, row in enumerate(fonts.glyph(chr(code))):
            for bit in range(8):
                color_pixel(banks, x + bit, y + row_index, 15 if row & (1 << bit) else 0)
        x += 8


def main():
    with tempfile.TemporaryDirectory(prefix='dhgr-text-') as directory:
        work = Path(directory)
        source = work / 'text.c'
        calls = ''.join('        dhgr_puts("%s",%d+page-1,%d);\n' % call for call in CALLS)
        source.write_text('''#include "dhgr.h"
int main(void) {
    unsigned char page;
    if (!dhgr_init()) return 1;
    for (page=1; page<=2; ++page) {
        dhgr_draw_page(page);
        dhgr_clear(page==1 ? 6 : 9);
''' + calls + '''    }
    *(volatile unsigned char *)0x1000 = 1;
    for (;;) {}
    return 0;
}
''')
        disk = build(work, source)
        result = a2test.run(disk, ['wait:9000', 'peek:1000:1', 'peek:C013:2',
                                  'peek:2000:16384', 'poke:C003:0',
                                  'peek:2000:16384', 'poke:C002:0'], iie=True)
        assert result.dumps[0] == b'\x01', 'text fixture did not finish'
        assert not any(value & 128 for value in result.dumps[1]), 'bank state leaked'
        expected_main = b''
        expected_aux = b''
        for page, color in enumerate((6, 9)):
            banks = [bytearray(PATTERNS[color][1 - bank::2]) * 4096 for bank in (0, 1)]
            for text, x, y in CALLS:
                model(banks, x + page, y, text.encode().decode('unicode_escape'))
            expected_main += banks[0]
            expected_aux += banks[1]
        for name, actual, expected in (('main', result.dumps[2], expected_main),
                                       ('aux', result.dumps[3], expected_aux)):
            if actual != expected:
                index = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
                raise AssertionError('%s-bank text mismatch at $%04X: %02X expected %02X'
                                     % (name, 0x2000 + index, actual[index], expected[index]))
    print('DHGR text: seven phases on both parities, both pages and banks, lower case,')
    print('unknown glyphs, the right-edge and bottom stops OK.')


if __name__ == '__main__':
    main()
