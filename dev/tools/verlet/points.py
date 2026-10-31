"""Verlet points as a structure of arrays: x, y and the previous ox, oy.

The velocity of a point is (x - ox, y - oy). x is 16.8 (24 bits on the
6502: vl_xf/xl/xh), y is 8.8 (vl_yf/yh) or, with y_high (VL_Y_HIGH), 16.8
(vl_yf/yh/yu); both are plain Python ints here, the 6502 keeps them modulo
2^24 / 2^16 (soa_bytes() masks the same way). Deltas and velocities are the
low 16 bits, signed (s16), as on the 6502.

pin (VL_PIN): a list of flags, one per point (None: no pin). A pinned point
is skipped by integrate (and push_all) and does not move in a constraint:
the other end takes the whole correction (verlet.constrain).

Each method is one routine of lib/physics (verlet.asm, verlet_rot.asm):

  integrate      vl_integrate     gravity, speed clamp, old := pos, pos += v
  pair_damp      vl_pair_damp     the relative speed of two points fades
  turn_pair      vl_turn_pair     turn the axis a -> b by k / 256 radian
  shift_point    vl_shift_point   move a point along the axis, no speed
  rest           vl_rest          old := pos (every point at rest)
  ceiling        vl_ceiling       no point above a row (no speed upwards)
  wrap           vl_wrap          past a lap, every point moves back a lap
  thrust         vl_thrust_axis / vl_thrust_perp (VL_THRUST): the push vector
  push, push_all vl_push / vl_push_all: point(s) += the push vector
"""
from .fixed import s16


def s24(v):
    v &= 0xFFFFFF
    return v - 0x1000000 if v & 0x800000 else v


class Points:
    pin = None                  # (class defaults: subclasses that set their
    y_high = False              # own attributes without __init__ keep them)

    def __init__(self, n=0, y_high=False, pins=False):
        self.x = [0] * n
        self.y = [0] * n
        self.ox = [0] * n
        self.oy = [0] * n
        self.y_high = y_high
        if pins:
            self.pin = [0] * n

    @property
    def n(self):
        return len(self.x)

    def place(self, i, x, y):
        """Point i at (x 16.8, y 8.8), at rest."""
        self.x[i] = self.ox[i] = x
        self.y[i] = self.oy[i] = y

    def integrate(self, i, gravity, vmax_x, vmax_y, left_wall=None):
        """vx = clamp(x - ox), vy = clamp(y - oy + gravity), old := pos,
        pos += v; with left_wall, a point left of it stops there (x = ox).
        A pinned point does not move."""
        if self.pin is not None and self.pin[i]:
            return
        x, ox = self.x, self.ox
        vx = s16(x[i] - ox[i])
        if vx > vmax_x:
            vx = vmax_x
        elif vx < -vmax_x:
            vx = -vmax_x
        y, oy = self.y, self.oy
        vy = s16(y[i] - oy[i] + gravity)
        if vy > vmax_y:
            vy = vmax_y
        elif vy < -vmax_y:
            vy = -vmax_y
        ox[i] = x[i]
        oy[i] = y[i]
        x[i] += vx
        y[i] += vy
        if left_wall is not None and x[i] < left_wall:
            x[i] = ox[i] = left_wall

    def integrate_all(self, gravity, vmax_x, vmax_y, left_wall=None):
        for i in range(len(self.x) - 1, -1, -1):
            self.integrate(i, gravity, vmax_x, vmax_y, left_wall)

    def delta(self, a, b):
        """(dx, dy) = point b - point a, 16 bits signed (vl_delta_ab)."""
        return s16(self.x[b] - self.x[a]), s16(self.y[b] - self.y[a])

    def pair_damp(self, a, b, shift):
        """d = (v_b - v_a) >> shift on each axis: ob += d, oa -= d (the
        spin of the axis a -> b fades, the sum of the speeds is kept)."""
        for p, o in ((self.x, self.ox), (self.y, self.oy)):
            d = s16((p[b] - o[b]) - (p[a] - o[a])) >> shift
            o[b] += d
            o[a] -= d

    def turn_pair(self, a, b, k):
        """Turn the axis a -> b: b += k (-dy, dx) >> 8, a -= the same (the
        perpendicular turned clockwise on screen, rows grow downwards)."""
        dx, dy = self.delta(a, b)
        px = (s16(-dy) * k) >> 8
        py = (dx * k) >> 8
        self.x[b] += px
        self.x[a] -= px
        self.y[b] += py
        self.y[a] -= py

    def shift_point(self, p, a, b, k):
        """Point p and its old position move k / 256 of the axis a -> b."""
        dx, dy = self.delta(a, b)
        mx = (dx * k) >> 8
        my = (dy * k) >> 8
        self.x[p] += mx
        self.ox[p] += mx
        self.y[p] += my
        self.oy[p] += my

    def thrust(self, a, b, k, shift, perp=False):
        """The push vector: (axis a -> b, or its perpendicular (-dy, dx)
        with perp) * k >> (8 + shift), k signed (vl_turn). -> (tx, ty)."""
        dx, dy = self.delta(a, b)
        if perp:
            dx, dy = s16(-dy), dx
        return ((dx * k) >> 8) >> shift, ((dy * k) >> 8) >> shift

    def push(self, i, t):
        """Point i += the push vector t (a speed change: old pos stays)."""
        self.x[i] += t[0]
        self.y[i] += t[1]

    def push_all(self, t):
        """Every point but the pinned ones += t (vl_push_all)."""
        pin = self.pin
        for i in range(len(self.x) - 1, -1, -1):
            if pin is None or not pin[i]:
                self.push(i, t)

    def rest(self):
        self.ox[:] = self.x
        self.oy[:] = self.y

    def ceiling(self, c):
        """No point above row c (8.8, whole rows): y = oy = c."""
        y, oy = self.y, self.oy
        for i in range(len(y)):
            if y[i] < c:
                y[i] = oy[i] = c

    def wrap(self, lap, margin, ref=0):
        """lap > 0 px: once point ref is lap + margin px or further, every
        point (and old point) moves back lap px. -> True if it did."""
        if lap and (self.x[ref] >> 8) >= lap + margin:
            d = lap << 8
            for i in range(len(self.x)):
                self.x[i] -= d
                self.ox[i] -= d
            return True
        return False

    def copy(self):
        c = Points.__new__(Points)
        c.x, c.y, c.ox, c.oy = self.x[:], self.y[:], self.ox[:], self.oy[:]
        if self.y_high:
            c.y_high = True
        if self.pin is not None:
            c.pin = self.pin[:]
        return c

    @classmethod
    def from_soa(cls, data, n, y_high=False):
        """The inverse of soa_bytes (x unsigned 24 bits, y unsigned 16, or
        signed 24 with y_high: the 6502 takes it signed, a point may fly
        above row 0)."""
        k = 12 if y_high else 10
        a = [data[j * n:(j + 1) * n] for j in range(k)]
        p = cls.__new__(cls)
        p.x = [a[0][i] | a[1][i] << 8 | a[2][i] << 16 for i in range(n)]
        if y_high:
            p.y_high = True
            p.y = [s24(a[3][i] | a[4][i] << 8 | a[5][i] << 16) for i in range(n)]
            p.ox = [a[6][i] | a[7][i] << 8 | a[8][i] << 16 for i in range(n)]
            p.oy = [s24(a[9][i] | a[10][i] << 8 | a[11][i] << 16) for i in range(n)]
        else:
            p.y = [a[3][i] | a[4][i] << 8 for i in range(n)]
            p.ox = [a[5][i] | a[6][i] << 8 | a[7][i] << 16 for i in range(n)]
            p.oy = [a[8][i] | a[9][i] << 8 for i in range(n)]
        return p

    def soa_bytes(self):
        """The 6502 layout: vl_xf, xl, xh, yf, yh, [yu,] oxf, oxl, oxh, oyf,
        oyh, [oyu,] n bytes each ([with y_high])."""
        ys = ((0, 8, 16) if self.y_high else (0, 8))
        out = []
        for arr, shs in ((self.x, (0, 8, 16)), (self.y, ys), (self.ox, (0, 8, 16)), (self.oy, ys)):
            for sh in shs:
                out += [(v >> sh) & 0xFF for v in arr]
        return bytes(out)
