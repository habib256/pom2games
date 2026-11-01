#!/usr/bin/env python3
"""CATAPULT on its disk in a2run: boot, the counters and the key line, the
power and angle keys, a shot fired (the same as the model's: the targets
down agree), the round played to its end (three shots, ROUND OVER), space
for a new round. Checks the state bytes and the text the screen shows (the
glyph bytes of the two text lines on the page on display), the ticks of
the 5 s aiming window (exactly 150: 30 a second), then the cycles a tick's
work costs (main to pace) while aiming and while a shot flies (median and
worst against LIMITS), the pacing (a flip every 2 video frames, 34,060
cycles to a poll, every flip in the vertical blank; the pile-ups whose
work alone outlasts a tick left out, their share printed), and a run with
vapor_count failing (the marker taken away before it: what a machine
without a floating bus sees): the game runs unpaced.

    python3 tests/test_catapult_disk.py      (tests/test_catapult.py runs it)
"""
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
CAT = HERE.parent
ROOT = CAT.parents[2]
sys.path.insert(0, str(CAT / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tools'))
import catapult as C  # noqa: E402
import a2test  # noqa: E402
from fonts import glyph  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

DISK = CAT / 'build/CATAPULT.dsk'
LBL = CAT / 'build/catapult.lbl'
STATE = ['cp_phase', 'cp_shots', 'cp_score', 'cp_power', 'cp_stop', 'frames']
# cycles of a tick's work (main to pace), median and worst: the measured numbers + 5 %
LIMITS = {'aiming': (3_900, 3_900), 'flying': (12_100, 47_300)}
FRAME = 17_030                          # cycles a video frame (a2run, NTSC)
TICK = C.TICK_FRAMES * FRAME            # a tick: 34,060 cycles


def look(lab):
    return [lab.peek(n) for n in STATE] + \
        [f'peek:{b + hgr_offset(y):04X}:40' for b in (0x2000, 0x4000) for y in range(16)] + [lab.peek('pidx')]


def seen(r, lab, k):
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
    steps = [lab.until('main', 2000), 'wait:30'] + look(lab)                    # 0: boot
    steps += ['wait:300'] + look(lab)                                          # 1: 5 s aiming
    steps += ['key:L', 'wait:4'] * 9 + ['key:K', 'wait:4', 'wait:20'] + look(lab)  # 2: power 9, angle 35
    steps += ['key: ', 'wait:60'] + look(lab)                                  # 3: 1 s of the shot
    steps += ['wait:900'] + look(lab)                                          # 4: the shot over
    steps += ['key: ', 'wait:1200', 'key: ', 'wait:1200'] + look(lab)         # 5: shots 2 and 3: over
    steps += ['key: ', 'wait:30'] + look(lab)                                  # 6: a new round
    r = a2test.run(str(DISK), steps, timeout=300)
    (s0, t0), (s1, _), (s2, t2), (s3, _), (s3b, _), (s4, t4), (s5, t5) = (seen(r, lab, k) for k in range(7))
    assert t0 == ['POWER 00  ANGLE 45  SHOTS 03  DOWN 00/6', 'J L:POWER  I K:ANGLE  SPACE:FIRE  R:NEW'], t0
    assert s0['cp_phase'] == C.AIM and s0['cp_shots'] == 3, s0
    aim_ticks = (s1['frames'] - s0['frames']) & 0xFF
    assert aim_ticks == 5 * C.TICK_HZ, aim_ticks                         # 5 s: 150 ticks
    assert s2['cp_power'] == 9 and s2['cp_stop'] == 1 and t2[0].startswith('POWER 09  ANGLE 35'), (s2, t2)
    c, _ = C.play([(9, 1)])                                                     # the model's shot
    assert s3['cp_phase'] == C.FLY, s3
    assert s3b['cp_phase'] == C.AIM and s3b['cp_score'] == c.score and s3b['cp_shots'] == 2, (s3b, c.score)
    assert s4['cp_phase'] == C.OVER and s4['cp_shots'] == 0 and t4[1].startswith(('ROUND OVER', 'ALL SIX')), (s4, t4)
    assert s5['cp_phase'] == C.AIM and s5['cp_shots'] == 3 and s5['cp_score'] == 0, s5
    print(f'catapult disk: boot "{t0[0]}"; power 9, angle 35, fire: {s3b["cp_score"]} down (the model: '
          f'{c.score}); round over: "{t4[1].split("  ")[0]}" {s4["cp_score"]} down; space: a new round; '
          f'5 s aiming: {aim_ticks} ticks')
    unpaced(lab)
    return frame_cycles(lab)


def frame_cycles(lab):
    """Aiming at rest (200 ticks: nothing moves, nothing is drawn but the
    counters that change), then four shots flying (power 9 angle 35, 15
    angle 45, 6 angle 45, 12 angle 25: 600 ticks each, the ticks in FLY).
    The cadence check leaves out the ticks whose work alone outlasts a
    tick (pile-ups: many balls awake, contacts, redrawn): they take 3
    video frames."""
    peeks = [('cp_phase', 1)]
    aim = frame_turns(lab, ['wait:30'], 200, peeks)[2:]          # (the first ticks draw it all)
    fly = []
    for keys in ('LLLLLLLLLK', 'LLLLLLLLLLLLLLLL', 'LLLLLL', 'LLLLLLLLLLLLKKK'):
        fly += frame_turns(lab, ['press:' + keys, 'wait:30', 'press: '], 600, peeks)
    flips = aim + fly
    out = [t for t in flips if t['work'] > TICK - 400]
    check_cadence('catapult', flips, out, TICK)
    print(f'catapult pile-ups: {len(out)} of {len(flips)} ticks ({100 * len(out) / len(flips):.1f} %) work longer '
          f'than a tick (3 video frames)')
    return check_cycles('catapult', {'aiming': [t['work'] for t in aim if t['st']['cp_phase'][0] == C.AIM],
                                     'flying': [t['work'] for t in fly if t['st']['cp_phase'][0] == C.FLY]})


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
    turn: more than 120 in 120 video frames while aiming) and L still
    raises the power."""
    r = a2test.run(str(DISK), unpaced_steps(lab, 'L', 10) + [lab.peek('cp_power')])
    ok, n = unpaced_flips(r, lab)
    pw = r.mem(lab['cp_power'], 1)[0]
    assert ok == 0 and n > 120 and pw == 1, (ok, n, pw)
    print(f'catapult without the marker (no floating bus): unpaced (pace_ok 0), {n} flips in 120 video frames; '
          f'L: power {pw}')


if __name__ == '__main__':
    main()
