#!/usr/bin/env python3
"""dhgr_font.py: the 7-row proportional font of the DHGR interface (lot 4).

Glyphs are drawn in DHGR colour pixels (4 dots each, ~1.8 times wider than
tall on screen): 3 x 7 letters read like a normal upper-case font. Widths are
0 (space) to 5 pixels; the advance is the width + 1. Used by tools/genhud.py (compass
ribbon), tools/gen_summary_font.py (survival panels) and the tests.

    glyph(c)  -> (width, rows): rows[r] bit b = pixel b (left first)
    width(s)  -> pixels of the string s without the final gap
"""

_GLYPHS = {
    ' ': ['', '', '', '', '', '', ''],      # advance 1: words 2 pixels apart
    '!': ['X', 'X', 'X', 'X', 'X', '.', 'X'],
    '%': ['X.X', '..X', '..X', '.X.', 'X..', 'X..', 'X.X'],
    '+': ['...', '...', '.X.', 'XXX', '.X.', '...', '...'],
    ',': ['.', '.', '.', '.', '.', 'X', 'X'],
    '-': ['...', '...', '...', 'XXX', '...', '...', '...'],
    '.': ['.', '.', '.', '.', '.', '.', 'X'],
    '/': ['..X', '..X', '.X.', '.X.', '.X.', 'X..', 'X..'],
    '0': ['XXX', 'X.X', 'X.X', 'X.X', 'X.X', 'X.X', 'XXX'],
    '1': ['.X', 'XX', '.X', '.X', '.X', '.X', '.X'],
    '2': ['XX.', '..X', '..X', '.X.', 'X..', 'X..', 'XXX'],
    '3': ['XX.', '..X', '..X', '.X.', '..X', '..X', 'XX.'],
    '4': ['X.X', 'X.X', 'X.X', 'XXX', '..X', '..X', '..X'],
    '5': ['XXX', 'X..', 'X..', 'XX.', '..X', '..X', 'XX.'],
    '6': ['.XX', 'X..', 'X..', 'XX.', 'X.X', 'X.X', '.X.'],
    '7': ['XXX', '..X', '..X', '.X.', '.X.', '.X.', '.X.'],
    '8': ['.X.', 'X.X', 'X.X', '.X.', 'X.X', 'X.X', '.X.'],
    '9': ['.X.', 'X.X', 'X.X', '.XX', '..X', '..X', 'XX.'],
    ':': ['.', '.', 'X', '.', '.', 'X', '.'],
    '=': ['...', '...', 'XXX', '...', 'XXX', '...', '...'],
    '?': ['XX.', '..X', '..X', '.X.', '.X.', '...', '.X.'],
    'A': ['.X.', 'X.X', 'X.X', 'XXX', 'X.X', 'X.X', 'X.X'],
    'B': ['XX.', 'X.X', 'X.X', 'XX.', 'X.X', 'X.X', 'XX.'],
    'C': ['.XX', 'X..', 'X..', 'X..', 'X..', 'X..', '.XX'],
    'D': ['XX.', 'X.X', 'X.X', 'X.X', 'X.X', 'X.X', 'XX.'],
    'E': ['XXX', 'X..', 'X..', 'XX.', 'X..', 'X..', 'XXX'],
    'F': ['XXX', 'X..', 'X..', 'XX.', 'X..', 'X..', 'X..'],
    'G': ['.XX', 'X..', 'X..', 'X.X', 'X.X', 'X.X', '.XX'],
    'H': ['X.X', 'X.X', 'X.X', 'XXX', 'X.X', 'X.X', 'X.X'],
    'I': ['X', 'X', 'X', 'X', 'X', 'X', 'X'],
    'J': ['..X', '..X', '..X', '..X', '..X', 'X.X', '.X.'],
    'K': ['X..X', 'X.X.', 'XX..', 'X...', 'XX..', 'X.X.', 'X..X'],
    'L': ['X..', 'X..', 'X..', 'X..', 'X..', 'X..', 'XXX'],
    'M': ['X...X', 'XX.XX', 'X.X.X', 'X.X.X', 'X...X', 'X...X', 'X...X'],
    'N': ['X..X', 'XX.X', 'XX.X', 'X.XX', 'X.XX', 'X..X', 'X..X'],
    'O': ['.X.', 'X.X', 'X.X', 'X.X', 'X.X', 'X.X', '.X.'],
    'P': ['XX.', 'X.X', 'X.X', 'XX.', 'X..', 'X..', 'X..'],
    'Q': ['.X.', 'X.X', 'X.X', 'X.X', 'X.X', 'XX.', '.XX'],
    'R': ['XX.', 'X.X', 'X.X', 'XX.', 'XX.', 'X.X', 'X.X'],
    'S': ['.XX', 'X..', 'X..', '.X.', '..X', '..X', 'XX.'],
    'T': ['XXX', '.X.', '.X.', '.X.', '.X.', '.X.', '.X.'],
    'U': ['X.X', 'X.X', 'X.X', 'X.X', 'X.X', 'X.X', 'XXX'],
    'V': ['X.X', 'X.X', 'X.X', 'X.X', 'X.X', '.X.', '.X.'],
    'W': ['X...X', 'X...X', 'X...X', 'X.X.X', 'X.X.X', 'XX.XX', 'X...X'],
    'X': ['X.X', 'X.X', 'X.X', '.X.', 'X.X', 'X.X', 'X.X'],
    'Y': ['X.X', 'X.X', 'X.X', '.X.', '.X.', '.X.', '.X.'],
    'Z': ['XXX', '..X', '..X', '.X.', 'X..', 'X..', 'XXX'],
}
FIRST, LAST = 32, 90            # glyph table of the 6502 font: ' ' .. 'Z'
ROWS = 7


def glyph(c):
    """(width, rows) of character c; unknown characters are a blank space."""
    art = _GLYPHS.get(c, _GLYPHS[' '])
    width = len(art[0])
    rows = tuple(sum(1 << b for b, p in enumerate(line) if p == 'X') for line in art)
    return width, rows


def width(text):
    """Pixels of `text`: widths + one-pixel gaps, without the final gap."""
    return sum(glyph(c)[0] + 1 for c in text) - 1 if text else 0


def table():
    """7 bytes per glyph FIRST..LAST: row bits 0..4, width in bits 5..7 of row 0."""
    out = bytearray()
    for code in range(FIRST, LAST + 1):
        w, rows = glyph(chr(code))
        assert 0 <= w <= 5 and all(r < 32 for r in rows)
        out += bytes((rows[0] | w << 5,) + rows[1:])
    return bytes(out)
