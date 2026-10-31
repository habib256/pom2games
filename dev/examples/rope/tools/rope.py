#!/usr/bin/env python3
"""ROPE -- the Python model of the rope toy's physics (dev/lib/physics).

The reference of src/phys.inc, bit for bit (tests/test_rope.py runs both
and compares the state tick after tick). `python3 tools/rope.py
src/ropeconst.inc` writes the constants and tables the 6502 assembles.

Nine Verlet points: 0 = the pin (VL_PIN: the program moves it, x = ox,
y = oy), 1..7 the rope, 8 = the weight. Eight links of LINK px with the
fixed gain 2^FIXED_K (VL_CON_FIXED_K, no k8 table); the last one ends on
the weight, a heavy point (VL_CON_HEAVY_POINT, shift HEAVY: it moves 3/5 of
what a rope point would). The world is the screen (y 8.8, rows 0..191),
with a height-map floor near the bottom.

A tick (Rope.tick(mv, mode, cut)), the inputs being the wanted state:
  cut 1 -> 0  the weight is put back under point 7, at rest (a link can
              only pull what is within 45 px)
  pin         x += mv * PIN_SPEED (clamped PIN_X0..PIN_X1), y one step of
              PIN_STEP rows toward PIN_Y[mode]; at rest (x = ox, y = oy)
  integrate   every point but the pin (gravity, speed clamp)
  links       2 passes of the 8 links (7 when cut), the ceiling, the walls
              (x < LEFT_WALL, x < 0 included: x = ox = LEFT_WALL; x >=
              RIGHT_WALL px or beyond 255: x = ox = RIGHT_WALL): the
              ground probes stay within the height map
  ground      mode 0 (swing): the weight only; mode 1 (floor): points 1..8
              (the rope lies on the floor); friction vt -= vt >> FRICTION
"""
from pathlib import Path
import math
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'tools'))
from verlet import Points, Constraint, HeightMap, tables, emit  # noqa: E402

N = 9
PIN, WEIGHT = 0, 8
LINK = 11                               # px: 88 px of rope
FIXED_K = 6
HEAVY = 2                               # the weight: (4 + 1) / (4 - 1) = 5/3 of a rope point
LINKS = [Constraint(i, i + 1, LINK, fixed_k=FIXED_K, heavy=HEAVY if i + 1 == WEIGHT else 0)
         for i in range(N - 1)]
GRAVITY = 0x0018
VMAX = 0x0600
PIN_SPEED = 2                           # px a tick
PIN_X0, PIN_X1 = 12, 243
PIN_Y = [28, 128]                       # rows: swing, floor
PIN_STEP = 2
START_X = 128
LEFT_WALL, RIGHT_WALL = 4, 251          # whole px: the height map's ends
CEIL = 18                               # row: below the two text lines
RADIUS, PROBE, SLOPE_MAX, FAR, BOUNCE = 0x0180, 2, 15, 0x1000, 24
FRICTION = 2


def terrain():
    """The floor: rows 168..186, a bump and a dip."""
    h = []
    for x in range(256):
        y = 178 + 5 * math.sin(x / 17.0) + 3 * math.sin(x / 7.0 + 1)
        y -= 8 * math.exp(-((x - 70) / 14.0) ** 2) - 6 * math.exp(-((x - 190) / 12.0) ** 2)
        h.append(int(round(y)))
    for x in range(2, 254):
        assert abs(h[x + 2] - h[x - 2]) < 128
    return h


HEIGHTS = terrain()


class Rope(Points):
    def __init__(self, x=START_X, mode=0):
        super().__init__(N, pins=True)
        self.pin[PIN] = 1
        self.hm = HeightMap(HEIGHTS, SLOPE_MAX, PROBE, RADIUS, FAR, BOUNCE)
        self.px, self.py = x, PIN_Y[mode]
        self.mode, self.cut = mode, 0
        for i in range(N):
            self.place(i, x << 8, (self.py + LINK * i) << 8)
        self.gnd = [0] * N

    def _attach(self):
        """The weight under point 7, at rest."""
        a = WEIGHT - 1
        self.place(WEIGHT, self.x[a], self.y[a] + (LINK << 8))

    def walls(self):
        for i in range(N):
            xh, xl = (self.x[i] >> 16) & 0xFF, (self.x[i] >> 8) & 0xFF
            if xh == 0xFF or (xh == 0 and xl < LEFT_WALL):
                self.x[i] = self.ox[i] = LEFT_WALL << 8
            elif xh or xl >= RIGHT_WALL:
                self.x[i] = self.ox[i] = RIGHT_WALL << 8

    def tick(self, mv=0, mode=0, cut=0):
        if self.cut and not cut:
            self._attach()
        self.cut, self.mode = cut, mode
        self.px = max(PIN_X0, min(PIN_X1, self.px + PIN_SPEED * mv))
        t = PIN_Y[mode]
        if self.py < t:
            self.py = min(t, self.py + PIN_STEP)
        elif self.py > t:
            self.py = max(t, self.py - PIN_STEP)
        self.place(PIN, self.px << 8, self.py << 8)
        self.integrate_all(GRAVITY, VMAX, VMAX)
        links = LINKS[:-1] if cut else LINKS
        for _ in range(2):
            for c in links:
                c.apply(self)
        self.ceiling(CEIL << 8)
        self.walls()
        self.gnd = [0] * N
        first = 1 if mode else WEIGHT
        for i in range(first, N):
            self.gnd[i] = int(self.hm.contact(self, i, lambda i, v: v - (v >> FRICTION)) is not None)

    def state_bytes(self):
        """The snapshot of tests/test_rope.py: the points (vl_xf..vl_oyh),
        then rp_px, rp_py, rp_mode, rp_cut, vl_gnd (9)."""
        return self.soa_bytes() + bytes([self.px, self.py, self.mode, self.cut] + self.gnd)


def write_inc(path):
    tab = tables(LINKS)
    hm = HeightMap((), SLOPE_MAX, PROBE)
    consts = [('GRAVITY', GRAVITY), ('VMAX', VMAX), ('FIXED_K', FIXED_K, 'dec'), ('HEAVY', HEAVY, 'dec'),
              ('LINK', LINK, 'dec'), ('PIN_SPEED', PIN_SPEED, 'dec'), ('PIN_X0', PIN_X0, 'dec'),
              ('PIN_X1', PIN_X1, 'dec'), ('PIN_Y0', PIN_Y[0], 'dec'), ('PIN_Y1', PIN_Y[1], 'dec'),
              ('PIN_STEP', PIN_STEP, 'dec'), ('START_X', START_X, 'dec'), ('RADIUS', RADIUS),
              ('LEFT_WALL', LEFT_WALL, 'dec'), ('RIGHT_WALL', RIGHT_WALL, 'dec'), ('CEIL', CEIL << 8),
              ('PROBE', PROBE, 'dec'), ('SLOPE_MAX', SLOPE_MAX, 'dec'), ('FAR', FAR),
              ('BOUNCE', BOUNCE, 'dec'), ('FRICTION', FRICTION, 'dec')]
    tabs = ['; links (verlet.tables, VL_CON_FIXED_K: no k8)',
            ('vl_con_a', tab['con_a']), ('vl_con_b', tab['con_b']),
            ('vl_con_l2l', emit.lo(tab['con_l2'])), ('vl_con_l2h', emit.hi(tab['con_l2'])),
            '; ground normals, slopes -SLOPE_MAX..SLOPE_MAX (64 = 1.0)',
            ('vl_norm_x', emit.sb(hm.nx)), ('vl_norm_y', emit.sb(hm.ny)),
            '; the floor: a row per column']
    for k in range(0, 256, 16):
        tabs.append(('heights' if k == 0 else '', HEIGHTS[k:k + 16]))
    text = emit.inc_text(consts, tabs, header=['; generated by tools/rope.py -- do not edit'])
    text = text.replace('\n:        .byte', '\n         .byte')
    return emit.write_if_changed(path, text)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        write_inc(sys.argv[1])
    else:
        r = Rope()
        for k in range(400):
            r.tick(1 if k < 40 else -1 if k < 90 else 0)
        sag = (r.y[WEIGHT] - r.y[PIN]) / 256
        print(f'swing: pin at {r.px}, weight {r.x[WEIGHT] / 256:.1f}, {sag:.1f} px below (rope {LINK * 8} px)')
        for k in range(300):
            r.tick(0, 1)
        print(f'floor: points on the ground {sum(r.gnd)}, weight row {r.y[WEIGHT] / 256:.1f}')
        for k in range(200):
            r.tick(0, 0, 1)
        print(f'cut: weight at ({r.x[WEIGHT] / 256:.1f}, {r.y[WEIGHT] / 256:.1f}), on the ground {r.gnd[WEIGHT]}')
