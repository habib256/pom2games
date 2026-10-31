"""Ground contact on line segments (lib/physics verlet_seg.asm).

The ground is a list of segments: walls, ceilings, overhangs, loops, what
a height map (one row per column) cannot hold. Segment k starts at
(x0, y0) (16.8 / 8.8, sub-pixel), runs along its tangent (-ny, nx) for
smax (8.8) and has the integer normal (nx, ny) (64 = 1.0, pointing to the
free side: on the left of the direction p0 -> p1 as seen on the screen,
rows growing downwards). A point is the centre of a disc of radius r. For
point i at (x, y):

  quick reject   its pixel (px, py) outside the segment's box bx0..bx1,
                 by0..by1 (whole pixels, unsigned compares): next segment
  dx, dy         s16(x - x0), s16(y - y0)      (the box keeps them < 128 px)
  d              s16((dx nx + dy ny) >> 6)     distance along the normal
  candidate      -depth <= d < best (best starts at r: the deepest wins,
                 the first in the scan order k = n-1 .. 0 on a tie)
  s              s16((dy nx - dx ny) >> 6)     position along the tangent:
                 0 <= s <= smax, else not this segment (no end caps: the
                 neighbour takes a joint)
  then           pen = r - d and the resolve of the height map
                 (verlet.ground.HeightMap.contact: push along the normal,
                 vn / vt, bounce, the tangent hook, rebuild).

The normal decides the line: choose normals of length close to 64
(near_normal(): nx^2 + ny^2 within a few units of 4096), because a contact
rebuilds the speed through the normal twice (decompose, rebuild): a
normal of length L scales the speed by L^2 / 4096 each tick in contact
(the 45 degree (45, -45) loses 1.1 % a tick, (50, -40) gains 0.1 %).
from_polyline() walks a polyline with those normals and places each
end on the exact tangent (8.8 corners), so the joints meet.

y_high (VL_Y_HIGH): rows are 16 bits (the box compares two bytes).
"""
import math

from .fixed import s16
from .ground import HeightMap


def near_normals(tol=12, scale=64):
    """The integer vectors (nx, ny) with |nx^2 + ny^2 - scale^2| <= tol,
    every direction: [(angle in degrees, nx, ny, error)]."""
    out = []
    for nx in range(-scale - 1, scale + 2):
        for ny in range(-scale - 1, scale + 2):
            e = nx * nx + ny * ny - scale * scale
            if abs(e) <= tol:
                out.append((math.degrees(math.atan2(ny, nx)) % 360, nx, ny, e))
    return sorted(out)


def near_normal(dx, dy, tol=12, max_err=2.0):
    """The normal of the direction (dx, dy) (free side on its left on the
    screen): the closest in angle among near_normals(tol) if within max_err
    degrees, else the rounded unit normal (the length error stays then)."""
    want = math.degrees(math.atan2(-dx, dy)) % 360       # (dy, -dx)
    best = None
    for a, nx, ny, e in near_normals(tol):
        da = abs((a - want + 180) % 360 - 180)
        key = (da, abs(e))
        if best is None or key < best[0]:
            best = (key, nx, ny)
    if best[0][0] <= max_err:
        return best[1], best[2]
    ln = math.hypot(dx, dy)
    return int(round(64 * dy / ln)), int(round(-64 * dx / ln))


class Segment:
    """x0 (16.8), y0 (8.8 / 16.8), the normal, smax (8.8), the box (px)
    and the end (x1, y1) (for drawing and the checks)."""

    def __init__(self, x0, y0, nx, ny, smax, box, x1, y1):
        self.x0, self.y0, self.nx, self.ny, self.smax = x0, y0, nx, ny, smax
        self.bx0, self.bx1, self.by0, self.by1 = box
        self.x1, self.y1 = x1, y1

    def __repr__(self):
        return (f'Segment({self.x0 / 256:.2f},{self.y0 / 256:.2f} -> {self.x1 / 256:.2f},{self.y1 / 256:.2f} '
                f'n=({self.nx},{self.ny}) smax={self.smax:#x})')


class SegmentGround:
    """segs: [(x0, y0, x1, y1)] in 8.8 (ints, sub-pixel ends) with an
    optional normal: (x0, y0, x1, y1, nx, ny). Without one, the normal is
    near_normal() of the direction; the segment then keeps (x0, y0), runs
    along the normal's tangent for the projection of p1 (its end moves a
    little when the normal is not exactly the direction's: from_polyline()
    chains the next segment from that end).

    radius, bounce: as the height map (VL_RADIUS, VL_BOUNCE); depth
    (VL_SEG_DEPTH, 8.8): a point further than this behind a segment's line
    is not in contact with it (a thin wall seen from its back); margin:
    pixels added around each box (default: radius and depth + 1)."""

    def contact(self, p, i, tangent=None, *args):
        """Contact of point i of Points p: HeightMap.contact (the same
        resolve, through probe_at) with this ground; vl_sgi[i] = the
        segment (0xFF none). -> vt after the hook, or None."""
        self._pt = i
        vt = HeightMap.contact(self, p, i, tangent, *args)
        self.sgi[i] = 0xFF if self.hit is None else self.hit
        return vt

    def __init__(self, segs, radius=0x0600, bounce=64, depth=0x0400, y_high=False, margin=None, cache=None):
        self.radius, self.bounce, self.depth, self.y_high = radius, bounce, depth, y_high
        self.cache = cache              # VL_SEG_CACHE (8.8) or None
        self.sgi = {}                   # vl_sgi: point -> its contact segment (0xFF none)
        if margin is None:
            margin = (max(radius, depth) + 255 >> 8) + 1
        self.margin = margin
        self.segs = []
        self.hit = None
        for sg in segs:
            x0, y0, x1, y1 = sg[:4]
            nx, ny = sg[4:6] if len(sg) > 4 else near_normal(x1 - x0, y1 - y0)
            self.segs.append(self._make(x0, y0, x1, y1, nx, ny))
        assert 1 <= len(self.segs) <= 128, 'VL_GROUND_SEGMENTS is 1..128'

    def _make(self, x0, y0, x1, y1, nx, ny):
        assert -64 <= nx <= 64 and -64 <= ny <= 64, (nx, ny)
        smax = (s16(y1 - y0) * nx - s16(x1 - x0) * ny) >> 6
        assert smax > 0, f'segment ({x0:#x},{y0:#x})-({x1:#x},{y1:#x}): empty along its tangent'
        # the end actually used: p0 + t 64 smax / |t|^2, t = (-ny, nx)
        ln2 = nx * nx + ny * ny
        ex = x0 + int(round(-ny * smax * 64 / ln2))
        ey = y0 + int(round(nx * smax * 64 / ln2))
        m = self.margin
        bx0 = (min(x0, ex) >> 8) - m
        bx1 = (max(x0, ex) >> 8) + m
        by0 = (min(y0, ey) >> 8) - m
        by1 = (max(y0, ey) >> 8) + m
        bx0, bx1 = max(bx0, 0), min(bx1, 0xFFFF)      # (unsigned compares)
        if self.y_high:
            by0, by1 = max(by0, 0), min(by1, 0x7FFF)
        else:
            by0, by1 = max(by0, 0), min(by1, 255)
        # the 6502 keeps dx, dy, d and s in 16 bits: |..| < 128 px
        assert bx1 - bx0 <= 88 and by1 - by0 <= 88, \
            f'segment ({x0 / 256:.1f},{y0 / 256:.1f}): box over 88 px, split it'
        sg = Segment(x0, y0, nx, ny, smax, (bx0, bx1, by0, by1), ex, ey)
        sg.given = (x0, y0, x1, y1, nx, ny)
        return sg

    @classmethod
    def from_polyline(cls, pts, closed=False, **kw):
        """pts: [(x, y)] in pixels (floats). Each segment's normal is the
        near_normal() of its direction, it starts where the previous one
        ended (8.8, rounded) and runs to the projection of the next corner:
        the joints meet, the corners move by a fraction of a pixel."""
        pts = list(pts) + ([pts[0]] if closed else [])
        segs = []
        x, y = int(round(pts[0][0] * 256)), int(round(pts[0][1] * 256))
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            bx8, by8 = int(round(bx * 256)), int(round(by * 256))
            nx, ny = near_normal(bx - ax, by - ay)
            ln2 = nx * nx + ny * ny
            # length along the tangent t = (-ny, nx) of the vector to the corner
            proj = ((bx8 - x) * -ny + (by8 - y) * nx) / ln2
            ex, ey = x + int(round(-ny * proj)), y + int(round(nx * proj))
            segs.append((x, y, ex, ey, nx, ny))
            x, y = ex, ey
        return cls(segs, **kw)

    def specs(self):
        """The (x0, y0, x1, y1, nx, ny) of each segment as given: to join
        grounds, SegmentGround(a.specs() + b.specs(), ...)."""
        return [sg.given for sg in self.segs]

    @property
    def n(self):
        return len(self.segs)

    def end_errors(self):
        """Distance (8.8) of each segment's given end from its line (the
        integer formula): a check that the normals fit the directions."""
        return [s16(((sg.x1 - sg.x0) * sg.nx + (sg.y1 - sg.y0) * sg.ny) >> 6) for sg in self.segs]

    def probe_at(self, x, y):
        """Point at (x 16.8, y 8.8 / 16.8) -> (nx, ny, pen) in contact,
        else None; self.hit = the segment (None without contact). With
        cache (VL_SEG_CACHE), the point's last segment (self.sgi, by
        contact()) is taken without the scan when -depth <= d < radius and
        cache <= s <= smax - cache."""
        if self.cache is not None:      # VL_SEG_CACHE: the last segment first
            k = self.sgi.get(getattr(self, '_pt', None), 0xFF)
            if k < len(self.segs):
                sg = self.segs[k]
                dx, dy = s16(x - sg.x0), s16(y - sg.y0)
                d = s16((dx * sg.nx + dy * sg.ny) >> 6)
                if -self.depth <= d < self.radius:
                    s = s16((dy * sg.nx - dx * sg.ny) >> 6)
                    if s >= self.cache and s + self.cache <= sg.smax:
                        self.hit = k
                        return sg.nx, sg.ny, self.radius - d
        px = (x >> 8) & 0xFFFF
        py = (y >> 8) & (0xFFFF if self.y_high else 0xFF)
        best, hit = self.radius, None
        for k in range(len(self.segs) - 1, -1, -1):
            sg = self.segs[k]
            if px < sg.bx0 or px > sg.bx1 or py < sg.by0 or py > sg.by1:
                continue
            dx, dy = s16(x - sg.x0), s16(y - sg.y0)
            d = s16((dx * sg.nx + dy * sg.ny) >> 6)
            if d >= best or d < -self.depth:
                continue
            s = s16((dy * sg.nx - dx * sg.ny) >> 6)
            if s < 0 or s > sg.smax:
                continue
            best, hit = d, k
        self.hit = hit
        if hit is None:
            return None
        sg = self.segs[hit]
        return sg.nx, sg.ny, self.radius - best

    # --- the 6502 tables ---------------------------------------------------------
    def consts(self):
        c = [('VL_GROUND_SEGMENTS', self.n, 'dec'), ('VL_SEG_DEPTH', self.depth)]
        if self.cache is not None:
            c.append(('VL_SEG_CACHE', self.cache))
        return c

    def tables(self):
        """(label, values) rows for verlet.emit: the segment tables
        verlet_seg.asm reads (signed bytes as '<v')."""
        S = self.segs
        out = [('vl_sg_x0f', [sg.x0 & 0xFF for sg in S]), ('vl_sg_x0l', [(sg.x0 >> 8) & 0xFF for sg in S]),
               ('vl_sg_y0f', [sg.y0 & 0xFF for sg in S]), ('vl_sg_y0h', [(sg.y0 >> 8) & 0xFF for sg in S]),
               ('vl_sg_nx', [f'<{sg.nx}' for sg in S]), ('vl_sg_ny', [f'<{sg.ny}' for sg in S]),
               ('vl_sg_sl', [sg.smax & 0xFF for sg in S]), ('vl_sg_sh', [sg.smax >> 8 for sg in S]),
               ('vl_sg_bx0l', [sg.bx0 & 0xFF for sg in S]), ('vl_sg_bx0h', [sg.bx0 >> 8 for sg in S]),
               ('vl_sg_bx1l', [sg.bx1 & 0xFF for sg in S]), ('vl_sg_bx1h', [sg.bx1 >> 8 for sg in S]),
               ('vl_sg_by0', [sg.by0 & 0xFF for sg in S]), ('vl_sg_by1', [sg.by1 & 0xFF for sg in S])]
        if self.y_high:
            out += [('vl_sg_by0h', [sg.by0 >> 8 for sg in S]), ('vl_sg_by1h', [sg.by1 >> 8 for sg in S])]
        return out

    def table_lines(self):
        from .emit import table_line
        return [table_line(*t) for t in self.tables()]
