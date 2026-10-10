#!/usr/bin/env python3
"""view3d.py: prototype of the Wilderness first-person terrain view.

Model recovered from SURV3D.CODE ($0800):
  - 140 columns of 2 pixels, one azimuth unit each: 139 units per 90 degrees,
    so the field of view is 90 degrees, centered on the heading.
  - per column a ray leaves (x, y) in steps of 2 map units, up to 128 steps.
  - at each step: h = height(x, y) // 2 (row-interpolated TOPO), dz = h - eye,
    q = clamp(dz * 256 / n, -127, 127) for step n, row = 95 - q * 96 / 256.
  - a sample is drawn only if q beats the steepest one seen so far
    (occlusion), which leaves the striped ridge lines of the original.
  - eye = ground // 2 + 1; h // 2 >= 24 (7200 ft) is snow.
Altitude in feet = 2400 + 100 * level (2400 = byte $60A0 * 100).

Usage: view3d.py TOPO.B X Y HEADING_DEG OUT.png
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import topo  # noqa: E402

SKY, GRASS, SNOW, WATER, LINE = b'\xd0\x40\xff', b'\x30\xc0\x30', b'\xff\xff\xff', b'\xd0\x40\xff', b'\x00\x00\x00'
SNOW_LINE = 24


def render(hm, water, x0, y0, heading):
    W, H = 280, 160
    img = [[SKY] * W for _ in range(H)]
    eye = int(hm[int(y0)][int(x0)]) // 2 + 1
    for col in range(140):
        a = math.radians(heading - 45 + col * 90 / 139)
        dx, dy = 2 * math.sin(a), 2 * math.cos(a)   # 0 = north (+y), 90 = east (+x)
        best = -128
        top = H                                     # lowest row not yet painted
        x, y = x0, y0
        for n in range(1, 129):
            x, y = x + dx, y + dy
            if not (0 <= x < 224 and 0 <= y < 168):
                break
            h = int(hm[int(y)][int(x)]) // 2
            q = max(-127, min(127, (h - eye) * 256 // n))
            if q <= best:
                continue
            best = q
            row = 95 - q * 96 // 256
            if row >= top:
                continue
            c = WATER if water[int(y)][int(x)] else (SNOW if h >= SNOW_LINE else GRASS)
            for r in range(max(row, 0), top):
                img[r][2 * col] = img[r][2 * col + 1] = c
            if row >= 0:
                img[row][2 * col] = img[row][2 * col + 1] = LINE
            top = row
    return img


def main():
    path, x0, y0, heading, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
    t = open(path, 'rb').read()
    hm = topo.heightmap(t)
    water = [[False] * 224 for _ in range(168)]
    for y, items in enumerate(topo.rows(t)):
        for x, v, f in items:
            if isinstance(f, tuple):
                for xx in range(x, min(f[1], 223) + 1):
                    water[y][xx] = True
            elif f is not None:
                water[y][x] = True
    img = render(hm, water, x0, y0, heading)
    topo.png(out, 280, 160, b''.join(b''.join(r) for r in img))


if __name__ == '__main__':
    main()
