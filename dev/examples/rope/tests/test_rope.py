#!/usr/bin/env python3
"""ROPE: the 6502 physics (src/phys.inc) against tools/rope.py, bit for bit,
then the toy on its disk in a2run.

Model part: scripted inputs -- a swing driven left and right to both ends
of the rail, the floor mode (the pin goes down, the rope lies on the floor,
the pin drags it along), the weight cut in flight and reattached, random
inputs (moves, mode and cut flips) for 1,500 ticks; the whole state
(points, pin, mode, cut, contacts) is compared every few rows with
verlet.harness. Disk part (--no-disk to skip): tests/test_rope_disk.py.

    python3 tests/test_rope.py [--no-disk] [--cycles]
"""
from pathlib import Path
import random
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROPE = HERE.parent
ROOT = ROPE.parents[2]
sys.path.insert(0, str(ROPE / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import rope as R  # noqa: E402
from verlet import harness  # noqa: E402
import a2test  # noqa: E402

SNAPS = [('vl_xf', 10 * R.N), ('rp_px', 4), ('vl_gnd', R.N)]
PRELUDE = '''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
.include "ropeconst.inc"
.include "physdefs.inc"
'''
EPILOGUE = '''
init:   JSR     mul_init
        JMP     phys_reset
tick:   JMP     phys_tick
.include "phys.inc"
.include "verlet_hmap.asm"
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
'''
INPUTS = ['in_mv', 'in_mode', 'in_cut']


def check(name, inputs, every=4):
    seg = []
    for n, v in harness.segments(inputs):
        while n:
            seg.append((min(n, 20), v))
            n -= seg[-1][0]
    rows = [(n, [v & 0xFF for v in vals], k % every == every - 1 or k == len(seg) - 1)
            for k, (n, vals) in enumerate(seg)]
    got = harness.run(PRELUDE, EPILOGUE, INPUTS, SNAPS, rows, init='init', includes=[ROPE / 'src'],
                      snap_seg='LOWBSS')
    p, k, t, ground = R.Rope(), 0, 0, 0
    for n, (mv, mode, cut), snap in rows:
        for _ in range(n):
            p.tick((mv ^ 0x80) - 0x80, mode, cut)
            ground += sum(p.gnd)
        t += n
        if snap:
            want = p.state_bytes()
            if want != got[k]:
                raise SystemExit(f'{name}: tick {t}, snapshot {k}\n  want {want.hex(" ")}\n  have {got[k].hex(" ")}')
            k += 1
    print(f'  {name}: {t} ticks == model in {k} snapshots (pin at {p.px}, {p.py}; '
          f'{ground} point-ticks on the floor)')
    return p


def scenarios():
    rng = random.Random(9)
    rnd, cur = [], [0, 0, 0]
    for _ in range(1500):
        r = rng.random()
        if r < 0.05:
            cur[0] = rng.choice([-1, 0, 1])
        elif r < 0.06:
            cur[1] ^= 1
        elif r < 0.075:
            cur[2] ^= 1
        rnd.append(tuple(cur))
    swing = [(1, 0, 0)] * 70 + [(-1, 0, 0)] * 140 + [(0, 0, 0)] * 60 + [(1, 0, 0)] * 30 + [(0, 0, 0)] * 100
    floor = [(0, 1, 0)] * 120 + [(-1, 1, 0)] * 60 + [(1, 1, 0)] * 90 + [(0, 1, 0)] * 80 + [(0, 0, 0)] * 80
    fling = [(1, 0, 0)] * 30 + [(-1, 0, 0)] * 25 + [(0, 0, 1)] * 150 + [(0, 0, 0)] * 100 + [(1, 1, 1)] * 60
    return [('swing to both ends of the rail', swing), ('the floor: the rope drags', floor),
            ('cut in flight, reattached', fling), ('random inputs', rnd)]


def check_model():
    print('rope physics, 6502 == tools/rope.py:')
    ends = {name: check(name, inp) for name, inp in scenarios()}
    assert ends['the floor: the rope drags'].py == R.PIN_Y[0]
    assert ends['cut in flight, reattached'].cut == 1


def tick_cycles():
    """Cycles of phys_tick: swinging, on the floor, cut."""
    text = harness.source(PRELUDE, EPILOGUE, INPUTS, [('vl_xf', 1)], [(1, [0, 0, 0], 0)])
    out = {}
    with tempfile.TemporaryDirectory(prefix='rope-cyc-') as tmp:
        lab, binary = harness.build(tmp, text, [ROPE / 'src'])
        steps = a2test.bin_steps(binary, 0x6000, lab['init'])[:1] + [f'call:{lab["init"]:04X}:20']
        cases = (('swing (moving the pin)', 1, 0, 0, 30), ('floor (rope on the ground)', 0, 1, 0, 150),
                 ('floor, the pin dragging', 1, 1, 0, 30))
        for name, mv, mode, cut, warm in cases:
            steps += [lab.poke('in_mv', mv), lab.poke('in_mode', mode), lab.poke('in_cut', cut)]
            steps += [f'call:{lab["tick"]:04X}:5'] * warm
        r = a2test.run(None, steps)
    el = [int(v) for v in re.findall(r'elapsed=(\d+)', r.out)][1:]
    at = 0
    for name, *_, warm in cases:
        part = el[at:at + warm][-20:]
        out[name] = (min(part), max(part))
        at += warm
    print('phys_tick cycles: ' + ', '.join(f'{k} {a:,}-{b:,}' for k, (a, b) in out.items()))
    return out


def main():
    check_model()
    if '--cycles' in sys.argv:
        tick_cycles()
    if '--no-disk' not in sys.argv:
        import test_rope_disk
        test_rope_disk.main()


if __name__ == '__main__':
    main()
