#!/usr/bin/env python3
"""Joystick QUICK inspection, deliberate destinations and concrete warnings."""
from common import DISK, L
from test_guidance import start, state
from test_joystick_journey import GamePortSession, event, byte, rows, IDLE


def open_quick(s):
    event(s, 'down', IDLE)
    for _ in range(32):
        if byte(s, 'mn_idx', byte(s, 'mn_cur')) == 126:
            break
        event(s, 'right', IDLE)
    assert byte(s, 'mn_idx', byte(s, 'mn_cur')) == 126, rows(s)
    before = state(s)
    event(s, 'ok')
    assert all(word in rows(s)[20] for word in ('CAMP', 'NEXT ACTION', 'MAP')), rows(s)
    assert state(s) == before, 'Opening QUICK changed simulation or RNG'
    return before


def choose(s, choice):
    for _ in range(4):
        if byte(s, 'menu_duration') == choice:
            return
        event(s, 'right')
    raise AssertionError('QUICK focus did not reach requested choice')


def inspection_and_memory():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        before = open_quick(s)
        for _ in range(6):
            event(s, 'down')
            assert state(s) == before
        choose(s, 2)
        event(s, 'cancel', IDLE)
        assert state(s) == before
        open_quick(s)
        assert byte(s, 'menu_duration') == 2, 'QUICK forgot deliberate focus'
        event(s, 'cancel', IDLE)
    print('QUICK browsing/cancel preserve simulation and remember focus')


def destinations():
    for choice in (0, 1, 2):
        with GamePortSession(DISK, menu=False) as s:
            start(s)
            if choice == 1:
                s.step(L.poke('thermal_mode', 0))
                s.step(L.poke('wet_mode', 0))
                s.step(L.poke('weak_health', 0))
                s.step(L.poke('ui_previous', 1, 5))  # observed thirst worsening
            before = open_quick(s)
            choose(s, choice)
            event(s, 'ok')
            text = ' '.join(rows(s))
            if choice == 0:
                assert 'CAMP - CHOOSE ONE ACTION' in text, rows(s)
            elif choice == 1:
                assert 'SURVIVAL GUIDE' in text and byte(s, 'dep_cursor') == 1, rows(s)
            else:
                assert 'CURSOR: CHOOSE A MAP POINT' in text, rows(s)
            assert state(s) == before, 'QUICK destination executed an action'
            if choice == 2:
                event(s, 'cancel')  # planner chooser returns to its native MAP
                assert state(s) == before
            event(s, 'cancel', IDLE)
            assert state(s) == before
    print('CAMP, NEXT ACTION and MAP open deliberately without simulation')


def warnings():
    for warning in ('FIRE STILL BURNING HERE.', 'NO CARRIED WATER STOCK.',
                    'NO CARRIED FOOD STOCK.', 'A CARRYING CAPACITY IS FULL.'):
        with GamePortSession(DISK, menu=False) as s:
            start(s)
            s.step(L.poke('fire_on', int(warning.startswith('FIRE'))))
            water = 0 if 'WATER STOCK' in warning else 8
            s.step(L.poke('it_place', 2, 22))
            s.step(L.poke('it_pack_lo', water, 22))
            s.step(L.poke('it_pack_hi', 0, 22))
            for noun in (*range(23, 38), *range(76, 87)):
                s.step(L.poke('it_pack_lo', 0, noun))
                s.step(L.poke('it_pack_hi', 0, noun))
            if 'FOOD STOCK' not in warning:
                s.step(L.poke('it_place', 2, 23))
                s.step(L.poke('it_pack_lo', 8, 23))
            # Capacity is inspected from the native totals already calculated
            # by the item commands. Fixture sets a concrete full pack volume.
            if 'CAPACITY' in warning:
                limit = s.step(L.peek('load_limits', 2, 4)).data
                for offset, value in enumerate(limit, 4):
                    s.step(L.poke('load_used', value, offset))
            before = open_quick(s)
            assert warning in rows(s)[21], rows(s)
            assert 'FIX:' in rows(s)[20], rows(s)
            choose(s, 3)
            assert state(s) == before, 'Selecting FIX changed simulation'
            event(s, 'cancel', IDLE)
            assert state(s) == before
    print('QUICK warnings reflect observed fire, stock and carrying capacity')




def fire_correction():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        s.step(L.poke('fire_on', 1))
        before = open_quick(s)
        choose(s, 3)
        event(s, 'ok')
        assert 'DOUSE THIS FIRE?' in ' '.join(rows(s)), rows(s)
        assert state(s) == before, 'Reviewing DOUSE changed simulation'
        event(s, 'cancel')
        assert 'FIX: DOUSE' in rows(s)[20], rows(s)
        assert byte(s, 'menu_duration') == 3
        assert state(s) == before, 'Cancelling DOUSE changed simulation'
        event(s, 'ok')
        event(s, 'ok', IDLE)
        assert byte(s, 'fire_on') == 0, rows(s)
        assert byte(s, 'menu_duration') == 3, 'Correction lost QUICK intent'
    print('QUICK fire correction requires confirmation and preserves focus')

def resource_corrections():
    # Exact native ground sources remain accessible when no stock is carried.
    for noun, verb, label in ((22, 6, 'DRINK'), (25, 5, 'EAT')):
        with GamePortSession(DISK, menu=False) as s:
            start(s)
            s.step(L.poke('fire_on', 0))
            for food in (*range(23, 38), *range(76, 87)):
                s.step(L.poke('it_pack_lo', 0, food))
                s.step(L.poke('it_pack_hi', 0, food))
            s.step(L.poke('it_place', 2, 22))
            s.step(L.poke('it_pack_lo', 0 if noun == 22 else 8, 22))
            s.step(L.poke('it_pack_hi', 0, 22))
            for name, value in (('it_place', 0), ('it_gnd_lo', 8), ('it_gnd_hi', 0)):
                s.step(L.poke(name, value, noun))
            s.step(L.poke('it_x', byte(s, 'px', 1), noun))
            s.step(L.poke('it_y', byte(s, 'py', 1), noun))
            before = open_quick(s)
            assert 'FIX: ' + label in rows(s)[20], rows(s)
            choose(s, 3)
            native_form = f'until:{L["keyboard_wait"]:04X},{L["idle"]:04X}:60000'
            event(s, 'ok', native_form)
            assert byte(s, 'mn_verb') == verb, rows(s)
            assert state(s) == before, 'Resource correction consumed without confirmation'
            event(s, 'cancel', IDLE)
            assert state(s) == before
    print('QUICK resource corrections open live native source selection read-only')


if __name__ == '__main__':
    inspection_and_memory()
    destinations()
    warnings()
    fire_correction()
    resource_corrections()
