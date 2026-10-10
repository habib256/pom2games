#!/usr/bin/env python3
"""topo.py: decode a Wilderness TOPO map (memory image loaded at $6000).

The map is 224 x 168 cells. For each row y, $6100+y / $61A8+y hold the high /
low byte of a record list, terminated by $FF:
  x, level              level < $80: ground height where the row crosses it
  x, $80|h, $80         river point at height h
  x, $80|h, $01, x1     lake span x..x1 at height h
  x, $80|h, f           other marker f (not drawn by TDRAW)
Woods: from $6250, one list of (x0, x1) spans per row, each ended by $FF.

Usage: topo.py TOPO.B OUT.png
"""
import struct, sys, zlib

W, H = 224, 168


def rows(t):
    m = lambda a: t[a - 0x6000]
    for y in range(H):
        i = m(0x61A8 + y) | m(0x6100 + y) << 8
        items = []
        while m(i) != 0xFF:
            x, v = m(i), m(i + 1)
            i += 2
            if v & 0x80:
                f = m(i)
                i += 1
                if f == 1:
                    items.append((x, v & 0x7F, (1, m(i))))
                    i += 1
                else:
                    items.append((x, v & 0x7F, f))
            else:
                items.append((x, v, None))
        yield items


def woods(t):
    i = 0x250
    for y in range(H):
        spans = []
        while t[i] != 0xFF:
            spans.append((t[i], t[i + 1]))
            i += 2
        i += 1
        yield spans


def heightmap(t):
    hm = []
    for items in rows(t):
        pts = sorted((x, v) for x, v, f in items) or [(0, 0)]
        row = []
        for x in range(W):
            lo = max((p for p in pts if p[0] <= x), default=pts[0])
            hi = min((p for p in pts if p[0] >= x), default=pts[-1])
            row.append(lo[1] if hi[0] == lo[0] else
                       lo[1] + (hi[1] - lo[1]) * (x - lo[0]) / (hi[0] - lo[0]))
        hm.append(row)
    return hm


def png(path, w, h, rgb):
    raw = b''.join(b'\0' + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    ch = lambda k, d: struct.pack('>I', len(d)) + k + d + struct.pack('>I', zlib.crc32(k + d))
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                           + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))


def main():
    t = open(sys.argv[1], 'rb').read()
    hm = heightmap(t)
    top = max(max(r) for r in hm)
    rgb = bytearray(W * H * 3)
    for y, r in enumerate(hm):
        for x, v in enumerate(r):
            g = int(40 + 200 * v / top)
            o = ((H - 1 - y) * W + x) * 3   # row 0 is the south edge
            rgb[o:o + 3] = bytes((g // 2, g, g // 2))
    put = lambda x, y, c: rgb.__setitem__(slice(((H - 1 - y) * W + x) * 3, ((H - 1 - y) * W + x) * 3 + 3), c)
    for y, spans in enumerate(woods(t)):
        for x0, x1 in spans:
            for x in range(x0, min(x1, W - 1) + 1):
                if (x + y) % 2:
                    put(x, y, b'\x00\x90\x00')
    for y, items in enumerate(rows(t)):
        for x, v, f in items:
            if isinstance(f, tuple):
                for xx in range(x, min(f[1], W - 1) + 1):
                    put(xx, y, b'\xff\x30\xff')
            elif f is not None:
                put(x, y, b'\xff\x30\xff' if f == 0x80 else b'\xff\x00\x00')
            else:
                put(x, y, b'\xff\xff\xff' if v % 4 == 0 else b'\xff\xc0\x00')
    png(sys.argv[2], W, H, rgb)
    print(f'max level {top}')


if __name__ == '__main__':
    main()
