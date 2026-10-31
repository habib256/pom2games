#!/usr/bin/env python3
"""ROPE on its disk in a2run: boot, the key line, L moves the pin, M lowers
it onto the floor (points in contact), space cuts the weight, R resets.
Checks the state bytes and the text the screen shows (the glyph bytes of
the two text lines on the page on display), and counts the frames drawn
over 10 seconds of swinging and of floor (frames per second).

    python3 tests/test_rope_disk.py      (tests/test_rope.py runs it)
"""
from pathlib import Path
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
    fps_swing = ((s2['frames'] - s1['frames']) & 0xFF) / 10
    fps_floor = ((s4['frames'] - s3['frames']) & 0xFF) / 10
    print(f'rope disk: boot "{t0[0]}"; L: pin {s0["rp_px"]} -> {s1["rp_px"]}; M: pin row {s3["rp_py"]}, '
          f'{g3} points on the floor; space: "{t5[1]}"; R: "{t6[1]}"; '
          f'{fps_swing:.1f} fps swinging, {fps_floor:.1f} fps on the floor')
    return fps_swing, fps_floor


if __name__ == '__main__':
    main()
