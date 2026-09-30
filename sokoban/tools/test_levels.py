#!/usr/bin/env python3
"""test_levels.py -- solve levels, play the solutions in the real game.

    test_levels.py [--a2run ../dev/tools/a2run/a2run] [--disk dist/SOKOBAN.dsk]
                   [--max-states N] LEVEL...

LEVEL is a 1-based index in the kept levels of the first collection (the
order of build/lv/report.txt minus the levels left out), e.g. 1 2 3 101.
Each level is solved here (breadth-first search over pushes, so small
levels only), then the game is booted in a2run, taken to the level with N,
and the solution typed as IJKL. The test passes when the game has moved on
to the next level (its cur_lvl in the zero page), i.e. it saw the level as
solved, with the move count of the solution.
"""
import argparse
import collections
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sokoban_levels as sl  # noqa: E402

DIRS = {'u': (-1, 0), 'd': (1, 0), 'l': (0, -1), 'r': (0, 1)}
KEYS = {'u': 'I', 'd': 'K', 'l': 'J', 'r': 'L'}


def solve(grid, max_states):
    h, w = len(grid), len(grid[0])
    walls = {(y, x) for y in range(h) for x in range(w) if grid[y][x] == '#'}
    goals = {(y, x) for y in range(h) for x in range(w) if grid[y][x] in '.*+'}
    boxes = frozenset((y, x) for y in range(h) for x in range(w) if grid[y][x] in '$*')
    player = next((y, x) for y in range(h) for x in range(w) if grid[y][x] in '@+')

    def reach(p, bx):
        seen = {p: ''}
        q = collections.deque([p])
        while q:
            c = q.popleft()
            for d, (dy, dx) in DIRS.items():
                n = (c[0] + dy, c[1] + dx)
                if n not in seen and n not in walls and n not in bx:
                    seen[n] = seen[c] + d
                    q.append(n)
        return seen

    start = (player, boxes)
    prev = {(min(reach(player, boxes)), boxes): None}
    q = collections.deque([(player, boxes, '')])
    while q:
        p, bx, path = q.popleft()
        if bx <= goals:
            return path
        r = reach(p, bx)
        for b in bx:
            for d, (dy, dx) in DIRS.items():
                stand = (b[0] - dy, b[1] - dx)
                to = (b[0] + dy, b[1] + dx)
                if stand not in r or to in walls or to in bx:
                    continue
                nb = frozenset(bx - {b} | {to})
                key = (min(reach(b, nb)), nb)
                if key in prev:
                    continue
                prev[key] = 1
                if len(prev) > max_states:
                    return None
                q.append((b, nb, path + r[stand] + d))
    return None


def zp_address(lst, name):
    """Address of a ZEROPAGE label from the ca65 listing (segment starts $50)."""
    seg, off = None, None
    for line in open(lst, encoding='latin-1'):
        if re.search(r'^\S+\s+\d+\s+\.zeropage', line):
            seg = 'zp'
        elif re.search(r'^\S+\s+\d+\s+\.(segment|bss|code|rodata|data)', line):
            seg = None
        m = re.match(r'^(\w{6})r\s+\d+\s+(?:xx\s+)?(\w+):', line)
        if seg == 'zp' and m and m.group(2) == name:
            off = int(m.group(1), 16)
    if off is None:
        sys.exit('%s not found in %s' % (name, lst))
    return 0x50 + off


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--a2run', default=os.path.join(HERE, '..', '..', 'dev', 'tools', 'a2run', 'a2run'))
    ap.add_argument('--disk', default=os.path.join(HERE, '..', 'dist', 'SOKOBAN.dsk'))
    ap.add_argument('--xsb', default=os.path.join(HERE, '..', 'levels', 'microban.xsb'))
    ap.add_argument('--lst', default=os.path.join(HERE, '..', 'build', 'sokoban.lst'))
    ap.add_argument('--max-states', type=int, default=200000)
    ap.add_argument('levels', nargs='+', type=int)
    a = ap.parse_args()

    kept = []
    for num, title, rows in sl.parse_xsb(a.xsb):
        grid, outside, w, h = sl.analyse(rows)
        if sl.check(grid) is None and sl.place(outside, w, h):
            kept.append((num, grid))
    cur_lvl = zp_address(a.lst, 'cur_lvl')
    moves = zp_address(a.lst, 'moves_lo')

    failed = 0
    for idx in a.levels:
        num, grid = kept[idx - 1]
        sol = solve(grid, a.max_states)
        if sol is None:
            print('level %d (#%d): not solved here (too big for the BFS), skipped' % (idx, num))
            continue
        steps = ['wait:900', 'key: ', 'wait:30']
        n = idx - 1
        while n > 0:                     # N ... N, one pack load at most on the way
            k = min(n, 20)
            steps += ['key:' + 'N' * k, 'wait:200']
            n -= k
        steps += ['peek:%04X:1' % cur_lvl]
        # all but the last move, then the counters, then the winning move
        body = ''.join(KEYS[c] for c in sol.lower())
        steps += ['key:' + body[:-1], 'wait:5', 'peek:%04X:2' % moves, 'key:' + body[-1], 'wait:300',
                  'key: ', 'wait:300', 'peek:%04X:1' % cur_lvl]
        out = subprocess.run([a.a2run, '--disk', a.disk] + steps, capture_output=True, text=True).stdout
        vals = [int(x, 16) for x in re.findall(r'^\w{4}: (\w\w)', out, re.M)]
        mv = re.findall(r'^\w{4}: (\w\w) (\w\w)', out, re.M)
        before, after = vals[0], vals[-1]
        count = int(mv[0][0], 16) + 256 * int(mv[0][1], 16) + 1 if mv else -1
        ok = before == idx - 1 and after == idx and count == len(sol)
        failed += not ok
        print('level %d (#%d): %d moves, %s' % (idx, num, len(sol),
              'ok' if ok else 'FAILED (cur_lvl %d -> %d, moves %d)' % (before, after, count)))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
