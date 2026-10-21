#!/usr/bin/env python3
"""DIRTBIKE trick points, reference model of src/tricks.inc (bit for bit).

Called once per race tick after the physics (Bike.tick):
  * the wheel axis (front - rear, low 16 bits of x as the 6502 has them)
    falls in one of 8 sectors of 45 degrees; while both wheels are off the
    ground, each step to the next / previous sector adds +1 / -1 to `rot`
    (8 steps = one full turn: no angle, no arctangent);
  * on landing: AIR_PTS per tick in the air if the jump lasted AIR_MIN
    ticks or more, plus FLIP_PTS x flips^2 (a double flip 4x, a triple 9x:
    the risk pays), flips = (|rot| + 2) >> 3 (a
    turn landed 90 degrees short still counts: the bike must land on its
    wheels anyway, or crash). The points wait in `pend` (at most 9999);
  * they are banked into `score` (at most 999999) after SAFE ticks on the
    ground (hops shorter than AIR_MIN do not restart that wait), or at the
    finish; a crash loses them;
  * a wheelie (rear wheel down, front wheel up) of WH_MIN ticks or more
    pays WH_PTS a tick when it ends, into `pend` like a jump.
The 6502 keeps pend and score in BCD; the values are the same.
"""

AIR_MIN = 12                # ticks in the air before a jump scores
AIR_PTS = 10                # per tick in the air
FLIP_PTS = 1000             # per full turn
WH_MIN = 15                 # ticks on the rear wheel before a wheelie scores
WH_PTS = 10                 # per tick of wheelie
SAFE = 20                   # ticks on the wheels that bank the points
PEND_MAX = 9999
SCORE_MAX = 999999


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def octant(dx, dy):
    """Sector 0..7 of (dx, dy), y down: 0 = level, nose to the right. Ties
    as the 6502 decides them (one comparison, |dx| >= |dy|)."""
    ax, ay = abs(dx), abs(dy)
    if dx >= 0 and dy >= 0:
        return 0 if ax >= ay else 1
    if dx < 0 and dy >= 0:
        return 2 if ay > ax else 3
    if dx < 0:
        return 4 if ax >= ay else 5
    return 6 if ay > ax else 7


STEP = {0: 0, 1: 1, 2: 2, 3: 0, 4: 0, 5: 0, 6: -2, 7: -1}


class Tricks:
    def __init__(self):
        self.score = 0
        self.pend = 0
        self.flips = 0              # flips in pend (for the message)
        self.air = 0
        self.rot = 0
        self.sector = 0             # the bike starts level
        self.safe = 0
        self.wh = 0                 # ticks of the wheelie going on
        self.jump = 0               # a jump scored in pend (for the message)
        self.banked = []            # (flips, points) per bank, for tests

    def tick(self, b):
        if b.crashed:
            self.pend = self.flips = self.air = self.rot = self.wh = self.jump = 0
            return
        sec = octant(s16(b.x[1] - b.x[0]), s16(b.y[1] - b.y[0]))
        d = STEP[(sec - self.sector) & 7]
        self.sector = sec
        if b.ground[0] and not b.ground[1]:
            self.wh = min(255, self.wh + 1)
        else:
            if self.wh >= WH_MIN:
                self.pend = min(PEND_MAX, self.pend + self.wh * WH_PTS)
            self.wh = 0
        if not (b.ground[0] or b.ground[1]):
            self.rot = max(-128, min(127, self.rot + d))
            self.air = min(255, self.air + 1)
            if self.air >= AIR_MIN:                     # a real jump: wait again
                self.safe = 0
            return
        if self.air:                                    # landing
            flips = (abs(self.rot) + 2) >> 3
            if self.air >= AIR_MIN:
                self.jump = 1
            pts = (self.air * AIR_PTS if self.air >= AIR_MIN else 0) + flips * flips * FLIP_PTS
            self.pend = min(PEND_MAX, self.pend + pts)
            self.flips = min(255, self.flips + flips)
            self.air = self.rot = 0
        self.safe = min(255, self.safe + 1)
        if self.pend and self.safe >= SAFE:
            self.bank()

    def bank(self):
        if self.pend:
            self.banked.append((self.flips, self.pend))
            self.score = min(SCORE_MAX, self.score + self.pend)
        self.pend = self.flips = self.jump = 0


def ride(h, inputs, finish_x):
    """Replay inputs; -> (Bike, Tricks) at the finish (points banked)."""
    import physics as P
    b, t = P.Bike(h), Tricks()
    for thr, brk, lean in inputs:
        b.tick(thr, bool(brk), lean)
        t.tick(b)
        if b.finished(finish_x):
            t.bank()
            break
    return b, t


if __name__ == '__main__':
    import tracks
    import trackcheck
    sols = trackcheck.solutions()
    for k in range(1, tracks.NTRACKS + 1):
        h, fin = tracks.build(k)
        b, t = ride(h, sols[k], fin)
        print(f'{k:2} {tracks.NAMES[k - 1]:15} score {t.score:6}  {t.banked}')
