#!/usr/bin/env python3
"""view_ref.py: bit-exact reference of the 6502 view renderer (src/view.s).

Same model as the original SURV3D (see docs/ANALYSE.md), on the MAP grid:
  - 140 columns of 2 pixels; column c looks at azimuth heading - 70 + c
    (560 units per turn, 0 = north, 140 = east): a 90 degree field of view.
  - the ray starts at (x, y) in 8.8 cells and moves 1 cell (2 units) per
    step along a 8.8 sine table, at most 128 steps or until it leaves the map.
  - eye = ground level + 2. At step n, dz = level - eye is visible when it
    beats the steepest slope so far: dz > thr, with thr += inc each step.
    A visible sample sets inc = dz * 256 / n (truncated), thr = dz * 256,
    and is drawn at row 95 - ((inc * 3) >> 4) (= 95 - 48 * dz / n),
    rows 0..159 except the central compass HUD; the horizon is row 95.
  - the column is painted from the bottom: each visible sample fills the rows
    between its row and the previous top with the ground colour and leaves a
    black dot on its own row; the sky fills what remains.
Colours are pixel pairs (even, odd): sky and water violet (1, 0), ground green
(0, 1), snow white (1, 1), ridge black (0, 0). The terrain covers HGR rows
0..159; rows 0..15 are reserved for the survival panels and compass.

Usage: view_ref.py MAP.bin [X8.8 Y8.8 HEADING] OUT.png
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import topo  # noqa: E402

GW, GH, HEADER = 112, 84, 64
HUD_ROWS = 16
VIEW_ROWS, HORIZON, STEPS = 160, 95, 128
SINQ = [round(256 * math.sin(i * math.pi / 2 / 140)) for i in range(141)]
SKY, GROUND, SNOWC, WATER, RIDGE = (1, 0), (0, 1), (1, 1), (1, 0), (0, 0)


def direction(a):
    q, i = divmod(a % 560, 140)
    s, c = SINQ[i], SINQ[140 - i]
    return ((s, c), (c, -s), (-s, -c), (-c, s))[q]


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


TILT_ROWS = 96          # LOOK UP / DOWN: rows per tilt step (docs/LOOK_UPDOWN.md)


def sample_row(inc, tilt=0):
    """Screen row of a visible sample of slope inc (signed 8.8), or None.

    95 - floor(3 * inc / 16) (= 95 - 48 * dz / n), moved down by 96 rows
    per tilt step (LOOK UP: tilt 1; LOOK DOWN: -1): 0 when above the view,
    None (hidden, the slope still counts for occlusion) below row 159.
    96 rows are 512 slope units: src/wild.s tilt_row projects the slope
    inc - 512 * tilt with the level tables."""
    row = HORIZON - ((inc * 3) >> 4) + TILT_ROWS * tilt
    if row >= VIEW_ROWS:
        return None
    return max(row, 0)


def columns(m, px, py, heading, tilt=0, steps=STEPS):
    """Per column, in painting order: [(kind, r0, r1, n)], rows r0..r1-1.

    kind: 'ground', 'snow', 'water' (the band below a visible sample n ray
    steps away), 'ridge' (that sample's own row) or 'sky' (rows 0..top-1,
    n = last step). Empty bands are kept: they are what the 6502 paints.
    tools/dhgr_ref.py colours the same events with the DHGR moods.
    tilt: -1, 0, 1 (LOOK DOWN, level, LOOK UP). steps: the ray budget
    (src/wild.s render_weather_limit: visibility // 2 - 1 steps when the
    weather visibility is below 240 half-cells, else 128).
    """
    grid = m[HEADER:]
    snow = m[11]
    eye = (grid[(py >> 8) * GW + (px >> 8)] & 0x7F) + 2
    out = []
    for col in range(140):
        events = []
        dx, dy = direction(heading - 70 + col)
        x, y = px, py
        thr, inc, top = -0x8000, 0, VIEW_ROWS
        n = 0
        for n in range(1, steps + 1):
            x, y = (x + dx) & 0xFFFF, (y + dy) & 0xFFFF
            if x >> 8 >= GW or y >> 8 >= GH:
                break
            v = grid[(y >> 8) * GW + (x >> 8)]
            dz = (v & 0x7F) - eye
            thr += inc
            if thr > 0x7FFF:
                break                     # nothing left can beat this slope
            thr = max(thr, -0x8000)
            if dz <= thr >> 8:
                continue
            q = (abs(dz) << 8) // n
            inc = -q if dz < 0 else q
            thr = dz << 8
            row = sample_row(inc, tilt)
            if row is None:
                continue
            if row < top:
                kind = 'water' if v & 0x80 else ('snow' if v & 0x7F >= snow else 'ground')
                events.append((kind, row + 1, top, n))
                events.append(('ridge', row, row + 1, n))
                top = row
                if top == 0:
                    break
        events.append(('sky', 0, top, n))
        out.append(events)
    return out


COLOURS = {'ground': GROUND, 'snow': SNOWC, 'water': WATER, 'ridge': RIDGE, 'sky': SKY}


def render(m, px, py, heading, tilt=0):
    """HGR bytes of rows 0..159 (40 bytes each), page cleared to 0 first."""
    fb = bytearray(VIEW_ROWS * 40)

    def paint(col, r0, r1, colour):
        for p, on in zip((2 * col, 2 * col + 1), colour):
            b, bit = divmod(p, 7)
            for r in range(r0, r1):
                o = r * 40 + b
                fb[o] = (fb[o] & ~(1 << bit)) | (on << bit)

    for col, events in enumerate(columns(m, px, py, heading, tilt)):
        for kind, r0, r1, n in events:
            paint(col, r0, r1, COLOURS[kind])
    for y in range(HUD_ROWS):
        fb[y*40:(y+1)*40] = bytes(40)
    return bytes(fb)


def to_png(path, fb):
    """Approximate NTSC colours, 280 x 160."""
    rgb = bytearray(280 * VIEW_ROWS * 3)
    pal = {(0, 0): b'\0\0\0', (1, 0): b'\xd0\x40\xff', (0, 1): b'\x30\xc0\x30', (1, 1): b'\xff\xff\xff'}
    for r in range(VIEW_ROWS):
        for c in range(140):
            pair = tuple((fb[r * 40 + (p // 7)] >> (p % 7)) & 1 for p in (2 * c, 2 * c + 1))
            o = (r * 280 + 2 * c) * 3
            rgb[o:o + 6] = pal[pair] * 2
    topo.png(path, 280, VIEW_ROWS, rgb)


def main():
    m = open(sys.argv[1], 'rb').read()
    if len(sys.argv) == 6:
        px, py, heading = (int(v, 0) for v in sys.argv[2:5])
    else:
        px, py, heading = m[2] | m[3] << 8, m[4] | m[5] << 8, m[6] | m[7] << 8
    to_png(sys.argv[-1], render(m, px, py, heading))


if __name__ == '__main__':
    main()
