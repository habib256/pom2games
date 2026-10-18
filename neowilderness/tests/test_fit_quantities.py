#!/usr/bin/env python3
"""Real joystick: explicit FIT quantities, exact native limits and no hidden clamp."""
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_joystick_journey import (
    GamePortSession, event, byte, rows, object_item, saved_state, IDLE,
)
from test_transfer_weight_preview import word, put_word, open_action
from test_save import differing, DERIVED_BYTES


def boot(s):
    menu = L.until('menu_key', 60000)
    s.step(menu); event(s, 'ok', menu); event(s, 'ok', IDLE)
    s.step(L.poke('nature_frequency', 0))


def fixture_word(s, low, high, item, value):
    s.step(L.poke(low, value & 255, item)); s.step(L.poke(high, value >> 8, item))


def set_room(s, slot, free):
    put_word(s, 'load_limits', word(s, 'load_used', slot)+free, slot)


def choose_fit(s, expected):
    assert byte(s, 'om_fit_valid') == 1 and word(s, 'om_fit') == expected
    assert f' FIT {expected}' in rows(s)[21], rows(s)[21]
    event(s, 'ok'); assert byte(s, 'om_phase') == 1
    event(s, 'left'); assert word(s, 'om_qty') == 1
    for _ in range(17):
        if word(s, 'om_qty') == expected:
            return
        event(s, 'right')
    raise AssertionError(('FIT not reachable', expected, word(s, 'om_qty')))


def accept(s, item, amount, before, source):
    assert word(s, 'om_qty') == amount
    event(s, 'ok'); assert byte(s, 'om_phase') == 2
    assert saved_state(s) == before
    projected = s.step(L.peek('om_total', 8)).data
    event(s, 'ok')
    assert s.step(L.peek('load_used', 8)).data == projected
    packed = byte(s, 'it_pack_lo', item) + 256*byte(s, 'it_pack_hi', item)
    ground = byte(s, 'it_gnd_lo', item) + 256*byte(s, 'it_gnd_hi', item)
    assert packed + ground == source
    return packed, ground


def food(disk, source=257, volume=2, weight=37, space=1000, blocked=None, cancel=False, all_refused=False, correction=False):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('it_place', 0, 25))
        fixture_word(s, 'it_pack_lo', 'it_pack_hi', 25, 0)
        fixture_word(s, 'it_gnd_lo', 'it_gnd_hi', 25, source)
        s.step(L.poke('it_vol_lo', volume, 25))
        if blocked == 'bag':
            s.step(L.poke('it_place', 0, 21))
        event(s, 'up'); event(s, 'right')
        if weight is None:
            put_word(s, 'load_limits', 65535)
            put_word(s, 'load_limits', 65535, 4)
        else:
            set_room(s, 0, weight); set_room(s, 4, space)
        if blocked == 'hands':
            set_room(s, 6, -1)
        expected = 0 if blocked else min(source,
            word(s, 'load_limits')-word(s, 'load_used'),
            (word(s, 'load_limits', 4)-word(s, 'load_used', 4))//(volume or 256))
        open_action(s, 0, 25, 0)
        assert word(s, 'om_qty') == source  # Opening keeps ALL, not FIT.
        if byte(s, 'om_bad'):
            assert 'NEED ' not in rows(s)[21] and f' FIT {expected}' in rows(s)[21]
        before = saved_state(s)
        if all_refused:
            event(s, 'ok'); event(s, 'ok'); event(s, 'ok')
            assert not differing(before, saved_state(s), DERIVED_BYTES)
            assert byte(s, 'it_pack_lo', 25) == 0
            open_action(s, 0, 25, 0)
            before = saved_state(s)
        if expected == 0:
            assert word(s, 'om_fit') == 0 and ' FIT 0' in rows(s)[21]
            event(s, 'ok'); event(s, 'left')
            assert word(s, 'om_qty') == 1
            event(s, 'ok'); assert saved_state(s) == before
            event(s, 'ok')
            assert not differing(before, saved_state(s), DERIVED_BYTES)
        else:
            if correction:
                identity = tuple(byte(s, name) for name in ('menu_noun', 'om_side', 'om_action'))
                command = s.step(L.peek('overlay_text', 37)).data
                event(s, 'ok'); event(s, 'ok')
                assert byte(s, 'om_phase') == 2 and word(s, 'om_qty') == source
                assert saved_state(s) == before
                event(s, 'up')  # Deliberately apply the advertised FIT correction.
                assert byte(s, 'om_phase') == 1 and word(s, 'om_qty') == expected
                assert tuple(byte(s, name) for name in ('menu_noun', 'om_side', 'om_action')) == identity
                assert s.step(L.peek('overlay_text', 37)).data == command
                assert saved_state(s) == before, 'FIT correction executed a native command'
            else:
                choose_fit(s, expected)
            if cancel:
                event(s, 'ok'); assert saved_state(s) == before
                event(s, 'cancel'); event(s, 'cancel'); event(s, 'cancel')
                assert not differing(before, saved_state(s), DERIVED_BYTES)
                assert byte(s, 'obj_selected') == 25
            else:
                packed, ground = accept(s, 25, expected, before, source)
                assert packed == expected and ground == source-expected
        print(f'  Food: stock {source}, volume {volume or 256}/oz, FIT {expected}, blocked={blocked}, cancel={cancel}: OK', flush=True)


def water(disk, place=3, source=9, contained=60, weight=100, space=6):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('it_place', place, 64)); s.step(L.poke('it_place', 4, 22))
        fixture_word(s, 'it_pack_lo', 'it_pack_hi', 22, contained)
        fixture_word(s, 'it_gnd_lo', 'it_gnd_hi', 22, source)
        event(s, 'up'); event(s, 'right')
        set_room(s, 0, weight)
        if place in (2, 3):
            set_room(s, place*2, space)
        expected = min(source, 64-contained, weight, space//2) if place in (2, 3) else 0
        code = s.step('peek:9600:256').data
        open_action(s, 0, 22, 7)
        assert s.step('peek:9600:256').data == code
        before = saved_state(s)
        assert word(s, 'om_qty') == source
        if expected:
            choose_fit(s, expected)
            packed, ground = accept(s, 22, expected, before, source+contained)
            assert packed == contained+expected and ground == source-expected
        else:
            assert word(s, 'om_fit') == 0 and ' FIT 0' in rows(s)[21]
            event(s, 'ok'); event(s, 'left'); event(s, 'ok')
            assert s.step('peek:9600:256').data == code and saved_state(s) == before
            event(s, 'ok')
            assert not differing(before, saved_state(s), DERIVED_BYTES)
        print(f'  Water: place {place}, {contained} in canteen, source {source}, FIT {expected}: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        food(disk, all_refused=True)
        food(disk, volume=3, weight=100, space=15)
        food(disk, source=100, volume=0, weight=1000, space=800)
        food(disk, source=65535, volume=1, weight=None)
        food(disk, source=3, weight=1)
        food(disk, source=3, weight=100)
        food(disk, blocked='hands')
        food(disk, blocked='bag')
        food(disk, cancel=True)
        food(disk, correction=True, cancel=True)
        food(disk, correction=True)
        water(disk)
        water(disk, place=2, space=8)
        water(disk, weight=2, space=100)
        water(disk, contained=64)
        water(disk, weight=0)
        water(disk, place=255, contained=0)
        water(disk, source=65535, contained=0, weight=1000, space=1000)
    print('Explicit FIT quantities: OK')
