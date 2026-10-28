#!/usr/bin/env python3
"""loadcalls.py: list the inline calls of the resident block loader ($4B03).

JSR $4B03 is followed by: count, command (bits 0-1: 1 read, 2 write, 3 format),
then count little-endian pointers to 6-byte descriptors
(block LE16, address LE16, length LE16).

Usage: loadcalls.py MEMORY_IMAGE [LO-HI ...]   (hex ranges to scan, default 4000-5200)
"""
import re
import sys


def calls(m, lo, hi):
    for x in re.finditer(b'\x20\x03\x4b', m[lo:hi]):
        a = lo + x.start()
        n, cmd = m[a + 3], m[a + 4]
        ptrs = [m[a + 5 + 2 * k] | m[a + 6 + 2 * k] << 8 for k in range(n)]
        yield a, cmd, [(p, m[p] | m[p + 1] << 8, m[p + 2] | m[p + 3] << 8, m[p + 4] | m[p + 5] << 8)
                       for p in ptrs]


def main():
    m = open(sys.argv[1], 'rb').read().ljust(0x10000, b'\0')
    ranges = [tuple(int(v, 16) for v in r.split('-')) for r in sys.argv[2:]] or [(0x4000, 0x5200)]
    for lo, hi in ranges:
        for a, cmd, ds in calls(m, lo, hi):
            s = '; '.join(f'[{p:04X}] blk ${b:03X} -> ${ad:04X}+${ln:04X}' for p, b, ad, ln in ds)
            print(f'{a:04X} cmd{cmd:02X} {s}')


if __name__ == '__main__':
    main()
