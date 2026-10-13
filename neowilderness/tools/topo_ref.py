#!/usr/bin/env python3
"""topo_ref.py: reference DHGR TOPO of Neowilderness (lot 4, src/topo.s).

TOPO is drawn at display time from the resident map ($7000: 64-byte header,
84 rows of 112 cells, y = 0 south; cell = level 0..125 in hundreds of feet,
bit 7 water) and the woodland mask ($0800, one bit per 2 x 2 cells). This
module is the exact integer model of src/topo.s; tests compare both banks.

Screen (physical rows 0..159, the mixed text below):
  map     colour pixel x = cell column 0..111 (groups 0..15), north up:
          screen row r shows cell row j = 21 * (159 - r) // 40, i.e.
          floor(t * 84 / 160) with t = 159 - r (2 rows per cell, 1 row for
          8 cells, Bresenham in the asm)
  legend  pixels 112..139 (groups 16..19): north arrow and N (rows 0..17),
          one block per 800 ft tint below the snow level up to the highest
          level, then a white snow block (from row 159 up, legend_blocks)
Colour of a cell, by priority: water (bit 7) medium blue; contour (its
level >> 2, 400 ft steps, above the east or north neighbour's) black; woods
dark green where (x + y) is odd; snow (level >= header +11, when set) white;
otherwise TINT[level >> 3] (woods are black on the dark green tint). Markers C (crash: header +3/+5), R (rangers:
+8/+9), H (cabin, if +16: +17/+18) and P (player: px/py high bytes), in that
order: a 3 x 5 glyph on a black 5 x 7 box centred on the cell's top row,
clamped inside the map; P's box takes the colour of a site on its cell.

Usage: topo_ref.py [MAP.bin] [--px X8.8 --py Y8.8] [OUT.png]
       (default build/map.bin, the start position, build/dhgr/topo_ref.png)
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import dhgr_palette as P  # noqa: E402

W, H = 112, 84
ROWS, COLS = 160, 140
HEADER = 64
FOREST_BYTES = 294
TINT = (P.DARK_GREEN, P.GREEN, P.YELLOW, P.ORANGE, P.BROWN, P.PINK, P.GREY1) + (P.WHITE,) * 9
WATER, WOODS, CONTOUR = P.MEDIUM_BLUE, P.DARK_GREEN, P.BLACK
LEGEND_X, LEGEND_W = 120, 12            # tint blocks: pixels 120..131
NORTH_X = 122                           # north arrow bitmap: pixels 122..128
NORTH = ('.......', '...X...', '...X...', '..XXX..', '..XXX..', '.XXXXX.', '.XXXXX.',
         '...X...', '...X...', '...X...', '.......', '.X...X.', '.XX..X.', '.X.X.X.',
         '.X..XX.', '.X...X.', '.......', '.......')
LEGEND_TOP = len(NORTH)                 # rows below the arrow: tint blocks from row 159 up
GLYPHS = {'C': ('XXX', 'X..', 'X..', 'X..', 'XXX'),
          'R': ('XX.', 'X.X', 'XX.', 'X.X', 'X.X'),
          'H': ('X.X', 'X.X', 'XXX', 'X.X', 'X.X'),
          'P': ('XX.', 'X.X', 'XX.', 'X..', 'X..')}
MARK_COLOUR = {'C': P.ORANGE, 'R': P.YELLOW, 'H': P.PINK, 'P': P.WHITE}


def cell_row(r):
    """Map row j shown on screen row r (0..159)."""
    return 21 * (159 - r) // 40


def top_row(j):
    """First (smallest) screen row of map row j, None if not shown."""
    return next((r for r in range(ROWS) if cell_row(r) == j), None)


def tint(data, level):
    snow = data[11]
    return P.WHITE if snow and level >= snow else TINT[level >> 3]


def woods(data, x, y):
    if not data[26] or len(data) < HEADER + W * H + FOREST_BYTES:
        return False
    mask = data[HEADER + W * H:]
    return bool(mask[(y // 2) * 7 + (x // 2) // 8] & (1 << ((x // 2) % 8)))


def cell_colour(data, x, y):
    grid = data[HEADER:HEADER + W * H]
    b = grid[y * W + x]
    if b & 0x80:
        return WATER
    q = b >> 2
    if x + 1 < W and q > (grid[y * W + x + 1] & 0x7F) >> 2:
        return CONTOUR
    if y + 1 < H and q > (grid[(y + 1) * W + x] & 0x7F) >> 2:
        return CONTOUR
    if (x + y) & 1 and woods(data, x, y):
        # dark green dots would vanish on the dark green tint: black there
        return P.BLACK if tint(data, b) == WOODS else WOODS
    return tint(data, b)


def legend(data, r):
    """Colours of pixels 112..139 of screen row r."""
    out = [P.BLACK] * (COLS - W)
    if r < len(NORTH):
        for i, ch in enumerate(NORTH[r]):
            if ch == 'X':
                out[NORTH_X - W + i] = P.WHITE
    else:
        n, snow_block, shift = legend_blocks(data)
        d = 159 - r
        k = d >> shift
        if k < n + snow_block and d & ((1 << shift) - 1) != (1 << shift) - 1:
            colour = TINT[k] if k < n else P.WHITE
            for x in range(LEGEND_X, LEGEND_X + LEGEND_W):
                out[x - W] = colour
    return out


def legend_blocks(data):
    """(tints shown, snow block 0/1, log2 of the block height).

    Tints 0..n-1 cover the levels below the snow level up to the map's
    highest level (header +21 = highest + 1; zero: unknown, 125); one white
    block follows when the snow level is set and reached. Blocks are 16 rows
    high when at most 8 are shown, 8 rows otherwise (top row black).
    """
    top = data[21] - 1 if data[21] else 125
    snow = data[11]
    below = min(top, snow - 1) if snow else top
    n = below // 8 + 1
    snow_block = int(bool(snow) and top >= snow)
    return n, snow_block, 4 if n + snow_block <= 8 else 3


def markers(data, px, py):
    """[(symbol, x, j)] in drawing order."""
    marks = [('C', data[3], data[5]), ('R', data[8], data[9])]
    if data[16]:
        marks.append(('H', data[17], data[18]))
    marks.append(('P', px >> 8, py >> 8))
    return marks


def page(data, px=None, py=None):
    """160 rows x 140 colour indices."""
    if len(data) < HEADER + W * H:
        raise ValueError('incomplete journey map')
    if px is None:
        px = data[2] | data[3] << 8
    if py is None:
        py = data[4] | data[5] << 8
    rows = {}
    out = []
    for r in range(ROWS):
        j = cell_row(r)
        if j not in rows:
            rows[j] = [cell_colour(data, x, j) for x in range(W)]
        out.append(rows[j] + legend(data, r))
    marks = markers(data, px, py)
    # P on a site: its box takes the site's colour (first of C, R, H).
    p_box = next((MARK_COLOUR[sym] for sym, x, j in marks[:-1]
                  if (x, j) == marks[-1][1:]), P.BLACK)
    for symbol, x, j in marks:
        r = top_row(j)
        if r is None:
            continue
        cx, cr = min(max(x, 2), W - 3), min(max(r, 3), ROWS - 4)
        glyph = GLYPHS[symbol]
        for dy in range(-3, 4):
            for dx in range(-2, 3):
                on = abs(dy) <= 2 and abs(dx) <= 1 and glyph[dy + 2][dx + 1] == 'X'
                box = p_box if symbol == 'P' else P.BLACK
                out[cr + dy][cx + dx] = MARK_COLOUR[symbol] if on else box
    return out


def render(data, px=None, py=None):
    """(main, aux) 8 KB banks; rows 0..159 hold TOPO, the rest is zero."""
    import dhgr_ref
    return dhgr_ref.encode(page(data, px, py))


def rows_of(bank, rows=range(ROWS)):
    """The 40 bytes of each listed row of an 8 KB bank (memory holes excluded)."""
    from hgr_tables import hgr_offset
    return b''.join(bank[hgr_offset(y):hgr_offset(y) + 40] for y in rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('map', nargs='?', type=Path, default=HERE / 'build/map.bin')
    ap.add_argument('out', nargs='?', type=Path, default=HERE / 'build/dhgr/topo_ref.png')
    ap.add_argument('--px', type=lambda v: int(v, 0))
    ap.add_argument('--py', type=lambda v: int(v, 0))
    a = ap.parse_args()
    import dhgr_ref
    a.out.parent.mkdir(parents=True, exist_ok=True)
    dhgr_ref.to_png(a.out, page(a.map.read_bytes(), a.px, a.py))
    print(a.out)


if __name__ == '__main__':
    main()
