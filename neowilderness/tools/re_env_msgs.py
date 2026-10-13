#!/usr/bin/env python3
"""re_env_msgs.py: dump the Journey-side messages printed by core $4D2A.

Message m (1-based, X register at $4D2A) is 64 bytes at SMALLDOS track
$18 + (m-1) / 64, sector ((m-1) / 4) mod 16, offset ((m-1) mod 4) * 64.
Text is high ASCII; 0 ends it; 1 = string at $0300, 2 = animal name (12-byte
entries from TOPO $60D0, index in $0F), 3.. = a number. Local analysis only.
Usage: re_env_msgs.py [FIRST LAST]
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smalldos  # noqa: E402

dk = smalldos.Disk(open('build/JOURNEY.dsk', 'rb').read())
dk.flip = True
first, last = (int(v, 0) for v in sys.argv[1:3]) if len(sys.argv) > 2 else (1, 255)
for m in range(first, last + 1):
    k = m - 1
    sec = dk.sector(0x18 + k // 64, (k // 4) % 16)
    raw = sec[(k % 4) * 64:(k % 4) * 64 + 64]
    out = ''
    for c in raw:
        if c == 0:
            break
        out += chr(c & 0x7F) if c & 0x80 else {1: '<S>', 2: '<ANIMAL>'}.get(c, f'<N{c}>')
    print(f'{m:3d} ${m:02X} {out}')
