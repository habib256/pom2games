"""Ground contact on a height map (lib/physics verlet_hmap.asm).

The ground is one row per world pixel, h[x] (rows grow downwards, 0..255).
A point is the centre of a disc of radius r (8.8). For point i:

  slope  s = clamp(s8(h[px + probe] - h[px - probe]), -slope_max, slope_max)
  normal (nx, ny) = 64 (s, -2 probe) / |(s, 2 probe)|   (tables, 64 = 1.0)
  w      = (h[px] << 8) - y; w >= far: no contact; w < -far: -far
  dist   = (w * -ny) >> 6       height of the centre above the ground line
  dist >= r: no contact; else pen = r - dist:
  push   x += (pen nx) >> 6, y += (pen ny) >> 6
  split  vn = (vx nx + vy ny) >> 6, vt = (vx (-ny) + vy nx) >> 6
  bounce vn < 0: vn = (-vn bounce) >> 8
  hook   vt = tangent(i, vt, ...)    (traction, brake, friction: the game's)
  rebuild vx = (vn nx + vt (-ny)) >> 6, vy = (vn ny + vt nx) >> 6,
          ox = x - vx, oy = y - vy

The slope is a byte difference (s8) like on the 6502: keep |h[x + probe] -
h[x - probe]| < 128. The tangent points forward along the ground, (-ny, nx).

base (VL_GROUND_BASE, with VL_Y_HIGH): the ground row is h[x] + base, for
worlds taller than 256 rows (y 16.8): w = ((h[px] + base) << 8) - y.
"""
import math

from .fixed import s16

_NORMALS = {}


def normals(slope_max, run=4, scale=64):
    """(nx, ny) tables, index s + slope_max, for slopes -slope_max..slope_max
    rows over `run` pixels."""
    key = (slope_max, run, scale)
    if key not in _NORMALS:
        nx, ny = [], []
        for s in range(-slope_max, slope_max + 1):
            ln = math.hypot(s, run)
            nx.append(int(round(scale * s / ln)))
            ny.append(int(round(-scale * run / ln)))
        _NORMALS[key] = (nx, ny)
    return _NORMALS[key]


def decompose(vx, vy, nx, ny):
    """-> (vn, vt): along the normal and the tangent (-ny, nx), >> 6."""
    return (vx * nx + vy * ny) >> 6, (vy * nx - vx * ny) >> 6


def rebuild(vn, vt, nx, ny):
    """-> (vx, vy) from the normal and tangent parts, >> 6."""
    return (vn * nx - vt * ny) >> 6, (vn * ny + vt * nx) >> 6


class HeightMap:
    def __init__(self, h, slope_max=15, probe=2, radius=0x0600, far=0x2000, bounce=64, base=0):
        self.h = h
        self.base = base
        self.slope_max, self.probe = slope_max, probe
        self.radius, self.far, self.bounce = radius, far, bounce
        self.nx, self.ny = normals(slope_max, 2 * probe)

    def height(self, px):
        return self.h[px]

    def slope(self, px):
        h, p, m = self.h, self.probe, self.slope_max
        s = (h[px + p] - h[px - p]) & 0xFF
        if s & 0x80:
            s -= 0x100
        return -m if s < -m else m if s > m else s

    def probe_at(self, x, y):
        """Point at (x 16.8, y 8.8) -> (nx, ny, pen) in contact, else None."""
        px = x >> 8
        s = self.slope(px) + self.slope_max
        nx, ny = self.nx[s], self.ny[s]
        w = ((self.h[px] + self.base) << 8) - y
        far = self.far
        if w >= far:
            return None
        if w < -far:
            w = -far
        dist = (w * -ny) >> 6
        if dist >= self.radius:
            return None
        return nx, ny, self.radius - dist

    def contact(self, p, i, tangent=None, *args):
        """Ground contact of point i of Points p. -> vt (after the tangent
        hook), or None without contact. tangent(i, vt, *args) -> vt runs
        between the bounce and the rebuild (p.ox[i] is still the old one)."""
        x, y, ox, oy = p.x, p.y, p.ox, p.oy
        hit = self.probe_at(x[i], y[i])
        if hit is None:
            return None
        nx, ny, pen = hit
        x[i] += (pen * nx) >> 6
        y[i] += (pen * ny) >> 6
        vx = s16(x[i] - ox[i])
        vy = s16(y[i] - oy[i])
        vn = (vx * nx + vy * ny) >> 6
        vt = (vy * nx - vx * ny) >> 6
        if vn < 0:
            vn = (-vn * self.bounce) >> 8
        if tangent is not None:
            vt = tangent(i, vt, *args)
        ox[i] = x[i] - ((vn * nx - vt * ny) >> 6)
        oy[i] = y[i] - ((vn * ny + vt * nx) >> 6)
        return vt
