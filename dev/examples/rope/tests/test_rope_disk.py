#!/usr/bin/env python3
"""ROPE on its disk in a2run: boot, the key line, L moves the pin, M lowers
it onto the floor (points in contact), space cuts the weight, R resets.
Checks the state bytes and the text the screen shows (the glyph bytes of
the two text lines on the page on display), then the cycles a main loop
turn costs swinging and on the floor (median and worst against LIMITS).

    python3 tests/test_rope_disk.py      (tests/test_rope.py runs it)
"""
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROPE = HERE.parent
ROOT = ROPE.parents[2]
sys.path.insert(0, str(ROPE / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import rope as R  # noqa: E402
import a2test  # noqa: E402
from fonts import glyph  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

DISK = ROPE / 'build/ROPE.dsk'
LBL = ROPE / 'build/rope.lbl'
STATE = ['rp_px', 'rp_py', 'rp_mode', 'rp_cut', 'frames']
# cycles a main loop turn, median and worst: the measured numbers + 5 %
LIMITS = {'swinging': (40_500, 41_400), 'floor': (50_200, 55_100)}


def look(lab):
    return [lab.peek(n) for n in STATE] + [lab.peek('vl_gnd', R.N)] + \
        [f'peek:{b + hgr_offset(y):04X}:40' for b in (0x2000, 0x4000) for y in range(16)] + [lab.peek('pidx')]


def seen(r, lab, k):
    st = {n: r.mem(lab[n], 1, k)[0] for n in STATE}
    gnd = sum(r.mem(lab['vl_gnd'], R.N, k))
    page = r.mem(lab['pidx'], 1, k)[0]
    rows = [r.mem(0x2000 + 0x2000 * page + hgr_offset(y), 40, k) for y in range(16)]
    lines = []
    for line in range(2):
        s = ''
        for col in range(40):
            cell = [rows[8 * line + y][col] for y in range(8)]
            s += next((chr(c) for c in range(0x20, 0x60) if glyph(c) == cell), '?')
        lines.append(s.rstrip())
    return st, gnd, lines


def main():
    lab = a2test.labels(LBL)
    steps = [lab.until('main', 2000), 'wait:60'] + look(lab)                 # 0: boot
    steps += ['key:L', 'wait:8', 'key:L', 'wait:8', 'key:L', 'wait:40'] + look(lab)  # 1: right
    steps += ['wait:600'] + look(lab)                                       # 2: 10 s swinging
    steps += ['key:M', 'wait:240'] + look(lab)                              # 3: the floor
    steps += ['wait:600'] + look(lab)                                       # 4: 10 s on the floor
    steps += ['key: ', 'wait:60'] + look(lab)                               # 5: cut
    steps += ['key:R', 'wait:30'] + look(lab)                               # 6: reset
    r = a2test.run(str(DISK), steps)
    (s0, _, t0), (s1, _, _), (s2, _, _), (s3, g3, t3), (s4, _, _), (s5, g5, t5), (s6, _, t6) = \
        (seen(r, lab, k) for k in range(7))
    assert t0 == ['J L:PIN  M:FLOOR  SPACE:CUT  R:RESET', 'SWING'], t0
    assert s0['rp_px'] == R.START_X and s0['rp_py'] == R.PIN_Y[0] and s0['rp_mode'] == 0, s0
    assert s1['rp_px'] > R.START_X + 20, s1
    assert s3['rp_mode'] == 1 and s3['rp_py'] == R.PIN_Y[1] and g3 >= 2 and t3[1] == 'FLOOR', (s3, g3, t3)
    assert s5['rp_cut'] == 1 and t5[1] == 'FLOOR - WEIGHT CUT', (s5, t5)
    assert s6['rp_cut'] == 0 and s6['rp_mode'] == 0 and s6['rp_px'] == R.START_X and t6[1] == 'SWING', (s6, t6)
    print(f'rope disk: boot "{t0[0]}"; L: pin {s0["rp_px"]} -> {s1["rp_px"]}; M: pin row {s3["rp_py"]}, '
          f'{g3} points on the floor; space: "{t5[1]}"; R: "{t6[1]}"')
    return frame_cycles(lab)


def frame_cycles(lab):
    """300 turns swinging (the pin moved right three times), 300 turns on
    the floor (M, 4 s to settle)."""
    peeks = [('rp_mode', 1)]
    swing = frame_turns(lab, ['press:L', 'wait:8', 'press:L', 'wait:8', 'press:L', 'wait:40'], 300, peeks)
    floor = frame_turns(lab, ['press:M', 'wait:240'], 300, peeks)
    return check_cycles('rope', {'swinging': [c for c, s in swing if s['rp_mode'][0] == 0],
                                 'floor': [c for c, s in floor if s['rp_mode'][0] == 1]})


def frame_turns(lab, pre, n, peeks, keyevery=0, key=''):
    """n main loop turns after the steps pre: [(cycles, {name: bytes})], the
    cycles from main to main (input, tick, events, a page drawn and shown),
    the bytes peeked at the end of the turn."""
    steps = [lab.until('main', 2000)] + pre + [lab.until('main', 600)]
    for i in range(n):
        if keyevery and i % keyevery == 0:
            steps.append('press:' + key)
        steps += [lab.until('input', 600), lab.until('main', 600)] + [lab.peek(name, ln) for name, ln in peeks]
    r = a2test.run(str(DISK), steps)
    cyc, rows, k = r.cycles[-(2 * n + 1)::2], r.rows[-n * len(peeks):], len(peeks)
    return [(cyc[i + 1] - cyc[i], {name: rows[i * k + j][1] for j, (name, _) in enumerate(peeks)})
            for i in range(n)]


def check_cycles(name, by_state):
    """Median and worst cycles a turn of each state against LIMITS (the
    measured numbers + 5 %)."""
    out = []
    for state, cs in by_state.items():
        med, worst = statistics.median(cs), max(cs)
        lim_med, lim_worst = LIMITS[state]
        assert med <= lim_med and worst <= lim_worst, \
            f'{name} {state}: median {med:,.0f}, worst {worst:,} cycles (limits {lim_med:,} / {lim_worst:,})'
        out.append(f'{state} {med:,.0f} / {worst:,} ({len(cs)} turns)')
    print(f'{name} frame cycles, median / worst: ' + ', '.join(out))
    return by_state


if __name__ == '__main__':
    main()
