#!/usr/bin/env python3
"""dhgr_ui.py: model and reader of the survival panels of the DHGR band (lot 4).

src/summary.s draws four fields in the 7-row font of tools/dhgr_font.py:
left panel (byte groups 0..6, colour pixels 0..48) and right panel (groups
13..19, pixels 91..139), each with an upper line (rows 0..7) and a lower
line (rows 8..15). A line is 8 rows: glyph rows 0..6, row 7 background.
Black panels; ink per character; a warning character is white on a deep
red strip that covers its cell (gap included) and the pixel before it.

    render(fields)        -> 16 rows x 140 colours (panel pixels only)
    panels(page)          -> the four field texts read back from a DHGR page
    styles(page, field)   -> [(char, ink, background)] of a field
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dhgr_palette as P  # noqa: E402
from dhgr_font import glyph, FIRST, LAST  # noqa: E402

BLACK, WARN = P.BLACK, P.MAGENTA            # deep red strip behind warnings
CALM, LABEL, GOOD, FAIR, HINT, WHITE = P.GREY2, P.GREY2, P.AQUA, P.YELLOW, P.LIGHT_BLUE, P.WHITE
PANEL_X = (0, 91)                           # first pixel of the left / right panel
WIDTH = 49
FIELDS = ((0, 0), (0, 8), (1, 0), (1, 8))   # (panel, first row)


def line(chars):
    """8 rows x 49 colours of one field: chars = [(char, ink, background)]."""
    rows = [[BLACK] * WIDTH for _ in range(8)]
    x = 0
    for ch, ink, bg in chars:
        w, bits = glyph(ch)
        if bg != BLACK:
            for r in range(8):
                for px in range(max(x - 1, 0), min(x + w + 1, WIDTH)):
                    rows[r][px] = bg
        for r in range(7):
            for b in range(w):
                if bits[r] >> b & 1 and x + b < WIDTH:
                    rows[r][x + b] = ink
        x += w + 1
    return rows


def render(fields):
    """16 rows x 140: the four fields, each a list of (char, ink, background)."""
    page = [[BLACK] * 140 for _ in range(16)]
    for (panel, y), chars in zip(FIELDS, fields):
        for r, row in enumerate(line(chars)):
            page[y + r][PANEL_X[panel]:PANEL_X[panel] + WIDTH] = row
    return page


_GLYPHS = sorted(((chr(c),) + glyph(chr(c)) for c in range(FIRST, LAST + 1) if chr(c) != ' '),
                 key=lambda g: -g[1])


def _read(rows):
    """Characters of an 8 x 49 field (rows of colours); ink = not background."""
    bgs = {BLACK, WARN}
    ink = [[c not in bgs for c in row[:7]] for row in zip(*rows)]   # per column
    out, x = [], 0
    while x < WIDTH:
        if not any(any(col) for col in ink[x:]):
            break
        if not any(ink[x]):
            out.append((' ', x))
            x += 1
            continue
        for ch, w, bits in _GLYPHS:
            if x + w > WIDTH:
                continue
            if all(ink[x + b][r] == bool(bits[r] >> b & 1) for b in range(w) for r in range(7)) and (
                    x + w >= WIDTH or not any(ink[x + w])):
                out.append((ch, x))
                x += w + 1
                break
        else:
            out.append(('?', x))
            x += 1
    # A space is one blank column between two glyph gaps: collapse the runs
    # of blank columns produced above into the spaces the font would draw.
    text = ''.join(ch for ch, _ in out)
    return text, out


def field_rows(page, field):
    panel, y = FIELDS[field]
    x0 = PANEL_X[panel]
    return [page[y + r][x0:x0 + WIDTH] for r in range(8)]


def panels(page):
    """The four field texts of a decoded DHGR page (rows of colours)."""
    return tuple(_read(field_rows(page, f))[0].rstrip() for f in range(4))


def styles(page, field):
    """[(char, ink colour, background colour)] of a field."""
    rows = field_rows(page, field)
    _, chars = _read(rows)
    out = []
    for ch, x in chars:
        w, bits = glyph(ch)
        inks = {rows[r][x + b] for r in range(7) for b in range(w) if bits[r] >> b & 1}
        bg = rows[7][min(x, WIDTH - 1)]
        out.append((ch, inks.pop() if len(inks) == 1 else None, bg))
    return out
