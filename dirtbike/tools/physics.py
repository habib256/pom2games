#!/usr/bin/env python3
"""DIRTBIKE physics, integer reference model of src/physics.inc.

The bike is three Verlet points: 0 = rear wheel, 1 = front wheel,
2 = rider. Each has a position and its previous position; the velocity is
their difference. One tick:

  1. integrate every point (gravity, speed clamp);
  2. lean: turn the wheel axis (nose up / down);
  3. distance constraints, CONSTRAINT_PASSES times: wheelbase (stiff),
     rear-rider and front-rider (soft: the suspension);
  4. ground contact for both wheels: push out along the ground normal,
     bounce, then traction (throttle on the rear wheel), brake, rolling loss;
  5. crash test (rider too close to the ground), finish test.

Units: x = 16.8 fixed point world pixels (24 bits), y = 8.8 screen rows
(rows grow downwards). Velocities and deltas are signed 8.8. Every product
is computed exactly and shifted with floor semantics (Python >>), which is
what the 6502 code does with its arithmetic shifts. The asm must match this
model bit for bit (tests/test_physics.py compares RAM after N ticks).

Constraints use no square root: for points a, b at rest length L,
  f = (|b-a|^2 - L^2) / (2 L^2)  ~  (|b-a| - L) / L
moves a by +f/2 (b-a) and b by -f/2 (b-a) (scaled by the stiffness).
"""
import math

# --- tuning -----------------------------------------------------------------
GRAVITY = 0x0030            # 8.8 px / tick^2 (down)
VMAX_X = 0x1200             # speed clamps, 8.8 px / tick: fast along the track,
VMAX_Y = 0x0800             # less in falls (the suspension takes 8 px / tick)
WHEEL_R = 0x0600            # wheel radius, 8.8 px
BOUNCE = 64                 # normal speed kept on impact, /256
ROLL_LOSS = 7               # tangential speed shift: vt -= vt >> ROLL_LOSS
THROTTLE_ACC = 31           # per throttle level, 8.8 px / tick^2 (8 x 31 < 256)
THROTTLE_MAX = 8            # levels 0..8
VT_MAX = 0x0D80             # traction stops adding speed above this (3x lot 1)
BRAKE = 0x0020              # 8.8 px / tick^2 removed from |vt| on each wheel
LEAN_MAX = 4                # lean turn per tick, /256 of the wheel axis
CONSTRAINT_PASSES = 1
RIDER_HIT = 0x0300          # crash if the rider gets this close to the ground

WHEELBASE = 24              # px
RIDER_UP = 16               # rider above the middle of the axis, px
RIDER_LEN = math.hypot(WHEELBASE / 2, RIDER_UP)

# constraint (a, b, rest length px, stiffness /1, the half move is folded in)
CONSTRAINTS = [
    (0, 1, WHEELBASE, 1.0),
    (0, 2, RIDER_LEN, 1.2),     # 0.6 bottomed out on every landing: the rider
    (1, 2, RIDER_LEN, 1.2),     # hit the ground (2026-10-21: "chuter moins")
]

LAPS = 3                    # a race: laps of a looping track (tracks.Track)
WRAP_MARGIN = 128           # this far past the line, the bike moves back a lap (> CAM_LEAD)
SLOPE_MAX = 15              # ground slope index: h[x+2] - h[x-2], clamped
LEFT_WALL = 16 << 8         # no point goes left of world pixel 16
FAR = 0x2000                # ground more than 32 rows below: no contact test
CEILING = 0x0800            # no point above row 8


def _l2q(length):
    """Rest length squared, in quarter pixels squared (|q| = delta >> 6)."""
    return int(round((length * 4) ** 2))


def _k8(length, stiff):
    """f = ((diff >> 3) * k8) >> 8 ~ diff * 256 / (2 L2q), half per point."""
    return int(round(2048 / (2 * _l2q(length)) * 256 * stiff / 2))


CON_TAB = [(a, b, _l2q(L), _k8(L, k)) for a, b, L, k in CONSTRAINTS]


def _normals():
    nx, ny = [], []
    for s in range(-SLOPE_MAX, SLOPE_MAX + 1):
        ln = math.hypot(s, 4)
        nx.append(int(round(64 * s / ln)))
        ny.append(int(round(-64 * 4 / ln)))
    return nx, ny


NORM_X, NORM_Y = _normals()     # index s + SLOPE_MAX; 64 = 1.0


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


class Bike:
    def __init__(self, track, x0=48):
        self.h = track
        self.lap_len = getattr(track, 'lap_len', 0)     # 0: the track does not loop
        self.laps = 0
        g = track[x0] - 6
        self.x = [x0 << 8, (x0 + WHEELBASE) << 8, (x0 + WHEELBASE // 2) << 8]
        self.y = [g << 8, g << 8, (g - RIDER_UP) << 8]
        self.ox = list(self.x)
        self.oy = list(self.y)
        self.ground = [0, 0]
        self.wheel_ang = [0, 0]
        self.crashed = False

    # --- one tick ---------------------------------------------------------
    def tick(self, throttle=0, brake=False, lean=0):
        for i in range(3):
            self._integrate(i)
        if lean:
            self._lean(lean)
        for _ in range(CONSTRAINT_PASSES):
            for c in CON_TAB:
                self._constrain(*c)
        for i in range(2):
            self._ground(i, throttle if i == 0 else 0, brake)
        self._ceiling()
        self.crashed = self.crashed or self._rider_hit()
        self._wrap()

    def _wrap(self):
        """A looping track repeats its first pixels after lap_len (padding): past
        lap_len + WRAP_MARGIN the three points move back by lap_len together,
        so nothing changes for the physics, and a lap is counted."""
        lap = self.lap_len
        if lap and (self.x[0] >> 8) >= lap + WRAP_MARGIN:
            for i in range(3):
                self.x[i] -= lap << 8
                self.ox[i] -= lap << 8
            self.laps += 1

    def _integrate(self, i):
        vx = clamp(s16(self.x[i] - self.ox[i]), -VMAX_X, VMAX_X)
        vy = clamp(s16(self.y[i] - self.oy[i]) + GRAVITY, -VMAX_Y, VMAX_Y)
        self.ox[i] = self.x[i]
        self.oy[i] = self.y[i]
        self.x[i] += vx
        self.y[i] += vy
        if self.x[i] < LEFT_WALL:
            self.x[i] = self.ox[i] = LEFT_WALL

    def _lean(self, lean):
        dx = s16(self.x[1] - self.x[0])
        dy = s16(self.y[1] - self.y[0])
        px = (-dy * lean) >> 8      # perpendicular, turned clockwise on screen
        py = (dx * lean) >> 8
        self.x[1] += px
        self.y[1] += py
        self.x[0] -= px
        self.y[0] -= py

    def _constrain(self, a, b, l2q, k8):
        dx = s16(self.x[b] - self.x[a])
        dy = s16(self.y[b] - self.y[a])
        qx = min(abs(dx >> 6), 180)
        qy = min(abs(dy >> 6), 180)
        diff = qx * qx + qy * qy - l2q
        d8 = clamp(diff >> 3, -4095, 4095)
        f = clamp((d8 * k8) >> 8, -127, 127)
        cx = (dx * f) >> 8
        cy = (dy * f) >> 8
        self.x[a] += cx
        self.y[a] += cy
        self.x[b] -= cx
        self.y[b] -= cy

    def _slope(self, px):
        return clamp(self.h[px + 2] - self.h[px - 2], -SLOPE_MAX, SLOPE_MAX)

    def _ground(self, i, throttle, brake):
        px = self.x[i] >> 8
        s = self._slope(px)
        nx = NORM_X[s + SLOPE_MAX]
        ny = NORM_Y[s + SLOPE_MAX]
        # height of the centre above the ground line, along the normal
        self.ground[i] = 0
        diff = (self.h[px] << 8) - self.y[i]
        if diff >= FAR:
            return
        dist = (max(diff, -FAR) * -ny) >> 6
        if dist >= WHEEL_R:
            return
        self.ground[i] = 1
        pen = WHEEL_R - dist
        self.x[i] += (pen * nx) >> 6
        self.y[i] += (pen * ny) >> 6
        vx = s16(self.x[i] - self.ox[i])
        vy = s16(self.y[i] - self.oy[i])
        tx, ty = -ny, nx            # tangent: forward along the ground
        vn = (vx * nx + vy * ny) >> 6
        vt = (vx * tx + vy * ty) >> 6
        if vn < 0:
            vn = (-vn * BOUNCE) >> 8
        if throttle and vt < VT_MAX:
            vt += throttle * THROTTLE_ACC
        if brake:
            if vt > BRAKE:
                vt -= BRAKE
            elif vt < -BRAKE:
                vt += BRAKE
            else:
                vt = 0
        vt -= vt >> ROLL_LOSS
        vx = (vn * nx + vt * tx) >> 6
        vy = (vn * ny + vt * ty) >> 6
        self.ox[i] = self.x[i] - vx
        self.oy[i] = self.y[i] - vy
        self.wheel_ang[i] = (self.wheel_ang[i] + (vt >> 5)) & 0xFF

    def _ceiling(self):
        for i in range(3):
            if self.y[i] < CEILING:
                self.y[i] = CEILING
                self.oy[i] = CEILING

    def _rider_hit(self):
        px = self.x[2] >> 8
        return self.y[2] + RIDER_HIT > (self.h[px] << 8)

    # --- helpers for tools and tests --------------------------------------
    def progress(self):
        """Distance covered, laps included (8.8 world pixels, both wheels)."""
        return 2 * self.laps * (self.lap_len << 8) + self.x[0] + self.x[1]

    def finished(self, fin):
        """Over the finish line: on a loop, fin = lap_len in the last lap."""
        return (not self.lap_len or self.laps >= LAPS - 1) and (self.x[0] >> 8) >= fin

    def angle(self):
        return math.degrees(math.atan2(self.y[1] - self.y[0], self.x[1] - self.x[0]))

    def speed_px(self):
        return (self.x[0] - self.ox[0]) / 256


if __name__ == '__main__':
    import track
    t = track.track1()
    b = Bike(t)
    for n in range(2000):
        b.tick(throttle=THROTTLE_MAX)
        if n % 50 == 0 or b.crashed:
            print(f'{n:4} x={b.x[0] / 256:7.1f} y={b.y[0] / 256:6.1f} '
                  f'ang={b.angle():6.1f} v={b.speed_px():5.2f} '
                  f'gnd={b.ground} rider_y={b.y[2] / 256:6.1f}')
        if b.crashed:
            print('CRASH')
            break
        if b.finished(track.FINISH_X):
            print('FINISH at tick', n)
            break
    print('constraints', CON_TAB)
