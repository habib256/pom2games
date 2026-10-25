#!/usr/bin/env python3
"""DIRTBIKE track compiler (and track1, the physics test's reference track).

A track is TRACK_LEN ground heights: height x = the screen row of the ground
surface at world pixel x (rows grow downwards, 0 = top); the game fills
everything below. Heights stay in [MIN_ROW, MAX_ROW] (no vertical scroll).

compile_patterns() gives the game's view: for every world pixel x, the
"window" of the 7 pixels x..x+6, which is what one HGR byte column shows
when the camera puts x at a byte boundary. A window is a pattern of partial
bytes (row mn + r holds the pixels whose height <= mn + r, bit 0 = left);
the game keeps per pixel the height and the pattern id, and per pattern its
row count k, rel0 (the row of pixel x inside it, so mn = h[x] - rel0) and
its bytes in a shared pool. tools/tracks.py builds the 30 tracks,
tools/packtrack.py writes them for the disk.

    python3 tools/track.py              # track 1's pattern count
"""
import math
import sys

TRACK_LEN = 4096
MIN_ROW = 64
MAX_ROW = 184
BASE = 160
START_X = 48            # rear wheel at the start
FINISH_X = 3800         # the race ends when the rear wheel passes it


def _smooth(h, radius):
    out = []
    n = len(h)
    for x in range(n):
        lo, hi = max(0, x - radius), min(n, x + radius + 1)
        out.append(math.fsum(h[lo:hi]) / (hi - lo))
    return out


def track1():
    h = []

    def flat(n, y):
        h.extend([y] * n)

    def ramp(n, y1):
        y0 = h[-1]
        h.extend(y0 + (y1 - y0) * (i + 1) / n for i in range(n))

    def waves(n, amp, period):
        y0 = h[-1]
        h.extend(y0 - amp * (1 - math.cos(2 * math.pi * i / period)) / 2 for i in range(n))

    flat(260, BASE)                 # start straight
    waves(400, 5, 40)               # small bumps
    ramp(140, 126)                  # kicker...
    flat(30, 126)
    ramp(24, 168)                   # ...and its drop: first jump
    flat(120, 168)
    waves(480, 26, 160)             # rolling hills
    ramp(60, BASE)
    waves(288, 4, 32)               # whoops
    flat(80, BASE)
    ramp(220, 92)                   # big hill
    flat(40, 92)
    ramp(200, 172)
    flat(100, 172)
    ramp(110, 134)                  # table top: take-off,
    flat(90, 134)                   # the table,
    ramp(150, 172)                  # landing slope
    waves(320, 14, 80)              # last hills
    ramp(80, BASE)
    flat(TRACK_LEN - len(h), BASE)  # finish straight and run-off
    h = h[:TRACK_LEN]
    h = _smooth(h, 2)
    out = [min(MAX_ROW, max(MIN_ROW, int(round(y)))) for y in h]
    assert len(out) == TRACK_LEN
    return out


def compile_patterns(h):
    """The game's format: per pixel x, the pattern of the window x..x+6
    (its partial bytes; rows from the window's minimum). The height stays
    stored per pixel, so mn = h[x] - rel0, rel0 = the first partial row that
    holds pixel 0 (k if none). -> (ids, patterns, pool, pool offsets) with
    patterns = [(k, rel0, partial bytes)]."""
    ext = h + [h[-1]] * 16
    table, pats, ids = {}, [], []
    for x in range(TRACK_LEN):
        w = ext[x:x + 7]
        m = min(w)
        part = tuple(sum(1 << i for i in range(7) if w[i] <= m + r) for r in range(max(w) - m))
        if part not in table:
            table[part] = len(pats)
            pats.append((len(part), w[0] - m, part))
        ids.append(table[part])
    assert len(pats) <= 256, len(pats)
    pool, offs = pack_pool([(0, 0, 0, p[2]) for p in pats])
    for x in range(TRACK_LEN):              # the game's view of the windows
        k, rel0, part = pats[ids[x]]
        assert h[x] - rel0 == min(ext[x:x + 7])
        assert bytes(part) == pool[offs[ids[x]]:offs[ids[x]] + k]
    return ids, pats, pool, offs


def pack_pool(entries):
    """All partial byte strings in one pool, overlapping where one string's
    end is another's start (greedy shortest superstring).
    -> (pool bytes, offset of each entry)."""
    strings = sorted({e[3] for e in entries if e[3]}, key=len, reverse=True)
    kept = []
    for st in strings:                  # drop strings inside longer ones
        if not any(_find(k, st) >= 0 for k in kept):
            kept.append(st)
    while len(kept) > 1:
        best = (0, 0, 1)
        for i, a in enumerate(kept):
            for j, b in enumerate(kept):
                if i != j:
                    for n in range(min(len(a), len(b)) - 1, best[0], -1):
                        if a[-n:] == b[:n]:
                            best = (n, i, j)
                            break
        n, i, j = best
        if n == 0:
            break
        merged = kept[i] + kept[j][n:]
        kept = [k for m, k in enumerate(kept) if m not in (i, j)] + [merged]
    pool = tuple(v for k in kept for v in k)
    offs = [(_find(pool, e[3]) if e[3] else 0) for e in entries]
    return bytes(pool), offs


def _find(hay, needle):
    n = len(needle)
    for i in range(len(hay) - n + 1):
        if hay[i:i + n] == needle:
            return i
    return -1


def main():
    ids, pats, pool, offs = compile_patterns(track1())
    print(f'track 1: {len(pats)} patterns, pool {len(pool)} bytes')


if __name__ == '__main__':
    main()
