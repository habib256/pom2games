#!/usr/bin/env python3
"""Real game-port source labels and carried-canteen prerequisite before GET."""
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_joystick_journey import (
    GamePortSession, event, byte, rows, object_item, saved_state, IDLE,
)
from test_transfer_weight_preview import open_action, put_word
from test_save import differing, DERIVED_BYTES

HINT = 'CARRY A CANTEEN BEFORE COLLECTING WATER.'


def source(s, side, item, label):
    object_item(s, side, item)
    event(s, 'ok')
    before = saved_state(s)
    assert f'FROM {label} TO ' in rows(s)[21], rows(s)[21]
    event(s, 'ok')
    quantity = byte(s, 'om_phase') == 1
    if quantity:
        event(s, 'ok')
    assert byte(s, 'om_phase') == 2
    assert f'FROM {label} TO ' in rows(s)[21], rows(s)[21]
    assert saved_state(s) == before
    for _ in range(3 if quantity else 2):
        event(s, 'cancel')
    assert not differing(before, saved_state(s), DERIVED_BYTES)


def refresh(s):
    event(s, 'cancel', IDLE); event(s, 'up')


def sources(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu); event(s, 'ok', IDLE)
        s.step(L.poke('nature_frequency', 0))
        put_word(s, 'load_limits', 2000)
        # Independent local/carried provision piles, crafted items and hide.
        for name, value in (('it_place', 4), ('it_pack_lo', 3), ('it_pack_hi', 0),
                            ('it_gnd_lo', 5), ('it_gnd_hi', 0)):
            s.step(L.poke(name, value, 25))
        s.step(L.poke('cr_b1', 3, 0)); s.step(L.poke('cr_b1', 2, 1))
        s.step(L.poke('cr_b1', 1, 4))
        s.step(L.poke('fg_pl', 5, 6)); s.step(L.poke('fg_pl', 4, 11))
        event(s, 'up'); event(s, 'right')
        for side, item, label in ((0, 25, 'LOCAL'), (1, 25, 'PACK'),
                                  (1, 66, 'PACK'), (1, 64, 'HANDS'),
                                  (1, 3, 'WORN'), (1, 22, 'CANTEEN'),
                                  (1, 89, 'HANDS'), (1, 90, 'PACK'),
                                  (1, 93, 'WORN'), (1, 82, 'CARRIED'),
                                  (1, 94, 'CARRIED')):
            source(s, side, item, label)
        print('  Exact local/pack/hands/worn/canteen sources; native provisions, crafts and wild piles: OK', flush=True)

        # Missing, hung and grounded canteens all fail explicit GET WATER.
        # Keep the selected amount below the canteen room, so its native
        # missing-container refusal is reached rather than the capacity gate.
        s.step(L.poke('it_pack_lo', 0, 22)); s.step(L.poke('it_pack_hi', 0, 22))
        for place in (0, 5, 255):
            s.step(L.poke('it_place', place, 64))
            refresh(s)
            code = s.step('peek:9600:256').data
            open_action(s, 0, 22, 7)
            assert s.step('peek:9600:256').data == code, 'water forecast overwrote STATUS code'
            before = saved_state(s)
            assert HINT in rows(s)[22], rows(s)[22]
            event(s, 'up')
            assert byte(s, 'om_action') == 6 and HINT not in rows(s)[22]
            event(s, 'down')
            assert HINT in rows(s)[22]
            event(s, 'ok'); event(s, 'left'); event(s, 'ok')
            assert byte(s, 'om_phase') == 2 and HINT in rows(s)[22]
            assert s.step('peek:9600:256').data == code
            assert saved_state(s) == before
            event(s, 'cancel'); event(s, 'cancel'); event(s, 'cancel')
            assert not differing(before, saved_state(s), DERIVED_BYTES)
            open_action(s, 0, 22, 7)
            event(s, 'ok'); event(s, 'left'); event(s, 'ok'); event(s, 'ok')
            assert 'CANTEEN NEEDED' in '\n'.join(rows(s)[20:23]), rows(s)[20:23]
            assert not differing(before, saved_state(s), DERIVED_BYTES)
        print('  Ground/hung/absent canteen: GET prerequisite, action change, read-only cancel, native atomic refusal: OK', flush=True)

        for place, destination in ((2, 'PACK'), (3, 'HANDS')):
            s.step(L.poke('it_place', place, 64))
            refresh(s)
            open_action(s, 0, 22, 7)
            assert f'TO CANTEEN/{destination}' in rows(s)[21]
            assert HINT not in rows(s)[22] and 'CAN FREE 64 OZ' in rows(s)[22]
            event(s, 'ok'); event(s, 'left'); event(s, 'ok'); event(s, 'ok')
            assert byte(s, 'it_pack_lo', 22) == 1
            s.step(L.poke('it_pack_lo', 0, 22))
        print('  Carried canteen: PACK/HANDS destination, exact room and successful GET at the game port: OK', flush=True)

        refresh(s)
        event(s, 'cancel', IDLE); event(s, 'up'); event(s, 'right')
        assert byte(s, 'pg_cur') == 2
        event(s, 'ok')
        entries = s.step(L.peek('overlay_text', byte(s, 'eq_n'))).data
        target = entries.index(66)
        for _ in range(140):
            if byte(s, 'eq_cur') == target:
                break
            event(s, 'up' if byte(s, 'eq_cur') > target else 'down')
        event(s, 'ok')
        before = saved_state(s)
        assert 'FROM PACK TO ' in rows(s)[21], rows(s)[21]
        event(s, 'ok')
        assert 'FROM PACK TO ' in rows(s)[21] and saved_state(s) == before
        event(s, 'cancel'); event(s, 'cancel')
        assert byte(s, 'eq_selected') == 66
        print('  EQUIPMENT uses the same precise source and preserves selection on cancel: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        sources(disk_with(tmp, map_fixture()))
    print('Transfer sources and containers: OK')
