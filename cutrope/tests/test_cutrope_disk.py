#!/usr/bin/env python3
"""CUTROPE on its disk in a2run: boot (the counters and the key line read
back from the glyph bytes), level 1's solution keyed at its tick (key 1 at
tick 45: the candy's trace every 5 ticks and the final state == the model,
the frog reached, 3 stars), N to level 2 and its solution (key 2 at tick 6,
key 1 at tick 105: the three stars, == the model), N to level 3 and an
early second cut (the candy on the spikes: LOST, a candy fewer, == the
model), R (the level again), the cursor moved by I and J with space held
across a rope (cut), the stick moving the cursor and button 0 cutting;
then the cycles a tick's work costs (main to pace) on each level and once
frozen with the jingle (median and worst against LIMITS), the bench (one
10-link rope and two of 6: measured, reported), the pacing (every flip of
the levels' ticks 34,060 cycles apart, in the vertical blank), and a run
with vapor_count failing (the marker taken away: no floating bus): the
game runs unpaced.

    python3 tests/test_cutrope_disk.py      (tests/test_cutrope.py runs it)
    python3 tests/test_cutrope_disk.py --fit   the pace estimate's terms
"""
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
ROOT = GAME.parent
sys.path.insert(0, str(GAME / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import cutrope as C  # noqa: E402
import a2test  # noqa: E402
from fonts import glyph  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

DISK = ROOT / 'dist/CUTROPE.dsk'
LBL = GAME / 'build/cutrope.lbl'
STATE = ['level', 'candies', 'cur_x', 'cur_y', 'frames']
GAME_STATE = ['cr_state', 'cr_on', 'cr_stars', 'cr_nstar', 'cr_ev']   # one block
# cycles of a tick's work (main to pace), median and worst: the measured numbers + 5 %
LIMITS = {'level 1': (20_550, 27_100), 'level 2': (28_450, 30_850), 'level 3': (31_700, 32_700),
          'frozen': (3_900, 25_650)}
FRAME = 17_030                          # cycles a video frame (a2run, NTSC)
TICK = C.TICK_FRAMES * FRAME            # a tick: 34,060 cycles
NSNAP = 10 * C.NPTS                     # the points' bytes (vl_xf..vl_oyh)


def look(lab):
    return [lab.peek(n) for n in STATE] + [lab.peek('vl_xf', NSNAP), lab.peek('vl_pin', C.NPTS),
                                         lab.peek('cr_state', 5), lab.peek('vl_gnd'), lab.peek('vl_sgi')] + \
        [f'peek:{b + hgr_offset(y):04X}:40' for b in (0x2000, 0x4000) for y in range(16)] + [lab.peek('pidx')]


def seen(r, lab, k):
    """The k-th look(): state bytes, the model's snapshot bytes, the two
    text lines of the page on display."""
    st = {n: r.mem(lab[n], 1, k)[0] for n in STATE}
    st.update(zip(GAME_STATE, r.mem(lab['cr_state'], 5, k)))
    snap = r.mem(lab['vl_xf'], NSNAP, k) + r.mem(lab['vl_pin'], C.NPTS, k) + r.mem(lab['cr_state'], 5, k) + \
        r.mem(lab['vl_gnd'], 1, k) + r.mem(lab['vl_sgi'], 1, k)
    page = r.mem(lab['pidx'], 1, k)[0]
    rows = [r.mem(0x2000 + 0x2000 * page + hgr_offset(y), 40, k) for y in range(16)]
    lines = []
    for line in range(2):
        s = ''
        for col in range(40):
            cell = [rows[8 * line + y][col] for y in range(8)]
            s += next((chr(c) for c in range(0x20, 0x60) if glyph(c) == cell), '?')
        lines.append(s.rstrip())
    return st, bytes(snap), lines


def keyed(lab, cuts, ticks, every=5):
    """Steps playing `ticks` ticks from a main entry: the key of each cut
    queued just before its tick's input, the candy (vl_xl, vl_yh of point 0)
    peeked every `every` ticks. -> steps, the ticks peeked."""
    cuts = dict(cuts)
    steps, at = [], []
    for t in range(ticks):
        if t in cuts:
            steps.append('press:' + str(cuts[t]))
        if t % every == 0:
            steps += [lab.peek('vl_xl', 1), lab.peek('vl_yh', 1)]
            at.append(t)
        steps += [lab.until('flip', 10), lab.until('main', 10)]
    return steps, at


def trace_of(r, lab, at, first):
    """The candy's (x, y) peeked by keyed(), from the first'th peek of vl_xl."""
    return [(r.mem(lab['vl_xl'], 1, first + i)[0], r.mem(lab['vl_yh'], 1, first + i)[0]) for i in range(len(at))]


def model_trace(level, cuts, at):
    g, cuts, out = C.Game(level), {t: 1 << (k - 1) for t, k in cuts}, []
    for t in range(max(at) + 1):
        if t in at:
            out.append(((g.x[0] >> 8) & 0xFF, (g.y[0] >> 8) & 0xFF))
        g.tick(cuts.get(t, 0))
    return out


def model_end(level, cuts, ticks=400):
    g, _, _ = C.play(level, [(t, 1 << (k - 1)) for t, k in cuts], ticks)
    g.tick()                            # frozen: only the events cleared
    return g


def main():
    lab = a2test.labels(LBL)
    sol = [[(t, m.bit_length()) for t, m in s] for s in C.SOLUTIONS]
    boot = a2test.run(str(DISK), [lab.until('main', 2000), 'wait:10'] + look(lab))
    st0, _, tx0 = seen(boot, lab, 0)                                                 # boot
    steps = [lab.until('main', 2000)]
    s1, at1 = keyed(lab, sol[0], 100)
    steps += s1 + ['wait:20'] + look(lab)                                             # 1: level 1 won
    steps += ['key:N', lab.until('main', 200)]
    s2, at2 = keyed(lab, sol[1], 160)
    steps += s2 + ['wait:20'] + look(lab)                                             # 2: level 2 won
    steps += ['key:N', lab.until('main', 200)]
    lost = [(4, 1), (20, 2)]
    s3, at3 = keyed(lab, lost, 120)
    steps += s3 + ['wait:20'] + look(lab)                                             # 3: level 3 lost
    steps += ['key:R', 'wait:30'] + look(lab)                                         # 4: R
    steps += ['key:I', 'wait:14', 'key:I', 'wait:14', 'key:I', 'wait:14'] + look(lab)   # 5: I x 3
    steps += ['key: ', 'wait:2', 'key:J', 'wait:20'] + look(lab)                                # 6: cursor cut
    steps += ['joy:-1,0', 'wait:20', 'joy:0,0', 'wait:4'] + look(lab)                 # 7: the stick
    steps += ['btn:0,1', 'joy:0,-1', 'wait:30', 'btn:0,0', 'joy:0,0', 'wait:4'] + look(lab)  # 8: button
    r = a2test.run(str(DISK), steps, timeout=300)
    (st1, sn1, tx1), (st2, sn2, tx2), (st3, sn3, tx3), (st4, _, tx4), (st5, _, _), \
        (st6, _, _), (st7, _, _), (st8, _, _) = (seen(r, lab, k) for k in range(8))
    assert tx0 == ['CUTROPE  LEVEL 1  STARS 0/3  CANDIES 5', '1-3: CUT  SPACE+IJKL/STICK: CUT  R  ESC'], tx0
    assert st0['cr_state'] == C.PLAY and st0['cr_on'] == 1 and st0['level'] == 0, st0
    # level 1: the trace and the end == the model
    tr1, want1 = trace_of(r, lab, at1, 0), model_trace(0, sol[0], at1)
    assert tr1 == want1, f'level 1 trace\n  6502  {tr1}\n  model {want1}'
    g1 = model_end(0, sol[0])
    assert sn1 == g1.state_bytes() and st1['cr_state'] == C.WON and st1['cr_nstar'] == 3, (st1, g1.state)
    assert tx1 == ['CUTROPE  LEVEL 1  STARS 3/3  CANDIES 5', 'YUM!  N: NEXT LEVEL   R: PLAY AGAIN'], tx1
    # level 2: the stars == the model
    tr2, want2 = trace_of(r, lab, at2, len(at1)), model_trace(1, sol[1], at2)
    assert tr2 == want2, f'level 2 trace\n  6502  {tr2}\n  model {want2}'
    g2 = model_end(1, sol[1])
    assert sn2 == g2.state_bytes() and st2['cr_state'] == C.WON and st2['cr_stars'] == 7, (st2, g2.stars)
    assert tx2[0] == 'CUTROPE  LEVEL 2  STARS 3/3  CANDIES 5', tx2
    # level 3: on the spikes
    tr3, want3 = trace_of(r, lab, at3, len(at1) + len(at2)), model_trace(2, lost, at3)
    assert tr3 == want3, f'level 3 trace\n  6502  {tr3}\n  model {want3}'
    g3 = model_end(2, lost)
    assert sn3 == g3.state_bytes() and st3['cr_state'] == C.LOST and g3.gnd and g3.lv.segs[g3.sgi][0] == 1, st3
    assert st3['candies'] == C.CANDIES - 1 and tx3[1] == 'CANDY LOST!   R: TRY AGAIN', (st3, tx3)
    assert st4['cr_state'] == C.PLAY and st4['level'] == 2 and st4['cr_on'] == 3 and \
        tx4[0] == 'CUTROPE  LEVEL 3  STARS 0/3  CANDIES 4', (st4, tx4)
    # the cursor: I x 3, then space + J across the right rope (x ~113 at row 46)
    assert (st5['cur_x'], st5['cur_y']) == (st4['cur_x'], st4['cur_y'] - 54), (st4, st5)
    assert st6['cur_x'] == st5['cur_x'] - 18 and st6['cr_on'] == 1, st6
    assert st7['cur_x'] < st6['cur_x'] - 20, (st6, st7)
    assert st8['cur_y'] < st7['cur_y'] - 20 and st8['cr_on'] == 0, (st7, st8)
    print(f'cutrope disk: boot "{tx0[0]}"; level 1 key 1 at tick 45: the frog, 3 stars, trace and state == '
          f'model ({len(at1)} points); level 2 keys 2, 1: 3 stars == model; level 3 too early: '
          f'"{tx3[1]}", {st3["candies"]} candies, == model; R: level 3 again; the cursor ({st4["cur_x"]}, '
          f'{st4["cur_y"]}) -> ({st5["cur_x"]}, {st5["cur_y"]}), space + J cut rope 2; the stick moved it, '
          f'button 0 cut rope 1')
    unpaced(lab)
    return frame_cycles(lab)


def frame_cycles(lab):
    """On each level: the solution's cuts, the stars, the frog and the
    jingle (frozen); levels 2 and 3 left hanging (every link on): every
    tick shorter than 2 video frames, every flip 34,060 cycles from the
    last one. Then the bench, measured and reported."""
    peeks = [('cr_state', 1), ('frozen', 1), ('tune_ptr', 2)]
    flips, by = [], {'level 1': [], 'level 2': [], 'level 3': [], 'frozen': []}
    runs = [(k, {t: str(m.bit_length()) for t, m in sol}, 210) for k, sol in enumerate(C.SOLUTIONS)]
    runs += [(1, {}, 150), (2, {}, 150)]                    # two ropes hanging: all links on
    for k, keys, n in runs:
        pre = [lab.poke('level', k), 'key:R']
        ts = frame_turns(lab, pre, n, peeks, keys)
        flips += ts
        by[f'level {k + 1}'] += [t['work'] for t in ts if t['st']['cr_state'][0] == C.PLAY]
        by['frozen'] += [t['work'] for t in ts if t['st']['frozen'][0] >= 3]
    check_cadence('cutrope', flips, [], TICK, share=1.0)
    bench = frame_turns(lab, [lab.poke('level', C.BENCH_LEVEL), 'key:R'], 120, peeks, {80: '2'})
    b3 = [t['work'] for t in bench[2:80]]
    b2 = [t['work'] for t in bench[82:]]
    one = frame_turns(lab, [lab.poke('level', C.BENCH_LEVEL), 'key:R'], 100, peeks, {5: '2', 8: '3'})
    b1 = [t['work'] for t in one[20:]]
    print(f'cutrope bench (10 + 6 + 6 links, not paced to 30 Hz): work {statistics.median(b3):,.0f} median, '
          f'{max(b3):,} worst; one 6-link rope cut (10 + 6): {statistics.median(b2):,.0f} / {max(b2):,}; '
          f'the 10-link rope alone: {statistics.median(b1):,.0f} / {max(b1):,}; '
          f'video frames per tick {sorted({round(t["flip"] / FRAME) for t in bench[2:] + one[20:]})}')
    return check_cycles('cutrope', by)


def frame_turns(lab, pre, n, peeks, keys=None):
    """n ticks after the steps pre: [{'work': cycles from main to pace
    (input, tick, events, a page drawn), 'flip': cycles from the last flip
    to this one, 'at': the cycle of this flip, 'st': {name: bytes} peeked
    after it}]; keys = {tick: key} queued before that tick's input."""
    keys = keys or {}
    steps = [lab.until('main', 2000)] + pre + [lab.until('flip', 600)]
    for i in range(n):
        if i in keys:
            steps.append('press:' + keys[i])
        steps += [lab.until('main', 600), lab.until('pace', 600), lab.until('flip', 600)]
        steps += [lab.peek(name, ln) for name, ln in peeks]
    r = a2test.run(str(DISK), steps, timeout=600)
    cyc, rows, k = r.cycles[-(3 * n + 1):], r.rows[-n * len(peeks):], len(peeks)
    return [{'work': cyc[3 * i + 2] - cyc[3 * i], 'flip': cyc[3 * i + 3] - cyc[3 * i], 'at': cyc[3 * i + 3],
             'st': {name: rows[i * k + j][1] for j, (name, _) in enumerate(peeks)}} for i in range(n)]


def check_cadence(name, flips, out, tick, share=0.98):
    """The pacing: the flips but those in out `tick` cycles apart to a poll
    (13 cycles), share of them at least; and every flip in the vertical
    blank: the cycle of the flip label modulo a frame (a2run's frames start
    at cycle 0: line = cycle // 65) on lines 192..261."""
    keep = [t for t in flips if t not in out]
    exact = sum(1 for t in keep if abs(t['flip'] - tick) <= 13)
    hist = {}
    for t in flips:
        f = round(t['flip'] / FRAME)
        hist[f] = hist.get(f, 0) + 1
    lines = sorted({t['at'] % FRAME // 65 for t in flips})
    assert exact >= share * len(keep), f'{name}: {exact} of {len(keep)} flips {tick:,} cycles apart {hist}'
    assert all(192 <= ln <= 261 for ln in lines), f'{name}: flips on lines {lines}'
    print(f'{name} cadence: {exact} of {len(keep)} flips {tick:,} cycles apart (+-13; {len(out)} left out), '
          f'video frames per flip {dict(sorted(hist.items()))}, every flip in the vertical blank '
          f'(lines {lines[0]}-{lines[-1]})')
    return exact, len(keep)


def check_cycles(name, by_state):
    """Median and worst cycles of a tick's work (main to pace) in each
    state against LIMITS (the measured numbers + 5 %)."""
    out = []
    for state, cs in by_state.items():
        med, worst = statistics.median(cs), max(cs)
        lim_med, lim_worst = LIMITS[state]
        out.append(f'{state} {med:,.0f} / {worst:,} ({len(cs)} ticks)')
        assert med <= lim_med and worst <= lim_worst, \
            f'{name} {state}: median {med:,.0f}, worst {worst:,} cycles (limits {lim_med:,} / {lim_worst:,})'
    print(f'{name} work cycles a tick, median / worst: ' + ', '.join(out))
    return by_state


FIT_TERMS = ['EST_BASE', 'EST_LINK', 'EST_DIGIT', 'EST_PHYS', 'EST_CUT', 'EST_STAR', 'EST_TUNE', 'EST_IDLE',
             'EST_STARS', 'EST_MSG']


def fit(lab):
    """--fit: the pace estimate's terms (src/cutrope.s EST_*) by least
    squares on the work of ~1,600 ticks (the solutions, early and late cuts,
    hanging): a tick's features are 1, nlink, tkd and the 7 tkf flags."""
    peeks = [('nlink', 1), ('tkf', 1), ('tkd', 1)]
    runs = [(k, {t: str(m.bit_length()) for t, m in sol}) for k, sol in enumerate(C.SOLUTIONS)]
    runs += [(0, {20: '1'}), (1, {30: '2', 60: '1'}), (2, {4: '1', 20: '2'}), (2, {10: '2', 90: '1'}), (1, {})]
    rows = []
    for k, keys in runs:
        for t in frame_turns(lab, [lab.poke('level', k), 'key:R'], 200, peeks, keys)[1:]:
            f = t['st']['tkf'][0]
            rows.append(([1, t['st']['nlink'][0], t['st']['tkd'][0]] + [(f >> b) & 1 for b in range(7)], t['work']))
    used = [j for j in range(len(FIT_TERMS)) if j == 0 or any(x[j] for x, _ in rows)]
    m = [[sum(x[i] * x[j] for x, _ in rows) for j in used] + [sum(x[i] * w for x, w in rows)] for i in used]
    for i in range(len(used)):                      # Gauss-Jordan on the normal equations
        p = max(range(i, len(used)), key=lambda r: abs(m[r][i]))
        m[i], m[p] = m[p], m[i]
        for r in range(len(used)):
            if r != i:
                f = m[r][i] / m[i][i]
                m[r] = [a - f * b for a, b in zip(m[r], m[i])]
    coef = {FIT_TERMS[used[i]]: m[i][-1] / m[i][i] for i in range(len(used))}
    res = [w - sum(coef.get(FIT_TERMS[j], 0) * x[j] for j in range(len(FIT_TERMS))) for x, w in rows]
    print('pace estimate fit: ' + ', '.join(f'{k} {v:,.0f}' for k, v in coef.items()) +
          f'; {len(rows)} ticks, residuals {min(res):,.0f} .. {max(res):,.0f} (half a frame: 8,515)')


def unpaced(lab):
    """Without the marker the game runs unpaced (a flip each main loop
    turn: more than 60 in 120 video frames) and L still moves the cursor."""
    marks = [f'poke:{base + k:04X}:00' for base in (0x3FD0, 0x5FD0) for k in range(24)]
    steps = [lab.until('vapor_pace_init', 2500)] + marks + [
        lab.until('main', 600), lab.peek('pace_ok'), lab.peek('frames', 2), 'wait:120', lab.peek('frames', 2),
        lab.peek('cur_x'), 'key:L', 'wait:10', lab.peek('cur_x')]
    r = a2test.run(str(DISK), steps)
    f0, f1 = (int.from_bytes(r.mem(lab['frames'], 2, k), 'little') for k in range(2))
    ok, n = r.mem(lab['pace_ok'], 1)[0], (f1 - f0) & 0xFFFF
    x0, x1 = r.mem(lab['cur_x'], 1, 0)[0], r.mem(lab['cur_x'], 1, 1)[0]
    assert ok == 0 and n > 60 and x1 == x0 + 18, (ok, n, x0, x1)
    print(f'cutrope without the marker (no floating bus): unpaced (pace_ok 0), {n} flips in 120 video frames; '
          f'L: cursor {x0} -> {x1}')


if __name__ == '__main__':
    if '--fit' in sys.argv:
        fit(a2test.labels(LBL))
    else:
        main()
