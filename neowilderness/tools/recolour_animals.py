#!/usr/bin/env python3
"""recolour_animals.py: 16-colour DHGR shading of the original animal sprites.

Art preview only (nothing here feeds the build). The original HGR sprites
(build/original_graphics/NAME.bin, tools/re_graphics.decode: one colour
pixel per column, codes 0..3, -1 transparent) are shown today with four DHGR
colours, dhgr_palette.SPRITES[NAME][code] (the day colours drawn by
src/sprites.s and modelled by tools/dhgr_ref.py / dhgr_sprites.convert).

The recolouring keeps every pixel position: the opaque set is unchanged and
each pixel keeps its code's role; only its colour is chosen from a ramp
(dark -> light) per code and per species, at a level given by local
structure, for a light from the top left:

  * a "form" term, the gradient of the blurred silhouette (display units,
    2:1 pixels): rims facing up/left are lit, rims facing down/right in shade;
  * a "part" term, the same on the pixel's own code region (stripes, bands,
    blotches catch their own light);
  * a broad top-to-bottom term (back lit, belly in shade).

Black (code 0) stays black (outline, seams, dark fur) unless the species
gives code 0 a ramp (the black bear: a dark blue rim light).

Outputs in build/recolour/: NAME_before.png, NAME_after.png (x4 / x2, sky
and ground background above, black below), sheet.png (all pairs, labelled),
animals.json (rows of colour numbers, -1 transparent, plus the cost table).
"""
import json
import math
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
from re_graphics import decode  # noqa: E402
import dhgr_palette as P  # noqa: E402
from dhgr_palette import (BLACK, MAGENTA, DARK_BLUE, PURPLE, DARK_GREEN, GREY1,  # noqa: E402
                          MEDIUM_BLUE, LIGHT_BLUE, BROWN, ORANGE, GREY2, PINK,
                          GREEN, YELLOW, AQUA, WHITE)
from genicons import FONT  # noqa: E402
from pack_boot import compress  # noqa: E402

SRC = HERE / 'build/original_graphics'
OUT = HERE / 'build/recolour'

ANIMALS = ('bear', 'cougar', 'rattlesnake', 'grizzly_bc', 'wolf_bc', 'moose_bc',
           'tiger', 'elephant', 'cobra', 'python', 'adder', 'crocodile',
           'puma', 'jaguar', 'ferdelance', 'anaconda', 'cat')

# Ramps, dark -> light. The two greys render identically (128,128,128).
WARM = (MAGENTA, ORANGE, PINK)               # warm fur
WARM4 = (MAGENTA, ORANGE, ORANGE, PINK)
WARM5 = (MAGENTA, ORANGE, ORANGE, ORANGE, PINK)
GREYF = (DARK_BLUE, GREY1, WHITE)            # grey fur / hide / metal
GREYF4 = (DARK_BLUE, GREY1, GREY1, WHITE)
GREENS = (DARK_GREEN, GREEN, AQUA)
OLIVE = (DARK_GREEN, BROWN, YELLOW)          # olive scales: sparing
BONE = (GREY1, WHITE)                        # tusks, antlers, belly
PALE = (ORANGE, PINK, WHITE)
SOLID = lambda c: (c,)                       # noqa: E731

# Per species: ramp of each code 0..3, and optional tuning.
# key: (ramp0, ramp1, ramp2, ramp3); extra keys: form/part/vert gains.
SPECIES = {
    'bear': dict(ramps=(SOLID(BLACK), (MAGENTA, ORANGE), (BLACK, BLACK, DARK_BLUE, DARK_BLUE, GREY1),
                        (ORANGE, PINK)), edge={0: DARK_BLUE}, edge_dark=DARK_BLUE,
                 bias=-0.1, vert=0.1),
    'cougar': dict(ramps=(SOLID(BLACK), (MAGENTA, MAGENTA, ORANGE), WARM5, (ORANGE, PINK, PINK))),
    'rattlesnake': dict(ramps=(SOLID(BLACK), (MAGENTA,), (BROWN, ORANGE, ORANGE, PINK), (PINK, WHITE)), seg=0.6, vol=0.8),
    'grizzly_bc': dict(ramps=(SOLID(BLACK), (MAGENTA, ORANGE), ((BLACK, MAGENTA), MAGENTA, MAGENTA, ORANGE, ORANGE), (ORANGE, ORANGE, YELLOW)), vol=0.7, dither=0.6),
    'wolf_bc': dict(ramps=(SOLID(BLACK), (DARK_BLUE, (GREY1, DARK_BLUE), GREY1, GREY1, WHITE),
                           (MAGENTA, ORANGE), (GREY1, WHITE, WHITE)), vol=0.7),
    'moose_bc': dict(ramps=(SOLID(BLACK), (MAGENTA, ORANGE), ((BLACK, MAGENTA), MAGENTA, MAGENTA, MAGENTA,
                                                             ORANGE),
                            (GREY1, GREY1, WHITE)), hatch={3: (MAGENTA, ORANGE, ORANGE)},
                     vert=0.0, vol=0.8),
    'tiger': dict(ramps=(SOLID(BLACK), (MAGENTA, ORANGE), WARM5, (GREY1, WHITE, WHITE, WHITE))),
    'elephant': dict(ramps=(SOLID(BLACK), (DARK_BLUE, (DARK_BLUE, GREY1), GREY1, GREY1, GREY1, WHITE), (DARK_BLUE, (DARK_BLUE, GREY1), GREY1, GREY1, GREY1, WHITE), (GREY1, WHITE, WHITE)), vol=0.5, rim=0.2),
    'cobra': dict(ramps=(SOLID(BLACK), (MAGENTA, ORANGE), ((BLACK, BROWN), BROWN, BROWN, BROWN, (BROWN, YELLOW)), (MAGENTA, ORANGE, ORANGE, ORANGE, PINK)), seg=0.5, vol=0.8),
    'python': dict(ramps=(SOLID(BLACK), (BLACK, DARK_GREEN), ((BLACK, BROWN), BROWN, BROWN, YELLOW), (BROWN, YELLOW, YELLOW, WHITE)), seg=0.6, vol=0.8),
    'adder': dict(ramps=(SOLID(BLACK), (MAGENTA, ORANGE), ((BLACK, MAGENTA), MAGENTA, MAGENTA, ORANGE, ORANGE, PINK), (GREY1, WHITE)), seg=0.6, vol=0.8),
    'crocodile': dict(ramps=(SOLID(BLACK), (MAGENTA, PINK), OLIVE, (BROWN, YELLOW))),
    'puma': dict(ramps=(SOLID(BLACK), (MAGENTA, MAGENTA, ORANGE), WARM5, (ORANGE, PINK, PINK))),
    'jaguar': dict(ramps=(SOLID(BLACK), (MAGENTA, MAGENTA, ORANGE), (ORANGE, ORANGE, YELLOW), WARM5)),
    'ferdelance': dict(ramps=(SOLID(BLACK), (GREY1,), ((BLACK, BROWN), BROWN, BROWN, GREY1), (GREY1, WHITE)), seg=0.6, vol=0.8),
    'anaconda': dict(ramps=(SOLID(BLACK), (BROWN,), ((BLACK, DARK_GREEN), DARK_GREEN, DARK_GREEN, GREEN, AQUA), (BROWN, YELLOW)), seg=0.6, vol=0.8),
    'cat': dict(ramps=(SOLID(BLACK), (MAGENTA, ORANGE), (DARK_BLUE, (DARK_BLUE, GREY1), GREY1, GREY1, GREY1, WHITE), (GREY1, WHITE, WHITE)), vol=0.5, rim=0.2),
}

LIGHT = (-0.6, -0.8)    # display units (u right, v down): from the top left


def load(name):
    """Cropped code grid (rows of -1..3) of an original sprite."""
    image, _ = decode((SRC / f'{name}.bin').read_bytes())
    rows = [r for r in image if any(c >= 0 for c in r)]
    ys = [y for y, r in enumerate(image) if any(c >= 0 for c in r)]
    rows = image[ys[0]:ys[-1] + 1]
    x0 = min(x for r in rows for x, c in enumerate(r) if c >= 0)
    x1 = max(x for r in rows for x, c in enumerate(r) if c >= 0)
    return [r[x0:x1 + 1] for r in rows]


def before(name, codes):
    pal = P.SPRITES[name]
    return [[pal[c] if c >= 0 else -1 for c in r] for r in codes]


def blur(mask, radius):
    """Separable box blur, radius in display units (x counts double)."""
    h, w = len(mask), len(mask[0])
    rx, ry = max(1, round(radius / 2)), max(1, round(radius))

    def run(rows, r):
        out = []
        for row in rows:
            n = len(row)
            acc = [0.0] * (n + 1)
            for i, v in enumerate(row):
                acc[i + 1] = acc[i] + v
            out.append([(acc[min(n, i + r + 1)] - acc[max(0, i - r)]) / (2 * r + 1) for i in range(n)])
        return out
    a = run(mask, rx)
    t = run([list(col) for col in zip(*a)], ry)
    return [list(r) for r in zip(*t)]


def gradient_term(f, x, y):
    """Lighting of field f at (x, y): positive where the surface faces the light."""
    h, w = len(f), len(f[0])
    g = lambda yy, xx: f[min(h - 1, max(0, yy))][min(w - 1, max(0, xx))]  # noqa: E731
    gu = (g(y, x + 1) - g(y, x - 1)) / 4.0     # per display unit (2 wide)
    gv = (g(y + 1, x) - g(y - 1, x)) / 2.0
    # outward normal = -gradient; lit when it points towards the light.
    return -(gu * LIGHT[0] + gv * LIGHT[1])


def edge_distances(codes, inside):
    """Per pixel, distances (display units, capped) to the first pixel outside
    `inside` towards the light (up, left, up-left) and away from it."""
    h, w = len(codes), len(codes[0])
    cap = 40
    dirs = ((0, -1, 1.0), (-1, 0, 2.0), (-1, -1, 2.24))

    def march(x, y, dx, dy, unit):
        n = 0
        while True:
            x, y = x + dx, y + dy
            if not (0 <= x < w and 0 <= y < h) or not inside(codes[y][x]):
                return n * unit + unit / 2
            n += 1
            if n * unit >= cap:
                return cap
    out = {}
    for y in range(h):
        for x in range(w):
            if inside(codes[y][x]):
                out[x, y] = ([march(x, y, dx, dy, u) for dx, dy, u in dirs],
                             [march(x, y, -dx, -dy, u) for dx, dy, u in dirs])
    return out


def neighbours(codes, x, y, c):
    h, w = len(codes), len(codes[0])
    return sum(1 for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
               if 0 <= x + dx < w and 0 <= y + dy < h and codes[y + dy][x + dx] == c)


def after(name, codes):
    """Recoloured grid. Shading s in 0..1 per pixel:
    s = 0.5 + bias + vol * (t - 0.5) + rim terms + part term + vert term,
    t = mean over the three light directions of far / (near + far), near and
    far the distances to the silhouette towards and away from the light."""
    spec = SPECIES[name]
    ramps = spec['ramps']
    hatch = spec.get('hatch', {})
    edge = spec.get('edge', {})          # code: colour of its lit-rim pixels only
    h, w = len(codes), len(codes[0])
    dist = edge_distances(codes, lambda c: c >= 0)
    # 'seg' > 0: each segment between black seams (snake coils) is also
    # shaded as its own cylinder, weight seg.
    kseg = spec.get('seg', 0.0)
    seg = edge_distances(codes, lambda c: c > 0) if kseg else {}
    parts = {k: blur([[1.0 if c == k else 0.0 for c in r] for r in codes], spec.get('part_r', 1.5))
             for k in range(4)}
    kvol, kp, kv = spec.get('vol', 0.6), spec.get('part', 0.6), spec.get('vert', 0.2)
    rim, shadow_rim = spec.get('rim', 0.35), spec.get('shadow_rim', 0.25)
    bias = spec.get('bias', 0.0)
    kd = spec.get('dither', 0.4)
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            c = codes[y][x]
            if c < 0:
                row.append(-1)
                continue
            ramp = ramps[c]
            if c in hatch and neighbours(codes, x, y, c) <= 1:
                ramp = hatch[c]
            near, far = dist[x, y]
            lit_rim = min(near[0], near[2]) <= 1.0 or near[1] <= 1.0
            if c in edge:
                any_rim = min(near + far) <= 1.0
                e = edge[c] if lit_rim else spec.get('edge_dark', ramp[0]) if any_rim and (x + y) & 1 else ramp[0]
                row.append(e)
                continue
            t = sum(f / (n + f) for n, f in zip(near, far)) / 3
            if (x, y) in seg:
                sn, sf = seg[x, y]
                t = (1 - kseg) * t + kseg * sum(f / (n + f) for n, f in zip(sn, sf)) / 3
            s = 0.5 + bias + kvol * (t - 0.5)
            if lit_rim:
                s += rim
            if min(far[0], far[1]) <= 1.0:
                s -= shadow_rim
            s += kp * gradient_term(parts[c], x, y)
            s += kv * (0.5 - y / max(1, h - 1))
            q = s * len(ramp) + kd * (((x + y) & 1) - 0.5)   # checker at ramp boundaries
            k = int(max(0.0, min(len(ramp) - 0.001, q)))
            e = ramp[k]
            row.append(e[(x + y) & 1] if isinstance(e, tuple) else e)
        out.append(row)
    return out


# ---------------------------------------------------------------- pictures
SX, SY = 4, 2


def canvas(w, h, c=BLACK):
    return [[c] * w for _ in range(h)]


def panel(grid, background):
    """Sprite at x4 / x2 with a margin, over 'sky' (sky and ground) or black."""
    h, w = len(grid), len(grid[0])
    mx, my = 4, 6
    cw, ch = (w + 2 * mx) * SX, (h + 2 * my) * SY
    img = canvas(cw, ch)
    if background == 'sky':
        horizon = my + h - 4          # feet slightly below the horizon line
        for yy in range(ch):
            v = yy // SY
            img[yy] = [(MEDIUM_BLUE if v < horizon - 10 else
                        LIGHT_BLUE if v < horizon else GREEN if v < horizon + 3 else DARK_GREEN)] * cw
    for y, r in enumerate(grid):
        for x, c in enumerate(r):
            if c < 0:
                continue
            for dy in range(SY):
                line = img[(y + my) * SY + dy]
                for dx in range(SX):
                    line[(x + mx) * SX + dx] = c
    return img


def stack(*imgs, gap=4):
    w = max(len(i[0]) for i in imgs)
    out = []
    for k, i in enumerate(imgs):
        if k:
            out += canvas(w, gap)
        out += [r + [BLACK] * (w - len(r)) for r in i]
    return out


def side(*imgs, gap=8):
    h = max(len(i) for i in imgs)
    rows = [[] for _ in range(h)]
    for k, i in enumerate(imgs):
        for y in range(h):
            if k:
                rows[y] += [BLACK] * gap
            rows[y] += i[y] if y < len(i) else [BLACK] * len(i[0])
    return rows


def text(img, s, x, y, k=2, c=WHITE):
    for i, ch in enumerate(s.upper()):
        if ch not in FONT:
            continue
        for dy, row in enumerate(FONT[ch].split('/')):
            for dx, bit in enumerate(row):
                if bit == '1':
                    for sy in range(k):
                        for sx in range(k):
                            yy, xx = y + dy * k + sy, x + i * 4 * k + dx * k + sx
                            if 0 <= yy < len(img) and 0 <= xx < len(img[0]):
                                img[yy][xx] = c


def write_png(path, rows):
    width, height = len(rows[0]), len(rows)

    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF))
    raw = b''.join(b'\0' + bytes(r) for r in rows)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'
                     + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 3, 0, 0, 0))
                     + chunk(b'PLTE', b''.join(bytes(rgb) for rgb in P.RGB))
                     + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def views(grid):
    return stack(panel(grid, 'sky'), panel(grid, 'black'))


# ---------------------------------------------------------------- cost
def nibble_bytes(grid):
    """4-bit raw bitmap, two pixels per byte, transparency as a separate 1-bit
    mask (rows padded to a byte)."""
    w, h = len(grid[0]), len(grid)
    pix = bytearray()
    for r in grid:
        vals = [max(0, c) for c in r] + [0] * (w & 1)
        pix += bytes(vals[i] << 4 | vals[i + 1] for i in range(0, len(vals), 2))
    mask = bytearray()
    for r in grid:
        bits = [1 if c >= 0 else 0 for c in r]
        bits += [0] * (-len(bits) % 8)
        mask += bytes(sum(b << j for j, b in enumerate(bits[i:i + 8])) for i in range(0, len(bits), 8))
    return bytes(pix), bytes(mask)


def column_runs(grid):
    """dhgr_sprites-like columns: per column top-to-bottom runs, 2 bytes per run
    (up_top, (len-1) << 4 | colour), plus a 2-byte offset per column."""
    h, w = len(grid), len(grid[0])
    body = bytearray()
    for x in range(w):
        y = 0
        while y < h:
            c = grid[y][x]
            if c < 0:
                y += 1
                continue
            n = 1
            while y + n < h and grid[y + n][x] == c and n < 16:
                n += 1
            body += bytes((h - 1 - y, (n - 1) << 4 | c))
            y += n
    return bytes(8 + 2 * (w + 1)) + bytes(body)


def lz(data):
    return len(compress(data)) + 2   # + window address, as build_disk.lz_store


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((SRC / 'manifest.json').read_text())['sprites']
    data, cost, cells = {}, {}, []
    for name in ANIMALS:
        codes = load(name)
        b, a = before(name, codes), after(name, codes)
        assert [[c >= 0 for c in r] for r in a] == [[c >= 0 for c in r] for r in codes]
        write_png(OUT / f'{name}_before.png', views(b))
        write_png(OUT / f'{name}_after.png', views(a))
        data[name] = dict(width=len(a[0]), height=len(a), rows=a,
                          colours=sorted({c for r in a for c in r if c >= 0}),
                          before_colours=sorted({c for r in b for c in r if c >= 0}))
        orig = (SRC / f'{name}.bin').read_bytes()
        pix, mask = nibble_bytes(a)
        runs = column_runs(a)
        cost[name] = dict(original=manifest[name]['encoded_bytes'],
                          original_lz=min(len(orig), lz(orig)),   # build_disk keeps the shorter
                          nibble=len(pix) + len(mask), nibble_lz=min(len(pix) + len(mask), lz(pix + mask)),
                          runs=len(runs), runs_lz=min(len(runs), lz(runs)))
        cell = side(views(b), views(a))
        lab = canvas(len(cell[0]), 16)
        text(lab, name.replace('_bc', '').replace('_', ' '), 2, 2)
        cells.append(stack(lab, cell, gap=0))
    tot = {k: sum(c[k] for c in cost.values()) for k in next(iter(cost.values()))}
    cost['TOTAL'] = tot
    (OUT / 'animals.json').write_text(json.dumps(dict(
        note='rows: DHGR colour numbers (dhgr_palette), -1 transparent; one entry = one '
             'DHGR colour pixel (displayed 2:1). cost in bytes: original = 2-bit column '
             'stream (manifest encoded_bytes); nibble = 4-bit bitmap + 1-bit mask; runs = '
             'column runs as dhgr_sprites (2 bytes per run of one colour); _lz = '
             'pack_boot.compress + 2-byte window.',
        animals=data, cost=cost), indent=None, separators=(',', ':')))
    # sheet: 4 columns
    # sheet: cells packed greedily into rows of at most MAXW pixels
    MAXW, GAP = 2400, 24
    rows, line = [], []

    def flush():
        hh = max(len(c) for c in line) + GAP
        band = canvas(MAXW, hh)
        x = 0
        for c in line:
            for y, r in enumerate(c):
                band[y][x:x + len(r)] = r
            x += len(c[0]) + GAP
        rows.extend(band)
    for c in cells:
        if line and sum(len(k[0]) + GAP for k in line) + len(c[0]) > MAXW:
            flush()
            line = []
        line.append(c)
    flush()
    write_png(OUT / 'sheet.png', rows)
    print(f"{'sprite':12} {'orig':>6} {'orig+lz':>8} {'4bit':>6} {'4bit+lz':>8} {'runs':>6} {'runs+lz':>8}")
    for n, c in cost.items():
        print(f"{n:12} {c['original']:6} {c['original_lz']:8} {c['nibble']:6} {c['nibble_lz']:8} "
              f"{c['runs']:6} {c['runs_lz']:8}")


def review(names, sx=8, sy=4):
    """build/recolour/review.png: before / after of NAMES on the sky, large."""
    global SX, SY
    SX, SY = sx, sy
    cells = []
    for name in names:
        codes = load(name)
        cells.append(side(panel(before(name, codes), 'sky'), panel(after(name, codes), 'sky'),
                          panel(after(name, codes), 'black')))
    write_png(OUT / 'review.png', stack(*cells, gap=8))


if __name__ == '__main__':
    if sys.argv[1:]:
        review(sys.argv[1:])
    else:
        main()
