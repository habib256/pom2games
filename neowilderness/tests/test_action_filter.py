#!/usr/bin/env python3
"""Real joystick: offered actions reflect placement, source and native USE gates."""
from test_joystick_journey import equipment_item
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_joystick_journey import (
    GamePortSession, event, byte, rows, object_item, action, saved_state, IDLE,
)


def open_objects(s):
    event(s, 'up'); event(s, 'right')
    assert byte(s, 'pg_cur') == 1


def check(s, item, place, side, expected):
    if item < 89:
        s.step(L.poke('it_place', place, item))
    else:
        s.step(L.poke('cr_b1', place, item-89))
    # Reopen so the visible lists are rebuilt from the fixture's new state.
    event(s, 'cancel', IDLE)
    event(s, 'up')
    object_item(s, side, item)
    event(s, 'ok')
    before = saved_state(s)
    observed = set()
    for _ in range(8):
        observed.add(byte(s, 'om_action'))
        event(s, 'down')
    assert observed == set(expected), (item, place, side, expected, observed)
    assert saved_state(s) == before
    event(s, 'cancel')
    print(f'  Item {item}, place {place}, side {side}: actions {sorted(observed)}, read-only: OK', flush=True)


def filters(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu); event(s, 'ok', IDLE)
        s.step(L.poke('nature_frequency', 0))
        open_objects(s)
        # PACK=0, CARRY=1, DROP=2, WEAR=3, USE=4, EAT=5, TASTE/DRINK=6, GET=7.
        for item, place, expected in (
            (5, 1, (0, 1, 2)), (2, 2, (1, 2, 3)), (59, 3, (0, 2, 4)),
            (21, 3, (2,)), (64, 2, (1, 2)), (64, 3, (0, 2)),
            (90, 2, (1, 2, 4)), (90, 3, (0, 2, 4)), (93, 1, (0, 1, 2, 4)),
            (47, 3, (0, 2, 4, 5)),
        ):
            check(s, item, place, 1, expected)
        check(s, 21, 0, 0, (1,))
        s.step(L.poke('it_place', 3, 21))
        for name, value in (('it_pack_lo', 2), ('it_pack_hi', 0),
                            ('it_gnd_lo', 14), ('it_gnd_hi', 0)):
            s.step(L.poke(name, value, 25))
        check(s, 25, 4, 0, (0, 5, 6))
        check(s, 25, 4, 1, (2, 5, 6))
        check(s, 22, 4, 0, (6, 7))
        check(s, 22, 4, 1, (2, 6))

        # Available bait is prepared only after confirming USE.
        s.step(L.poke('fg_bait', 0)); s.step(L.poke('fg_use', 0))
        check(s, 72, 2, 1, (1, 2, 4))
        before = saved_state(s)
        action(s, 4)
        assert byte(s, 'fg_bait') and byte(s, 'fg_use') & 1
        assert byte(s, 'pg_cur') == 1 and byte(s, 'obj_selected', 1) == 72
        print('  USE TRAP remains offered; available bait is prepared automatically and keeps selection: OK', flush=True)

        # Restore ordinary load before testing actual native placement changes.
        s.step(L.poke('cr_b1', 255, 1)); s.step(L.poke('cr_b1', 255, 4))
        s.step(L.poke('it_place', 0, 72))
        event(s, 'cancel', IDLE)
        event(s, 'up'); event(s, 'right')
        assert byte(s, 'pg_cur') == 2
        event(s, 'ok')
        equipment_item(s, 59)
        assert byte(s, 'overlay_text', byte(s, 'eq_cur')) == 59
        event(s, 'ok')
        assert byte(s, 'om_mask') == 0x15
        event(s, 'cancel')
        action(s, 0)                       # PACK KNIFE
        assert byte(s, 'it_place', 59) == 2
        event(s, 'ok')
        assert byte(s, 'om_mask') == 0x16
        event(s, 'cancel')
        action(s, 4)                       # native USE activates and takes the knife
        assert byte(s, 'care_tools') & 2 and byte(s, 'it_place', 59) == 3
        action(s, 0)                       # packing does not clear its native use flag
        assert byte(s, 'it_place', 59) == 2 and byte(s, 'care_tools') & 2
        action(s, 1)                       # CARRY changes location, keeps activation
        assert byte(s, 'it_place', 59) == 3
        event(s, 'ok')
        assert byte(s, 'om_mask') == 0x15 and byte(s, 'care_tools') & 2
        event(s, 'cancel')
        assert byte(s, 'pg_cur') == 2 and byte(s, 'eq_selected') == 59
        print('  EQUIPMENT refreshes choices after PACK/USE/CARRY and keeps the active knife selected: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        filters(disk_with(tmp, map_fixture()))
    print('Object action filters: OK')
