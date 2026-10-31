"""Distance constraints without a square root (lib/physics verlet_con.asm).

For points a, b at rest length L (l2q = (4 L)^2, quarter pixels):

  q   = min(|delta >> 6|, 180) on each axis      (vl_quarter_abs)
  q2  = qx^2 + qy^2                              (vl_square: quarter squares)
  d8  = clamp((q2 - l2q) >> 3, -4095, 4095)
  f   = clamp((d8 * k8) >> 8, -127, 127)         ~ (|ab| - L) / L, half
  c   = (delta * f) >> 8                         per axis
  a  += c, b -= c

The ranges: |b - a| < 128 px on each axis (16-bit deltas), a link up to
45 px (q clamped to 180). A heavy b (heavy = shift n) takes c - c' and a
takes c + c', c' = c >> n rounded toward zero: b weighs (2^n - 1) / (2^n + 1)
of a's move. minlen (px): constrain() returns True when q2 < l2q(minlen)
(DIRTBIKE: the rider squashed on a wheel).

Variants: a constraint may carry one (l2q, k8) row per variant (DIRTBIKE:
the rider's rest lengths per lean level); the 6502 reads row
constraint * nvariants + variant.

fixed_k = s (VL_CON_FIXED_K): the gain is 2^s for every row (k8 = 2^s),
f = clamp((q2 - l2q) / 2^(11 - s), +-127) rounded toward zero (one shift,
no d8, no product, no k8 table): a dead band the same on both sides of
the rest length (the floor of the product pushes a link that is a hair
short and leaves one a hair long: a body flying free creeps round). min_only
(VL_CON_MIN_ONLY, bit 7 of vl_con_b): the link only pushes (no correction
while q2 >= l2q): a minimum distance, for ragdolls and collisions. Pinned
points (Points.pin, VL_PIN): a pinned end does not move, the other takes
the whole correction (2 c); both pinned, nothing moves.
"""
from .fixed import l2q as _l2q, k8 as _k8, asr0


def constrain(p, a, b, l2q, k8, heavy=0, minlen=None, min_only=False, fixed_k=None):
    """One constraint on Points p. -> True when q2 < minlen (l2q units).
    fixed_k = s: f = (q2 - l2q) / 2^(11 - s) rounded toward zero, no d8
    (k8 unused)."""
    x, y = p.x, p.y
    dx = (x[b] - x[a]) & 0xFFFF
    if dx & 0x8000:
        dx -= 0x10000
    dy = (y[b] - y[a]) & 0xFFFF
    if dy & 0x8000:
        dy -= 0x10000
    qx = abs(dx >> 6)
    if qx > 180:
        qx = 180
    qy = abs(dy >> 6)
    if qy > 180:
        qy = 180
    q2 = qx * qx + qy * qy
    short = minlen is not None and q2 < minlen
    if min_only and q2 >= l2q:
        return short
    if fixed_k is None:
        d8 = (q2 - l2q) >> 3
        if d8 > 4095:
            d8 = 4095
        elif d8 < -4095:
            d8 = -4095
        f = (d8 * k8) >> 8
    else:
        f = asr0(q2 - l2q, 11 - fixed_k)
    if f > 127:
        f = 127
    elif f < -127:
        f = -127
    cx = (dx * f) >> 8
    cy = (dy * f) >> 8
    pin = p.pin
    if pin is not None and (pin[a] or pin[b]):
        if not pin[a]:
            x[a] += 2 * cx
            y[a] += 2 * cy
        elif not pin[b]:
            x[b] -= 2 * cx
            y[b] -= 2 * cy
        return short
    if heavy:
        hx = asr0(cx, heavy)
        hy = asr0(cy, heavy)
        x[a] += cx + hx
        y[a] += cy + hy
        x[b] -= cx - hx
        y[b] -= cy - hy
    else:
        x[a] += cx
        y[a] += cy
        x[b] -= cx
        y[b] -= cy
    return short


class Constraint:
    """Constraint(a, b, length px, stiffness, heavy=shift, minlen=px,
    variants=[length px, ...], fixed_k=s, min_only=bool): the rows are
    (l2q, k8) per variant (one row without variants); fixed_k: k8 = 2^s
    (the stiffness is then ignored)."""

    def __init__(self, a, b, length, stiff=1.0, heavy=0, minlen=None, variants=None,
                 fixed_k=None, min_only=False):
        self.a, self.b, self.length, self.stiff = a, b, length, stiff
        self.heavy = heavy
        self.minlen = None if minlen is None else _l2q(minlen)
        self.min_only = min_only
        self.fixed_k = fixed_k
        lengths = [length] if variants is None else list(variants)
        if fixed_k is not None:
            assert 0 <= fixed_k <= 8, fixed_k
            self.rows = [(_l2q(L), 1 << fixed_k) for L in lengths]
        else:
            self.rows = [(_l2q(L), _k8(L, stiff)) for L in lengths]

    @property
    def l2q(self):
        return self.rows[0][0]

    @property
    def k8(self):
        return self.rows[0][1]

    def apply(self, p, variant=0):
        l2, k = self.rows[variant]
        return constrain(p, self.a, self.b, l2, k, self.heavy, self.minlen, self.min_only, self.fixed_k)


def con_pass(p, cons, variant=0):
    """Every constraint once, in order (vl_con_pass). -> any minlen alarm."""
    short = False
    for c in cons:
        short |= c.apply(p, variant)
    return short


def tables(cons, nvariants=1):
    """The 6502 tables: con_a, con_b (one byte each per constraint, bit 7
    of con_b = min_only), con_l2 (words) and con_k8 at index constraint *
    nvariants + variant (not needed with VL_CON_FIXED_K)."""
    rows = []
    for c in cons:
        r = c.rows if len(c.rows) == nvariants else c.rows * nvariants
        assert len(r) == nvariants, (c.a, c.b, len(c.rows), nvariants)
        rows += r
    return {'con_a': [c.a for c in cons], 'con_b': [c.b | (0x80 if c.min_only else 0) for c in cons],
            'con_l2': [r[0] for r in rows], 'con_k8': [r[1] for r in rows]}
