#!/usr/bin/env python3
"""Comparable GET result -> BOIL 1 OZ -> DRINK 1 OZ joystick gesture count.

--baseline uses immutable /tmp/neowilderness-ux6-baseline labels and disk.
Both paths begin after the same native GET and use the same native portions.
"""
import sys
import tempfile
from pathlib import Path
import common
if '--baseline' in sys.argv:
    base = Path('/tmp/neowilderness-ux6-baseline')
    common.L.clear()
    common.L.update(common.a2test.labels(base / 'wild.lbl'))
    common.DISK = base / 'NEOWILDERNESSXL.po'
from common import L, disk_with
from test_care_water_preview import fixture
from test_fit_quantities import boot
from test_joystick_journey import GamePortSession, event, byte, grid, IDLE, READY
from test_survival_flows import open_flow, choose_source
from test_result_followups import followup, quantity


class CountedSession(GamePortSession):
    gestures = 0
    counting = False
    def step(self, step):
        if self.counting and (step.startswith('joy:') and step != 'joy:0,0'
                              or step.startswith('btn:') and step.endswith(',1')):
            self.gestures += 1
        return super().step(step)


with tempfile.TemporaryDirectory() as tmp:
    disk = disk_with(tmp, fixture(water=(20, 20, 64)))
    with CountedSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('it_place', 2, 64))
        s.step(L.poke('it_pack_lo', 0, 22))
        s.step(L.poke('it_pack_hi', 0, 22))
        event(s, 'right', IDLE); event(s, 'left', IDLE)
        grid(s, 'MAKE', 'FIRE')
        grid(s, 'GET')
        choose_source(s, 22, READY if '--baseline' not in sys.argv else IDLE)
        s.counting = True
        if '--baseline' in sys.argv:
            open_flow(s, water=True, choice=1)
            event(s, 'ok', IDLE)
        else:
            followup(s, 'WATER COLLECTED')
            event(s, 'ok', IDLE)
        while byte(s, 'mn_cur'):
            event(s, 'left', IDLE)
        event(s, 'ok', READY if '--baseline' not in sys.argv else IDLE)
        if '--baseline' in sys.argv:
            open_flow(s, water=True, choice=2)
            event(s, 'ok', IDLE)
            choose_source(s, 22)
            event(s, 'ok', IDLE)
        else:
            followup(s, 'BOILED PORTION')
            event(s, 'ok')
            quantity(s, 1, IDLE)
        print(f'GET result -> BOIL 1 OZ -> DRINK 1 OZ: {s.gestures} joystick gestures')
