#!/usr/bin/env python3
"""The empty hall of fame, file DIRTHOF on the disk (src/hof.inc's hof_img).

    python3 tools/hof.py OUT.bin

"DBH" v1, then per track: best time (min = $FF: none, sec, hun), initials,
best points (BCD, 3 bytes) and their initials; the last initials typed.
The game rewrites its two sectors in place through RWTS, so the file is made
once, at its full size. (`make` rebuilding the disk empties it again.)
"""
import sys
from pathlib import Path

NTRACKS = 30


def empty():
    data = b'DBH\x01'
    data += bytes([0xFF] * NTRACKS) + bytes(NTRACKS) + bytes(NTRACKS)
    data += b'-' * (3 * NTRACKS)
    data += bytes(3 * NTRACKS) + b'-' * (3 * NTRACKS)
    data += b'AAA'
    assert len(data) + 4 <= 512
    return data


def main():
    out = Path(sys.argv[1])
    data = empty()
    if not out.exists() or out.read_bytes() != data:
        out.write_bytes(data)


if __name__ == '__main__':
    main()
