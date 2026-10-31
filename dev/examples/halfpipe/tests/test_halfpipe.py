#!/usr/bin/env python3
"""HALFPIPE: the 6502 physics (src/phys.inc) against tools/halfpipe.py, bit
for bit, then the game on a disk in a2run.

Model part: scenarios of scripted inputs (a pilot run on the model, then
replayed): pumping up to the lips and above, 360s landed (lean in the air,
stop in time), an over-rotation that lands upside down (a crash and its
debris), 1,500 ticks of random inputs; the state (points, contacts and
their segments, status, air, rotation, score) is compared every few rows.
Disk part (--no-disk to skip): tests/test_halfpipe_disk.py.

    python3 tests/test_halfpipe.py [--no-disk] [--cycles]
"""
from pathlib import Path
import random
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
PIPE = HERE.parent
ROOT = PIPE.parents[2]
sys.path.insert(0, str(PIPE / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import halfpipe as H  # noqa: E402
from verlet import harness  # noqa: E402
import a2test  # noqa: E402

SNAPS = [('vl_xf', 30), ('vl_gnd', 6), ('hp_status', 12)]
PRELUDE = '''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
.include "pipeconst.inc"
.include "physdefs.inc"
'''
EPILOGUE = '''
init:   JSR     mul_init
        JMP     phys_reset
tick:   JMP     phys_tick
.include "phys.inc"
.include "verlet_seg.asm"
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "mul.asm"
.include "bcd.asm"
'''


def s8(v):
    return v - 256 if v & 0x80 else v


def run_model(pilot, ticks):
    """Closed loop on the model -> the inputs, one (pump, lean) a tick."""
    p, out = H.Rider(), []
    for k in range(ticks):
        pump, lean = pilot(p, k)
        out.append((pump, lean))
        p.tick(pump, lean)
    return out


def check(name, inputs, every=6):
    seg = []
    for n, v in harness.segments(inputs):
        while n:
            seg.append((min(n, 25), v))
            n -= seg[-1][0]
    rows = [(n, [pump & 0xFF, lean & 0xFF], k % every == every - 1 or k == len(seg) - 1)
            for k, (n, (pump, lean)) in enumerate(seg)]
    while sum(1 for r in rows if r[2]) * sum(n for _, n in SNAPS) > 4000:
        every += 2
        rows = [(n, v, k % every == every - 1 or k == len(rows) - 1) for k, (n, v, _) in enumerate(rows)]
    got = harness.run(PRELUDE, EPILOGUE, ['in_pump', 'in_lean'], SNAPS, rows, init='init',
                      includes=[PIPE / 'src'], snap_seg='LOWBSS', limit=200000)
    p, k, t = H.Rider(), 0, 0
    landings, peak = [], 255
    for n, (pump, lean), snap in rows:
        for _ in range(n):
            sc = p.score
            p.tick(pump, s8(lean))
            if p.score != sc:
                landings.append(p.spins)
            peak = min(peak, p.peak)
        t += n
        if snap:
            want = p.state_bytes()
            if want != got[k]:
                raise SystemExit(f'{name}: tick {t}, snapshot {k}\n  want {want.hex(" ")}\n  have {got[k].hex(" ")}')
            k += 1
    status = ['riding', 'crashed'][p.status]
    print(f'  {name}: {t} ticks == model in {k} snapshots, {status}, score {p.score}, '
          f'{len(landings)} landings ({sum(1 for s in landings if s)} with a 360), body peak row {peak}')
    return p, landings, peak


def pumper(p, k):
    return H.pumper(p, k) if p.status == H.RIDE else (0, 0)


def trick(stop, high):
    """Pump on the ground; in the air above the lip by `high` px, lean until
    |rot| reaches `stop` octants."""
    def pilot(p, k):
        if p.status:
            return 0, 0
        if p.gnd[0] or p.gnd[1]:
            return 1, 0
        if p.peak < H.LIP_Y - high and abs(s8(p.rot)) < stop:
            return 0, 1
        return 0, 0
    return pilot


def scenarios():
    rng = random.Random(7)
    rnd, cur = [], (0, 0)
    for _ in range(1500):
        if rng.random() < 0.05:
            cur = (int(rng.random() < 0.6), rng.choice([-1, 0, 0, 1]))
        rnd.append(cur)
    return [('pumping to the lips', pumper, 700), ('360s', trick(7, 10), 1300),
            ('over-rotation, crash and debris', trick(3, 0), 450),
            ('random inputs', lambda p, k: rnd[k], 1500)]


def check_model():
    print('halfpipe physics, 6502 == tools/halfpipe.py:')
    out = {}
    for name, pilot, ticks in scenarios():
        out[name] = check(name, run_model(pilot, ticks))
    p, landings, peak = out['pumping to the lips']
    assert p.status == H.RIDE and peak < H.LIP_Y - 10, (p.status, peak)
    p, landings, _ = out['360s']
    assert p.status == H.RIDE and sum(1 for s in landings if s == 1) >= 2, landings
    p, _, _ = out['over-rotation, crash and debris']
    assert p.status == H.CRASHED and p.timer > 100, (p.status, p.timer)


def tick_cycles():
    """Cycles of phys_tick: rolling on the bottom, on a curve, in the air."""
    text = harness.source(PRELUDE, EPILOGUE, ['in_pump', 'in_lean'], [('vl_xf', 1)], [(1, [0, 0], 0)])
    states = {}
    p = H.Rider()
    for k in range(400):
        pump, lean = H.pumper(p, k)
        p.tick(pump, lean)
        if p.gnd[0] and p.gnd[1] and 'bottom' not in states and p.g.sgi[0] in (8, 9):
            states['both wheels on the bottom'] = (p.copy(), dict(p.g.sgi), p.air, p.oct)
        if p.gnd[0] and p.gnd[1] and 'curve' not in states and p.g.sgi[0] in H.CURVES:
            states['both wheels on a curve'] = (p.copy(), dict(p.g.sgi), p.air, p.oct)
        if p.air > 20 and 'air' not in states:
            states['in the air'] = (p.copy(), dict(p.g.sgi), p.air, p.oct)
    with tempfile.TemporaryDirectory(prefix='halfpipe-cyc-') as tmp:
        lab, binary = harness.build(tmp, text, [PIPE / 'src'])
        steps = a2test.bin_steps(binary, 0x6000, lab['init'])[:1] + [f'call:{lab["init"]:04X}:20']
        for name, (q, sgi, air, oc) in states.items():
            steps += [lab.poke('vl_xf', v, k) for k, v in enumerate(q.soa_bytes())]
            steps += [lab.poke('vl_sgi', sgi.get(i, 0xFF), i) for i in range(3)]
            steps += [lab.poke('hp_air', air), lab.poke('hp_oct', oc), lab.poke('in_pump', 1),
                      lab.poke('in_lean', 0), f'call:{lab["tick"]:04X}:5']
        r = a2test.run(None, steps)
    el = [int(v) for v in re.findall(r'elapsed=(\d+)', r.out)][1:]
    out = dict(zip(states, el))
    print('phys_tick cycles: ' + ', '.join(f'{k} {v:,}' for k, v in out.items()))
    return out


def main():
    check_model()
    if '--cycles' in sys.argv:
        tick_cycles()
    if '--no-disk' not in sys.argv:
        import test_halfpipe_disk
        test_halfpipe_disk.main()


if __name__ == '__main__':
    main()
