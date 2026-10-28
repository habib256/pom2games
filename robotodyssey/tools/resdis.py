#!/usr/bin/env python3
"""resdis.py IMAGE START END: linear 6502 listing that knows the game's
inline-parameter calls.

- JSR $4913/$491C/$491E/$4920 (resident module): text follows the JSR,
  ended by its first byte with bit 7 set ('|' = carriage return).
- JSR $4B03 (loader): count, command, then count descriptor pointers.
Uses dev/tools/re6502 for decoding.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'dev', 'tools'))
from re6502.opcodes import decode, text  # noqa: E402

STRINGS = {0x4913, 0x491C, 0x491E, 0x4920}


def listing(m, a, end):
    while a < end:
        d = decode(m, a, cmos=False)
        if d is None:
            print('%04X: .byte $%02X' % (a, m[a]))
            a += 1
            continue
        mn, mode, ln, op = d
        print('%04X: %s' % (a, text(m, a)))
        a += ln
        if mn == 'jsr' and op in STRINGS:
            s = []
            start = a
            while True:
                b = m[a]
                a += 1
                s.append('|' if (b & 0x7F) == 0x0D else chr(b & 0x7F))
                if b >= 0x80:
                    break
            print('%04X:   .text "%s"' % (start, ''.join(s)))
        elif mn == 'jsr' and op == 0x4B03:
            n, cmd = m[a], m[a + 1]
            ptrs = [m[a + 2 + 2 * i] | m[a + 3 + 2 * i] << 8 for i in range(n)]
            print('%04X:   .loader n=%d cmd=$%02X %s' % (a, n, cmd, ' '.join('$%04X' % p for p in ptrs)))
            a += 2 + 2 * n


def main():
    m = open(sys.argv[1], 'rb').read()
    listing(m, int(sys.argv[2], 16), int(sys.argv[3], 16))


if __name__ == '__main__':
    main()
