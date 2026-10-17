#!/usr/bin/env python3
"""Joystick-only instrument previews: native light gates and aid replacement."""
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_joystick_journey import (
    GamePortSession, event, byte, rows, object_item, action, IDLE,
)
from test_camp_requirements import set_fields
from test_use_requirements import preview
from test_lighting_requirements import equipment_preview

DARK = 'TOO DARK. COMPASS/WATCH AID CLEARED.'
HINTS = {
    52: 'OPEN TOPO. CLEAR COMPASS/WATCH / 0 MIN.',
    53: 'NO LIGHT NEEDED. WATCH OFF / 0 MIN.',
    54: 'WATCH AID. REPLACES COMPASS / 0 MIN.',
    55: 'IN HAND. CLEAR COMPASS/WATCH / 0 MIN.',
    56: 'CHART REFUSED. COMPASS/WATCH CLEARED.',
}


def instruments(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu); event(s, 'ok', IDLE)
        set_fields(s, nature_frequency=0)
        for item in HINTS:
            s.step(L.poke('it_place', 2, item))
        event(s, 'up'); event(s, 'right')
        # Night, dawn, AM, PM, dusk x clear, cloudy, rain. FLASHLIGHT and
        # shelter do not override the instrument-specific native predicate.
        for period in range(5):
            for sky in range(3):
                set_fields(s, period=period, weather_sky=sky, light=1,
                           camp_use=8, shelter_inside=1, orient_aid=7)
                lit = period in (2, 3) or (period in (1, 4) and sky == 0)
                for item in HINTS:
                    expected = HINTS[item] if item == 53 or lit else DARK
                    preview(s, item, expected)
        print('  75 instrument previews: night/dawn/AM/PM/dusk x clear/cloud/rain; no state changes: OK', flush=True)

        # A refusal may clear COMPASS/WATCH, but never the shadow bit.
        # Show the actual native result; do not turn this into an atomic block.
        for item in (52, 54, 55, 56):
            set_fields(s, period=0, weather_sky=0, light=1, camp_use=8, orient_aid=7)
            preview(s, item, DARK)
            elapsed = s.step(L.peek('s_elap', 5)).data
            places = s.step(L.peek('it_place', 5, 52)).data
            action(s, 4)
            assert 'INSUFFICIENT LIGHT' in '\n'.join(rows(s)[20:23])
            assert byte(s, 'orient_aid') == 4
            assert s.step(L.peek('it_place', 5, 52)).data == places
            assert s.step(L.peek('s_elap', 5)).data == elapsed
        print('  Native dark refusals clear compass/watch, retain shadow, positions and time: OK', flush=True)

        for item, aid in ((53, 5), (54, 6), (55, 4)):
            set_fields(s, period=0 if item == 53 else 2, weather_sky=2, orient_aid=7)
            preview(s, item, HINTS[item])
            elapsed = s.step(L.peek('s_elap', 5)).data
            action(s, 4)
            assert byte(s, 'it_place', item) == 3 and byte(s, 'orient_aid') == aid
            assert s.step(L.peek('s_elap', 5)).data == elapsed
        set_fields(s, period=2, weather_sky=2, orient_aid=7)
        preview(s, 56, HINTS[56])
        elapsed = s.step(L.peek('s_elap', 5)).data
        action(s, 4)
        assert byte(s, 'orient_aid') == 4 and byte(s, 'it_place', 56) == 2
        assert s.step(L.peek('s_elap', 5)).data == elapsed
        print('  Compass works at night; watch replaces compass; altimeter only held; chart refuses: OK', flush=True)

        set_fields(s, period=2, weather_sky=2, orient_aid=7)
        preview(s, 52, HINTS[52])
        elapsed = s.step(L.peek('s_elap', 5)).data
        action(s, 4)
        assert byte(s, 'overlay_current') == 10  # TOPO, waiting for game-port input.
        assert byte(s, 'it_place', 52) == 3 and byte(s, 'orient_aid') == 4
        assert s.step(L.peek('s_elap', 5)).data == elapsed
        event(s, 'cancel')
        assert byte(s, 'pg_cur') == 1
        object_item(s, 1, 52)
        print('  USE MAP opens TOPO and returns to OBJECTS using game-port buttons, no time: OK', flush=True)

        # The same shared dialog must preserve EQUIPMENT selection and show
        # the warning before a dark refusal, not merely after executing USE.
        event(s, 'cancel', IDLE)
        event(s, 'up'); event(s, 'right')
        assert byte(s, 'pg_cur') == 2
        set_fields(s, period=0, orient_aid=5)
        equipment_preview(s, 54, DARK)
        event(s, 'cancel', IDLE); event(s, 'up')
        equipment_preview(s, 53, HINTS[53])
        event(s, 'cancel', IDLE); event(s, 'up')
        set_fields(s, period=2)
        equipment_preview(s, 56, HINTS[56])
        print('  EQUIPMENT: lighting, replacement and chart refusal hints before confirmation, cancel read-only: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        instruments(disk_with(tmp, map_fixture()))
    print('Instrument USE requirements: OK')
