#!/usr/bin/env python3
"""CUTROPE -- the level solver (tools/cutrope.py --solve).

    python3 tools/cutrope.py --solve [LEVEL...] [--depth N] [--step S]
            [--until T] [--horizon H]

For each level (1-based; all by default): every schedule of up to N actions
(depth, default: the stored solution's length), each at a tick multiple of S
(default 1) up to T, played on the model up to H ticks. The actions are the
keys: cut a rope still on, pop the bubble while it holds the candy, puff a
cushion that is ready while the candy is ahead of it (a puff out of reach
changes nothing but the cushion's wait: not tried). It prints how many
schedules win, with how many stars, the 3-star ones in windows, and checks
the stored solution (3 stars) with the width of each of its actions' window
(the other actions kept).

As a module: search(), windows(), check().
"""
from collections import defaultdict
import sys

import cutrope as C

NAMES = ['1', '2', '3', '4', '5', '6']


def key_name(mask):
    return '+'.join(NAMES[b] for b in range(6) if mask >> b & 1)


def actions(g):
    """The useful single actions now (masks)."""
    out = [1 << r for r in range(g.lv.nropes) if g.on >> r & 1]
    if g.bub == C.BUB_CAUGHT:
        out.append(C.M_POP)
    xl, yh = g.candy_px()
    for c, (ax, ay, d) in enumerate(g.lv.cushions):
        if not g.cool[c]:
            along, across = [(xl - ax, yh - ay), (yh - ay, xl - ax), (ax - xl, yh - ay), (ay - yh, xl - ax)][d]
            if 0 <= along < C.PUFF_LEN and abs(across) <= C.PUFF_W + (along >> 2):
                out.append(C.M_CUSH << c)
    return out


def search(level, depth, step=1, until=150, horizon=300, data=None):
    """Every schedule of <= depth actions: -> ({schedule: (state, stars)} of
    the winning ones, schedules played)."""
    wins, count = {}, [0]

    def dfs(g, t, sched, d):
        while t < horizon and g.state == C.PLAY:
            if d and t <= until and t % step == 0:
                for a in actions(g):
                    h = g.clone()
                    h.tick(a)
                    dfs(h, t + 1, sched + ((t, a),), d - 1)
            g.tick()
            t += 1
        count[0] += 1
        if g.state == C.WON:
            wins[sched] = g.nstar

    dfs(C.Game(level, data), 0, (), depth)
    return wins, count[0]


def runs(ticks, step=1):
    """[1, 2, 3, 5, 6] -> '1-3, 5-6' (ticks step apart: one run)."""
    out, ticks = [], sorted(ticks)
    for t in ticks:
        if out and t <= out[-1][1] + step:
            out[-1][1] = t
        else:
            out.append([t, t])
    return ', '.join(f'{a}' if a == b else f'{a}-{b}' for a, b in out)


def windows(wins, stars=3):
    """The schedules with that many stars, grouped by their keys and all
    ticks but the last: {(keys, earlier ticks): last ticks}."""
    by = defaultdict(list)
    for sched, n in wins.items():
        if n == stars:
            keys = tuple(key_name(m) for _, m in sched)
            by[(keys, tuple(t for t, _ in sched[:-1]))].append(sched[-1][0])
    return by


def play_sched(level, sched, horizon=400, data=None):
    g, sched = C.Game(level, data), dict(sched)
    for t in range(horizon):
        g.tick(sched.get(t, 0))
        if g.state != C.PLAY:
            return g, t + 1
    return g, horizon


def tolerance(level, sol, data=None):
    """Per action of the solution: the ticks it can move to (the others
    kept) with the result still 3 stars."""
    out = []
    for k, (t0, m) in enumerate(sol):
        ok = []
        for t in range(max(0, t0 - 40), t0 + 41):
            s = list(sol)
            s[k] = (t, m)
            if len({tt for tt, _ in s}) < len(s):
                continue
            g, _ = play_sched(level, s, data=data)
            if g.state == C.WON and g.nstar == 3:
                ok.append(t)
        # the run that holds t0
        lo = hi = t0
        while lo - 1 in ok:
            lo -= 1
        while hi + 1 in ok:
            hi += 1
        out.append((key_name(m), lo, hi))
    return out


def check(level, data=None):
    """The stored solution: (won with 3 stars, ticks, tolerance)."""
    sol = C.SOLUTIONS[level]
    g, t = play_sched(level, sol, data=data)
    return g.state == C.WON and g.nstar == 3, t, tolerance(level, sol, data)


def trivial(level, data=None):
    """The schedules a beginner tries first: nothing, every rope cut at once
    at tick 0 (-> state, stars)."""
    out = {}
    g, _ = play_sched(level, [], data=data)
    out['nothing'] = (g.state, g.nstar)
    lv = C.Level(data or C.LEVEL_BYTES[level])
    g, _ = play_sched(level, [(0, (1 << lv.nropes) - 1)], data=data)
    out['all cut at 0'] = (g.state, g.nstar)
    return out


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    opt = {}
    for k, a in enumerate(argv):
        if a.startswith('--') and a != '--solve':
            opt[a[2:]] = int(argv[k + 1])
            args.remove(argv[k + 1])
    levels = [int(a) - 1 for a in args] or range(C.NLEVEL)
    for lv in levels:
        name = C.LEVELS[lv]['name']
        depth = opt.get('depth', len(C.SOLUTIONS[lv]))
        ok, t, tol = check(lv)
        print(f'level {lv + 1} {name}: solution {C.SOLUTIONS[lv]} -> '
              f'{"3 stars" if ok else "NOT 3 STARS"} at tick {t}; windows '
              + ', '.join(f'key {k} {a}-{b}' for k, a, b in tol))
        wins, n = search(lv, depth, opt.get('step', 1), opt.get('until', 150), opt.get('horizon', 300))
        hist = defaultdict(int)
        for s in wins.values():
            hist[s] += 1
        print(f'  {n:,} schedules of <= {depth} actions: won {len(wins):,} '
              f'({", ".join(f"{k} stars {v:,}" for k, v in sorted(hist.items()))})')
        for (keys, early), last in sorted(windows(wins).items(), key=lambda kv: -len(kv[1]))[:12]:
            pre = ', '.join(f'{k}@{t}' for k, t in zip(keys, early))
            print(f'    {pre + ", " if pre else ""}{keys[-1]} at {runs(last, opt.get("step", 1))}')
        print('  ' + ', '.join(f'{k}: {["playing", "won", "lost"][s]} {n} stars' for k, (s, n) in trivial(lv).items()))


if __name__ == '__main__':
    main(sys.argv[1:])
