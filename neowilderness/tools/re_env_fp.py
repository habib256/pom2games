#!/usr/bin/env python3
"""re_env_fp.py: decode Applesoft 5-byte floats (MBF) from a RAM image.

Usage: re_env_fp.py RAM.bin START END   -> every 5-byte slot that decodes sanely
       re_env_fp.py RAM.bin ADDR...      -> the floats at these addresses
"""
import sys


def mbf(b):
    if b[0] == 0:
        return 0.0
    sign = -1 if b[1] & 0x80 else 1
    mant = ((b[1] | 0x80) << 24 | b[2] << 16 | b[3] << 8 | b[4]) / 2 ** 32
    return sign * mant * 2.0 ** (b[0] - 128)


if __name__ == '__main__':
    m = open(sys.argv[1], 'rb').read()
    args = [int(a, 16) for a in sys.argv[2:]]
    for a in (range(args[0], args[1]) if len(args) == 2 and args[1] - args[0] > 5 else args):
        v = mbf(m[a:a + 5])
        print(f'{a:04X} {m[a:a + 5].hex(" ")}  {v:.6g}')
