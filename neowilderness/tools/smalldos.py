#!/usr/bin/env python3
"""smalldos.py: read Wilderness (Electric Transit) SMALLDOS disks.

Usage: smalldos.py IMAGE.dsk [--order dos|prodos|phys] [--extract DIR]
"""
import argparse, os, sys

DOS_L2P = [0, 13, 11, 9, 7, 5, 3, 1, 14, 12, 10, 8, 6, 4, 2, 15]
DOS_P2L = [DOS_L2P.index(p) for p in range(16)]
ORDERS = {
    'dos': DOS_L2P,
    'prodos': [0, 2, 4, 6, 8, 10, 12, 14, 1, 3, 5, 7, 9, 11, 13, 15],
    'phys': list(range(16)),
    # SMALLDOS sector s = DOS 3.3 logical sector 15 - s
    'smalldos': [DOS_L2P[15 - s] for s in range(16)],
}


class Disk:
    def __init__(self, data, order='smalldos'):
        self.d, self.m = data, ORDERS[order]
        # Game disks number tracks from the outside in: SMALLDOS track t is
        # physical track 34 - t, so the catalog (track 0) sits on track $22.
        self.flip = False
        self.flip = self.sector(0, 0)[:4] != b'\x06\0\0\0'

    def sector(self, t, s):
        if self.flip:
            t = 34 - t
        o = (t * 16 + DOS_P2L[self.m[s]]) * 256
        return self.d[o:o + 256]

    def run(self, t, s, n):
        out = b''
        for _ in range(n):
            out += self.sector(t, s)
            s += 1
            if s == 16:
                t, s = t + 1, 0
        return out

    def catalog(self):
        # 4 catalog sectors on SMALLDOS track 0; each
        # holds 5 entries of 32 bytes at +$60: type, sectors, track, sector,
        # 0, name (27 chars, high ASCII).  Files are contiguous runs.
        if self.sector(0, 0)[:4] != b'\x06\0\0\0':
            return
        for cs in range(4):
            sec = self.sector(0, cs)
            for o in range(0x60, 256, 32):
                e = sec[o:o + 32]
                if e[0] not in (0xC1, 0xC2):
                    continue
                name = bytes(b & 0x7F for b in e[5:]).decode().rstrip()
                yield chr(e[0] & 0x7F), e[1], e[2], e[3], e[4], name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('--order', default='smalldos', choices=ORDERS)
    ap.add_argument('--extract')
    a = ap.parse_args()
    dk = Disk(open(a.image, 'rb').read(), a.order)
    for typ, n, t, s, x, name in dk.catalog():
        print(f'{typ} {n:3d} T{t:02X} S{s:X} {x:02X} {name}')
        if a.extract:
            os.makedirs(a.extract, exist_ok=True)
            open(os.path.join(a.extract, f'{name}.{typ}'), 'wb').write(dk.run(t, s, n))


if __name__ == '__main__':
    sys.exit(main())
