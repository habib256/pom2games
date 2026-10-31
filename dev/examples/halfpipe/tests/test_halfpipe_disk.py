#!/usr/bin/env python3
"""HALFPIPE on its disk in a2run: boot, the HUD and the help line, a minute
of pump key presses (the rider gets above a lip: the AIR counter), the
frame cost, then the rider put upside down over the bottom (a crash: the
message line), R (a new run, score 0). Checks the state bytes and the text
the screen shows (the glyph bytes of the HUD and of the message line on
the page on display).

    python3 tests/test_halfpipe_disk.py      (tests/test_halfpipe.py runs it)
"""
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
PIPE = HERE.parent
ROOT = PIPE.parents[2]
sys.path.insert(0, str(PIPE / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import halfpipe as H  # noqa: E402
import a2test  # noqa: E402
from fonts import glyph  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

DISK = PIPE / 'build/HALFPIPE.dsk'
LBL = PIPE / 'build/halfpipe.lbl'
STATE = ['hp_status', 'hp_score', 'hp_score+1', 'hp_score+2', 'air_px', 'msg']
ROWS = [(base, y) for base in (0x2000, 0x4000) for y in range(16)]


def look(lab):
    """Steps that dump the state bytes, the HUD rows of both pages, pidx."""
    out = []
    for n in STATE:
        name, _, off = n.partition('+')
        out.append(lab.peek(name, 1, int(off or 0)))
    return out + [f'peek:{b + hgr_offset(y):04X}:40' for b, y in ROWS] + [lab.peek('pidx')]


def seen(r, lab, k):
    """The state and the two text lines on display at the k-th look()."""
    st = {}
    for n in STATE:
        name, _, off = n.partition('+')
        st[n] = r.mem(lab[name] + int(off or 0), 1, k)[0]
    page = r.mem(lab['pidx'], 1, k)[0]
    rows = [r.mem(0x2000 + 0x2000 * page + hgr_offset(y), 40, k) for y in range(16)]
    lines = []
    for line in range(2):
        s = ''
        for col in range(40):
            cell = [rows[8 * line + y][col] for y in range(8)]
            s += next((chr(c) for c in range(0x20, 0x60) if glyph(c) == cell), '?')
        lines.append(s.rstrip())
    return st, lines


def upside_down():
    """The rider inverted over the middle of the bottom (body below the
    wheels), at rest: it falls on its body."""
    p = H.Rider()
    for i, (x, y) in enumerate([(122, 120), (110, 120), (116, 128)]):
        p.place(i, x << 8, y << 8)
    return p.soa_bytes()


def main():
    lab = a2test.labels(LBL)
    steps = [lab.until('main', 2000)] + [lab.until('render', 10), lab.until('main', 120)] * 3 + look(lab)  # 0
    steps += ['key:K', 'wait:20'] * 120 + [lab.until('render', 10), lab.until('main', 120)] + look(lab)  # 1
    steps += [lab.poke('vl_xf', v, k) for k, v in enumerate(upside_down())]               # inverted
    steps += ['wait:120', lab.until('render', 10), lab.until('main', 120)] + look(lab)    # 2: crashed
    steps += ['key:R', 'wait:6', lab.until('render', 10), lab.until('main', 120)] + look(lab)  # 3: again
    r = a2test.run(str(DISK), steps)
    (s0, t0), (s1, t1), (s2, t2), (s3, t3) = (seen(r, lab, k) for k in range(4))
    assert s0['hp_status'] == 0 and s0['msg'] == 0, s0
    assert t0[0] == 'SCORE 000000  LAST 0000  AIR 000', t0
    assert t0[1] == 'K/SPACE:PUMP  J L:LEAN  R:RESTART', t0
    assert s1['hp_status'] == 0 and s1['air_px'] > 0, s1
    assert s2['hp_status'] == 1 and s2['msg'] == 5 and t2[1].startswith('CRASHED!'), (s2, t2)
    assert s3['hp_status'] == 0 and s3['hp_score'] == 0 and s3['msg'] == 0, s3
    print(f'halfpipe disk: boot, HUD "{t0[0]}"; pumping: score {s1["hp_score+1"]:02X}{s1["hp_score"]:02X}, '
          f'air {s1["air_px"]} px above the lip, "{t1[1]}"; upside down: "{t2[1].split("  ")[0]}"; R: a new run')
    frame_cycles(lab)


def frame_cycles(lab, n=120):
    """Average cycles of a main loop turn (input, tick, events, a page
    drawn), pumping: n turns after 300 of warm-up."""
    steps = [lab.until('main', 2000)] + ['key:K', 'wait:20'] * 30 + [lab.until('main', 120)]
    steps += [lab.until('render', 10), lab.until('main', 10)] * n
    r = a2test.run(str(DISK), steps)
    cyc = [int(v) for v in re.findall(r'cycles=(\d+)', r.out)]
    per = (cyc[-1] - cyc[-1 - 2 * n]) / n
    print(f'halfpipe frame: {per:,.0f} cycles a turn while pumping ({a2test.CPU_HZ / per:.1f} fps, a tick a frame)')
    return per


if __name__ == '__main__':
    main()
