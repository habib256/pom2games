#!/usr/bin/env python3
"""forest_ref.py: reference of the woodland canopies of src/forest.s.

trees() returns, per screen column, the nearest visible Sierra crown found
during the first eight ray steps (src/forest.s forest_probe): rows
begin..end-1, the cell x that phases the stipple, the end of the crown
(forest_crown_end: the trunk starts there) and the ray step n of the tree.
A crown belongs to one cell (centre_cell): every column of it, even one whose
sample crossed into the next cell along the ray, draws that cell's crown.
hgr() paints them over tools/view_ref.render like the HGR engine did (black
contour and trunk, green stipple on odd rows of the odd pixel);
tools/dhgr_ref.py colours the same canopies with the DHGR moods.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import view_ref  # noqa: E402
from mkmap import forest_at  # noqa: E402


def trees(m, px, py, heading, tilt=0):
    """{col: (begin, end, cx, crown_end, n)} of the canopy drawn per column.

    tilt (LOOK UP / DOWN): no tree looking up (the original's rule); looking
    down the feet move up by 96 rows, a foot above the view hides the tree."""
    out = {}
    if tilt > 0:
        return out
    horizon = 95 + view_ref.TILT_ROWS * tilt
    eye = (m[64 + (py >> 8) * 112 + (px >> 8)] & 127) + 2
    for col in range(140):
        dx, dy = view_ref.direction(heading - 70 + col)
        x, y = px, py
        thr, inc, top, tree = -32768, 0, 160, None
        for n in range(1, 129):
            x = (x + dx) & 65535
            y = (y + dy) & 65535
            cx, cy = x >> 8, y >> 8
            if cx >= 112 or cy >= 84:
                break
            cell = m[64 + cy * 112 + cx]
            dz = (cell & 127) - eye
            if n <= 8 and tree is None:
                tree = crown(m, px, py, x, y, dx, dy, n, eye, horizon, top)
            thr += inc
            if thr > 32767:
                break
            thr = max(thr, -32768)
            if dz <= thr >> 8:
                continue
            q = (abs(dz) << 8) // n
            inc = -q if dz < 0 else q
            thr = dz << 8
            row = view_ref.sample_row(inc, tilt)
            if row is None:
                continue
            if row < top:
                top = row
                if not top:
                    break
        if tree:
            out[col] = tree
    return out


def centre_cell(pu, pv, cu, cv, v, dv, n):
    """Along-axis cell of the crown met by a ray sample at step n (forest.s
    forest_centre).

    A crown stands on the transverse centre line of its cell (cu: transverse
    cell, centre cu * 256 + 127). The samples of every column at step n lie
    on the circle of radius 256 n around the player (pu, pv), so the crown's
    centre column meets it at pv + sign(dv) sqrt((256 n)^2 - L^2). An edge
    column may sample the crown in the next cell along the ray; it still draws
    that one crown (one base, one profile, one stipple phase). A crown centre
    lies within 38 units of each of its samples along the axis, so only the
    samples within 64 units of a cell boundary B test it, in rounded 1/16
    cells (error < 17 units): every column of a crown finds the same cell.
    The boundary is always ahead of the player (d > 0)."""
    frac = v & 255
    if 64 <= frac < 192:
        return cv
    edge = cv + 1 if frac >= 192 else cv          # B / 256
    d = abs((edge * 256 - pv + 8) >> 4)
    lat = abs((cu * 256 + 127 - pu + 8) >> 4)
    beyond = (lat * lat + d * d) >> 8 < n * n     # B before the centre
    return edge - ((not beyond) ^ (dv < 0))


def crown(m, px, py, x, y, dx, dy, n, eye, horizon, top):
    """(begin, end, cx, crown_end, n) of the crown met at step n, or None."""
    if abs(dy) >= abs(dx):      # transverse x, along y
        p = (x & 255) - 96
        cx, cy = x >> 8, centre_cell(px, py, x >> 8, y >> 8, y, dy, n)
    else:
        p = (y & 255) - 96
        cx, cy = centre_cell(py, px, y >> 8, x >> 8, x, dx, n), y >> 8
    p //= 2
    if not 0 <= p < 31 or not (0 <= cx < 112 and 0 <= cy < 84):
        return None
    cell = m[64 + cy * 112 + cx]
    if cell & 128 or (cell & 127) + m[10] >= (m[27] or 110) or not forest_at(m, cx, cy):
        return None
    dz = (cell & 127) - eye
    p = min(p, 30 - p)
    kind = (cx ^ cy) & 2
    lo = max(31, 42 - 2 * ((p + 1) // 2)) if kind else 31
    hi = 47 + 7 * p if kind else 24 + 8 * p
    q = (abs(dz) * 256) // n
    off = (q * 3) >> 4
    base = horizon - off if dz >= 0 else horizon + off
    if off < 256 and base >= 0:
        begin = max(0, base - hi // n)
        end = min(top, base - (0 if p >= 14 else lo) // n)
        if begin < 160 and end > begin:
            return (begin, end, cx, base - 32 // n, n)
    return None


def hgr(m, px, py, heading, tilt=0):
    """HGR bytes of rows 0..159: view_ref.render with the HGR canopies."""
    fb = bytearray(view_ref.render(m, px, py, heading, tilt))
    for col, (begin, end, cx, crown_end, n) in trees(m, px, py, heading, tilt).items():
        for r in range(max(16, begin), end):
            for p in (2 * col, 2 * col + 1):
                fb[r * 40 + p // 7] &= ~(1 << (p % 7))
                if begin < r < crown_end and (r ^ cx) & 1 and p & 1:
                    fb[r * 40 + p // 7] |= 1 << (p % 7)
    return bytes(fb)
