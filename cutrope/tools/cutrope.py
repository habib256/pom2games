#!/usr/bin/env python3
"""CUTROPE -- the Python model of the game's physics and rules, the level
compiler and the constant emitter (dev/lib/physics).

The reference of src/phys.inc, bit for bit (tests/test_cutrope.py runs both
and compares the whole state tick after tick). `python3 tools/cutrope.py
src/cutconst.inc` writes the constants, the compiled levels, the sprites
and the jingles the 6502 assembles; `python3 tools/cutrope.py` plays the
levels' solutions on the model and prints them.

The world is the screen: x 16.8 (pixels 0..255 used), y 8.8 (rows 0..191).
Verlet points (verlet.Points, pins on): 0 = the candy (the only point that
touches the ground: VL_GROUND = 1), then each rope's pin and its inner
points, rope after rope; the points a level does not use stay pinned. A
rope of n links from its pin P: links (P, P+1), ..., (P+n-1, 0), all of
the rope's rest length (VL_CON_FIXED_K: gain 2^FIXED_K), the last one
ending on the candy, the heavy point (VL_CON_HEAVY_POINT = 0, shift HEAVY:
it moves (2^n - 1) / (2^n + 1) of what a rope point would).

A tick (Game.tick(cut, cx, cy, btn)), in PLAY only (WON / LOST: frozen):
  cut     the ropes in the mask `cut` (keys 1-3) and, with the button
          held, every rope with a link within CUT_R of the cursor (cx, cy)
          (near(): whole pixels, a box then |cross| <= CUT_R (|dx| + |dy|))
          are cut: their points pinned where they are (frozen, no longer
          linked or drawn: the rope is gone), event EV_CUT
  integrate   every point but the pinned ones (gravity, speed clamp)
  links   PASSES pass(es) of the links of the ropes still on, rope by rope,
          pin to candy
  ceiling no point above row CEIL (under the two text lines)
  ground  the candy against the level's segments (verlet_seg: platforms
          and spikes), friction vt -= vt >> FRICTION in contact
  rules   the candy off the field (x < 4, x >= 252 or beyond, y >= LOST_Y)
          -> LOST; each star not yet taken within STAR_R px (dx^2 + dy^2
          <= STAR_R^2, whole pixels) -> taken (EV_STAR); the candy's pixel
          in the frog's 14 x 14 box -> WON (EV_WON); a contact with a spike
          segment -> LOST (EV_LOST)

The rate: TICK_HZ ticks a second (vapor_pace: a tick every 2 video
frames); the constants are tuned at that rate (no derived ones).
"""
from pathlib import Path
import math
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(ROOT / 'dev/tools/audio'))
from verlet import Points, SegmentGround, constrain, emit  # noqa: E402
from verlet.fixed import l2q, s8  # noqa: E402
import tune as tunes  # noqa: E402

# --- the rate and the physics ------------------------------------------------------
TICK_HZ = 30
TICK_FRAMES = 60 // TICK_HZ             # video frames a tick (vapor_pace)
NPTS = 23                               # VL_NPOINTS: the candy + 22 rope points
NCON = 22                               # VL_NCON: links (3 ropes: 10 + 6 + 6)
NROPE = 3
NSEG = 8                                # segment slots (vl_sg_* in BSS)
GRAVITY = 0x0016                        # 8.8 px / tick^2 (~80 px/s^2)
VMAX = 0x0600                           # 6 px a tick: < RADIUS + DEPTH (no tunnelling)
FIXED_K = 5                             # gain 2^5: rigid in one pass for 16-px links
HEAVY = 1                               # the candy: (2 + 1) / (2 - 1) = 3 rope points
PASSES = 1                              # link passes a tick (the budget: see README)
CEIL = 18                               # row: below the two text lines
RADIUS, DEPTH, BOUNCE = 0x0380, 0x0400, 24   # the candy's disc against the segments
FRICTION = 3                            # on a platform: vt -= vt >> 3 a tick
STAR_R = 6                              # px: candy 3.5 + star 2.5
CUT_R = 2                               # px: the cursor's reach (L1-scaled, 2..2.8)
LOST_Y = 187                            # the candy's row from which it is lost
X_MIN, X_MAX = 4, 251                   # its columns while on the field
FROG_W = 14
PLAY, WON, LOST = 0, 1, 2
EV_CUT, EV_STAR, EV_WON, EV_LOST = 1, 2, 4, 8
SPIKE_H = 4                             # px: the teeth under a spike segment's line
CANDIES = 5                             # (cutrope.s) a game's candies

# --- the levels ----------------------------------------------------------------------
# ropes: (pin x, pin y, links, slack): the rope runs from the pin to the candy's
# start, its length slack x the distance, its inner points on a sag (whole px);
# stars: centres; frog: top left of its 14 x 14 box; segs: (x0, y0, x1, y1,
# kind) whole px, kind 0 = a platform (free side above: drawn left to right),
# 1 = spikes (horizontal: the line is the teeth's tips).
LEVELS = [
    dict(name='SWING', candy=(60, 60), ropes=[(110, 26, 4, 1.0)],
         stars=[(99, 90), (158, 99), (183, 121)], frog=(200, 150),
         segs=[(190, 164, 230, 164, 0)]),
    dict(name='TWO ROPES', candy=(128, 48), ropes=[(100, 24, 3, 1.0), (164, 24, 4, 1.3)],
         stars=[(74, 52), (132, 81), (148, 108)], frog=(156, 140),
         segs=[(146, 154, 186, 154, 0)]),
    dict(name='SPIKES', candy=(100, 60), ropes=[(66, 24, 4, 1.0), (134, 24, 4, 1.0)],
         stars=[(134, 80), (176, 82), (193, 105)], frog=(202, 128),
         segs=[(4, 182, 80, 182, 1), (80, 182, 156, 182, 1), (156, 182, 200, 182, 1),
               (190, 142, 232, 142, 0)]),
]
# the cycle bench (not played: tests poke it): one 10-link rope and two of 6
BENCH = dict(name='BENCH', candy=(128, 96), ropes=[(128, 20, 10, 1.0), (60, 40, 6, 1.0), (196, 40, 6, 1.0)],
             stars=[(20, 30), (30, 30), (40, 30)], frog=(230, 20), segs=[(4, 182, 76, 182, 1)])
NLEVEL = len(LEVELS)


def sag_points(p, c, n, slack):
    """The rope's n + 1 points from p to c (8.8) and its link length (px):
    straight at slack 1; else the shape it hangs in between the two ends
    (links slack x |pc| / n, relaxed with exact lengths from a parabola),
    so that the level starts without a jolt."""
    (px, py), (cx, cy) = p, c
    ln = slack * math.hypot(cx - px, cy - py) / n
    pts = [[px + (cx - px) * i / n, py + (cy - py) * i / n] for i in range(n + 1)]
    if slack > 1:
        for i in range(1, n):
            pts[i][1] += 2 * ln * slack * (i / n) * (1 - i / n) * n
        for _ in range(4000):
            for i in range(1, n):
                pts[i][1] += 0.05
            for i in range(n):
                a, b = pts[i], pts[i + 1]
                dx, dy = b[0] - a[0], b[1] - a[1]
                d = math.hypot(dx, dy) or 1e-9
                k = (d - ln) / d
                wa = 0 if i == 0 else (1 if i + 1 == n else 0.5)
                wb = 0 if i + 1 == n else (1 if i == 0 else 0.5)
                a[0] += wa * k * dx
                a[1] += wa * k * dy
                b[0] -= wb * k * dx
                b[1] -= wb * k * dy
    return [(int(round(x * 256)), int(round(y * 256))) for x, y in pts], ln


def seg_specs(segs):
    """(x0, y0, x1, y1) 8.8 for SegmentGround, the order of the level."""
    return [(x0 << 8, y0 << 8, x1 << 8, y1 << 8) for x0, y0, x1, y1, _ in segs]


def ground_of(segs):
    return SegmentGround(seg_specs(segs), radius=RADIUS, depth=DEPTH, bounce=BOUNCE)


def compile_level(lv):
    """The level record the 6502 loads (phys_load), bytes:
      nropes, candy x, y, 3 stars (x, y), frog x, y, nsegs,
      per rope: pin x, pin y, links n, l2q lo, hi, then the n - 1 inner
                points (x 8.8, y 8.8: xf, xl, yf, yh), pin side first,
      per segment: kind, x0, y0, x1, y1 (drawing), then its 14 bytes of the
                vl_sg_* tables (x0f x0l y0f y0h nx ny sl sh bx0l bx0h bx1l
                bx1h by0 by1, segments.py)."""
    ropes, segs = lv['ropes'], lv['segs']
    assert 1 <= len(ropes) <= NROPE and len(lv['stars']) == 3 and len(segs) <= NSEG
    out = [len(ropes), *lv['candy']]
    for s in lv['stars']:
        out += s
    out += [*lv['frog'], len(segs)]
    npts, ncon = 1, 0
    for px, py, n, slack in ropes:
        assert py >= CEIL and 1 <= n
        pts, ln = sag_points((px, py), lv['candy'], n, slack)
        q = l2q(ln)
        assert ln <= 45 and q < 65536
        out += [px, py, n, q & 0xFF, q >> 8]
        for x, y in pts[1:-1]:
            assert CEIL << 8 <= y <= 190 << 8 and 0 <= x <= 255 << 8
            out += [x & 0xFF, x >> 8, y & 0xFF, y >> 8]
        npts += n
        ncon += n
    assert npts <= NPTS and ncon <= NCON, (npts, ncon)
    if segs:
        g = ground_of(segs)
        rows = [vals for _, vals in g.tables()[:14]]
        for k, (x0, y0, x1, y1, kind) in enumerate(segs):
            assert kind == 0 or y0 == y1, 'spikes are horizontal'
            out += [kind, x0, y0, x1, y1]
            out += [int(r[k][1:]) & 0xFF if isinstance(r[k], str) else r[k] for r in rows]
    assert len(out) < 256, 'phys_load indexes the record with Y'
    return bytes(b & 0xFF for b in out)


LEVEL_BYTES = [compile_level(lv) for lv in LEVELS] + [compile_level(BENCH)]
BENCH_LEVEL = NLEVEL


class Level:
    """A level record parsed back (the model reads what the 6502 reads)."""

    def __init__(self, data):
        d = list(data)
        self.nropes, self.candy = d[0], (d[1], d[2])
        self.stars = [(d[3], d[4]), (d[5], d[6]), (d[7], d[8])]
        self.frog = (d[9], d[10])
        nseg, k = d[11], 12
        self.ropes = []                 # (pin x, y, n, l2q, inner points)
        for _ in range(self.nropes):
            px, py, n, q = d[k], d[k + 1], d[k + 2], d[k + 3] | d[k + 4] << 8
            k += 5
            inner = [(d[k + 4 * i] | d[k + 4 * i + 1] << 8, d[k + 4 * i + 2] | d[k + 4 * i + 3] << 8)
                     for i in range(n - 1)]
            k += 4 * (n - 1)
            self.ropes.append((px, py, n, q, inner))
        self.segs = []                  # (kind, x0, y0, x1, y1)
        for _ in range(nseg):
            self.segs.append(tuple(d[k:k + 5]))
            k += 19
        assert k == len(d)


class Game(Points):
    def __init__(self, level=0):
        super().__init__(NPTS, pins=True)
        self.load(level)

    def load(self, level):
        """phys_load: the level's points at rest, its links, its ground."""
        L = self.lv = Level(LEVEL_BYTES[level])
        for i in range(NPTS):
            self.place(i, 0, CEIL << 8)
            self.pin[i] = 1
        self.place(0, L.candy[0] << 8, L.candy[1] << 8)
        self.pin[0] = 0
        self.links = []                 # per rope: [(a, b, l2q)]
        self.first = []                 # per rope: its pin's point
        p = 1
        for px, py, n, q, inner in L.ropes:
            self.first.append(p)
            self.place(p, px << 8, py << 8)
            for i, (x, y) in enumerate(inner):
                self.place(p + 1 + i, x, y)
                self.pin[p + 1 + i] = 0
            self.links.append([(p + k, p + k + 1 if k < n - 1 else 0, q) for k in range(n)])
            p += n
        self.ground = ground_of([(x0, y0, x1, y1, kind) for kind, x0, y0, x1, y1 in L.segs]) if L.segs else None
        self.state, self.on, self.stars, self.nstar, self.ev = PLAY, (1 << L.nropes) - 1, 0, 0, 0
        self.gnd, self.sgi = 0, 0xFF

    def near(self, r, cx, cy):
        """The cursor within CUT_R of a link of rope r (whole pixels: xl, yh)."""
        x, y = self.x, self.y
        for a, b, _ in self.links[r]:
            ax, ay = (x[a] >> 8) & 0xFF, (y[a] >> 8) & 0xFF
            dx, dy = s8(((x[b] >> 8) & 0xFF) - ax), s8(((y[b] >> 8) & 0xFF) - ay)
            ux, uy = s8(cx - ax), s8(cy - ay)
            if not (min(0, dx) - CUT_R <= ux <= max(0, dx) + CUT_R):
                continue
            if not (min(0, dy) - CUT_R <= uy <= max(0, dy) + CUT_R):
                continue
            if abs(dx * uy - dy * ux) <= CUT_R * (abs(dx) + abs(dy)):
                return True
        return False

    def cut(self, r):
        for a, _, _ in self.links[r]:
            self.pin[a] = 1
        self.on &= ~(1 << r)
        self.ev |= EV_CUT

    def tick(self, cut=0, cx=0, cy=0, btn=0):
        self.ev = 0
        if self.state != PLAY:
            return
        for r in range(self.lv.nropes):
            if self.on >> r & 1 and (cut >> r & 1 or (btn and self.near(r, cx, cy))):
                self.cut(r)
        self.integrate_all(GRAVITY, VMAX, VMAX)
        for _ in range(PASSES):
            for r in range(self.lv.nropes):
                if self.on >> r & 1:
                    for a, b, q in self.links[r]:
                        constrain(self, a, b, q, 1 << FIXED_K, HEAVY if b == 0 else 0, fixed_k=FIXED_K)
        self.ceiling(CEIL << 8)
        self.gnd, self.sgi = 0, 0xFF
        if self.ground is not None:
            self.gnd = int(self.ground.contact(self, 0, lambda i, v: v - (v >> FRICTION)) is not None)
            self.sgi = self.ground.sgi[0]
        self.rules()

    def rules(self):
        xh, xl, yh = (self.x[0] >> 16) & 0xFF, (self.x[0] >> 8) & 0xFF, (self.y[0] >> 8) & 0xFF
        if xh or xl < X_MIN or xl > X_MAX or yh >= LOST_Y:
            self.state, self.ev = LOST, self.ev | EV_LOST
            return
        for s, (sx, sy) in enumerate(self.lv.stars):
            if not self.stars >> s & 1:
                dx, dy = abs(xl - sx), abs(yh - sy)
                if dx <= STAR_R and dy <= STAR_R and dx * dx + dy * dy <= STAR_R * STAR_R:
                    self.stars |= 1 << s
                    self.nstar += 1
                    self.ev |= EV_STAR
        fx, fy = self.lv.frog
        if fx <= xl < fx + FROG_W and fy <= yh < fy + FROG_W:
            self.state, self.ev = WON, self.ev | EV_WON
            return
        if self.gnd and self.lv.segs[self.sgi][0] == 1:
            self.state, self.ev = LOST, self.ev | EV_LOST

    def state_bytes(self):
        """The snapshot of tests/test_cutrope.py: the points (vl_xf..vl_oyh),
        vl_pin, then cr_state, cr_on, cr_stars, cr_nstar, cr_ev, vl_gnd,
        vl_sgi."""
        return self.soa_bytes() + bytes(self.pin) + bytes(
            [self.state, self.on, self.stars, self.nstar, self.ev, self.gnd, self.sgi])


# --- solutions: what the tests and the demo play ---------------------------------------
# per level: [(tick, cut mask)] -- the keys 1-3 at those ticks
SOLUTIONS = [
    [(45, 1)],                          # 3-star window: ticks 43-48
    [(6, 2), (105, 1)],                 # the right rope first (key 2); then 101-109
    [(4, 1), (52, 2)],                  # the left rope first; then 44-62
]


def play(level, cuts, ticks=400, cursor=None):
    """The model with key cuts {tick: mask} (and cursor inputs {tick: (cx,
    cy, btn)}): -> (game, ticks played, trace of the candy (x, y) px)."""
    g = Game(level)
    cuts = dict(cuts)
    trace = []
    for t in range(ticks):
        cx, cy, btn = (cursor or {}).get(t, (0, 0, 0))
        g.tick(cuts.get(t, 0), cx, cy, btn)
        trace.append((g.x[0] / 256, g.y[0] / 256))
        if g.state != PLAY:
            return g, t + 1, trace
    return g, ticks, trace


# --- the art ---------------------------------------------------------------------------
CANDY = ['..###..', '.#####.', '#######', '###.###', '#######', '.#####.', '..###..']
STAR = ['..#..', '.###.', '#####', '.###.', '..#..']
CURSOR = ['...#...', '...#...', '.......', '##...##', '.......', '...#...', '...#...']
FROG = ['..##......##..',
        '.#..#....#..#.',
        '.#.##....##.#.',
        '..##......##..',
        '.############.',
        '#............#',
        '#.##########.#',
        '#.#........#.#',
        '#..########..#',
        '#............#',
        '#............#',
        '.#..........#.',
        '..##########..',
        '.##........##.']


def preshift(rows):
    """pl_sprite data: W = bytes a row (enough for shift 6), H rows, 7 shifts
    of H x W bytes (bit 0 = leftmost pixel)."""
    w = (len(rows[0]) + 6 + 6) // 7
    out = []
    for sh in range(7):
        for r in rows:
            bits = sum(1 << (i + sh) for i, c in enumerate(r) if c == '#')
            out += [(bits >> (7 * k)) & 0x7F for k in range(w)]
    return w, len(rows), out


SPRITES = [('candy', CANDY), ('star', STAR), ('cursor', CURSOR), ('frog', FROG)]

# jingles (tune.asm: a tick of ~1/60 s of tone, then the program's own half
# frame; at 30 game ticks a second a tune tick lasts a game tick)
TUNES = [('tune_won', 'C6:2 E6:2 G6:2 C7:5'), ('tune_lost', 'G5:3 D#5:3 C5:6')]


def write_inc(path):
    consts = [('TICK_FRAMES', TICK_FRAMES, 'dec'), ('NPTS', NPTS, 'dec'), ('NCON', NCON, 'dec'),
              ('NROPE', NROPE, 'dec'), ('NSEG', NSEG, 'dec'), ('NLEVEL', NLEVEL, 'dec'),
              ('BENCH_LEVEL', BENCH_LEVEL, 'dec'), ('GRAVITY', GRAVITY), ('VMAX', VMAX),
              ('FIXED_K', FIXED_K, 'dec'), ('HEAVY', HEAVY, 'dec'), ('PASSES', PASSES, 'dec'),
              ('CEIL', CEIL << 8), ('RADIUS', RADIUS), ('DEPTH', DEPTH), ('BOUNCE', BOUNCE, 'dec'),
              ('FRICTION', FRICTION, 'dec'), ('STAR_R', STAR_R, 'dec'), ('CUT_R', CUT_R, 'dec'),
              ('LOST_Y', LOST_Y, 'dec'), ('X_MIN', X_MIN, 'dec'), ('X_MAX', X_MAX, 'dec'),
              ('FROG_W', FROG_W, 'dec'), ('SPIKE_H', SPIKE_H, 'dec'), ('CANDIES', CANDIES, 'dec'),
              ('PLAY', PLAY, 'dec'), ('WON', WON, 'dec'), ('LOST', LOST, 'dec'),
              ('EV_CUT', EV_CUT, 'dec'), ('EV_STAR', EV_STAR, 'dec'), ('EV_WON', EV_WON, 'dec'),
              ('EV_LOST', EV_LOST, 'dec')]
    tabs = ['; the levels (compile_level), then the cycle bench',
            ('lvl_lo', [f'<lvl{k}' for k in range(len(LEVEL_BYTES))]),
            ('lvl_hi', [f'>lvl{k}' for k in range(len(LEVEL_BYTES))])]
    for k, data in enumerate(LEVEL_BYTES):
        for i in range(0, len(data), 16):
            tabs.append((f'lvl{k}' if i == 0 else '', list(data[i:i + 16])))
    tabs.append('; sprites for pl_sprite: .byte W, H, then the 7 shifts')
    for name, rows in SPRITES:
        w, h, data = preshift(rows)
        tabs.append(f'{name}_desc: .byte {w}, {h}')
        tabs += [f'        .addr {name}_spr + {s * w * h}' for s in range(7)]
        for i in range(0, len(data), 14):
            tabs.append((f'{name}_spr' if i == 0 else '', data[i:i + 14]))
    tabs.append('; jingles (tune.asm events)')
    for label, text in TUNES:
        data = tunes.tune(text, 1)
        tabs += tunes.asm(label, data).rstrip('\n').split('\n')
    text = emit.inc_text(consts, tabs, header=['; generated by tools/cutrope.py -- do not edit'])
    text = text.replace('\n:        .byte', '\n         .byte')
    return emit.write_if_changed(path, text)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        write_inc(sys.argv[1])
    else:
        for k, sol in enumerate(SOLUTIONS):
            g, t, tr = play(k, sol)
            print(f'level {k + 1} {LEVELS[k]["name"]}: cuts {sol} -> {["PLAY", "WON", "LOST"][g.state]} '
                  f'after {t} ticks, {g.nstar} stars, candy at ({tr[-1][0]:.1f}, {tr[-1][1]:.1f})')
