#!/usr/bin/env python3
"""mkmap.py: generate a Wilderness map with the TMAKE algorithm.

The world is 224 x 168 units (x east, y north). Its height is a sum of
separable Gaussian mountains in four scales (TMAKE lines 2000-4300): border
and corner mountains, then 224*168*2.1e-4*sqrt(level) central ones. The goal
(ranger outpost) sits near the east or west edge; the start (crash site) is
the first central mountain far enough from it. Rivers run downhill from
random sources and fill the pits they reach into lakes.

The game reads the map as a grid of 112 x 84 cells (one cell = 2 units = one
ray step), see map_bin(). Usage: mkmap.py [--seed N] [--level L] OUT.bin [PREVIEW.png]
"""
import argparse, math, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import topo  # noqa: E402

W, H = 224, 168
GW, GH = W // 2, H // 2
HEADER = 64
UNITS = 560                     # azimuth units per turn (140 per quadrant)
MC = (0.25, 0.4, 0.7, 0.3)      # amplitude of each mountain scale
TOP_LEVEL = 84                  # highest level (10800 ft above a 2400 ft base)
BASE = 24                       # base altitude / 100 ft
SNOW = 48                       # levels at and above this are snow
MAX_LEVEL = 125                 # format limit (see map_bin)


def gauss(k, d):
    """Mountain profile of scale k at distance d units (TMAKE table, centered)."""
    x = d * 6 * 2 ** k / 470
    z = math.exp(-x * x)
    return z * 0.8 + 0.2 if k == 0 else z


class Map:
    def __init__(self, seed, level):
        self.rnd = random.Random(seed)
        self.level = level
        self.mountains = []           # (x, y, scale, amplitude)
        self.place_goal()
        self.place_mountains()
        self.heights()
        self.water = [[False] * W for _ in range(H)]
        self.rivers(13)
        for x, y in (self.start, self.goal):       # never start or arrive in water
            for j in range(max(0, y - 2), min(H, y + 3)):
                for i in range(max(0, x - 2), min(W, x + 3)):
                    self.water[j][i] = False

    def place_goal(self):
        r = self.rnd.random
        xc = 28 - self.level
        self.goal = (int(xc + (r() < .5) * (W - 2 * xc)), int(18 + 132 * r()))

    def add(self, x, y, k, z):
        gx, gy = self.goal
        if math.hypot(x - gx, y - gy) >= 16:     # the outpost stays on flat ground
            self.mountains.append((x, y, k, z * MC[k]))

    def place_mountains(self):
        r = self.rnd.random
        for side in (0, 1):                     # north / south borders
            for i in (1, 2):
                self.add(int(r() * 24 + i * 66 + 1), side * 167, 1, 1)
        for side in (0, 1):                     # west / east borders
            self.add(side * 223, int(r() * 24 + 72), 1, 1)
        for x, y in ((0, 0), (211, 0), (0, 144), (211, 144)):
            self.add(int(x + r() * 13), int(y + r() * 24), 2, 1)
        n = int(W * H * 2.1e-4 * math.sqrt(self.level))
        far = 76 + 10 * self.level
        gx, gy = self.goal
        self.start = None
        for i in range(n):
            x, y, z = int(W * r()), int(H * r()), .5 * r() + .5
            self.add(x, y, i * 4 // n, z)
            if (self.start is None and math.hypot(x - gx, y - gy) >= far
                    and 18 <= x <= 205 and 18 <= y <= 149):
                self.start = (x, y)
        if self.start is None:
            x = gx + (1 if gx < 112 else -1) * int(far + r() * 12)
            self.start = (min(max(x, 18), 205), min(max(H - gy, 18), 149))

    def heights(self):
        raw = [[0.0] * W for _ in range(H)]
        for mx, my, k, a in self.mountains:
            gx = [gauss(k, x - mx) for x in range(W)]
            for y in range(H):
                gy = a * gauss(k, y - my)
                row = raw[y]
                for x in range(W):
                    row[x] += gy * gx[x]
        lo = min(min(r) for r in raw)
        hi = max(max(r) for r in raw)
        self.h = [[round((v - lo) / (hi - lo) * TOP_LEVEL) for v in r] for r in raw]

    def rivers(self, count):
        r = self.rnd.random
        for _ in range(count):
            x, y = 20 + int(r() * 184), 20 + int(r() * 128)
            for _ in range(600):
                if self.water[y][x]:
                    break
                self.water[y][x] = True
                nxt = min(((self.h[y + dy][x + dx], x + dx, y + dy)
                           for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                           if (dx or dy) and 0 <= x + dx < W and 0 <= y + dy < H),
                          default=None)
                if nxt is None or x in (0, W - 1) or y in (0, H - 1):
                    break
                if nxt[0] >= self.h[y][x]:
                    x, y = self.lake(x, y)
                    if x is None:
                        break
                else:
                    x, y = nxt[1], nxt[2]

    def lake(self, x, y, size=300):
        """Flood the pit at (x, y) up to its spill level; return the outlet."""
        level = self.h[y][x]
        cells = {(x, y)}
        while len(cells) < size:
            rim = {(i + dx, j + dy) for i, j in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                   if 0 <= i + dx < W and 0 <= j + dy < H} - cells
            low = min(self.h[j][i] for i, j in rim)
            out = [(i, j) for i, j in rim if self.h[j][i] < level]
            if out:
                for i, j in cells:
                    self.water[j][i] = True
                    self.h[j][i] = level
                return out[0]
            level = max(level, low)
            cells |= {(i, j) for i, j in rim if self.h[j][i] <= level}
        for i, j in cells:
            self.water[j][i] = True
            self.h[j][i] = level
        return None, None


def heading_to(sx, sy, tx, ty):
    """Azimuth units (0 = north, 140 = east) from (sx, sy) toward (tx, ty)."""
    return round(math.degrees(math.atan2(tx - sx, ty - sy)) % 360 * UNITS / 360) % UNITS


def map_bin(h, water, start, goal, heading):
    """MAP file, loaded at $7000: a 64-byte header, then 84 rows of 112 cells.

    header +0 'W' +1 version 1, +2/+3 start x 8.8 (cells), +4/+5 start y 8.8,
    +6/+7 heading (0..559), +8/+9 goal x, y (cells), +10 base altitude / 100,
    +11 snow level. Cell byte: level 0..125, bit 7 = water. The renderer
    needs level - eye + 128 in a byte, eye = level + 2: levels stop at 125.
    """
    sx, sy = start
    hdr = bytearray(HEADER)
    hdr[0:2] = b'W\x01'
    hdr[2], hdr[3] = (sx % 2) * 0x80, sx // 2
    hdr[4], hdr[5] = (sy % 2) * 0x80, sy // 2
    hdr[6], hdr[7] = heading & 0xFF, heading >> 8
    hdr[8], hdr[9] = goal[0] // 2, goal[1] // 2
    hdr[10], hdr[11] = BASE, SNOW
    grid = bytearray()
    for j in range(GH):
        for i in range(GW):
            level = h[2 * j][2 * i]
            if not 0 <= level <= MAX_LEVEL:
                raise ValueError(f'level {level} at ({2 * i}, {2 * j}) outside 0..{MAX_LEVEL}')
            grid.append(level | (0x80 if water[2 * j][2 * i] else 0))
    return bytes(hdr + grid)


def preview(path, h, water, marks=()):
    top = max(max(r) for r in h) or 1
    rgb = bytearray(W * H * 3)
    for y in range(H):
        for x in range(W):
            o = ((H - 1 - y) * W + x) * 3
            if water[y][x]:
                rgb[o:o + 3] = b'\xd0\x40\xff'
            else:
                g = int(40 + 200 * h[y][x] / top)
                rgb[o:o + 3] = bytes((g, g, g)) if h[y][x] >= SNOW else bytes((g // 2, g, g // 2))
                if h[y][x] % 4 == 0 and x and h[y][x - 1] != h[y][x]:
                    rgb[o:o + 3] = b'\x00\x00\x00'
    for (x, y), c in marks:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if 0 <= x + dx < W and 0 <= y + dy < H:
                    o = ((H - 1 - y - dy) * W + x + dx) * 3
                    rgb[o:o + 3] = c
    topo.png(path, W, H, rgb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=1985)
    ap.add_argument('--level', type=int, default=4, choices=range(1, 11), metavar='1..10')
    ap.add_argument('out')
    ap.add_argument('preview', nargs='?')
    a = ap.parse_args()
    m = Map(a.seed, a.level)
    head = heading_to(*m.start, W // 2, H // 2)
    open(a.out, 'wb').write(map_bin(m.h, m.water, m.start, m.goal, head))
    if a.preview:
        preview(a.preview, m.h, m.water, ((m.start, b'\xff\x00\x00'), (m.goal, b'\xff\xff\x00')))
    print(f'seed {a.seed} level {a.level}: {len(m.mountains)} mountains, start {m.start} '
          f'goal {m.goal} heading {head}')


if __name__ == '__main__':
    main()
