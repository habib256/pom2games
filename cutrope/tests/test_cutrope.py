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
from verlet import harness  # noqa: E402
import a2test  # noqa: E402

SNAPS = [('vl_xf', 10 * C.NPTS), ('vl_pin', C.NPTS), ('cr_state', 5), ('vl_gnd', 1), ('vl_sgi', 1)]
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
        LDA     #{level}
        JMP     phys_load
tick:   JMP     phys_tick
.include "phys.inc"
.include "verlet_seg.asm"
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
'''
INPUTS = ['in_cut', 'in_cx', 'in_cy', 'in_btn']


def check(name, level, inputs, every=1):
    """inputs: a (cut, cx, cy, btn) tuple a tick."""
    seg = []
    for n, v in harness.segments(inputs):
        while n:
            seg.append((min(n, 20), v))
            n -= seg[-1][0]
    while (len(seg) + every - 1) // every * SNAP_BYTES > 0x4000:
        every += 1
    rows = [(n, list(vals), k % every == every - 1 or k == len(seg) - 1) for k, (n, vals) in enumerate(seg)]
    got = harness.run(PRELUDE, EPILOGUE.format(level=level), INPUTS, SNAPS, rows, init='init',
                      includes=[GAME / 'src'], cfg=CFG, snap_seg='SNAPS', limit=200000)
    g, k, t = C.Game(level), 0, 0
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
          f'{g.nstar} stars, ropes on {g.on:03b})')
    return g


def keyed(cuts, ticks):
    cuts = dict(cuts)
    return [(cuts.get(t, 0), 0, 0, 0) for t in range(ticks)]


def sweep(level, ticks=240, seed=1):
    """The cursor sweeping left and right across the screen at the ropes'
    rows, the button held now and then: cuts by near()."""
    rng = random.Random(seed)
    out, x, y, dx, btn = [], 20, 40, 3, 0
    for t in range(ticks):
        x += dx
        if x > 235 or x < 20:
            dx = -dx
        if rng.random() < 0.05:
            y = rng.randrange(28, 60)
        if rng.random() < 0.08:
            btn = int(rng.random() < 0.6)
        out.append((0, x & 0xFF, y, btn))
    return out


def random_play(level, ticks, seed):
    rng = random.Random(seed)
    out, x, y, btn = [], 128, 80, 0
    for t in range(ticks):
        x = max(0, min(255, x + rng.randrange(-4, 5)))
        y = max(16, min(191, y + rng.randrange(-4, 5)))
        if rng.random() < 0.1:
            btn ^= 1
        cut = (1 << rng.randrange(3)) if rng.random() < 0.01 else 0
        out.append((cut, x, y, btn))
    return out


def scenarios():
    yield 'level 1 solution: key 1 at the swing', 0, keyed(C.SOLUTIONS[0], 110)
    yield 'level 2 solution: the right rope, then the left', 1, keyed(C.SOLUTIONS[1], 170)
    yield 'level 3 solution: over the spikes to the ledge', 2, keyed(C.SOLUTIONS[2], 120)
    yield 'level 3: the second cut too early, on the spikes', 2, keyed([(4, 1), (20, 2)], 140)
    yield 'level 1 left swinging', 0, keyed([], 300)
    for lv in range(C.NLEVEL):
        yield f'level {lv + 1}: the cursor sweeping, button held', lv, sweep(lv, seed=lv)
    for lv in range(C.NLEVEL):
        yield f'level {lv + 1}: random play', lv, random_play(lv, 400, 10 + lv)
    yield 'the bench: three ropes, then cut one by one', C.BENCH_LEVEL, keyed([(120, 2), (160, 4), (200, 1)], 240)


def check_model():
    print('cutrope physics and rules, 6502 == tools/cutrope.py:')
    ends = {name: check(name, lv, inp) for name, lv, inp in scenarios()}
    for k in range(C.NLEVEL):
        g = [v for n, v in ends.items() if n.startswith(f'level {k + 1} solution')][0]
        assert g.state == C.WON and g.nstar == 3, (k, g.state, g.nstar)
    spikes = ends['level 3: the second cut too early, on the spikes']
    assert spikes.state == C.LOST and spikes.gnd and spikes.lv.segs[spikes.sgi][0] == 1
    cut = sum(1 for n, g in ends.items() if 'cursor' in n and g.on != (1 << g.lv.nropes) - 1)
    assert cut == C.NLEVEL, f'the cursor cut ropes in {cut} levels only'


def tick_cycles():
    """Cycles of phys_tick per level (the solution's ticks, the bench)."""
    out = {}
    with tempfile.TemporaryDirectory(prefix='cutrope-cyc-') as tmp:
        for lv in list(range(C.NLEVEL)) + [C.BENCH_LEVEL]:
            text = harness.source(PRELUDE, EPILOGUE.format(level=lv), INPUTS, [('vl_xf', 1)], [(1, [0, 0, 0, 0], 0)])
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
