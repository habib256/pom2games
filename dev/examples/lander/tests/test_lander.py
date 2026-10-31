#!/usr/bin/env python3
"""LANDER: the 6502 physics (src/phys.inc) against tools/lander.py, bit for
bit, then the game on a disk in a2run.

Model part: scenarios of scripted inputs (an autopilot run on the model,
then replayed: landings on pads A and C, a free fall and its debris, random
inputs that hit the walls, the ceiling and the end of the fuel, a landing
off the pads, a tilted touch-down); the state (points, status, fuel,
counters, contacts) is compared every few rows. Disk part (--no-disk to
skip): boot build/LANDER.dsk, check the first frames, the thrust key (the
fuel goes down), then put the lander above pad B and let the game land it:
the status byte, the frame count and the status line text on the screen.

    python3 tests/test_lander.py [--no-disk] [--cycles]
"""
from pathlib import Path
import random
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
LANDER = HERE.parent
ROOT = LANDER.parents[2]
sys.path.insert(0, str(LANDER / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import lander as L  # noqa: E402
from verlet import harness  # noqa: E402
import a2test  # noqa: E402

SNAPS = [('vl_xf', 36), ('lv_status', 7), ('vl_gnd', 3)]
PRELUDE = '''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
.include "landconst.inc"
.include "physdefs.inc"
'''


def epilogue(start):
    x, y, vx, vy = start
    return f'''
init:   JSR     mul_init
        LDA     #{x}
        STA     st_x
        LDA     #<{y}
        STA     st_y
        LDA     #>{y}
        STA     st_y+1
        LDA     #<{vx & 0xFFFF}
        STA     st_vx
        LDA     #>{vx & 0xFFFF}
        STA     st_vx+1
        LDA     #<{vy & 0xFFFF}
        STA     st_vy
        LDA     #>{vy & 0xFFFF}
        STA     st_vy+1
        JMP     phys_reset
tick:   JMP     phys_tick
.include "phys.inc"
.include "verlet_hmap.asm"
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "mul.asm"
'''


def run_model(start, pilot, ticks):
    """Closed loop on the model -> the inputs, one (thr, rot) a tick."""
    p, out = L.Lander(start), []
    for k in range(ticks):
        thr, rot = pilot(p, k)
        out.append((thr, rot))
        p.tick(thr, rot)
    return out


def check(name, start, inputs, every=6):
    seg = []
    for n, v in harness.segments(inputs):      # rows of 25 ticks at most
        while n:
            seg.append((min(n, 25), v))
            n -= seg[-1][0]
    rows = [(n, [thr & 0xFF, rot & 0xFF], k % every == every - 1 or k == len(seg) - 1)
            for k, (n, (thr, rot)) in enumerate(seg)]
    while sum(1 for r in rows if r[2]) * sum(n for _, n in SNAPS) > 4000:
        every += 2
        rows = [(n, v, k % every == every - 1 or k == len(rows) - 1) for k, (n, v, _) in enumerate(rows)]
    got = harness.run(PRELUDE, epilogue(start), ['in_thr', 'in_rot'], SNAPS, rows, init='init',
                      includes=[LANDER / 'src'], snap_seg='LOWBSS')
    p, k, t = L.Lander(start), 0, 0
    for n, (thr, rot), snap in rows:
        for _ in range(n):
            p.tick(thr, (rot ^ 0x80) - 0x80)
        t += n
        if snap:
            want = p.state_bytes()
            if want != got[k]:
                raise SystemExit(f'{name}: tick {t}, snapshot {k}\n  want {want.hex(" ")}\n  have {got[k].hex(" ")}')
            k += 1
    status = ['flying', 'landed on pad ' + 'ABC'[p.pad - 1] if p.pad else 'landed', 'crashed'][p.status]
    print(f'  {name}: {t} ticks == model in {k} snapshots, {status}, fuel {p.fuel}')
    return p


def scenarios():
    def auto(pad):
        return lambda p, k: L.autopilot(p, pad) if p.status == L.FLY else (0, 0)
    rng = random.Random(5)
    rnd, cur = [], (0, 0)
    for _ in range(1500):
        if rng.random() < 0.06:
            cur = (int(rng.random() < 0.55), rng.choice([-1, 0, 0, 1]))
        rnd.append(cur)

    def down(p, k):                             # straight down, gently
        return int(p.status == L.FLY and p.y[2] - p.oy[2] > 0x40), 0

    def tilted(p, k):
        if p.status != L.FLY:
            return 0, 0
        thr, _ = L.autopilot(p, 1)
        return thr, 1 if k % 40 < 8 else 0
    return [('pad A', L.above(0), auto(0), 900), ('pad C', L.above(2), auto(2), 900),
            ('free fall and debris', L.START, lambda p, k: (0, 0), 500),
            ('random inputs', L.START, lambda p, k: rnd[k], 1500),
            ('off the pads', (90, 300, 0, 0), down, 900),
            ('tilted touch-down', L.above(1), tilted, 900)]


def check_model():
    print('lander physics, 6502 == tools/lander.py:')
    ends = {}
    for name, start, pilot, ticks in scenarios():
        ends[name] = check(name, start, run_model(start, pilot, ticks))
    assert ends['pad A'].status == L.LANDED and ends['pad A'].pad == 1
    assert ends['pad C'].status == L.LANDED and ends['pad C'].pad == 3
    assert ends['free fall and debris'].status == L.CRASHED
    assert ends['off the pads'].status == L.CRASHED
    assert ends['tilted touch-down'].status == L.CRASHED


def tick_cycles():
    """Cycles of phys_tick in flight: coasting, thrusting and turning."""
    start = L.above(1)
    text = harness.source(PRELUDE, epilogue(start), ['in_thr', 'in_rot'], [('vl_xf', 1)], [(1, [0, 0], 0)])
    with tempfile.TemporaryDirectory(prefix='lander-cyc-') as tmp:
        lab, binary = harness.build(tmp, text, [LANDER / 'src'])
        steps = a2test.bin_steps(binary, 0x6000, lab['init'])[:1] + [f'call:{lab["init"]:04X}:20']
        out = {}
        for name, thr, rot in (('coast', 0, 0), ('engine', 1, 0), ('engine + turn', 1, 1)):
            steps += [lab.poke('in_thr', thr), lab.poke('in_rot', rot)] + [f'call:{lab["tick"]:04X}:5'] * 4
        r = a2test.run(None, steps)
    el = [int(v) for v in re.findall(r'elapsed=(\d+)', r.out)][1:]
    for k, name in enumerate(('coast', 'engine', 'engine + turn')):
        out[name] = max(el[4 * k:4 * k + 4])
    print('phys_tick cycles in flight: ' + ', '.join(f'{k} {v:,}' for k, v in out.items()))
    return out


def main():
    check_model()
    if '--cycles' in sys.argv:
        tick_cycles()
    if '--no-disk' not in sys.argv:
        import test_lander_disk
        test_lander_disk.main()


if __name__ == '__main__':
    main()
