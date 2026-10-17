#!/usr/bin/env python3
"""Read-only container advice and real joystick remedies, without new blocks."""
from test_joystick_journey import equipment_item
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_joystick_journey import (
    GamePortSession, event, byte, rows, object_item, action, saved_state, IDLE,
)
from test_transfer_weight_preview import open_action, put_word, word
from test_save import differing, DERIVED_BYTES

PACK = 'BACKPACK NEEDED. PICK IT UP WITH CARRY BACKPACK.'
BAG = 'EMPTY THE BACKPACK BEFORE DROPPING. DROP ITS CONTENTS FIRST.'
CAN = 'EMPTY THE CANTEEN BEFORE DROPPING. DRINK WATER OR DROP WATER.'


def refresh(s):
    event(s, 'cancel', IDLE); event(s, 'up')


def preview(s, side, item, target, hint):
    open_action(s, side, item, target)
    before = saved_state(s)
    assert hint in rows(s)[22], rows(s)[22]
    assert '|' not in rows(s)[22] and 'RETURN SELECT' in rows(s)[23]
    if target == 0:
        event(s, 'down')
        assert hint not in rows(s)[22]
        event(s, 'up')
        assert hint in rows(s)[22]
    event(s, 'ok')
    quantity = byte(s, 'om_phase') == 1
    if quantity:
        event(s, 'ok')
    assert byte(s, 'om_phase') == 2 and hint in rows(s)[22]
    assert 'RETURN CONFIRM' in rows(s)[23] and saved_state(s) == before
    for _ in range(3 if quantity else 2):
        event(s, 'cancel')
    assert not differing(before, saved_state(s), DERIVED_BYTES)


def refused(s, side, item, target, text):
    object_item(s, side, item)
    before = saved_state(s)
    action(s, target)
    assert text in '\n'.join(rows(s)[20:23]), rows(s)[20:23]
    assert not differing(before, saved_state(s), DERIVED_BYTES)


def containers(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu); event(s, 'ok', IDLE)
        s.step(L.poke('nature_frequency', 0))
        put_word(s, 'load_limits', 2000)
        event(s, 'up')
        for row, label in ((3, 'HEALTH'), (4, 'ENERGY'), (5, 'MEAL'),
                           (6, 'WATER'), (7, 'BODY')):
            assert label in rows(s)[row][:41], (row, rows(s)[row])
        print('  STATUS: five gauges keep their real rows and line breaks after text banking: OK', flush=True)
        event(s, 'right')

        for place in (0, 5, 255):
            s.step(L.poke('it_place', place, 21)); refresh(s)
            for item in (11, 25, 92):
                preview(s, 0, item, 0, PACK)
                refused(s, 0, item, 0, 'BACKPACK NEEDED')
        s.step(L.poke('it_place', 3, 21)); refresh(s)
        open_action(s, 0, 11, 0)
        assert PACK not in rows(s)[22]
        event(s, 'cancel')
        object_item(s, 0, 11); action(s, 0)
        assert byte(s, 'it_place', 11) == 2
        print('  PACK gear/provisions/craft: ground/hung/absent bag explained; carried bag permits native transfer: OK', flush=True)

        preview(s, 1, 21, 2, BAG)
        refused(s, 1, 21, 2, 'EMPTY THE BACKPACK')
        preview(s, 1, 64, 2, CAN)
        refused(s, 1, 64, 2, 'EMPTY THE CANTEEN')
        object_item(s, 1, 22); action(s, 2)  # Actual remedy: empty water first.
        assert byte(s, 'it_pack_lo', 22) == 0 and byte(s, 'it_pack_hi', 22) == 0
        open_action(s, 1, 64, 2)
        assert CAN not in rows(s)[22]
        event(s, 'cancel')
        object_item(s, 1, 64); action(s, 2)
        assert byte(s, 'it_place', 64) == 0
        print('  DROP CANTEEN: full refusal and read-only preview, then DROP WATER -> accepted empty canteen: OK', flush=True)

        # EQUIPMENT must show the same real DROP prerequisite and keep focus.
        event(s, 'cancel', IDLE)
        event(s, 'up'); event(s, 'right')
        assert byte(s, 'pg_cur') == 2
        event(s, 'ok')
        equipment_item(s, 21)
        event(s, 'ok')
        assert byte(s, 'om_action') == 2 and BAG in rows(s)[22]
        before = saved_state(s)
        event(s, 'ok')
        assert byte(s, 'om_phase') == 2 and BAG in rows(s)[22]
        assert saved_state(s) == before
        event(s, 'cancel'); event(s, 'cancel')
        assert byte(s, 'eq_selected') == 21
        event(s, 'cancel', IDLE)
        event(s, 'up'); event(s, 'left')

        # Follow DROP ITS CONTENTS through actual UI actions, not fixture edits.
        for item in range(1, 76):
            place = byte(s, 'it_place', item)
            if 23 <= item < 38:
                packed = byte(s, 'it_pack_lo', item) or byte(s, 'it_pack_hi', item)
                take = place != 5 and packed
            else:
                take = item != 22 and place == 2
            if take:
                object_item(s, 1, item); action(s, 2)
        assert word(s, 'load_used', 4) == 0
        open_action(s, 1, 21, 2)
        assert BAG not in rows(s)[22]
        event(s, 'cancel')
        object_item(s, 1, 21); action(s, 2)
        assert byte(s, 'it_place', 21) == 0
        print('  EQUIPMENT warning and selection; joystick DROP contents -> empty PACK -> accepted DROP BACKPACK: OK', flush=True)

        # Native wild piles have no backpack prerequisite: do not invent one.
        for name, value in (('fg_x', byte(s, 'px', 1)), ('fg_y', byte(s, 'py', 1))):
            s.step(L.poke(name, value))
        s.step(L.poke('fg_b1', 0, 6)); s.step(L.poke('fg_gl', 3, 6))
        s.step(L.poke('fg_gh', 0, 6)); s.step(L.poke('fg_pl', 0, 6))
        s.step(L.poke('fg_ph', 0, 6)); refresh(s)
        open_action(s, 0, 82, 0)
        assert PACK not in rows(s)[22]
        event(s, 'cancel')
        object_item(s, 0, 82); action(s, 0)
        assert byte(s, 'fg_pl', 6) == 3 and byte(s, 'fg_gl', 6) == 0
        print('  Wild pile PACK remains permitted without a carried backpack, matching native rules: OK', flush=True)

        # The compact usable ranges must preserve every old gear USE choice.
        for item in (9, 11, 12, *range(38, 76)):
            s.step(L.poke('it_place', 2, item))
        s.step(L.poke('it_place', 3, 21)); refresh(s)
        usable = {9, 11, 12, *range(38, 60), 66, 67, 71, 72, 73}
        for item in (9, 11, 12, *range(38, 76)):
            object_item(s, 1, item); event(s, 'ok')
            assert bool(byte(s, 'om_mask') & 16) == (item in usable), item
            event(s, 'cancel')
        print('  All 41 tested gear USE masks match the original supported set: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        containers(disk_with(tmp, map_fixture()))
    print('Container prerequisites: OK')
