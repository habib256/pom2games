#!/usr/bin/env python3
"""LANDER -- the Python model of the demo's physics (dev/lib/physics).

The reference of src/phys.inc, bit for bit (tests/test_lander.py runs both
and compares the state tick after tick). Design and tune here, then
`python3 tools/lander.py src/landconst.inc` writes the constants and
tables the 6502 side assembles.

The lander is three Verlet points: 0 = left leg, 1 = right leg, 2 = top,
an exact 6-8-10 triangle (legs 12 px apart, top 8 px above): every delta of
the rest shape is a multiple of a quarter pixel, so the fixed-gain links
(VL_CON_FIXED_K) see no error at all and the lander falls without turning.
The engine pushes the three points along the perpendicular of the legs'
axis (vl_thrust_perp + vl_push_all: a pure translation, no torque); the
turn keys turn the legs' axis (vl_turn_pair) and vl_pair_damp makes the
spin fade, so the lander turns while a key is held and stops after.

The world is 256 px wide and WORLD_H rows tall (y in 16.8: VL_Y_HIGH); the
ground is the height map + GROUND_BASE (VL_GROUND_BASE), with flat pads.
A tick (Lander.tick(thr, rot)):

  flying   vy = speed of the top before the tick; integrate (gravity, the
           left wall), the right wall, pair damping, turn, thrust (fuel),
           2 constraint passes, the ground for the 3 points (friction),
           1 pass, the ceiling; then the rules:
             the top touches the ground                      -> crash
             a leg touches after a tick without contact and
               vy > V_SAFE or |tilt| > TILT_MAX               -> crash
             a leg down: |tilt| > TILT_MAX                    -> crash
                         SETTLE ticks with a leg down (a resting leg
                         leaves the ground now and then: only a tick
                         with both legs up starts again): both legs on
                         the same pad -> landed, else -> crash
  crashed  the links break: each point gets a kick (KICK), then flies,
           bounces and slides on its own (no constraints); timer counts
  landed   nothing moves
tilt = y(right leg) - y(left leg), 8.8.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'tools'))
from verlet import Points, Constraint, HeightMap, tables, emit  # noqa: E402
from verlet.fixed import s16  # noqa: E402

# --- world ------------------------------------------------------------------------
WORLD_W, WORLD_H = 256, 536
GROUND_BASE = 280                       # ground row = h[x] + GROUND_BASE
LEFT_WALL, RIGHT_WALL = 4, 251          # whole px
CEIL = 2                                # row
# pads: (first column, last column, ground row)
PADS = [(20, 55, 500), (116, 143, 438), (196, 219, 400)]


def terrain():
    """256 ground rows: hills and peaks between three flat pads."""
    import math
    h = []
    for x in range(WORLD_W):
        y = 470 + 30 * math.sin(x / 13.0) + 22 * math.sin(x / 5.3 + 1) + 12 * math.sin(x / 2.1)
        # peaks around pad C, a plateau under pad B
        y -= 70 * math.exp(-((x - 180) / 9.0) ** 2) + 60 * math.exp(-((x - 236) / 8.0) ** 2)
        y -= 40 * math.exp(-((x - 100) / 10.0) ** 2)
        h.append(int(round(y)))
    for x0, x1, row in PADS:            # the pads, and a ramp of 6 px to them
        for x in range(x0, x1 + 1):
            h[x] = row
        for k in range(1, 7):
            for x, w in ((x0 - k, k / 7), (x1 + k, k / 7)):
                if 0 <= x < WORLD_W:
                    h[x] = int(round(row + (h[x] - row) * w))
    h = [min(WORLD_H - 2, max(GROUND_BASE, v)) - GROUND_BASE for v in h]
    for x in range(2, WORLD_W - 2):     # vl_ground: |h[x+2] - h[x-2]| < 128
        assert abs(h[x + 2] - h[x - 2]) < 128
    return h


HEIGHTS = terrain()

# --- the lander -------------------------------------------------------------------
LEG_HALF, TOP_UP = 6, 8                 # px: the 6-8-10 triangle
FIXED_K = 6                             # link gain 2^6
LINKS = [Constraint(0, 1, 2 * LEG_HALF, fixed_k=FIXED_K),
         Constraint(0, 2, 10, fixed_k=FIXED_K),
         Constraint(1, 2, 10, fixed_k=FIXED_K)]
GRAVITY = 0x0004                        # 8.8 px / tick^2
VMAX = 0x0300                           # 3 px a tick
THRUST_SHIFT = 4                        # VL_THRUST
THRUST_K = -13                          # vl_turn for the engine: 12 px * -13 / 4096 = -0.04 px/tick^2
ROT_K = 1                               # vl_turn of a turn key, a tick
SPIN_DAMP = 2                           # vl_pair_damp: the spin fades by 1/4 a tick
RADIUS = 0x0180                         # legs: 1.5 px
PROBE, SLOPE_MAX, FAR, BOUNCE = 2, 15, 0x1000, 40
FRICTION = 2                            # on the ground vt -= vt >> 2 a tick
FUEL = 250                              # units; one every 2 thrust ticks
V_SAFE = 0x0060                         # 0.375 px a tick
TILT_MAX = 0x0280                       # 2.5 px over the 12 px of the legs (~12 degrees)
SETTLE = 16                             # ticks on both legs before the verdict
KICK = [(-0x00C0, -0x0100), (0x00C0, -0x00C0), (0x0020, -0x0180)]   # the explosion (8.8 px/tick)
START = (60, 30, 0x0040, 0)             # top-left: x, y of the legs, vx, vy (8.8)

FLY, LANDED, CRASHED = 0, 1, 2


class Lander(Points):
    def __init__(self, start=START):
        super().__init__(3, y_high=True)
        self.hm = HeightMap(HEIGHTS, SLOPE_MAX, PROBE, RADIUS, FAR, BOUNCE, base=GROUND_BASE)
        x, y, vx, vy = start
        for i, (dx, dy) in enumerate([(-LEG_HALF, 0), (LEG_HALF, 0), (0, -TOP_UP)]):
            self.place(i, (x + dx) << 8, (y + dy) << 8)
            self.ox[i] -= vx
            self.oy[i] -= vy
        self.status = FLY
        self.fuel, self.fsub = FUEL, 0
        self.settle, self.contact, self.timer, self.pad = 0, 0, 0, 0
        self.gnd = [0, 0, 0]
        self.vy = 0

    def _ground(self, n):
        for i in range(n):
            self.gnd[i] = int(self.hm.contact(self, i, lambda i, v: v - (v >> FRICTION)) is not None)

    def _walls(self):
        for i in range(3):
            if self.x[i] >= RIGHT_WALL << 8:
                self.x[i] = self.ox[i] = RIGHT_WALL << 8

    def pad_of(self, i):
        c = self.x[i] >> 8
        for k, (x0, x1, _) in enumerate(PADS):
            if x0 <= c <= x1:
                return k + 1
        return 0

    def tick(self, thr=0, rot=0):
        if self.status == LANDED:
            return
        if self.status == CRASHED:
            self.integrate_all(GRAVITY, VMAX, VMAX, LEFT_WALL << 8)
            self._walls()
            self._ground(3)
            self.ceiling(CEIL << 8)
            if self.timer < 255:
                self.timer += 1
            return
        self.vy = s16(self.y[2] - self.oy[2])
        self.integrate_all(GRAVITY, VMAX, VMAX, LEFT_WALL << 8)
        self._walls()
        self.pair_damp(0, 1, SPIN_DAMP)
        if rot:
            self.turn_pair(0, 1, ROT_K if rot > 0 else -ROT_K)
        if thr and self.fuel:
            self.push_all(self.thrust(0, 1, THRUST_K, THRUST_SHIFT, perp=True))
            self.fsub ^= 1
            if not self.fsub:
                self.fuel -= 1
        for _ in range(2):
            for c in LINKS:
                c.apply(self)
        self._ground(3)
        for c in LINKS:
            c.apply(self)
        self.ceiling(CEIL << 8)
        self._rules()

    def _rules(self):
        g = self.gnd
        tilt = s16(self.y[1] - self.y[0])
        steep = tilt > TILT_MAX or tilt < -TILT_MAX
        if g[2]:
            return self.crash()
        if not (g[0] or g[1]):
            self.contact = 0
            self.settle = 0
            return
        if not self.contact and (self.vy > V_SAFE or steep):
            return self.crash()
        self.contact = 1
        if steep:
            return self.crash()
        self.settle += 1
        if self.settle < SETTLE:
            return
        pad = self.pad_of(0)
        if pad and pad == self.pad_of(1):
            self.status, self.pad = LANDED, pad
        else:
            self.crash()

    def crash(self):
        self.status, self.timer = CRASHED, 0
        for i, (kx, ky) in enumerate(KICK):
            self.ox[i] -= kx
            self.oy[i] -= ky

    def state_bytes(self):
        """The snapshot of tests/test_lander.py: the points (vl_xf..vl_oyu),
        then lv_status, lv_fuel, lv_fsub, lv_settle, lv_contact, lv_timer,
        lv_pad, lv_gnd (3)."""
        return self.soa_bytes() + bytes([self.status, self.fuel, self.fsub, self.settle, self.contact,
                                         self.timer, self.pad] + self.gnd)


# --- autopilot (tests, demo tuning) -------------------------------------------------
def autopilot(p, pad=0):
    """(thr, rot) for this tick: keep the legs level, slide over pad `pad`
    (0..2) leaning a little, brake the fall harder near the ground."""
    x0, x1, row = PADS[pad]
    cx = (x0 + x1) // 2
    xm = (p.x[0] + p.x[1]) >> 9
    vx = s16(p.x[2] - p.ox[2])
    vy = s16(p.y[2] - p.oy[2])
    tilt = s16(p.y[1] - p.y[0])
    alt = (row << 8) - max(p.y[0], p.y[1])
    # the engine pushes along the body: a tilt > 0 (right leg low) pushes
    # right; lean toward the pad, against the drift (only against it low)
    err = (cx - xm) * 8 if alt > 0x2000 else 0
    want = max(-0x100, min(0x100, err - vx * 6))
    rot = 1 if tilt < want - 0x20 else -1 if tilt > want + 0x20 else 0
    target = 0x40 if alt < 0x1800 else min(0x100, 0x40 + alt // 128)
    thr = 1 if vy > target or (abs(want) > 0x60 and vy > -0x40) else 0
    return thr, rot


def above(pad, y=30):
    """A start over the middle of pad `pad`, at rest."""
    x0, x1, _ = PADS[pad]
    return ((x0 + x1) // 2, y, 0, 0)


def fly(pilot=autopilot, ticks=3000, start=START, **kw):
    p = Lander(start)
    inputs = []
    for _ in range(ticks):
        if p.status != FLY:
            break
        thr, rot = pilot(p, **kw)
        inputs.append((thr, rot))
        p.tick(thr, rot)
    return p, inputs


# --- the 6502 constants -------------------------------------------------------------
def write_inc(path):
    tab = tables(LINKS)
    nx, ny = HeightMap((), SLOPE_MAX, PROBE).nx, HeightMap((), SLOPE_MAX, PROBE).ny
    consts = [('GRAVITY', GRAVITY), ('VMAX', VMAX), ('THRUST_SHIFT', THRUST_SHIFT, 'dec'),
              ('THRUST_K', THRUST_K & 0xFF), ('ROT_K', ROT_K, 'dec'), ('SPIN_DAMP', SPIN_DAMP, 'dec'),
              ('FIXED_K', FIXED_K, 'dec'), ('RADIUS', RADIUS), ('PROBE', PROBE, 'dec'),
              ('SLOPE_MAX', SLOPE_MAX, 'dec'), ('FAR', FAR), ('BOUNCE', BOUNCE, 'dec'),
              ('FRICTION', FRICTION, 'dec'), ('GROUND_BASE', GROUND_BASE), ('WORLD_H', WORLD_H),
              ('LEFT_WALL', LEFT_WALL << 8), ('RIGHT_WALL', RIGHT_WALL, 'dec'), ('CEIL', CEIL << 8),
              ('FUEL', FUEL, 'dec'), ('V_SAFE', V_SAFE), ('TILT_MAX', TILT_MAX), ('SETTLE', SETTLE, 'dec'),
              ('NPADS', len(PADS), 'dec'), ('LEG_HALF', LEG_HALF, 'dec'), ('TOP_UP', TOP_UP, 'dec'),
              ('START_X', START[0], 'dec'), ('START_Y', START[1], 'dec'), ('START_VX', START[2]),
              ('START_VY', START[3])]
    tabs = ['; links (verlet.tables, VL_CON_FIXED_K: no k8)',
            ('vl_con_a', tab['con_a']), ('vl_con_b', tab['con_b']),
            ('vl_con_l2l', emit.lo(tab['con_l2'])), ('vl_con_l2h', emit.hi(tab['con_l2'])),
            '; ground normals, slopes -SLOPE_MAX..SLOPE_MAX (64 = 1.0)',
            ('vl_norm_x', emit.sb(nx)), ('vl_norm_y', emit.sb(ny)),
            '; pads: first, last column, ground row (16 bits)',
            ('pad_x0', [p[0] for p in PADS]), ('pad_x1', [p[1] for p in PADS]),
            ('pad_rl', emit.lo([p[2] for p in PADS])), ('pad_rh', emit.hi([p[2] for p in PADS])),
            '; the explosion: speed kicks of the three points (8.8)',
            ('kick_xl', emit.lo([k[0] for k in KICK])), ('kick_xh', emit.hi([k[0] for k in KICK])),
            ('kick_yl', emit.lo([k[1] for k in KICK])), ('kick_yh', emit.hi([k[1] for k in KICK])),
            '; ground rows - GROUND_BASE, one per column']
    for k in range(0, WORLD_W, 16):
        tabs.append(('heights' if k == 0 else '', HEIGHTS[k:k + 16]))
    text = emit.inc_text(consts, tabs, header=['; generated by tools/lander.py -- do not edit'])
    text = text.replace('\n:        .byte', '\n         .byte')
    return emit.write_if_changed(path, text)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        write_inc(sys.argv[1])
    else:
        for pad in range(len(PADS)):
            p, inp = fly(pad=pad)
            print(f'from the start, pad {pad}: status {p.status} pad {p.pad} after {len(inp)} ticks')
            p, inp = fly(pad=pad, start=above(pad))
            print(f'pad {pad}: status {p.status} pad {p.pad} after {len(inp)} ticks, fuel {p.fuel}, '
                  f'thrust ticks {sum(t for t, _ in inp)}')
        p, inp = fly(lambda p: (0, 0))
        print(f'free fall: status {p.status} after {len(inp)} ticks')
