#!/usr/bin/env python3
"""Joystick lighting previews, native sunlight gates and battery edge cases."""
import tempfile
from common import L, disk_with, fp
from gendata import fp as encode
from test_forest import map_fixture
from test_joystick_journey import (
    GamePortSession, event, byte, rows, object_item, action, saved_state, IDLE,
)
from test_use_requirements import preview
from test_camp_requirements import set_fields, refused
from test_save import differing, DERIVED_BYTES

SUN = 'SUN >=30 DEG NEEDED. 15 MIN / NO FIRE.'


def stock(s, value):
    s.step(L.poke('it_pack_lo', value & 255, 66))
    s.step(L.poke('it_pack_hi', value >> 8, 66))


def equipment_preview(s, item, expected):
    event(s, 'ok')
    for _ in range(140):
        if byte(s, 'overlay_text', byte(s, 'eq_cur')) == item:
            break
        entries = s.step(L.peek('overlay_text', byte(s, 'eq_n'))).data
        event(s, 'up' if entries.index(item) < byte(s, 'eq_cur') else 'down')
    assert byte(s, 'overlay_text', byte(s, 'eq_cur')) == item
    event(s, 'ok')
    for _ in range(8):
        if byte(s, 'om_action') == 4:
            break
        event(s, 'down')
    assert byte(s, 'om_action') == 4
    before = saved_state(s)
    assert expected in rows(s)[22], rows(s)[22]
    event(s, 'ok')
    assert byte(s, 'om_phase') == 2 and expected in rows(s)[22]
    assert saved_state(s) == before
    event(s, 'cancel'); event(s, 'cancel')
    assert byte(s, 'eq_selected') == item
    assert not differing(before, saved_state(s), DERIVED_BYTES)


def lighting(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu); event(s, 'ok', IDLE)
        set_fields(s, nature_frequency=0, weather_sky=0, wind=0,
                   camp_use=0, light=0, shelter_inside=0, night=0)
        s.step(L.poke('it_place', 2, 39))
        event(s, 'up'); event(s, 'right')
        for count in (0, 0xFFFF):
            stock(s, count)
            preview(s, 66, 'BATTERY CHARGE EXHAUSTED.')
        # Exactly zero is an atomic refusal; the native negative-count case
        # still sets light and takes the flashlight in hand, without U_FLASH.
        stock(s, 0)
        refused(s, 66, 'USED UP')
        stock(s, 0xFFFF)
        object_item(s, 1, 66)
        elapsed = s.step(L.peek('s_elap', 5)).data
        action(s, 4)
        assert byte(s, 'light') == 1 and byte(s, 'it_place', 66) == 3
        assert not byte(s, 'camp_use') & 8
        assert byte(s, 'it_pack_hi', 66) == 255 and byte(s, 'it_pack_lo', 66) == 255
        assert s.step(L.peek('s_elap', 5)).data == elapsed
        for count in (257, 1):
            stock(s, count)
            preview(s, 66, 'BATTERIES AVAILABLE. ONE USE / 0 MIN.')
            elapsed = s.step(L.peek('s_elap', 5)).data
            action(s, 4)
            remaining = byte(s, 'it_pack_lo', 66) + 256*byte(s, 'it_pack_hi', 66)
            assert remaining == count-1 and byte(s, 'camp_use') & 8
            assert byte(s, 'light') == 1 and byte(s, 'it_place', 66) == 3
            assert s.step(L.peek('s_elap', 5)).data == elapsed
        preview(s, 66, 'BATTERY CHARGE EXHAUSTED.')
        refused(s, 66, 'USED UP')
        assert byte(s, 'camp_use') & 8  # Native last-use activation survives.
        print('  Flashlight: zero/signed/full-word/last-use counters, one use and 0 MIN preserved: OK', flush=True)

        for fields, hint in (
            (dict(shelter_inside=1, night=1, weather_sky=2), 'MAGNF GLASS NEEDS OUTDOOR SUNLIGHT.'),
            (dict(shelter_inside=0, night=1), 'MAGNF GLASS NEEDS DAYLIGHT.'),
            (dict(night=0, weather_sky=1), 'MAGNF GLASS NEEDS A CLEAR SKY.'),
            (dict(weather_sky=2), 'MAGNF GLASS NEEDS A CLEAR SKY.'),
        ):
            set_fields(s, **fields)
            preview(s, 39, hint)
            refused(s, 39, 'INSUFFICIENT LIGHT')
        set_fields(s, weather_sky=0, shelter_inside=0, night=0, camp_use=0)
        # Native solar calculation uses the scenario latitude/date and hour.
        # At the deterministic start date, 7 AM is below 30 degrees, 10 above.
        preview(s, 39, SUN)
        refused(s, 39, 'INSUFFICIENT LIGHT')
        for i, value in enumerate(encode(10)):
            s.step(L.poke('s_hour', value, i))
        preview(s, 39, SUN)  # No false READY from a stale/rounded sky cache.
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        action(s, 4)
        assert byte(s, 'it_place', 39) == 3
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-.25) < .001
        assert not byte(s, 'camp_use') & 2 and not byte(s, 'fire_on')
        print('  Glass: shelter/night/cloud/rain, low/high Sun, native 15 MIN and no fire: OK', flush=True)

        event(s, 'cancel', IDLE)
        event(s, 'up'); event(s, 'left'); event(s, 'left')
        assert byte(s, 'pg_cur') == 6
        equipment_preview(s, 39, SUN)
        # Return from list to view and reopen with tab focus for each fixture.
        event(s, 'cancel', IDLE); event(s, 'up')
        stock(s, 0)
        equipment_preview(s, 66, 'BATTERY CHARGE EXHAUSTED.')
        event(s, 'cancel', IDLE); event(s, 'up')
        stock(s, 6)
        equipment_preview(s, 66, 'BATTERIES AVAILABLE. ONE USE / 0 MIN.')
        print('  EQUIPMENT: same live lighting hints, read-only confirm/cancel and selection preserved: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        lighting(disk_with(tmp, map_fixture()))
    print('Lighting USE requirements: OK')
