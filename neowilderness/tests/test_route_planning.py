#!/usr/bin/env python3
"""Visible XL map targets, true/magnetic bearings and precise joystick caps.

Fixtures establish positions; every target and heading decision below uses the
rendered map or public degree input. Memory reads only assert final results.
"""
import tempfile
from common import L, a2test, disk_with, text_screen, dhgr_view
from test_sites import mapbin, native_mapbin
from test_joystick_journey import event

IDLE = L.until('idle', 60000)
READY = L.until('keyboard_wait', 60000)
NAV = L.until('nav_key', 60000)
MENU = L.until('nav_menu_key', 60000)


def word(s, name):
    return int.from_bytes(s.step(L.peek(name, 2)).data, 'little')


def screen(s):
    return '\n'.join(text_screen(s.step('peek:0400:1024').data))


def command(s, text, ready=IDLE):
    s.step('key:'+text+'\r')
    s.step('wait:1')
    s.step(ready)


def enter_plan(s, destination=0):
    if s.step(L.peek('route_active')).data != b'\0':
        event(s, 'ok', NAV)
        event(s, 'right', NAV)
        event(s, 'ok', MENU)
    else:
        event(s, 'ok', MENU)
    for _ in range(destination):
        event(s, 'down', MENU)
    event(s, 'ok', NAV)


def assert_map_drawn(s):
    rows = text_screen(s.step('peek:0400:1024').data)
    assert all(row.strip() for row in rows[2:23]), rows
    assert any('++' in row for row in rows[2:23]), rows


def main():
    m = bytearray(mapbin())
    m[2:6] = bytes((0, 20, 0, 20))
    m[8:10] = bytes((24, 20))
    m[16:19] = bytes((1, 20, 24))
    m[24] = 17
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp, m)) as s:
        s.step(IDLE)
        command(s, 'MAP', READY)
        assert 'DEG MAG' in screen(s) and 'TRUE N UP' in screen(s)
        clock = s.step(L.peek('s_elap', 5)).data
        position = s.step(L.peek('px', 4)).data
        enter_plan(s, 1)  # RANGERS chosen using the game port
        assert 'TARGET RANGERS 24,20' in screen(s) and '4.0 CELLS' in screen(s)
        assert_map_drawn(s)
        event(s, 'cancel', READY)
        enter_plan(s, 2)  # CRASH SITE
        assert 'TARGET CRASH SITE 20,20' in screen(s)
        event(s, 'cancel', READY)
        enter_plan(s, 3)  # CABIN
        assert 'TARGET CABIN 20,24' in screen(s) and '0 DEG TRUE' in screen(s)
        assert_map_drawn(s)
        event(s, 'cancel', READY)
        enter_plan(s)
        assert_map_drawn(s)
        assert 'TARGET CRASH SITE 20,20' in screen(s)
        # The map itself shows the cabin north and the outpost east. Select
        # the east neighbour by one joystick gesture; read the public result.
        event(s, 'right', NAV)
        text = screen(s)
        assert 'TARGET 21,20' in text and '1.0 CELLS' in text, text
        assert '90 DEG TRUE / 73 MAG' in text, text
        assert word(s, 'nav_true') == 90 and word(s, 'nav_mag') == 73
        # Follow the north-up map around the eight neighbours; no player
        # position reads are needed to choose these cursor directions.
        for control, bearing, distance in (
                ('up', 45, '1.4'), ('left', 0, '1.0'),
                ('left', 315, '1.4'), ('down', 270, '1.0'),
                ('down', 225, '1.4'), ('right', 180, '1.0'),
                ('right', 135, '1.4'), ('up', 90, '1.0')):
            event(s, control, NAV)
            text = screen(s)
            assert f'{bearing} DEG TRUE' in text and f'{distance} CELLS' in text, text
            assert word(s, 'nav_true') == bearing
            assert word(s, 'nav_mag') == (bearing - 17) % 360
        # A controlled pending-trip fixture must survive preview/cancellation.
        s.step(L.poke('travel_pending', 1))
        # Reviewing and cancelling make no simulation changes.
        event(s, 'ok', NAV)
        event(s, 'cancel', NAV)
        assert s.step(L.peek('s_elap', 5)).data == clock
        assert s.step(L.peek('px', 4)).data == position
        assert s.step(L.peek('travel_pending')).data == b'\x01'
        # Take this chosen cap. Native compass error remains bounded by 2°.
        event(s, 'ok', NAV)
        event(s, 'ok', IDLE)
        assert s.step(L.peek('travel_pending')).data == b'\x00'
        actual = word(s, 'heading') * 360 / 560
        assert abs(actual - 90) < 3, actual
        assert s.step(L.peek('orient_aid')).data[0] & 1
        assert s.step(L.peek('px', 4)).data == position
        assert s.step(L.peek('s_elap', 5)).data == clock
        # Reopening after overlay replacement retains the chosen target.
        assert s.step(L.peek('route_active')).data == b'\x01'
        command(s, 'MAP', READY)
        event(s, 'ok', NAV)
        assert 'TARGET 21,20' in screen(s) and 'RESUME CAP' in screen(s)
        assert '1.0 CELLS' in screen(s)
        event(s, 'right', NAV)
        event(s, 'right', NAV)
        assert 'ABANDON TARGET' in screen(s)
        event(s, 'cancel', READY)
        assert s.step(L.peek('route_active')).data == b'\x01'
        event(s, 'ok', NAV)
        event(s, 'right', NAV)
        event(s, 'right', NAV)
        event(s, 'ok', READY)
        assert s.step(L.peek('route_active')).data == b'\0'
        assert s.step(L.peek('travel_pending')).data == b'\0'
        event(s, 'cancel', IDLE)
        assert s.step(L.peek('px', 4)).data == position
        assert s.step(L.peek('s_elap', 5)).data == clock
        # Degree input wraps; horizontal gestures change one degree and
        # vertical gestures ten. Cancellation preserves the actual heading.
        before = word(s, 'heading')
        s.step(L.poke('travel_pending', 1))
        command(s, 'LOOK AZIMUTH', READY)
        event(s, 'left', READY)
        assert '> 359' in screen(s)
        event(s, 'right', READY)
        assert '> 0' in screen(s)
        event(s, 'up', READY)
        assert '> 10' in screen(s)
        event(s, 'down', READY)
        assert '> 0' in screen(s)
        event(s, 'cancel', IDLE)
        assert word(s, 'heading') == before
        assert s.step(L.peek('s_elap', 5)).data == clock
        assert s.step(L.peek('travel_pending')).data == b'\x01'
        # Selecting a target does not bypass the equipment requirement.
        s.step(L.poke('it_place', 255, 53))
        s.step(L.poke('orient_aid', 0))
        command(s, 'MAP', READY)
        enter_plan(s)
        event(s, 'right', NAV)
        event(s, 'ok', NAV)
        event(s, 'ok', IDLE)
        assert 'FIRST PUT DIRECTION AID' in screen(s)
        assert s.step(L.peek('route_active')).data == b'\0'
        assert s.step(L.peek('travel_pending')).data == b'\x01'
        assert word(s, 'heading') == before
        assert s.step(L.peek('px', 4)).data == position
        assert s.step(L.peek('s_elap', 5)).data == clock
    print('  XL map target, distance, TRUE/MAG, native aid, angle joystick and atomic cancel: OK')
    # TOPO keeps its return code in the SIM window too. Planning replaces
    # that code, so both snapshot and native-geography returns must work.
    for fixture in (mapbin, native_mapbin):
        with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp, fixture())) as s:
            s.step(IDLE)
            before = dhgr_view(s.step('peek:2000:8192').data)
            clock = s.step(L.peek('s_elap', 5)).data
            command(s, 'TOPO', READY)
            event(s, 'right', READY)  # MAP over TOPO
            enter_plan(s)
            assert_map_drawn(s)
            event(s, 'cancel', READY)
            event(s, 'cancel', IDLE)
            assert dhgr_view(s.step('peek:2000:8192').data) == before, fixture.__name__
            assert s.step(L.peek('s_elap', 5)).data == clock
    print('  TOPO/MAP/planner cancellation restores legacy and native outdoor views: OK')
    fractional = bytearray(native_mapbin())
    fractional[2:6] = bytes((0, 34, 128, 28))
    fractional[24] = 17
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp, fractional)) as s:
        s.step(IDLE)
        command(s, 'MAP', READY)
        enter_plan(s)
        assert_map_drawn(s)
        event(s, 'right', NAV)
        text = screen(s)
        assert 'TARGET 35,28' in text and '1.1 CELLS' in text, text
        assert '117 DEG TRUE / 100 MAG' in text, text
        assert_map_drawn(s)
    print('  Native fractional start: visible terrain/cursor and 1.1 cells at117 TRUE/100 MAG: OK')



if __name__ == '__main__':
    main()
