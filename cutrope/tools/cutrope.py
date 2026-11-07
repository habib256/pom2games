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
  cut     the ropes in the mask `cut` (keys 1-3; the game's mouse adds the
          ropes its knife found along a swipe there too) and, with the button
          held, every rope with a link within CUT_R of the cursor (cx, cy)
          (near(): whole pixels, a box then |cross| <= CUT_R (|dx| + |dy|))
          are cut: their points pinned where they are (frozen, no longer
          linked or drawn: the rope is gone), event EV_CUT
  pop     the bubble holding the candy: mask bit 5 (key 6), or the button
          with the cursor within POP_R of the candy (EV_POP)
  puff    each cushion: waiting (cool -= 1), or mask bit 3 + c (keys 4-5) /
          the button within CUSH_R of it: PUFF_COOL ticks of wait, EV_PUFF,
          the candy's speed changed when it is ahead (puff())
  integrate   every point but the pinned ones (gravity, speed clamp); the
          candy in its bubble then floats (v -= v >> BUB_DRAG, vy -= BUOY)
  links   PASSES pass(es) of the links of the ropes still on, rope by rope,
          pin to candy
  ceiling no point above row CEIL (under the two text lines)
  ground  the candy against the level's segments (verlet_seg: platforms
          and spikes), friction vt -= vt >> FRICTION in contact
  rules   the candy off the field (x < 4, x >= 252 or beyond, y >= LOST_Y)
          -> LOST; the free bubble within STAR_R -> caught (EV_CATCH), the
          caught one above BUB_TOP -> LOST (floated away); each star not yet taken within STAR_R px (dx^2 + dy^2
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
from verlet.fixed import l2q, s8, s16  # noqa: E402
import tune as tunes  # noqa: E402

# --- the rate and the physics ------------------------------------------------------
TICK_HZ = 30
TICK_FRAMES = 60 // TICK_HZ             # video frames a tick (vapor_pace)
NPTS = 23                               # VL_NPOINTS: the candy + 22 rope points
NCON = 22                               # VL_NCON: links (3 ropes: 10 + 6 + 6)
NROPE = 3
NSEG = 8                                # segment slots (vl_sg_* in BSS)
LEVEL_MAX = 252                         # a level record: one disk sector after DOS's header
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
EV_CUT, EV_STAR, EV_WON, EV_LOST, EV_POP, EV_PUFF, EV_CATCH, EV_BOING = 1, 2, 4, 8, 16, 32, 64, 128
# segment kinds: a platform, spikes, a trampoline (horizontal: on a contact the
# candy leaves upwards at the vertical speed it came with, TRAMP_MIN at least;
# its speed along keeps what the contact left of it)
SEG_PLATFORM, SEG_SPIKES, SEG_TRAMP = 0, 1, 2
TRAMP_MIN = 0x0200
SPIKE_H = 4                             # px: the teeth under a spike segment's line
# the input mask (keys 1-6): bits 0-2 cut ropes 1-3, bits 3-4 puff cushions 1-2,
# bit 5 pops the bubble
NCUSH = 2
M_CUSH, M_POP = 8, 32
# the bubble (one a level at most): it catches the candy when the candy's pixel
# is within STAR_R of its centre (the stars' test); caught, the candy floats:
# after the integration its speed loses v >> BUB_DRAG and BUOY is taken off
# its vy (net up: BUOY - GRAVITY), terminal ~ 2^BUB_DRAG x that. Popped by key
# 6 or the button with the cursor within POP_R (box) of the candy; the candy
# caught and above row BUB_TOP has floated away: lost.
BUB_NONE, BUB_FREE, BUB_CAUGHT = 0, 1, 2
BUOY = 0x0030
BUB_DRAG = 3
BUB_TOP = CEIL + 4
POP_R = 7
# the air cushions (two a level at most): (x, y) the body's centre, dir 0 right,
# 1 down, 2 left, 3 up. A puff (key 4 / 5, or the button with the cursor within
# CUSH_R (box) of the centre; then PUFF_COOL ticks before the next one) pushes
# the candy when its pixel is ahead: along = 0 .. PUFF_LEN - 1 px on the axis,
# |across| <= PUFF_W + along / 4; its speed += PUFF[along >> 3] on the axis
# (before the integration).
DIRS = 'RDLU'
CUSH_R = 6
PUFF_COOL = 10
PUFF_SHOW = 4                           # (cutrope.s) ticks the puff is drawn
PUFF_LEN, PUFF_W = 80, 10
PUFF = [0x0200, 0x01D0, 0x01A0, 0x0170, 0x0140, 0x0110, 0x00E0, 0x00B0, 0x0090, 0x0070]
assert len(PUFF) == PUFF_LEN >> 3

# --- the levels (tools/levels.py: the data and a solution each) -------------------------
from levels import LEVELS, BENCH, SOLUTIONS  # noqa: E402
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
      nropes, candy x, y, 3 stars (x, y), frog x, y, nsegs, bubble x, y (x = 0:
      none), ncush, per cushion x, y, dir,
      per rope: pin x, pin y, links n, l2q lo, hi, then the n - 1 inner
                points (x 8.8, y 8.8: xf, xl, yf, yh), pin side first,
      per segment: kind, x0, y0, x1, y1 (drawing), then its 14 bytes of the
                vl_sg_* tables (x0f x0l y0f y0h nx ny sl sh bx0l bx0h bx1l
                bx1h by0 by1, segments.py)."""
    ropes, segs = lv['ropes'], lv['segs']
    cush = lv.get('cushions', [])
    bub = lv.get('bubble', (0, 0))
    assert 1 <= len(ropes) <= NROPE and len(lv['stars']) == 3 and len(segs) <= NSEG
    assert len(cush) <= NCUSH and (bub[0] == 0 or 8 <= bub[0] <= 247 and BUB_TOP + 6 <= bub[1] <= 184)
    out = [len(ropes), *lv['candy']]
    for s in lv['stars']:
        out += s
    out += [*lv['frog'], len(segs), *bub, len(cush)]
    for x, y, d in cush:
        assert 14 <= x <= 241 and 30 <= y <= 176, (x, y)
        out += [x, y, DIRS.index(d)]
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
            assert kind == SEG_PLATFORM or y0 == y1, 'spikes and trampolines are horizontal'
            out += [kind, x0, y0, x1, y1]
            out += [int(r[k][1:]) & 0xFF if isinstance(r[k], str) else r[k] for r in rows]
    assert len(out) <= LEVEL_MAX, 'a level fits its sector (after DOS\'s 4-byte header)'
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
        nseg = d[11]
        self.bubble = (d[12], d[13])
        ncush, k = d[14], 15
        self.cushions = [tuple(d[k + 3 * i:k + 3 * i + 3]) for i in range(ncush)]
        k += 3 * ncush
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


def within(xl, yh, cx, cy, r=STAR_R):
    """The stars' (and the bubble's) test: |dx|, |dy| <= r, dx^2 + dy^2 <= r^2."""
    dx, dy = abs(xl - cx), abs(yh - cy)
    return dx <= r and dy <= r and dx * dx + dy * dy <= r * r


def boxed(ax, ay, bx, by, r):
    return abs(ax - bx) <= r and abs(ay - by) <= r


class Game(Points):
    def __init__(self, level=0, data=None):
        super().__init__(NPTS, pins=True)
        self.load(level, data)

    def clone(self):
        g = Game.__new__(Game)
        g.x, g.y, g.ox, g.oy, g.pin = self.x[:], self.y[:], self.ox[:], self.oy[:], self.pin[:]
        g.y_high = False
        g.lv, g.links, g.first, g.ground = self.lv, self.links, self.first, self.ground
        g.state, g.on, g.stars, g.nstar, g.ev = self.state, self.on, self.stars, self.nstar, self.ev
        g.bub, g.cool, g.gnd, g.sgi = self.bub, self.cool[:], self.gnd, self.sgi
        return g

    def load(self, level, data=None):
        """phys_load: the level's points at rest, its links, its ground."""
        L = self.lv = Level(data if data is not None else LEVEL_BYTES[level])
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
        self.bub = BUB_FREE if L.bubble[0] else BUB_NONE
        self.cool = [0] * NCUSH
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

    def candy_px(self):
        return (self.x[0] >> 8) & 0xFF, (self.y[0] >> 8) & 0xFF

    def puff(self, c):
        """Cushion c puffs: the candy's speed changes when it is ahead."""
        ax, ay, d = self.lv.cushions[c]
        xl, yh = self.candy_px()
        along, across = [(xl - ax, yh - ay), (yh - ay, xl - ax), (ax - xl, yh - ay), (ay - yh, xl - ax)][d]
        if not (0 <= along < PUFF_LEN and abs(across) <= PUFF_W + (along >> 2)):
            return
        imp = PUFF[along >> 3]
        if d == 0:
            self.x[0] += imp
        elif d == 1:
            self.y[0] += imp
        elif d == 2:
            self.x[0] -= imp
        else:
            self.y[0] -= imp

    def tick(self, cut=0, cx=0, cy=0, btn=0):
        self.ev = 0
        if self.state != PLAY:
            return
        for r in range(self.lv.nropes):
            if self.on >> r & 1 and (cut >> r & 1 or (btn and self.near(r, cx, cy))):
                self.cut(r)
        if self.bub == BUB_CAUGHT and (cut & M_POP or (btn and boxed(cx, cy, *self.candy_px(), POP_R))):
            self.bub = BUB_NONE
            self.ev |= EV_POP
        for c, (ax, ay, _) in enumerate(self.lv.cushions):
            if self.cool[c]:
                self.cool[c] -= 1
            elif cut & (M_CUSH << c) or (btn and boxed(cx, cy, ax, ay, CUSH_R)):
                self.cool[c] = PUFF_COOL
                self.ev |= EV_PUFF
                self.puff(c)
        self.integrate_all(GRAVITY, VMAX, VMAX)
        if self.bub == BUB_CAUGHT:
            self.x[0] -= s16(self.x[0] - self.ox[0]) >> BUB_DRAG
            self.y[0] -= (s16(self.y[0] - self.oy[0]) >> BUB_DRAG) + BUOY
        for _ in range(PASSES):
            for r in range(self.lv.nropes):
                if self.on >> r & 1:
                    for a, b, q in self.links[r]:
                        constrain(self, a, b, q, 1 << FIXED_K, HEAVY if b == 0 else 0, fixed_k=FIXED_K)
        self.ceiling(CEIL << 8)
        self.gnd, self.sgi = 0, 0xFF
        if self.ground is not None:
            vin = s16(self.y[0] - self.oy[0])
            self.gnd = int(self.ground.contact(self, 0, lambda i, v: v - (v >> FRICTION)) is not None)
            self.sgi = self.ground.sgi[0]
            if self.gnd and self.lv.segs[self.sgi][0] == SEG_TRAMP:
                self.oy[0] = (self.y[0] + max(abs(vin), TRAMP_MIN)) & 0xFFFF
                self.ev |= EV_BOING
        self.rules()

    def rules(self):
        xh, xl, yh = (self.x[0] >> 16) & 0xFF, (self.x[0] >> 8) & 0xFF, (self.y[0] >> 8) & 0xFF
        if xh or xl < X_MIN or xl > X_MAX or yh >= LOST_Y:
            self.state, self.ev = LOST, self.ev | EV_LOST
            return
        if self.bub == BUB_FREE:
            if within(xl, yh, *self.lv.bubble):
                self.bub = BUB_CAUGHT
                self.ev |= EV_CATCH
        elif self.bub == BUB_CAUGHT and yh < BUB_TOP:
            self.state, self.ev = LOST, self.ev | EV_LOST
            return
        for s, (sx, sy) in enumerate(self.lv.stars):
            if not self.stars >> s & 1 and within(xl, yh, sx, sy):
                self.stars |= 1 << s
                self.nstar += 1
                self.ev |= EV_STAR
        fx, fy = self.lv.frog
        if fx <= xl < fx + FROG_W and fy <= yh < fy + FROG_W:
            self.state, self.ev = WON, self.ev | EV_WON
            return
        if self.gnd and self.lv.segs[self.sgi][0] == SEG_SPIKES:
            self.state, self.ev = LOST, self.ev | EV_LOST

    def state_bytes(self):
        """The snapshot of tests/test_cutrope.py: the points (vl_xf..vl_oyh),
        vl_pin, then cr_state, cr_on, cr_stars, cr_nstar, cr_ev, cr_bub,
        cr_cool (2), vl_gnd, vl_sgi."""
        return self.soa_bytes() + bytes(self.pin) + bytes(
            [self.state, self.on, self.stars, self.nstar, self.ev, self.bub, *self.cool, self.gnd, self.sgi])


# --- playing a schedule on the model ---------------------------------------------------
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


BUBBLE = ['...#####...',
          '..#.....#..',
          '.#.......#.',
          '#.........#',
          '#.........#',
          '#.........#',
          '#.........#',
          '#.........#',
          '.#.......#.',
          '..#.....#..',
          '...#####...']
# a cushion pointing right, its centre (0, 0): the bellows, then the nozzle
CUSH_SHAPE = [(-7, -4, 1, -4), (1, -4, 1, 4), (1, 4, -7, 4), (-7, 4, -7, -4), (-4, -4, -4, 4),
              (1, -2, 5, -3), (1, 2, 5, 3), (5, -3, 5, 3)]
# its puff (drawn PUFF_SHOW ticks)
PUFF_SHAPE = [(9, -4, 13, -6), (9, 0, 15, 0), (9, 4, 13, 6)]


def rot(line, d):
    """A line (x0, y0, x1, y1) of the right-pointing shape turned to
    direction d (R D L U: screen rows grow downwards)."""
    def r(x, y):
        return [(x, y), (-y, x), (-x, -y), (y, -x)][d]
    return [*r(*line[:2]), *r(*line[2:])]


SPRITES = [('candy', CANDY), ('star', STAR), ('cursor', CURSOR), ('frog', FROG), ('bubble', BUBBLE)]

# jingles (tune.asm: a tick of ~1/60 s of tone, then the program's own half
# frame; at 30 game ticks a second a tune tick lasts a game tick)
TUNES = [('tune_won', 'C6:2 E6:2 G6:2 C7:5'), ('tune_lost', 'G5:3 D#5:3 C5:6')]


def write_inc(path):
    consts = [('TICK_FRAMES', TICK_FRAMES, 'dec'), ('NPTS', NPTS, 'dec'), ('NCON', NCON, 'dec'),
              ('NROPE', NROPE, 'dec'), ('NSEG', NSEG, 'dec'), ('NLEVEL', NLEVEL, 'dec'),
              ('BENCH_LEVEL', BENCH_LEVEL, 'dec'), ('LEVEL_MAX', LEVEL_MAX, 'dec'),
              ('GRAVITY', GRAVITY), ('VMAX', VMAX),
              ('FIXED_K', FIXED_K, 'dec'), ('HEAVY', HEAVY, 'dec'), ('PASSES', PASSES, 'dec'),
              ('CEIL', CEIL << 8), ('RADIUS', RADIUS), ('DEPTH', DEPTH), ('BOUNCE', BOUNCE, 'dec'),
              ('FRICTION', FRICTION, 'dec'), ('STAR_R', STAR_R, 'dec'), ('CUT_R', CUT_R, 'dec'),
              ('LOST_Y', LOST_Y, 'dec'), ('X_MIN', X_MIN, 'dec'), ('X_MAX', X_MAX, 'dec'),
              ('FROG_W', FROG_W, 'dec'), ('SPIKE_H', SPIKE_H, 'dec'),
              ('PLAY', PLAY, 'dec'), ('WON', WON, 'dec'), ('LOST', LOST, 'dec'),
              ('EV_CUT', EV_CUT, 'dec'), ('EV_STAR', EV_STAR, 'dec'), ('EV_WON', EV_WON, 'dec'),
              ('EV_LOST', EV_LOST, 'dec'), ('EV_POP', EV_POP, 'dec'), ('EV_PUFF', EV_PUFF, 'dec'),
              ('EV_CATCH', EV_CATCH, 'dec'), ('EV_BOING', EV_BOING, 'dec'), ('SEG_SPIKES', SEG_SPIKES, 'dec'),
              ('SEG_TRAMP', SEG_TRAMP, 'dec'), ('TRAMP_MIN', TRAMP_MIN), ('NCUSH', NCUSH, 'dec'), ('M_CUSH', M_CUSH, 'dec'),
              ('M_POP', M_POP, 'dec'), ('BUB_NONE', BUB_NONE, 'dec'), ('BUB_FREE', BUB_FREE, 'dec'),
              ('BUB_CAUGHT', BUB_CAUGHT, 'dec'), ('BUOY', BUOY), ('BUB_DRAG', BUB_DRAG, 'dec'),
              ('BUB_TOP', BUB_TOP, 'dec'), ('POP_R', POP_R, 'dec'), ('CUSH_R', CUSH_R, 'dec'),
              ('PUFF_COOL', PUFF_COOL, 'dec'), ('PUFF_SHOW', PUFF_SHOW, 'dec'),
              ('PUFF_LEN', PUFF_LEN, 'dec'), ('PUFF_W', PUFF_W, 'dec')]
    tabs = ['; the speed change of a puff by distance (along >> 3)',
            ('puff_lo', [v & 0xFF for v in PUFF]), ('puff_hi', [v >> 8 for v in PUFF])]
    tabs.append('; the cushions\' lines, per direction (R D L U): x0, y0, x1, y1 from the centre')
    tabs.append(('cush_lines', [b & 0xFF for d in range(4) for ln in CUSH_SHAPE for b in rot(ln, d)]))
    tabs.append(('puff_lines', [b & 0xFF for d in range(4) for ln in PUFF_SHAPE for b in rot(ln, d)]))
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
    consts += [('CUSH_NL', len(CUSH_SHAPE), 'dec'), ('PUFF_NL', len(PUFF_SHAPE), 'dec')]
    text = emit.inc_text(consts, tabs, header=['; generated by tools/cutrope.py -- do not edit'])
    text = text.replace('\n:        .byte', '\n         .byte')
    return emit.write_if_changed(path, text)


def write_levels(path):
    """The LEVELS file: level k (then the bench) in the k-th sector, after
    the 4 bytes DOS's binary header takes from the first one: the payload
    holds level k at 256 k (cutrope.s reads sector k, the record at +4)."""
    out = bytearray()
    for k, data in enumerate(LEVEL_BYTES):
        out += bytes(256 * k - len(out)) + data if k else data
    out += bytes(-(len(out) + 4) % 256)
    Path(path).write_bytes(bytes(out))


if __name__ == '__main__':
    if '--solve' in sys.argv:
        import solve
        solve.main(sys.argv[1:])
    elif len(sys.argv) > 2 and sys.argv[1] == '--levels':
        write_levels(sys.argv[2])
    elif len(sys.argv) > 2 and sys.argv[1] == '--save':
        Path(sys.argv[2]).write_bytes(bytes(256 - 4))     # CUTSAVE: one sector, nothing won
    elif len(sys.argv) > 1:
        write_inc(sys.argv[1])
    else:
        for k, sol in enumerate(SOLUTIONS):
            g, t, tr = play(k, sol)
            print(f'level {k + 1} {LEVELS[k]["name"]}: keys {sol} -> {["PLAY", "WON", "LOST"][g.state]} '
                  f'after {t} ticks, {g.nstar} stars, candy at ({tr[-1][0]:.1f}, {tr[-1][1]:.1f})')
