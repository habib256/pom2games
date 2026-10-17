#!/usr/bin/env python3
"""Real joystick: quick transfer quantities, exact 16-bit stock and no ALL meals."""
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_joystick_journey import GamePortSession, event, byte, object_item, IDLE, saved_state


def quantity(s):
    return int.from_bytes(s.step(L.peek('om_qty', 2)).data, 'little')


def open_item(s, item, side=0):
    event(s, 'up')
    if byte(s, 'pg_cur') == 0:
        event(s, 'right')
    assert byte(s, 'pg_cur') == 1
    object_item(s, side, item)
    event(s, 'ok')


def leave(s):
    event(s, 'cancel'); event(s, 'cancel'); event(s, 'cancel', IDLE)


def quick(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu); event(s, 'ok', IDLE)
        s.step(L.poke('nature_frequency', 0))
        for stock in (1, 3, 14, 257, 32769, 65535):
            for name, value in (('it_place', 0), ('it_gnd_lo', stock & 255),
                                ('it_gnd_hi', stock >> 8), ('it_pack_lo', 0), ('it_pack_hi', 0)):
                s.step(L.poke(name, value, 25))
            open_item(s, 25)
            event(s, 'ok')
            assert byte(s, 'om_phase') == 1 and quantity(s) == stock
            before = saved_state(s)
            event(s, 'right')
            assert quantity(s) == 1
            value = 1
            while value < stock:
                value = min(value*2, stock)
                event(s, 'right')
                assert quantity(s) == value, (stock, value, quantity(s))
            # Reaching ALL and wrapping must never alter source or simulation.
            assert saved_state(s) == before
            event(s, 'left')
            assert quantity(s) == 1
            if stock > 1:
                event(s, 'up'); assert quantity(s) == 2
                event(s, 'down'); assert quantity(s) == 1
            leave(s)
        print('  Quick doubling, exact ALL, wrap, fine steps and atomic cancel through 65535 OZ: OK', flush=True)

        # An exact partial transfer still goes through explicit confirmation.
        s.step(L.poke('it_gnd_lo', 14, 25)); s.step(L.poke('it_gnd_hi', 0, 25))
        open_item(s, 25)
        event(s, 'ok'); event(s, 'left')
        event(s, 'right'); event(s, 'right'); event(s, 'up')
        assert quantity(s) == 5
        event(s, 'ok')
        assert byte(s, 'om_phase') == 2 and byte(s, 'it_gnd_lo', 25) == 14
        event(s, 'ok')
        assert byte(s, 'it_gnd_lo', 25) == 9 and byte(s, 'it_pack_lo', 25) == 5
        print('  Five ounces selected quickly and transferred only after confirmation: OK', flush=True)
        event(s, 'cancel', IDLE)
        open_item(s, 25, 1)
        assert byte(s, 'om_action') == 2
        event(s, 'ok')
        assert quantity(s) == 5
        for expected in (1, 2, 4, 5):
            event(s, 'right')
            assert quantity(s) == expected
        event(s, 'left'); event(s, 'right'); event(s, 'right')
        event(s, 'ok'); event(s, 'ok')
        assert byte(s, 'it_pack_lo', 25) == 1 and byte(s, 'it_gnd_lo', 25) == 13
        print('  CARRIED DROP uses its own stock and deposits four ounces into the local pile: OK', flush=True)
        object_item(s, 0, 25); event(s, 'ok')
        while byte(s, 'om_action') != 5:
            event(s, 'down')
        event(s, 'ok')
        assert quantity(s) == 1
        event(s, 'right')
        assert quantity(s) == 1
        leave(s)
        print('  EAT retains one-ounce default and no quick ALL consumption: OK', flush=True)

        s.step(L.poke('it_gnd_lo', 9, 22)); s.step(L.poke('it_gnd_hi', 0, 22))
        s.step(L.poke('it_pack_lo', 60, 22)); s.step(L.poke('it_pack_hi', 0, 22))
        open_item(s, 22)
        assert byte(s, 'om_action') == 7
        event(s, 'ok')
        assert quantity(s) == 9
        before = saved_state(s)
        for expected in (1, 2, 4, 8, 9):
            event(s, 'right')
            assert quantity(s) == expected
        assert saved_state(s) == before
        event(s, 'left'); event(s, 'right'); event(s, 'right')
        assert quantity(s) == 4
        event(s, 'ok'); event(s, 'ok')
        assert byte(s, 'it_pack_lo', 22) == 64 and byte(s, 'it_gnd_lo', 22) == 5
        event(s, 'cancel', IDLE)
        open_item(s, 22, 1)
        while byte(s, 'om_action') != 6:
            event(s, 'down')
        event(s, 'ok'); event(s, 'right')
        assert quantity(s) == 1
        leave(s)
        print('  GET water uses ground stock, fills the exact canteen space; DRINK has no ALL: OK', flush=True)

        # The banked command builder must preserve multi-byte decimal quantities.
        s.step(L.poke('it_place', 0, 25))
        s.step(L.poke('it_pack_lo', 0, 25)); s.step(L.poke('it_pack_hi', 0, 25))
        s.step(L.poke('it_gnd_lo', 44, 25)); s.step(L.poke('it_gnd_hi', 1, 25))
        s.step(L.poke('load_limits', 2000 & 255))
        s.step(L.poke('load_limits', 2000 >> 8, 1))
        open_item(s, 25)
        event(s, 'ok'); event(s, 'left')
        for _ in range(8):
            event(s, 'right')
        event(s, 'up')
        assert quantity(s) == 257
        event(s, 'ok'); event(s, 'ok')
        assert int.from_bytes(s.step(L.peek('it_pack_lo', 1, 25)).data +
                              s.step(L.peek('it_pack_hi', 1, 25)).data, 'little') == 257
        assert byte(s, 'it_gnd_lo', 25) == 43 and byte(s, 'it_gnd_hi', 25) == 0
        print('  Banked PACK command preserves the exact 257-ounce decimal quantity: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        quick(disk_with(tmp, map_fixture()))
    print('Quick quantities: OK')
