#!/usr/bin/env python3
"""solver.py -- a Sokoban solver for the tests, plus the dead-square rule.

    solver.py [--max-nodes N] [--weight W] FILE.xsb [LEVEL...]

A* over pushes: a state is the box set plus the area the player can reach
(named by its smallest cell), the cost is the number of pushes, the estimate
an optimal assignment of boxes to targets (each box to its own target,
counted in pushes). Two deadlock rules prune the search:

  - dead squares: a box on a cell from which no push sequence can bring it
    to a target can never be saved. The live cells are found by pulling a
    box backwards from every target (the box at c goes to c+d when the
    player has room at c+d and c+2d); every other floor cell is dead.
    dead_squares() gives them; the game computes the same table at level
    start (sokoban.s, find_dead) and warns when a box is pushed onto one.
  - freeze: a box blocked on both axes (by a wall, by dead squares on both
    sides, or by a box blocked the same way) never moves again; if one box
    of such a group is off target, the level is lost.

The answer is not optimal (moves are not minimised), only valid: a string of
u / d / l / r player steps, pushes included. check() replays it.
"""
import argparse
import heapq
import os
import sys

DIRS = {'u': (-1, 0), 'd': (1, 0), 'l': (0, -1), 'r': (0, 1)}
OPP = {'u': 'd', 'd': 'u', 'l': 'r', 'r': 'l'}
BIG = 10 ** 6


def parse(grid):
    """walls, targets, boxes, player of a padded grid (sokoban_levels.analyse)."""
    h, w = len(grid), len(grid[0])
    cells = [(y, x) for y in range(h) for x in range(w)]
    walls = {c for c in cells if grid[c[0]][c[1]] == '#'}
    goals = {c for c in cells if grid[c[0]][c[1]] in '.*+'}
    boxes = frozenset(c for c in cells if grid[c[0]][c[1]] in '$*')
    player = next(c for c in cells if grid[c[0]][c[1]] in '@+')
    return walls, goals, boxes, player


def inside(grid, walls, player):
    """The cells the player could ever stand on (floor reachable without boxes)."""
    h, w = len(grid), len(grid[0])
    seen, stack = {player}, [player]
    while stack:
        y, x = stack.pop()
        for dy, dx in DIRS.values():
            n = (y + dy, x + dx)
            if 0 <= n[0] < h and 0 <= n[1] < w and n not in walls and n not in seen:
                seen.add(n)
                stack.append(n)
    return seen


def assignment(cost):
    """Smallest total of cost[i][j] taking a distinct column j for each row i
    (Hungarian method, rows <= columns)."""
    n, m = len(cost), len(cost[0])
    inf = float('inf')
    u, v, p, way = [0] * (n + 1), [0] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = [inf] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], inf, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    return -v[0]


class Level:
    """The fixed part of a level, floor cells numbered for speed."""

    def __init__(self, grid):
        walls, goals, boxes, player = parse(grid)
        floor = sorted(inside(grid, walls, player))
        self.cells = floor
        index = {c: i for i, c in enumerate(floor)}
        n = len(floor)
        self.nb = {d: [index.get((c[0] + dy, c[1] + dx), -1) for c in floor]
                   for d, (dy, dx) in DIRS.items()}          # -1 = wall
        self.goals = frozenset(index[g] for g in goals)
        self.boxes = frozenset(index[b] for b in boxes)
        self.player = index[player]
        self.dist = []                       # pushes from each cell, per target
        for g in sorted(self.goals):
            d = [None] * n
            d[g], queue = 0, [g]
            for c in queue:                  # pull: box c -> to, player beyond
                for k in DIRS:
                    to = self.nb[k][c]
                    if to >= 0 and d[to] is None and self.nb[k][to] >= 0:
                        d[to] = d[c] + 1
                        queue.append(to)
            self.dist.append(d)
        self.live = [any(d[c] is not None for d in self.dist) for c in range(n)]

    def estimate(self, boxes):
        return assignment([[BIG if d[b] is None else d[b] for d in self.dist] for b in boxes])

    def reach(self, p, boxes):
        seen, stack, nb = {p}, [p], self.nb
        while stack:
            c = stack.pop()
            for k in 'udlr':
                n = nb[k][c]
                if n >= 0 and n not in boxes and n not in seen:
                    seen.add(n)
                    stack.append(n)
        return seen

    def frozen(self, b, boxes):
        """True if the box just pushed to b is part of a group of boxes that
        can never move again with one of them off target."""
        nb, live = self.nb, self.live
        group = set()

        def blocked(c, axis, seen):
            x, y = (nb['l'][c], nb['r'][c]) if axis == 0 else (nb['u'][c], nb['d'][c])
            if x < 0 or y < 0 or (not live[x] and not live[y]):
                return True
            seen = seen | {c}
            return any(s in boxes and (s in seen or stuck(s, seen)) for s in (x, y))

        def stuck(c, seen):
            if blocked(c, 0, seen) and blocked(c, 1, seen):
                group.add(c)
                return True
            return False

        return stuck(b, frozenset()) and any(c not in self.goals for c in group)


def dead_squares(grid):
    """The floor cells (row, col) where a box can never reach a target."""
    lv = Level(grid)
    return {lv.cells[c] for c in range(len(lv.cells)) if not lv.live[c]}


def solve(grid, max_nodes=300000, weight=1):
    """A move string solving the level, or None (unsolvable or too big).
    weight > 1 trusts the estimate more: faster, longer solutions."""
    lv = Level(grid)
    if not all(lv.live[b] for b in lv.boxes):
        return None
    nb = lv.nb
    parent = {(lv.boxes, min(lv.reach(lv.player, lv.boxes))): None}
    heap = [(weight * lv.estimate(lv.boxes), 0, 0, lv.boxes, lv.player)]
    tick = 0
    while heap:
        _, g, _, bx, p = heapq.heappop(heap)
        r = lv.reach(p, bx)
        if bx <= lv.goals:
            return path_of((bx, min(r)), parent, lv)
        here = (bx, min(r))
        for b in bx:
            for d in 'udlr':
                to, back = nb[d][b], nb[OPP[d]][b]
                if back not in r or to < 0 or to in bx or not lv.live[to]:
                    continue
                nbx = bx - {b} | {to}
                if lv.frozen(to, nbx):
                    continue
                key = (nbx, min(lv.reach(b, nbx)))
                if key in parent:
                    continue
                h = lv.estimate(nbx)
                if h >= BIG:
                    continue
                parent[key] = (here, b, d)
                if len(parent) > max_nodes:
                    return None
                tick += 1
                heapq.heappush(heap, (g + 1 + weight * h, g + 1, tick, nbx, b))
    return None


def walk(lv, src, dst, bx):
    """Shortest player path src -> dst avoiding boxes, as a u/d/l/r string."""
    prev, queue = {src: None}, [src]
    for c in queue:
        if c == dst:
            break
        for d in 'udlr':
            n = lv.nb[d][c]
            if n >= 0 and n not in bx and n not in prev:
                prev[n] = (c, d)
                queue.append(n)
    out = []
    while prev[dst]:
        dst, d = prev[dst]
        out.append(d)
    return ''.join(reversed(out))


def path_of(key, parent, lv):
    """Replay the pushes from the start, walking the player between them."""
    pushes = []
    while parent[key]:
        key, b, d = parent[key]
        pushes.append((b, d))
    pushes.reverse()
    bx, p, out = set(lv.boxes), lv.player, []
    for b, d in pushes:
        out.append(walk(lv, p, lv.nb[OPP[d]][b], bx) + d)
        bx.remove(b)
        bx.add(lv.nb[d][b])
        p = b
    return ''.join(out)


def check(grid, moves):
    """True if the moves solve the level (an independent replay)."""
    walls, goals, boxes, p = parse(grid)
    bx = set(boxes)
    for d in moves:
        dy, dx = DIRS[d]
        n = (p[0] + dy, p[1] + dx)
        if n in walls:
            return False
        if n in bx:
            to = (n[0] + dy, n[1] + dx)
            if to in walls or to in bx:
                return False
            bx.remove(n)
            bx.add(to)
        p = n
    return bx <= goals


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sokoban_levels as sl
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--max-nodes', type=int, default=300000)
    ap.add_argument('--weight', type=float, default=1)
    ap.add_argument('xsb')
    ap.add_argument('levels', nargs='*', type=int, help='1-based ranks in the kept levels (default: all)')
    a = ap.parse_args()
    kept = sl.kept_levels(a.xsb)
    failed = 0
    for idx in a.levels or range(1, len(kept) + 1):
        num, grid = kept[idx - 1]
        sol = solve(grid, a.max_nodes, a.weight)
        ok = sol is not None and check(grid, sol)
        failed += not ok
        print('level %d (#%d): %s' % (idx, num, '%d moves' % len(sol) if ok else 'NOT SOLVED'), flush=True)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
