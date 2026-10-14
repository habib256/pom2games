#!/usr/bin/env python3
"""Cardinal commands apply signed regional magnetic declination.

Checks angular quantization independently of the implementation. LOOK N/E/S/W
need the compass in use (lot 7, msg 42 otherwise): USE COMPASS first, and
the original's random measurement error, INT of (RND - .5) * 4 degrees
(W9 = 4), widens the tolerance to 2 degrees.
"""
from common import L, DISK, a2test


def main():
    cases = [(declination, name, degrees)
             for declination in (-128, -90, -17, -1, 0, 1, 17, 90, 127)
             for name, degrees in [('N', 0), ('E', 90), ('S', 180), ('W', 270)]]
    idle = L.until('idle', 20000)
    steps = [idle, 'key:USE COMPASS\r', 'wait:1', idle]
    for declination, name, _ in cases:
        steps += [f'poke:7018:{declination & 255:02X}', f'key:LOOK {name}\r',
                  'wait:1', idle, L.peek('heading', 2)]
    result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=1800)
    failures = []
    for i, (declination, name, degrees) in enumerate(cases):
        actual = int.from_bytes(result.mem(L['heading'], 2, i), 'little')*360/560
        expected = (degrees+declination) % 360
        error = abs((actual-expected+180) % 360-180)
        if error > 2 + 360/560/2 + 1e-9:
            failures.append((declination, name, expected, actual))
    for failure in failures:
        print('  declination, cardinal, expected, actual:', failure)
    print(f'{len(cases)} signed declination/cardinal cases: ' + ('FAIL' if failures else 'OK'))
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
