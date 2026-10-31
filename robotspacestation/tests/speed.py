#!/usr/bin/env python3
"""Frames per drone turn in the room (not part of `make test`): missions 1,
4 and 7 (default) from a save with their solution boards (tests/test_model.py
solution), RUN, then tick_count over a window of emulated frames (a2shot's
time: host load does not matter). A mission won inside the window stops the
turns: the window is short enough for 1, 4 and 7, and `won` is reported.

    python3 tests/speed.py --disk ../dist/ROBOTSTATION.po --labels build/game.lbl [--iic]
"""
import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tests'))
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import a2test
import test_lab
import test_zone
from test_lab import MACHINE, idle, run
from test_campaign import title_click
from test_model import solution
from model import save_bytes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', required=True)
    ap.add_argument('--labels', required=True)
    ap.add_argument('--iic', action='store_true')
    ap.add_argument('--missions', default='1,4,7')
    ap.add_argument('--frames', type=int, default=150)
    args = ap.parse_args()
    if args.iic:
        MACHINE[:] = ['--iic']
    test_zone.GAME_PO = Path(args.disk).resolve()
    L = a2test.labels(args.labels)
    test_lab.SYNC[:] = [idle(L, 3000)]
    test_lab.POKE[:] = [L]
    os.chdir(HERE)
    for m in (int(k) - 1 for k in args.missions.split(',')):
        b = solution(m)
        a, b2 = b if isinstance(b, tuple) else (b, None)
        disk = test_zone.disk_with_save(save_bytes(test_zone.EMPTY, reached=m, drone=a, drone2=b2), f'speed{m}')
        steps = ['wait:1700'] + title_click(m) + ['wait:200', idle(L), 'key:M', 'wait:30',
                                                  L.peek('_tick_count', 2), f'wait:{args.frames}',
                                                  L.peek('_tick_count', 2), L.peek('_won', 1)]
        r = run(disk, steps)
        t0, t1 = (int.from_bytes(r.mem(L['_tick_count'], 2, n), 'little') for n in (0, 1))
        won = r.mem(L['_won'], 1)[0]
        turns = t1 - t0
        print(f'{MACHINE[0][2:]} mission {m + 1}: {turns} turns in {args.frames} frames = '
              f'{args.frames / max(1, turns):.2f} frames/turn{" (won inside the window)" if won else ""}')


if __name__ == '__main__':
    main()
