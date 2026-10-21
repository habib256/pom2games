#!/usr/bin/env python3
"""The 30 DIRTBIKE tracks, from very easy to very hard.

Every track is TRACK_LEN ground heights (tools/track.py compiles them). It is
built from a vocabulary of elements -- bumps, hills, kickers, gaps, table
tops, steps, drops, whoops, stairs -- whose size grows with the difficulty
d = 0 (track 1) .. 1 (track 30). Tracks 1-3 are written by hand; the others
draw their elements from a seeded generator, so a track never changes once
its seed is chosen. SEEDS holds seeds that pass tools/trackcheck.py: the
track compiles within the game's limits and tools/solver.py finishes it.

    python3 tools/tracks.py            # list: finish line, patterns, pool
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from track import TRACK_LEN, MIN_ROW, MAX_ROW, BASE, START_X  # noqa: E402

NTRACKS = 30
START_FLAT = 400                # flat at the start: room to get going
PRE_FINISH = 300                # flat straight before the finish line
PAD = 336                       # the loop's first pixels again after its end:
                                # the screen and the bike see past the line
                                # until the bike moves back a lap (physics.py)


class Track(list):
    """Ground rows of a looping track: lap_len pixels, then PAD repeated."""
    lap_len = 0

NAMES = [                       # at most 14 characters (hall of fame line)
    'EASY RIDE', 'LITTLE BUMPS', 'FIRST JUMP', 'HILLS', 'THE KICKER',
    'WAVES', 'TABLETOP', 'MOUNTAINS', 'DOUBLE JUMP', 'THE STEPS',
    'THE VALLEY', 'WHOOPS', 'ROLLERCOASTER', 'THE CHASM', 'STAIRCASE',
    'DUNES', 'THE CLIFF', 'RODEO', 'TRIPLE JUMP', 'CANYON',
    'WASHBOARD', 'THE WALL', 'IN A ROW', 'TRAPS', 'EVEREST',
    'CHAOS', 'THE VOID', 'INFERNO', 'NIGHTMARE', 'THE ULTIMATE',
]
assert max(map(len, NAMES)) <= 14

# generator seed per track (tracks 4..30): each one has a solution found by
# tools/solver.py (stored in tests/solutions.txt, replayed by make test)
SEEDS = {k: k for k in range(4, NTRACKS + 1)}
SEEDS.update({24: 100, 27: 101, 28: 100, 29: 100, 30: 101})
# re-seeded for the faster bike (2026-10-21: x1.5 then x2 speed, VMAX_X / VMAX_Y)
SEEDS.update({9: 103, 18: 104, 19: 102, 21: 103, 24: 105, 27: 104, 29: 108})
SEEDS.update({23: 110})          # and for the x2 speed
SEEDS.update({26: 120, 29: 120})  # and for the flat start / finish straight
SEEDS.update({11: 130, 19: 132, 20: 130, 27: 130})  # and for 3-lap circuits
SEEDS.update({11: 200, 13: 201, 16: 200, 17: 200, 20: 203, 22: 203, 23: 202,  # and for
              24: 200, 26: 204, 29: 200, 30: 201})                           # x1.5 speed
SEEDS.update({8: 300, 10: 301, 16: 303, 17: 302, 18: 300, 20: 300, 24: 302,  # and for
              29: 304})                                                      # the engine brake


class Builder:
    def __init__(self):
        self.h = []

    @property
    def y(self):
        return self.h[-1]

    def flat(self, n, y=None):
        self.h.extend([self.y if y is None else y] * n)

    def ramp(self, n, y1):
        y0 = self.y
        self.h.extend(y0 + (y1 - y0) * (i + 1) / n for i in range(n))

    def curve(self, n, y1):
        """S-shaped ramp (cosine), gentler at both ends."""
        y0 = self.y
        self.h.extend(y0 + (y1 - y0) * (1 - math.cos(math.pi * (i + 1) / n)) / 2 for i in range(n))

    def waves(self, n, amp, period):
        y0 = self.y
        self.h.extend(y0 - amp * (1 - math.cos(2 * math.pi * i / period)) / 2 for i in range(n))

    def hill(self, width, height):
        y0 = self.y
        self.curve(width // 2, y0 - height)
        self.curve(width - width // 2, y0)

    def kicker(self, up, height, drop):
        """Ramp up, then a steep drop back down: a jump."""
        y0 = self.y
        self.ramp(up, y0 - height)
        self.flat(6)
        self.ramp(drop, y0)

    def gap(self, up, height, width, land):
        """Take-off ramp, a hollow, a landing slope going down. The hollow's
        far side climbs at 1:2, so a jump too short costs time, not the race."""
        y0 = self.y
        self.ramp(up, y0 - height)
        self.ramp(8, min(MAX_ROW, y0 + 14))
        self.flat(width)
        top = y0 - height * 2 // 3
        self.ramp(max(16, int(2 * (self.y - top))), top)
        self.ramp(land, y0)

    def table(self, up, height, top, down):
        y0 = self.y
        self.ramp(up, y0 - height)
        self.flat(top)
        self.ramp(down, y0)

    def step(self, rise, n):
        """A short steep wall: up (rise > 0) or a drop (rise < 0)."""
        self.ramp(n, self.y - rise)

    def stairs(self, count, rise, tread, n):
        for _ in range(count):
            self.step(rise, n)
            self.flat(tread)

    def clamp_level(self, lo=100, hi=172):
        """Keep the running level inside the screen band between elements."""
        if self.y < lo:
            self.curve(80, lo + 10)
        elif self.y > hi:
            self.curve(80, hi - 10)


def finish(b):
    """Close the loop: back to the start level, the finish straight, a lap of
    a multiple of 7 pixels (the camera moves back whole HGR bytes), circular
    smoothing, rows; then PAD again and flat ground. -> (Track, lap_len);
    the finish line is at lap_len (in the last lap), the start straight is
    the run-off."""
    b.curve(60, BASE)
    b.flat(PRE_FINISH)
    while len(b.h) % 7:
        b.flat(1)
    lap = len(b.h)
    assert lap + PAD <= TRACK_LEN, (lap, 'track too long')
    h = b.h
    loop = []
    for x in range(lap):
        y = sum(h[(x + d) % lap] for d in range(-2, 3)) / 5
        loop.append(min(MAX_ROW, max(MIN_ROW, int(round(y)))))
    t = Track(loop + loop[:PAD] + [BASE] * (TRACK_LEN - lap - PAD))
    t.lap_len = lap
    return t, lap


def hand(k):
    b = Builder()
    b.flat(START_FLAT, BASE)
    if k == 1:          # flat ground, a few soft hills
        b.flat(200)
        b.hill(240, 12)
        b.flat(160)
        b.hill(300, 18)
        b.flat(200)
        b.hill(200, 10)
        b.flat(180)
        b.hill(280, 16)
        b.flat(200)
        b.hill(240, 14)
        b.flat(160)
    elif k == 2:        # small bumps
        b.waves(320, 3, 48)
        b.flat(120)
        b.waves(320, 4, 40)
        b.flat(120)
        b.hill(260, 20)
        b.waves(320, 4, 44)
        b.flat(120)
        b.waves(300, 5, 40)
        b.flat(100)
    elif k == 3:        # one gentle kicker
        b.waves(240, 3, 48)
        b.flat(160)
        b.kicker(160, 16, 60)
        b.flat(200)
        b.hill(260, 22)
        b.flat(120)
        b.kicker(160, 18, 70)
        b.flat(160)
        b.hill(240, 18)
        b.flat(140)
        b.kicker(170, 20, 70)
        b.flat(120)
    return finish(b)


ELEMENTS = ['bumps', 'hill', 'kicker', 'whoops', 'table', 'gap', 'step', 'drop', 'stairs', 'valley']


def generated(k, seed):
    d = (k - 1) / (NTRACKS - 1)
    rnd = random.Random(seed * 7919 + k)
    b = Builder()
    b.flat(START_FLAT, BASE)
    length = int(2400 + 1300 * d)
    # which elements may appear, growing with d
    pool = ['bumps', 'hill', 'kicker']
    if d > 0.10:
        pool += ['whoops', 'table']
    if d > 0.25:
        pool += ['gap', 'step', 'valley']
    if d > 0.40:
        pool += ['drop', 'stairs']
    cap = TRACK_LEN - PAD - PRE_FINISH - 80 - 7   # room for the finish curve
    while len(b.h) < length:
        before = len(b.h)
        e = rnd.choice(pool)
        s = 0.35 + 0.65 * d * rnd.uniform(0.8, 1.2)     # severity
        if e == 'bumps':
            b.waves(rnd.randrange(160, 320), 2 + 6 * s, rnd.choice([32, 40, 48]))
        elif e == 'hill':
            b.hill(rnd.randrange(160, 300), int(14 + 44 * s))
        elif e == 'kicker':
            b.kicker(rnd.randrange(90, 150), int(12 + 30 * s), max(14, int(80 - 60 * s)))
        elif e == 'whoops':
            b.waves(rnd.randrange(160, 300), 3 + 3 * s, max(36, int(48 - 12 * s)))
        elif e == 'table':
            b.table(rnd.randrange(90, 130), int(14 + 26 * s), rnd.randrange(50, 110),
                    max(30, int(130 - 80 * s)))
        elif e == 'gap':
            b.gap(rnd.randrange(100, 140), int(16 + 20 * s), int(16 + 60 * s), rnd.randrange(80, 140))
        elif e == 'step':
            rise = int(6 + 14 * s)
            b.step(rise, max(int(rise / 1.2), int(30 - 14 * s)))
            b.flat(rnd.randrange(40, 100))
        elif e == 'drop':
            b.step(-int(10 + 34 * s), max(6, int(24 - 16 * s)))
            b.flat(rnd.randrange(40, 100))
        elif e == 'stairs':
            rise = int(5 + 8 * s)
            b.stairs(rnd.randrange(3, 6), rise, rnd.randrange(30, 60), max(int(rise / 1.2), int(20 - 8 * s)))
        elif e == 'valley':
            b.hill(rnd.randrange(160, 280), -int(14 + 30 * s))
        b.flat(rnd.randrange(max(16, int(100 - 80 * d)), max(40, int(180 - 120 * d))))
        b.clamp_level()
        if len(b.h) > cap:              # the last element did not fit
            del b.h[before:]
            break
    return finish(b)


def build(k):
    """Track k (1..30) -> (heights, finish_x)."""
    if k <= 3:
        return hand(k)
    return generated(k, SEEDS[k])


if __name__ == '__main__':
    import track
    for k in range(1, NTRACKS + 1):
        h, fin = build(k)
        ids, pats, pool, offs = track.compile_patterns(h)
        print(f'{k:2} {NAMES[k - 1]:15} finish {fin:4}  patterns {len(pats):3}  pool {len(pool):4}')
