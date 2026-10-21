#!/usr/bin/env python3
"""Find a way through a track: beam search over the physics model.

Every STEP ticks each kept state tries every action (lean x throttle); the
states that crash are dropped, the BEAM furthest ones (one per position and
attitude bin) are kept. The physics is deterministic, so the inputs found
are a proof that the track can be finished, and a reference time.

    python3 tools/solver.py 17            # solve track 17, print the time
    python3 tools/solver.py --all OUT     # solve all, write the solutions
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import physics as P  # noqa: E402
import tracks  # noqa: E402

STEP = 6
BEAM = 24
# full or half throttle, coast, brake: at the faster speeds (2026-10-21) some
# crests need the speed taken off before them
ACTIONS = [(thr, brk, lean) for thr, brk in ((P.THROTTLE_MAX, 0), (P.THROTTLE_MAX // 2, 0), (0, 0), (0, 1))
           for lean in (-4, -2, 0, 2, 4)]
MAX_TICKS = 4000 * P.LAPS
# leaning back costs: per tick, lean back levels x TILT_COST, taken off the
# progress when the beam sorts (without it the rider sat back most of the
# time: the demos looked leaning back; wheelies are fine)
TILT_COST = 256


def clone(b):
    c = P.Bike.__new__(P.Bike)
    c.h, c.lap_len, c.laps = b.h, b.lap_len, b.laps
    c.x, c.y, c.ox, c.oy = b.x[:], b.y[:], b.ox[:], b.oy[:]
    c.ground, c.wheel_ang, c.crashed = b.ground[:], b.wheel_ang[:], b.crashed
    c.tilt = b.tilt
    return c


def solve(h, fin, beam=BEAM):
    """-> list of per-tick (throttle, brake, lean), or None. The fastest
    states first; failing that, a beam that keeps every speed band (the
    slow ride that brakes before a crest)."""
    return _beam(h, fin, beam, None) or _beam(h, fin, 2 * beam, 4)


def _beam(h, fin, beam, per_speed):
    start = P.Bike(h)
    start.tilt = 0
    states = [(start, [])]
    for _ in range(MAX_TICKS // STEP):
        cand = []
        for b, path in states:
            for act in ACTIONS:
                c = clone(b)
                for t in range(STEP):
                    c.tick(*act)
                    c.tilt += -act[2] if act[2] < 0 else 0
                    if c.crashed:
                        break
                    if c.finished(fin):
                        return path + [act] * (t + 1)
                if not c.crashed:
                    cand.append((c, path + [act] * STEP))
        if not cand:
            return None
        cand.sort(key=lambda s: s[0].tilt * TILT_COST - s[0].progress())
        seen, band, states = set(), {}, []
        for c, path in cand:
            v = (c.x[0] - c.ox[0]) >> 7
            key = (c.progress() >> 10, int(c.angle()) // 15, v)
            if key in seen or (per_speed and band.get(v, 0) >= per_speed):
                continue
            seen.add(key)
            band[v] = band.get(v, 0) + 1
            states.append((c, path))
            if len(states) == beam:
                break
    return None


def rle(inputs):
    out = []
    for a in inputs:
        if out and out[-1][1] == a:
            out[-1][0] += 1
        else:
            out.append([1, a])
    return out


def main():
    if sys.argv[1] == '--all':
        lines = []
        for k in range(1, tracks.NTRACKS + 1):
            h, fin = tracks.build(k)
            sol = solve(h, fin)
            if sol is None:
                print(k, tracks.NAMES[k - 1], 'NO SOLUTION', flush=True)
                lines.append(f'{k} none')
                continue
            print(k, tracks.NAMES[k - 1], f'{len(sol)} ticks', flush=True)
            lines.append(f'{k} ' + ' '.join(f'{n}:{a[0]},{a[1]},{a[2]}' for n, a in rle(sol)))
        Path(sys.argv[2]).write_text('\n'.join(lines) + '\n')
        return
    for a in sys.argv[1:]:
        k = int(a)
        h, fin = tracks.build(k)
        sol = solve(h, fin)
        print(k, tracks.NAMES[k - 1], 'NO SOLUTION' if sol is None else f'{len(sol)} ticks')


if __name__ == '__main__':
    main()
