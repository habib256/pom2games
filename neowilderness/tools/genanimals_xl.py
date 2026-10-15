#!/usr/bin/env python3
"""genanimals_xl.py: a new 16-colour DHGR animal set (XL edition, preview).

Art preview only (nothing here feeds the build). Each of the 17 animal
sprites of the original is redrawn from scratch at view size, in a modern
pixel-art style: solid shaded ramps (no dither), a 1-pixel dark outline, one
light from the top left, 4-7 colours per sprite.

Geometry is authored in display units on the real 2:1 screen: one DHGR
colour pixel (one sprite column) is 2 units wide and 1 unit (one row) tall.
A sprite is a list of primitives (ellipses, tapered tubes, polygons), each
with a material (a ramp dark -> light, an optional pattern) and a normal
model; the rasteriser keeps the topmost primitive per pixel, shades it by
Lambert from the light, then draws the outline (silhouette edge, plus the
inner edge of primitives marked line=True against what lies under them).
Hand touches (eyes, claws, nostrils) are pixel lists.

Placement constraints of the game are kept: each new sprite has exactly the
original's width in columns (the projection centres on width // 2), its
bottom opaque row on the original's bottom row (the ground anchor 'base'),
and no more rows than the original (original_top_row upward).

Outputs in build/animals_xl/: NAME.png (x4 / x2: on the day view above,
on black below), sheet.png (per animal: original as drawn today | new, day
and night, and the new one decimated at shifts 1 and 2 as the distant
billboard samples it), animals.json (rows of colour numbers, -1
transparent, plus the cost table).

Usage: genanimals_xl.py            all outputs
       genanimals_xl.py NAME...    build/animals_xl/review.png, large
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
import recolour_animals as R  # noqa: E402
from dhgr_palette import (BLACK, MAGENTA, DARK_BLUE, PURPLE, DARK_GREEN, GREY1,  # noqa: E402,F401
                          MEDIUM_BLUE, LIGHT_BLUE, BROWN, ORANGE, GREY2, PINK,
                          GREEN, YELLOW, AQUA, WHITE)

SRC = HERE / 'build/original_graphics'
OUT = HERE / 'build/animals_xl'
GREY = GREY1

LIGHT = (-0.45, -0.62, 0.64)
_n = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _n for c in LIGHT)


# ---------------------------------------------------------------- materials
class Mat:
    """ramp: colours dark -> light. bias/gain: level = bias + gain * (lam - .5).
    pat(p) -> colour or None, p a dict (u, v, t, d, k, lam, x, y)."""

    def __init__(self, ramp, bias=0.42, gain=1.25, pat=None, outline=BLACK, hi=0.6, rim=None):
        self.ramp, self.bias, self.gain, self.pat, self.outline = ramp, bias, gain, pat, outline
        self.hi = hi
        self.rim = ramp[-1] if rim is None else rim

    def colour(self, lam, shade, p):
        d = lam - 0.5
        level = self.bias + shade + self.gain * (d * self.hi if d > 0 else d)
        k = int(max(0, min(len(self.ramp) - 1, math.floor(level * len(self.ramp)))))
        p['k'] = k
        p['lam'] = lam
        if self.pat:
            c = self.pat(p)
            if c is not None:
                return c
        c = self.ramp[k]
        if isinstance(c, tuple):         # checker mix of two colours
            c = c[(p['x'] + p['y']) & 1]
        return c


# ---------------------------------------------------------------- primitives
def norm3(x, y, z):
    n = math.sqrt(x * x + y * y + z * z) or 1.0
    return x / n, y / n, z / n


class Prim:
    line = False
    shade = 0.0
    flat = 1.0      # < 1: rounder edges (stronger shading), > 1: flatter

    def __init__(self, mat, line=False, shade=0.0, flat=1.0, grp=None):
        self.mat, self.line, self.shade, self.flat = mat, line, shade, flat
        self.grp = grp if grp is not None else id(self)


class Ellipse(Prim):
    def __init__(self, cx, cy, rx, ry, mat, ang=0.0, **kw):
        super().__init__(mat, **kw)
        self.cx, self.cy, self.rx, self.ry = cx, cy, rx, ry
        self.ca, self.sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))

    def hit(self, u, v):
        du, dv = u - self.cx, v - self.cy
        x = (du * self.ca + dv * self.sa) / self.rx
        y = (-du * self.sa + dv * self.ca) / self.ry
        r2 = x * x + y * y
        if r2 > 1:
            return None
        nx, ny = x * self.ca - y * self.sa, x * self.sa + y * self.ca
        return norm3(nx, ny, math.sqrt(1 - r2) * self.flat), dict(t=0.0, d=x, e=math.sqrt(r2))


class Tube(Prim):
    """Polyline of (u, v, radius) points; a tapered capsule."""

    def __init__(self, pts, mat, **kw):
        super().__init__(mat, **kw)
        self.pts = pts
        self.cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.cum.append(self.cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))

    def hit(self, u, v):
        best = None
        for i, (a, b) in enumerate(zip(self.pts, self.pts[1:])):
            ex, ey = b[0] - a[0], b[1] - a[1]
            L2 = ex * ex + ey * ey or 1e-9
            s = max(0.0, min(1.0, ((u - a[0]) * ex + (v - a[1]) * ey) / L2))
            px, py = a[0] + s * ex, a[1] + s * ey
            r = a[2] + s * (b[2] - a[2])
            dx, dy = u - px, v - py
            q = math.hypot(dx, dy) / r
            if q <= 1 and (best is None or q < best[0]):
                L = math.sqrt(L2)
                side = (ex * dy - ey * dx) / (L * r)    # signed lateral offset
                best = (q, dx / r, dy / r, self.cum[i] + s * L, side)
        if best is None:
            return None
        q, nx, ny, t, side = best
        return norm3(nx, ny, math.sqrt(max(0, 1 - q * q)) * self.flat), dict(t=t, d=side, e=q)


class Poly(Prim):
    def __init__(self, pts, mat, n=(0.0, 0.0), **kw):
        super().__init__(mat, **kw)
        self.pts, self.n = pts, n

    def hit(self, u, v):
        inside = False
        pts = self.pts
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            if (y1 > v) != (y2 > v) and u < x1 + (v - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
        if not inside:
            return None
        return norm3(self.n[0], self.n[1], self.flat), dict(t=0.0, d=0.0, e=0.0)


class Cut(Prim):
    """Erase (transparent) inside an ellipse or polygon shape."""

    def __init__(self, shape):
        super().__init__(None)
        self.shape = shape

    def hit(self, u, v):
        return self.shape.hit(u, v)


def arc(cx, cy, rx, ry, a0, a1, r0, r1=None, n=12):
    """Tube points along an elliptic arc (degrees, 0 = right, 90 = down)."""
    r1 = r0 if r1 is None else r1
    out = []
    for i in range(n + 1):
        s = i / n
        a = math.radians(a0 + (a1 - a0) * s)
        out.append((cx + rx * math.cos(a), cy + ry * math.sin(a), r0 + (r1 - r0) * s))
    return out


# ---------------------------------------------------------------- raster
def render(spec):
    W, H = spec['w'], spec['h']
    prims = spec['prims']
    top = [[None] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            u, v = 2 * x + 1.0, y + 0.5
            for k in range(len(prims) - 1, -1, -1):
                h = prims[k].hit(u, v)
                if h:
                    top[y][x] = None if prims[k].mat is None else (k, h)
                    break
    # Smoothed normal per group: gradient of the blurred union of the group's
    # coverage, so bodies built of several ellipses shade as one volume.
    alpha = spec.get('alpha', 0.45)
    rad = spec.get('blur', 5.0)
    fields = {}
    for g in {p.grp for p in prims if p.mat is not None}:
        mask = [[0.0] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                u, v = 2 * x + 1.0, y + 0.5
                if any(p.grp == g and p.mat is not None and p.hit(u, v) for p in prims):
                    mask[y][x] = 1.0
        fields[g] = R.blur(mask, rad)
    grid = [[-1] * W for _ in range(H)]
    lams = [[0.0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if top[y][x] is None:
                continue
            k, (n, info) = top[y][x]
            p = prims[k]
            f = fields[p.grp]
            gx = (f[y][min(W - 1, x + 1)] - f[y][max(0, x - 1)]) / 4.0
            gy = (f[min(H - 1, y + 1)][x] - f[max(0, y - 1)][x]) / 2.0
            kf = spec.get("kf", 1.3) * rad
            fn = norm3(-gx * kf, -gy * kf, 1.0)
            a = getattr(p, 'alpha', alpha)
            n = norm3(*(a * c1 + (1 - a) * c2 for c1, c2 in zip(n, fn)))
            lam = sum(a * b for a, b in zip(n, LIGHT))
            info = dict(info, u=2 * x + 1.0, v=y + 0.5, x=x, y=y)
            grid[y][x] = p.mat.colour(lam, p.shade, info)
            lams[y][x] = lam
    out = [r[:] for r in grid]
    lit_outline = spec.get('outline_lit')
    for y in range(H):
        for x in range(W):
            if top[y][x] is None:
                continue
            k = top[y][x][0]
            p = prims[k]
            edge = lit = False
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                xx, yy = x + dx, y + dy
                o = top[yy][xx] if 0 <= xx < W and 0 <= yy < H else None
                if o is None:
                    edge = True
                    lit = lit or dx < 0 or dy < 0
                elif p.line and o[0] < k and prims[o[0]].grp != p.grp:
                    edge = True
            if edge:
                out[y][x] = lit_outline if (lit and lit_outline is not None) else p.mat.outline
    # Rim light: the pixel just inside the outline on the lit side (above,
    # or to the left on steep edges) takes the material's rim colour.
    def opaque(xx, yy):
        return 0 <= xx < W and 0 <= yy < H and top[yy][xx] is not None
    for y in range(H):
        for x in range(W):
            if top[y][x] is None or out[y][x] != grid[y][x]:
                continue
            p = prims[top[y][x][0]]
            if p.mat.rim is None or getattr(p, 'norim', False):
                continue
            up = opaque(x, y - 1) and not opaque(x, y - 2) and out[y - 1][x] != grid[y - 1][x]
            left = opaque(x - 1, y) and not opaque(x - 2, y) and out[y][x - 1] != grid[y][x - 1]
            if up or (left and lams[y][x] > spec.get('rim_left', 0.75)):
                out[y][x] = p.mat.rim
    for x, y, c in spec.get('dots', ()):
        if 0 <= x < W and 0 <= y < H:
            out[y][x] = c
    return out


# ---------------------------------------------------------------- helpers
def leg(top, knee, foot, r0, r1, r2, mat, paw=None, **kw):
    """A leg tube; paw (rx, ry) adds a foot ellipse resting on foot."""
    out = [Tube([(top[0], top[1], r0), (knee[0], knee[1], r1), (foot[0], foot[1] - r2, r2)], mat, **kw)]
    if paw:
        out.append(Ellipse(foot[0] + paw[0] * 0.35, foot[1] - paw[1], paw[0], paw[1], mat,
                           grp=out[0].grp, line=kw.get('line', False), shade=kw.get('shade', 0.0)))
    return out


def hexgrid(u, v, su, sv, ofs=(0.0, 0.0)):
    """Nearest point of a staggered grid: (du, dv) from it."""
    j = math.floor((v - ofs[1]) / sv + 0.5)
    shift = su / 2 if j & 1 else 0.0
    i = math.floor((u - ofs[0] - shift) / su + 0.5)
    cu, cv = ofs[0] + shift + i * su, ofs[1] + j * sv
    best = (u - cu, v - cv, i, j)
    for jj in (j - 1, j + 1):
        sh = su / 2 if jj & 1 else 0.0
        ii = math.floor((u - ofs[0] - sh) / su + 0.5)
        du, dv = u - (ofs[0] + sh + ii * su), v - (ofs[1] + jj * sv)
        if du * du / (su * su) + dv * dv / (sv * sv) < best[0] ** 2 / (su * su) + best[1] ** 2 / (sv * sv):
            best = (du, dv, ii, jj)
    return best


def hash2(i, j):
    return ((i * 73856093) ^ (j * 19349663)) % 1000 / 1000.0


# ================================================================ species
SPECIES = {}


def species(fn):
    SPECIES[fn.__name__] = fn
    return fn


def size(name):
    m = json.loads((SRC / 'manifest.json').read_text())['sprites'][name]
    return m['width'] // 2, m['height']


@species
def bear(W, H):
    """Sierra black bear, walking right, head low."""
    fur = Mat((BLACK, BLACK, BLACK, BLACK, DARK_BLUE), bias=0.5, gain=1.6, rim=GREY)
    far = Mat((BLACK, BLACK, DARK_BLUE), bias=0.3, gain=1.0, rim=DARK_BLUE)
    muz = Mat((MAGENTA, ORANGE, PINK), bias=0.45)
    B = H
    p = []
    p += leg((52, 34), (48, 44), (47, B), 6, 5, 4, far, paw=(5, 3))
    p += leg((24, 34), (30, 44), (29, B), 7, 5, 4, far, paw=(5, 3))
    p.append(Ellipse(36, 30, 30, 15, fur, flat=0.9, grp=1))
    p.append(Ellipse(28, 24, 18, 11, fur, ang=-8, grp=1))           # rump / back
    p.append(Ellipse(50, 25, 13, 11, fur, grp=1))                   # shoulder
    legs = Mat((BLACK, BLACK, DARK_BLUE), bias=0.5, gain=1.6, rim=GREY)
    p += leg((18, 32), (16, 44), (17, B), 9, 6, 4, legs, paw=(6, 3), line=True)
    p += leg((58, 34), (60, 44), (61, B), 7, 6, 4, legs, paw=(6, 3), line=True)
    p.append(Ellipse(64, 31, 10, 9, fur, grp=2, line=True))        # head
    p.append(Ellipse(59, 22, 3.5, 3.5, fur, grp=2))                 # ear
    p.append(Ellipse(73, 34, 6, 4, muz, grp=2))                    # muzzle
    return dict(prims=p, outline_lit=DARK_BLUE,
                dots=[(33, 29, BLACK), (32, 29, GREY), (39, 33, BLACK)])



@species
def grizzly_bc(W, H):
    """Grizzly, walking right, shoulder hump, dished face, pale-tipped fur."""
    fur = Mat((MAGENTA, MAGENTA, ORANGE, ORANGE, ORANGE, PINK), bias=0.42, gain=1.25)
    far = Mat((BLACK, MAGENTA, MAGENTA, ORANGE), bias=0.35, gain=1.0)
    B = H
    p = []
    p += leg((70, 34), (68, 46), (66, B), 7, 6, 5, far, paw=(6, 3))
    p += leg((28, 34), (34, 46), (32, B), 8, 6, 5, far, paw=(6, 3))
    p.append(Ellipse(46, 30, 40, 16, fur, flat=0.9, grp=1))
    p.append(Ellipse(64, 21, 15, 9, fur, grp=1))                  # hump
    p.append(Ellipse(22, 28, 16, 15, fur, grp=1))                 # rump
    p += leg((20, 34), (18, 46), (20, B), 11, 8, 5, fur, paw=(7, 3), line=True)
    p += leg((76, 32), (80, 46), (82, B), 9, 7, 5, fur, paw=(7, 3), line=True)
    p.append(Ellipse(86, 29, 11, 10, fur, grp=2, line=True))
    p.append(Ellipse(96, 33, 6, 4.5, Mat((MAGENTA, ORANGE, PINK), bias=0.5), grp=2))
    p.append(Ellipse(80, 19, 3.5, 3.5, fur, grp=2))
    return dict(prims=p, dots=[(44, 27, BLACK), (50, 32, BLACK),
                              (43, 53, WHITE), (45, 53, WHITE), (13, 53, WHITE), (11, 53, WHITE)])



@species
def cougar(W, H):
    """Cougar stalking low, right, long tail curling up at the tip."""
    fur = Mat((MAGENTA, ORANGE, ORANGE, ORANGE, PINK), bias=0.40)
    far = Mat((MAGENTA, MAGENTA, ORANGE), bias=0.35, gain=1.0)
    pale = Mat((ORANGE, PINK, WHITE), bias=0.45)
    B = H
    p = []
    p.append(Tube([(30, 24, 3.5), (18, 30, 3), (8, 34, 2.8), (3, 28, 2.6), (6, 21, 2.4)], fur))
    p += leg((76, 30), (74, 38), (72, B), 4.5, 4, 3, far, paw=(4, 2.5))
    p += leg((40, 28), (46, 36), (44, B), 6, 4, 3, far, paw=(4, 2.5))
    p.append(Ellipse(58, 25, 28, 9, fur, ang=4, flat=0.9, grp=1))
    p.append(Ellipse(40, 23, 11, 9, fur, grp=1))
    p.append(Ellipse(64, 31, 14, 3.5, pale, grp=1))               # belly
    p += leg((36, 26), (30, 36), (34, B), 8, 5, 3, fur, paw=(5, 2.5), line=True)
    p += leg((80, 28), (84, 36), (86, B), 5.5, 4.5, 3, fur, paw=(5, 2.5), line=True)
    p.append(Tube([(76, 24, 7), (86, 20, 6)], fur, grp=2))         # neck
    p.append(Ellipse(91, 18, 9, 7.5, fur, grp=2, line=True))
    p.append(Ellipse(99, 21, 5, 4, pale, grp=2))
    p.append(Ellipse(86, 10, 3, 3.5, fur, grp=2))
    p.append(Ellipse(93, 10, 2.6, 3, fur, grp=2, shade=-0.1))
    return dict(prims=p, dots=[(46, 16, YELLOW), (47, 16, BLACK), (51, 19, MAGENTA), (50, 22, BLACK),
                              (1, 21, BLACK), (2, 20, BLACK), (3, 19, BLACK)])



@species
def puma(W, H):
    """Puma (South America) sitting upright, three-quarter, looking at us."""
    fur = Mat((MAGENTA, ORANGE, ORANGE, ORANGE, PINK), bias=0.40)
    far = Mat((MAGENTA, MAGENTA, ORANGE), bias=0.35, gain=1.0)
    pale = Mat((ORANGE, PINK, WHITE), bias=0.45)
    B = H
    p = []
    p.append(Tube([(18, 70, 3.2), (8, 69, 3), (3, 62, 2.8), (6, 54, 2.5)], fur))   # tail
    p.append(Ellipse(28, 50, 20, 22, fur, flat=0.8, grp=1))           # haunch+body
    p.append(Ellipse(38, 44, 13, 16, fur, grp=1))                      # chest
    p.append(Ellipse(40, 44, 6, 11, pale, grp=1))                      # chest blaze
    p += leg((32, 54), (33, 64), (32, B), 5, 4, 3, far, paw=(4, 2.5))
    p += leg((44, 52), (46, 64), (47, B), 5.5, 4.5, 3, fur, paw=(5, 2.5), line=True)
    p.append(Ellipse(17, 60, 13, 10, fur, grp=3, line=True))          # hind thigh
    p.append(Ellipse(24, 70, 9, 3, fur, grp=3))                       # hind foot
    p.append(Ellipse(38, 21, 15, 12, fur, line=True, grp=2))           # head
    p.append(Ellipse(26, 10, 4, 5, fur, grp=2))
    p.append(Ellipse(50, 10, 4, 5, fur, grp=2))
    p.append(Ellipse(38, 28, 8, 5.5, pale, grp=2))                     # muzzle
    return dict(prims=p, dots=[(15, 20, YELLOW), (16, 20, BLACK), (21, 20, BLACK), (22, 20, YELLOW),
                              (19, 25, MAGENTA), (18, 26, BLACK), (19, 27, BLACK), (20, 26, BLACK)])



def stripes(u0, period, wob):
    def pat(p):
        if p['k'] == 0 and p['e'] > 0.85:
            return None
        s = (p['u'] + 0.35 * p['v'] + wob * math.sin(p['v'] / 3.5 + p['u'] / 11)) % period
        w = 1.9 if p['e'] < 0.7 else 1.2
        if p['u'] > u0 and s < w * 2:
            return BLACK
        return None
    return pat


@species
def tiger(W, H):
    """Tiger walking right, big head, vertical stripes tapering down the flanks."""
    def stripe(p):
        u, v = p['u'], p['v']
        if p['e'] > 0.88 or u < 10 or u > 76:
            return None
        s = (u + 2.5 * math.sin(v / 4.0 + u / 13.0)) % 10
        w = 4.6 * (1.0 - max(0.0, v - 25) / 22.0)
        return BLACK if s < w else None
    fur = Mat((MAGENTA, ORANGE, ORANGE, ORANGE, PINK), bias=0.40, pat=stripe)
    far = Mat((MAGENTA, MAGENTA, ORANGE), bias=0.35, gain=1.0, pat=stripe)
    white = Mat((GREY, WHITE, WHITE), bias=0.45)
    def tailring(p):
        return BLACK if p['e'] < 0.9 and p['t'] % 7 < 2.4 else None
    B = H
    p = []
    p.append(Tube([(20, 30, 4), (10, 38, 3.8), (6, 50, 3.6), (9, 58, 3.6)], Mat(fur.ramp, bias=0.4, pat=tailring)))
    p += leg((68, 44), (68, 56), (66, B), 7, 6, 5, far, paw=(6, 3))
    p += leg((32, 44), (38, 56), (36, B), 8, 6, 5, far, paw=(6, 3))
    p.append(Ellipse(48, 36, 30, 13, fur, flat=0.9, grp=1))
    p.append(Ellipse(68, 36, 12, 14, fur, grp=1))
    p.append(Ellipse(26, 35, 14, 13, fur, grp=1))
    p.append(Ellipse(52, 46, 20, 3.5, white, grp=1))
    p.append(Ellipse(24, 42, 12, 12, fur, grp=3, line=True))
    p += leg((24, 48), (24, 58), (24, B), 8, 6, 5.5, fur, paw=(6.5, 3), grp=3)
    p.append(Ellipse(74, 44, 9, 10, fur, grp=4, line=True))
    p += leg((74, 50), (77, 58), (78, B), 7.5, 6, 5.5, fur, paw=(6.5, 3), grp=4)
    p.append(Ellipse(86, 30, 13, 12, fur, grp=2, line=True))
    p.append(Ellipse(78, 19, 3.5, 3.5, fur, grp=2))
    p.append(Ellipse(91, 19, 3.5, 3.5, fur, grp=2))
    p.append(Ellipse(93, 36, 7, 5, white, grp=2))
    p.append(Ellipse(82, 35, 5, 4, white, grp=2))
    return dict(prims=p, dots=[(44, 27, YELLOW), (45, 27, BLACK), (48, 33, PINK), (49, 34, BLACK),
                              (47, 37, BLACK), (48, 37, BLACK), (43, 24, BLACK), (42, 25, BLACK),
                              (41, 30, BLACK), (40, 31, BLACK), (42, 22, BLACK), (44, 22, BLACK)])



def rosettes(su, sv, ru, rv, u0=0, head_u=None):
    def pat(p):
        if p['e'] > 0.9:
            return None
        u, v = p['u'], p['v']
        if head_u is not None and u > head_u:
            du, dv, i, j = hexgrid(u, v, 5, 4)
            return BLACK if (du / 1.1) ** 2 + (dv / 0.6) ** 2 < 1 and hash2(i, j) < 0.55 else None
        du, dv, i, j = hexgrid(u + 3 * hash2(j0 := int(v // sv), 1), v, su, sv)
        q = math.sqrt((du / ru) ** 2 + (dv / rv) ** 2)
        a = math.atan2(dv, du)
        gap = (a + 6 * hash2(i, j)) % (2 * math.pi) < 1.1
        if 0.7 <= q <= 1.05 and not gap:
            return BLACK
        if q < 0.7:
            return MAGENTA if p['k'] >= 1 else BLACK
        return None
    return pat


@species
def jaguar(W, H):
    """Jaguar walking right: stocky, massive head, big rosettes."""
    ros = rosettes(15, 10, 6, 4.2, head_u=96)
    fur = Mat((MAGENTA, ORANGE, ORANGE, ORANGE, YELLOW), bias=0.42, pat=ros)
    far = Mat((MAGENTA, MAGENTA, ORANGE), bias=0.35, gain=1.0, pat=ros)
    pale = Mat((ORANGE, PINK, WHITE), bias=0.45)
    B = H
    p = []
    p.append(Tube([(22, 32, 4.2), (12, 40, 4), (8, 52, 3.8), (12, 60, 3.6)], fur))
    p += leg((86, 44), (86, 56), (84, B), 8, 7, 6, far, paw=(7, 3))
    p += leg((38, 44), (44, 56), (42, B), 9, 7, 6, far, paw=(7, 3))
    p.append(Ellipse(60, 36, 36, 15, fur, flat=0.9, grp=1))
    p.append(Ellipse(86, 37, 14, 16, fur, grp=1))
    p.append(Ellipse(32, 35, 15, 14, fur, grp=1))
    p.append(Ellipse(62, 49, 16, 3, Mat((ORANGE, WHITE), bias=0.5), grp=1))
    p.append(Ellipse(30, 42, 13, 13, fur, grp=3, line=True))
    p += leg((30, 48), (30, 58), (30, B), 9, 7, 6, fur, paw=(7.5, 3), grp=3)
    p.append(Ellipse(92, 44, 10, 11, fur, grp=4, line=True))
    p += leg((92, 50), (95, 58), (96, B), 8.5, 7, 6, fur, paw=(7.5, 3), grp=4)
    p.append(Ellipse(106, 30, 14, 12.5, fur, grp=2, line=True))
    p.append(Ellipse(99, 19, 3.5, 3.5, fur, grp=2))
    p.append(Ellipse(115, 36, 7, 5, pale, grp=2))
    return dict(prims=p, dots=[(54, 27, YELLOW), (55, 27, BLACK), (58, 33, PINK), (59, 34, BLACK),
                              (57, 38, BLACK), (58, 38, BLACK)])



@species
def cat(W, H):
    """Andean cat: silver-grey, rust blotches, very thick ringed tail."""
    def blotch(p):
        if p['e'] > 0.85:
            return None
        du, dv, i, j = hexgrid(p['u'], p['v'], 12, 7)
        if p['u'] > 34 and p['u'] < 82 and (du / 3.2) ** 2 + (dv / 2.6) ** 2 < 1:
            return ORANGE if p['k'] >= 1 else MAGENTA
        return None
    fur = Mat((DARK_BLUE, GREY, GREY, GREY, WHITE), bias=0.42, pat=blotch)
    far = Mat((DARK_BLUE, DARK_BLUE, GREY), bias=0.35, gain=1.0)

    def rings(p):
        if p['e'] > 0.9:
            return None
        if (p['t'] % 10) < 4:
            return ORANGE if p['k'] >= 1 else MAGENTA
        return None
    tail = Mat((DARK_BLUE, GREY, GREY, WHITE), bias=0.45, pat=rings)
    pale = Mat((GREY, WHITE, WHITE), bias=0.5)
    B = H
    p = []
    p.append(Tube([(38, 36, 7), (26, 42, 8.5), (16, 50, 8.5), (8, 44, 8), (6, 32, 7.5), (12, 22, 6.5)], tail))
    p += leg((76, 46), (76, 54), (74, B), 5, 4.5, 4, far, paw=(4.5, 2.5))
    p += leg((46, 46), (52, 54), (50, B), 6, 4.5, 4, far, paw=(4.5, 2.5))
    p.append(Ellipse(62, 38, 26, 12, fur, flat=0.9, grp=1))
    p.append(Ellipse(44, 38, 12, 12, fur, grp=1))
    p.append(Ellipse(64, 47, 16, 3, pale, grp=1))
    p.append(Ellipse(42, 44, 10, 10, fur, grp=3, line=True))
    p += leg((42, 48), (42, 56), (42, B), 6, 5, 4, fur, paw=(5, 2.5), grp=3)
    p += leg((80, 42), (84, 54), (86, B), 6, 5, 4, fur, paw=(5, 2.5), line=True)
    p.append(Ellipse(90, 31, 11, 10, fur, grp=2, line=True))
    p.append(Ellipse(98, 35, 5.5, 4, pale, grp=2))
    p.append(Ellipse(84, 22, 3.5, 3.5, fur, grp=2))
    p.append(Ellipse(94, 21, 3.2, 3.2, fur, grp=2, shade=-0.1))
    return dict(prims=p, dots=[(46, 29, WHITE), (47, 29, BLACK), (50, 34, MAGENTA), (50, 35, BLACK),
                              (43, 26, ORANGE), (44, 25, ORANGE)])



@species
def wolf_bc(W, H):
    """Grey wolf, standing alert, head high, bushy tail down."""
    def saddle(p):
        if p['e'] < 0.85 and p['k'] >= 1 and p['v'] < 50 - 0.08 * abs(p['u'] - 46) and 18 < p['u'] < 72:
            return DARK_BLUE if p['k'] == 1 else None
        return None
    fur = Mat((DARK_BLUE, GREY, GREY, GREY, WHITE), bias=0.42)
    far = Mat((BLACK, DARK_BLUE, GREY), bias=0.35, gain=1.0)
    pale = Mat((GREY, WHITE, WHITE), bias=0.55)
    B = H
    p = []
    p.append(Tube([(22, 50, 6), (12, 62, 7.5), (9, 74, 7), (11, 84, 4)], fur))
    p += leg((74, 64), (72, 80), (70, B), 6, 4.5, 3.5, far, paw=(4.5, 2.5))
    p += leg((34, 62), (40, 78), (38, B), 7, 4.5, 3.5, far, paw=(4.5, 2.5))
    p.append(Ellipse(48, 56, 30, 13, fur, flat=0.9, grp=1))
    p.append(Ellipse(28, 54, 14, 14, fur, grp=1))
    p.append(Ellipse(72, 54, 15, 16, fur, grp=1))                     # chest / mane
    p.append(Ellipse(80, 62, 7, 9, pale, grp=1))
    p.append(Tube([(74, 48, 11), (82, 32, 8)], fur, grp=1))           # neck
    p.append(Ellipse(26, 62, 11, 12, fur, grp=3, line=True))
    p += leg((24, 66), (22, 80), (26, B), 8, 5, 3.5, fur, paw=(5, 2.5), grp=3)
    p += leg((80, 62), (82, 80), (84, B), 7, 5, 3.5, fur, paw=(5, 2.5), line=True)
    p.append(Ellipse(86, 26, 10, 8.5, fur, grp=2, line=True))         # head
    p.append(Tube([(92, 28, 5), (101, 31, 3.2)], fur, grp=2))         # muzzle
    p.append(Ellipse(94, 33, 6, 2.2, pale, grp=2))
    p.append(Poly([(77, 23), (78, 9), (86, 20)], fur, n=(-0.5, -0.4), grp=2))
    p.append(Poly([(85, 20), (89, 8), (93, 21)], fur, n=(-0.2, -0.4), grp=2, shade=-0.1))
    return dict(prims=p, dots=[(45, 24, YELLOW), (46, 24, BLACK), (51, 30, BLACK), (50, 32, BLACK)])



@species
def moose_bc(W, H):
    """Bull moose walking right: high shoulders, long drooping head, bell,
    broad palmate antlers; dark brown coat (magenta / olive mix), pale legs."""
    MIX = (MAGENTA, BROWN)                     # reads as a dark brown
    coat = Mat((BLACK, (BLACK, MAGENTA), MIX, MIX, MIX), bias=0.45, gain=1.2, rim=ORANGE)
    far = Mat((BLACK, (BLACK, MAGENTA), MIX), bias=0.35, gain=1.0, rim=MAGENTA)
    legm = Mat((BLACK, BLACK, GREY, GREY), bias=0.5, rim=WHITE,
               pat=lambda q: (MIX[(q['x'] + q['y']) & 1] if q['k'] >= 2 else BLACK) if q['v'] < 64 else None)
    ant = Mat((MAGENTA, ORANGE, ORANGE, PINK), bias=0.5, rim=PINK)
    B = H
    p = []
    p += leg((70, 54), (70, 68), (68, B), 5, 3.4, 2.6, far, paw=(3, 2))
    p += leg((30, 54), (38, 68), (36, B), 6, 3.4, 2.6, far, paw=(3, 2))
    p.append(Ellipse(46, 44, 32, 13, coat, flat=0.9, grp=1))
    p.append(Ellipse(66, 38, 18, 15, coat, grp=1))                     # shoulder hump
    p.append(Ellipse(24, 43, 12, 12, coat, grp=1))
    p.append(Tube([(15, 38, 2.5), (13, 44, 2)], coat, grp=1))         # tail stub
    p.append(Ellipse(24, 50, 9, 10, coat, grp=3, line=True))          # thigh
    p += leg((24, 56), (22, 68), (24, B), 6, 3.6, 2.6, legm, paw=(3, 2), grp=3)
    p.append(Ellipse(74, 50, 7, 9, coat, grp=4, line=True))
    p += leg((76, 56), (78, 68), (80, B), 5, 3.6, 2.6, legm, paw=(3, 2), grp=4)
    p.append(Tube([(76, 42, 9), (84, 36, 7)], coat, grp=2))           # neck
    p.append(Tube([(84, 34, 6), (94, 40, 5), (99, 46, 5.5)], coat, grp=2, line=True))   # head + muzzle
    p.append(Tube([(94, 40, 4.2), (99, 46, 4.6)], Mat((BLACK, MAGENTA, (MAGENTA, ORANGE)), bias=0.5, rim=ORANGE), grp=2))
    p.append(Tube([(86, 44, 2.4), (87, 54, 1.8)], coat, grp=2))       # bell
    p.append(Ellipse(80, 30, 4.5, 2.5, coat, ang=-35, grp=2))         # ear
    # far antler: a tip peeking out on the right; near palm: a broad shovel
    # sweeping up and back from the skull, short points along its rim
    g = 20
    p.append(Ellipse(90, 21, 8, 4.5, ant, ang=-40, shade=-0.3, grp=g + 1, line=True))
    p.append(Tube([(92, 18, 2.8), (96, 11, 2.4)], ant, shade=-0.3, grp=g + 1))
    for u0, v0, u1, v1 in ((56, 22, 50, 15), (60, 17, 56, 9), (67, 14, 66, 6), (74, 14, 76, 6)):
        p.append(Tube([(u0, v0, 3.8), (u1, v1, 3.0)], ant, grp=g, line=True))
    p.append(Tube([(85, 30, 3.5), (79, 25, 3.5)], ant, line=True, grp=g + 2))
    p.append(Ellipse(68, 21, 15, 7, ant, ang=-16, line=True, grp=g + 2))
    return dict(prims=p, dots=[(45, 37, BLACK), (49, 44, BLACK), (48, 43, BLACK)])



@species
def elephant(W, H):
    """Asian elephant in three-quarter view towards the right, trunk hanging
    and curling forward, small tusks, columnar legs."""
    hide = Mat((BLACK, DARK_BLUE, GREY, GREY, GREY, GREY), bias=0.55, gain=1.25, rim=WHITE)
    far = Mat((BLACK, DARK_BLUE, GREY), bias=0.35, gain=1.0, rim=GREY)
    tusk = Mat((GREY, WHITE, WHITE), bias=0.6)
    B = H + 3          # feet cut flat by the bottom edge
    p = []
    p.append(Tube([(8, 30, 1.5), (5, 46, 1.2), (6, 50, 2)], hide))
    p.append(Tube([(34, 52, 8), (34, B, 7.5)], far))
    p.append(Tube([(58, 54, 7.5), (60, B, 7)], far))
    p.append(Ellipse(38, 34, 31, 22, hide, flat=1.1, grp=1))
    p.append(Ellipse(48, 22, 20, 12, hide, grp=1))                     # high back
    p.append(Tube([(20, 50, 9.5), (20, 62, 8.5), (20, B, 8.5)], hide, line=True, grp=3))
    p.append(Tube([(50, 54, 8.5), (48, B, 8)], hide, line=True, grp=4))
    p.append(Tube([(72, 50, 8.5), (73, B, 8)], hide, line=True, grp=5))   # near front leg
    p.append(Ellipse(74, 27, 14, 15, hide, line=True, grp=2))            # head
    p.append(Ellipse(70, 15, 7, 5, hide, grp=2))                         # twin dome
    p.append(Tube([(82, 36, 6.5), (86, 48, 5), (86, 58, 3.8), (89, 65, 3), (94, 63, 2.4)], hide, line=True, grp=2))
    p.append(Ellipse(62, 30, 10, 14, hide, ang=10, line=True, shade=-0.22, grp=6))   # ear
    p.append(Tube([(78, 42, 2.4), (83, 49, 1.8), (88, 50, 1.2)], tusk, line=True, grp=7))
    return dict(prims=p, dots=[(39, 24, BLACK), (38, 23, WHITE)])



# ---------------- snakes
def coil(p, cx, cy, rx, ry, r, mat, back_first=True, grp=None, line=True, shade=0.0, a0=180, a1=540):
    """A horizontal ring of body seen from slightly above: the far (upper)
    half, then the near (lower) half over it."""
    g = grp if grp is not None else object()
    pts = arc(cx, cy, rx, ry, a0, a1, r, n=28)
    p.append(Tube(pts, mat, line=line, grp=id(g), shade=shade))


def sine_path(u0, u1, v0, amp, period, r0, r1, phase=0.0, n=24, taper=1.0):
    """Points along a sine; the radius grows from r0 to r1 over the first
    'taper' fraction of the length (the tail), then stays."""
    out = []
    for i in range(n + 1):
        t = i / n
        u = u0 + (u1 - u0) * t
        r = r0 + (r1 - r0) * min(1.0, t / taper) ** 0.7
        out.append((u, v0 + amp * math.sin(2 * math.pi * (u - u0) / period + phase), r))
    return out
def bands(period, frac, colour, dark=None, skip_belly=False):
    def pat(p):
        if p['e'] > 0.82:
            return None
        if (p['t'] % period) < period * frac:
            return dark if (dark is not None and p['k'] == 0) else colour
        return None
    return pat


def diamonds(period, w, dark, light):
    def pat(p):
        if p['e'] > 0.85:
            return None
        s = abs((p['t'] % period) - period / 2) / (period / 2) + abs(p['d']) * 1.1
        if s < w:
            return dark
        if s < w + 0.32:
            return light
        return None
    return pat


@species
def rattlesnake(W, H):
    """Western diamondback, coiled, neck raised in an S, rattle up behind."""
    scales = Mat((MAGENTA, ORANGE, ORANGE, PINK), bias=0.42, pat=diamonds(12, 0.55, MAGENTA, WHITE), rim=PINK)
    head = Mat((MAGENTA, ORANGE, ORANGE, PINK), bias=0.45)
    rattle = Mat((GREY, GREY, WHITE), bias=0.5,
                 pat=lambda q: BLACK if q['e'] < 0.9 and q['t'] % 3.5 < 1 else None)
    p = []
    p.append(Tube([(16, 38, 3.5), (10, 30, 3), (9, 22, 2.6)], scales))               # tail
    p.append(Tube([(9, 24, 4.4), (10, 11, 3.8)], rattle, line=True))
    p.append(Tube(arc(33, 35.5, 26, 6.5, 200, 520, 5.5, 5.5, n=28), scales, line=True))
    p.append(Tube(arc(35, 29, 17, 4.5, 190, 470, 5, 5, n=24), scales, line=True))
    p.append(Tube([(40, 30, 5), (50, 24, 4.6), (48, 16, 4.2), (40, 12, 4), (44, 6, 3.8)], scales, line=True))
    p.append(Ellipse(52, 6.5, 8, 4.5, head, line=True))
    return dict(prims=p, dots=[(27, 5, YELLOW), (28, 5, BLACK), (30, 8, MAGENTA), (31, 9, MAGENTA), (32, 8, MAGENTA)])



@species
def cobra(W, H):
    """Spectacled cobra reared up, hood spread, coils on the ground."""
    body = Mat((BLACK, MAGENTA, ORANGE, ORANGE), bias=0.45, rim=PINK)
    def throat(q):
        return MAGENTA if 18 < q['v'] < 40 and int(q['v']) % 7 < 2 else None
    belly = Mat((ORANGE, PINK, PINK, WHITE), bias=0.5, pat=throat)
    p = []
    p.append(Tube(arc(41, 75, 35, 7, 200, 520, 6.2, 6.2, n=28), body, line=True))
    p.append(Tube(arc(43, 66, 22, 5, 190, 480, 5.8, 5.8, n=24), body, line=True))
    p.append(Tube([(46, 66, 6.4), (38, 56, 6.4), (42, 46, 6.4), (41, 38, 7)], body, line=True))
    p.append(Tube([(46, 66, 3), (38, 56, 3), (42, 46, 3), (41, 40, 3)], belly, grp=5))
    p.append(Ellipse(41, 26, 21, 15, body, flat=1.6, line=True, grp=6))             # hood
    p.append(Tube([(41, 30, 13), (41, 40, 7)], body, grp=6))
    p.append(Ellipse(41, 28, 9, 13, belly, grp=6))
    p.append(Tube([(41, 36, 4.5), (41, 42, 3)], belly, grp=6))
    p.append(Ellipse(41, 11, 8.5, 6.5, body, grp=6, line=True))
    return dict(prims=p, dots=[(18, 10, YELLOW), (22, 10, YELLOW), (19, 10, BLACK), (21, 10, BLACK),
                              (20, 15, MAGENTA), (20, 16, MAGENTA), (19, 17, MAGENTA), (21, 17, MAGENTA)])




@species
def python(W, H):
    """Burmese python slithering in a slow S, thick body, head raised."""
    def blot(q):
        if q['e'] > 0.86:
            return None
        s = q['t'] % 16
        k = abs(s - 8) / 5.6 + 0.3 * q['d'] * q['d']
        if q['d'] < 0.15 and k < 1.0:                       # dorsal saddle
            return BLACK if k > 0.72 else MAGENTA
        s2 = (q['t'] + 8) % 16
        if q['d'] > 0.35 and abs(s2 - 8) < 2.4:             # lateral blotch
            return BLACK if abs(s2 - 8) > 1.4 else MAGENTA
        return None
    skin = Mat((BROWN, ORANGE, ORANGE, PINK), bias=0.45, pat=blot, rim=ORANGE)
    head = Mat((BROWN, ORANGE, ORANGE, PINK), bias=0.45, rim=ORANGE)
    p = []
    path = sine_path(2, 74, 17, 2.0, 56, 1.8, 8.5, phase=0.6, taper=0.4)
    p.append(Tube(path, skin))
    p.append(Tube([path[-1], (82, 12, 6), (85, 9, 5)], skin, grp=9))
    p.append(Ellipse(89, 7.5, 7.5, 4.6, head, line=True, grp=9))
    return dict(prims=p, dots=[(45, 6, BLACK), (46, 6, YELLOW)])





@species
def adder(W, H):
    """Death adder: short, very thick, lying in a loose flat coil, head
    resting on the body, pale tail lure raised beside it. Grey, rust bands."""
    def bars(q):
        if q['e'] > 0.82:
            return None
        if (q['t'] % 9) < 3.4:
            return MAGENTA if q['k'] < 2 else ORANGE
        return None
    skin = Mat((DARK_BLUE, GREY, GREY, GREY, GREY, WHITE), bias=0.55, pat=bars, rim=WHITE, hi=0.25)
    head = Mat((DARK_BLUE, GREY, GREY, GREY), bias=0.5, rim=WHITE)
    p = []
    p.append(Tube([(12, 30, 2.6), (8, 22, 2.2), (11, 14, 2)], Mat((MAGENTA, ORANGE, ORANGE, WHITE), bias=0.6), line=True))
    p.append(Tube(arc(31, 34.5, 26, 5.5, 160, 520, 7.2, 7.2, n=30), skin, line=True))
    p.append(Tube(arc(31, 29, 14, 3, 200, 400, 6, 6, n=14), skin, line=True))
    p.append(Tube([(50, 39, 7), (59, 32, 6), (60, 24, 5.4)], skin, line=True, grp=4))
    p.append(Poly([(52, 18), (62, 13), (70, 15), (71, 21), (62, 27), (52, 25)], head, n=(-0.2, -0.4), line=True, grp=4))
    return dict(prims=p, dots=[(31, 17, YELLOW), (32, 17, BLACK), (35, 19, MAGENTA), (36, 19, MAGENTA)])




@species
def ferdelance(W, H):
    """Fer-de-lance: loose S on the ground, lance head lifted. Olive-brown,
    dark triangles edged pale."""
    def tri(q):
        if q['e'] > 0.86:
            return None
        s = q['t'] % 12
        k = abs(s - 6) / 6            # 0 at the centre of a mark
        if k < 0.6 - 0.4 * abs(q['d']):
            return BLACK
        if k < 0.8 - 0.4 * abs(q['d']):
            return GREY
        return None
    skin = Mat((DARK_GREEN, BROWN, BROWN, YELLOW), bias=0.45, pat=tri, rim=YELLOW)
    head = Mat((DARK_GREEN, BROWN, BROWN, YELLOW), bias=0.45)
    p = []
    path = sine_path(2, 60, 22, 4.0, 46, 1.6, 5.6, phase=0.5, taper=0.45)
    p.append(Tube(path, skin))
    p.append(Tube([path[-1], (68, 16, 5.2), (70, 11, 4.6)], skin, line=True, grp=1))
    p.append(Poly([(66, 6), (80, 5), (87, 9), (80, 13), (66, 15)], head, n=(-0.2, -0.5), line=True))
    return dict(prims=p, dots=[(37, 7, YELLOW), (38, 7, BLACK)])




@species
def anaconda(W, H):
    """Green anaconda: two heavy loops on the ground, a third over them,
    head lifted on the right."""
    def spots(q):
        if q['e'] > 0.86:
            return None
        s = q['t'] % 11
        side = q['d'] > 0
        if (2 < s < 7.5) if side else (7 < s or s < 1.5):
            if abs(abs(q['d']) - 0.4) < 0.3:
                return BLACK
        return None
    skin = Mat((BLACK, DARK_GREEN, DARK_GREEN, GREEN), bias=0.48, pat=spots, rim=GREEN)
    head = Mat((BLACK, DARK_GREEN, DARK_GREEN, GREEN), bias=0.5)
    p = []
    p.append(Tube(arc(26, 34, 22, 7, 180, 540, 7, 7, n=28), skin, line=True))
    p.append(Tube(arc(62, 34, 22, 7, 180, 540, 7, 7, n=28), skin, line=True))
    p.append(Tube(arc(44, 24, 26, 5, 160, 400, 6.8, 6.5, n=24), skin, line=True))
    p.append(Tube([(68, 26, 6.5), (74, 18, 5.6), (76, 12, 5)], skin, line=True, grp=1))
    p.append(Ellipse(80, 9, 9, 5, head, line=True, grp=1))
    return dict(prims=p, dots=[(41, 7, YELLOW), (42, 7, BLACK)])




@species
def crocodile(W, H):
    """Nile crocodile, belly on the ground, legs splayed, jaws open,
    dorsal scutes on the silhouette."""
    def bands(q):
        if q['e'] < 0.8 and q['k'] >= 1 and q['u'] < 98 and int((q['u'] + 0.5 * q['v']) / 7) % 3 == 0:
            return BLACK if q['k'] == 1 else DARK_GREEN
        return None
    hide = Mat((BLACK, DARK_GREEN, BROWN, BROWN), bias=0.45, pat=bands, rim=GREEN)
    head = Mat((BLACK, DARK_GREEN, BROWN, BROWN), bias=0.48, rim=GREEN)
    far = Mat((BLACK, BLACK, DARK_GREEN), bias=0.4, rim=DARK_GREEN)
    belly = Mat((BROWN, YELLOW), bias=0.5)
    B = H
    p = []
    p.append(Tube([(100, 48, 5), (108, 52, 4), (110, B - 2, 3.5)], far))
    p.append(Tube([(44, 48, 5), (36, 52, 4), (34, B - 2, 3.5)], far))
    for u in range(12, 98, 6):                                     # scutes
        top = 34 if u > 36 else 34 + (36 - u) * 0.33
        p.append(Poly([(u - 2.6, top + 5), (u, top), (u + 2.6, top + 5)], hide, n=(-0.2, -0.6), grp=1))
    p.append(Tube([(2, 54, 1.8), (14, 51, 4.5), (30, 47, 8), (44, 45, 10)], hide, grp=1))
    p.append(Ellipse(70, 46, 34, 10.5, hide, flat=1.1, grp=1))
    p.append(Ellipse(72, 55, 26, 2.5, belly, grp=1))
    p.append(Tube([(54, 50, 6), (46, 54, 5), (48, B - 2, 3.5)], hide, line=True, grp=3))
    p.append(Ellipse(45, B - 2, 6, 2, hide, grp=3))
    p.append(Tube([(92, 50, 6), (100, 54, 5), (102, B - 2, 3.5)], hide, line=True, grp=4))
    p.append(Ellipse(105, B - 2, 6, 2, hide, grp=4))
    p.append(Poly([(108, 46), (136, 36), (138, 50), (108, 52)], Mat((MAGENTA,), bias=0.6, rim=MAGENTA), grp=8))
    p.append(Ellipse(108, 44, 11, 8, head, grp=2, line=True))
    p.append(Poly([(104, 40), (138, 30), (141, 33), (110, 46)], head, n=(-0.3, -0.7), grp=2, line=True))
    p.append(Ellipse(110, 37, 3.5, 2.5, head, grp=2))                    # eye bump
    p.append(Poly([(108, 48), (138, 49), (141, 52), (108, 55)], head, n=(0.0, 0.3), grp=7, line=True))
    teeth = [(58, 41), (61, 40), (64, 39), (67, 38), (59, 48), (62, 48), (65, 48), (68, 48)]
    return dict(prims=p, dots=[(55, 36, YELLOW), (56, 36, BLACK)] + [(x, y, WHITE) for x, y in teeth])




# ---------------------------------------------------------------- outputs
def draw(name):
    W, H = size(name)
    spec = SPECIES[name](W, H)
    spec.update(w=W, h=H)
    g = render(spec)
    # Settle on the ground: drop empty bottom rows (the anchor is the
    # bottom opaque row of the original).
    while not any(c >= 0 for c in g[-1]):
        g = [[-1] * W] + g[:-1]
    # Constraints: same width, bottom row = ground anchor, height <= original.
    assert len(g[0]) == W and len(g) == H
    assert any(c >= 0 for c in g[-1]), f'{name}: nothing on the ground row'
    return g


def decimate(grid, shift):
    """The distant billboard's sampling (dhgr_sprites.convert, sprites.s):
    column j << shift, rows with (base - y) % (1 << shift) == 0."""
    s = 1 << shift
    H, W = len(grid), len(grid[0])
    rows = [grid[y] for y in range(H) if (H - 1 - y) % s == 0]
    return [[r[x] for x in range(0, W, s)] for r in rows]


def check_window(grid):
    return len(R.column_runs(grid))


def main(names=None):
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((SRC / 'manifest.json').read_text())['sprites']
    review = bool(names)
    names = names or list(SPECIES)
    data, cost, cells = {}, {}, []
    for name in names:
        new = draw(name)
        codes = R.load(name)
        old = R.before(name, codes)
        if review:
            cells.append(R.side(R.panel(old, 'sky'), R.panel(new, 'sky'), R.panel(new, 'black')))
            continue
        R.write_png(OUT / f'{name}.png', R.views(new))
        cols = sorted({c for r in new for c in r if c >= 0})
        data[name] = dict(width=len(new[0]), height=len(new), base_row=manifest[name]['original_top_row'] + len(new) - 1,
                          rows=new, colours=cols)
        orig = (SRC / f'{name}.bin').read_bytes()
        pix, mask = R.nibble_bytes(new)
        runs = R.column_runs(new)
        cost[name] = dict(original=len(orig), original_lz=min(len(orig), R.lz(orig)),
                          nibble=len(pix) + len(mask), nibble_lz=min(len(pix) + len(mask), R.lz(pix + mask)),
                          runs=len(runs), runs_lz=min(len(runs), R.lz(runs)), colours=len(cols))
        far = R.stack(R.panel(decimate(new, 1), 'sky'), R.panel(decimate(new, 2), 'sky'))
        cell = R.side(R.views(old), R.views(new), far)
        lab = R.canvas(len(cell[0]), 16)
        R.text(lab, name.replace('_bc', '').replace('_', ' '), 2, 2)
        cells.append(R.stack(lab, cell, gap=0))
    if review:
        global_sx = (8, 4)
        R.SX, R.SY = global_sx
        cells = []
        for name in names:
            new = draw(name)
            old = R.before(name, R.load(name))
            cells.append(R.side(R.panel(old, 'sky'), R.panel(new, 'sky'), R.panel(new, 'black')))
        R.write_png(OUT / 'review.png', R.stack(*cells, gap=8))
        return
    tot = {k: sum(c[k] for c in cost.values()) for k in next(iter(cost.values()))}
    cost['TOTAL'] = tot
    (OUT / 'animals.json').write_text(json.dumps(dict(
        note='rows: DHGR colour numbers (dhgr_palette), -1 transparent; one entry = one DHGR colour '
             'pixel (displayed 2:1); width = original columns, last row = ground anchor (base_row on '
             'the 192-row original frame). cost in bytes: original = 2-bit column stream (.bin); '
             'nibble = 4-bit bitmap + 1-bit mask; runs = column runs as dhgr_sprites (2 bytes per run '
             'of one colour, header + offsets); _lz = pack_boot.compress + 2-byte window.',
        animals=data, cost=cost), separators=(',', ':')))
    MAXW, GAP = 2600, 24
    rows, line = [], []

    def flush():
        hh = max(len(c) for c in line) + GAP
        band = R.canvas(MAXW, hh)
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
    R.write_png(OUT / 'sheet.png', rows)
    print(f"{'sprite':12} {'orig':>6} {'orig+lz':>8} {'4bit':>6} {'4bit+lz':>8} {'runs':>6} {'runs+lz':>8} col")
    for n, c in cost.items():
        print(f"{n:12} {c['original']:6} {c['original_lz']:8} {c['nibble']:6} {c['nibble_lz']:8} "
              f"{c['runs']:6} {c['runs_lz']:8} {c['colours']:3}")


if __name__ == '__main__':
    main(sys.argv[1:] or None)
