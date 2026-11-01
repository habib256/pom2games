#!/usr/bin/env python3
"""The empty hall of fame, file DIRTHOF on the disk (src/hof.inc's hof_img).

    python3 tools/hof.py OUT.bin

"DBH" v1, then per track: best time (min = $FF: none, sec, hun), initials,
best points (BCD, 3 bytes) and their initials; the last initials typed;
the input device chosen (0: the joystick when one is found, 1: the keyboard).
The game rewrites its two sectors in place through RWTS, so the file is made
once, at its full size. (`make` rebuilding the disk empties it again.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
from fonts import write_if_changed  # noqa: E402

NTRACKS = 30


def empty():
    data = b'DBH\x01'
    data += bytes([0xFF] * NTRACKS) + bytes(NTRACKS) + bytes(NTRACKS)
    data += b'-' * (3 * NTRACKS)
    data += bytes(3 * NTRACKS) + b'-' * (3 * NTRACKS)
    data += b'AAA'
    data += b'\x00'
    assert len(data) + 4 <= 512
    return data


def main():
    out = Path(sys.argv[1])
    data = empty()
    write_if_changed(out, data)


if __name__ == '__main__':
    main()
