#!/usr/bin/env python3
"""The survival guide is reachable from MENU with only the game port."""
from common import DISK, L, a2test
from test_fit_quantities import boot
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, IDLE


def menu_guide():
    with GamePortSession(DISK, menu=False) as s:
        boot(s)
        event(s, 'up'); event(s, 'left')
        assert byte(s, 'pg_cur') == 6 and byte(s, 'pg_focus') == 0
        assert 'SURVIVAL' in '\n'.join(rows(s))
        before = saved_state(s)
        for _ in range(5):
            event(s, 'down')
        assert byte(s, 'pg_focus') == 5
        event(s, 'ok')
        assert 'SURVIVAL GUIDE' in rows(s)[0]
        assert saved_state(s) == before
        for _ in range(4):
            event(s, 'down')
            assert saved_state(s) == before
        event(s, 'cancel', IDLE)
        assert saved_state(s) == before
    print('  MENU fifth choice opens SURVIVAL by joystick; browsing and cancellation preserve native state: OK')


def native_reentry():
    from test_input import command, snapshot
    from test_object_actions import key
    for rest in (False, True):
        results = []
        for menu in (False, True):
            with a2test.Session(DISK) as s:
                s.step(IDLE)
                s.step(L.poke('nature_frequency', 0))
                command(s, 'PACK CANDYBARS 2 OZ')
                assert byte(s, 'it_pack_lo', 25) == 2
                if menu:
                    s.step('key:STATUS\\r')
                    s.step(L.until('keyboard_wait', 60000))
                    key(s, '\\<')
                    s.step('press:\\e'); s.step(IDLE)
                if rest:
                    command(s, 'REST 1 MIN')
                command(s, 'EAT CANDYBARS 1 OZ')
                assert byte(s, 'it_pack_lo', 25) == 1
                results.append(snapshot(s))
        assert results[0] == results[1], ('MENU changed native REST/EAT', rest)
    print('  Native EAT directly after MENU and after MENU/REST matches the untouched command path: OK')


if __name__ == '__main__':
    menu_guide()
    native_reentry()
