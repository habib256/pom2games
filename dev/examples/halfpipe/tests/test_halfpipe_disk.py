#!/usr/bin/env python3
"""HALFPIPE on its disk in a2run: boot, the HUD and the help line, a minute
of pump key presses (the rider gets above a lip: the AIR counter), the
frame cost, then the rider put upside down over the bottom (a crash: the
message line), R (a new run, score 0). Checks the state bytes and the text
the screen shows (the glyph bytes of the HUD and of the message line on
the page on display), then the cycles a main loop turn costs riding
(median and worst against LIMITS).

    python3 tests/test_halfpipe_disk.py      (tests/test_halfpipe.py runs it)
"""
from pathlib import Path
import statistics
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
# cycles of a tick's work (main to pace), median and worst: the measured numbers + 5 %
LIMITS = {'riding': (17_800, 29_800)}
FRAME = 17_030                          # cycles a video frame (a2run, NTSC)
TICK = H.TICK_FRAMES * FRAME            # a tick: 34,060 cycles


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
    steps += lab.poke('vl_xf', upside_down())               # inverted
    steps += ['wait:70', lab.until('render', 10), lab.until('main', 120)] + look(lab)     # 2: crashed (< AGAIN_T ticks)
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
    unpaced(lab)
    frame_cycles(lab)


def frame_cycles(lab):
    """1,500 ticks pumping (K every 10 ticks: up to the lips, jumps,
    landings that score, with their chime and message): the ticks riding.
    The cadence check leaves out the ticks of a landing that scored (the
    chime: 20,000-60,000 cycles of tones) and of a crash (the growl)."""
    peeks = [('hp_status', 1), ('hp_score', 3)]
    turns = frame_turns(lab, [], 1500, peeks, 10, 'K')[2:]   # (the first ticks draw it all)
    flips, out, riding = [], [], []
    for i in range(1, len(turns)):
        t, p = turns[i], turns[i - 1]
        flips.append(t)
        if t['st']['hp_score'] != p['st']['hp_score'] or t['st']['hp_status'] != p['st']['hp_status']:
            out.append(t)
        elif t['st']['hp_status'][0] == 0:
            riding.append(t['work'])
    check_cadence('halfpipe', flips, out, TICK)
    return check_cycles('halfpipe', {'riding': riding})


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
    return [lab.until('vapor_pace_init', 600)] + marks + [
        lab.until('main', 600), lab.peek('pace_ok'), lab.peek('frames', 2), 'wait:120', lab.peek('frames', 2),
        'key:' + key, f'wait:{after}']


def unpaced_flips(r, lab):
    """pace_ok and the flips in the 120 video frames of unpaced_steps."""
    f0, f1 = (int.from_bytes(r.mem(lab['frames'], 2, k), 'little') for k in range(2))
    return r.mem(lab['pace_ok'], 1)[0], (f1 - f0) & 0xFFFF


def unpaced(lab):
    """Without the marker the game runs unpaced (a flip each main loop
    turn: more than 60 in 120 video frames) and K still pumps."""
    r = a2test.run(str(DISK), unpaced_steps(lab, 'K', 4) + [lab.peek('pump_hold')])
    ok, n = unpaced_flips(r, lab)
    hold = r.mem(lab['pump_hold'], 1)[0]
    assert ok == 0 and n > 60 and hold > 0, (ok, n, hold)
    print(f'halfpipe without the marker (no floating bus): unpaced (pace_ok 0), {n} flips in 120 video frames; '
          f'K: pumping ({hold} ticks left)')


if __name__ == '__main__':
    main()
