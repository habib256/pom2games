#!/usr/bin/env python3
"""CATAPULT on its disk in a2run: boot, the counters and the key line, the
power and angle keys, a shot fired (the same as the model's: the targets
down agree), the round played to its end (three shots, ROUND OVER), space
for a new round. Checks the state bytes and the text the screen shows (the
glyph bytes of the two text lines on the page on display) and counts the
frames drawn while aiming and while a shot flies (frames per second).

    python3 tests/test_catapult_disk.py      (tests/test_catapult.py runs it)
"""
from pathlib import Path
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
    steps += ['key: ', 'wait:300'] + look(lab)                                 # 3: 5 s of the shot
    steps += ['wait:900'] + look(lab)                                          # 4: the shot over
    steps += ['key: ', 'wait:1200', 'key: ', 'wait:1200'] + look(lab)         # 5: shots 2 and 3: over
    steps += ['key: ', 'wait:30'] + look(lab)                                  # 6: a new round
    r = a2test.run(str(DISK), steps, timeout=300)
    (s0, t0), (s1, _), (s2, t2), (s3, _), (s3b, _), (s4, t4), (s5, t5) = (seen(r, lab, k) for k in range(7))
    assert t0 == ['POWER 00  ANGLE 45  SHOTS 03  DOWN 00/6', 'J L:POWER  I K:ANGLE  SPACE:FIRE  R:NEW'], t0
    assert s0['cp_phase'] == C.AIM and s0['cp_shots'] == 3, s0
    assert s2['cp_power'] == 9 and s2['cp_stop'] == 1 and t2[0].startswith('POWER 09  ANGLE 35'), (s2, t2)
    c, _ = C.play([(9, 1)])                                                     # the model's shot
    assert s3['cp_phase'] == C.FLY, s3
    assert s3b['cp_phase'] == C.AIM and s3b['cp_score'] == c.score and s3b['cp_shots'] == 2, (s3b, c.score)
    assert s4['cp_phase'] == C.OVER and s4['cp_shots'] == 0 and t4[1].startswith(('ROUND OVER', 'ALL SIX')), (s4, t4)
    assert s5['cp_phase'] == C.AIM and s5['cp_shots'] == 3 and s5['cp_score'] == 0, s5
    fps_aim = ((s1['frames'] - s0['frames']) & 0xFF) / 5
    fps_shot = ((s3['frames'] - s2['frames']) & 0xFF) / 5
    print(f'catapult disk: boot "{t0[0]}"; power 9, angle 35, fire: {s3b["cp_score"]} down (the model: '
          f'{c.score}); round over: "{t4[1].split("  ")[0]}" {s4["cp_score"]} down; space: a new round; '
          f'{fps_aim:.1f} fps aiming, {fps_shot:.1f} fps over the 5 s of a shot')
    return fps_aim, fps_shot


if __name__ == '__main__':
    main()
