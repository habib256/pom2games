#!/usr/bin/env python3
"""Compare a frozen selector with the current one using game-port input only.

Run separately for each matching disk/labels pair; no fixture or build writes.
"""
import argparse
import json
from pathlib import Path
import time
from common import DISK, HERE, L, a2test

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--disk', type=Path, default=DISK)
p.add_argument('--labels', type=Path, default=HERE / 'build/wild.lbl')
p.add_argument('--legacy', action='store_true', help='old 15-minute quick step')
args = p.parse_args()
L.clear()
L.update(a2test.labels(args.labels))
from test_joystick_journey import GamePortSession, event, grid, saved_state, READY, IDLE
from test_menu_bar import duration_control

with GamePortSession(args.disk, menu=False) as s:
    menu = L.until('menu_key', 60000)
    s.step(menu)
    event(s, 'ok', menu)
    for _ in range(3):
        event(s, 'up', menu)
    event(s, 'ok', IDLE)
    before = saved_state(s)
    rng = s.step(L.peek('weather_seed', 4)).data
    grid(s, 'WAIT', ready=READY)
    start = s.step(READY).cycles[-1]
    wall = time.monotonic()
    gestures = 0
    while True:
        current = int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little')
        if current == 1:
            break
        control = ('down' if current - 1 >= 15 else 'left') if args.legacy else duration_control(current, 1)
        event(s, control)
        gestures += 1
        assert gestures < 100
    cycles = s.step(READY).cycles[-1] - start
    assert saved_state(s) == before
    assert s.step(L.peek('weather_seed', 4)).data == rng
    print(json.dumps({'disk': str(args.disk), 'selection': '60 to 1 MIN',
                      'gestures': gestures, 'cycles': cycles,
                      'seconds': round(time.monotonic()-wall, 3),
                      'state_and_rng_unchanged': True}))
