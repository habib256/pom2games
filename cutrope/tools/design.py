#!/usr/bin/env python3
"""CUTROPE -- level design by search (a tool: tools/levels.py holds the result).

    python3 tools/design.py TEMPLATE [--seed S] [--tries N] [--keep K]

A template draws a level's skeleton at random (the candy, its ropes, a
bubble, cushions, spikes) and a plan (the keys and their ticks); the plan is
played on the model; the frog is put where the candy is at the plan's end
(on a ledge), the three stars on its path, after the first key. A candidate
is kept when the solver (solve.py) finds that:
  - the plan wins with 3 stars after its last key, and each of its keys can move by at least
    MIN_TOL ticks either way with the result still 3 stars (a person at 30
    ticks a second);
  - doing nothing, or cutting every rope at once, does not give 3 stars;
  - among every schedule of as many keys (step 2), few give 3 stars (the
    level asks for the timing).
It prints the kept ones as tools/levels.py entries, the hardest last.
"""
import math
import random
import sys

import cutrope as C
import solve
from levels import L1, L2, L3, P4, P5, POP, spikes

MIN_TOL = 2                 # ticks a key can move each way (a window of 5)
MAX_SHARE = {1: 0.15, 2: 0.04, 3: 0.02}     # of the schedules (step 2) that give 3 stars
FLOOR = 182


def rope(rng, candy, n, slack=1.0, dx=(-60, 60), dy=(-60, -24)):
    """A pin above the candy whose links come out 9-15 px."""
    for _ in range(200):
        px = candy[0] + rng.randint(*dx)
        py = candy[1] + rng.randint(*dy)
        if not (C.CEIL + 6 <= py and 8 <= px <= 247):
            continue
        ln = slack * math.hypot(candy[0] - px, candy[1] - py) / n
        if 9 <= ln <= 15:
            return (px, py, n, slack)
    return None


# --- templates: -> (level dict without stars / frog, plan [(tick, mask)]) ---------
def t_swing(rng):
    candy = (rng.randint(30, 226), rng.randint(40, 90))
    r = rope(rng, candy, rng.choice([3, 4]), dx=(-70, 70), dy=(-50, -10))
    return dict(candy=candy, ropes=[r]), [(rng.randint(20, 90), L1)]


def t_two(rng):
    candy = (rng.randint(60, 196), rng.randint(40, 80))
    a = rope(rng, candy, rng.choice([3, 4]), dx=(-70, -20))
    b = rope(rng, candy, rng.choice([3, 4]), slack=rng.choice([1.0, 1.0, 1.2, 1.3]), dx=(20, 70))
    first = rng.choice([L1, L2])
    t1 = rng.randint(4, 60)
    return dict(candy=candy, ropes=[a, b]), [(t1, first), (t1 + rng.randint(15, 80), L1 + L2 - first)]


def t_three(rng):
    candy = (rng.randint(80, 176), rng.randint(50, 90))
    rs = [rope(rng, candy, 3, dx=(-70, -30)), rope(rng, candy, 2, dx=(-10, 10), dy=(-40, -22)),
          rope(rng, candy, 3, dx=(30, 70))]
    order = [L1, L2, L3]
    rng.shuffle(order)
    t = rng.randint(4, 40)
    plan = []
    for m in order:
        plan.append((t, m))
        t += rng.randint(12, 60)
    return dict(candy=candy, ropes=rs), plan


# auto: the bubble where the candy is `bubble` ticks after the first key; each
# cushion (key index in the plan, dir, distance, across) aimed at the candy
# where it is when that key puffs it
def t_bubble(rng):
    """Cut, the bubble catches the candy on its way, it floats, pop it."""
    candy = (rng.randint(40, 216), rng.randint(40, 80))
    r = rope(rng, candy, rng.choice([3, 4]), dx=(-60, 60), dy=(-40, -20))
    t1 = rng.randint(5, 50)
    return (dict(candy=candy, ropes=[r]), [(t1, L1), (t1 + rng.randint(25, 90), POP)],
            dict(bubble=rng.randint(6, 20)))


def t_swing_bubble(rng):
    """The bubble on the swing: it lifts the candy on its rope; cut, pop."""
    candy = (rng.randint(40, 216), rng.randint(50, 90))
    r = rope(rng, candy, rng.choice([3, 4]), dx=(-70, 70), dy=(-50, -10))
    t1 = rng.randint(30, 80)
    return (dict(candy=candy, ropes=[r]), [(t1, L1), (t1 + rng.randint(20, 80), POP)],
            dict(bubble=-rng.randint(5, 25)))


def t_cushion(rng):
    """A rope and a cushion: a puff swings the candy, the cut sends it."""
    candy = (rng.randint(50, 206), rng.randint(50, 100))
    r = rope(rng, candy, rng.choice([3, 4]), dx=(-30, 30), dy=(-50, -24))
    t1 = rng.randint(3, 20)
    plan = [(t1, P4), (t1 + rng.randint(10, 50), L1)]
    return dict(candy=candy, ropes=[r]), plan, dict(cushions=[(0, rng.choice('RL'), rng.randint(20, 50), 0)])


def t_drop_cushion(rng):
    """Cut, then a puff sends the falling candy aside."""
    candy = (rng.randint(60, 196), rng.randint(40, 70))
    r = rope(rng, candy, 3, dx=(-20, 20), dy=(-45, -27))
    t1 = rng.randint(5, 40)
    return (dict(candy=candy, ropes=[r]), [(t1, L1), (t1 + rng.randint(8, 25), P4)],
            dict(cushions=[(1, rng.choice('RL'), rng.randint(20, 45), rng.randint(-6, 6))]))


def t_two_cushions(rng):
    """Cut, puff one way, then the other."""
    candy = (rng.randint(60, 196), rng.randint(40, 70))
    r = rope(rng, candy, 3, dx=(-20, 20), dy=(-45, -27))
    t1 = rng.randint(5, 30)
    t2 = t1 + rng.randint(6, 18)
    d = rng.choice('RL')
    return (dict(candy=candy, ropes=[r]), [(t1, L1), (t2, P4), (t2 + rng.randint(12, 30), P5)],
            dict(cushions=[(1, d, rng.randint(20, 40), 0), (2, rng.choice('UDRL'), rng.randint(20, 40), 0)]))


def t_bubble_cushion(rng):
    """Cut, caught by the bubble, a puff steers it, pop."""
    candy = (rng.randint(60, 196), rng.randint(40, 70))
    r = rope(rng, candy, 3, dx=(-40, 40), dy=(-45, -24))
    t1 = rng.randint(5, 40)
    t2 = t1 + rng.randint(25, 50)
    return (dict(candy=candy, ropes=[r]), [(t1, L1), (t2, P4), (t2 + rng.randint(15, 50), POP)],
            dict(bubble=rng.randint(6, 18), cushions=[(1, rng.choice('RL'), rng.randint(20, 45), 0)]))


def t_two_bubble(rng):
    """Two ropes and a bubble."""
    lv, plan = t_two(rng)
    plan.append((plan[-1][0] + rng.randint(25, 60), POP))
    return lv, plan, dict(bubble=rng.randint(5, 20) + plan[1][0] - plan[0][0])


def t_tramp(rng):
    """Cut on the swing: the candy lands on a trampoline, bounces to the frog."""
    candy = (rng.randint(40, 216), rng.randint(40, 80))
    r = rope(rng, candy, rng.choice([3, 4]), dx=(-70, 70), dy=(-50, -15))
    t1 = rng.randint(10, 80)
    return (dict(candy=candy, ropes=[r]), [(t1, L1)],
            dict(tramps=[(0, rng.randint(10, 35), rng.randint(14, 30))], tail=rng.randint(30, 70)))


def t_two_tramps(rng):
    """Two bounces: the second trampoline where the first sends it."""
    candy = (rng.randint(40, 216), rng.randint(40, 70))
    r = rope(rng, candy, 3, dx=(-70, 70), dy=(-45, -20))
    t1 = rng.randint(10, 70)
    d1 = rng.randint(10, 30)
    return (dict(candy=candy, ropes=[r]), [(t1, L1)],
            dict(tramps=[(0, d1, rng.randint(14, 26)), (0, d1 + rng.randint(25, 60), rng.randint(14, 26))],
                 tail=d1 + rng.randint(60, 110)))


def t_tramp_cushion(rng):
    """Cut, bounce, a puff in the air sends it to the frog."""
    candy = (rng.randint(40, 216), rng.randint(40, 70))
    r = rope(rng, candy, 3, dx=(-50, 50), dy=(-45, -20))
    t1 = rng.randint(10, 60)
    d1 = rng.randint(10, 30)
    t2 = t1 + d1 + rng.randint(6, 20)
    return (dict(candy=candy, ropes=[r]), [(t1, L1), (t2, P4)],
            dict(tramps=[(0, d1, rng.randint(14, 26))],
                 cushions=[(1, rng.choice('RL'), rng.randint(20, 40), 0)], tail=rng.randint(20, 50)))


def t_two_tramp(rng):
    """Two ropes, then a trampoline."""
    lv, plan = t_two(rng)
    return lv, plan, dict(tramps=[(1, rng.randint(10, 30), rng.randint(14, 26))], tail=rng.randint(40, 80))


TEMPLATES = dict(tramp=t_tramp, two_tramps=t_two_tramps, tramp_cushion=t_tramp_cushion, two_tramp=t_two_tramp, swing=t_swing, two=t_two, three=t_three, bubble=t_bubble, swing_bubble=t_swing_bubble,
                 cushion=t_cushion, drop_cushion=t_drop_cushion, two_cushions=t_two_cushions,
                 bubble_cushion=t_bubble_cushion, two_bubble=t_two_bubble)
VEC = dict(R=(1, 0), D=(0, 1), L=(-1, 0), U=(0, -1))


def candy_at(lv, plan, tick):
    """The candy's pixel at the start of `tick` (None: the level ends first
    or does not compile)."""
    try:
        g, sched = C.Game(0, C.compile_level(lv)), dict(plan)
    except AssertionError:
        return None
    for t in range(tick):
        g.tick(sched.get(t, 0))
        if g.state != C.PLAY:
            return None
    return g.candy_px()


def anchor(lv, plan, auto):
    """The auto bubble and cushions placed (-> the level, or None)."""
    lv = dict(lv, stars=[(20, 30), (30, 30), (40, 30)], frog=(4, 20), segs=[])
    if auto.get('bubble') is not None:
        p = candy_at(lv, plan, plan[0][0] + auto['bubble'])
        if p is None or not (8 <= p[0] <= 247 and C.BUB_TOP + 6 <= p[1] <= 184):
            return None
        lv['bubble'] = p
    for k, dt, w in auto.get('tramps', []):
        p = candy_at(lv, plan, plan[k][0] + dt)
        if p is None or not (40 <= p[1] <= 170 and 4 + w <= p[0] <= 251 - w):
            return None
        y = p[1] + 5
        lv['segs'] = lv['segs'] + [(p[0] - w, y, p[0] + w, y, 2)]
    cush = []
    for k, d, dist, across in auto.get('cushions', []):
        p = candy_at(dict(lv, cushions=cush), plan, plan[k][0])
        if p is None:
            return None
        vx, vy = VEC[d]
        x, y = p[0] - vx * dist - vy * across, p[1] - vy * dist + vx * across
        if not (16 <= x <= 239 and 32 <= y <= 172):
            return None
        cush.append((x, y, d))
    if cush:
        lv['cushions'] = cush
    return lv


def place(lv, plan, rng, tail=None):
    """Play the plan on the skeleton (spikes on the floor, unless a ledge):
    -> the level with its frog and stars, or None. tail: ticks after the
    last key to the frog (default 15-45); with trampolines, every one of
    them bounces the candy first."""
    own = list(lv.get('segs', []))
    lv = dict(lv, stars=[(20, 30), (30, 30), (40, 30)], frog=(4, 20), segs=own + list(spikes(4, 251, FLOOR)))
    if rng.random() < 0.3:
        lv['segs'] = own                # no floor: the candy falls out
    try:
        data = C.compile_level(lv)
    except AssertionError:
        return None
    g, sched, trace = C.Game(0, data), dict(plan), []
    end = plan[-1][0] + (tail or rng.randint(15, 45))
    bounced = set()
    for t in range(end):
        g.tick(sched.get(t, 0))
        if g.state != C.PLAY:
            return None
        if g.ev & C.EV_BOING:
            bounced.add(g.sgi)
        trace.append(g.candy_px())
    if len(bounced) < sum(1 for sg in own if sg[4] == C.SEG_TRAMP):
        return None
    fx, fy = trace[-1]
    if not (11 <= fx <= 244 and 30 <= fy <= 168):
        return None
    lv['frog'] = (fx - 7, fy - 7)
    t0 = plan[0][0]
    path = trace[max(4, t0 - 20):end - 6]     # the stars: by length along the path
    if len(path) < 6:
        return None
    arc = [0]
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        arc.append(arc[-1] + math.hypot(bx - ax, by - ay))
    if arc[-1] < 40:
        return None
    for _ in range(20):
        fs = sorted(rng.uniform(0.05, 0.95) for _ in range(3))
        if min(b - a for a, b in zip([0] + fs, fs + [1])) >= 0.12:
            break
    else:
        return None
    stars = [path[next(i for i, a in enumerate(arc) if a >= f * arc[-1])] for f in fs]
    pts = stars + [(fx, fy)]
    for i in range(4):
        for j in range(i):
            if abs(pts[i][0] - pts[j][0]) + abs(pts[i][1] - pts[j][1]) < 12:
                return None
    if any(not (8 <= x <= 247 and 24 <= y <= 180) for x, y in stars):
        return None
    lv['stars'] = stars
    ledge = (fx - 20, fy + 8, fx + 20, fy + 8, 0)
    segs = [s for s in lv['segs'] if s[4] != 1 or not (s[0] <= fx + 22 and s[2] >= fx - 22)] if fy + 8 > FLOOR - 12 else lv['segs']
    lv['segs'] = segs + [tuple(max(4, min(251, v)) if k in (0, 2) else v for k, v in enumerate(ledge))]
    return lv


def budget_ok(lv):
    links = sum(r[2] for r in lv['ropes'])
    return links + (1 if lv.get('bubble') else 0) + len(lv.get('cushions', [])) <= 7


REJECT = {}


def no(why):
    REJECT[why] = REJECT.get(why, 0) + 1


def evaluate(lv, plan):
    """-> (score, report) or None: the checks of the module's docstring."""
    try:
        data = C.compile_level(lv)
    except AssertionError:
        return no('compile')
    g, t = solve.play_sched(0, plan, data=data)
    if g.state != C.WON or g.nstar != 3:
        return no('plan not 3 stars')
    if t <= plan[-1][0]:
        return no('won before the last key')
    tol = solve.tolerance(0, plan, data)
    if any(min(t0 - a, b - t0) < MIN_TOL for (k, a, b), (t0, _) in zip(tol, plan)):
        return no('tolerance')
    for name, (st, n) in solve.trivial(0, data).items():
        if st == C.WON and n == 3:
            return no('trivial')
    wins, count = solve.search(0, len(plan), step=2 if len(plan) < 3 else 4, until=plan[-1][0] + 30,
                               horizon=t + 60, data=data)
    three = sum(1 for n in wins.values() if n == 3)
    share = three / max(count, 1)
    if share > MAX_SHARE[len(plan)]:
        return no('share')
    width = min(b - a + 1 for _, a, b in tol)
    pts = [lv['candy'], *lv['stars'], (lv['frog'][0] + 7, lv['frog'][1] + 7)]
    spread = max(x for x, _ in pts) - min(x for x, _ in pts) + (max(y for _, y in pts) - min(y for _, y in pts)) // 2
    if spread < 70:
        return no('spread')
    return spread, dict(ticks=t, tol=tol, three=three, count=count, width=width, spread=spread)


def fmt(lv, plan, rep):
    keys = {L1: 'L1', L2: 'L2', L3: 'L3', P4: 'P4', P5: 'P5', POP: 'POP'}
    parts = [f"candy={lv['candy']}", f"ropes={lv['ropes']}"]
    if lv.get('bubble'):
        parts.append(f"bubble={lv['bubble']}")
    if lv.get('cushions'):
        parts.append(f"cushions={lv['cushions']}")
    parts += [f"stars={lv['stars']}", f"frog={lv['frog']}", f"segs={lv['segs']}"]
    sol = '[' + ', '.join(f'({t}, {keys[m]})' for t, m in plan) + ']'
    win = ', '.join(f'key {k} {a}-{b}' for k, a, b in rep['tol'])
    return (f"    dict(name='?', " + ', '.join(parts) + f",\n         solution={sol}, windows='{win}'),"
            f"  # {rep['three']} of {rep['count']} schedules 3 stars, won at {rep['ticks']}, spread {rep['spread']}")


def main(argv):
    name = argv[0]
    opt = {a[2:]: int(argv[k + 1]) for k, a in enumerate(argv) if a.startswith('--')}
    rng = random.Random(opt.get('seed', 1))
    kept = []
    for _ in range(opt.get('tries', 300)):
        sk, plan, *auto = TEMPLATES[name](rng)
        if any(r is None for r in sk['ropes']):
            continue
        if auto:
            sk = anchor(sk, plan, auto[0])
            if sk is None:
                no('anchor')
                continue
        if not budget_ok(sk):
            continue
        lv = place(sk, plan, rng, auto[0].get('tail') if auto else None)
        if lv is None:
            no('place')
            continue
        ev = evaluate(lv, plan)
        if ev:
            kept.append((ev[0], lv, plan, ev[1]))
            if len(kept) >= opt.get('keep', 6):
                break
    for spread, lv, plan, rep in sorted(kept, key=lambda k: k[0]):
        print(fmt(lv, plan, rep))
    print(f'# {name}: kept {len(kept)}; rejected {REJECT}')


if __name__ == '__main__':
    main(sys.argv[1:])
