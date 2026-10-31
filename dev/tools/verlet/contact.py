"""Circle contacts (lib/physics verlet_circ.asm).

Points become circles: radius rad[i] in Q units (1 unit = 2^Q / 256 px:
Q = 5 is an eighth of a pixel, the default; 4 a sixteenth, 6 a quarter).
A pair's radii add up to R <= 127 units (Q = 5: 15.9 px). For points a, b:

  d      = b - a (x 24 bits, y 8.8 taken as 17 bits, or 24 with y_high);
           |d| >= 128 << Q on an axis: no contact (the fast path)
  q      = |d| >> Q per axis (symmetric: the magnitude first)
           q >= R on an axis, or qx^2 + qy^2 >= R^2: no contact
  s      = isqrt(qx^2 + qy^2) (lib/math isqrt16), pen = R - s (1..R)
  n      = (sx (qx rcp[s]) >> 8, sy (qy rcp[s]) >> 8), rcp[s] = ceil(2^14 / s):
           the unit normal a -> b at 64 = 1.0, |n| <= 64; s = 0: (0, -64)
  push   T = (pen |n|) >> (6 - Q) per axis (8.8): a moves -T/2, b +T/2,
           positions AND old positions (no speed from the push)
  speed  rv = v_b - v_a (16 bits), vn = (rv . n) >> 6; vn < 0 (closing):
           m = -vn, j = m + ((m e) >> 8) when m > vmin (restitution e/256),
           else j = m (inelastic); a's speed -= (j/2 |n|) >> 6 along n, b's
           += the same (moved old positions)

The halves are `share`: T >> 1 each; a pinned point (Points.pin, VL_PIN)
does not move and the other takes all of T (and of j); both pinned: no
contact. heavy = n with flags hv (VL_CIRC_HEAVY): when exactly one point of
the pair is heavy it takes half - (half >> n), the other half + (half >> n).

sleep = v (VL_CIRC_SLEEP, with pins): a point whose pin is 0x80 sleeps
(vl_integrate, vl_contact_box skip it; in a pair it is pinned). A contact
whose closing speed m exceeds v wakes it (pin 0, then a free point); a
gentler one leaves it asleep: a resting stack stays asleep, a sleeping
ball is the ground of an awake one. sleep_check (vl_circ_sleep) puts a
free point to sleep after `ticks` ticks in a row with |vx|, |vy| <= v.

Error: the distance s is exact to a unit (floor of the root of the floored
q, both within one unit: Q = 5, 1/8 px), the normal to 1/64 (each
component within 1 of 64 q / s: the reciprocal of s is rounded up, the
product floored; an axis-aligned normal is exactly 64), and the push lands each point within one unit of R apart. No
approximation of the square root itself: an exact isqrt16 on q2 < 16129
costs ~70 cycles and keeps deep hits (a fast ball half inside another)
right, where the constraint-style linearisation (q2 - R^2) / 2R^2 would
underestimate the push by 2.7 times at half the radius.

Boxes (vl_contact_box): static axis-aligned boxes (x0, y0, x1, y1), whole
pixels 0..255, edges included; the point (radius r, x < 256 px, y < 256
rows) against the closest point of each box, the same q, s, pen, n. The
centre inside a box, or within a unit of it (s = 0): out through the
nearest face (top first, then left, right, bottom), to exactly r units
from it. The speed then splits like the ground's (vn, vt), a closing vn
bounces (m > vmin: vn = (m e) >> 8, else 0), vt -= vt >> friction, and
the speed is rebuilt (old = pos - v).
"""
import math

from .fixed import s16
from .points import s24


def rcp(s):
    """ceil(2^14 / s), s = 1..127 (the 6502 table vl_crcp_lo/hi): rounded
    up, an axis-aligned normal is exactly 64 (mul_dir's short cuts)."""
    return (16384 + s - 1) // s


def _ydelta(p, a, b):
    if p.y_high:
        return s24(p.y[b] - p.y[a])
    return (p.y[b] & 0xFFFF) - (p.y[a] & 0xFFFF)


def _q(d, Q):
    """|d| >> Q, or None when |d| >= 128 << Q (no contact)."""
    ad = -d if d < 0 else d
    if ad >= 128 << Q:
        return None
    return ad >> Q


def normal(qx, qy, sx, sy, s):
    """-> (nx, ny) at 64 = 1.0; sx, sy = the signs (-1, 0, 1) of the delta."""
    if s == 0:
        return 0, -64
    r = rcp(s)
    nx = (qx * r) >> 8
    ny = (qy * r) >> 8
    return (-nx if sx < 0 else nx), (-ny if sy < 0 else ny)


def share(t, pa, pb, ha, hb, heavy):
    """Total t >= 0 -> (a's part, b's part)."""
    if pa:
        return 0, t
    if pb:
        return t, 0
    half = t >> 1
    if heavy and ha != hb:
        d = half >> heavy
        return (half - d, half + d) if ha else (half + d, half - d)
    return half, half


def _addsub(arr, i, g, v):
    """arr[i] += s16(v) when g > 0, -= s16(v) otherwise (vl_add_xv /
    vl_sub_xv: the 6502 never negates the value)."""
    v = s16(v)
    arr[i] += v if g > 0 else -v


def _move(p, i, mx, my):
    """Point i and its old position += (mx, my) (16-bit signed values)."""
    p.x[i] += mx
    p.ox[i] += mx
    p.y[i] += my
    p.oy[i] += my


def pair(p, a, b, R, Q=5, bounce=0, vmin=0, heavy=0, hv=None, sleep=0):
    """Circles a, b with radii adding up to R units. -> True in contact."""
    pin = p.pin
    pa = bool(pin is not None and pin[a])
    pb = bool(pin is not None and pin[b])
    if pa and pb:
        return False
    dx = s24(p.x[b] - p.x[a])
    qx = _q(dx, Q)
    if qx is None or qx >= R:
        return False
    dy = _ydelta(p, a, b)
    qy = _q(dy, Q)
    if qy is None or qy >= R:
        return False
    q2 = qx * qx + qy * qy
    if q2 >= R * R:
        return False
    s = math.isqrt(q2)
    pen = R - s
    nx, ny = normal(qx, qy, (dx > 0) - (dx < 0), (dy > 0) - (dy < 0), s)
    ha = hb = 0
    if heavy:
        ha, hb = bool(hv[a]), bool(hv[b])
    rvx = s16((p.x[b] - p.ox[b]) - (p.x[a] - p.ox[a]))
    rvy = s16((p.y[b] - p.oy[b]) - (p.y[a] - p.oy[a]))
    vn = s16((rvx * nx + rvy * ny) >> 6)
    if sleep and (pa or pb) and vn < 0 and -vn > sleep:
        if pa and pin[a] == 0x80:
            pin[a], pa = 0, False
        if pb and pin[b] == 0x80:
            pin[b], pb = 0, False
    sh = 6 - Q
    tx = (pen * abs(nx)) >> sh
    ty = (pen * abs(ny)) >> sh
    ax, bx = share(tx, pa, pb, ha, hb, heavy)
    ay, by = share(ty, pa, pb, ha, hb, heavy)
    gx = -1 if nx < 0 else 1
    gy = -1 if ny < 0 else 1
    for arr in (p.x, p.ox):
        _addsub(arr, a, -gx, ax)
        _addsub(arr, b, gx, bx)
    for arr in (p.y, p.oy):
        _addsub(arr, a, -gy, ay)
        _addsub(arr, b, gy, by)
    if vn >= 0:                         # (the push moved pos and old: same vn)
        return True
    m = -vn
    j = m + ((m * bounce) >> 8) if bounce and m > vmin else m
    ja, jb = share(j, pa, pb, ha, hb, heavy)
    anx, any_ = abs(nx), abs(ny)
    _addsub(p.ox, a, gx, (ja * anx) >> 6)
    _addsub(p.oy, a, gy, (ja * any_) >> 6)
    _addsub(p.ox, b, -gx, (jb * anx) >> 6)
    _addsub(p.oy, b, -gy, (jb * any_) >> 6)
    return True


def contact_all(p, rad, Q=5, bounce=0, vmin=0, heavy=0, hv=None, sleep=0):
    """Every pair i < j of the first len(rad) points, both radii non-zero
    (vl_contact_all, a in 0..n-2, b in a+1..n-1). -> contacts."""
    n, hits = len(rad), 0
    for a in range(n - 1):
        if not rad[a]:
            continue
        for b in range(a + 1, n):
            if rad[b] and pair(p, a, b, rad[a] + rad[b], Q, bounce, vmin, heavy, hv, sleep):
                hits += 1
    return hits


def _box_side(v, lo, hi, Q):
    """-> (sign, q) of a coordinate (16 bits) against [lo, hi] (8.8), or None."""
    if v < lo:
        sg, ad = -1, lo - v
    elif v > hi:
        sg, ad = 1, v - hi
    else:
        return 0, 0
    if ad >= 128 << Q:
        return None
    return sg, ad >> Q


def box1(p, i, r, bx, Q=5, bounce=0, vmin=0, friction=0):
    """Point i (radius r units, x < 256 px, y < 256 rows: boxes() checks)
    against box bx = (x0, y0, x1, y1) px. -> True in contact."""
    x0, y0, x1, y1 = bx
    xv, yv = p.x[i] & 0xFFFF, p.y[i] & 0xFFFF
    hx = _box_side(xv, x0 << 8, x1 << 8, Q)
    if hx is None or hx[1] >= r:
        return False
    hy = _box_side(yv, y0 << 8, y1 << 8, Q)
    if hy is None or hy[1] >= r:
        return False
    (sx, qx), (sy, qy) = hx, hy
    q2 = qx * qx + qy * qy
    if q2 >= r * r:
        return False
    rq = r << Q
    if q2 == 0:
        if sx == 0 and sy == 0:             # inside: the nearest face
            depth = [(yv - (y0 << 8), 0), (xv - (x0 << 8), 1), ((x1 << 8) - xv, 2), ((y1 << 8) - yv, 3)]
            face = depth[0]
            for d in depth[1:]:
                if d[0] < face[0]:
                    face = d
            face = face[1]
        else:
            face = 0 if sy < 0 else 1 if sx < 0 else 2 if sx > 0 else 3
        if face == 0:
            _move(p, i, 0, s16((y0 << 8) - rq - yv))
            nx, ny = 0, -64
        elif face == 1:
            _move(p, i, s16((x0 << 8) - rq - xv), 0)
            nx, ny = -64, 0
        elif face == 2:
            _move(p, i, s16((x1 << 8) + rq - xv), 0)
            nx, ny = 64, 0
        else:
            _move(p, i, 0, s16((y1 << 8) + rq - yv))
            nx, ny = 0, 64
    else:
        s = math.isqrt(q2)
        pen = r - s
        nx, ny = normal(qx, qy, sx, sy, s)
        sh = 6 - Q
        tx = (pen * abs(nx)) >> sh
        ty = (pen * abs(ny)) >> sh
        for arr in (p.x, p.ox):
            _addsub(arr, i, -1 if nx < 0 else 1, tx)
        for arr in (p.y, p.oy):
            _addsub(arr, i, -1 if ny < 0 else 1, ty)
    vx = s16(p.x[i] - p.ox[i])
    vy = s16(p.y[i] - p.oy[i])
    vn = s16((vx * nx + vy * ny) >> 6)
    vt = s16((vy * nx - vx * ny) >> 6)
    if vn < 0:
        m = -vn
        vn = (m * bounce) >> 8 if bounce and m > vmin else 0
    if friction:
        vt = s16(vt - (vt >> friction))
    p.ox[i] = p.x[i] - s16((vn * nx - vt * ny) >> 6)
    p.oy[i] = p.y[i] - s16((vn * ny + vt * nx) >> 6)
    return True


def boxes(p, i, r, bxs, Q=5, bounce=0, vmin=0, friction=0):
    """Point i against every box in order (vl_contact_box). -> contacts.
    Nothing for a radius 0, a pinned point, x >= 256 px (or < 0), or with
    y_high y outside rows 0..255 (tested once, before the first box)."""
    if not r or (p.pin is not None and p.pin[i]):
        return 0
    if (p.x[i] >> 16) & 0xFF or (p.y_high and (p.y[i] >> 16) & 0xFF):
        return 0
    return sum(1 for b in bxs if box1(p, i, r, b, Q, bounce, vmin, friction))


def sleep_check(p, i, still, v, ticks=16):
    """vl_circ_sleep: a free point (pin 0) with |vx| <= v and |vy| <= v
    `ticks` ticks in a row goes to sleep (pin 0x80, at rest); still[] counts.
    -> True when it fell asleep."""
    if p.pin[i]:
        return False
    vx = s16(p.x[i] - p.ox[i])
    vy = s16(p.y[i] - p.oy[i])
    if abs(vx) > v or abs(vy) > v:
        still[i] = 0
        return False
    still[i] += 1
    if still[i] < ticks:
        return False
    still[i] = 0
    p.pin[i] = 0x80
    p.ox[i], p.oy[i] = p.x[i], p.y[i]
    return True


def rad_q(px, Q=5):
    """A radius in pixels -> units (round)."""
    return int(round(px * 256 / (1 << Q)))
