#!/usr/bin/env python3
"""Controlled joystick benchmark from an untouched Sierra level 1 start.

Reads internal list identities to choose fixtures deterministically; this is
not a blind playthrough. No simulation state is patched. Counts every game
port gesture after journey creation, including page/list navigation.
"""
import argparse
import json
from pathlib import Path
import common

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline', type=Path, help='directory with disk and wild.lbl')
p.add_argument('--capture', type=Path, help='capture the grouped review screen')
p.add_argument('--group', action='store_true', help='use the departure checklist')
p.add_argument('--disk', type=Path)
p.add_argument('--labels', type=Path)
a = p.parse_args()
disk = a.disk or (a.baseline / 'NEOWILDERNESSXL.po' if a.baseline else common.DISK)
labels = a.labels or (a.baseline / 'wild.lbl' if a.baseline else None)
if labels:
    common.L.clear()
    common.L.update(common.a2test.labels(labels))
from common import L
import test_joystick_journey as J
from test_objects import entry

count = 0

def event(s, control, ready=J.READY):
    global count
    J.event(s, control, ready)
    count += 1


def choose(s, side, item):
    if not J.byte(s, 'pg_focus'):
        event(s, 'ok')
    if J.byte(s, 'obj_side') != side:
        event(s, 'right' if side else 'left')
    entries = s.step(L.peek('overlay_text', J.byte(s, 'ob_n', side),
                            J.byte(s, 'ob_at', side))).data
    assert item in entries, (item, list(entries), J.rows(s))
    target = entries.index(item)
    for _ in range(140):
        if entry(s, side) == item:
            return
        event(s, 'up' if J.byte(s, 'obj_cur', side) > target else 'down')
    raise AssertionError(('cursor', item))


def commit(s, action):
    event(s, 'ok')
    for _ in range(8):
        if J.byte(s, 'om_action') == action:
            break
        event(s, 'down')
    assert J.byte(s, 'om_action') == action, J.rows(s)
    event(s, 'ok')
    if J.byte(s, 'om_phase') == 1:
        if action == 7:
            event(s, 'left')  # set one ounce, valid on the baseline too
            for _ in range(6):
                event(s, 'right')  # 2, 4, 8, 16, 32, 64 ounces
        event(s, 'ok')
    assert J.byte(s, 'om_phase') == 2, J.rows(s)
    event(s, 'ok')


with J.GamePortSession(disk, menu=False) as s:
    menu = L.until('menu_key', 60000)
    s.step(menu)
    J.event(s, 'ok', menu)
    for _ in range(3):
        J.event(s, 'up', menu)
    J.event(s, 'ok', J.IDLE)
    assert s.step('peek:7016:1').data == b'\x01', 'not level 1'
    stages = {}
    if a.group:
        event(s, 'up')
        while J.byte(s, 'pg_cur') != 6:
            event(s, 'left')
        for _ in range(4):
            event(s, 'down')
        event(s, 'ok')
        for _ in range(5):
            event(s, 'ok')
            event(s, 'down')
        for _ in range(9):
            event(s, 'down')
        event(s, 'ok')
        if a.capture:
            s.step(f'shot:{a.capture}')
        event(s, 'ok')
        assert J.byte(s, 'dep_running') == 3, J.rows(s)
        assert s.step(L.peek('dep_mask', 2)).data == bytes(2)
        if a.capture:
            s.step(f'shot:{a.capture.with_name(a.capture.stem + "-completed" + a.capture.suffix)}')
        event(s, 'cancel', J.IDLE)
        stages['prepared'] = count
    event(s, 'up')
    while J.byte(s, 'pg_cur') != 1:
        event(s, 'right')
    for name, side, item, operation in (
        ('backpack', 0, 21, 1), ('canteen', 0, 64, 1),
        ('water', 0, 22, 7), ('food', 0, 23, 0),
        ('compass', 0, 53, 0),
        ('use_compass', 1, 53, 4)):
        if a.group and name != 'use_compass':
            continue
        choose(s, side, item)
        commit(s, operation)
        stages[name] = count
    assert J.byte(s, 'it_place', 21) != 0
    assert J.byte(s, 'it_place', 64) != 0
    assert J.byte(s, 'it_place', 53) != 0
    water = J.byte(s, 'it_pack_lo', 22) + 256 * J.byte(s, 'it_pack_hi', 22)
    food = J.byte(s, 'it_pack_lo', 23) + 256 * J.byte(s, 'it_pack_hi', 23)
    assert water == 64 and food > 0, (water, food, J.rows(s))
    result = {'gestures': count, 'stages_cumulative': stages,
              'water_oz': water, 'food_oz': food,
              'placements': {str(i): J.byte(s, 'it_place', i) for i in (21, 64, 53)},
              'compass_active': J.byte(s, 'orient_aid')}
    result['inventory_state'] = {name: s.step(L.peek(name, 76)).data.hex()
        for name in ('it_place', 'it_pack_lo', 'it_pack_hi', 'it_gnd_lo', 'it_gnd_hi',
                     'it_oz_lo', 'it_oz_hi', 'it_vol_lo', 'it_vol_hi')}
    assert result['compass_active']
    print(json.dumps(result, indent=2))
