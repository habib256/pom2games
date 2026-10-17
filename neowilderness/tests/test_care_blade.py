#!/usr/bin/env python3
"""Joystick CUT BODY: possession, activation, stale cells and native preparation."""
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_fit_quantities import boot
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, IDLE
from test_status_care_return import RESULT, returned
from mkmap import MAP_BYTES, FOREST_BYTES

ACTIVE = 'BLADE IN USE'
PREPARE = 'BLADE AVAILABLE; USE KNIFE/AXE FIRST'
MISSING = 'NO BLADE HERE; FIND KNIFE/AXE'


def check(disk, name, knife=255, axe=255, flags=0, stale=None,
          remote=False, expected=PREPARE, first='USE KNIFE', accepted=True):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('injury_active', 1, 7))
        for item, place in ((59, knife), (58, axe)):
            s.step(L.poke('it_place', place, item))
            s.step(L.poke('it_x', byte(s, 'px', 1)+int(remote), item))
            s.step(L.poke('it_y', byte(s, 'py', 1), item))
        s.step(L.poke('care_tools', flags))
        s.step(L.poke('care_tool_x', byte(s, 'px', 1)+int(stale == 'x')))
        s.step(L.poke('care_tool_y', byte(s, 'py', 1)+int(stale == 'y')))
        event(s, 'up'); event(s, 'down'); event(s, 'right')
        assert byte(s, 'pg_g') == 1
        line = rows(s)[22]
        assert f'0 MIN; {expected}' in line and 'DOSES' not in line, (name, line)
        before = saved_state(s)
        event(s, 'right'); event(s, 'left')
        assert rows(s)[22] == line and saved_state(s) == before
        assert byte(s, 'care_tools') == flags, 'preview expired a stale native flag'
        event(s, 'cancel', IDLE)
        assert saved_state(s) == before
        event(s, 'up'); event(s, 'down'); event(s, 'right')
        clock = s.step(L.peek('s_elap', 5)).data
        # Observe the first command before it executes; buttons are the only input.
        s.step('btn:0,1'); s.step(L.until('do_command', 60000))
        actual = s.step(L.peek('inbuf', 24)).data.split(b'\0')[0].decode()
        assert actual == first, (name, actual, first)
        s.step('btn:0,0'); s.step(RESULT); s.step('wait:6')
        assert byte(s, 'medical_actions', 6) == int(accepted)
        assert s.step(L.peek('s_elap', 5)).data == clock
        if not accepted:
            assert 'USE KNIFE OR USE AXE.' in '\n'.join(r[:39] for r in rows(s)[20:23]), rows(s)[20:23]
            assert byte(s, 'care_tools') == (0 if stale else flags)
        returned(s, 7, 1)
        assert (ACTIVE if accepted else MISSING) in rows(s)[22], (name, rows(s)[22])
        print(f'  {name}: {expected}; {actual}; native cut={accepted}, 0 MIN, preview read-only: OK', flush=True)


def display_words(tmp):
    # Banking these labels supplies the RAM for the blade preview.
    cases = ((-1, 10, False, 'FREEZE', 'LOW', 'CLEAR'),
             (40, 60, True, 'COLD', 'MEDIUM', 'WOODS'),
             (70, 100, False, 'NICE', 'MEDIUM', 'ROCKY'),
             (90, 115, True, 'WARM', 'HIGH', 'SCRUB'),
             (100, 20, True, 'HOT', 'LOW', 'WOODS'))
    for temperature, height, wooded, air, altitude, ground in cases:
        fixture = map_fixture(height)
        fixture[10] = 0
        if not wooded:
            fixture[MAP_BYTES:] = bytes(FOREST_BYTES)
        with GamePortSession(disk_with(tmp, fixture), menu=False) as s:
            boot(s)
            for item in (55, 69):  # qualitative words without instruments
                s.step(L.poke('it_place', 255, item))
            s.step(L.poke('airtemp', temperature & 255))
            event(s, 'up')
            screen = rows(s)
            assert air in screen[4] and altitude in screen[6] and ground in screen[6], (air, altitude, ground, screen[4:7])
    print('  Banked words: five temperatures, three altitude levels, four ground classes keep their display: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        check(disk, 'packed knife', knife=2)
        check(disk, 'held knife without activation', knife=3)
        check(disk, 'axe only', axe=2, first='USE AXE')
        check(disk, 'knife before axe', knife=2, axe=2)
        check(disk, 'active knife', knife=3, flags=2, expected=ACTIVE, first='CUT BODY')
        check(disk, 'active axe', axe=3, flags=1, expected=ACTIVE, first='CUT BODY')
        check(disk, 'native active packed knife', knife=2, flags=2, expected=ACTIVE, first='CUT BODY')
        check(disk, 'active local ground knife', knife=0, flags=2, expected=ACTIVE, first='CUT BODY')
        check(disk, 'hung knife unavailable', knife=5, flags=2, expected=MISSING, first='CUT BODY', accepted=False)
        check(disk, 'ground knife elsewhere', knife=0, flags=2, remote=True, expected=MISSING, first='CUT BODY', accepted=False)
        check(disk, 'stale X, prepare knife', knife=2, flags=2, stale='x')
        check(disk, 'stale Y, prepare axe', axe=2, flags=1, stale='y', first='USE AXE')
        check(disk, 'stale flags and no blade', flags=3, stale='x', expected=MISSING, first='CUT BODY', accepted=False)
        check(disk, 'both flags, only knife remains', knife=2, flags=3, expected=ACTIVE, first='CUT BODY')
        check(disk, 'axe flag but only unprepared knife', knife=2, flags=1)
        check(disk, 'knife flag but only unprepared axe', axe=2, flags=2, first='USE AXE')
        display_words(tmp)
    print('Care blade: OK')
