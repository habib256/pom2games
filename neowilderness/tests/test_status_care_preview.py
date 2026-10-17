#!/usr/bin/env python3
"""STATUS care information through real joystick events; previews stay read-only."""
import tempfile
from common import L, disk_with, fp
from test_forest import map_fixture
from test_fit_quantities import boot
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, IDLE

GESTURES = ((1, 2), (3,), (3,), (4, 5), (5, 6), (7, 8), (9,),
            (10, 11, 12), (13,), (14,), (5,), (15,), (16,))
MINUTES = (30, 30, 30, 0, 0, 0, 0, 0, 0, 30, 0, 15, 30, 0, 0, 0)
ITEMS = {7: 43, 10: 42, 13: 41, 14: 48, 15: 47, 16: 50}
HINTS = ('NO ITEM NEEDED', 'NO ITEM NEEDED', 'SPLINT REQUIRED', 'WATER ALSO NEEDED',
         'WATER OZ NEXT', 'RAIN/WATER OR OZ NEXT', 'ITEM REQUIRED', 'SUNGLASSES ALSO HELP',
         'FIRE NEEDED', 'ITEM REQUIRED', 'BLADE AVAILABLE; USE KNIFE/AXE FIRST',
         'ACTIVE BITE REQUIRED', 'LIGHT NEEDED; FLASHLIGHT IF DARK',
         'ITEM REQUIRED', 'ITEM REQUIRED', 'ITEM REQUIRED')


def activate(s):
    for i in range(13):
        s.step(L.poke('injury_active', 1, i))
        s.step(L.poke('injury_treated', 0, i))
    for item in ITEMS.values():
        s.step(L.poke('it_place', 2, item))
        s.step(L.poke('it_pack_lo', 2, item)); s.step(L.poke('it_pack_hi', 0, item))
    s.step(L.poke('light', 0))


def matrix(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s); activate(s); event(s, 'up')
        legend = rows(s)[15]
        for phrase in ('ACTIVE: NEEDS CARE', 'TREATED: CARE GIVEN', 'PROTECTED: PREVENTION'):
            assert phrase in legend, legend
        assert 'SEVERE CUTS' in rows(s)[16] and 'ALTITUDE SICKNESS' in rows(s)[19]
        event(s, 'down')
        before = saved_state(s)
        count = 0
        for condition, gestures in enumerate(GESTURES, 1):
            assert byte(s, 'pg_focus') == condition
            for index, gesture in enumerate(gestures):
                line = rows(s)[22]
                assert f'{MINUTES[gesture-1]} MIN; {HINTS[gesture-1]}' in line, (condition, index, line)
                if gesture in ITEMS:
                    assert '; HERE' in line, line
                    if gesture != 7:
                        assert '; DOSES 2' in line, line
                if gesture == 13:
                    assert '; DARK' in line, line
                assert 'ESC VIEW' in rows(s)[23]
                assert saved_state(s) == before
                count += 1
                if index+1 < len(gestures):
                    event(s, 'right')
            if condition < 13:
                event(s, 'down')
        assert count == 19
        event(s, 'cancel', IDLE)
        assert saved_state(s) == before
        print('  Three state explanations, 19 gesture previews, native minutes, presence/doses/light, read-only navigation/cancel: OK', flush=True)


def kit(disk, stock, light, place=2, execute=False):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('injury_active', 1, 8))
        s.step(L.poke('it_place', place, 41))
        s.step(L.poke('it_pack_lo', stock & 255, 41)); s.step(L.poke('it_pack_hi', stock >> 8, 41))
        s.step(L.poke('light', light))
        if execute and not light:
            s.step(L.poke('it_place', 2, 66))
            s.step(L.poke('it_pack_lo', 2, 66)); s.step(L.poke('it_pack_hi', 0, 66))
        event(s, 'up'); event(s, 'down')
        line = rows(s)[22]
        assert line.startswith('30 MIN; LIGHT NEEDED; FLASHLIGHT IF DARK'), line
        if place == 255:
            assert '; NOT HERE' in line and 'DOSES' not in line, line
        else:
            assert f'; DOSES {stock if stock < 32768 else 0}' in line, line
            assert ('; LIT' if light else '; DARK') in line, line
        before = saved_state(s)
        event(s, 'right'); event(s, 'left')  # one gesture wraps without changing the journey
        assert saved_state(s) == before and rows(s)[22] == line
        if execute:
            elapsed = fp(s.step(L.peek('s_elap', 5)).data)
            event(s, 'ok', L.until('q_care_wait', 60000))
            event(s, 'cancel', IDLE)
            assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-.5) < 1e-6
            actual = byte(s, 'it_pack_lo', 41)+256*byte(s, 'it_pack_hi', 41)
            assert actual == (stock-1 if 0 < stock < 32768 else stock)
        print(f'  First aid stock {stock}, light {light}, place {place}; preview and native use={execute}: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        matrix(disk)
        kit(disk, 2, 0)
        kit(disk, 2, 0, execute=True)
        kit(disk, 2, 1, execute=True)
        kit(disk, 0, 1, execute=True)
        kit(disk, 65535, 1, execute=True)
        kit(disk, 32767, 1)
        kit(disk, 0, 1, place=255)
    print('STATUS care preview: OK')
