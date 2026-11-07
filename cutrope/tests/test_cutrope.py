#!/usr/bin/env python3
"""CUTROPE: the 6502 physics and rules (src/phys.inc) against
tools/cutrope.py, bit for bit, then the game on its disk in a2run.

Model part: scripted inputs on each level -- the three solutions (key
cuts: the candy into the frog with its three stars), level 3's early cut
(the candy on the spikes), a level left swinging, the cursor swept across
the ropes with the button held (near(): the box and the cross product,
both signs, the ends of the links), random play (keys, cursor, button) on
every level and the cycle bench (one 10-link rope and two of 6); the whole
state (points, pins, state, ropes on, stars, events, the ground contact
and its segment) is compared every row with verlet.harness. Disk part
(--no-disk to skip): tests/test_cutrope_disk.py.

    python3 tests/test_cutrope.py [--no-disk] [--cycles]
"""
from pathlib import Path
import random
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
ROOT = GAME.parent
sys.path.insert(0, str(GAME / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import cutrope as C  # noqa: E402
from levels import spikes  # noqa: E402
from verlet import harness  # noqa: E402
import a2test  # noqa: E402

SNAPS = [('vl_xf', 10 * C.NPTS), ('vl_pin', C.NPTS), ('cr_state', 6 + C.NCUSH), ('vl_gnd', 1), ('vl_sgi', 1)]
SNAP_BYTES = sum(n for _, n in SNAPS)
CFG = HERE / 'harness.cfg'              # the snapshots in $2000-$5FFF
PRELUDE = '''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
.include "cutconst.inc"
.include "physdefs.inc"
'''
EPILOGUE = '''
init:   JSR     mul_init
        LDA     #<record
        STA     lvp
        LDA     #>record
        STA     lvp+1
        JMP     phys_load
tick:   JMP     phys_tick
record: .byte {record}
.include "phys.inc"
.include "verlet_seg.asm"
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
'''
INPUTS = ['in_cut', 'in_cx', 'in_cy', 'in_btn']


def epilogue(level, data=None):
    data = data if data is not None else C.LEVEL_BYTES[level]
    return EPILOGUE.format(record=', '.join(str(b) for b in data))


# levels for the bubble and the cushions alone (not played)
MECHANICS = [
    dict(name='BUBBLE', candy=(120, 80), ropes=[(120, 30, 3, 1.0)], bubble=(120, 130),
         cushions=[(60, 150, 'R'), (120, 64, 'D')],
         stars=[(120, 110), (90, 60), (150, 60)], frog=(30, 40), segs=spikes(4, 250, 182)),
    dict(name='CUSHIONS', candy=(128, 70), ropes=[(100, 26, 3, 1.0), (156, 26, 3, 1.0)],
         cushions=[(128, 130, 'U'), (200, 80, 'L')],
         stars=[(128, 120), (80, 100), (170, 90)], frog=(220, 160), segs=[(200, 176, 240, 176, 0)]),
    dict(name='TRAMPOLINES', candy=(70, 60), ropes=[(110, 26, 4, 1.0)], cushions=[(30, 120, 'R')],
         stars=[(140, 60), (180, 60), (200, 60)], frog=(230, 30),
         segs=[(40, 150, 110, 150, 2), (110, 170, 180, 170, 2), (180, 120, 240, 120, 2)] + spikes(4, 251, 184)),
]
MECH_BYTES = [C.compile_level(lv) for lv in MECHANICS]


def check(name, level, inputs, every=1, data=None):
    """inputs: a (cut, cx, cy, btn) tuple a tick."""
    seg = []
    for n, v in harness.segments(inputs):
        while n:
            seg.append((min(n, 20), v))
            n -= seg[-1][0]
    while (len(seg) + every - 1) // every * SNAP_BYTES > 0x4000:
        every += 1
    rows = [(n, list(vals), k % every == every - 1 or k == len(seg) - 1) for k, (n, vals) in enumerate(seg)]
    got = harness.run(PRELUDE, epilogue(level, data), INPUTS, SNAPS, rows, init='init',
                      includes=[GAME / 'src'], cfg=CFG, snap_seg='SNAPS', limit=200000)
    g, k, t = C.Game(level, data), 0, 0
    states = []
    for n, (cut, cx, cy, btn), snap in rows:
        for _ in range(n):
            g.tick(cut, cx, cy, btn)
        t += n
        if snap:
            want = g.state_bytes()
            if want != got[k]:
                diff = [i for i in range(len(want)) if want[i] != got[k][i]]
                raise SystemExit(f'{name}: tick {t}, snapshot {k}, bytes {diff[:12]}\n'
                                 f'  want {want.hex(" ")}\n  have {got[k].hex(" ")}')
            k += 1
        states.append(g.state)
    print(f'  {name}: {t} ticks == model in {k} snapshots ({["playing", "won", "lost"][g.state]}, '
          f'{g.nstar} stars, ropes on {g.on:03b}, bubble {g.bub})')
    return g


def keyed(cuts, ticks):
    cuts = dict(cuts)
    return [(cuts.get(t, 0), 0, 0, 0) for t in range(ticks)]


def sweep(level, ticks=240, seed=1):
    """The cursor sweeping left and right across the screen between the
    pins' rows and the candy's, the button held now and then: cuts by near()."""
    rng = random.Random(seed)
    lv = C.LEVELS[level] if level < C.NLEVEL else C.BENCH
    y0, y1 = min(r[1] for r in lv['ropes']) + 4, lv['candy'][1]
    out, x, y, dx, btn = [], 20, (y0 + y1) // 2, 3, 0
    for t in range(ticks):
        x += dx
        if x > 235 or x < 20:
            dx = -dx
        if rng.random() < 0.05:
            y = rng.randrange(y0, y1)
        if rng.random() < 0.08:
            btn = int(rng.random() < 0.6)
        out.append((0, x & 0xFF, y, btn))
    return out


def random_play(level, ticks, seed, keys=3):
    rng = random.Random(seed)
    out, x, y, btn = [], 128, 80, 0
    for t in range(ticks):
        x = max(0, min(255, x + rng.randrange(-4, 5)))
        y = max(16, min(191, y + rng.randrange(-4, 5)))
        if rng.random() < 0.1:
            btn ^= 1
        cut = (1 << rng.randrange(keys)) if rng.random() < 0.01 * keys / 3 else 0
        out.append((cut, x, y, btn))
    return out


def mechanics():
    """The bubble: caught after a cut, floated and popped by key 6, then by
    the cursor; floated away to the top; the cushions puffed by keys and by
    the cursor (the wait between puffs), the candy ahead and not."""
    b, c, _ = MECH_BYTES
    yield 'bubble: cut, caught, popped by key 6', b, keyed([(10, 1), (70, C.M_POP)], 160)
    yield 'bubble: floated away', b, keyed([(10, 1)], 400)
    pop = keyed([(10, 1)], 160)
    for t in range(30, 160):
        pop[t] = (0, 120, max(20, 135 - t // 2), int(t % 9 < 5))
    yield 'bubble: the cursor follows the candy, pops it', b, pop
    puffs = keyed([(10, 1), (40, C.M_CUSH), (44, C.M_CUSH), (52, C.M_CUSH)] +
                  [(t, 2 * C.M_CUSH) for t in range(60, 200, 12)], 200)
    yield 'bubble: caught, puffed by both cushions', b, puffs
    yield 'cushions: keys 4 and 5 under a hanging candy', c, keyed(
        [(5, C.M_CUSH), (20, C.M_CUSH), (31, 2 * C.M_CUSH), (50, 1), (60, C.M_CUSH), (75, 2), (90, 2 * C.M_CUSH)], 220)
    held = keyed([], 120)
    for t in range(10, 120):
        held[t] = (0, 90 + (t & 3) - 1, 120 - (t & 1), 1)
    yield 'cushions: the button held on cushion 1', c, held
    t = MECH_BYTES[2]
    yield 'trampolines: dropped straight, bouncing', t, keyed([(2, 1)], 300)
    yield 'trampolines: cut on the swing, puffed', t, keyed([(30, 1), (60, C.M_CUSH), (90, C.M_CUSH)], 300)
    for k, data in enumerate(MECH_BYTES):
        yield f'{MECHANICS[k]["name"].lower()}: random play', data, random_play(0, 400, 40 + k, keys=6)


SPIKES = next(k for k, lv in enumerate(C.LEVELS) if lv['name'] == 'SPIKES')


def scenarios():
    for lv in range(C.NLEVEL):
        sol = C.SOLUTIONS[lv]
        _, won, _ = C.play(lv, sol)
        yield f'level {lv + 1} solution ({C.LEVELS[lv]["name"]})', lv, keyed(sol, won + 20)
    yield f'level {SPIKES + 1}: the second cut too early, on the spikes', SPIKES, keyed([(4, 1), (20, 2)], 140)
    yield 'level 1 left swinging', 0, keyed([], 300)
    for lv in range(0, C.NLEVEL, 2):
        yield f'level {lv + 1}: the cursor sweeping, button held', lv, sweep(lv, seed=lv)
    for lv in range(1, C.NLEVEL, 2):
        yield f'level {lv + 1}: random play', lv, random_play(lv, 400, 10 + lv, keys=6)
    yield 'the bench: three ropes, then cut one by one', C.BENCH_LEVEL, keyed([(120, 2), (160, 4), (200, 1)], 240)


def check_model():
    print('cutrope physics and rules, 6502 == tools/cutrope.py:')
    ends = {name: check(name, lv, inp) for name, lv, inp in scenarios()}
    mech = {name: check(name, 0, inp, data=data) for name, data, inp in mechanics()}
    assert mech['bubble: floated away'].state == C.LOST
    assert any(g.bub == C.BUB_NONE and g.lv.bubble[0] for g in mech.values())
    for k in range(C.NLEVEL):
        g = [v for n, v in ends.items() if n.startswith(f'level {k + 1} solution')][0]
        assert g.state == C.WON and g.nstar == 3, (k, g.state, g.nstar)
    spikes = ends[f'level {SPIKES + 1}: the second cut too early, on the spikes']
    assert spikes.state == C.LOST and spikes.gnd and spikes.lv.segs[spikes.sgi][0] == 1
    sweeps = [g for n, g in ends.items() if 'cursor' in n]
    cut = sum(1 for g in sweeps if g.on != (1 << g.lv.nropes) - 1)
    assert cut == len(sweeps), f'the cursor cut ropes in {cut} of {len(sweeps)} levels only'


def tick_cycles():
    """Cycles of phys_tick per level (the solution's ticks, the bench)."""
    out = {}
    with tempfile.TemporaryDirectory(prefix='cutrope-cyc-') as tmp:
        for lv in list(range(C.NLEVEL)) + [C.BENCH_LEVEL]:
            text = harness.source(PRELUDE, epilogue(lv), INPUTS, [('vl_xf', 1)], [(1, [0, 0, 0, 0], 0)])
            lab, binary = harness.build(Path(tmp), text, [GAME / 'src'], cfg=CFG)
            steps = a2test.bin_steps(binary, 0x6000, lab['init'])[:1] + [f'call:{lab["init"]:04X}:20']
            steps += [lab.poke(name, 0) for name in INPUTS] + [f'call:{lab["tick"]:04X}:5'] * 90
            r = a2test.run(None, steps)
            el = [int(v) for v in re.findall(r'elapsed=(\d+)', r.out)][1:]
            out[lv] = (min(el), sorted(el)[len(el) // 2], max(el))
    print('phys_tick cycles (min / median / max over 90 ticks, all ropes on): ' +
          ', '.join(f'{"bench" if k == C.BENCH_LEVEL else f"level {k + 1}"} {a:,} / {m:,} / {b:,}'
                    for k, (a, m, b) in out.items()))
    return out


def main():
    check_model()
    if '--cycles' in sys.argv:
        tick_cycles()
    if '--no-disk' not in sys.argv:
        import test_cutrope_disk
        test_cutrope_disk.main()


if __name__ == '__main__':
    main()
