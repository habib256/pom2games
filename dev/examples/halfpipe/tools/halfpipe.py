#!/usr/bin/env python3
"""HALFPIPE -- the Python model of the demo's physics (dev/lib/physics).

The reference of src/phys.inc, bit for bit (tests/test_halfpipe.py runs
both and compares the state tick after tick). Design and tune here, then
`python3 tools/halfpipe.py src/pipeconst.inc` writes the constants and
tables the 6502 side assembles (verlet.emit).

The pipe is a SegmentGround (lib/physics verlet_seg.asm): decks, vertical
lips, two quarter pipes of six segments each and a flat bottom, plus the
screen-edge walls; the normals are near-unit integer vectors (|n|^2 within
a few units of 4096), so a wheel rolling on a segment keeps its speed.
Each joint of a quarter turns by 10-15 degrees: a wheel crossing it loses
the part of its speed into the next segment (1 - cos), the pump gives it
back.

The rider is three Verlet points: 0 = rear wheel, 1 = front wheel, 2 =
body, an exact 6-8-10 triangle (wheels 12 px apart, body 8 px above) of
fixed-gain links. A tick (Rider.tick(pump, lean)):

  riding   integrate (gravity); in the air: pair damping of the wheels
           (the spin fades), lean turns the wheels' axis (vl_turn_pair);
           2 constraint passes; the segment ground for the 3 points (the
           tangent hook pumps: a wheel going up a curve or a wall gets
           PUMP_K more tangential speed while the pump is on); 1 pass;
           the ceiling; then the rules:
             the body touches the pipe                          -> crash
             no wheel down: air += 1, the octant of the wheels' axis
                            is followed (rot += -1 / 0 / +1)
             a wheel down after AIR_MIN ticks or more in the air: a
               landing; the body less than LAND_MIN along the normal
               of that wheel's segment (upside down)           -> crash
               else, if the body went above the lip row (peak < LIP_Y),
               the trick: points = 10 * min(air / 16, 9) +
               100 * min(spins, 9), spins = (|rot| + 4) / 8, score += it
             then air = rot = 0
  crashed  the links break: each point flies on its own (no links, no
           pump), timer counts to 255
"""
from pathlib import Path
import math
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'tools'))
from verlet import Points, Constraint, SegmentGround, tables, emit  # noqa: E402
from verlet.fixed import s16  # noqa: E402

# --- the pipe ---------------------------------------------------------------------
LIP_Y = 80                              # deck row
BOTTOM_Y = 182                          # flat bottom row
LEFT_X, RIGHT_X = 30, 226               # the vertical lips
EDGE_L, EDGE_R = 3, 252                 # screen-edge walls
TOP_Y = 17                              # the ceiling row (HUD above)
SEG_LEN = 12                            # px, each curve segment
# directions of the left quarter's segments, degrees from straight down
# (those of near-unit normals: 9.90 = (63, 11), 24.96 = (58, 27), 38.66 = (50, 40))
QUARTER = [9.90, 24.96, 38.66, 51.34, 65.04, 80.10]


def quarter_drop():
    return SEG_LEN * sum(math.cos(math.radians(a)) for a in QUARTER), \
        SEG_LEN * sum(math.sin(math.radians(a)) for a in QUARTER)


def pipe_points():
    """The inside of the pipe, left deck to right deck (free side above:
    on the left of the direction as seen on screen)."""
    dy, dx = quarter_drop()
    wall_y = BOTTOM_Y - dy              # where the quarters start
    pts = [(EDGE_L, LIP_Y), (LEFT_X, LIP_Y), (LEFT_X, wall_y)]
    x, y = LEFT_X, wall_y
    for a in QUARTER:
        x += SEG_LEN * math.sin(math.radians(a))
        y += SEG_LEN * math.cos(math.radians(a))
        pts.append((x, y))
    mid = (LEFT_X + RIGHT_X) / 2
    pts.append((mid, BOTTOM_Y))         # the bottom in two segments
    pts.append((RIGHT_X - dx, BOTTOM_Y))
    x, y = RIGHT_X - dx, BOTTOM_Y
    for a in reversed(QUARTER):
        x += SEG_LEN * math.sin(math.radians(a))
        y -= SEG_LEN * math.cos(math.radians(a))
        pts.append((x, y))
    pts += [(RIGHT_X, LIP_Y), (EDGE_R, LIP_Y)]
    return pts


RADIUS, DEPTH, BOUNCE = 0x0200, 0x0400, 16
CACHE = 0x0200                          # VL_SEG_CACHE: 2 px from the ends


def pipe():
    kw = dict(radius=RADIUS, depth=DEPTH, bounce=BOUNCE, cache=CACHE)
    main = SegmentGround.from_polyline(pipe_points(), **kw)
    edges = [SegmentGround.from_polyline([(EDGE_L, TOP_Y), (EDGE_L, LIP_Y)], **kw),
             SegmentGround.from_polyline([(EDGE_R, LIP_Y), (EDGE_R, TOP_Y)], **kw)]
    return SegmentGround(main.specs() + [s for e in edges for s in e.specs()], **kw)


PIPE = pipe()
CURVES = [k for k, sg in enumerate(PIPE.segs) if sg.nx not in (0, 64, -64) or sg.ny not in (0, 64, -64)]

# --- the rider --------------------------------------------------------------------
HALF, BODY_UP = 6, 8                    # px: the 6-8-10 triangle
FIXED_K = 6
LINKS = [Constraint(0, 1, 2 * HALF, fixed_k=FIXED_K),
         Constraint(0, 2, 10, fixed_k=FIXED_K),
         Constraint(1, 2, 10, fixed_k=FIXED_K)]
GRAVITY = 0x000C                        # 8.8 px / tick^2
VMAX = 0x0600
PUMP_K = 0x0014                         # tangential speed a pumping wheel gains a tick (going up)
ROT_K = 5                               # vl_turn of a lean, a tick
SPIN_DAMP = 3                           # vl_pair_damp in the air
AIR_MIN = 8                             # ticks in the air for a landing to count
LAND_MIN = 0x0300                       # the body this far along the normal at least (8.8)
KICK = [(-0x0080, -0x0100), (0x0080, -0x00C0), (0x0010, -0x0140)]
# the start: on the left wall, facing down (rear wheel, front wheel, body: px)
START = [(LEFT_X + 2, LIP_Y + 8), (LEFT_X + 2, LIP_Y + 20), (LEFT_X + 10, LIP_Y + 14)]
START_OCT = 1                           # octant(0, 12): the axis points down
RIDE, CRASHED = 0, 1


def octant(dx, dy):
    """0..7 counter-clockwise on screen... of the vector (dx, dy) (rows down):
    the 6502's test order (signs, then |dx| > |dy|)."""
    ax, ay = abs(dx), abs(dy)
    if dy >= 0:
        if dx >= 0:
            return 0 if ax > ay else 1
        return 2 if ay >= ax else 3
    if dx < 0:
        return 4 if ax > ay else 5
    return 6 if ay >= ax else 7


class Rider(Points):
    def __init__(self, start=START):
        super().__init__(3)
        self.g = SegmentGround(PIPE.specs(), radius=RADIUS, depth=DEPTH, bounce=BOUNCE, cache=CACHE)
        for i, (x, y) in enumerate(start):
            self.place(i, x << 8, y << 8)
        self.status, self.timer = RIDE, 0
        self.air, self.rot, self.oct = 0, 0, START_OCT
        self.score, self.last, self.spins, self.peak = 0, 0, 0, 255
        self.gnd = [0, 0, 0]
        self.pumping = 0
        assert octant(*self.delta(0, 1)) == START_OCT

    # the tangent hook: a wheel going up (vt and nx of opposite signs, nx != 0)
    def _hook(self, i, vt):
        if self.pumping and i < 2:
            nx = self.g.segs[self.g.hit].nx
            if nx and (vt < 0) != (nx < 0):
                vt = vt + PUMP_K if vt >= 0 else vt - PUMP_K
        return vt

    def _ground(self):
        g = self.g
        for i in range(3):
            self.gnd[i] = int(g.contact(self, i, self._hook) is not None)

    def tick(self, pump=0, lean=0):
        if self.status == CRASHED:
            self.pumping = 0
            self.integrate_all(GRAVITY, VMAX, VMAX)
            self._ground()
            self.ceiling(TOP_Y << 8)
            if self.timer < 255:
                self.timer += 1
            return
        self.pumping = pump
        self.integrate_all(GRAVITY, VMAX, VMAX)
        if self.air:
            self.pair_damp(0, 1, SPIN_DAMP)
            if lean:
                self.turn_pair(0, 1, ROT_K if lean > 0 else -ROT_K)
        for _ in range(2):
            for c in LINKS:
                c.apply(self)
        self._ground()
        for c in LINKS:
            c.apply(self)
        self.ceiling(TOP_Y << 8)
        self._rules()

    def _rules(self):
        g = self.gnd
        if g[2]:
            return self.crash()
        if not (g[0] or g[1]):
            if self.air < 255:
                self.air += 1
            o = octant(*self.delta(0, 1))
            self.rot = (self.rot + ((o - self.oct + 4) & 7) - 4) & 0xFF
            self.oct = o
            row = self.y[2] >> 8
            if row < self.peak:
                self.peak = row
            return
        if self.air >= AIR_MIN:
            w = 0 if g[0] else 1
            sg = self.g.segs[self.g.sgi[w]]
            bx, by = self.delta(w, 2)
            if s16((bx * sg.nx + by * sg.ny) >> 6) < LAND_MIN:
                return self.crash()
            if self.peak >= LIP_Y:      # not above the lip: no trick
                return self._reset()
            r = self.rot - 256 if self.rot & 0x80 else self.rot
            spins = (abs(r) + 4) >> 3
            self.spins = spins
            self.last = 10 * min(self.air >> 4, 9) + 100 * min(spins, 9)
            self.score = min(self.score + self.last, 999999)
        self._reset()

    def _reset(self):
        self.air, self.rot = 0, 0
        self.oct = octant(*self.delta(0, 1))
        self.peak = 255

    def crash(self):
        self.status, self.timer = CRASHED, 0
        for i, (kx, ky) in enumerate(KICK):
            self.ox[i] -= kx
            self.oy[i] -= ky

    def state_bytes(self):
        """The snapshot of tests/test_halfpipe.py: the points (vl_xf..vl_oyh),
        vl_gnd (3), vl_sgi (3), then hp_status, hp_timer, hp_air, hp_rot,
        hp_oct, hp_spins, hp_peak, hp_score (3 bytes BCD, low first),
        hp_last (2 bytes BCD)."""
        sgi = [self.g.sgi.get(i, 0xFF) for i in range(3)]
        return self.soa_bytes() + bytes(self.gnd + sgi + [self.status, self.timer, self.air, self.rot,
                                                          self.oct, self.spins, self.peak]) + \
            bcd(self.score, 3) + bcd(self.last, 2)


def bcd(v, n):
    s = f'{v:0{2 * n}d}'[-2 * n:]
    return bytes(int(s[2 * k:2 * k + 2], 16) for k in range(n - 1, -1, -1))


# --- a scripted rider (tests, tuning) ---------------------------------------------
def pumper(p, k):
    """Pump whenever a wheel is down: (pump, lean)."""
    return (1 if (p.gnd[0] or p.gnd[1]) else 0), 0


def ride(pilot=pumper, ticks=1500, start=START):
    p = Rider(start)
    inputs = []
    for k in range(ticks):
        pump, lean = pilot(p, k)
        inputs.append((pump, lean))
        p.tick(pump, lean)
    return p, inputs


# --- the 6502 constants -------------------------------------------------------------
def write_inc(path):
    tab = tables(LINKS)
    g = PIPE
    consts = [('GRAVITY', GRAVITY), ('VMAX', VMAX), ('ROT_K', ROT_K, 'dec'), ('SPIN_DAMP', SPIN_DAMP, 'dec'),
              ('FIXED_K', FIXED_K, 'dec'), ('RADIUS', RADIUS), ('BOUNCE', BOUNCE, 'dec'),
              ('PUMP_K', PUMP_K), ('AIR_MIN', AIR_MIN, 'dec'), ('LAND_MIN', LAND_MIN),
              ('TOP_Y', TOP_Y << 8), ('LIP_Y', LIP_Y, 'dec'), ('START_OCT', START_OCT, 'dec'), ('HALF', HALF, 'dec'), ('BODY_UP', BODY_UP, 'dec'),
              *g.consts(),
              ('NDRAW', g.n, 'dec')]
    tabs = ['; links (verlet.tables, VL_CON_FIXED_K: no k8)',
            ('vl_con_a', tab['con_a']), ('vl_con_b', tab['con_b']),
            ('vl_con_l2l', emit.lo(tab['con_l2'])), ('vl_con_l2h', emit.hi(tab['con_l2'])),
            '; the pipe: segments (verlet.SegmentGround.tables)', *g.tables(),
            '; the pipe as drawn: segment ends (whole px)',
            ('pipe_x0', [min(255, round(sg.x0 / 256)) for sg in g.segs]),
            ('pipe_y0', [round(sg.y0 / 256) for sg in g.segs]),
            ('pipe_x1', [min(255, round(sg.x1 / 256)) for sg in g.segs]),
            ('pipe_y1', [round(sg.y1 / 256) for sg in g.segs]),
            '; the start (px)', ('start_x', [p[0] for p in START]), ('start_y', [p[1] for p in START]),
            '; the crash: speed kicks of the three points (8.8)',
            ('kick_xl', emit.lo([k[0] for k in KICK])), ('kick_xh', emit.hi([k[0] for k in KICK])),
            ('kick_yl', emit.lo([k[1] for k in KICK])), ('kick_yh', emit.hi([k[1] for k in KICK]))]
    text = emit.inc_text(consts, tabs, header=['; generated by tools/halfpipe.py -- do not edit'])
    return emit.write_if_changed(path, text)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        write_inc(sys.argv[1])
    else:
        for sg in PIPE.segs:
            print(sg, sg.nx * sg.nx + sg.ny * sg.ny - 4096)
        p, inp = ride(ticks=1500)
        print(f'pumping 1500 ticks: status {p.status} score {p.score}')
