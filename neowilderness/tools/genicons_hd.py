#!/usr/bin/env python3
"""Neowilderness menu icons, high-resolution set; run with Python 3 from anywhere.

Each icon is 28 x 24 DHGR colour pixels, any of the 16 colours per pixel.
A DHGR colour pixel displays 2:1 (wide), so shapes are designed in display
units: u = 2 * x + 1 (0..56), v = y + 0.5 (0..24); a circle of radius r is
r / 2 pixels wide and r pixels tall. Shapes are filled with a colour ramp
(dark -> light) shaded for a light coming from the top left; a black
separation line is carved where a new part overlaps an earlier one.

Outputs, in build/icons_hd/: <name>.png (x8 horizontally, x4 vertically),
sheet.png (labelled grid, black background), compare.png (old 14 x 12 set
from tools/genicons.py next to the new one, same box size) and icons.json
(names mapped to 24 rows of 28 colour numbers).
"""

import json
import math
from pathlib import Path

from dhgr_palette import (BLACK, MAGENTA, DARK_BLUE, PURPLE, DARK_GREEN, GREY1,
                          MEDIUM_BLUE, LIGHT_BLUE, BROWN, ORANGE, GREY2, PINK,
                          GREEN, YELLOW, AQUA, WHITE)
from genicons import CRAFT, TOOLS, FONT, decode_art, write_png

W, H = 28, 24

# Ramps, dark -> light. GREY1 and GREY2 render identically, so metal gets
# its depth from dark blue below and light blue / white above.
STEEL = (DARK_BLUE, GREY1, GREY1, WHITE)
WOOD = (MAGENTA, ORANGE, ORANGE, ORANGE, PINK)
DARKWOOD = (MAGENTA, ORANGE, ORANGE, PINK)
HEMP = (BROWN, ORANGE, YELLOW)
LEAF = (DARK_GREEN, GREEN, AQUA)
BLUE = (DARK_BLUE, MEDIUM_BLUE, LIGHT_BLUE, WHITE)
SNOW = (MEDIUM_BLUE, LIGHT_BLUE, WHITE)
EARTH = (MAGENTA, BROWN, ORANGE, PINK)
RED = (MAGENTA, PINK)
FIRE = (MAGENTA, ORANGE, YELLOW, WHITE)
SKIN = (MAGENTA, ORANGE, PINK)
CLOTH = (GREY1, LIGHT_BLUE, WHITE)
STONE = (DARK_BLUE, GREY1, WHITE)

LIGHT = (-0.55, -0.62, 0.56)
_n = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _n for c in LIGHT)


def level(ramp, i):
    """Ramp colour for an intensity 0..1."""
    k = int(i * len(ramp))
    return ramp[max(0, min(len(ramp) - 1, k))]


class Icon:
    def __init__(self):
        self.p = [[BLACK] * W for _ in range(H)]

    # ---- masks (sets of pixels), shapes in display units -----------------
    @staticmethod
    def mask(pred):
        out = set()
        for y in range(H):
            for x in range(W):
                n = sum(pred(2 * x + du, y + dv)
                        for du in (0.5, 1.5) for dv in (0.25, 0.75))
                if n >= 2:
                    out.add((x, y))
        return out

    def ellipse(self, cu, cv, ru, rv):
        return self.mask(lambda u, v: ((u - cu) / ru) ** 2 + ((v - cv) / rv) ** 2 <= 1)

    def rect(self, u0, v0, u1, v1):
        return self.mask(lambda u, v: u0 <= u <= u1 and v0 <= v <= v1)

    def poly(self, pts):
        def inside(u, v):
            c = False
            n = len(pts)
            for i in range(n):
                (a, b), (cc, d) = pts[i], pts[(i + 1) % n]
                if (b > v) != (d > v) and u < (cc - a) * (v - b) / (d - b) + a:
                    c = not c
            return c
        return self.mask(inside)

    def capsule(self, p0, p1, w0, w1=None):
        """Thick segment, half-width w0 at p0 and w1 at p1 (display units)."""
        w1 = w0 if w1 is None else w1
        (a, b), (c, d) = p0, p1
        L2 = (c - a) ** 2 + (d - b) ** 2

        def inside(u, v):
            t = max(0.0, min(1.0, ((u - a) * (c - a) + (v - b) * (d - b)) / L2))
            pu, pv = a + t * (c - a), b + t * (d - b)
            return (u - pu) ** 2 + (v - pv) ** 2 <= (w0 + t * (w1 - w0)) ** 2
        return self.mask(inside)

    # ---- painting ---------------------------------------------------------
    def separate(self, m, col=BLACK):
        ring = set()
        for (x, y) in m:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if q not in m and 0 <= q[0] < W and 0 <= q[1] < H:
                    ring.add(q)
        for (x, y) in ring:
            if self.p[y][x] != BLACK:
                self.p[y][x] = col

    def fill(self, m, ramp, shade='edge', sep=True, **kw):
        """shade: 'flat' (mid colour), 'edge' (lit top/left rim, dark
        bottom/right rim), 'sphere' (cu, cv, ru, rv) or 'cyl' (p0, p1, r)."""
        if isinstance(ramp, int):
            ramp = (ramp,)
        if sep:
            self.separate(m, kw.get('sepcol', BLACK))
        for (x, y) in m:
            u, v = 2 * x + 1, y + 0.5
            if shade == 'flat':
                c = ramp[kw.get('k', len(ramp) // 2)]
            elif shade == 'edge':
                up = (x, y - 1) not in m
                lf = (x - 1, y) not in m
                dn = (x, y + 1) not in m
                rt = (x + 1, y) not in m
                mid = kw.get('k', max(0, len(ramp) // 2 - (len(ramp) > 3)))
                if (dn or rt) and not (up or lf):
                    c = ramp[0]
                elif (up or lf) and not (dn or rt):
                    c = ramp[min(len(ramp) - 1, mid + 1)]
                else:
                    c = ramp[mid]
            elif shade == 'sphere':
                cu, cv, ru, rv = kw['c']
                du, dv = (u - cu) / ru, (v - cv) / rv
                r2 = min(1.0, du * du + dv * dv)
                n = (du, dv, math.sqrt(1 - r2))
                i = sum(a * b for a, b in zip(n, LIGHT))
                c = level(ramp, (i + kw.get('bias', 0.0)) * kw.get('gain', 1.0))
            elif shade == 'cyl':
                (a, b), (cc, d), r = kw['axis']
                L = math.hypot(cc - a, d - b)
                pu, pv = -(d - b) / L, (cc - a) / L      # perpendicular
                t = ((u - a) * pu + (v - b) * pv) / r
                t = max(-1.0, min(1.0, t))
                n = (pu * t, pv * t, math.sqrt(1 - t * t))
                i = sum(p * q for p, q in zip(n, LIGHT))
                c = level(ramp, (i + kw.get('bias', 0.0)) * kw.get('gain', 1.0))
            elif callable(shade):
                c = shade(u, v, x, y)
            self.p[y][x] = c
        return m

    def px(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.p[y][x] = c

    def pxs(self, pts, c):
        for x, y in pts:
            self.px(x, y, c)

    def line(self, x0, y0, x1, y1, c):
        """Bresenham line in pixel coordinates."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.px(x0, y0, c)
            if (x0, y0) == (x1, y1):
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def outline(self, col, only_black=True):
        """Ring of col around everything drawn (on black background)."""
        filled = {(x, y) for y in range(H) for x in range(W) if self.p[y][x] != BLACK}
        for (x, y) in list(filled):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if q not in filled and 0 <= q[0] < W and 0 <= q[1] < H:
                    self.p[q[1]][q[0]] = col


# ---------------------------------------------------------------------------
# The icons.

def axe(c):
    c.fill(c.capsule((21, 23.5), (29, 3), 2.3), WOOD, 'cyl', axis=((21, 23.5), (29, 3), 2.3))
    head = c.poly([(12, 0.5), (16, 2.3), (22, 3.2), (26, 2.2), (36, 2.2), (37, 3.6), (37, 7.2),
                   (36, 8.6), (26, 8.6), (22, 8.2), (16, 10.2), (12, 13), (9.5, 9.5), (9, 4)])
    c.fill(head, STEEL, 'edge')
    for y in range(0, 14):
        row = sorted(x for (x, yy) in head if yy == y)
        if row:
            c.px(row[0], y, WHITE)
    c.pxs(((7, 2), (8, 2), (12, 3), (13, 3)), WHITE)
    c.pxs(((14, 0), (14, 1)), PINK)      # handle top through the eye
    c.px(15, 1, MAGENTA)


def knife(c):
    a, b = (5, 22.8), (55, 0.6)
    du, dv = b[0] - a[0], b[1] - a[1]
    L = math.hypot(du, dv)
    tu, tv = du / L, dv / L
    nu, nv = -tv, tu                       # points down-right (edge side)

    def at(t, o):
        return (a[0] + du * t + nu * o, a[1] + dv * t + nv * o)
    blade = [at(0.42, -1.8), at(0.96, -0.6), at(1.0, 0.3), at(0.88, 2.4), at(0.7, 3.6),
             at(0.5, 3.8), at(0.42, 3.4)]
    c.fill(c.poly(blade), STEEL, 'edge')
    p0, p1 = at(0.45, -1.2), at(0.93, -0.3)
    c.line(int(p0[0] // 2), int(p0[1]), int(p1[0] // 2), int(p1[1]), WHITE)
    g0, g1 = at(0.39, -4), at(0.39, 5.5)
    c.fill(c.capsule(g0, g1, 1.3), (BROWN, ORANGE, YELLOW), 'flat', k=1)
    h0, h1 = at(0.02, 0.8), at(0.36, 0.8)
    c.fill(c.capsule(h0, h1, 2.4), DARKWOOD, 'cyl', axis=(h0, h1, 2.4))
    for t in (0.12, 0.26):
        p = at(t, 0.0)
        c.px(int(p[0] // 2), int(p[1]), YELLOW)


def rope(c):
    # coil seen from above: a spiral of two turns, twisted strand
    cu, cv, ru, rv = 27, 11.8, 26, 11.6
    s0, pitch, half, turns = 0.94, 0.37, 0.12, 2.05

    def strand(u, v):
        du, dv = (u - cu) / ru, (v - cv) / rv
        rho = math.hypot(du, dv)
        phi = (math.atan2(dv, du) - 0.6) % (2 * math.pi)
        for k in range(4):
            a = phi + 2 * math.pi * k
            if a > turns * 2 * math.pi:
                break
            s = s0 - pitch * a / (2 * math.pi)
            if abs(rho - s) <= half:
                return (rho - s) / half, du / max(rho, 1e-3), dv / max(rho, 1e-3)
        return None

    m = c.mask(lambda u, v: strand(u, v) is not None)

    def shade(u, v, x, y):
        t, cx, cy = strand(u, v) or (0.0, 0.0, 0.0)
        nz = math.sqrt(max(0.0, 1 - t * t))
        i = nz * LIGHT[2] + t * (cx * LIGHT[0] + cy * LIGHT[1]) * 1.2
        if (x + y) % 3 == 0:
            return MAGENTA if i < 0.8 else ORANGE
        return YELLOW if i > 0.8 else ORANGE if i > 0.15 else MAGENTA
    c.fill(m, HEMP, shade)
    tail = c.capsule((48, 15), (55, 23.5), 1.3)
    c.fill(tail, HEMP, lambda u, v, x, y: MAGENTA if (x + y) % 3 == 0 else ORANGE)


def matches(c):
    # sleeve in 3/4 view, drawer pulled out to the right, one burning match
    top = c.poly([(2, 11), (26, 11), (32, 6), (8, 6)])
    c.fill(top, (PINK,), 'flat', k=0)
    front = c.rect(2, 11, 26, 21)
    c.fill(front, (MAGENTA,), lambda u, v, x, y: BROWN if y in (18, 19) else MAGENTA)
    tray = c.poly([(26, 12), (40, 12), (46, 7), (32, 7)])
    c.fill(tray, (ORANGE,), 'flat', k=0)
    inner = c.poly([(28, 11.5), (39, 11.5), (43.5, 7.8), (33, 7.8)])
    c.fill(inner, (BLACK,), 'flat', k=0, sep=False)
    for x, y in ((16, 10), (18, 10), (17, 9), (19, 9), (20, 10), (21, 9)):
        c.px(x, y, MAGENTA)
        if c.p[y + 1][x] == BLACK and y + 1 <= 11:
            c.px(x, y + 1, YELLOW)
    dfront = c.rect(26, 12, 40, 19)
    c.fill(dfront, (ORANGE,), 'flat', k=0, sep=False)
    c.line(13, 12, 19, 12, PINK)
    c.pxs(((9, 7), (8, 8), (9, 8), (10, 8), (9, 9)), ORANGE)
    c.px(9, 8, YELLOW)
    # burning match
    c.line(25, 22, 25, 11, YELLOW)
    c.line(26, 22, 26, 11, ORANGE)
    c.pxs(((25, 10), (26, 10)), MAGENTA)
    flame = c.poly([(51, -0.5), (55, 4), (55.5, 7.5), (51, 9.8), (46.5, 7.5), (47, 4)])
    c.fill(flame, (ORANGE,), 'flat', k=0, sep=False)
    inner = c.poly([(51, 3), (53.5, 6), (51, 9), (48.5, 6)])
    c.fill(inner, (YELLOW,), 'flat', k=0, sep=False)
    c.pxs(((25, 7), (25, 6)), WHITE)


def flashlight(c):
    body = c.capsule((3, 13), (26, 13), 4.2)
    c.fill(body, BLUE, 'cyl', axis=((3, 13), (26, 13), 4.2))
    neck = c.poly([(25, 8.8), (31, 5.5), (31, 20.5), (25, 17.2)])
    c.fill(neck, BLUE, 'cyl', axis=((25, 13), (31, 13), 7), sep=False)
    head = c.rect(31, 5, 37, 21)
    c.fill(head, STEEL, 'cyl', axis=((31, 13), (37, 13), 8))
    lens = c.rect(37, 6, 39, 20)
    c.fill(lens, (YELLOW, WHITE), 'flat', k=1, sep=False)
    c.fill(c.rect(14, 7.2, 19, 8.8), (ORANGE,), 'flat', k=0, sep=False)
    for x in (4, 6, 8):
        for y in range(11, 16):
            c.px(x, y, DARK_BLUE)
    for y in range(H):
        for x in range(20, W):
            u, v = 2 * x + 1, y + 0.5
            if u > 41 and abs(v - 13) < 6 + (u - 41) * 0.45 and (x + y) % 2 == 0:
                c.px(x, y, YELLOW if abs(v - 13) < 3 + (u - 41) * 0.2 else ORANGE)


def compass(c):
    cu, cv, r = 28, 12.5, 11
    case = c.ellipse(cu, cv, 22, 11)
    c.fill(case, (BROWN, ORANGE, YELLOW, WHITE), 'sphere', c=(cu, cv, 22, 11), gain=1.3)
    face = c.ellipse(cu, cv, 17, 8.5)
    c.fill(face, (DARK_BLUE,), 'flat', k=0)
    # ticks N E S W
    for x, y in ((13, 5), (13, 19), (6, 12), (21, 12)):
        c.px(x, y, WHITE)
    for x, y in ((9, 7), (18, 7), (9, 17), (18, 17)):
        c.px(x, y, MEDIUM_BLUE)
    # needle: red north, white south, tilted
    north = c.poly([(36, 5), (30.5, 13.5), (25.5, 11.5)])
    c.fill(north, (MAGENTA, ORANGE), 'flat', k=1, sep=False)
    c.line(17, 6, 14, 11, MAGENTA)
    south = c.poly([(20, 20), (25.5, 11.5), (30.5, 13.5)])
    c.fill(south, (LIGHT_BLUE, WHITE), 'flat', k=1, sep=False)
    c.px(13, 12, YELLOW)
    # bail ring on top
    c.px(13, 0, YELLOW)
    c.px(14, 0, ORANGE)
    c.px(12, 0, ORANGE)
    # glass glint
    c.px(9, 9, LIGHT_BLUE)
    c.px(10, 8, LIGHT_BLUE)


def fishing(c):
    rod_tip = (50, 1)
    rod = c.capsule((6, 23), rod_tip, 1.4, 0.6)
    c.fill(rod, (BROWN, ORANGE, YELLOW), 'flat', k=1)
    grip = c.capsule((4, 23.5), (14, 18), 1.8)
    c.fill(grip, (MAGENTA, ORANGE), 'cyl', axis=((4, 23.5), (14, 18), 1.8))
    reel = c.ellipse(15, 21, 4, 3)
    c.fill(reel, STEEL, 'sphere', c=(15, 21, 4, 3))
    # line hanging from the tip
    c.line(25, 1, 25, 13, WHITE)
    # bobber
    bob = c.ellipse(51, 14.5, 4.5, 3.6)
    c.fill(bob, (WHITE,), 'flat', k=0, sep=False)
    low = {(x, y) for (x, y) in bob if y >= 15}
    c.fill(low, (MAGENTA, ORANGE), 'flat', k=0, sep=False)
    c.px(24, 14, PINK)
    # hook below the bobber
    c.line(25, 18, 25, 21, LIGHT_BLUE)
    c.pxs(((24, 22), (23, 21), (23, 20)), LIGHT_BLUE)
    c.px(25, 22, LIGHT_BLUE)


def stove(c):
    can = c.mask(lambda u, v: (abs(u - 28) <= 12 and 16 <= v <= 23.5) or
                 ((u - 28) / 12) ** 2 + ((v - 16) / 3.5) ** 2 <= 1)
    c.fill(can, (MEDIUM_BLUE,), lambda u, v, x, y: DARK_BLUE if u > 33 else MEDIUM_BLUE)
    c.line(10, 15, 10, 22, LIGHT_BLUE)
    c.line(11, 14, 11, 22, WHITE)
    c.line(9, 19, 18, 19, DARK_BLUE)
    c.fill(c.rect(24, 12, 32, 13.5), STEEL, 'cyl', axis=((28, 12), (28, 13.5), 4))
    burner = c.mask(lambda u, v: ((u - 28) / 11) ** 2 + ((v - 11) / 1.6) ** 2 <= 1)
    c.fill(burner, STEEL, 'flat', k=1)
    c.line(9, 10, 12, 10, WHITE)
    # pot supports
    c.pxs(((7, 8), (8, 9), (8, 10), (20, 8), (19, 9), (19, 10)), GREY1)
    c.pxs(((6, 8), (21, 8)), WHITE)
    # flame: tall centre tongue, two side tongues
    for pts, col in (
        ([(28, -0.5), (31, 3), (32.5, 6), (34.5, 3), (35.5, 7), (34, 10), (22, 10), (20.5, 7),
          (21.5, 3), (23.5, 6), (25, 3)], ORANGE),
        ([(28, 3), (30.5, 6), (31, 10), (25, 10), (25.5, 6)], YELLOW),
        ([(28, 6.5), (29.5, 8.5), (29, 10), (27, 10), (26.5, 8.5)], WHITE),
    ):
        c.fill(c.poly(pts), (col,), 'flat', k=0, sep=False)
    for x in (11, 12, 15, 16):
        c.px(x, 10, LIGHT_BLUE)


def utensils(c):
    # fork, knife, spoon side by side
    for x in (3, 5, 7):
        c.line(x, 0, x, 5, GREY1)
        c.px(x, 0, WHITE)
    c.line(3, 6, 7, 6, GREY1)
    c.line(4, 7, 6, 7, GREY1)
    c.px(3, 6, WHITE)
    c.line(5, 8, 5, 13, GREY1)
    c.line(4, 14, 4, 22, WHITE)
    c.line(5, 14, 5, 22, GREY1)
    c.line(6, 14, 6, 22, DARK_BLUE)
    c.pxs(((5, 23), (4, 23)), DARK_BLUE)
    # knife
    blade = c.poly([(27, 0.5), (31, 1.5), (31.5, 12.5), (25, 12.5), (25, 4)])
    c.fill(blade, STEEL, 'edge')
    c.line(12, 2, 12, 12, WHITE)
    hnd = c.capsule((28.5, 14), (28.5, 22.5), 2.6)
    c.fill(hnd, DARKWOOD, 'cyl', axis=((28.5, 14), (28.5, 22.5), 2.6))
    c.pxs(((14, 16), (14, 20)), YELLOW)
    # spoon
    bowl = c.ellipse(47, 5.5, 6.5, 5.5)
    c.fill(bowl, STEEL, 'sphere', c=(47, 5.5, 6.5, 5.5), gain=1.0)
    c.pxs(((22, 2), (22, 3)), WHITE)
    c.line(23, 11, 23, 14, GREY1)
    c.line(22, 15, 22, 22, WHITE)
    c.line(23, 15, 23, 22, GREY1)
    c.line(24, 15, 24, 22, DARK_BLUE)
    c.pxs(((22, 23), (23, 23)), DARK_BLUE)


def gun(c):
    # stock
    stock = c.poly([(1, 13), (14, 10.5), (22, 10.5), (22, 14), (14, 15), (6, 20), (1, 20)])
    c.fill(stock, DARKWOOD, 'edge')
    fore = c.poly([(22, 10.5), (40, 10.5), (40, 13.5), (22, 14)])
    c.fill(fore, DARKWOOD, 'edge')
    barrel = c.rect(20, 7.5, 55, 9.8)
    c.fill(barrel, STEEL, 'cyl', axis=((20, 8.6), (55, 8.6), 1.3))
    receiver = c.rect(18, 7, 28, 12)
    c.fill(receiver, STEEL, 'edge')
    scope = c.capsule((20, 4), (34, 4), 1.6)
    c.fill(scope, (DARK_BLUE, MEDIUM_BLUE, LIGHT_BLUE), 'cyl', axis=((20, 4), (34, 4), 1.6))
    c.pxs(((12, 6), (15, 6)), GREY1)
    # trigger guard
    c.pxs(((10, 14), (10, 15), (11, 16), (12, 16), (13, 15), (13, 14)), GREY1)
    c.px(11, 14, LIGHT_BLUE)
    c.px(27, 7, WHITE)


def tent(c):
    F, FL, FR = (38, 1), (26, 21), (53, 21)
    B, BL = (16, 4), (3, 19)
    side = c.poly([B, F, FL, BL])
    c.fill(side, (ORANGE,), 'flat', k=0)
    c.line(8, 4, 18, 1, YELLOW)
    c.line(8, 5, 18, 2, YELLOW)
    front = c.poly([F, FR, FL])
    c.fill(front, (MAGENTA,), 'flat', k=0)
    door = c.poly([(39, 7), (46, 21), (33, 21)])
    c.fill(door, (BLACK,), 'flat', k=0, sep=False)
    c.line(19, 7, 16, 20, ORANGE)
    c.line(19, 7, 22, 20, PINK)
    # seams on the side panel
    c.line(13, 3, 6, 18, BROWN)
    # ground
    c.line(1, 22, 27, 22, BROWN)
    c.line(2, 23, 26, 23, DARK_GREEN)
    # guy rope and peg
    c.line(26, 12, 27, 21, LIGHT_BLUE)


def canteen(c):
    body = c.ellipse(26, 14.5, 18, 9)
    c.fill(body, LEAF, 'sphere', c=(26, 14.5, 18, 9), gain=1.25)
    # rim seam
    c.line(5, 14, 21, 14, DARK_GREEN)
    neck = c.rect(22, 3, 30, 6)
    c.fill(neck, STEEL, 'cyl', axis=((22, 4.5), (30, 4.5), 4))
    cap = c.rect(21, 0.5, 31, 3)
    c.fill(cap, STEEL, 'cyl', axis=((21, 1.7), (31, 1.7), 5))
    # strap
    strap = c.mask(lambda u, v: 0.0 < (u - 46) ** 2 / 64 + (v - 6) ** 2 / 36 <= 1 and
                   ((u - 46) ** 2 / 36 + (v - 6) ** 2 / 16 >= 1) and u > 34)
    c.fill(strap, (BROWN, ORANGE), 'flat', k=0)
    c.line(16, 4, 19, 6, BROWN)


def hut(c):
    # log cabin with a turf roof
    roof = c.poly([(28, 0.5), (55, 11), (1, 11)])
    c.fill(roof, LEAF, lambda u, v, x, y: (DARK_GREEN if y % 3 == 2 else GREEN) if u < 28
           else (BLACK if y % 3 == 2 else DARK_GREEN))
    c.line(13, 1, 1, 10, AQUA)
    walls = c.rect(7, 11.5, 49, 22.5)
    c.fill(walls, WOOD, lambda u, v, x, y: MAGENTA if y % 3 == 2 else ORANGE)
    for y in (12, 15, 18, 21):
        c.px(3, y, PINK)
        c.px(24, y, PINK)
    door = c.rect(23, 14, 33, 22.5)
    c.fill(door, (BLACK,), 'flat', k=0, sep=False)
    c.line(11, 14, 11, 22, BROWN)
    c.line(16, 14, 16, 22, BROWN)
    win = c.rect(38, 14, 44, 18)
    c.fill(win, (YELLOW,), 'flat', k=0)
    c.line(0, 23, 27, 23, DARK_GREEN)


def igloo(c):
    cu, cv = 25, 22
    dome = c.mask(lambda u, v: ((u - cu) / 23) ** 2 + ((v - cv) / 20) ** 2 <= 1 and v <= 23.5)
    c.fill(dome, SNOW, 'sphere', c=(cu, cv, 23, 20), gain=1.35, bias=0.05)
    # block joints
    for rowv in (8, 13, 18):
        for (x, y) in dome:
            if y == rowv:
                c.px(x, y, MEDIUM_BLUE)
    for (x, y) in dome:
        band = 0 if y < 8 else 1 if y < 13 else 2 if y < 18 else 3
        if y in (8, 13, 18):
            continue
        if (x + band * 2) % 4 == 0 and y > 3:
            c.px(x, y, LIGHT_BLUE if c.p[y][x] == WHITE else MEDIUM_BLUE)
    # entrance tunnel
    tun = c.mask(lambda u, v: ((u - 44) / 11) ** 2 + ((v - 23.5) / 11) ** 2 <= 1)
    c.fill(tun, SNOW, 'sphere', c=(44, 23.5, 11, 11), gain=1.3)
    hole = c.mask(lambda u, v: ((u - 46) / 5.5) ** 2 + ((v - 24) / 6.5) ** 2 <= 1)
    c.fill(hole, (BLACK,), 'flat', k=0, sep=False)
    c.line(0, 23, 27, 23, LIGHT_BLUE)


def trench(c):
    ground = c.poly([(6, 6.5), (55, 6.5), (53, 23.5), (0.5, 23.5)])
    c.fill(ground, (DARK_GREEN,), lambda u, v, x, y: GREEN if y == 6 or (x * 5 + y * 3) % 11 == 0 else DARK_GREEN)
    pit = c.poly([(11, 9.5), (35, 9.5), (33, 20.5), (6, 20.5)])
    c.fill(pit, (BLACK,), 'flat', k=0, sep=False)
    far = c.poly([(11, 9.5), (35, 9.5), (32, 14.5), (12, 14.5)])
    c.fill(far, EARTH, lambda u, v, x, y: BROWN if y >= 12 else (ORANGE if y == 9 else BROWN), sep=False)
    right = c.poly([(35, 9.5), (33, 20.5), (29.5, 20.5), (32, 14.5)])
    c.fill(right, EARTH, lambda u, v, x, y: ORANGE, sep=False)
    c.pxs(((9, 11), (13, 10), (11, 12), (14, 12), (7, 13)), MAGENTA)
    c.line(3, 21, 15, 21, GREEN)
    heap = c.mask(lambda u, v: ((u - 45.5) / 10) ** 2 + ((v - 22) / 12) ** 2 <= 1 and v < 22.5)
    c.fill(heap, (MAGENTA, BROWN, ORANGE, ORANGE), 'sphere', c=(45.5, 22, 10, 12), gain=1.05)
    for x, y in ((21, 15), (24, 18), (20, 19), (25, 13)):
        c.px(x, y, MAGENTA)
    c.line(23, 1, 23, 7, ORANGE)
    c.line(22, 0, 24, 0, YELLOW)
    c.pxs(((22, 1), (24, 1)), YELLOW)
    blade = c.poly([(42.5, 7.5), (50, 7.5), (49.5, 12), (46.2, 13.5), (43, 12)])
    c.fill(blade, STEEL, 'edge')


def club(c):
    pts = [((7, 22.5), 1.8), ((22, 15), 2.4), ((36, 7.5), 3.8), ((46, 3), 4.6)]
    m = set()
    for (p0, w0), (p1, w1) in zip(pts, pts[1:]):
        m |= c.capsule(p0, p1, w0, w1)
    m |= c.ellipse(36, 6.5, 4, 3.5) | c.ellipse(44, 7, 3.5, 3)
    c.fill(m, WOOD, 'cyl', axis=((7, 22.5), (46, 3), 4.6))
    for x, y in ((17, 6), (21, 4), (19, 8), (14, 10)):
        c.px(x, y, BROWN)
    c.pxs(((18, 5), (22, 3)), YELLOW)
    for x, y in ((4, 21), (5, 20), (6, 20), (7, 19)):
        c.px(x, y, MAGENTA)


def spear(c):
    c.fill(c.capsule((2, 23), (40, 6), 0.9), WOOD, 'flat', k=1)
    c.line(1, 23, 19, 7, ORANGE)
    head = c.poly([(55, 0.5), (45, 3.5), (37, 10), (42, 9), (49, 6.5)])
    c.fill(head, STONE, 'edge')
    c.line(26, 1, 21, 4, WHITE)
    # binding
    for x, y in ((19, 7), (20, 7), (18, 8), (19, 8)):
        c.px(x, y, YELLOW)
    c.pxs(((20, 8), (18, 7)), BROWN)
    # feathers / tassel
    c.pxs(((17, 9), (16, 10), (17, 10)), MAGENTA)


def bow(c):
    # bow arc on the left, string on the right, nocked arrow
    arc = c.mask(lambda u, v: 0.80 <= math.hypot((u - 34) / 22, (v - 12) / 11.8) <= 1.0 and u < 34)
    c.fill(arc, WOOD, 'flat', k=1)
    for (x, y) in arc:
        if (x - 1, y) not in arc or (x, y - 1) not in arc:
            c.px(x, y, PINK)
    c.fill(c.rect(10, 9.5, 14, 14.5), (MAGENTA, PINK), 'flat', k=0)
    # string: from the tips to the nock point
    c.line(16, 1, 23, 12, WHITE)
    c.line(16, 22, 23, 12, WHITE)
    # arrow
    c.line(2, 12, 24, 12, ORANGE)
    head = c.poly([(0.5, 12), (6, 9.5), (5, 12), (6, 14.5)])
    c.fill(head, STEEL, 'edge', sep=False)
    c.pxs(((25, 11), (26, 10), (25, 13), (26, 14), (24, 11), (24, 13)), MAGENTA)
    c.pxs(((26, 11), (26, 13), (27, 10), (27, 14)), PINK)


def splint(c):
    arm = c.capsule((2, 14), (42, 14), 4.6)
    c.fill(arm, SKIN, lambda u, v, x, y: ORANGE if v > 17 else (WHITE if y == 10 and x % 5 == 1 else PINK))
    hand = c.mask(lambda u, v: ((u - 48) / 7) ** 2 + ((v - 14.5) / 5.5) ** 2 <= 1)
    c.fill(hand, SKIN, lambda u, v, x, y: ORANGE if v > 17.5 or u > 52 else PINK)
    c.pxs(((26, 13), (26, 15)), MAGENTA)          # finger creases
    c.fill(c.capsule((44, 9.5), (49, 8.5), 1.5), SKIN, lambda u, v, x, y: PINK)
    for v0, v1 in ((3.5, 8.5), (19.8, 23.5)):
        board = c.rect(3, v0, 42, v1)
        c.fill(board, WOOD, lambda u, v, x, y, v0=v0: YELLOW if y == int(v0) else
               (MAGENTA if x in (8, 15) and y % 2 else ORANGE))
    for u in (11, 31):
        tie = c.rect(u - 2, 2.5, u + 2, 23.5)
        c.fill(tie, CLOTH, lambda uu, vv, x, y, u=u: WHITE if uu < u else GREY1)
    c.pxs(((6, 1), (4, 0)), WHITE)
    c.pxs(((16, 1), (17, 0)), WHITE)


def sunglasses(c):
    def lens(cu):
        return c.mask(lambda u, v: ((u - cu) / 11.5) ** 2 + ((v - 13) / 8.5) ** 2 <= 1 and v >= 6.5)
    for cu in (15, 41):
        m = lens(cu)
        rim = c.mask(lambda u, v, cu=cu: ((u - cu) / 13.5) ** 2 + ((v - 13) / 10) ** 2 <= 1 and v >= 5)
        c.fill(rim, (GREY1, WHITE), 'edge')
        c.fill(m, (DARK_BLUE,), lambda u, v, x, y: PURPLE if v < 9.5 else (MEDIUM_BLUE if v < 13 else DARK_BLUE),
               sep=False)
        # glint
        x0 = int((cu - 6) / 2)
        c.px(x0, 9, WHITE)
        c.px(x0 + 1, 8, WHITE)
        c.px(x0, 10, LIGHT_BLUE)
    # bridge
    c.line(13, 6, 14, 6, WHITE)
    c.line(13, 7, 14, 7, GREY1)
    # temples
    c.line(0, 5, 1, 6, GREY1)
    c.line(27, 5, 26, 6, GREY1)


def sunscreen(c):
    body = c.mask(lambda u, v: (abs(u - 28) <= 11 and 9 <= v <= 23.5) or
                  ((u - 28) / 11) ** 2 + ((v - 9) / 4) ** 2 <= 1)
    c.fill(body, (MEDIUM_BLUE,), lambda u, v, x, y: DARK_BLUE if u > 34 else MEDIUM_BLUE)
    c.line(10, 9, 10, 22, WHITE)
    c.px(11, 7, WHITE)
    cap = c.rect(22, 0.5, 34, 4.5)
    c.fill(cap, (ORANGE,), lambda u, v, x, y: MAGENTA if u > 31 else (YELLOW if u < 25 else ORANGE))
    sun = c.ellipse(28, 15.5, 4.6, 3.2)
    c.fill(sun, (ORANGE, YELLOW), lambda u, v, x, y: YELLOW if (u < 27 and v < 15.5) else ORANGE, sep=False)
    for k in range(8):
        a = k * math.pi / 4
        for r in (8.0, 10.0):
            u, v = 28 + math.cos(a) * r, 15.5 + math.sin(a) * r * 0.66
            c.px(int(u // 2), int(v), ORANGE if r > 9 else YELLOW)


def rock(c):
    outline = [(4, 23.5), (2, 17), (6, 10), (14, 5), (24, 2.5), (34, 3), (44, 7), (51, 13),
               (54, 19), (52, 23.5)]
    c.fill(c.poly(outline), (GREY1,), 'flat', k=0)
    X = (26, 12)
    facets = (
        ([(6, 10), (14, 5), (24, 2.5), (34, 3), X, (14, 13)], WHITE),
        ([(34, 3), (44, 7), (51, 13), (38, 14), X], GREY1),
        ([(4, 23.5), (2, 17), (6, 10), (14, 13), (18, 23.5)], GREY1),
        ([(14, 13), X, (38, 14), (36, 23.5), (18, 23.5)], GREY1),
        ([(38, 14), (51, 13), (54, 19), (52, 23.5), (36, 23.5)], DARK_BLUE),
    )
    for i, (pts, col) in enumerate(facets):
        m = c.poly(pts)
        c.fill(m, (col,), 'flat', k=0, sepcol=DARK_BLUE)
    c.pxs(((8, 4), (9, 3), (10, 3), (11, 2), (7, 5), (12, 2)), GREEN)
    c.pxs(((9, 4), (10, 4)), DARK_GREEN)
    c.pxs(((3, 10), (4, 9)), LIGHT_BLUE)


DRAW = {
    'AXE': axe, 'KNIFE': knife, 'ROPE': rope, 'MATCHES': matches,
    'FLASHLIGHT': flashlight, 'COMPASS': compass, 'FISHNG GEAR': fishing,
    'STOVE': stove, 'UTENSILS': utensils, 'GUN': gun, 'TENT': tent,
    'CANTEEN': canteen, 'HUT': hut, 'IGLOO': igloo, 'TRENCH': trench,
    'CLUB': club, 'SPEAR': spear, 'BOW': bow, 'SPLINT': splint,
    'SUNGLASSES': sunglasses, 'SUNSCREEN': sunscreen, 'ROCK': rock,
}


def render():
    icons = {}
    for name in TOOLS + CRAFT:
        c = Icon()
        DRAW[name](c)
        icons[name] = c.p
    return icons


def scale(rows, sx, sy):
    return [[c for c in row for _ in range(sx)] for row in rows for _ in range(sy)]


def label(canvas, name, x, y, k=2):
    for i, char in enumerate(name):
        if char == ' ':
            continue
        for dy, row in enumerate(FONT[char].split('/')):
            for dx, bit in enumerate(row):
                if bit == '1':
                    for sy in range(k):
                        for sx in range(k):
                            canvas[y + dy * k + sy][x + i * 4 * k + dx * k + sx] = WHITE


def blit(canvas, pixels, x, y):
    for dy, row in enumerate(pixels):
        canvas[y + dy][x:x + len(row)] = row


def main():
    icons = render()
    out = Path(__file__).resolve().parent.parent / 'build' / 'icons_hd'
    out.mkdir(parents=True, exist_ok=True)
    SX, SY = 8, 4                       # 224 x 96 per icon
    cw, ch = 240, 120
    sheet = [[BLACK] * (cw * 4) for _ in range(ch * 6)]
    for i, (name, rows) in enumerate(icons.items()):
        pixels = scale(rows, SX, SY)
        write_png(out / (name.lower().replace(' ', '_') + '.png'), pixels)
        x, y = (i % 4) * cw + 8, (i // 4) * ch + 4
        blit(sheet, pixels, x, y)
        label(sheet, name, x + (224 - (len(name) * 8 - 2)) // 2, y + 100)
    write_png(out / 'sheet.png', sheet)

    # Old (14 x 12 at x16/x8) next to new (28 x 24 at x8/x4): same box.
    old = decode_art()
    cw2, ch2 = 2 * 224 + 40, 120
    cols = 2
    rows_n = (len(icons) + cols - 1) // cols
    comp = [[BLACK] * (cw2 * cols) for _ in range(ch2 * rows_n)]
    for i, name in enumerate(icons):
        x, y = (i % cols) * cw2 + 8, (i // cols) * ch2 + 4
        blit(comp, scale(old[name], 16, 8), x, y)
        blit(comp, scale(icons[name], SX, SY), x + 224 + 16, y)
        for yy in range(y, y + 96):
            comp[yy][x + 224 + 7] = GREY1
        label(comp, name, x + (448 - (len(name) * 8 - 2)) // 2, y + 100)
    write_png(out / 'compare.png', comp)

    (out / 'icons.json').write_text(json.dumps(icons, indent=1) + '\n', encoding='utf-8')
    print(f'Wrote {len(icons)} icons, sheet.png, compare.png and icons.json to {out}')


if __name__ == '__main__':
    main()
