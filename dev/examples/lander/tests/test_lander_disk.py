#!/usr/bin/env python3
"""LANDER on its disk in a2run: boot, the HUD, the engine key, a landing on
pad B (the lander put 4 rows above it, at rest), R, then a free fall that
crashes. Checks the state bytes and the text the screen shows (the glyph
bytes of the HUD and of the message line on the page on display), then
the cycles a main loop turn costs coasting, with the engine, over the
debris and on the two turns of a zone change (median and worst against
LIMITS).

    python3 tests/test_lander_disk.py      (tests/test_lander.py runs it)
"""
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
LANDER = HERE.parent
ROOT = LANDER.parents[2]
sys.path.insert(0, str(LANDER / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import lander as L  # noqa: E402
import a2test  # noqa: E402
from fonts import glyph  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

DISK = LANDER / 'build/LANDER.dsk'
LBL = LANDER / 'build/lander.lbl'


STATE = ['lv_status', 'lv_fuel', 'lv_pad', 'zone', 'msg']
ROWS = [(base, y) for base in (0x2000, 0x4000) for y in range(16)]
# cycles a main loop turn, median and worst: the measured numbers + 5 %
LIMITS = {'coasting': (14_000, 14_600), 'engine': (17_700, 21_200),
          'debris': (8_300, 18_600), 'zone change': (66_300, 128_100)}


def look(lab):
    """Steps that dump the state bytes, the HUD rows of both pages, pidx."""
    return [lab.peek(n) for n in STATE] + [f'peek:{b + hgr_offset(y):04X}:40' for b, y in ROWS] + \
        [lab.peek('pidx')]


def seen(r, lab, k):
    """The state and the two text lines on display at the k-th look()."""
    st = {n: r.mem(lab[n], 1, k)[0] for n in STATE}
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


def main():
    lab = a2test.labels(LBL)
    land = L.Lander((129, 434, 0, 0)).soa_bytes()
    steps = [lab.until('main', 2000)] + [lab.until('events', 10), lab.until('main', 120)] * 3 + look(lab)  # 0
    steps += ['key:K', lab.until('events', 10)] + [lab.until('main', 10), lab.until('events', 10)] * 8
    steps += [lab.until('main', 120)] + look(lab)                        # 1: the engine
    steps += ['key: ', lab.until('events', 10), lab.until('main', 120)]  # engine cut
    steps += lab.poke('vl_xf', land)      # 4 rows above pad B
    steps += ['wait:150', lab.until('main', 120)] + look(lab)            # 2: landed
    steps += ['key:R', 'wait:4', lab.until('main', 120)] + look(lab)     # 3: again
    steps += ['wait:600', lab.until('main', 120)] + look(lab)            # 4: free fall
    r = a2test.run(str(DISK), steps)
    (s0, t0), (s1, _), (s2, t2), (s3, _), (s4, t4) = (seen(r, lab, k) for k in range(5))
    assert s0 == {'lv_status': 0, 'lv_fuel': L.FUEL, 'lv_pad': 0, 'zone': 0, 'msg': 0}, s0
    assert t0[0].startswith('ALT ') and 'FUEL 250' in t0[0], t0
    assert t0[1] == 'J L:TURN  K:ENGINE  SPACE:CUT  R:RESTART', t0
    assert s1['lv_status'] == 0 and s1['lv_fuel'] < L.FUEL, s1
    assert s2 == {'lv_status': 1, 'lv_fuel': s1['lv_fuel'], 'lv_pad': 2, 'zone': 3, 'msg': 2}, s2
    assert t2[1].startswith('LANDED ON PAD B!') and t2[0].startswith('ALT   0 '), t2
    assert s3 == {'lv_status': 0, 'lv_fuel': L.FUEL, 'lv_pad': 0, 'zone': 0, 'msg': 0}, s3
    assert s4['lv_status'] == 2 and s4['msg'] == 4 and t4[1].startswith('CRASHED!'), (s4, t4)
    print(f'lander disk: boot, HUD "{t0[0]}"; engine: fuel {s1["lv_fuel"]}; above pad B: '
          f'"{t2[1].split("  ")[0]}" (zone {s2["zone"]}, "{t2[0]}"); R; free fall: "{t4[1].split("  ")[0]}"')
    return frame_cycles(lab)


def frame_cycles(lab):
    """A free fall from the start (400 turns: coasting through the four
    zones, the crash, the debris) and 300 turns with K every 10 (the
    engine). The two turns of a zone change (each page cleared and its
    ground drawn) and the crash's turn (its growl) are kept apart."""
    peeks = [('lv_status', 1), ('burn', 1), ('zone', 1), ('dirty', 2)]
    by = {k: [] for k in LIMITS}
    for turns in (frame_turns(lab, [], 400, peeks), frame_turns(lab, [], 300, peeks, 10, 'K')):
        for i in range(2, len(turns)):                 # (the first turns draw the HUD, the message)
            c, s = turns[i]
            p = turns[i - 1][1]
            if s['zone'] != p['zone'] or any(p['dirty']):
                by['zone change'].append(c)
            elif s['lv_status'][0] == L.CRASHED:
                if p['lv_status'][0] == L.CRASHED:
                    by['debris'].append(c)
            elif s['lv_status'][0] == 0:
                by['engine' if s['burn'][0] else 'coasting'].append(c)
    return check_cycles('lander', by)


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
