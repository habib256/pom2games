#!/usr/bin/env python3
"""Joystick transfer forecasts: signed load change, cumulative excess and no mutation."""
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_joystick_journey import (
    GamePortSession, event, byte, rows, object_item, saved_state, IDLE,
)
from test_save import differing, DERIVED_BYTES


def word(s, name, offset=0):
    return int.from_bytes(s.step(L.peek(name, 2, offset)).data, 'little')


def put_word(s, name, value, offset=0):
    s.step(L.poke(name, value & 255, offset))
    s.step(L.poke(name, value >> 8, offset+1))


def open_action(s, side, item, target):
    object_item(s, side, item)
    event(s, 'ok')
    for _ in range(8):
        if byte(s, 'om_action') == target:
            return
        event(s, 'down')
    raise AssertionError((item, target, rows(s)))


def check_preview(s, side, item, target, delta, quantity=None, commit=True):
    open_action(s, side, item, target)
    before = saved_state(s)
    if quantity is not None:
        event(s, 'ok'); assert byte(s, 'om_phase') == 1
        event(s, 'left')
        for _ in range(quantity-1):
            event(s, 'up')
    expected = f' WT {delta:+d} OZ'
    assert expected in rows(s)[21], (expected, rows(s)[21])
    projected = word(s, 'om_total')
    current = word(s, 'load_used')
    assert projected-current == delta
    # Quantity and confirmation remain read-only. The help stays on row 23.
    event(s, 'ok')
    assert byte(s, 'om_phase') == 2 and expected in rows(s)[21]
    assert 'RETURN CONFIRM' in rows(s)[23]
    assert saved_state(s) == before
    if commit:
        event(s, 'ok')
        assert word(s, 'load_used') == projected
    else:
        event(s, 'cancel'); event(s, 'cancel')
        assert not differing(before, saved_state(s), DERIVED_BYTES)


def transfers(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu); event(s, 'ok', IDLE)
        s.step(L.poke('nature_frequency', 0))
        # Controlled capacities make accepted forecasts independent of the
        # normal 43-ounce opening margin; source stocks remain native.
        put_word(s, 'load_limits', 4000)
        event(s, 'up'); event(s, 'right')
        check_preview(s, 0, 25, 0, 5, quantity=5)
        check_preview(s, 1, 25, 2, -3, quantity=3)
        check_preview(s, 0, 11, 1, 45)
        check_preview(s, 1, 11, 0, 0)
        check_preview(s, 1, 11, 1, 0, commit=False)
        check_preview(s, 1, 11, 2, -45)
        check_preview(s, 1, 2, 3, 0)
        check_preview(s, 1, 2, 1, 0)
        check_preview(s, 1, 2, 0, 0)
        print('  Food pickup/drop, ground gear and PACK/HANDS/WORN moves: exact signed load forecast = native: OK', flush=True)

        # Exercise both signs beyond signed-16 range. This fixture changes
        # only ground gear weight; the transfer still runs the native rules.
        put_word(s, 'load_limits', 65535)
        s.step(L.poke('it_oz_lo', 40000 & 255, 11))
        s.step(L.poke('it_oz_hi', 40000 >> 8, 11))
        check_preview(s, 0, 11, 1, 40000)
        check_preview(s, 1, 11, 2, -40000)
        s.step(L.poke('it_oz_lo', 45, 11)); s.step(L.poke('it_oz_hi', 0, 11))
        print('  +40000 and -40000 OZ keep their true sign and match native accepted transfers: OK', flush=True)

        # Both packed and hand-held canteens include the newly fetched water
        # once in weight, with the native destination-specific volume.
        for target_place in (2, 3):
            check_preview(s, 1, 64, 0 if target_place == 2 else 1, 0)
            s.step(L.poke('it_pack_lo', 10, 22)); s.step(L.poke('it_pack_hi', 0, 22))
            event(s, 'cancel', IDLE); event(s, 'up')  # settle the fixture's load
            check_preview(s, 0, 22, 7, 5, quantity=5)
            check_preview(s, 1, 22, 2, -4, quantity=4)
        print('  Water GET/DROP: packed/held canteen, exact ounces and unchanged help row: OK', flush=True)

        # Preview both native failures before confirming, without hiding one
        # behind another. Rejection must preserve the stock and the clock.
        for target, slot, label in ((1, 6, 'HANDS'), (0, 4, 'PACK')):
            for offset in (0, slot):
                put_word(s, 'load_limits', word(s, 'load_used', offset), offset)
            open_action(s, 0, 11, target)
            before = saved_state(s)
            weight = word(s, 'om_total')-word(s, 'load_limits')
            volume = word(s, 'om_total', slot)-word(s, 'load_limits', slot)
            assert weight == 45 and volume > 0
            assert f'OVER {weight} OZ' in rows(s)[22], rows(s)[22]
            assert f'{label} OVER {volume}' in rows(s)[22], rows(s)[22]
            assert ' WT +45 OZ' in rows(s)[21]
            event(s, 'ok')
            assert saved_state(s) == before
            event(s, 'ok')
            assert not differing(before, saved_state(s), DERIVED_BYTES)
            assert 'WEIGHT' in '\n'.join(rows(s)[20:23])
        print('  Simultaneous weight/HANDS and weight/PACK excess before confirmation; native refusal atomic: OK', flush=True)

        event(s, 'cancel', IDLE)
        event(s, 'up'); event(s, 'left'); event(s, 'left')
        assert byte(s, 'pg_cur') == 6
        event(s, 'ok')
        entries = s.step(L.peek('overlay_text', byte(s, 'eq_n'))).data
        target = entries.index(2)  # Packed parka: wearing it changes no total weight.
        for _ in range(140):
            if byte(s, 'eq_cur') == target:
                break
            event(s, 'up' if byte(s, 'eq_cur') > target else 'down')
        event(s, 'ok')
        for _ in range(8):
            if byte(s, 'om_action') == 3:
                break
            event(s, 'down')
        assert byte(s, 'om_action') == 3
        before = saved_state(s)
        assert ' WT +0 OZ' in rows(s)[21]
        event(s, 'ok')
        assert byte(s, 'om_phase') == 2 and ' WT +0 OZ' in rows(s)[21]
        assert saved_state(s) == before
        event(s, 'cancel'); event(s, 'cancel')
        assert byte(s, 'eq_selected') == 2
        assert not differing(before, saved_state(s), DERIVED_BYTES)
        print('  EQUIPMENT shares the weight preview and preserves selection/state on cancel: OK', flush=True)




if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        transfers(disk_with(tmp, map_fixture()))
    print('Transfer weight previews: OK')
