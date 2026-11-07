#!/usr/bin/env python3
"""CUTROPE with an AppleMouse (a2shot, POM2's II+ with the AppleWin card
model in slot 4): the driver finds the card; in the menu the choice follows
the pointer (over a locked cell, then level 1's) and a click plays; in
level 1, the pointer moved with the button up puts the cursor there; then
held down and moved 45 px across the rope in one go: the cursor follows it
CUR_SPEED px a step and the knife, tried on each step, cuts the rope (a
jump of the pointer cannot step over it); a move without the button cuts
nothing.

    python3 tests/test_cutrope_mouse.py      (skipped without a2shot)
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
ROOT = GAME.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402
import subprocess  # noqa: E402

DISK = ROOT / 'dist/CUTROPE.dsk'
LBL = GAME / 'build/cutrope.lbl'


def a2shot(steps):
    r = subprocess.run([str(a2test.A2SHOT), '--mouse=applewin', '--disk', str(DISK)] + a2test.escape(steps),
                       capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    return a2test.Result(r.stdout)


def main():
    if not a2test.have_a2shot():
        print('cutrope mouse: a2shot missing, skipped')
        return
    lab = a2test.labels(LBL)
    peeks = [lab.peek('cr_on'), lab.peek('cur_x', 2), lab.peek('sel')]
    steps = [lab.until('menu_idle', 3000), lab.peek('_mouse_slot'),
             'mouse:70,50,0', 'wait:3'] + peeks + [                     # 0: cell 2 (locked)
             'mouse:20,50,0', 'wait:3'] + peeks + [                     # 1: cell 1
             'mouse:20,50,1', 'wait:3', 'mouse:20,50,0', lab.until('main', 300), 'wait:10',
             'mouse:140,30,0', 'wait:4'] + peeks + [                    # 2: no button: no cut
             'mouse:70,30,0', 'wait:4'] + peeks + [                     # 3: the cursor there
             'mouse:70,30,1', 'mouse:110,75,1', 'wait:2'] + peeks + [   # 4: one swipe
             'wait:10'] + peeks + ['mouse:110,75,0']                    # 5: caught up
    r = a2shot(steps)
    slot = r.mem(lab['_mouse_slot'], 1)[0]
    seen = [(r.mem(lab['cr_on'], 1, k)[0], tuple(r.mem(lab['cur_x'], 2, k)), r.mem(lab['sel'], 1, k)[0])
            for k in range(6)]
    assert slot == 4, slot
    assert seen[0][2] == 1 and seen[1][2] == 0, seen
    assert seen[2][0] == 1 and seen[2][1] == (140, 30), seen
    assert seen[3][1] == (70, 30) and seen[3][0] == 1, seen
    assert seen[4][0] == 0, f'the swipe did not cut the rope: {seen}'
    assert seen[5][1] == (110, 75), seen
    print(f'cutrope mouse: the card in slot {slot}; the menu follows the pointer (cell 2, cell 1), a click plays '
          f'level 1; the cursor at the pointer {seen[3][1]}, no cut without the button; one swipe of 45 px with '
          f'the button: the rope cut, the cursor at {seen[4][1]} then {seen[5][1]}')


if __name__ == '__main__':
    main()
