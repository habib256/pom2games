#!/usr/bin/env python3
"""NEXT ACTION selects advice through the game port, never executes it."""
from common import DISK, L
from test_guidance import start, state
from test_joystick_journey import GamePortSession, event, byte, rows, IDLE


def open_priority(s):
    event(s, 'up')
    for _ in range(7):
        if byte(s, 'pg_cur') == 6:
            break
        event(s, 'left')
    assert byte(s, 'pg_cur') == 6
    for _ in range(7):
        event(s, 'down')
    assert byte(s, 'pg_focus') == 7
    assert 'NEXT ACTION' in ' '.join(rows(s))
    before = state(s)
    event(s, 'ok')
    return before


def main():
    for flag, value, topic in (('ui_previous', 1, 1),
                               ('ui_previous', 2, 0),
                               ('ui_previous', 4, 2),
                               ('thermal_mode', 2, 3),
                               ('night', 1, None)):
        with GamePortSession(DISK, menu=False) as s:
            start(s)
            for index in (0, 1, 5):
                s.step(L.poke('ui_previous', 0, index))
            s.step(L.poke('weak_health', 0))
            s.step(L.poke('thermal_mode', 0))
            s.step(L.poke('wet_mode', 0))
            s.step(L.poke('night', 0))
            s.step(L.poke(flag, value, 5 if flag == 'ui_previous' else 0))
            before = open_priority(s)
            if topic is None:
                assert 'PREPARE NIGHT' in ' '.join(rows(s)), rows(s)
            else:
                assert 'SURVIVAL GUIDE' in ' '.join(rows(s)), rows(s)
                assert byte(s, 'dep_cursor') == topic, (flag, value, rows(s))
            assert state(s) == before, (flag, value, 'advice executed simulation')
            event(s, 'cancel', IDLE)
            assert state(s) == before, (flag, value, 'cancel changed simulation')
    print('NEXT ACTION: thirst, hunger, fatigue, cold and night advice; inspection/cancel preserve state and RNG: OK')
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        for index in range(13):
            s.step(L.poke('injury_active', 0, index))
        s.step(L.poke('weak_health', 1))
        s.step(L.poke('thermal_mode', 0))
        s.step(L.poke('wet_mode', 0))
        s.step(L.poke('ui_previous', 2, 5))
        before = open_priority(s)
        assert byte(s, 'dep_cursor') == 0, 'Weakness without an injury must still address hunger'
        assert state(s) == before
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('Weakness without active injury retains actionable food advice: OK')
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        s.step(L.poke('game_options', byte(s, 'game_options') & ~0x40))
        for name in ('weak_health', 'thermal_mode', 'wet_mode', 'night'):
            s.step(L.poke(name, 0))
        for index in (0, 1, 5):
            s.step(L.poke('ui_previous', 0, index))
        before = open_priority(s)
        from test_route_planning import assert_map_drawn
        assert_map_drawn(s)
        assert state(s) == before
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('No urgent need: map inspection and cancellation preserve simulation and RNG: OK')


if __name__ == '__main__':
    main()
