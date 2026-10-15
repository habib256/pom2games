#!/usr/bin/env python3
"""topo_palette.py: colour roles and byte tables of the DHGR TOPO sheet (lot 4).

Everything the 6502 needs besides the resident map is a byte table built at
display time from the map header (base altitude +10, snow level +11, highest
level + 1 at +21, timberline +27). Colour numbers are the LORES numbers of
tools/dhgr_palette.py; a pair (a, b) is a checkerboard dither, a where
(x + row) is even, b where it is odd.

Hypsometric ramp below the snow line, low to high:
    green, green/yellow, yellow, yellow/orange, orange, orange/brown,
    brown, brown/grey, grey, grey/white            then white (snow).
Contours every 400 ft (four levels): brown on the light tints, black on
brown/grey, light blue on snow. Index contours (every 2000 ft above sea
level, header base included) are bold (both sides of the crossing): black
on land, grey on snow. Open water dark blue, water touching land (banks,
whole rivers) medium blue. Woods: dark green on three pixels in four below
the timberline, the tint shows through a staggered window.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dhgr_palette as P  # noqa: E402

BLACK, WHITE = P.BLACK, P.WHITE
WATER = P.DARK_BLUE             # open water away from the bank
SHORE = P.MEDIUM_BLUE           # water pixel touching land: lighter rim, whole rivers
WOODS = P.DARK_GREEN
STRIP = P.BLACK                 # margin background (x 0..13 and 126..139)
INK = P.WHITE                   # north arrow, scale labels

# Ramp entries below the snow line, low to high; the snow tint is separate.
RAMP = (P.GREEN, (P.GREEN, P.YELLOW), P.YELLOW, (P.YELLOW, P.ORANGE), P.ORANGE,
        (P.ORANGE, P.BROWN), P.BROWN, (P.BROWN, P.GREY1), P.GREY1, (P.GREY1, P.WHITE))
SNOW = P.WHITE
# Contour colours by ramp entry (normal, index); last entry: snow.
LINE = (P.BROWN,) * 6 + (P.BLACK,) * 4 + (P.LIGHT_BLUE,)
INDEX = (P.BLACK,) * 10 + (P.GREY1,)

# Markers: letter -> (box colour, letter colour); drawn R, H, then C on top.
MARKERS = {'C': (P.MAGENTA, P.WHITE), 'H': (P.BLACK, P.YELLOW), 'R': (P.PURPLE, P.WHITE),
           'P': (P.WHITE, P.DARK_BLUE)}   # the player: an arrow A0..A7 (N, NE .. NW)

# 3 x 5 glyphs, one byte per row, bit 2 = left pixel (22 glyphs, 110 bytes).
GLYPHS = {
    'C': (7, 4, 4, 4, 7), 'H': (5, 5, 7, 5, 5), 'R': (6, 5, 6, 5, 5), 'N': (5, 7, 7, 7, 5),
    '0': (7, 5, 5, 5, 7), '1': (2, 6, 2, 2, 7), '2': (7, 1, 7, 4, 7), '3': (7, 1, 3, 1, 7),
    '4': (5, 5, 7, 1, 1), '5': (7, 4, 7, 1, 7), '6': (7, 4, 7, 5, 7), '7': (7, 1, 1, 2, 2),
    '8': (7, 5, 7, 5, 7), '9': (7, 5, 7, 1, 7),
    'A0': (2, 7, 2, 2, 2), 'A1': (3, 1, 2, 4, 0), 'A2': (4, 6, 7, 6, 4), 'A3': (0, 4, 2, 1, 3),
    'A4': (2, 2, 2, 7, 2), 'A5': (0, 1, 2, 4, 6), 'A6': (1, 3, 7, 3, 1), 'A7': (6, 4, 2, 1, 0),
}

# Codes of the 6502 row buffers: K = band (0..31) | K_WOODS, or K_WATER.
K_WOODS = 0x20
K_WATER = 0x40


def header(data):
    """(base, snow, top band, timber) from the map header, with legacy defaults."""
    base = data[10] or 24
    snow = data[11] or 48
    top = (data[21] - 1) if data[21] else max(v & 0x7F for v in data[64:64 + 9408])
    timber = data[27] or 110
    return base, snow, top // 4, timber


def ramp_index(band, snow):
    """Ramp entry of a band; len(RAMP) means the snow tint."""
    sb = (snow + 3) // 4        # first band whose lowest level is snow
    if band >= sb:
        return len(RAMP)
    return min(len(RAMP) - 1, band * len(RAMP) // sb)


def tint(band, snow):
    i = ramp_index(band, snow)
    return SNOW if i == len(RAMP) else RAMP[i]


def woods_dot(x, row):
    """Woods colour on three pixels in four; the tint shows through a staggered
    window (period 2 in x, 4 in rows), so forests are dark green masses that
    keep a speckle of their elevation tint."""
    return not (x % 2 == (row >> 1) % 2 and row % 2 == 0)


def pick(entry, parity):
    """Colour of a solid colour or (even, odd) pair at (x + row) & 1 = parity."""
    if isinstance(entry, tuple):
        return entry[parity]
    return entry


def is_index(band, base):
    """Level 4 * band is an index contour: a multiple of 2000 ft above sea level."""
    return (4 * band + base) % 20 == 0


def index_count(band, base):
    """Index levels 4k with 1 <= k <= band: two bands are separated by an index
    contour iff their counts differ (the crossings between them are 4k, lo < k <= hi)."""
    return sum(is_index(k, base) for k in range(1, band + 1))


def wooded(band, base, timber):
    """Woods are shown where the band's lowest level is under the timberline."""
    return 4 * band + base < timber


def tables(data):
    """Byte tables built at display time.

    fill{r}{p}[K]  65 bytes x 8: colour of a plain pixel of code K on a row with
                   row & 3 = r, in a column with x & 1 = p (tint dither
                   (x + row) & 1, woods window woods_dot(x, row))
    mark[K]        65: normal contour colour of K's band; mark[K_WATER] = SHORE
                   (a water pixel "marked" by a land neighbour is a rim)
    indexk[K]      64: bold contour colour of K's band
    idxk[K]        64: index_count(band): index crossing iff idxk differ
    """
    base, snow, _top, timber = header(data)
    out = {}
    fill = [[bytearray(65), bytearray(65)] for _ in range(4)]
    mark, indexk, idxk = bytearray(65), bytearray(64), bytearray(64)
    for k in range(64):
        b = k & 31
        i = ramp_index(b, snow)
        mark[k], indexk[k], idxk[k] = LINE[i], INDEX[i], index_count(b, base)
        entry = SNOW if i == len(RAMP) else RAMP[i]
        for r in range(4):
            for p in (0, 1):
                c = pick(entry, (p + r) & 1)
                if k & K_WOODS and wooded(b, base, timber) and woods_dot(p, r):
                    c = WOODS
                fill[r][p][k] = c
    for r in range(4):
        for p in (0, 1):
            fill[r][p][K_WATER] = WATER
            out[f'fill{r}{p}'] = bytes(fill[r][p])
    mark[K_WATER] = SHORE
    out.update(mark=bytes(mark), indexk=bytes(indexk), idxk=bytes(idxk))
    return out


PACK = {'T0': lambda r: r, 'T1a': lambda r: (r & 7) << 4, 'T1b': lambda r: r >> 3,
        'T2': lambda r: r << 1, 'T3a': lambda r: (r & 3) << 5, 'T3b': lambda r: r >> 2,
        'T4': lambda r: r << 2, 'T5a': lambda r: (r & 1) << 6, 'T5b': lambda r: r >> 1,
        'T6': lambda r: r << 3}


def pack_tables():
    """Ten 16-byte tables. A group of seven colours c0..c6 is four bytes
    (aux even, main even, aux odd, main odd), r = rot(c):
      b0 = r0 | (r1 & 7) << 4                 = T0[c0] | T1a[c1]
      b1 = r1 >> 3 | r2 << 1 | (r3 & 3) << 5  = T1b[c1] | T2[c2] | T3a[c3]
      b2 = r3 >> 2 | r4 << 2 | (r5 & 1) << 6  = T3b[c3] | T4[c4] | T5a[c5]
      b3 = r5 >> 1 | r6 << 3                  = T5b[c5] | T6[c6]
    """
    return {k: bytes(fn(P.rot(c)) & 0x7F for c in range(16)) for k, fn in PACK.items()}


def table_sizes():
    sizes = {k: len(v) for k, v in tables(bytes(64 + 9408)).items()}
    sizes.update({k: len(v) for k, v in pack_tables().items()})
    sizes['glyphs'] = 5 * len(GLYPHS)
    return sizes
