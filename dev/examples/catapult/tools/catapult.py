#!/usr/bin/env python3
"""CATAPULT -- the Python model of the demo's physics (dev/lib/physics).

The reference of src/phys.inc, bit for bit (tests/test_catapult.py runs
both and compares the state tick after tick). `python3 tools/catapult.py
src/catconst.inc` writes the constants and tables the 6502 assembles.

Nine Verlet points: 0 = the projectile, 1..6 = the targets (circles of
RAD units, VL_CIRC = 7, VL_CIRC_Q = 5: 1/8 px), 7 = the arm's base (always
pinned), 8 = its tip. The world is the screen (y 8.8), a height-map hill
under the catapult, static boxes (a pillar, a platform, a cup between two
posts) under the targets.

Phases (cp_phase):
  AIM    the tip and the projectile at rest at the pull angle (power 0..PMAX
         picks it from arm_dx / arm_dy), both pinned. in_fire -> SWING: the
         tip is freed and pushed along the arm's perpendicular
         (vl_thrust_perp, VL_THRUST = 1, + vl_push): turn = POW0 +
         power * POW_K, a speed of ARM * turn / 512 px a tick.
  SWING  the tip flies round the pinned base (integrate, 2 link passes); the
         projectile is the tip (same position and old position: the same
         speed). The arm crossing the stop direction of in_stop (cross
         product <= 0), or SWING_MAX ticks: the projectile is let go (FLY),
         the tip stops at the stop angle, pinned (the arm hits its bar).
  FLY    the circles: integrate, the walls and the ceiling, one pass of
         vl_contact_all, then each awake circle against the boxes and the
         ground; a target woken wakes its group (the pillar, the column,
         the pyramid: a sleeping target is pinned, one woken under another
         would leave it floating), then vl_circ_sleep for each. A target CAN_FALL px under its start
         scores (once). The shot ends when the projectile and every target
         sleep, or after SHOT_MAX ticks: a shot left -> AIM (the projectile
         back in the cup), else OVER; all 6 down -> OVER.
  OVER   nothing moves (in_fire: the game restarts the round).
"""
from pathlib import Path
import math
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'tools'))
from verlet import Points, Constraint, HeightMap, tables, emit, contact  # noqa: E402
from verlet.fixed import s16  # noqa: E402

N, NC = 9, 7                            # points, circles
PROJ, BASE, TIP = 0, 7, 8
Q = 5
RADPX = 5
RAD = contact.rad_q(RADPX, Q)           # 40 units
GRAVITY = 0x0010
VMAX = 0x0600
BOUNCE, VMIN, CFRICTION = 64, 0x0030, 3     # contacts: restitution 1/4 above VMIN
HEAVY = 1                               # the projectile weighs 3 targets
SLEEP, SLEEP_TICKS = 0x0028, 16       # > 2 g: a ball resting on an awake one (one pass)
GBOUNCE, GFRICTION = 32, 3              # the ground
PROBE, SLOPE_MAX, FAR = 2, 15, 0x1000
LEFT_WALL, RIGHT_WALL, CEIL = 4, 251, 18
THRUST = 1
ARM = 24                                # px
FIXED_K = 4                             # a 24-px link, pinned end: 2^4 = 1 / (2 l2q) in one pass
LINKS = [Constraint(BASE, TIP, ARM, fixed_k=FIXED_K)]
BASE_XY = (36, 140)
PMAX = 15                               # power steps
POW0, POW_K = 50, 4                     # turn = POW0 + power * POW_K: ARM * turn / 512 px a tick
PULL0, PULL_K = 180, 2                  # pull angle (degrees, y up) = PULL0 + power * PULL_K
STOPS = [25, 35, 45, 55, 65]            # launch angles (degrees): the stop = launch + 90
SWING_MAX = 40
SHOT_MAX = 500
SHOTS = 3
CAN_FALL = 8                            # px under the start: down
AIM, SWING, FLY, OVER = 0, 1, 2, 3

# boxes: (x0, y0, x1, y1) px, edges included
BOXES = [(112, 130, 118, 178),          # A: the pillar
         (150, 150, 172, 154),          # B: the platform
         (196, 160, 222, 164),          # C: the cup's floor
         (196, 150, 199, 160),          # D: its left post
         (219, 150, 222, 160)]          # E: its right post
U = 1 << Q                              # a unit in 8.8
TARGETS = [(115 << 8, (130 << 8) - RAD * U),                    # on the pillar
           (161 << 8, (150 << 8) - RAD * U),                    # a column of 2
           (161 << 8, (150 << 8) - 3 * RAD * U),
           (204 << 8, (160 << 8) - RAD * U),                    # the pyramid
           (214 << 8, (160 << 8) - RAD * U),
           (209 << 8, (160 << 8) - RAD * U - 70 * U)]           # (8.75 px up: q2 > R^2)
GROUP = [1, 2, 2, 4, 4, 4]              # the targets' groups (bits): woken together


def terrain():
    h = []
    for x in range(256):
        y = 178 - 34 * math.exp(-((x - 34) / 26.0) ** 2) + 2 * math.sin(x / 9.0)
        h.append(int(round(y)))
    for x in range(2, 254):
        assert abs(h[x + 2] - h[x - 2]) < 128
    return h


HEIGHTS = terrain()


def _deg(a):
    """Degrees (y up) -> a screen direction (cos, -sin)."""
    r = math.radians(a)
    return math.cos(r), -math.sin(r)


def arm_table():
    """(dx, dy) 8.8 of the tip from the base for each power."""
    out = []
    for p in range(PMAX + 1):
        c, s = _deg(PULL0 + p * PULL_K)
        out.append((int(round(ARM * 256 * c)), int(round(ARM * 256 * s))))
    return out


def stop_table():
    """Per stop: the direction (sx, sy) at 64 = 1.0 and the tip's rest (dx, dy) 8.8."""
    out = []
    for la in STOPS:
        c, s = _deg(la + 90)
        out.append((int(round(64 * c)), int(round(64 * s)), int(round(ARM * 256 * c)), int(round(ARM * 256 * s))))
    return out


def ring():
    pts = []
    for k in range(20):
        a = 2 * math.pi * k / 20
        p = (int(round(RADPX * math.cos(a))), int(round(RADPX * math.sin(a))))
        if p not in pts:
            pts.append(p)
    return [p[0] for p in pts], [p[1] for p in pts]


RING = ring()
ARMS = arm_table()
STOP = stop_table()


class Catapult(Points):
    def __init__(self):
        super().__init__(N, pins=True)
        self.hm = HeightMap(HEIGHTS, SLOPE_MAX, PROBE, RAD * U, FAR, GBOUNCE)
        self.rad = [RAD] * NC
        self.hv = [1] + [0] * (NC - 1)
        self.still = [0] * NC
        self.place(BASE, BASE_XY[0] << 8, BASE_XY[1] << 8)
        self.pin[BASE] = 1
        for k, (x, y) in enumerate(TARGETS):
            self.place(1 + k, x, y)
            self.pin[1 + k] = 0x80
        self.phase, self.shots, self.score, self.timer = AIM, SHOTS, 0, 0
        self.down = [0] * (NC - 1)
        self.power, self.stop = 0, 2
        self.hits = 0
        self.gnd = [0] * NC
        self._aim()

    def _aim(self):
        dx, dy = ARMS[self.power]
        bx, by = self.x[BASE], self.y[BASE]
        self.place(TIP, bx + dx, by + dy)
        self.place(PROJ, bx + dx, by + dy)
        self.pin[TIP] = self.pin[PROJ] = 1
        self.still[PROJ] = 0

    def _walls(self):
        for i in range(NC):
            xh, xl = (self.x[i] >> 16) & 0xFF, (self.x[i] >> 8) & 0xFF
            if xh == 0xFF or (xh == 0 and xl < LEFT_WALL):
                self.x[i] = self.ox[i] = LEFT_WALL << 8
            elif xh or xl >= RIGHT_WALL:
                self.x[i] = self.ox[i] = RIGHT_WALL << 8
        y, oy = self.y, self.oy
        for i in range(NC):
            if y[i] < CEIL << 8:
                y[i] = oy[i] = CEIL << 8

    def tick(self, power=0, stop=2, fire=0):
        ph = self.phase
        if ph == AIM:
            self.power, self.stop = power, stop
            self._aim()
            if fire:
                self.phase = SWING
                self.timer = 0
                self.pin[TIP] = 0
                t = self.thrust(BASE, TIP, POW0 + power * POW_K, THRUST, perp=True)
                self.push(TIP, t)
            return
        if ph == SWING:
            self.integrate_all(GRAVITY, VMAX, VMAX)
            for _ in range(2):
                for c in LINKS:
                    c.apply(self)
            self.x[PROJ], self.ox[PROJ] = self.x[TIP], self.ox[TIP]
            self.y[PROJ], self.oy[PROJ] = self.y[TIP], self.oy[TIP]
            self.timer += 1
            sx, sy, rx, ry = STOP[self.stop]
            ex, ey = self.delta(BASE, TIP)
            if ex * sy - ey * sx <= 0 or self.timer >= SWING_MAX:
                self.phase, self.timer = FLY, 0
                self.pin[PROJ] = 0
                self.place(TIP, self.x[BASE] + rx, self.y[BASE] + ry)
                self.pin[TIP] = 1
            return
        if ph != FLY:
            return
        self.integrate_all(GRAVITY, VMAX, VMAX)
        self._walls()
        was = self.pin[1:NC]
        self.hits = contact.contact_all(self, self.rad, Q, BOUNCE, VMIN, HEAVY, self.hv, SLEEP)
        woke = 0
        for k in range(NC - 1):
            if was[k] and not self.pin[1 + k]:
                woke |= GROUP[k]
        for k in range(NC - 1):                         # a target woke: its group
            if woke & GROUP[k]:
                self.pin[1 + k] = 0
        self.gnd = [0] * NC
        for i in range(NC):
            if self.pin[i]:
                continue
            self.hits += contact.boxes(self, i, RAD, BOXES, Q, BOUNCE, VMIN, CFRICTION)
            self.gnd[i] = int(self.hm.contact(self, i, lambda i, v: v - (v >> GFRICTION)) is not None)
        for i in range(NC):
            contact.sleep_check(self, i, self.still, SLEEP, SLEEP_TICKS)
        for k in range(NC - 1):
            if not self.down[k] and (self.y[1 + k] >> 8) >= (TARGETS[k][1] >> 8) + CAN_FALL:
                self.down[k] = 1
                self.score += 1
        self.timer += 1
        still = all(self.pin[i] for i in range(NC))
        if self.score == NC - 1:
            self.phase = OVER
        elif still or self.timer >= SHOT_MAX:
            self.shots -= 1
            if self.shots:
                self.phase = AIM
                self._aim()
            else:
                self.phase = OVER

    def state_bytes(self):
        """The snapshot of tests/test_catapult.py: the points (vl_xf..vl_oyh),
        vl_pin (9), vl_still (7), then cp_phase, cp_shots, cp_score,
        cp_timer (2), cp_power, cp_stop, cp_down (6), vl_gnd (7)."""
        return self.soa_bytes() + bytes(self.pin) + bytes(self.still) + bytes(
            [self.phase, self.shots, self.score, self.timer & 0xFF, self.timer >> 8, self.power, self.stop]
            + self.down + self.gnd)


def play(shots, max_ticks=3000):
    """shots: [(power, stop)]: aim, fire, wait for the shot to end. -> the
    model and the inputs, one (power, stop, fire) a tick."""
    c, inputs, k = Catapult(), [], 0
    for _ in range(max_ticks):
        if c.phase == OVER:
            break
        if c.phase == AIM:
            if k >= len(shots):
                break
            pw, st = shots[k]
            if c.power != pw or c.stop != st:
                inp = (pw, st, 0)
            else:
                inp = (pw, st, 1)
                k += 1
        else:
            inp = (c.power, c.stop, 0)
        inputs.append(inp)
        c.tick(*inp)
    return c, inputs


def write_inc(path):
    tab = tables(LINKS)
    hm = HeightMap((), SLOPE_MAX, PROBE)
    consts = [('GRAVITY', GRAVITY), ('VMAX', VMAX), ('RAD', RAD, 'dec'), ('RADPX', RADPX, 'dec'),
              ('CQ', Q, 'dec'), ('CBOUNCE', BOUNCE, 'dec'), ('CVMIN', VMIN), ('CFRICTION', CFRICTION, 'dec'),
              ('CHEAVY', HEAVY, 'dec'), ('CSLEEP', SLEEP), ('CSLEEP_TICKS', SLEEP_TICKS, 'dec'),
              ('GBOUNCE', GBOUNCE, 'dec'), ('GFRICTION', GFRICTION, 'dec'), ('PROBE', PROBE, 'dec'),
              ('SLOPE_MAX', SLOPE_MAX, 'dec'), ('FAR', FAR), ('LEFT_WALL', LEFT_WALL, 'dec'),
              ('RIGHT_WALL', RIGHT_WALL, 'dec'), ('CEIL', CEIL << 8), ('THRUST', THRUST, 'dec'),
              ('ARM', ARM, 'dec'), ('FIXED_K', FIXED_K, 'dec'), ('BASE_X', BASE_XY[0], 'dec'),
              ('BASE_Y', BASE_XY[1], 'dec'), ('PMAX', PMAX, 'dec'), ('POW0', POW0, 'dec'),
              ('POW_K', POW_K, 'dec'), ('NSTOP', len(STOPS), 'dec'), ('SWING_MAX', SWING_MAX, 'dec'),
              ('SHOT_MAX', SHOT_MAX), ('SHOTS', SHOTS, 'dec'), ('CAN_FALL', CAN_FALL, 'dec'),
              ('NBOX', len(BOXES), 'dec'), ('NRING', len(RING[0]), 'dec')]
    tabs = ['; the arm (verlet.tables, VL_CON_FIXED_K: no k8)',
            ('vl_con_a', tab['con_a']), ('vl_con_b', tab['con_b']),
            ('vl_con_l2l', emit.lo(tab['con_l2'])), ('vl_con_l2h', emit.hi(tab['con_l2'])),
            '; ground normals, slopes -SLOPE_MAX..SLOPE_MAX (64 = 1.0)',
            ('vl_norm_x', emit.sb(hm.nx)), ('vl_norm_y', emit.sb(hm.ny)),
            '; the boxes (px, edges included)',
            ('vl_box_x0', [b[0] for b in BOXES]), ('vl_box_y0', [b[1] for b in BOXES]),
            ('vl_box_x1', [b[2] for b in BOXES]), ('vl_box_y1', [b[3] for b in BOXES]),
            '; the targets at the start (8.8 / 16.8 low bytes; x < 256 px)',
            ('tg_xf', emit.lo([t[0] for t in TARGETS])), ('tg_xl', emit.hi([t[0] for t in TARGETS])),
            ('tg_yf', emit.lo([t[1] for t in TARGETS])), ('tg_yh', emit.hi([t[1] for t in TARGETS])),
            ('tg_group', GROUP),
            '; the tip from the base for each power (8.8)',
            ('arm_dxl', emit.lo([a[0] for a in ARMS])), ('arm_dxh', emit.hi([a[0] for a in ARMS])),
            ('arm_dyl', emit.lo([a[1] for a in ARMS])), ('arm_dyh', emit.hi([a[1] for a in ARMS])),
            '; the stops: direction (64 = 1.0), the tip at rest there (8.8)',
            ('stop_sx', emit.sb([s[0] for s in STOP])), ('stop_sy', emit.sb([s[1] for s in STOP])),
            ('stop_dxl', emit.lo([s[2] for s in STOP])), ('stop_dxh', emit.hi([s[2] for s in STOP])),
            ('stop_dyl', emit.lo([s[3] for s in STOP])), ('stop_dyh', emit.hi([s[3] for s in STOP])),
            ('stop_deg', STOPS),
            '; the aim mark: 16 px along each launch direction',
            ('aim_dx', emit.sb([int(round(16 * math.cos(math.radians(a)))) for a in STOPS])),
            ('aim_dy', emit.sb([int(round(-16 * math.sin(math.radians(a)))) for a in STOPS])),
            '; a circle of RADPX px: 20 points (dx, dy)',
            ('ring_dx', emit.sb(RING[0])), ('ring_dy', emit.sb(RING[1])),
            '; the hill: a row per column']
    for k in range(0, 256, 16):
        tabs.append(('heights' if k == 0 else '', HEIGHTS[k:k + 16]))
    text = emit.inc_text(consts, tabs, header=['; generated by tools/catapult.py -- do not edit'])
    text = text.replace('\n:        .byte', '\n         .byte')
    return emit.write_if_changed(path, text)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        write_inc(sys.argv[1])
    else:
        for pw in range(0, PMAX + 1, 3):
            for st in range(len(STOPS)):
                c, inp = play([(pw, st)])
                land = (c.x[PROJ] >> 8, c.y[PROJ] >> 8)
                print(f'power {pw:2} angle {STOPS[st]}: lands at {land}, {c.score} down, {len(inp)} ticks')
