#!/usr/bin/env python3
"""Measure the same carried AXE activation from an already selected object.

Pass --baseline to use the immutable pre-pass disk and labels in /tmp.
The count includes opening ACTIONS and both confirmation presses.
"""
import sys
from pathlib import Path
import common

disk = common.DISK
if '--baseline' in sys.argv:
    base = Path('/tmp/neowilderness-ux2-baseline')
    common.L.clear()
    common.L.update(common.a2test.labels(base / 'wild.lbl'))
    disk = base / 'NEOWILDERNESSXL.po'

from common import L
from test_joystick_journey import GamePortSession, event, byte, object_item, IDLE


with GamePortSession(disk, menu=False) as s:
    menu = L.until('menu_key', 60000)
    s.step(menu)
    event(s, 'ok', menu)
    event(s, 'ok', IDLE)
    s.step(L.poke('nature_frequency', 0))
    s.step(L.poke('it_place', 2, 58))
    s.step(L.poke('care_tools', 0))
    event(s, 'up')
    event(s, 'right')
    object_item(s, 1, 58)
    gestures = 1
    event(s, 'ok')
    while byte(s, 'om_action') != 4:
        event(s, 'down')
        gestures += 1
    event(s, 'ok')
    gestures += 1
    assert byte(s, 'om_phase') == 2
    event(s, 'ok')
    gestures += 1
    assert byte(s, 'care_tools') & 1
    print(f'Carried AXE selected -> activate: {gestures} joystick gestures')
