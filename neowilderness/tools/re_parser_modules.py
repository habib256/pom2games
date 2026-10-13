#!/usr/bin/env python3
"""re_parser_modules.py: message ids and chained loads of the verb modules.

Scans each module (Journey side, loaded at $5800) for LDX #n followed within
a few bytes by JSR/JMP $4D21/$4D24/$4D27/$4D2A (print message n), and for
LDX #track / LDY #sector / LDA #count followed by JMP/JSR $03DB/$03DE.
Usage: re_parser_modules.py [JOURNEY.dsk]
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smalldos  # noqa: E402

MODULES = [(0x08, 0x00, 1), (0x0D, 0x0F, 3), (0x0F, 0x00, 7), (0x0F, 0x07, 6), (0x0F, 0x0F, 1),
           (0x10, 0x00, 5), (0x10, 0x05, 7), (0x11, 0x00, 7), (0x11, 0x07, 8), (0x12, 0x00, 8),
           (0x12, 0x08, 6), (0x12, 0x0E, 2), (0x13, 0x0C, 7), (0x14, 0x03, 5), (0x15, 0x0A, 1),
           (0x15, 0x0B, 5), (0x06, 0x00, 2), (0x06, 0x04, 6), (0x09, 0x05, 3), (0x0E, 0x02, 8),
           (0x0E, 0x0A, 6), (0x07, 0x01, 5), (0x14, 0x08, 8)]
MSG = {0x4D21, 0x4D24, 0x4D27, 0x4D2A}


def scan(b):
    msgs, loads = set(), set()
    for i in range(len(b) - 6):
        if b[i] == 0xA2:
            for j in range(i + 2, min(i + 9, len(b) - 2)):
                if b[j] in (0x20, 0x4C) and (b[j + 1] | b[j + 2] << 8) in MSG:
                    msgs.add(b[i + 1])
                    break
        if b[i] in (0x20, 0x4C) and (b[i + 1] | b[i + 2] << 8) in (0x03DB, 0x03DE):
            w = b[max(0, i - 8):i]
            t = s = n = None
            for k in range(len(w) - 1):
                if w[k] == 0xA2: t = w[k + 1]
                if w[k] == 0xA0: s = w[k + 1]
                if w[k] == 0xA9: n = w[k + 1]
            loads.add((t, s, n, 'run' if (b[i + 1] | b[i + 2] << 8) == 0x03DB else 'load'))
    return sorted(msgs), sorted(loads, key=str)


def main():
    dk = smalldos.Disk(open(sys.argv[1] if len(sys.argv) > 1 else 'build/JOURNEY.dsk', 'rb').read())
    dk.flip = True
    for t, s, n in MODULES:
        msgs, loads = scan(dk.run(t, s, n))
        print(f'T{t:02X} S{s:02X} n{n}: msgs {msgs}  loads {loads}')


if __name__ == '__main__':
    main()
