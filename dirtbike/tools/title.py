#!/usr/bin/env python3
"""The DIRTBIKE title picture: an 8 KB HGR page (monochrome, white strokes).

    python3 tools/title.py OUT.hgr [preview.png]

A slanted DIRTBIKE logo (the game font x4), a subtitle, a rider in mid-air
over a kicker, speed lines and white hills, the port's credit on a black
band at the bottom. Rows TITLE_PROMPT..+7 (columns PROMPT_X) stay black
for the blinking prompt the game prints (src/title.inc). Strokes are at
least 2 pixels wide: a lone HGR pixel shows a colour fringe. The Makefile
packs it with fhpack (file TITLE on the disk).
"""
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import fonts  # noqa: E402
from a2test import hgr_offset  # noqa: E402

W, H = 280, 192
TITLE_PROMPT = 66               # = src/title.inc: under the subtitle
PROMPT_X = (84, 190)            # its columns (13..25 x 7 px), kept black
CREDIT = 'APPLE II PORT: VERHILLE ARNAUD'
CREDIT_Y = 183                  # white on a black band under the ground
VERSION = 'V1.1'                # bottom left, just above the ground


class Canvas:
    def __init__(self):
        self.px = [[0] * W for _ in range(H)]

    def set(self, x, y, v=1):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < W and 0 <= y < H:
            self.px[y][x] = v

    def dot(self, x, y, r=1.0, v=1):
        for yy in range(int(y - r) - 1, int(y + r) + 2):
            for xx in range(int(x - r) - 1, int(x + r) + 2):
                if (xx - x) ** 2 + (yy - y) ** 2 <= r * r:
                    self.set(xx, yy, v)

    def line(self, x0, y0, x1, y1, r=1.0):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        for i in range(n + 1):
            t = i / n
            self.dot(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r)

    def ring(self, cx, cy, rad, r=1.0):
        for i in range(96):
            a = 2 * math.pi * i / 96
            self.dot(cx + rad * math.cos(a), cy + rad * math.sin(a), r)

    def text(self, s, x, y, scale=1, slant=0.0):
        for k, ch in enumerate(s):
            rows = fonts.glyph(ch)
            for gy, bits in enumerate(rows):
                for gx in range(8):
                    if bits >> gx & 1:
                        for sy in range(scale):
                            yy = y + gy * scale + sy
                            shift = slant * (8 * scale - 1 - gy * scale - sy)
                            for sx in range(scale):
                                self.set(x + (k * 8 + gx) * scale + sx + shift, yy)

    def poly(self, pts):
        ys = [y for _, y in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            xs = []
            for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[0::2], xs[1::2]):
                for x in range(int(round(a)), int(round(b)) + 1):
                    self.set(x, y)

    def fill_below(self, profile):
        for x, top in enumerate(profile):
            for y in range(int(top), H):
                self.set(x, y)


def picture():
    c = Canvas()
    # logo: the game font x4, slanted, with a hollow drop shadow
    logo, scale, slant = 'DIRTBIKE', 4, 0.22
    width = len(logo) * 8 * scale
    x0, y0 = (W - width) // 2 - 4, 12
    shadow = Canvas()
    shadow.text(logo, x0 + 4, y0 + 4, scale, slant)
    c.text(logo, x0, y0, scale, slant)
    for y in range(H):
        for x in range(W):
            # shadow outline where the letters are not
            if shadow.px[y][x] and not c.px[y][x]:
                edge = any(not shadow.px[yy][xx] for yy, xx in
                           ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1))
                           if 0 <= yy < H and 0 <= xx < W)
                if edge:
                    c.px[y][x] = 1
    sub = 'MOTOCROSS TIME TRIAL'
    c.text(sub, (W - 8 * len(sub)) // 2, 52)
    # rolling hills along the bottom, a curved kicker on the left
    ground = [172 - 5 * math.sin(x / 21) - 3 * math.sin(x / 8 + 1) for x in range(W)]
    for x in range(0, 64):
        t = x / 63
        ground[x] = min(ground[x], 176 - 46 * t ** 1.7)
    c.fill_below(ground)
    vx = 2                                  # the version, resting on the slope
    c.text(VERSION, vx, int(min(ground[vx:vx + 8 * len(VERSION)])) - 9)
    # the credit: white on a black band at the bottom
    for y in range(CREDIT_Y - 3, H):
        c.px[y] = [0] * W
    c.text(CREDIT, (W - 8 * len(CREDIT)) // 2, CREDIT_Y)
    # the rider in mid-air, nose up, flying away from the kicker
    ang, k = math.radians(-16), 1.5
    cx, cy = 198, 120
    ca, sa = math.cos(ang), math.sin(ang)

    def at(u, v):                           # bike frame coordinates -> screen
        u, v = u * k, v * k
        return cx + u * ca - v * sa, cy + u * sa + v * ca
    rear, front = at(-17, 7), at(17, 7)
    for (wx, wy) in (rear, front):
        c.ring(wx, wy, 9 * k, 1.6)          # tyre
        c.ring(wx, wy, 9 * k - 4, 0.6)      # rim
        c.dot(wx, wy, 2.2)                  # hub
    bars, peg = at(10, -12), at(-1, 2)
    c.line(*rear, *peg, 1.8)                # swing arm
    for d in (-1.2, 1.2):                   # double fork
        c.line(front[0] + d, front[1], bars[0] + d, bars[1], 1.0)
    c.poly([at(-5, -3), at(7, -3), at(5, 5), at(-3, 5)])          # engine
    c.poly([at(-16, -8), at(-2, -8), at(10, -10), at(12, -6), at(-2, -4), at(-16, -5)])  # seat, tank
    c.line(*at(-21, -7), *at(-15, -7), 1.2)  # rear mudguard tip
    c.line(*at(13, -3), *at(22, -1), 1.2)    # front mudguard
    c.line(*at(-3, 4), *at(-16, -2), 1.0)    # exhaust
    knee, hip = at(6, -12), at(-6, -14)     # rider standing on the pegs
    shoulder, head = at(2, -27), at(5, -34)
    c.line(*peg, *knee, 2.0)
    c.line(*knee, *hip, 2.2)
    c.line(*peg, *at(2, 2), 1.6)            # boot
    c.line(*hip, *shoulder, 3.0)            # back
    c.line(*shoulder, *at(10, -20), 1.6)    # arm to the bars
    c.line(*at(10, -20), *bars, 1.6)
    c.line(*shoulder, *head, 1.6)           # neck
    c.dot(*head, 5.6)                       # helmet, black visor
    vx, vy = at(8, -35)
    c.line(vx - 1, vy, vx + 3, vy + 1, 0.8)
    for x in range(int(vx), int(vx) + 3):
        c.set(x, vy, 0)
    # speed lines behind the bike
    for j, (dy, ln) in enumerate(((-16, 38), (-4, 54), (8, 40), (20, 26))):
        x1 = cx - 50 - 5 * j
        c.line(x1 - ln, cy + dy, x1, cy + dy, 0.7)
    hint = 'H: HELP'                        # under the blinking prompt
    c.text(hint, (W - 8 * len(hint)) // 2, TITLE_PROMPT + 13)
    # no lone pixel (it would show a colour fringe): every stroke 2 wide
    for row in c.px:
        for x in range(W - 1, 0, -1):
            if row[x - 1]:
                row[x] = 1
    # keep the prompt black
    for y in range(TITLE_PROMPT - 2, TITLE_PROMPT + 10):
        for x in range(*PROMPT_X):
            c.px[y][x] = 0
    return c


def hgr(c):
    page = bytearray(8192)
    for y in range(H):
        for col in range(40):
            b = 0
            for k in range(7):
                if c.px[y][col * 7 + k]:
                    b |= 1 << k
            page[hgr_offset(y) + col] = b
    return bytes(page)


def png(c, path):
    raw = b''.join(b'\x00' + bytes(255 * v for v in row) for row in c.px)

    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 0, 0, 0, 0)) +
                           chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def main():
    c = picture()
    data = hgr(c)
    out = Path(sys.argv[1])
    if not out.exists() or out.read_bytes() != data:
        out.write_bytes(data)
    if len(sys.argv) > 2:
        png(c, sys.argv[2])


if __name__ == '__main__':
    main()
