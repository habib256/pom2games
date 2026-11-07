#!/usr/bin/env python3
"""CUTROPE on its disk in a2run.

Run 1 (a copy of the disk): boot to the menu (the title, no star, level 1
chosen, 2 and 3 locked: read back from the glyph bytes); space: level 1's
solution keyed at its tick (the candy's trace every 5 ticks and the final
state == the model, the frog reached, 3 stars, the counters); N (the stars
written to CUTSAVE) to level 2 and its solution (== the model); N to level
3 and an early second cut (the candy on the spikes: LOST, == the model); R
(the level again); the cursor moved by I and J with space held across a
rope (cut), the stick moving the cursor and button 0 cutting; ESC: the menu
with 6 stars, levels 1-2 won, 3 chosen, 4 locked; the disk written.
Run 2 (that disk): CUTSAVE read at boot (the same menu); a bubble level, a
cushion level and a level with two trampolines played from their solutions
(== the model, 3 stars).
Then the cycles a tick's work costs (main to pace) on levels 1-3, a bubble
and a cushion level and once frozen with the jingle (median and worst
against LIMITS), every level's worst under the tick (--all: every level,
else a sample), the bench (one 10-link rope and two of 6: measured,
reported), the pacing (every flip 34,060 cycles apart, in the vertical
blank), and a run with vapor_count failing (the marker taken away: no
floating bus): the game runs unpaced.

    python3 tests/test_cutrope_disk.py [--all]   (tests/test_cutrope.py runs it)
    python3 tests/test_cutrope_disk.py --fit     the pace estimate's terms
"""
from pathlib import Path
import shutil
import statistics
import sys
import tempfile

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
ROOT = GAME.parent
sys.path.insert(0, str(GAME / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import cutrope as C  # noqa: E402
import a2test  # noqa: E402
import dos33  # noqa: E402
from fonts import glyph  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

SRC = ROOT / 'dist/CUTROPE.dsk'
DISK = SRC                              # a copy while the tests run (on_copy)
LBL = GAME / 'build/cutrope.lbl'
STATE = ['level', 'total', 'cur_x', 'cur_y', 'frames']
NSTATE = 6 + C.NCUSH                    # cr_state .. cr_cool
GAME_STATE = ['cr_state', 'cr_on', 'cr_stars', 'cr_nstar', 'cr_ev', 'cr_bub']   # one block
BUBBLE = next(k for k, lv in enumerate(C.LEVELS) if any(m == C.M_POP for _, m in lv['solution']))
SPIKES = next(k for k, lv in enumerate(C.LEVELS) if lv['name'] == 'SPIKES')
TRAMP = next(k for k, lv in enumerate(C.LEVELS) if sum(sg[4] == C.SEG_TRAMP for sg in lv['segs']) > 1)
CUSHION = next(k for k, lv in enumerate(C.LEVELS) if lv.get('cushions') and not lv.get('bubble'))
# cycles of a tick's work (main to pace), median and worst: the measured numbers + 5 %
LIMITS = {'level 1': (20_300, 26_820), 'two ropes': (28_080, 30_470), 'spikes': (31_320, 32_280),
          'bubble': (7_920, 18_800), 'cushion': (15_170, 22_040), 'trampolines': (7_630, 17_150), 'frozen': (3_850, 25_950)}
WORST = 33_000                          # any level: a tick's work (flips at 34,060)
FRAME = 17_030                          # cycles a video frame (a2run, NTSC)
# two flips' distance: a poll is 13 cycles, but once in 256 polls vapor_sync's
# @hit_wrap path samples 1 cycle early and returns 2 later (its DEY): +-15
POLL_JITTER = 15
TICK = C.TICK_FRAMES * FRAME            # a tick: 34,060 cycles
NSNAP = 10 * C.NPTS                     # the points' bytes (vl_xf..vl_oyh)


def look(lab):
    return [lab.peek(n) for n in STATE] + [lab.peek('vl_xf', NSNAP), lab.peek('vl_pin', C.NPTS),
                                         lab.peek('cr_state', NSTATE), lab.peek('vl_gnd'), lab.peek('vl_sgi')] + \
        [f'peek:{b + hgr_offset(y):04X}:40' for b in (0x2000, 0x4000) for y in range(16)] + [lab.peek('pidx')]


MENU_ROWS = [8, 24] + [48 + 16 * r for r in range((C.NLEVEL + 4) // 5)]


def look_menu(lab):
    # (from the byte before each row: not the addresses look() reads, whose
    # k-th peek seen() takes)
    return [lab.peek('best', C.NLEVEL), f'peek:{lab["total"] - 2:04X}:3', lab.peek('sel')] + \
        [f'peek:{0x1FFF + hgr_offset(sl + y):04X}:41' for sl in MENU_ROWS for y in range(8)]


def text_line(rows):
    """8 rows of 40 bytes -> the line of text (bbfont glyphs)."""
    return ''.join(next((chr(c) for c in range(0x20, 0x60) if glyph(c) == [rows[y][col] for y in range(8)]), '?')
                   for col in range(40)).rstrip()


def seen_menu(r, lab, k):
    """The k-th look_menu(): best, total, the choice, the lines of text."""
    best, total, sel = list(r.mem(lab['best'], C.NLEVEL, k)), r.mem(lab['total'] - 2, 3, k)[2], r.mem(lab['sel'], 1, k)[0]
    lines = [text_line([r.mem(0x1FFF + hgr_offset(sl + y), 41, k)[1:] for y in range(8)]) for sl in MENU_ROWS]
    return best, total, sel, lines


def seen(r, lab, k):
    """The k-th look(): state bytes, the model's snapshot bytes, the two
    text lines of the page on display."""
    st = {n: r.mem(lab[n], 1, k)[0] for n in STATE}
    st.update(zip(GAME_STATE, r.mem(lab['cr_state'], len(GAME_STATE), k)))
    snap = r.mem(lab['vl_xf'], NSNAP, k) + r.mem(lab['vl_pin'], C.NPTS, k) + r.mem(lab['cr_state'], NSTATE, k) + \
        r.mem(lab['vl_gnd'], 1, k) + r.mem(lab['vl_sgi'], 1, k)
    page = r.mem(lab['pidx'], 1, k)[0]
    rows = [r.mem(0x2000 + 0x2000 * page + hgr_offset(y), 40, k) for y in range(16)]
    return st, bytes(snap), [text_line(rows[0:8]), text_line(rows[8:16])]


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


def to_game(lab):
    """From boot: the menu, space (its choice), the first tick's main."""
    return [lab.until('menu_idle', 3000), 'key: ', lab.until('main', 300)]


def cells(best):
    """The menu's grid lines for these results, nothing chosen."""
    out = []
    for k in range(C.NLEVEL):
        open_ = k == 0 or best[k - 1]
        n = max(best[k] - 1, 0)
        out.append(f' {k + 1:02} ' + ('*' * n + '.' * (3 - n) if open_ else '---') + ' ')
    return [''.join(out[r:r + 5]).rstrip() for r in range(0, C.NLEVEL, 5)]


def chosen(lines, sel):
    """lines with cell sel in brackets."""
    r, c = divmod(sel, 5)
    row = lines[r].ljust(40)
    lines = list(lines)
    lines[r] = (row[:8 * c] + '[' + row[8 * c + 1:8 * c + 7] + ']' + row[8 * c + 8:]).rstrip()
    return lines


def menu_ok(seen, best, sel):
    got_best, total, got_sel, lines = seen
    stars = sum(max(b - 1, 0) for b in best)
    want = ['C U T R O P E'.center(39).rstrip(), f'STARS {stars:2}/{3 * C.NLEVEL:02}'.rjust(25).rstrip()]
    want += chosen(cells(best), sel)
    assert got_best == best and total == stars and got_sel == sel, (got_best, total, got_sel)
    assert lines == want, '\n'.join(f'{a!r}\n{b!r}' for a, b in zip(lines, want) if a != b)


def on_copy(fn, *args):
    """fn(*args) with DISK a temporary copy of dist/CUTROPE.dsk: the
    emulator writes the disk back and the game writes CUTSAVE, never into
    dist/."""
    global DISK
    with tempfile.TemporaryDirectory(prefix='cutrope-') as work:
        DISK = Path(work) / 'CUTROPE.dsk'
        shutil.copyfile(SRC, DISK)
        try:
            return fn(*args)
        finally:
            DISK = SRC


def main():
    return on_copy(checks)


def checks():
    lab = a2test.labels(LBL)
    sol = [[(t, m.bit_length()) for t, m in s] for s in C.SOLUTIONS]
    none = [0] * C.NLEVEL
    steps = [lab.until('menu_idle', 3000)] + look_menu(lab) + ['key: ', lab.until('main', 300)]
    s1, at1 = keyed(lab, sol[0], 100)
    steps += s1 + ['wait:20'] + look(lab)                                             # 1: level 1 won
    steps += ['key:N', lab.until('main', 200)]
    s2, at2 = keyed(lab, sol[1], 160)
    steps += s2 + ['wait:20'] + look(lab)                                             # 2: level 2 won
    steps += ['key:N', lab.until('main', 200)]
    s2b, at2b = keyed(lab, sol[2], 170)
    steps += s2b + ['wait:20'] + look(lab)                                            # 2b: level 3 won
    steps += [lab.poke('level', SPIKES), 'key:R', lab.until('main', 200)]
    lost = [(4, 1), (20, 2)]
    s3, at3 = keyed(lab, lost, 120)
    steps += s3 + ['wait:20'] + look(lab)                                             # 3: SPIKES lost
    steps += ['key:R', 'wait:30'] + look(lab)                                         # 4: R
    steps += ['key:I', 'wait:14', 'key:I', 'wait:14', 'key:I', 'wait:14'] + look(lab)   # 5: I x 3
    steps += ['key: ', 'wait:2', 'key:J', 'wait:20'] + look(lab)                                # 6: cursor cut
    steps += ['joy:-1,0', 'wait:20', 'joy:0,0', 'wait:4'] + look(lab)                 # 7: the stick
    steps += ['btn:0,1', 'joy:0,-1', 'wait:30', 'btn:0,0', 'joy:0,0', 'wait:4'] + look(lab)  # 8: button
    with tempfile.TemporaryDirectory(prefix='cutrope-') as tmp:
        saved = Path(tmp) / 'saved.dsk'
        steps += ['key:\x1b', lab.until('menu_idle', 600)] + look_menu(lab) + [f'dsk:{saved}']
        r = a2test.run(str(DISK), steps, timeout=300)
        m0, m1 = seen_menu(r, lab, 0), seen_menu(r, lab, 1)
        (st1, sn1, tx1), (st2, sn2, tx2), (st2b, sn2b, tx2b), (st3, sn3, tx3), (st4, _, tx4), (st5, _, _), \
            (st6, _, _), (st7, _, _), (st8, _, _) = (seen(r, lab, k) for k in range(9))
        menu_ok(m0, none, 0)
        # level 1: the trace and the end == the model
        tr1, want1 = trace_of(r, lab, at1, 0), model_trace(0, sol[0], at1)
        assert tr1 == want1, f'level 1 trace\n  6502  {tr1}\n  model {want1}'
        g1 = model_end(0, sol[0])
        assert sn1 == g1.state_bytes() and st1['cr_state'] == C.WON and st1['cr_nstar'] == 3, (st1, g1.state)
        assert tx1 == ['CUTROPE  LEVEL  1  STARS 3/3  TOTAL  3', 'YUM!  N: NEXT LEVEL  R: AGAIN  ESC: MENU'], tx1
        # level 2: == the model
        tr2, want2 = trace_of(r, lab, at2, len(at1)), model_trace(1, sol[1], at2)
        assert tr2 == want2, f'level 2 trace\n  6502  {tr2}\n  model {want2}'
        g2 = model_end(1, sol[1])
        assert sn2 == g2.state_bytes() and st2['cr_state'] == C.WON and st2['cr_stars'] == 7, (st2, g2.stars)
        assert tx2[0] == 'CUTROPE  LEVEL  2  STARS 3/3  TOTAL  6', tx2
        tr2b, want2b = trace_of(r, lab, at2b, len(at1) + len(at2)), model_trace(2, sol[2], at2b)
        assert tr2b == want2b, f'level 3 trace\n  6502  {tr2b}\n  model {want2b}'
        g2b = model_end(2, sol[2])
        assert sn2b == g2b.state_bytes() and st2b['cr_nstar'] == 3, st2b
        assert tx2b[0] == 'CUTROPE  LEVEL  3  STARS 3/3  TOTAL  9', tx2b
        # SPIKES: on the spikes
        tr3, want3 = trace_of(r, lab, at3, len(at1) + len(at2) + len(at2b)), model_trace(SPIKES, lost, at3)
        assert tr3 == want3, f'SPIKES trace\n  6502  {tr3}\n  model {want3}'
        g3 = model_end(SPIKES, lost)
        assert sn3 == g3.state_bytes() and st3['cr_state'] == C.LOST and g3.gnd and g3.lv.segs[g3.sgi][0] == 1, st3
        assert tx3[1] == 'CANDY LOST!    R: TRY AGAIN    ESC: MENU', tx3
        assert st4['cr_state'] == C.PLAY and st4['level'] == SPIKES and st4['cr_on'] == 3 and \
            tx4[0] == f'CUTROPE  LEVEL  {SPIKES + 1}  STARS 0/3  TOTAL  9', (st4, tx4)
        # the cursor: I x 3, then space + J across the right rope (x ~113 at row 46)
        assert (st5['cur_x'], st5['cur_y']) == (st4['cur_x'], st4['cur_y'] - 54), (st4, st5)
        assert st6['cur_x'] == st5['cur_x'] - 18 and st6['cr_on'] == 1, st6
        assert st7['cur_x'] < st6['cur_x'] - 20, (st6, st7)
        assert st8['cur_y'] < st7['cur_y'] - 20 and st8['cr_on'] == 0, (st7, st8)
        won = [4, 4, 4] + [0] * (C.NLEVEL - 3)
        menu_ok(m1, won, SPIKES)
        image = saved.read_bytes()
        got = dos33.read_file(image, 'CUTSAVE')
        assert got[:4] == b'CRS1' and list(got[4:4 + C.NLEVEL]) == won, got[:4 + C.NLEVEL]
        print(f'cutrope disk: the menu "{m0[3][0]}"; level 1 key 1 at tick 45: the frog, 3 stars, trace and state '
              f'== model ({len(at1)} points); levels 2 and 3: 3 stars == model; SPIKES too early: '
              f'"{tx3[1]}", == model; R: SPIKES again; the cursor ({st4["cur_x"]}, {st4["cur_y"]}) -> '
              f'({st5["cur_x"]}, {st5["cur_y"]}), space + J cut rope 2; the stick moved it, button 0 cut rope 1; '
              f'ESC: the menu, {m1[1]} stars, "{m1[3][2]}"; CUTSAVE {got[:4].decode()} {list(got[4:8])}...')
        # run 2: the saved disk, a bubble level and a cushion level
        steps = [lab.until('menu_idle', 3000)] + look_menu(lab) + ['key: ', lab.until('main', 300)]
        traces = []
        for k in (BUBBLE, CUSHION, TRAMP):
            keys = [(t, m.bit_length()) for t, m in C.SOLUTIONS[k]]
            steps += [lab.poke('level', k), 'key:R', lab.until('main', 300)]
            sk, at = keyed(lab, keys, C.play(k, C.SOLUTIONS[k])[1] + 20)
            steps += sk + ['wait:20'] + look(lab)
            traces.append((k, keys, at))
        r = a2test.run(str(saved), steps, timeout=300)
        menu_ok(seen_menu(r, lab, 0), won, 3)
        first = 0
        for i, (k, keys, at) in enumerate(traces):
            st, sn, tx = seen(r, lab, i)
            tr, want = trace_of(r, lab, at, first), model_trace(k, keys, at)
            first += len(at)
            assert tr == want, f'level {k + 1} trace\n  6502  {tr}\n  model {want}'
            g = model_end(k, keys)
            assert sn == g.state_bytes() and st['cr_state'] == C.WON and st['cr_nstar'] == 3, (k, st)
        print(f'cutrope disk, saved: the menu again with {m1[1]} stars; level {BUBBLE + 1} (a bubble) and level '
              f'{CUSHION + 1} (cushions), level {TRAMP + 1} (two trampolines): their solutions, 3 stars, == model')
    unpaced(lab)
    return frame_cycles(lab, '--all' in sys.argv)


def frame_cycles(lab, every=False):
    """On level 1, TWO ROPES, SPIKES, a bubble and a cushion level (every
    level with every=True): the solution's keys, the stars, the frog and the
    jingle (frozen); TWO ROPES and SPIKES left hanging (every link on): every tick's
    work under WORST, every flip 34,060 cycles from the last one. Then the
    bench, measured and reported."""
    peeks = [('cr_state', 1), ('frozen', 1), ('tune_ptr', 2)]
    flips, by, worst = [], {k: [] for k in LIMITS}, {}
    names = {0: 'level 1', 2: 'two ropes', SPIKES: 'spikes', BUBBLE: 'bubble', CUSHION: 'cushion',
             TRAMP: 'trampolines'}
    levels = range(C.NLEVEL) if every else sorted(names)
    runs = [(k, {t: str(m.bit_length()) for t, m in C.SOLUTIONS[k]}, C.play(k, C.SOLUTIONS[k])[1] + 60)
            for k in levels]
    runs += [(2, {}, 150), (SPIKES, {}, 150)]               # two ropes hanging: all links on
    for k, keys, n in runs:
        pre = [lab.poke('level', k), 'key:R']
        ts = frame_turns(lab, pre, n, peeks, keys)
        flips += ts
        play = [t['work'] for t in ts if t['st']['cr_state'][0] == C.PLAY]
        worst[k] = max(worst.get(k, 0), max(play))
        if k in names:
            by[names[k]] += play
        by['frozen'] += [t['work'] for t in ts if t['st']['frozen'][0] >= 3]
    check_cadence('cutrope', flips, [], TICK, share=1.0)
    over = {k + 1: w for k, w in worst.items() if w > WORST}
    assert not over, f'cutrope: levels over {WORST:,} cycles a tick: {over}'
    top = max(worst, key=worst.get)
    print(f'cutrope: {len(worst)} levels, every tick under {WORST:,} cycles (the worst: level {top + 1}, '
          f'{worst[top]:,})')
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
    steps = to_game(lab) + pre + [lab.until('flip', 600)]
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
    (POLL_JITTER), share of them at least; and every flip in the vertical
    blank: the cycle of the flip label modulo a frame (a2run's frames start
    at cycle 0: line = cycle // 65) on lines 192..261."""
    keep = [t for t in flips if t not in out]
    exact = sum(1 for t in keep if abs(t['flip'] - tick) <= POLL_JITTER)
    hist = {}
    for t in flips:
        f = round(t['flip'] / FRAME)
        hist[f] = hist.get(f, 0) + 1
    lines = sorted({t['at'] % FRAME // 65 for t in flips})
    assert exact >= share * len(keep), f'{name}: {exact} of {len(keep)} flips {tick:,} cycles apart {hist}'
    assert all(192 <= ln <= 261 for ln in lines), f'{name}: flips on lines {lines}'
    print(f'{name} cadence: {exact} of {len(keep)} flips {tick:,} cycles apart (+-{POLL_JITTER}; {len(out)} left out), '
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
             'EST_STARS', 'EST_MSG', 'EST_BUB']


def fit(lab):
    """--fit: the pace estimate's terms (src/cutrope.s EST_*) by least
    squares on the work of ~1,600 ticks (the solutions, early and late cuts,
    hanging): a tick's features are 1, nlink, tkd and the 7 tkf flags."""
    peeks = [('nlink', 1), ('tkf', 1), ('tkd', 1)]
    runs = [(k, {t: str(m.bit_length()) for t, m in sol}) for k, sol in enumerate(C.SOLUTIONS)]
    runs += [(0, {20: '1'}), (2, {30: '2', 60: '1'}), (SPIKES, {4: '1', 20: '2'}), (SPIKES, {10: '2', 90: '1'}),
             (2, {})]
    runs += [(BUBBLE, {10: '1', 60: '6'}), (CUSHION, {5: '4', 12: '5', 30: '1', 50: '2'})]
    rows = []
    for k, keys in runs:
        for t in frame_turns(lab, [lab.poke('level', k), 'key:R'], 200, peeks, keys)[1:]:
            f = t['st']['tkf'][0]
            rows.append(([1, t['st']['nlink'][0], t['st']['tkd'][0]] + [(f >> b) & 1 for b in range(8)], t['work']))
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
        lab.until('menu_idle', 600), 'key: ', lab.until('main', 600), lab.peek('pace_ok'), lab.peek('frames', 2), 'wait:120', lab.peek('frames', 2),
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
        on_copy(fit, a2test.labels(LBL))
    else:
        main()
