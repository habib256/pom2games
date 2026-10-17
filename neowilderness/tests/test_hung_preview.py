#!/usr/bin/env python3
"""Whole hung-pack forecast equals native recovery without tentative mutation."""
import tempfile
from common import L, a2test, disk_with
from test_forest import map_fixture
from test_objects import state, rows
from test_object_actions import command, select, key, confirm, stock, IDLE


def read(s, name, n=1, offset=0):
    return s.step(L.peek(name, n, offset)).data


def word(s, name, offset=0):
    return int.from_bytes(read(s, name, 2, offset), 'little')


def run(packed_can, refuse=False, slot=0):
    with tempfile.TemporaryDirectory() as tmp:
        with a2test.Session(disk_with(tmp, map_fixture())) as s:
            s.step(IDLE)
            stock(s, 8, 3)  # independent candy pile on ground and in the bag
            if packed_can:
                command(s, 'PACK CANTEEN')
            command(s, 'HANG FOOD')
            assert read(s, 'it_place', 1, 21) == b'\5'
            select(s, 0, 21)
            before = state(s)
            rng = read(s, 'weather_seed', 4), read(s, 'fauna_rng')
            forecast = read(s, 'om_total', 8)
            assert forecast[:2] != read(s, 'load_used', 2)
            delta = int.from_bytes(forecast[:2], 'little') - word(s, 'load_used')
            assert f' WT {delta:+d} OZ' in rows(s)[21], rows(s)[21]
            assert 'FREE AFTER:' in rows(s)[22], rows(s)[22]
            need = int.from_bytes(forecast[4:6], 'little') - word(s, 'load_used', 4)
            assert f'PACK NEED {need} IN3' in rows(s)[21], rows(s)[21]
            assert 'CARRIED ALL CONTENTS' in rows(s)[21], rows(s)[21]
            for _ in range(3):
                key(s, '\\v')  # only LOWER exists, so redraw the same forecast
                assert read(s, 'om_total', 8) == forecast
                assert state(s) == before
                assert (read(s, 'weather_seed', 4), read(s, 'fauna_rng')) == rng
            if refuse:
                used = int.from_bytes(forecast[slot:slot+2], 'little')
                s.step(L.poke('load_limits', (used-1) & 255, slot))
                s.step(L.poke('load_limits', (used-1) >> 8, slot+1))
                key(s, '\\v')
                assert ('AFTER: OVER 1 OZ' if slot == 0 else 'PACK OVER 1 IN3') in rows(s)[22], rows(s)[22]
                confirm(s)
                assert state(s) == before
                assert 'LOAD CAPACITY' in ' '.join(rows(s)[20:23])
            else:
                elapsed = read(s, 's_elap', 5)
                confirm(s)
                assert read(s, 'load_used', 8) == forecast
                assert read(s, 's_elap', 5) == elapsed
                assert read(s, 'it_pack_lo', 1, 25) == b'\10'
                assert read(s, 'it_gnd_lo', 1, 25) == b'\3'
                assert read(s, 'it_place', 1, 21) != b'\5'
    print(f'  canteen {"packed" if packed_can else "held"}, {"refused" if refuse else "accepted"}: forecast exact, no double water/pack volume, stock/time/RNG preserved: OK')


def overflow():
    with tempfile.TemporaryDirectory() as tmp:
        with a2test.Session(disk_with(tmp, map_fixture())) as s:
            s.step(IDLE)
            command(s, 'HANG FOOD')
            s.step(L.poke('it_place', 5, 25))
            s.step(L.poke('it_pack_lo', 255, 25))
            s.step(L.poke('it_pack_hi', 255, 25))
            select(s, 0, 21)
            before = state(s)
            assert read(s, 'om_bad') != b'\0'
            assert 'OVERFLOW' in rows(s)[22], rows(s)[22]
            assert 'PACK NEED' not in rows(s)[21], rows(s)[21]
            assert ' WT ' not in rows(s)[21], rows(s)[21]
            confirm(s)
            assert state(s) == before
            assert 'LOAD CAPACITY' in ' '.join(rows(s)[20:23])
    print('  aggregate overflow is flagged before confirmation; native refusal preserves hung stock: OK')


if __name__ == '__main__':
    run(False)
    run(True)
    run(True, refuse=True)
    run(True, refuse=True, slot=4)
    overflow()
