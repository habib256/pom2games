#!/usr/bin/env python3
"""hstrings.py FILE BASE [MIN]: list the high-bit ASCII texts of a segment.

Robot Odyssey keeps its messages as bytes with bit 7 set, $8D for a new
line, ended by $00. Prints 'ADDR: text' (lines joined with ' / ').
BASE is the load address in hex (from the BBB_AAAA.bin name if omitted).
"""
import os
import sys


def texts(data, base, minlen=4):
    out, start, buf = [], None, []
    for i, b in enumerate(data):
        if b >= 0xA0 or b == 0x8D:
            if start is None:
                start = i
            buf.append('/' if b == 0x8D else chr(b & 0x7F))
            continue
        if start is not None and len(buf) >= minlen:
            out.append((base + start, ''.join(buf), b == 0))
        start, buf = None, []
    if start is not None and len(buf) >= minlen:
        out.append((base + start, ''.join(buf), False))
    return out


def main():
    path = sys.argv[1]
    if len(sys.argv) > 2:
        base = int(sys.argv[2], 16)
    else:
        base = int(os.path.basename(path).split('_')[1][:4], 16)
    minlen = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    data = open(path, 'rb').read()
    for addr, text, z in texts(data, base, minlen):
        print('%04X%s %s' % (addr, ':' if z else '?', text))


if __name__ == '__main__':
    main()
