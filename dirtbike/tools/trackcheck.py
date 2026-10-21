#!/usr/bin/env python3
"""Check the 30 tracks: each compiles within the game's limits, and the
stored solution (tests/solutions.txt, from tools/solver.py) reaches the
finish line without a crash in the physics model.

    python3 tools/trackcheck.py          # every track
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import physics as P  # noqa: E402
import track  # noqa: E402
import tracks  # noqa: E402

TPS = 30


def solutions(path=HERE.parent / 'tests/solutions.txt'):
    """{track: [(throttle, brake, lean)] per tick}"""
    out = {}
    for line in path.read_text().split('\n'):
        if not line.strip():
            continue
        k, *runs = line.split()
        ticks = []
        for r in runs:
            n, a = r.split(':')
            ticks += [tuple(int(v) for v in a.split(','))] * int(n)
        out[int(k)] = ticks
    return out


def replay(h, fin, inputs):
    b = P.Bike(h)
    for n, (thr, brk, lean) in enumerate(inputs):
        b.tick(thr, bool(brk), lean)
        if b.crashed:
            return 'crash', n
        if b.finished(fin):
            return 'finish', n + 1
    return 'short', len(inputs)


def main():
    sols = solutions()
    bad = 0
    for k in range(1, tracks.NTRACKS + 1):
        h, fin = tracks.build(k)
        ids, pats, pool, offs = track.compile_patterns(h)
        res, n = replay(h, fin, sols.get(k, []))
        bad += res != 'finish'
        print(f'{k:2} {tracks.NAMES[k - 1]:15} {res:6} {n / TPS:5.1f} s  finish {fin:4}  '
              f'patterns {len(pats):3}  pool {len(pool):4}')
    if bad:
        sys.exit(f'{bad} track(s) without a working solution')


if __name__ == '__main__':
    main()
