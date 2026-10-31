"""Verlet points as a structure of arrays: x, y and the previous ox, oy.

The velocity of a point is (x - ox, y - oy). x is 16.8 (24 bits on the
6502: vl_xf/xl/xh), y is 8.8 (vl_yf/yh); both are plain Python ints here,
the 6502 keeps them modulo 2^24 / 2^16 (soa_bytes() masks the same way).
Deltas and velocities are the low 16 bits, signed (s16), as on the 6502.

Each method is one routine of lib/physics (verlet.asm, verlet_rot.asm):

  integrate      vl_integrate     gravity, speed clamp, old := pos, pos += v
  pair_damp      vl_pair_damp     the relative speed of two points fades
  turn_pair      vl_turn_pair     turn the axis a -> b by k / 256 radian
  shift_point    vl_shift_point   move a point along the axis, no speed
  rest           vl_rest          old := pos (every point at rest)
  ceiling        vl_ceiling       no point above a row (no speed upwards)
  wrap           vl_wrap          past a lap, every point moves back a lap
"""
from .fixed import s16


class Points:
    def __init__(self, n=0):
        self.x = [0] * n
        self.y = [0] * n
        self.ox = [0] * n
        self.oy = [0] * n

    @property
    def n(self):
        return len(self.x)

    def place(self, i, x, y):
        """Point i at (x 16.8, y 8.8), at rest."""
        self.x[i] = self.ox[i] = x
        self.y[i] = self.oy[i] = y

    def integrate(self, i, gravity, vmax_x, vmax_y, left_wall=None):
        """vx = clamp(x - ox), vy = clamp(y - oy + gravity), old := pos,
        pos += v; with left_wall, a point left of it stops there (x = ox)."""
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
        return c

    @classmethod
    def from_soa(cls, data, n):
        """The inverse of soa_bytes (x unsigned 24 bits, y unsigned 16)."""
        a = [data[k * n:(k + 1) * n] for k in range(10)]
        p = cls.__new__(cls)
        p.x = [a[0][i] | a[1][i] << 8 | a[2][i] << 16 for i in range(n)]
        p.y = [a[3][i] | a[4][i] << 8 for i in range(n)]
        p.ox = [a[5][i] | a[6][i] << 8 | a[7][i] << 16 for i in range(n)]
        p.oy = [a[8][i] | a[9][i] << 8 for i in range(n)]
        return p

    def soa_bytes(self):
        """The 6502 layout: vl_xf, xl, xh, yf, yh, oxf, oxl, oxh, oyf, oyh,
        n bytes each."""
        out = []
        for arr, sh in ((self.x, 0), (self.x, 8), (self.x, 16), (self.y, 0), (self.y, 8),
                        (self.ox, 0), (self.ox, 8), (self.ox, 16), (self.oy, 0), (self.oy, 8)):
            out += [(v >> sh) & 0xFF for v in arr]
        return bytes(out)
