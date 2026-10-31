#!/usr/bin/env python3
"""CATAPULT: the 6502 physics (src/phys.inc) against tools/catapult.py, bit
for bit, then the game on its disk in a2run.

Model part: scripted rounds -- three shots each (power, angle), aimed and
fired by a script played on the model, then replayed: shots short into
the hill, onto the pillar, the column, the cup, long ones against the right
wall, a round played to its end (OVER), random aiming; the whole state
(points, pins and sleep counters, phase, shots, score, timer, the targets
down, ground contacts) is compared every few rows with verlet.harness.
Disk part (--no-disk to skip): tests/test_catapult_disk.py.

    python3 tests/test_catapult.py [--no-disk] [--cycles]
"""
from pathlib import Path
import random
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
CAT = HERE.parent
ROOT = CAT.parents[2]
sys.path.insert(0, str(CAT / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import catapult as C  # noqa: E402
from verlet import harness  # noqa: E402
import a2test  # noqa: E402

SNAPS = [('vl_xf', 10 * C.N), ('vl_pin', C.N), ('vl_still', C.NC), ('cp_phase', 13), ('vl_gnd', C.NC)]
PRELUDE = '''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
.include "catconst.inc"
.include "physdefs.inc"
'''
EPILOGUE = '''
init:   JSR     mul_init
        JSR     sqrt_init
        JMP     phys_reset
tick:   JMP     phys_tick
.include "phys.inc"
.include "verlet_circ.asm"
.include "verlet_hmap.asm"
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "sqrt.asm"
.include "mul.asm"
'''
INPUTS = ['in_power', 'in_stop', 'in_fire']


def check(name, inputs, every=5):
    seg = []
    for n, v in harness.segments(inputs):
        while n:
            seg.append((min(n, 20), v))
            n -= seg[-1][0]
    rows = [(n, list(vals), k % every == every - 1 or k == len(seg) - 1) for k, (n, vals) in enumerate(seg)]
    while sum(1 for r in rows if r[2]) * sum(n for _, n in SNAPS) > 7000:
        every += 2
        rows = [(n, v, k % every == every - 1 or k == len(rows) - 1) for k, (n, v, _) in enumerate(rows)]
    got = harness.run(PRELUDE, EPILOGUE, INPUTS, SNAPS, rows, init='init', includes=[CAT / 'src'],
                      snap_seg='LOWBSS', limit=200000)
    c, k, t = C.Catapult(), 0, 0
    for n, (pw, st, fire), snap in rows:
        for _ in range(n):
            c.tick(pw, st, fire)
        t += n
        if snap:
            want = c.state_bytes()
            if want != got[k]:
                raise SystemExit(f'{name}: tick {t}, snapshot {k}\n  want {want.hex(" ")}\n  have {got[k].hex(" ")}')
            k += 1
    phase = ['aiming', 'swinging', 'flying', 'over'][c.phase]
    print(f'  {name}: {t} ticks == model in {k} snapshots, {phase}, {c.shots} shots left, {c.score} down')
    return c


def scenarios():
    rng = random.Random(12)
    rnd = [(rng.randrange(C.PMAX + 1), rng.randrange(len(C.STOPS))) for _ in range(3)]
    return [('short, the pillar, the column', [(0, 0), (9, 0), (6, 2)]),
            ('the cup, long, high', [(9, 1), (15, 0), (12, 4)]),
            ('a round to the end', [(6, 1), (9, 0), (6, 4)]),
            ('random aiming', rnd)]


def check_model():
    print('catapult physics, 6502 == tools/catapult.py:')
    ends = []
    for name, shots in scenarios():
        c, inputs = C.play(shots)
        inputs += [(c.power, c.stop, 0)] * 30
        ends.append(check(name, inputs))
    assert any(e.score >= 3 for e in ends), [e.score for e in ends]
    assert all(e.phase == C.OVER for e in ends[:3]), [e.phase for e in ends]
    return ends


def tick_cycles():
    """Cycles of phys_tick over the scripted rounds: aiming, swinging, flying
    (without and with contacts: vl_chits), over."""
    text = harness.source(PRELUDE, EPILOGUE, INPUTS, [('vl_xf', 1)], [(1, [0, 0, 0], 0)])
    out = {}
    with tempfile.TemporaryDirectory(prefix='cat-cyc-') as tmp:
        lab, binary = harness.build(tmp, text, [CAT / 'src'])
        for _, shots in scenarios():
            c, inputs = C.play(shots)
            steps = a2test.bin_steps(binary, 0x6000, lab['init'])[:1] + [f'call:{lab["init"]:04X}:20']
            for pw, st, fire in inputs:
                steps += [lab.peek('cp_phase'), lab.poke('in_power', pw), lab.poke('in_stop', st),
                          lab.poke('in_fire', fire), f'call:{lab["tick"]:04X}:5', lab.peek('vl_chits')]
            r = a2test.run(None, steps)
            el = [int(v) for v in re.findall(r'elapsed=(\d+)', r.out)][1:]
            for k, e in enumerate(el):
                ph = r.mem(lab['cp_phase'], 1, k)[0]
                name = ['aim', 'swing', 'fly', 'over'][ph]
                if name == 'fly' and r.mem(lab['vl_chits'], 1, k)[0]:
                    name = 'fly, contacts'
                out.setdefault(name, []).append(e)
    print('phys_tick cycles: ' + ', '.join(f'{k} {min(v):,}-{max(v):,} (mean {sum(v) // len(v):,}, '
                                           f'90 % under {sorted(v)[len(v) * 9 // 10]:,}, {len(v)} ticks)'
                                           for k, v in out.items()))
    return out


def main():
    check_model()
    if '--cycles' in sys.argv:
        tick_cycles()
    if '--no-disk' not in sys.argv:
        import test_catapult_disk
        test_catapult_disk.main()


if __name__ == '__main__':
    main()
