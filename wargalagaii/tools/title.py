#!/usr/bin/env python3
"""WARGALAGA II title picture (lot 9) -> an 8 KB HGR page.

The top of the title screen: WARGALAGA in big letters (the game's font, a
font dot = 2 cells x 3 rows, orange / white / blue bands), II below it
(green / white / violet), a line of text, a row of the game's small aliens
in their four tints, a few stars. Rows PANEL_TOP..191 stay black: front.s
writes the menu, the high scores and the help there.

Cells are two dots wide, as in tools/sprites.py; each byte's palette bit is
set by what it holds (a byte never mixes the two groups: asserted).

    tools/title.py OUT.hgr          the page (front.s gets it LZ4FH-packed)
    tools/title.py --png OUT.png    a preview
"""
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites

fonts = sprites.fonts
PANEL_TOP = 88                       # front.s: PANEL_LINE * 8
SUBTITLE = 'APPLE //E AND //C, 128K'


class Page:
    def __init__(self):
        self.dots = [[0] * 280 for _ in range(192)]
        self.pal = [[None] * 40 for _ in range(192)]

    def cell(self, y, x, kind, palette):
        """Cell x (0..139) of row y: kind L, R or W in palette 0/1."""
        for half, on in enumerate(sprites.dots(kind)):
            if on:
                self.dot(y, 2 * x + half, palette)

    def dot(self, y, x, palette):
        b = x // 7
        assert self.pal[y][b] in (None, palette), (y, x, 'one palette a byte')
        self.pal[y][b] = palette
        self.dots[y][x] = 1

    def bytes(self):
        page = bytearray(8192)
        for y in range(192):
            base = (y & 7) * 0x400 + (y >> 3 & 7) * 0x80 + (y >> 6) * 0x28
            for b in range(40):
                v = sum(self.dots[y][7 * b + i] << i for i in range(7))
                page[base + b] = v | (self.pal[y][b] or 0) << 7 if v else 0
        return bytes(page)


def big_text(page, text, x0, y0, bands):
    """A font dot = 2 cells x 3 rows; bands: (kind, palette) of each third."""
    for n, ch in enumerate(text):
        for r, row in enumerate(fonts.glyph(ch)):
            kind, palette = bands[min(2, r * 3 // 7)]
            for c in range(7):
                if row >> c & 1:
                    for dy in range(3):
                        for dx in range(2):
                            page.cell(y0 + 3 * r + dy, x0 + 14 * n + 2 * c + dx, kind, palette)


def small_text(page, text, y0):
    """The font as the game draws it (white, palette 0), centred on bytes."""
    b0 = (40 - len(text)) // 2
    for n, ch in enumerate(text):
        for r, row in enumerate(fonts.glyph(ch)):
            for c in range(7):
                if row >> c & 1:
                    page.dot(y0 + r, 7 * (b0 + n) + c, 0)


def build():
    page = Page()
    orange, blue, green, violet = ('R', 1), ('L', 1), ('R', 0), ('L', 0)
    white1, white0 = ('W', 1), ('W', 0)
    word = 'WARGALAGA'
    big_text(page, word, (140 - 14 * len(word)) // 2, 4, (orange, white1, blue))
    big_text(page, 'II', (140 - 28) // 2, 32, (green, white0, violet))
    small_text(page, SUBTITLE, 60)
    for j in range(9):                       # 2-byte aligned: one palette each
        design, tint = j % len(sprites.SMALL), j % 4
        frame = sprites.SMALL[design][1 + j % 2]
        for r, row in enumerate(sprites.tinted(sprites.two_tone(frame), tint)):
            for c, kind in enumerate(row):
                if kind != '.':
                    page.cell(74 + r, 7 + 14 * j + c, kind, sprites.TINTS[tint][0])
    rng = random.Random(1983)
    for _ in range(40):                      # stars on bytes left black
        y, x = rng.randrange(0, PANEL_TOP - 4), rng.randrange(0, 280)
        if all(not page.dots[yy][7 * (x // 7) + i] for yy in range(max(0, y - 1), y + 2) for i in range(7)):
            page.dot(y, x, rng.randrange(2))
    assert not any(any(row) for row in page.dots[PANEL_TOP:]), 'the panel stays black'
    return page


def png(page, path, scale=3):
    import apple2img
    rgb = {(0, 0): (0xC0, 0x40, 0xFF), (0, 1): (0x40, 0xE0, 0x40),
           (1, 0): (0x40, 0x90, 0xFF), (1, 1): (0xFF, 0x80, 0x20)}
    lines = []
    for y in range(192):
        line = []
        for x in range(280):
            d = page.dots[y]
            lit = [k for k in (x - 1, x) if 0 <= k < 280 and d[k]]
            if not lit:                      # a colour dot covers 2 dots
                p = (0, 0, 0)
            elif len(lit) == 2 or (d[x] and x < 279 and d[x + 1]):
                p = (255, 255, 255)
            else:
                p = rgb[(page.pal[y][lit[0] // 7] or 0, lit[0] & 1)]
            line += [p] * scale
        lines += [line] * scale
    apple2img.png_write(path, lines)


def main():
    page = build()
    if sys.argv[1:2] == ['--png']:
        png(page, sys.argv[2])
    else:
        Path(sys.argv[1]).write_bytes(page.bytes())


if __name__ == '__main__':
    main()
