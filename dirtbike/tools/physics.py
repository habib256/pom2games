#!/usr/bin/env python3
"""DIRTBIKE physics, integer reference model of src/physics.inc.

The bike is three Verlet points: 0 = rear wheel, 1 = front wheel,
2 = rider. Each has a position and its previous position; the velocity is
their difference. One tick:

  1. integrate every point (gravity, speed clamp);
  2. in the air or on one wheel, the spin of the wheel axis fades; the axis
     turns: the brake pulls the nose down (the wheel's reaction on the
     frame), in the air the lean and the throttle turn it too;
  3. distance constraints, CONSTRAINT_PASSES times: wheelbase (stiff),
     rear-rider and front-rider (soft: the suspension). The lean shifts the
     rider along the bike (their rest lengths); he is heavier than a wheel;
  4. ground contact for both wheels: push out along the ground normal,
     bounce, then traction (throttle on the rear wheel), brake, engine
     brake, rolling loss;
  5. the constraints again (the frame stays a frame after the ground);
  6. crash tests: rider too close to the ground, a rider link squashed, the
     bike over (front behind rear with a wheel down); finish test.

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
ENGINE_BRAKE = 7            # rear wheel, no throttle: also vt -= vt >> ENGINE_BRAKE
THROTTLE_ACC = 31           # per throttle level, 8.8 px / tick^2 (8 x 31 < 256)
THROTTLE_MAX = 8            # levels 0..8
VT_MAX = 0x0D80             # traction stops adding speed above this (3x lot 1)
BRAKE = 0x0020              # 8.8 px / tick^2 removed from |vt| on each wheel
LEAN_MAX = 4                # lean levels -4..4 (+: forward / nose down)
LEAN_SHIFT = 1.0            # the rider moves this far along the bike per level, px
GYRO_DIV = 8                # in the air, throttle / GYRO_DIV turns the nose up and
GYRO_BRAKE = 4              # the brake turns it down (the rear wheel is a gyroscope)
CONSTRAINT_PASSES = 1       # before the ground contact (one more after it)
RIDER_HIT = 0x0300          # crash if the rider gets this close to the ground
RIDER_MIN = 0.5             # crash if a rider link gets this short (x rest length)
FLIP_DX = 4 << 8            # crash: a wheel down, the front this far behind the rear
SPIN_DAMP = 4               # in the air or on one wheel: wheel relative speed
                            # -= itself >> SPIN_DAMP (tyre, suspension, rider)

SUSP_K = 0.9                # firm, not hard: 1.2 then 1.0 were a little too easy (user)
RIDER_HEAVY = 3             # rider links: the wheel takes c + c >> 3, the rider
                            # c - c >> 3 (the rider weighs 9 / 7 of a wheel)
WHEELBASE = 24              # px
RIDER_UP = 16               # rider above the middle of the axis, px
RIDER_LEN = math.hypot(WHEELBASE / 2, RIDER_UP)

# constraint (a, b, rest length px, stiffness /1, the half move is folded in).
# The rider is heavier than a wheel (RIDER_HEAVY); a 3x heavier rider made
# the bike too hard to keep on whoops (2026-10-21, solver).
CONSTRAINTS = [
    (0, 1, WHEELBASE, 1.0),
    (0, 2, RIDER_LEN, SUSP_K),  # the suspension: two passes a tick (before and
    (1, 2, RIDER_LEN, SUSP_K),  # after the ground), so less than 1 is enough
]


def rider_len(lean, wheel):
    """Rest length of a rider link with the rider shifted lean levels forward."""
    s = lean * LEAN_SHIFT
    return math.hypot(WHEELBASE / 2 + (s if wheel == 0 else -s), RIDER_UP)

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
# rider links per lean level (index lean + LEAN_MAX): rest length^2, k8
RIDER_TAB = [[(_l2q(rider_len(l, w)), _k8(rider_len(l, w), SUSP_K))
              for l in range(-LEAN_MAX, LEAN_MAX + 1)] for w in (0, 1)]
L2Q_MIN = _l2q(RIDER_LEN * RIDER_MIN)       # rider links: squashed below


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
        self.squashed = False

    # --- one tick ---------------------------------------------------------
    def tick(self, throttle=0, brake=False, lean=0):
        air = not (self.ground[0] or self.ground[1])    # (last tick's contact)
        one = self.ground[0] != self.ground[1]          # on one wheel
        for i in range(3):
            self._integrate(i)
        # the rear wheel's torque turns the frame the other way: the brake
        # pulls the nose down; in the air the throttle lifts it (on the ground
        # the traction already does) and the rider turns the bike (lean); on
        # the ground only his weight acts (the lean shifts it, _cons)
        turn = GYRO_BRAKE if brake else 0
        if air or one:
            self._spin_damp()
        if air:
            turn += lean - throttle // GYRO_DIV
        if turn:
            self._lean(turn)
        cons = self._cons(lean)
        for _ in range(CONSTRAINT_PASSES):
            for c in cons:
                self._constrain(*c)
        for i in range(2):
            self._ground(i, throttle if i == 0 else 0, brake)
        self.squashed = False
        for c in cons:                      # the frame again, after the ground
            self._constrain(*c)
        self._ceiling()
        self.crashed = self.crashed or self._rider_hit() or self.squashed or self._flipped()
        self._wrap()

    @staticmethod
    def _cons(lean):
        """The three constraints, the rider shifted by the lean."""
        r, f = RIDER_TAB[0][lean + LEAN_MAX], RIDER_TAB[1][lean + LEAN_MAX]
        return (CON_TAB[0], (0, 2) + r, (1, 2) + f)

    def _spin_damp(self):
        """In the air nothing turns the bike but the rider: the relative speed
        of the wheels (its spin) fades by 1 / 2^SPIN_DAMP a tick."""
        for p, o in ((self.x, self.ox), (self.y, self.oy)):
            d = s16((p[1] - o[1]) - (p[0] - o[0])) >> SPIN_DAMP
            o[1] += d
            o[0] -= d

    def _flipped(self):
        """A wheel on the ground and the front wheel behind the rear one: the
        bike went over (a wheelie looped, or it landed on its back)."""
        return bool(self.ground[0] or self.ground[1]) and s16(self.x[1] - self.x[0]) < -FLIP_DX

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
        q2 = qx * qx + qy * qy
        if b == 2 and q2 < L2Q_MIN:
            self.squashed = True        # the rider on a wheel: a crash
        diff = q2 - l2q
        d8 = clamp(diff >> 3, -4095, 4095)
        f = clamp((d8 * k8) >> 8, -127, 127)
        cx = (dx * f) >> 8
        cy = (dy * f) >> 8
        if b == 2:                      # the rider is heavier than a wheel
            self.x[a] += cx + (cx >> RIDER_HEAVY)
            self.y[a] += cy + (cy >> RIDER_HEAVY)
            self.x[b] -= cx - (cx >> RIDER_HEAVY)
            self.y[b] -= cy - (cy >> RIDER_HEAVY)
            return
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
        if i == 0 and not throttle:
            vt -= vt >> ENGINE_BRAKE
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
