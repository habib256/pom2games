#!/usr/bin/env python3
"""mkmap.py: TMAKE-inspired mountains with deterministic downhill drainage.

The world is 224 x 168 units (x east, y north). Its height is a sum of
separable Gaussian mountains in four scales (TMAKE lines 2000-4300): border
and corner mountains, then 224*168*2.1e-4*sqrt(level) central ones. The goal
(ranger outpost) sits near the east or west edge; the start (crash site) is
the first central mountain far enough from it. Rivers run downhill from
random sources to an edge or confluence and fill real pits to their spill
level. The drainage reconstruction is not the original TMAKE machine code.

The game reads the map as a grid of 112 x 84 cells (one cell = 2 units = one
ray step), see map_bin(). The fine 224 x 168 geography it is reduced from can
be exported (fine_bytes(), --fine) or appended to a native map (--native,
header byte 37), whose atlas tools/build_disk.py makes resident (lot 5).
Usage: mkmap.py [--seed N] [--level L] [--fine FINE.bin] [--native] OUT.bin [PREVIEW.png]
"""
import argparse, heapq, math, os, random, sys

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
NEIGHBORS = tuple((dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
FOREST_BYTES = (GW // 2) * (GH // 2) // 8
MAP_BYTES = HEADER + GW * GH
MAX_LEVEL = 125                 # format limit (see map_bin)


def gauss(k, d):
    """Mountain profile of scale k at distance d units (TMAKE table, centered)."""
    x = d * 6 * 2 ** k / 470
    z = math.exp(-x * x)
    return z * 0.8 + 0.2 if k == 0 else z


class Map:
    def __init__(self, seed, level):
        self.seed = seed
        self.rnd = random.Random(seed)
        self.level = level
        self.mountains = []           # (x, y, scale, amplitude)
        self.place_goal()
        self.place_mountains()
        self.heights()
        self.water = [[False] * W for _ in range(H)]
        self.lake = [[False] * W for _ in range(H)]
        self.rivers(13)
        self.forest = forests(seed, level)

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

    def drainage(self):
        """Priority flood from the edges: spill levels and acyclic outlets.

        Equal-height plateaus drain along this tree instead of being treated
        as pits. Only cells below their spill level belong to a lake.
        """
        levels = [[None] * W for _ in range(H)]
        parent = [[None] * W for _ in range(H)]
        border = [(x, y) for y in range(H) for x in range(W)
                  if x in (0, W-1) or y in (0, H-1)]
        tie = random.Random(getattr(self, 'seed', 0) ^ 0x57415452)
        tie.shuffle(border)
        heap = []
        order = 0
        for x, y in border:
            levels[y][x] = self.h[y][x]
            heapq.heappush(heap, (self.h[y][x], order, x, y))
            order += 1
        while heap:
            height, _, x, y = heapq.heappop(heap)
            for dx, dy in NEIGHBORS:
                xx, yy = x+dx, y+dy
                if 0 <= xx < W and 0 <= yy < H and levels[yy][xx] is None:
                    level = max(height, self.h[yy][xx])
                    levels[yy][xx] = level
                    parent[yy][xx] = (x, y)
                    heapq.heappush(heap, (level, order, xx, yy))
                    order += 1
        return levels, parent

    def rivers(self, count):
        levels, parent = self.drainage()
        ground = [row[:] for row in self.h]
        protected = {(i, j) for x, y in (self.start, self.goal)
                     for j in range(max(0, y-2), min(H, y+3))
                     for i in range(max(0, x-2), min(W, x+3))}
        self.river_sources = []
        self.river_paths = []
        for _ in range(count):
            source = (20+int(self.rnd.random()*184), 20+int(self.rnd.random()*128))
            cursor = source
            planned = {}
            basin = set()
            path = []
            while cursor is not None:
                x, y = cursor
                path.append(cursor)
                if self.water[y][x]:
                    break  # join an existing watercourse
                level = levels[y][x]
                if ground[y][x] < level and cursor not in planned:
                    # Flood the entire submerged basin to its spill surface.
                    # Cells at the spill height remain shoreline/outlet, not
                    # an unbounded artificial lake across the whole plateau.
                    pending = [cursor]
                    planned[cursor] = level
                    basin.add(cursor)
                    while pending:
                        i, j = pending.pop()
                        for dx, dy in NEIGHBORS:
                            xx, yy = i+dx, j+dy
                            if (0 <= xx < W and 0 <= yy < H
                                    and (xx, yy) not in planned
                                    and levels[yy][xx] == level
                                    and ground[yy][xx] < level):
                                planned[xx, yy] = level
                                basin.add((xx, yy))
                                pending.append((xx, yy))
                else:
                    planned[cursor] = level
                downhill = [(xx, yy) for dx, dy in NEIGHBORS
                            for xx, yy in [(x+dx, y+dy)]
                            if 0 <= xx < W and 0 <= yy < H and levels[yy][xx] < level]
                if downhill:
                    cursor = max(downhill, key=lambda p: (level-levels[p[1]][p[0]]) /
                                 math.hypot(p[0]-x, p[1]-y))
                else:
                    cursor = parent[y][x]
            # Reject a source whose stream/lake covers the crash or rangers;
            # erasing squares of water afterwards would leave broken rivers.
            if not planned or protected.intersection(planned):
                continue
            for (x, y), height in planned.items():
                if not self.water[y][x]:
                    if not hasattr(self, 'lake'):    # maps assembled by tests
                        self.lake = [[False] * W for _ in range(H)]
                    self.lake[y][x] = (x, y) in basin
                self.water[y][x] = True
                self.h[y][x] = height
            self.river_sources.append(source)
            self.river_paths.append(path)


def forest_contours(seed, level):
    """TMAKE 100..340: min five shapes, radius 10, harmonics 1..4, eccentricity .7.

    A separate deterministic stream leaves the port's terrain/drainage intact.
    The original uses its Applesoft USR random generator, not Python's stream.
    """
    rnd = random.Random(seed ^ 0x574F4F44)
    shapes = []
    for _ in range(max(5, int(1.5 * level))):
        amplitudes = [rnd.random() * 3 for _ in range(4)]
        eccentricity = rnd.random() * .7
        phases = [rnd.random() * math.tau for _ in range(5)]
        cx, cy = 24 + int(176 * rnd.random()), 24 + int(120 * rnd.random())
        points = []
        for degrees in range(360):
            angle = degrees * math.pi / 180
            radius = (10 + sum(a * math.sin(p + (k+1)*angle)
                               for k,(a,p) in enumerate(zip(amplitudes, phases))))
            radius /= 1 - eccentricity * math.cos(angle + phases[4])
            x = min(W-1,max(0,cx+math.floor(radius*math.cos(angle)+.5)))
            y = min(H-1,max(0,cy+math.floor(radius*math.sin(angle)+.5)))
            points.append((x,y))
        shapes.append(points)
    return shapes


def forests(seed, level):
    """Fill each original-style irregular contour, then union their coverage."""
    cover = [[False]*W for _ in range(H)]
    for points in forest_contours(seed,level):
        edges = list(zip(points, points[1:]+points[:1]))
        for y in range(max(0,min(p[1] for p in points)), min(H,max(p[1] for p in points)+1)):
            scan = y + .5
            xs = sorted(x0+(scan-y0)*(x1-x0)/(y1-y0)
                        for (x0,y0),(x1,y1) in edges if min(y0,y1)<=scan<max(y0,y1))
            for x0,x1 in zip(xs[::2],xs[1::2]):
                for x in range(max(0,math.ceil(x0-.5)),min(W,math.ceil(x1-.5))):
                    cover[y][x] = True
    return cover


def forest_bits(woods):
    """56 x 42 forest cells (four world units), one bit each, 294 resident bytes."""
    out = bytearray(FOREST_BYTES)
    if woods is not None:
        for y in range(GH//2):
            for x in range(GW//2):
                if woods[4*y+2][4*x+2]:
                    out[y*7+x//8] |= 1 << (x%8)
    return bytes(out)


def forest_at(data, x, y):
    """Forest bit for a terrain cell; absent extension means a legacy bare map."""
    if len(data) < MAP_BYTES+FOREST_BYTES or not data[26] or not (0<=x<GW and 0<=y<GH):
        return False
    return bool(data[MAP_BYTES+(y//2)*7+(x//2)//8] & (1<<((x//2)%8)))


FINE_BYTES = W * H + (W // 8) * H     # 42 336: native cells, then woodland


def fine_bytes(h, water, woods=None, lake=None):
    """The fine geography of a native map (format of the Sierra comparison
    maps, tests/test_adventure.original_map): one byte per unit, row-major,
    level | $80 for water with bit 6 = lake (water levels fit six bits), then
    the woodland bitmap, 28 bytes per row, least significant bit first.
    """
    cells = bytearray()
    for y in range(H):
        for x in range(W):
            level = h[y][x]
            if water[y][x]:
                if not 0 <= level < 64:
                    raise ValueError(f'water level {level} at ({x}, {y}) does not fit 6 bits')
                level |= 0x80 | (0x40 if lake is not None and lake[y][x] else 0)
            elif not 0 <= level <= MAX_LEVEL:
                raise ValueError(f'level {level} at ({x}, {y}) outside 0..{MAX_LEVEL}')
            cells.append(level)
    bits = bytearray((W // 8) * H)
    if woods is not None:
        for y in range(H):
            for x in range(W):
                if woods[y][x]:
                    bits[y * (W // 8) + x // 8] |= 1 << (x % 8)
    return bytes(cells + bits)


def heading_to(sx, sy, tx, ty):
    """Azimuth units (0 = north, 140 = east) from (sx, sy) toward (tx, ty)."""
    return round(math.degrees(math.atan2(tx - sx, ty - sy)) % 360 * UNITS / 360) % UNITS


def coarse_grid(h, water):
    """Preserve every water unit in its 2x2 cell, using its lowest surface.

    A narrow stream must survive odd coordinates. Picking the dry north-west
    sample's height for a wet cell would put water on a hill beside its bed.
    """
    grid = bytearray()
    for j in range(GH):
        for i in range(GW):
            wet = [h[y][x] for y in (2*j, 2*j+1) for x in (2*i, 2*i+1) if water[y][x]]
            level = min(wet) if wet else h[2*j][2*i]
            if not 0 <= level <= MAX_LEVEL:
                raise ValueError(f'level {level} in cell ({i}, {j}) outside 0..{MAX_LEVEL}')
            grid.append(level | (0x80 if wet else 0))
    return grid


def map_bin(h, water, start, goal, heading, difficulty=4, declination=17, woods=None):
    """MAP file, loaded at $7000: a 64-byte header, then 84 rows of 112 cells.

    header +0 'W' +1 version 1, +2/+3 start x 8.8 (cells), +4/+5 start y 8.8,
    +6/+7 heading (0..559), +8/+9 goal x, y (cells), +10 base altitude / 100,
    +11 snow level, +12 latitude (signed degrees), +13/+14 winter / summer
    mean temperature at sea level (deg F), +15 highest wind (mph): the region
    climate of the Sierra Nevada (TOPO $60A8, $4BB0/$4BB1, $60B9 of the
    original). +16 cabin flag, +17/+18 cabin cell x/y, +19/+20
    cabin bearing (our placement rule), +21 highest level + 1 (zero = unknown),
    +22 difficulty 1..10, +23 regional climate index (Sierra 31); zero means
    legacy defaults of 4 and 31 respectively. +24 signed magnetic
    declination in degrees (Sierra TOPO $60A9: 17); zero is true north.
    +25 signed east longitude for the added lunar ephemeris (Sierra -120);
    legacy maps with zero use Greenwich for that extension.
    +26 forest-extension flag, +27 timberline in hundreds of feet (Sierra 110).
    With the flag, 294 packed woodland bytes follow the 9408 terrain cells:
    56 columns x 42 rows, row-major, least significant bit first. These are
    loaded separately at $0800, leaving the terrain at $7040 unchanged.
    Cell byte: level 0..125, bit 7 = water. The renderer
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
    hdr[12], hdr[13], hdr[14], hdr[15] = 38, 41, 77, 30
    hdr[26], hdr[27] = bool(woods is not None), 110  # forest extension, timberline /100 ft
    grid = coarse_grid(h, water)
    # One cabin on dry ground, one third of the way toward the outpost.
    # Header 16 flag, 17/18 cell, 19/20 fixed facing bearing.
    cx, cy = round((2 * sx + goal[0]) / 6), round((2 * sy + goal[1]) / 6)
    candidates = [(i, j) for j in range(1, GH - 1) for i in range(1, GW - 1)
                  if not grid[j*GW+i] & 0x80 and (i, j) != (sx//2, sy//2)
                  and (i, j) != (goal[0]//2, goal[1]//2)]
    if candidates:
        cx, cy = min(candidates, key=lambda c: (c[0]-cx)**2 + (c[1]-cy)**2)
        facing = heading_to(sx, sy, goal[0], goal[1])
        hdr[16:21] = bytes((1, cx, cy, facing & 255, facing >> 8))
    hdr[25] = (-120) & 255  # Sierra longitude for added lunar ephemeris (east positive)
    hdr[22], hdr[23] = difficulty, 31  # fauna: difficulty and Sierra climate index
    if not -128 <= declination <= 127:
        raise ValueError('magnetic declination must fit a signed byte')
    hdr[24] = declination & 255
    hdr[21] = 1 + max(v & 0x7F for v in grid)
    return bytes(hdr + grid) + (forest_bits(woods) if woods is not None else b'')


def preview(path, h, water, marks=(), woods=None):
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
                if woods is not None and woods[y][x]:
                    rgb[o:o+3] = bytes((8,72,8))
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
    ap.add_argument('--fine', metavar='FINE.bin', help='also write the 224 x 168 fine geography')
    ap.add_argument('--native', action='store_true',
                    help='native map: header byte 37 set, fine geography appended (lot 5)')
    ap.add_argument('out')
    ap.add_argument('preview', nargs='?')
    a = ap.parse_args()
    m = Map(a.seed, a.level)
    head = heading_to(*m.start, W // 2, H // 2)
    data = bytearray(map_bin(m.h, m.water, m.start, m.goal, head, a.level, woods=m.forest))
    fine = fine_bytes(m.h, m.water, m.forest, m.lake) if a.fine or a.native else None
    if a.native:
        data[37] = 1
        data += fine
    open(a.out, 'wb').write(data)
    if a.fine:
        open(a.fine, 'wb').write(fine)
    if a.preview:
        preview(a.preview, m.h, m.water, ((m.start, b'\xff\x00\x00'), (m.goal, b'\xff\xff\x00')), m.forest)
    print(f'seed {a.seed} level {a.level}: {len(m.mountains)} mountains, start {m.start} '
          f'goal {m.goal} heading {head}')


if __name__ == '__main__':
    main()
