#!/usr/bin/env python3
"""re_state_fp.py: decode Applesoft 5-byte floats in a binary.

Usage: re_state_fp.py BIN START ADDR...   (hex)
"""
import sys


def fp(b):
    e = b[0]
    if e == 0:
        return 0.0
    m = ((b[1] | 0x80) << 24 | b[2] << 16 | b[3] << 8 | b[4]) / 2 ** 32
    return (-1 if b[1] & 0x80 else 1) * m * 2.0 ** (e - 128)


if __name__ == '__main__':
    data, start = open(sys.argv[1], 'rb').read(), int(sys.argv[2], 16)
    for a in sys.argv[3:]:
        o = int(a, 16) - start
        print(f'{a}: {fp(data[o:o + 5]):.6g}  ({data[o:o + 5].hex(" ")})')
