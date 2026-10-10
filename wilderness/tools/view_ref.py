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
    rows 0..159; the horizon is row 95.
  - the column is painted from the bottom: each visible sample fills the rows
    between its row and the previous top with the ground colour and leaves a
    black dot on its own row; the sky fills what remains.
Colours are pixel pairs (even, odd): sky and water violet (1, 0), ground green
(0, 1), snow white (1, 1), ridge black (0, 0). The view covers HGR rows 0..159.

Usage: view_ref.py MAP.bin [X8.8 Y8.8 HEADING] OUT.png
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import topo  # noqa: E402

GW, GH, HEADER = 112, 84, 64
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


def render(m, px, py, heading):
    """HGR bytes of rows 0..159 (40 bytes each), page cleared to 0 first."""
    grid = m[HEADER:]
    snow = m[11]
    eye = (grid[(py >> 8) * GW + (px >> 8)] & 0x7F) + 2
    fb = bytearray(VIEW_ROWS * 40)

    def paint(col, r0, r1, colour):
        for p, on in zip((2 * col, 2 * col + 1), colour):
            b, bit = divmod(p, 7)
            for r in range(r0, r1):
                o = r * 40 + b
                fb[o] = (fb[o] & ~(1 << bit)) | (on << bit)

    for col in range(140):
        dx, dy = direction(heading - 70 + col)
        x, y = px, py
        thr, inc, top = -0x8000, 0, VIEW_ROWS
        for n in range(1, STEPS + 1):
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
            if inc >= 512:
                off = HORIZON
            elif inc < -512:
                continue
            else:
                off = min((inc * 3) >> 4, HORIZON)
                if off < HORIZON - VIEW_ROWS + 1:
                    continue
            row = HORIZON - off
            if row < top:
                colour = WATER if v & 0x80 else (SNOWC if v & 0x7F >= snow else GROUND)
                paint(col, row + 1, top, colour)
                paint(col, row, row + 1, RIDGE)
                top = row
                if top == 0:
                    break
        paint(col, 0, top, SKY)
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
