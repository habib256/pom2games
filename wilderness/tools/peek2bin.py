#!/usr/bin/env python3
"""peek2bin.py: turn a2shot 'peek:' hex dumps (stdin) into a flat binary from $0000."""
import sys

mem = bytearray(0x10000)
top = 0
for line in sys.stdin:
    if len(line) > 5 and line[4] == ':':
        a = int(line[:4], 16)
        for k, h in enumerate(line[5:].split()):
            mem[a + k] = int(h, 16)
        top = max(top, a + len(line[5:].split()))
sys.stdout.buffer.write(mem[:top])
