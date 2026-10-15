#!/usr/bin/env python3
"""Neowilderness animal icons, one per species; run with Python 3 from anywhere.

Same format and conventions as tools/genicons_hd.py: 28 x 24 DHGR colour
pixels, designed in 2:1 display units (u = 2x + 1 in 0..56, v = y + 0.5 in
0..24), light from the top left, black background. Animals face left.

Species of the six regions (build/regions/fauna.json): British Columbia
grizzly, wolf, moose; Sierra Nevada black bear, cougar, rattlesnake; Burma
tiger, elephant, cobra, python; New Guinea death adder, crocodile (the Dani
'cannibal' record is a person, not drawn here); Bolivia puma (= cougar),
jaguar, fer-de-lance, anaconda; Chile puma, Andean cat.

Outputs, in build/icons_animals/: <name>.png (x8 / x4), sheet.png and
icons.json (names mapped to 24 rows of 28 colour numbers).
"""

import json
import math
from pathlib import Path

from dhgr_palette import (BLACK, MAGENTA, DARK_BLUE, PURPLE, DARK_GREEN, GREY1,
                          MEDIUM_BLUE, LIGHT_BLUE, BROWN, ORANGE, GREY2, PINK,
                          GREEN, YELLOW, AQUA, WHITE)
from genicons import write_png
from genicons_hd import H, LIGHT, W, Icon, blit, label, level, scale

NAMES = ('GRIZZLY', 'BLACK BEAR', 'WOLF', 'MOOSE', 'COUGAR', 'RATTLESNAKE',
         'TIGER', 'ELEPHANT', 'COBRA', 'PYTHON', 'DEATH ADDER', 'CROCODILE',
         'JAGUAR', 'FER DE LANCE', 'ANACONDA', 'ANDEAN CAT')

REGIONS = {
    'GRIZZLY': 'British Columbia', 'WOLF': 'British Columbia', 'MOOSE': 'British Columbia',
    'BLACK BEAR': 'Sierra Nevada', 'COUGAR': 'Sierra Nevada, Bolivia, Chile (puma)',
    'RATTLESNAKE': 'Sierra Nevada', 'TIGER': 'Burma', 'ELEPHANT': 'Burma',
    'COBRA': 'Burma', 'PYTHON': 'Burma', 'DEATH ADDER': 'New Guinea',
    'CROCODILE': 'New Guinea', 'JAGUAR': 'Bolivia', 'FER DE LANCE': 'Bolivia',
    'ANACONDA': 'Bolivia', 'ANDEAN CAT': 'Chile',
}

GRIZ = (BROWN, ORANGE, ORANGE, YELLOW)
TAWNY = (BROWN, ORANGE, ORANGE, YELLOW)
GREYFUR = (DARK_BLUE, GREY1, GREY1, WHITE)
TIGERFUR = (MAGENTA, ORANGE, ORANGE, PINK)


# ---------------------------------------------------------------------------
# helpers

def blob(c, parts):
    """Union of ellipses (cu, cv, ru, rv) and capsules ((p0), (p1), w0[, w1])."""
    m = set()
    for p in parts:
        if len(p) == 4 and not isinstance(p[0], tuple):
            m |= c.ellipse(*p)
        else:
            m |= c.capsule(*p)
    return m


def body_shade(ramp, cu, cv, ru, rv, gain=1.0, bias=0.0, lo=0.12, hi=0.82):
    """Sphere-like shading around one centre for a whole silhouette: the mid
    colour dominates, shadow and highlight only at the rims. ramp is
    (shadow, mid, ..., light)."""
    def f(u, v, x, y):
        du, dv = (u - cu) / ru, (v - cv) / rv
        r2 = du * du + dv * dv
        if r2 > 1:
            k = math.sqrt(r2)
            du, dv, r2 = du / k * 0.999, dv / k * 0.999, 0.998
        n = (du * 0.5, dv * 0.5, math.sqrt(1 - r2))
        k = math.sqrt(sum(a * a for a in n)) or 1.0
        i = (sum(a * b for a, b in zip(n, LIGHT)) / k + bias) * gain
        return ramp[0] if i < lo else ramp[-1] if i > hi else ramp[1]
    return f


def leg(c, top, foot, w, col, foot_col=None):
    m = c.capsule(top, foot, w, w * 0.85)
    c.fill(m, (col,), 'flat', k=0, sep=False)
    if foot_col is not None:
        x, y = int(foot[0] // 2), int(foot[1])
        c.px(x, y, foot_col)
    return m


def spline(ctrl, n=24):
    """Catmull-Rom through control points (u, v, w): dense samples."""
    pts = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * b + (-a + cc) * t + (2 * a - 5 * b + 4 * cc - d) * t2
                                    + (-a + 3 * b - 3 * cc + d) * t3)
                             for a, b, cc, d in zip(p0, p1, p2, p3)))
    out.append(ctrl[-1])
    return out


def tube(c, ctrl, colour, n=24, outline=True):
    """Snake body along ctrl; later samples lie on top. colour(s, t, i, x, y)
    gets the arc length s, the signed offset t (-1..1), the light i."""
    pts = spline(ctrl, n)
    s_acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        s_acc.append(s_acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))

    def top_index(u, v):
        best = None
        for i in range(len(pts) - 1, -1, -1):
            pu, pv, w = pts[i]
            if (u - pu) ** 2 + (v - pv) ** 2 <= w * w:
                best = i
                break
        if best is None:
            return None
        lo, hi = max(0, best - 10), min(len(pts) - 1, best + 10)
        return min(range(lo, hi + 1), key=lambda j: (u - pts[j][0]) ** 2 + (v - pts[j][1]) ** 2
                   if (u - pts[j][0]) ** 2 + (v - pts[j][1]) ** 2 <= pts[j][2] ** 2 else 1e9)

    m = c.mask(lambda u, v: top_index(u, v) is not None)
    idx = {}
    for (x, y) in m:
        u, v = 2 * x + 1, y + 0.5
        j = top_index(u, v)
        if j is None:
            j = min(range(len(pts)), key=lambda q: (u - pts[q][0]) ** 2 + (v - pts[q][1]) ** 2)
        idx[(x, y)] = j
        a = pts[max(0, j - 1)]
        b = pts[min(len(pts) - 1, j + 1)]
        tu, tv = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tu, tv) or 1.0
        nu, nv = -tv / L, tu / L
        w = pts[j][2]
        t = ((u - pts[j][0]) * nu + (v - pts[j][1]) * nv) / w
        t = max(-1.0, min(1.0, t))
        nz = math.sqrt(1 - t * t)
        i = nu * t * LIGHT[0] + nv * t * LIGHT[1] + nz * LIGHT[2]
        c.p[y][x] = colour(s_acc[j], t, i, x, y)
    if outline:
        # black seam where an upper stretch crosses a lower one
        for (x, y), j in idx.items():
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if q in idx and idx[q] > j + 14:
                    c.p[y][x] = BLACK
    return pts


# ---------------------------------------------------------------------------
# mammals (facing left)

def edge_shade(m, mid, lit, dark, deep=2):
    """Mid colour, lit on the top/left rim, dark on the bottom/right rim and
    deep pixels above an underside (belly shadow)."""
    def f(u, v, x, y):
        if (x, y + 1) not in m or (x + 1, y) not in m:
            return dark
        if (x, y - 1) not in m or ((x - 1, y) not in m and (x, y - 2) not in m):
            return lit
        if deep > 1 and (x, y + deep) not in m and (x + 1, y + deep) not in m and (x - 1, y + deep) not in m:
            return dark
        return mid
    return f


def rim(c, m, lit, dark=None):
    """Recolour the silhouette edge: lit on top/left, dark on bottom/right."""
    for (x, y) in m:
        up, lf = (x, y - 1) not in m, (x - 1, y) not in m
        dn, rt = (x, y + 1) not in m, (x + 1, y) not in m
        if (up or lf) and lit is not None:
            c.p[y][x] = lit
        elif (dn or rt) and dark is not None:
            c.p[y][x] = dark


def feline(c, fur, deep=0.0, head=0.0, tail='long', far_col=None):
    """Side view of a big cat facing left; fur = (shadow, mid, light)."""
    d, h = deep, head
    far_col = far_col or fur[0]
    far = c.poly([(26.5, 15), (30.5, 15), (30, 23.5), (26.5, 23.5)]) | \
        c.poly([(38, 15), (42, 15), (42, 23.5), (38.5, 23.5)])
    c.fill(far, (far_col,), 'flat', k=0)
    if tail == 'long':
        tl = [(47, 9.5), (51, 12), (53, 17), (54.5, 21), (55.5, 22.5), (55.5, 23.5),
              (53, 23.5), (51, 19.5), (49.5, 14.5), (46.5, 12.5)]
    else:
        tl = [(47, 9.5), (51, 11.5), (54, 9), (54.5, 4), (56, 2.5), (56, 5), (55.5, 10),
              (52, 14), (48.5, 13)]
    body = c.poly([(1.5, 11 + h * 0.2), (4, 9 - h * 0.5), (7, 7.5 - h), (8.5, 7 - h),
                   (9.5, 4.2 - h), (12, 6.2 - h), (14, 7 - h * 0.6), (18, 9 - d * 0.5),
                   (24, 8.5 - d), (36, 9 - d), (44, 8.5 - d * 0.6)] + tl +
                  [(46, 14), (47, 18), (48, 23.5), (44, 23.5), (43, 19), (40, 16 + d * 0.3),
                   (36, 16 + d * 0.3), (28, 16 + d * 0.3), (26, 17), (25.5, 23.5), (21, 23.5),
                   (21, 17), (19, 15), (16, 14), (11, 13 + h * 0.5), (5, 13 + h * 0.4),
                   (2, 12.5 + h * 0.3)])
    sh = edge_shade(body, fur[1], fur[2], fur[0])

    def f(u, v, x, y):
        if 13.5 + d * 0.3 < v < 16.5 + d * 0.3 and 14 <= u <= 42 and (x, y + 1) in body:
            return WHITE                                            # pale belly
        return sh(u, v, x, y)
    c.fill(body, fur, f)
    c.pxs(((1, 12), (2, 12), (1, 13), (2, 13)), WHITE)
    c.px(0, 11, PINK)
    c.px(3, 9 - int(h * 0.5), YELLOW)
    c.px(2, 9 - int(h * 0.5), BLACK)
    c.px(5, 5 - int(h), BLACK)
    for x in (10, 11, 21, 22):
        c.px(x, 23, WHITE)
    return body


def path_len(ctrl, n=24):
    pts = spline(ctrl, n)
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def grizzly(c):
    far = c.poly([(27, 16), (34, 16), (33.5, 23.5), (28, 23.5)]) | \
        c.poly([(38, 15), (45, 15), (44, 23.5), (38.5, 23.5)])
    c.fill(far, (BROWN,), 'flat', k=0)
    body = c.poly([(1, 13), (3, 11), (8, 8.5), (11, 6.5), (11.5, 4.5), (14, 4.5), (15, 6.5),
                   (18, 5.5), (24, 2.5), (30, 3.5), (38, 4.5), (46, 6), (51, 9), (53, 13),
                   (53, 18), (52, 23.5), (45, 23.5), (45, 18), (41, 17), (31, 17.5),
                   (26, 17), (25.5, 23.5), (15.5, 23.5), (15.5, 18), (13, 15.5), (8, 15.5),
                   (3.5, 15)])
    c.fill(body, GRIZ, edge_shade(body, ORANGE, YELLOW, BROWN))
    for (x, y) in body:
        if y < 8 and 9 <= x <= 22 and (x + y) % 2 == 0:
            c.p[y][x] = YELLOW                                     # grizzled hump
    c.pxs(((4, 10), (5, 10)), BLACK)
    c.pxs(((0, 12), (0, 13)), BLACK)
    c.px(6, 5, BROWN)
    c.line(2, 14, 5, 14, BROWN)
    for x in (8, 9, 10, 23, 24, 25):
        c.px(x, 23, WHITE)
    c.line(12, 18, 12, 22, BROWN)


def black_bear(c):
    far = c.poly([(27, 15.5), (33, 15.5), (32.5, 23.5), (27.5, 23.5)]) | \
        c.poly([(39, 15), (45, 15), (44, 23.5), (39.5, 23.5)])
    c.fill(far, (BLACK,), lambda u, v, x, y: DARK_BLUE if (x + y) % 2 else BLACK)
    body = c.poly([(1, 12), (3, 10.5), (8, 9.5), (10, 7), (10.5, 4.2), (13.5, 4), (14.5, 6),
                   (16, 6), (17, 4.5), (20, 4.5), (20, 6.5), (30, 5), (40, 5), (48, 7.5),
                   (52, 11), (53, 17), (52, 23.5), (45.5, 23.5), (45, 18), (40, 17),
                   (31, 17.5), (26, 17), (25.5, 23.5), (16, 23.5), (16, 18), (13, 15.5),
                   (8, 14.8), (3, 14)])
    sh = edge_shade(body, BLACK, GREY1, DARK_BLUE, deep=0)

    def fur(u, v, x, y):
        k = sh(u, v, x, y)
        if k == BLACK:
            d = next((j for j in range(1, 6) if (x, y - j) not in body), 6)
            if d == 1 or (d == 2 and (x + y) % 2):
                return DARK_BLUE                                    # sheen under the lit back
        return k
    c.fill(body, (BLACK,), fur)
    for (x, y) in body:
        if (x, y - 1) not in body and 5 < x < 22:
            c.p[y][x] = WHITE
    muzzle = c.poly([(1, 12), (3, 10.5), (8, 9.8), (8.5, 14.2), (3, 14)])
    c.fill(muzzle, (ORANGE,), lambda u, v, x, y: PINK if v < 11.5 else ORANGE, sep=False)
    c.px(0, 11, BLACK)
    c.px(0, 12, BLACK)
    c.px(5, 8, WHITE)
    c.px(4, 8, BLACK)
    c.pxs(((6, 5), (9, 5)), MAGENTA)
    c.pxs(((8, 14), (9, 15), (9, 14)), WHITE)


def wolf(c):
    far = c.poly([(26.5, 15), (30, 15), (29.5, 23.5), (26.5, 23.5)]) | \
        c.poly([(38, 15), (41.5, 15), (41, 23.5), (38, 23.5)])
    c.fill(far, (DARK_BLUE,), 'flat', k=0)
    body = c.poly([(1, 9.5), (8, 8), (10, 6.5), (11, 5), (12.5, 1.5), (15, 5.5), (18, 6.5),
                   (24, 7), (36, 7.5), (44, 7.5), (46.5, 8.5), (50, 11), (53, 15), (54.5, 19.5),
                   (52, 20.5), (49.5, 17.5), (47, 13.5), (46.5, 15), (47, 19), (47.5, 23.5),
                   (43.5, 23.5), (43, 19), (41, 16), (37, 15.5), (28, 15), (26, 16.5),
                   (25.5, 23.5), (21.5, 23.5), (21.5, 18), (19.5, 15.5), (17, 14.5),
                   (13, 12.5), (8, 11.5), (3, 11.2), (1.5, 10.5)])
    sh = edge_shade(body, GREY1, WHITE, DARK_BLUE)

    def fur(u, v, x, y):
        if u > 50 and v > 17.5:
            return DARK_BLUE                                        # dark tail tip
        if 14 <= x <= 22 and 7 <= y <= 9 and (x + y) % 2:
            return DARK_BLUE                                        # saddle
        return sh(u, v, x, y)
    c.fill(body, GREYFUR, fur)
    c.pxs(((0, 9), (0, 10)), BLACK)
    c.px(5, 8, YELLOW)
    c.px(4, 8, BLACK)
    c.px(6, 4, BLACK)
    c.pxs(((7, 12), (8, 13), (8, 12)), WHITE)
    c.line(1, 10, 5, 10, WHITE)


def moose(c):
    far = c.poly([(27, 14), (30, 14), (30, 23.5), (27.5, 23.5)]) | \
        c.poly([(42, 13), (45.5, 13), (45, 23.5), (42, 23.5)])
    c.fill(far, (MAGENTA,), lambda u, v, x, y: GREY1 if v > 19 else MAGENTA)
    body = c.poly([(1, 12), (3, 9.5), (8, 7.5), (13, 5.5), (16, 5), (18, 5.5), (22, 2.5),
                   (29, 3), (38, 5), (46, 5.5), (50, 7), (51.5, 10), (50.5, 13), (49, 16),
                   (49.5, 23.5), (46.5, 23.5), (46, 16), (44, 13.5), (30, 14), (26.5, 15),
                   (26.5, 23.5), (23.5, 23.5), (23, 15), (21, 13), (17, 13), (16.5, 15),
                   (15.5, 18), (14.5, 14.5), (11, 14), (5.5, 16), (1.5, 15.5)])
    sh = edge_shade(body, BROWN, ORANGE, MAGENTA)

    def fur(u, v, x, y):
        if v > 18.5 and u > 20:
            return GREY1 if (x + 1, y) in body else DARK_BLUE      # pale stockings
        return sh(u, v, x, y)
    c.fill(body, (BROWN,), fur)
    # palmate antler drawn by hand: tines, palm, beam down to the skull
    for y, xs, col in ((0, (4, 6, 8, 10, 12), WHITE), (1, range(4, 13), WHITE),
                       (2, range(5, 12), GREY1), (3, range(7, 11), GREY1), (4, (8, 9), GREY1)):
        for x in xs:
            c.px(x, y, col)
    c.pxs(((12, 2), (11, 3)), DARK_BLUE)
    c.px(5, 8, BLACK)
    c.px(0, 12, BLACK)
    c.px(1, 13, BLACK)
    c.px(8, 5, MAGENTA)
    c.line(1, 14, 3, 15, MAGENTA)


def cougar(c):
    body = feline(c, (BROWN, ORANGE, YELLOW))
    c.pxs(((27, 22), (27, 23), (26, 23)), BLACK)                   # dark tail tip
    c.px(2, 11, ORANGE)


def tiger(c):
    body = feline(c, (MAGENTA, ORANGE, PINK), deep=1.0, head=0.8, tail='long', far_col=MAGENTA)
    for (x, y) in body:
        u, v = 2 * x + 1, y + 0.5
        if u < 9 or c.p[y][x] == WHITE or y > 17:
            continue
        k = int(u + (0.6 if u < 30 else -0.6) * v)
        if k % 8 == 0 and (x * 7 + y * 3) % 6:
            c.p[y][x] = BLACK
    for (x, y) in body:                                             # ringed tail
        if x >= 24 and y >= 9 and (y % 3 == 0):
            c.p[y][x] = BLACK
    c.pxs(((4, 9), (4, 10), (6, 8)), BLACK)


def jaguar(c):
    body = feline(c, (BROWN, ORANGE, YELLOW), deep=1.6, head=1.2, tail='up')
    for cx, cy in ((10, 9), (13, 8), (16, 9), (19, 8), (22, 9), (8, 12), (12, 12), (16, 12),
                   (20, 12), (24, 11), (14, 15), (19, 15), (11, 17), (20, 19), (24, 6)):
        if (cx, cy) not in body:
            continue
        for x, y in ((cx, cy - 1), (cx - 1, cy), (cx + 1, cy), (cx, cy + 1)):
            if (x, y) in body and c.p[y][x] != WHITE:
                c.p[y][x] = BLACK
        c.p[cy][cx] = ORANGE
    c.pxs(((4, 8), (5, 9), (6, 10)), BLACK)


def elephant(c):
    far = c.poly([(27, 17), (32, 17), (32, 23.5), (27, 23.5)]) | \
        c.poly([(38, 17), (43, 17), (43, 23.5), (38, 23.5)])
    c.fill(far, (DARK_BLUE,), 'flat', k=0)
    c.fill(c.capsule((51, 9), (54, 17), 0.8), (GREY1,), 'flat', k=0, sep=False)
    body = c.poly([(5, 23.5), (2.5, 20), (2, 15), (3, 11), (5, 7), (7, 3.5), (12, 1.5),
                   (18, 2.3), (28, 1.5), (40, 2.3), (48, 5.5), (52, 10), (52, 16), (51, 23.5),
                   (45, 23.5), (44.5, 18.5), (36, 18.5), (30, 18.5), (29.5, 23.5),
                   (22, 23.5), (21.5, 17), (16, 16), (12, 15), (9, 14.5), (7.5, 17),
                   (8.5, 21), (9.5, 23.5)])
    EL = (DARK_BLUE, GREY1, WHITE)
    c.fill(body, EL, edge_shade(body, GREY1, WHITE, DARK_BLUE))
    rim(c, body, None, DARK_BLUE)
    for (x, y) in body:
        if (x, y - 1) not in body and 3 < x < 22:
            c.p[y][x] = WHITE
    ear = c.poly([(15, 4), (25, 4), (27.5, 8), (26, 13.5), (20, 16), (15.5, 12)])
    c.fill(ear, (DARK_BLUE, GREY1), lambda u, v, x, y: GREY1 if u < 22 and v < 12 else DARK_BLUE,
           sepcol=DARK_BLUE)
    tube(c, [(10.5, 14.5, 0.9), (8, 16.5, 0.9), (4.5, 17.5, 0.8)], lambda *a: WHITE,
         outline=False)
    c.px(5, 7, BLACK)
    c.pxs(((3, 18), (3, 20), (4, 22)), DARK_BLUE)                # trunk folds
    for x in (11, 12, 23, 24):
        c.px(x, 23, WHITE)


def andean_cat(c):
    AC = (DARK_BLUE, GREY1, WHITE)
    far = c.poly([(26, 16), (29, 16), (29, 23.5), (26, 23.5)]) | \
        c.poly([(34, 16), (37, 16), (37, 23.5), (34, 23.5)])
    c.fill(far, (DARK_BLUE,), 'flat', k=0)
    tail = tube(c, [(38, 12, 2.6), (45, 16, 3.0), (51, 15, 3.0), (54, 10, 2.8), (53.5, 5, 2.6)],
                lambda s, t, i, x, y: (ORANGE if int(s) % 5 < 2 else (WHITE if i > 0.75 else GREY1)))
    body = c.poly([(3, 12), (5, 10), (8, 8.5), (9, 5.5), (11.5, 8), (14, 8), (16, 5.5),
                   (17, 9), (21, 10.5), (32, 10.5), (39, 11), (41, 15), (40, 18), (40.5, 23.5),
                   (37.5, 23.5), (37, 18.5), (34, 17), (25, 17), (24, 23.5), (21, 23.5),
                   (21, 17.5), (17, 15.5), (12, 15), (5, 14.5)])
    c.fill(body, AC, edge_shade(body, GREY1, WHITE, DARK_BLUE))
    rim(c, body, None, DARK_BLUE)
    for x, y in ((11, 11), (13, 12), (15, 11), (12, 14), (16, 14), (18, 12), (14, 15),
                 (17, 15), (10, 13), (19, 15), (8, 10), (7, 10)):
        if (x, y) in body:
            c.px(x, y, ORANGE)
    c.px(4, 10, AQUA)
    c.px(3, 10, BLACK)
    c.px(1, 12, PINK)
    c.pxs(((2, 13), (3, 13)), WHITE)
    c.pxs(((10, 23), (11, 23), (19, 23), (20, 23)), WHITE)


# ---------------------------------------------------------------------------
# reptiles

def head(c, cu, cv, ru, rv, ramp, eye, tip=None, sep=False):
    pts = [(cu + ru, cv - rv * 0.7), (cu + ru, cv + rv * 0.7), (cu - ru * 0.7, cv + rv * 0.9),
           (tip or (cu - ru, cv)), (cu - ru * 0.7, cv - rv * 0.9)]
    m = c.poly(pts)
    c.fill(m, ramp, 'edge', sep=sep)
    c.px(*eye)
    return m


def rattlesnake(c):
    def col(s, t, i, x, y):
        if s < 4.5:
            return YELLOW if int(s * 1.5) % 2 else WHITE           # rattle
        if s < 10:
            return BLACK if int(s / 1.4) % 2 else WHITE            # banded tail
        d = (s % 7) - 3.5
        k = abs(d) + abs(t) * 3.0
        if k < 2.0:
            return BROWN
        if k < 2.7:
            return PINK
        return ORANGE if i > 0.05 else BROWN
    tube(c, [(52, 2.5, 1.4), (51.5, 8, 1.8), (48, 14, 2.4), (40, 18.5, 2.8), (30, 19.5, 3.0),
             (20, 18.5, 3.0), (12, 16.5, 2.9), (10, 12, 2.7), (14, 8.5, 2.5), (17, 5, 2.3)], col)
    head(c, 12, 4.2, 5, 3.0, (BROWN, ORANGE, YELLOW), (4, 3, BLACK), tip=(6.5, 4.6))
    c.pxs(((2, 4), (1, 5)), MAGENTA)
    c.px(1, 4, MAGENTA)
    c.line(5, 5, 7, 5, BROWN)


def cobra(c):
    def col(s, t, i, x, y):
        if int(s) % 6 == 0:
            return YELLOW if i > 0.3 else ORANGE                  # pale crossbands
        return ORANGE if i > 0.85 else BROWN if i > 0.1 else MAGENTA
    tube(c, [(54, 21, 1.2), (46, 20, 2.4), (30, 22, 2.8), (14, 21, 2.8), (10, 17.5, 2.6),
             (20, 15.5, 2.6), (34, 17, 2.6), (32, 12, 2.8), (29, 7, 3.0)], col)
    hood = c.mask(lambda u, v: ((u - 28) / 9.5) ** 2 + ((v - 7) / 5.5) ** 2 <= 1 and v > 1.6)
    c.fill(hood, (BROWN,), lambda u, v, x, y: YELLOW if abs(u - 28) < 4.5 and v > 3.5 else
           (MAGENTA if u > 33 else BROWN if u > 23 else ORANGE))
    for y in (5, 7, 9, 11):                                        # throat bands
        c.px(13, y, ORANGE)
        c.px(14, y, ORANGE)
    c.pxs(((11, 4), (16, 4), (11, 5), (16, 5)), BLACK)            # hood eye-spots
    hd = c.ellipse(28, 2, 4.5, 1.8)
    c.fill(hd, (BROWN, ORANGE, YELLOW), 'edge')
    c.pxs(((12, 1), (15, 1)), BLACK)
    c.pxs(((13, 3), (14, 3)), MAGENTA)


def python(c):
    def col(s, t, i, x, y):
        d = (s % 9)
        if 1.8 < d < 7 and abs(t) < 0.8 - 0.18 * abs(d - 4.4):
            edge = abs(t) > 0.55 - 0.18 * abs(d - 4.4) or d < 2.5 or d > 6.4
            return BLACK if edge else MAGENTA
        return YELLOW if i > 0.85 else ORANGE if i > 0.25 else BROWN
    tube(c, [(55, 14, 1.0), (50, 12, 2.2), (42, 9, 3.4), (32, 10, 3.6), (25, 15, 3.6),
             (18, 19, 3.4), (11, 18, 3.2), (8, 13, 3.0)], col)
    head(c, 7, 9.5, 5.5, 3.0, (BROWN, ORANGE, YELLOW), (2, 8, BLACK), tip=(1, 10))
    c.pxs(((3, 9), (4, 9), (5, 9)), MAGENTA)
    c.px(0, 11, MAGENTA)


def death_adder(c):
    ctrl = [(16, 9, 3.6), (30, 6, 4.0), (44, 9, 4.2), (49, 15.5, 4.0), (40, 20.5, 3.6),
            (26, 21, 3.0), (18, 19, 2.0), (17, 15.5, 1.2), (20, 14, 0.9)]
    end = path_len(ctrl)

    def col(s, t, i, x, y):
        if s > end - 3:
            return WHITE                                           # pale lure
        if s > end - 8:
            return BLACK if int(s) % 2 else GREY1
        band = int(s / 3.2) % 2
        return (ORANGE if i > 0.3 else MAGENTA) if band else (GREY1 if i > 0.3 else DARK_BLUE)
    tube(c, ctrl, col)
    hd = c.poly([(19, 6.5), (19, 12.5), (9, 13), (2.5, 10.5), (4, 8), (9, 6)])
    c.fill(hd, (MAGENTA, ORANGE, PINK), 'edge')
    c.px(4, 8, YELLOW)
    c.px(3, 8, BLACK)
    c.line(3, 10, 8, 11, MAGENTA)
    c.pxs(((7, 7), (8, 7)), GREY1)


def fer_de_lance(c):
    def col(s, t, i, x, y):
        d = s % 7
        tri = abs(d - 3.5) < 3.0 * abs(t) - 0.2
        if tri:
            return BLACK if abs(d - 3.5) < 3.0 * abs(t) - 1.0 else YELLOW
        return GREY1 if i > 0.75 else BROWN
    tube(c, [(55.5, 21, 0.7), (49, 20, 1.5), (42, 16, 2.0), (34, 17, 2.2), (26, 20.5, 2.2),
             (18, 18, 2.2), (15, 13, 2.0), (17, 9, 1.8)], col)
    hd = c.poly([(1, 9), (6, 6.5), (12, 6.2), (18, 8), (18, 10.5), (12, 12), (6, 11.5)])
    c.fill(hd, (BROWN, ORANGE, YELLOW), lambda u, v, x, y: YELLOW if 8 <= v < 9 and u > 6 else
           (GREY1 if v < 8 else BROWN))
    c.px(4, 7, BLACK)
    c.px(4, 8, YELLOW)
    c.px(0, 9, MAGENTA)


def anaconda(c):
    # water first, then coils half sunk
    water = c.mask(lambda u, v: v > 15.5 and ((u - 28) / 28) ** 2 + ((v - 19.5) / 5) ** 2 <= 1)
    c.fill(water, (DARK_BLUE, MEDIUM_BLUE), lambda u, v, x, y:
           LIGHT_BLUE if (x + 2 * y) % 9 == 0 else (MEDIUM_BLUE if y < 19 else DARK_BLUE))
    AN = (DARK_GREEN, DARK_GREEN, GREEN, AQUA)

    def col(s, t, i, x, y):
        d = s % 7
        if 2 < d < 4.5 and abs(t - 0.2) < 0.55:
            return BLACK
        if t > 0.7 and i < 0.4:
            return YELLOW
        return level(AN, i * 1.1)
    pts = tube(c, [(52, 18, 1.4), (46, 15, 3.0), (36, 13, 3.4), (26, 16, 3.4), (18, 17, 3.2),
                   (12, 13, 3.0), (14, 7.5, 2.8)], col)
    # ripples over the sunk part
    for x in range(1, 27):
        if c.p[19][x] != BLACK:
            c.p[19][x] = MEDIUM_BLUE if x % 3 else LIGHT_BLUE
    for x in range(3, 25):
        if c.p[21][x] in (GREEN, DARK_GREEN, BLACK, AQUA, YELLOW) and water.__contains__((x, 21)):
            c.p[21][x] = DARK_BLUE
    head(c, 10, 5.5, 5, 2.8, (DARK_GREEN, GREEN, AQUA), (3, 4, BLACK), tip=(4.5, 6))
    c.pxs(((4, 5), (5, 5), (6, 5)), ORANGE)                        # orange eye stripe
    c.pxs(((7, 3), (8, 3)), BLACK)


def crocodile(c):
    CR = (DARK_GREEN, DARK_GREEN, GREEN, AQUA)
    leg(c, (20, 17), (17, 22.5), 1.8, DARK_GREEN)
    leg(c, (40, 17), (37, 22.5), 1.8, DARK_GREEN)

    def col(s, t, i, x, y):
        if t < -0.75 and int(s) % 3 == 0:
            return BLACK                                           # scutes
        if t > 0.55:
            return YELLOW if t > 0.8 else GREEN
        return level(CR, i * 1.1)
    tube(c, [(14, 13.5, 3.2), (24, 13, 4.4), (36, 13.5, 4.2), (45, 15.5, 3.0), (52, 19, 2),
             (55.5, 22, 1.0)][::-1], col)
    # open jaws: upper raised, lower flat, pink mouth, white teeth
    upper = c.poly([(15, 9.5), (15, 13.5), (2, 12.2), (1, 9), (5, 7.5)])
    lower = c.poly([(15, 14), (15, 17.5), (3, 17.2), (1.5, 15.5)])
    mouth = c.poly([(15, 12.5), (15, 15), (3, 15.5), (2.5, 13)])
    c.fill(mouth, (PINK,), 'flat', k=0, sep=False)
    c.fill(upper, CR, 'edge')
    c.fill(lower, CR, 'edge')
    for x in (1, 3, 5):
        c.px(x, 12, WHITE)
    for x in (2, 4, 6):
        c.px(x, 15, WHITE)
    c.fill(c.ellipse(12, 8.5, 2.5, 1.6), (YELLOW,), 'flat', k=0)
    c.px(6, 8, BLACK)
    leg(c, (24, 17), (26, 23), 2.0, GREEN)
    leg(c, (44, 17.5), (46, 23), 2.0, GREEN)
    c.pxs(((12, 23), (13, 23), (22, 23), (23, 23)), DARK_GREEN)


DRAW = {
    'GRIZZLY': grizzly, 'BLACK BEAR': black_bear, 'WOLF': wolf, 'MOOSE': moose,
    'COUGAR': cougar, 'RATTLESNAKE': rattlesnake, 'TIGER': tiger, 'ELEPHANT': elephant,
    'COBRA': cobra, 'PYTHON': python, 'DEATH ADDER': death_adder, 'CROCODILE': crocodile,
    'JAGUAR': jaguar, 'FER DE LANCE': fer_de_lance, 'ANACONDA': anaconda,
    'ANDEAN CAT': andean_cat,
}


def render():
    icons = {}
    for name in NAMES:
        c = Icon()
        DRAW[name](c)
        icons[name] = c.p
    return icons


def main():
    icons = render()
    out = Path(__file__).resolve().parent.parent / 'build' / 'icons_animals'
    out.mkdir(parents=True, exist_ok=True)
    SX, SY = 8, 4
    cw, ch = 240, 120
    sheet = [[BLACK] * (cw * 4) for _ in range(ch * 4)]
    for i, (name, rows) in enumerate(icons.items()):
        pixels = scale(rows, SX, SY)
        write_png(out / (name.lower().replace(' ', '_') + '.png'), pixels)
        x, y = (i % 4) * cw + 8, (i // 4) * ch + 4
        blit(sheet, pixels, x, y)
        label(sheet, name, x + (224 - (len(name) * 8 - 2)) // 2, y + 100)
    write_png(out / 'sheet.png', sheet)
    (out / 'icons.json').write_text(json.dumps(icons, indent=1) + '\n', encoding='utf-8')
    print(f'Wrote {len(icons)} icons, sheet.png and icons.json to {out}')


if __name__ == '__main__':
    main()
