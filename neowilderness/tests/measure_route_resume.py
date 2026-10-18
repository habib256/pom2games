#!/usr/bin/env python3
"""Measure joystick gestures to reapply a Rangers cap after first orientation.

Both runs start an untouched Sierra level 1 journey. Setup and measurement
use game-port gestures exclusively; memory reads assert position/time/results.
The measured interval includes opening MAP from the view and applying the cap.
"""
import argparse
import json
import time
from pathlib import Path
import common

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline', type=Path, help='frozen directory containing disk and wild.lbl')
p.add_argument('--output', type=Path, help='write the JSON result')
a = p.parse_args()
disk = a.baseline / 'NEOWILDERNESSXL.po' if a.baseline else common.DISK
if a.baseline:
    common.L.clear()
    common.L.update(common.a2test.labels(a.baseline / 'wild.lbl'))
from common import L
from test_joystick_journey import GamePortSession, event as gesture

IDLE = L.until('idle', 60000)
READY = L.until('keyboard_wait', 60000)
NAV = L.until('nav_key', 60000)
MENU = L.until('nav_menu_key', 60000)
count = 0
controls = []


def event(s, control, ready=READY):
    global count
    gesture(s, control, ready)
    count += 1
    controls.append(control)


def state(s):
    return {name: s.step(L.peek(name, size)).data.hex()
            for name, size in (('px', 4), ('s_elap', 5))}


def open_map(s):
    event(s, 'up')       # view -> remembered top page
    event(s, 'up')       # top tab -> TOPO
    event(s, 'right')    # TOPO -> MAP


def choose_rangers(s):
    event(s, 'ok', MENU)
    event(s, 'down', MENU)
    event(s, 'ok', NAV)
    event(s, 'ok', NAV)
    event(s, 'ok', IDLE)


with GamePortSession(disk, menu=False) as s:
    menu = L.until('menu_key', 60000)
    s.step(menu)
    event(s, 'ok', menu)  # Sierra
    event(s, 'ok', IDLE)  # level 1
    initial = state(s)
    destination = s.step('peek:7008:2').data.hex()
    open_map(s)
    choose_rangers(s)
    assert state(s) == initial, 'initial orientation moved the player or spent time'
    before = state(s)
    count = 0
    controls.clear()
    start = time.monotonic()
    open_map(s)
    if 'route_active' in L:
        assert s.step(L.peek('route_active')).data == b'\x01'
        event(s, 'ok', NAV)
        assert s.step(L.peek('nav_x', 2)).data.hex() == destination
        event(s, 'ok', IDLE)
    else:
        choose_rangers(s)
    elapsed = time.monotonic() - start
    after = state(s)
    assert before == after, 'reapplying the cap moved the player or spent time'
    assert s.step('peek:7008:2').data.hex() == destination
    result = {
        'build': str(a.baseline) if a.baseline else 'current',
        'flow': 'view -> MAP -> reapply Rangers cap after first orientation',
        'gestures': count,
        'controls': controls,
        'host_seconds': round(elapsed, 3),
        'destination_xy_hex': destination,
        'before': before,
        'after': after,
        'heading_native': int.from_bytes(s.step(L.peek('heading', 2)).data, 'little'),
        'setup_uses_pokes': False,
    }
    text = json.dumps(result, indent=2)
    if a.output:
        a.output.write_text(text + '\n')
    print(text)
