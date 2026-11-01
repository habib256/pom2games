#!/usr/bin/env python3
"""LANDER on its disk in a2run: boot, the HUD, the engine key, a landing on
pad B (the lander put 4 rows above it, at rest), R, then a free fall that
crashes. Checks the state bytes and the text the screen shows (the glyph
bytes of the HUD and of the message line on the page on display), then
the cycles a tick's work costs (main to pace) coasting, with the engine,
over the debris and on the two ticks of a zone change (median and worst
against LIMITS), the pacing (a flip every 2 video frames, 34,060 cycles to
a poll, every flip in the vertical blank), and a run with vapor_count
failing (the marker taken away before it: what a machine without a
floating bus sees): the game runs unpaced.

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
# cycles of a tick's work (main to pace), median and worst: the measured numbers + 5 %
LIMITS = {'coasting': (14_000, 14_800), 'engine': (18_100, 21_000),
          'debris': (10_400, 17_000), 'zone change': (67_100, 129_100)}
FRAME = 17_030                          # cycles a video frame (a2run, NTSC)
TICK = L.TICK_FRAMES * FRAME            # a tick: 34,060 cycles


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
    unpaced(lab)
    return frame_cycles(lab)


def frame_cycles(lab):
    """A free fall from the start (400 ticks: coasting through the four
    zones, the crash, the debris) and 300 ticks with K every 10 (the
    engine). The two ticks of a zone change (each page cleared and its
    ground drawn) and the crash's tick (its growl) are kept apart: they
    take more than a tick (4 to 8 video frames for a zone change, 10 for
    the growl), and the cadence check leaves them out."""
    peeks = [('lv_status', 1), ('burn', 1), ('zone', 1), ('dirty', 2)]
    by = {k: [] for k in LIMITS}
    flips, out = [], []
    for turns in (frame_turns(lab, [], 400, peeks), frame_turns(lab, [], 300, peeks, 10, 'K')):
        for i in range(2, len(turns)):                 # (the first ticks draw the HUD, the message)
            t = turns[i]
            s, p = t['st'], turns[i - 1]['st']
            flips.append(t)
            if s['zone'] != p['zone'] or any(p['dirty']):
                by['zone change'].append(t['work'])
                out.append(t)
            elif s['lv_status'][0] == L.CRASHED:
                if p['lv_status'][0] == L.CRASHED:
                    by['debris'].append(t['work'])
                else:
                    out.append(t)                      # the crash: the growl
            elif s['lv_status'][0] == 0:
                by['engine' if s['burn'][0] else 'coasting'].append(t['work'])
    check_cadence('lander', flips, out, TICK)
    return check_cycles('lander', by)


def frame_turns(lab, pre, n, peeks, keyevery=0, key=''):
    """n ticks after the steps pre: [{'work': cycles from main to pace
    (input, tick, events, a page drawn), 'flip': cycles from the last flip
    to this one, 'at': the cycle of this flip, 'st': {name: bytes} peeked
    after it}]."""
    steps = [lab.until('main', 2000)] + pre + [lab.until('flip', 600)]
    for i in range(n):
        if keyevery and i % keyevery == 0:
            steps.append('press:' + key)
        steps += [lab.until('main', 600), lab.until('pace', 600), lab.until('flip', 600)]
        steps += [lab.peek(name, ln) for name, ln in peeks]
    r = a2test.run(str(DISK), steps, timeout=600)
    cyc, rows, k = r.cycles[-(3 * n + 1):], r.rows[-n * len(peeks):], len(peeks)
    return [{'work': cyc[3 * i + 2] - cyc[3 * i], 'flip': cyc[3 * i + 3] - cyc[3 * i], 'at': cyc[3 * i + 3],
             'st': {name: rows[i * k + j][1] for j, (name, _) in enumerate(peeks)}} for i in range(n)]


def check_cadence(name, flips, out, tick, share=0.98):
    """The pacing: the flips but those in out (work longer than a tick)
    `tick` cycles apart to a poll (13 cycles), share of them at least; and
    every flip in the vertical blank: the cycle of the flip label modulo a
    frame (a2run's frames start at cycle 0: line = cycle // 65) on lines
    192..261, after the last line shown (the page switch follows within a
    few cycles; row 191 holds the marker on both pages anyway)."""
    keep = [t for t in flips if t not in out]
    exact = sum(1 for t in keep if abs(t['flip'] - tick) <= 13)
    hist = {}
    for t in flips:
        f = round(t['flip'] / FRAME)
        hist[f] = hist.get(f, 0) + 1
    lines = sorted({t['at'] % FRAME // 65 for t in flips})
    assert exact >= share * len(keep), f'{name}: {exact} of {len(keep)} flips {tick:,} cycles apart'
    assert all(192 <= ln <= 261 for ln in lines), f'{name}: flips on lines {lines}'
    print(f'{name} cadence: {exact} of {len(keep)} flips {tick:,} cycles apart (+-13; {len(out)} left out: '
          f'work longer than a tick), video frames per flip {dict(sorted(hist.items()))}, '
          f'every flip in the vertical blank (lines {lines[0]}-{lines[-1]})')
    return exact, len(keep)


def check_cycles(name, by_state):
    """Median and worst cycles of a tick's work (main to pace) in each
    state against LIMITS (the measured numbers + 5 %)."""
    out = []
    for state, cs in by_state.items():
        med, worst = statistics.median(cs), max(cs)
        lim_med, lim_worst = LIMITS[state]
        assert med <= lim_med and worst <= lim_worst, \
            f'{name} {state}: median {med:,.0f}, worst {worst:,} cycles (limits {lim_med:,} / {lim_worst:,})'
        out.append(f'{state} {med:,.0f} / {worst:,} ({len(cs)} ticks)')
    print(f'{name} work cycles a tick, median / worst: ' + ', '.join(out))
    return by_state


def unpaced_steps(lab, key, after=30):
    """vapor_count failing: the marker cleared just before vapor_pace_init
    (a machine without a floating bus never reads it). Steps: pace_ok,
    frames, 120 video frames, frames, the key, `after` frames."""
    marks = [f'poke:{base + k:04X}:00' for base in (0x3FD0, 0x5FD0) for k in range(24)]
    return [lab.until('vapor_pace_init', 2500)] + marks + [
        lab.until('main', 600), lab.peek('pace_ok'), lab.peek('frames', 2), 'wait:120', lab.peek('frames', 2),
        'key:' + key, f'wait:{after}']


def unpaced_flips(r, lab):
    """pace_ok and the flips in the 120 video frames of unpaced_steps."""
    f0, f1 = (int.from_bytes(r.mem(lab['frames'], 2, k), 'little') for k in range(2))
    return r.mem(lab['pace_ok'], 1)[0], (f1 - f0) & 0xFFFF


def unpaced(lab):
    """Without the marker the game runs unpaced (a flip each main loop
    turn: more than 60 in 120 video frames) and the engine still burns
    fuel."""
    r = a2test.run(str(DISK), unpaced_steps(lab, 'K') + [lab.peek('lv_fuel')])
    ok, n = unpaced_flips(r, lab)
    fuel = r.mem(lab['lv_fuel'], 1)[0]
    assert ok == 0 and n > 60 and fuel < L.FUEL, (ok, n, fuel)
    print(f'lander without the marker (no floating bus): unpaced (pace_ok 0), {n} flips in 120 video frames; '
          f'K: fuel {fuel}')


if __name__ == '__main__':
    main()
