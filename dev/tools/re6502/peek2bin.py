#!/usr/bin/env python3
"""peek2bin.py: turn a2shot 'peek:' hex dumps (stdin) into a flat binary from $0000.

    a2shot ... peek:0000:0xC000 | python3 -I dev/tools/re6502/peek2bin.py > ram.bin

Lines 'AAAA: HH HH ...' fill a 64 KB image; the output stops after the
highest byte dumped. Other lines are ignored.
"""
import sys


def peek2bin(lines):
    """Iterable of a2shot peek lines -> bytes from $0000 up to the last byte seen."""
    mem = bytearray(0x10000)
    top = 0
    for line in lines:
        if len(line) > 5 and line[4] == ':':
            a = int(line[:4], 16)
            for k, h in enumerate(line[5:].split()):
                mem[a + k] = int(h, 16)
            top = max(top, a + len(line[5:].split()))
    return bytes(mem[:top])


if __name__ == '__main__':
    sys.stdout.buffer.write(peek2bin(sys.stdin))
