#!/usr/bin/env python3
"""A simple rider for tools/physics.py: proves a track can be finished.

Lean keeps the bike parallel to the ground under it (in the air: level with
the ground ahead), throttle is full unless the nose rises too much.

    python3 tools/autopilot.py          # rides track 1, prints the result
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import physics as P  # noqa: E402
import track  # noqa: E402

TPS = 30                    # ticks per second of race time


def ground_angle(h, x, ahead=0):
    x = int(x) + ahead
    return math.degrees(math.atan2(h[x + 6] - h[x - 6], 12))


def controls(b, prev_ang):
    ang = b.angle()                     # +: nose down (screen y grows)
    mid = (b.x[0] + b.x[1]) / 512
    air = not (b.ground[0] or b.ground[1])
    target = ground_angle(b.h, mid, 30 if air else 0)
    err = ang - target
    rate = ang - prev_ang
    u = -(err * 0.35 + rate * 2.5)
    lean = max(-P.LEAN_MAX, min(P.LEAN_MAX, int(round(u))))
    throttle = P.THROTTLE_MAX if err > -25 else 2
    return throttle, False, lean


def ride(t, max_ticks=6000, log=False, finish_x=track.FINISH_X):
    b = P.Bike(t)
    prev = b.angle()
    inputs = []
    best, stuck, back = 0, 0, 0
    for n in range(max_ticks):
        thr, brk, lean = controls(b, prev)
        x = b.x[0] >> 8
        if x > best + 2:
            best, stuck = x, 0
        else:
            stuck += 1
        if stuck > 50:                  # stuck: roll back for a run-up
            back, stuck = 40, 0
        if back:
            back -= 1
            thr = 0
        prev = b.angle()
        inputs.append((thr, brk, lean))
        b.tick(thr, brk, lean)
        if log and n % 100 == 0:
            print(f'{n:5} x={b.x[0] / 256:7.1f} ang={b.angle():6.1f} gnd={b.ground}')
        if b.crashed:
            return 'crash', n, b, inputs
        if b.finished(finish_x):
            return 'finish', n, b, inputs
    return 'timeout', max_ticks, b, inputs


if __name__ == '__main__':
    res, n, b, _ = ride(track.track1(), log='-v' in sys.argv)
    print(f'{res} after {n} ticks ({n / TPS:.1f} s) at x={b.x[0] / 256:.0f}')
