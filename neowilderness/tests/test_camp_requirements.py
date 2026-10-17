#!/usr/bin/env python3
"""Joystick camp previews: actual native gates, no side effects during browsing."""
import tempfile
from common import L, disk_with, fp
from test_forest import map_fixture
from test_joystick_journey import (
    GamePortSession, event, byte, rows, object_item, action, saved_state, IDLE,
)
from test_use_requirements import preview
from test_save import differing, DERIVED_BYTES


def set_fields(s, **fields):
    for name, value in fields.items():
        s.step(L.poke(name, value))


def refused(s, item, message):
    object_item(s, 1, item)
    before = saved_state(s)
    action(s, 4)
    assert message in '\n'.join(rows(s)[20:23]), rows(s)[20:23]
    assert not differing(before, saved_state(s), DERIVED_BYTES)


def camp(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu); event(s, 'ok', IDLE)
        set_fields(s, nature_frequency=0, weather_sky=0, wind=0,
                   camp_use=0, fire_on=0, fire_near=0)
        s.step(L.poke('it_place', 2, 71))
        event(s, 'up'); event(s, 'right')
        preview(s, 71, 'FUEL INACTIVE. USE FUEL FIRST.')
        refused(s, 71, 'BOTH FUEL AND FIRE')

        for stock in (0, 0xFFFF):
            s.step(L.poke('it_pack_lo', stock & 255, 40))
            s.step(L.poke('it_pack_hi', stock >> 8, 40))
            preview(s, 40, 'NO USABLE FUEL LEFT.')
        s.step(L.poke('it_pack_lo', 8, 40)); s.step(L.poke('it_pack_hi', 0, 40))
        preview(s, 40, 'FUEL AVAILABLE. USE ACTIVATES ONE OZ.')
        action(s, 4)
        assert byte(s, 'camp_use') & 4 and byte(s, 'it_pack_lo', 40) == 7
        preview(s, 71, 'NO IGNITION. USE MATCHES OR USE FIRE.')
        refused(s, 71, 'BOTH FUEL AND FIRE')
        # A lit fire alone is insufficient: USE FIRE (fire_near) is the native gate.
        set_fields(s, fire_on=1, fire_near=0)
        preview(s, 71, 'NO IGNITION. USE MATCHES OR USE FIRE.')
        set_fields(s, fire_near=1)
        preview(s, 71, 'READY. SET DOWN STOVE / 30 MIN.')
        print('  Stove: active fuel, ignition and nearby fire distinguished; refusals atomic: OK', flush=True)

        set_fields(s, camp_use=0, fire_on=0, fire_near=0, weather_sky=0, wind=40)
        preview(s, 38, 'MATCHES READY. USE THEN MAKE FIRE.')
        set_fields(s, wind=41)
        preview(s, 38, 'WIND >=41 MPH. ACTIVATE FUEL FIRST.')
        refused(s, 38, 'TOO MUCH RAIN OR WIND')
        set_fields(s, weather_sky=2, wind=0)
        preview(s, 38, 'RAIN. ACTIVATE FUEL FIRST.')
        refused(s, 38, 'TOO MUCH RAIN OR WIND')
        set_fields(s, camp_use=4, wind=41)
        preview(s, 38, 'MATCHES READY. USE THEN MAKE FIRE.')
        set_fields(s, shelter_inside=1, camp_use=0)
        preview(s, 38, 'CAUTION: USING MATCHES INSIDE SHELTER.')
        matches = byte(s, 'it_pack_lo', 38)
        action(s, 4)
        assert byte(s, 'it_pack_lo', 38) == matches-1 and byte(s, 'camp_use') & 1
        print('  Matches: 40/41 MPH boundary, rain, fuel override and native shelter caution: OK', flush=True)

        set_fields(s, shelter_inside=0, camp_use=4, weather_sky=0, wind=0)
        cell = 0x7040 + byte(s, 'py', 1)*112 + byte(s, 'px', 1)
        ground = s.step(f'peek:{cell:04X}:1').data[0]
        s.step(f'poke:{cell:04X}:{ground | 128:02X}')
        event(s, 'cancel', IDLE); event(s, 'up')
        preview(s, 38, 'IN WATER. MOVE TO LAND FIRST.')
        refused(s, 38, 'WATER')
        s.step(f'poke:{cell:04X}:{ground:02X}')
        event(s, 'cancel', IDLE); event(s, 'up')
        # Empty and negative match counters must not be advertised as ready.
        for stock in (0, 0xFFFF):
            s.step(L.poke('it_pack_lo', stock & 255, 38))
            s.step(L.poke('it_pack_hi', stock >> 8, 38))
            preview(s, 38, 'NO MATCHES LEFT. FIND ANOTHER IGNITION.')
        s.step(L.poke('it_pack_lo', 24, 38)); s.step(L.poke('it_pack_hi', 0, 38))
        print('  Water is refused even with active fuel; empty/signed stocks show no usable supply: OK', flush=True)

        set_fields(s, camp_use=0)
        object_item(s, 1, 40); action(s, 4)
        object_item(s, 1, 38); action(s, 4)
        preview(s, 71, 'READY. SET DOWN STOVE / 30 MIN.')
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        action(s, 4)
        assert byte(s, 'it_place', 71) == 0 and byte(s, 'camp_use') & 16
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-.5) < .001
        object_item(s, 1, 40); action(s, 4)
        object_item(s, 1, 38); action(s, 4)
        preview(s, 71, 'READY. STOVE ALREADY DOWN / 0 MIN.', side=0)
        elapsed = s.step(L.peek('s_elap', 5)).data
        action(s, 4)
        assert s.step(L.peek('s_elap', 5)).data == elapsed
        assert byte(s, 'camp_use') & 16
        print('  Joystick USE FUEL -> USE MATCHES -> USE STOVE: 30 MIN carried, 0 MIN already down: OK', flush=True)

        event(s, 'cancel', IDLE)
        event(s, 'up'); event(s, 'left'); event(s, 'left')
        assert byte(s, 'pg_cur') == 6
        event(s, 'ok')
        for _ in range(140):
            if byte(s, 'overlay_text', byte(s, 'eq_cur')) == 71:
                break
            event(s, 'down')
        assert byte(s, 'overlay_text', byte(s, 'eq_cur')) == 71
        event(s, 'ok')
        assert 'STOVE ALREADY DOWN / 0 MIN' in rows(s)[22]
        event(s, 'ok')
        assert byte(s, 'om_phase') == 2 and 'STOVE ALREADY DOWN / 0 MIN' in rows(s)[22]
        event(s, 'cancel'); event(s, 'cancel')
        assert byte(s, 'eq_selected') == 71
        set_fields(s, camp_use=0, weather_sky=0, wind=41)
        event(s, 'cancel', IDLE); event(s, 'up'); event(s, 'ok')
        for _ in range(140):
            if byte(s, 'overlay_text', byte(s, 'eq_cur')) == 38:
                break
            event(s, 'down')
        assert byte(s, 'overlay_text', byte(s, 'eq_cur')) == 38
        event(s, 'ok')
        for _ in range(8):
            if byte(s, 'om_action') == 4:
                break
            event(s, 'down')
        before = saved_state(s)
        assert 'WIND >=41 MPH' in rows(s)[22]
        event(s, 'ok')
        assert byte(s, 'om_phase') == 2 and 'WIND >=41 MPH' in rows(s)[22]
        assert saved_state(s) == before
        event(s, 'cancel'); event(s, 'cancel')
        assert byte(s, 'pg_cur') == 6 and byte(s, 'eq_selected') == 38
        print('  EQUIPMENT shows ready stove timing and live wind prerequisite without mutation: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        camp(disk_with(tmp, map_fixture()))
    print('Camp USE requirements: OK')
