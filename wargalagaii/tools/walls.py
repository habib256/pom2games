#!/usr/bin/env python3
"""WARGALAGA II walls (lot 10) -> the textures of WG2.AUX at WALL_AUX.

Warblade frames its field with two textured walls (rock, flesh...); here
the bytes 0-3 and 36-39 of rows 8-191 (model.FIELD_COL). A texture is a
tile of WALL_H rows, 8 bytes a row (the left wall's 4, then the right
wall's), drawn in cells (two dots, like the sprites): smoothed value noise
-> black cracks, a shade (checkerboard), the tint, white crests lit from
above, a rim of the tint along the field. One texture a quarter of the game (levels 1-25,
26-50...): blue rock, orange flesh, violet crystal, green moss.

    tools/walls.py --aux F      write the 4 textures (WALL_TILE bytes each)
    tools/walls.py --png F      preview, the four side by side
"""
import math
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites

WALL_H = 64                     # rows in a tile (rows 8-191: 184 = 64 + 64 + 56)
WALL_CELLS = 14                 # 4 bytes
WALL_TILE = WALL_H * 8
# (palette, dot side, noise seed, cell scale x, rows scale y): rock is
# lumpy, flesh is stretched, crystal is fine, moss is round.
QUARTERS = [(1, 'L', 11, 3.0, 6.0), (1, 'R', 23, 2.5, 11.0), (0, 'L', 37, 2.0, 4.0),
            (0, 'R', 41, 3.5, 5.0)]


def noise_field(seed, sx, sy):
    """Value noise over 14 cells x WALL_H rows, periodic in y (the tile
    repeats down the wall)."""
    rnd = random.Random(seed)
    gx = int(math.ceil(WALL_CELLS / sx)) + 2
    gy = int(round(WALL_H / sy))
    grid = [[rnd.random() for _ in range(gy)] for _ in range(gx)]
    ky = WALL_H / gy

    def at(c, y):
        fx, fy = c / sx, (y % WALL_H) / ky
        i, j = int(fx), int(fy)
        u, v = fx - i, fy - j
        u, v = u * u * (3 - 2 * u), v * v * (3 - 2 * v)
        a = grid[i][j % gy] * (1 - u) + grid[i + 1][j % gy] * u
        b = grid[i][(j + 1) % gy] * (1 - u) + grid[i + 1][(j + 1) % gy] * u
        return a * (1 - v) + b * v
    return at


def wall_cells(quarter, side):
    """side 0: left wall (rim on its last cell), 1: right (rim on cell 0).
    -> WALL_H strings of 14 cells ('.', 'W', and the tint's 'L'/'R')."""
    palette, dot, seed, sx, sy = QUARTERS[quarter]
    at = noise_field(seed + 101 * side, sx, sy)
    rows = []
    for y in range(WALL_H):
        row = ''
        for c in range(WALL_CELLS):
            rim = c == WALL_CELLS - 1 if side == 0 else c == 0
            n = at(c, y)
            if rim:
                ch = dot
            elif n < 0.40:
                ch = '.'
            elif n - at(c, y - 1) > 0.05 and n > 0.56:
                ch = 'W'
            elif n < 0.60:                   # shade: a checkerboard of the tint
                ch = dot if (c + y) % 2 else '.'
            else:
                ch = dot
            row += ch
        rows.append(row)
    return rows


def tile(quarter):
    """-> WALL_H rows of 8 bytes (left wall, right wall)."""
    palette = QUARTERS[quarter][0]
    walls = [wall_cells(quarter, s) for s in (0, 1)]
    out = []
    for y in range(WALL_H):
        row = []
        for w in walls:
            d = sprites.dots(w[y])
            row += [palette << 7 | sum(d[7 * b + i] << i for i in range(7)) for b in range(4)]
        out.append(row)
    return out


def aux_image():
    return b''.join(bytes(b for row in tile(q) for b in row) for q in range(len(QUARTERS)))


def png(path, scale=3):
    pix = []
    for y in range(WALL_H):
        line = []
        for q in range(len(QUARTERS)):
            palette, dot = QUARTERS[q][:2]
            for w in (wall_cells(q, 0), wall_cells(q, 1)):
                for ch in w[y]:
                    rgb = (0, 0, 0) if ch == '.' else (255, 255, 255) if ch == 'W' \
                        else sprites.RGB[(ch, palette)]
                    line += [rgb] * (2 * scale)
                line += [(40, 40, 40)] * (2 * scale)
        pix += [line] * scale
    sprites.write_png(path, pix)


def main():
    assert len(aux_image()) == len(QUARTERS) * WALL_TILE
    if '--aux' in sys.argv:
        Path(sys.argv[sys.argv.index('--aux') + 1]).write_bytes(aux_image())
    elif '--png' in sys.argv:
        png(sys.argv[sys.argv.index('--png') + 1])
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
