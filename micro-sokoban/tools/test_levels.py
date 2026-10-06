#!/usr/bin/env python3
"""test_levels.py -- play solutions in the real game.

    test_levels.py [--a2run ../dev/tools/a2run/a2run] [--disk ../dist/MICRO-SOKOBAN.dsk]
                   [--coll N] [--xsb FILE] [--solutions FILE] [--max-nodes N]
                   (--all | LEVEL...)

LEVEL is a 1-based index in the kept levels of collection --coll (1 to 4 =
Microban I to IV, default 1; the file of that collection is the default
--xsb), in the order of build/lv/report.txt minus the levels left out, e.g.
1 2 3 101. Collections 2-4 are reached through the level grid (G, N for
each collection, RETURN); --all takes every kept level of the collection.
The solution comes from levels/solutions.txt (tools/make_solutions.py, every
level, checked by replay), or from tools/solver.py when a level is not in
it. The game is booted in a2run, taken to the level with N, and the
solution typed as IJKL. The test passes when the game has moved on
to the next level (its cur_lvl in the zero page), i.e. it saw the level as
solved, with the move count of the solution; after the last level of a
collection, past the BRAVO screen, to level 1 of a collection.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'dev', 'tools'))
import a2test  # noqa: E402
import micro_sokoban_levels as sl  # noqa: E402
import solver  # noqa: E402

DIRS = {'u': (-1, 0), 'd': (1, 0), 'l': (0, -1), 'r': (0, 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--a2run', default=os.path.join(HERE, '..', '..', 'dev', 'tools', 'a2run', 'a2run'))
    ap.add_argument('--disk', default=os.path.join(HERE, '..', '..', 'dist', 'MICRO-SOKOBAN.dsk'))
    ap.add_argument('--coll', type=int, default=1, choices=(1, 2, 3, 4))
    ap.add_argument('--xsb', default=None)
    ap.add_argument('--labels', default=os.path.join(HERE, '..', 'build', 'micro_sokoban.lbl'))
    ap.add_argument('--solutions', default=os.path.join(HERE, '..', 'levels', 'solutions.txt'))
    ap.add_argument('--max-nodes', type=int, default=200000)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('levels', nargs='*', type=int)
    a = ap.parse_args()
    hud = ('I', 'II', 'III', 'IV')[a.coll - 1]
    known = sl.read_solutions(a.solutions)
    if a.xsb is None:
        a.xsb = os.path.join(HERE, '..', 'levels', ('microban.xsb', 'microban2.xsb',
                                                    'microban3.xsb', 'microban4.xsb')[a.coll - 1])

    kept = sl.kept_levels(a.xsb)         # as the game draws them (turned or not)
    labels = a2test.labels(a.labels)

    failed = 0
    for idx in range(1, len(kept) + 1) if a.all else a.levels:
        num, grid = kept[idx - 1]
        sol = known.get((hud, num)) or solver.solve(grid, a.max_nodes, weight=3)
        if sol is None or not solver.check(grid, sol):
            print('level %d (#%d): no solution, FAILED' % (idx, num))
            failed += 1
            continue
        steps = ['wait:1800', 'key:G', 'wait:90']
        if a.coll > 1:
            steps += ['key:N', 'wait:200'] * (a.coll - 1)
        steps += ['key:\r', 'wait:600']
        n = idx - 1
        while n > 0:                     # N ... N, one pack load at most on the way
            k = min(n, 20)
            # A pack load temporarily restores DOS zero page; wait for it
            # before peeking the game's cur_coll / cur_lvl values.
            steps += ['key:' + 'N' * k, 'wait:600']
            n -= k
        steps += [labels.peek('cur_coll', 2)]
        # all but the last move, then the counters, then the winning move
        body = sl.solution_keys(sol)
        last = idx == len(kept)          # then the BRAVO screen, then level 1 of a collection
        steps += ['key:' + body[:-1], 'wait:5', labels.peek('moves_lo', 2), 'key:' + body[-1], 'wait:1000',
                  'key: ', 'wait:600'] + (['key: ', 'wait:400'] if last else []) + [labels.peek('cur_lvl')]
        result = a2test.run(a.disk, steps, emulator=a.a2run, check=False)
        dumps = result.dumps
        if len(dumps) < 3:
            sys.exit('a2run gave no memory dumps:\n' + result.out)
        coll, before = dumps[0][0], dumps[0][1]
        count = int.from_bytes(dumps[1][:2], 'little') + 1
        after = dumps[2][0]
        ok = coll == a.coll - 1 and before == idx - 1 and after == (0 if last else idx) and count == len(sol)
        failed += not ok
        print('level %d (#%d): %d moves, %s' % (idx, num, len(sol),
              'ok' if ok else 'FAILED (cur_lvl %d -> %d, moves %d)' % (before, after, count)))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
