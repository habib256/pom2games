#!/usr/bin/env python3
"""Survival advice, native action menus and cancellation through the game port."""
from common import DISK, L
from test_joystick_journey import (
    GamePortSession, event, byte, saved_state, rows, IDLE, READY,
)


def start(s):
    menu = L.until('menu_key', 60000)
    s.step(menu)
    event(s, 'ok', menu)
    for _ in range(3):
        event(s, 'up', menu)
    event(s, 'ok', IDLE)
    s.step(L.poke('nature_frequency', 0))


def state(s):
    return (saved_state(s), s.step(L.peek('weather_seed', 4)).data)


def open_guide(s):
    event(s, 'up')
    for _ in range(7):
        if byte(s, 'pg_cur') == 6:
            break
        event(s, 'left')
    assert byte(s, 'pg_cur') == 6
    while byte(s, 'pg_focus') < 5:
        event(s, 'down')
    before = state(s)
    event(s, 'ok')
    assert 'SURVIVAL GUIDE' in ' '.join(rows(s)), rows(s)
    assert byte(s, 'dep_cursor') == 0
    return before


def open_status_need(s, focus):
    """Select the visible STATUS gauge with the real game port."""
    event(s, 'up')
    for _ in range(7):
        if byte(s, 'pg_cur') == 0:
            break
        event(s, 'right')
    assert byte(s, 'pg_cur') == 0
    assert byte(s, 'pg_focus') == 0
    before = state(s)
    for _ in range(focus):
        event(s, 'down')
    assert byte(s, 'pg_focus') == focus
    assert [rows(s)[r][1:7].strip() for r in range(3, 8)] == [
        'HEALTH', 'ENERGY', 'MEAL', 'WATER', 'BODY']
    event(s, 'ok')
    return before


def direct_status_needs():
    for focus, topic, hint in ((2, 2, 'REST 30 MIN'), (3, 0, 'UP TO 4 OZ'),
                                (4, 1, 'UP TO 8 OZ'), (5, 3, 'BODY')):
        with GamePortSession(DISK, menu=False) as s:
            start(s)
            before = open_status_need(s, focus)
            assert byte(s, 'dep_cursor') == topic, rows(s)
            assert hint in ' '.join(rows(s)), rows(s)
            assert state(s) == before
            event(s, 'cancel', IDLE)
            assert state(s) == before
            event(s, 'up')
            assert byte(s, 'pg_cur') == 0 and byte(s, 'pg_focus') == 0
    print('STATUS joystick gauges open their advice directly; cancel preserves state and remembered tab: OK')


def direct_health():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        s.step(L.poke('injury_active', 1, 0))
        # Render once before comparing: medical_apply refreshes derived health.
        event(s, 'up'); event(s, 'cancel', IDLE)
        before = open_status_need(s, 1)
        assert byte(s, 'pg_focus') == 6
        assert 'STOP BLEEDING' in rows(s)[23], rows(s)
        assert state(s) == before
        event(s, 'down')
        assert 'ALL CONDITIONS' in rows(s)[23]
        event(s, 'ok')
        assert byte(s, 'st_all') == 1
        assert state(s) == before
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('STATUS HEALTH enters active care and keeps the full catalogue accessible: OK')


def cancellation():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        before = open_guide(s)
        assert 'UP TO 4 OZ' in ' '.join(rows(s)), rows(s)
        assert 'AVAILABLE HERE' in ' '.join(rows(s)), rows(s)
        assert 'RANGERS' not in ' '.join(rows(s)), rows(s)
        for fragment in ('UP TO 8 OZ', 'REST 30 MIN', 'MAKE THEN USE FIRE'):
            event(s, 'down')
            assert fragment in ' '.join(rows(s)), rows(s)
            assert state(s) == before
        event(s, 'up')
        assert byte(s, 'dep_cursor') == 2
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('Guide inspection and cancellation preserve stocks, clock and RNG: OK')


def missing_matches():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        s.step(L.poke('it_place', 255, 38))
        s.step(L.poke('it_pack_lo', 0, 38))
        s.step(L.poke('it_pack_hi', 0, 38))
        s.step(L.poke('fire_on', 0))
        before = open_guide(s)
        for _ in range(3):
            event(s, 'down')
        assert 'NEED MATCHES WITH USES LEFT' in ' '.join(rows(s)), rows(s)
        assert state(s) == before
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('Cold guidance identifies missing native ignition prerequisite: OK')


def no_food():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        for name in ('it_pack_lo', 'it_pack_hi', 'it_gnd_lo', 'it_gnd_hi'):
            for item in range(23, 38):
                s.step(L.poke(name, 0, item))
        for name in ('fg_pl', 'fg_ph', 'fg_gl', 'fg_gh'):
            for item in range(11):
                s.step(L.poke(name, 0, item))
        before = open_guide(s)
        assert 'NO FOOD HERE: FORAGE OR HUNT' in ' '.join(rows(s)), rows(s)
        assert state(s) == before
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('Guide distinguishes absent edible stock from available provisions: OK')


def low_stock():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        for name in ('it_pack_lo', 'it_pack_hi', 'it_gnd_lo', 'it_gnd_hi'):
            for item in range(23, 38):
                s.step(L.poke(name, 0, item))
        s.step(L.poke('it_gnd_lo', 1, 23))
        before = open_guide(s)
        assert 'NUTS: TRY 1 OZ' in ' '.join(rows(s)), rows(s)
        assert state(s) == before
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('One ounce available produces a one ounce suggestion without consuming: OK')


def hot_body():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        # The displayed thermal assessment is interface state, not a world edit.
        open_guide(s)
        s.step(L.poke('thermal_mode', 1))
        before = state(s)
        for _ in range(3):
            event(s, 'down')
        assert 'HOT: SEEK SHADE, REST AND DRINK; AVOID FIRE' in ' '.join(rows(s)), rows(s)
        assert 'MAKE THEN USE FIRE' not in ' '.join(rows(s)), rows(s)
        assert state(s) == before
        event(s, 'ok', READY)
        assert 'DURATION 30 MIN' in ' '.join(rows(s)), rows(s)
        assert state(s) == before
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('Hot body proposes cooling and opens a reversible REST form: OK')


def comfortable_body():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        open_guide(s)
        s.step(L.poke('thermal_mode', 0))
        s.step(L.poke('wet_mode', 0))
        before = state(s)
        for _ in range(3):
            event(s, 'down')
        assert 'BODY COMFORTABLE: NO ACTION NEEDED' in ' '.join(rows(s)), rows(s)
        assert 'MAKE THEN USE FIRE' not in ' '.join(rows(s)), rows(s)
        event(s, 'ok')
        assert 'BODY COMFORTABLE: NO ACTION NEEDED' in ' '.join(rows(s)), rows(s)
        assert state(s) == before
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('Comfortable BODY stays in guide on Enter and cancels without effect: OK')


def fatigue_advice():
    for rest, deficit, expected, choice in (('f_24', None, 'ENERGY BEAT: TRY REST 8 H', 480),
                                    (None, 'f_16', 'ENERGY TIRED: TRY REST 2 H', 120)):
        with GamePortSession(DISK, menu=False) as s:
            start(s)
            open_guide(s)
            for target, source in (('s_rest', rest), ('s_defr', deficit)):
                value = s.step(L.peek(source, 5)).data if source else bytes(5)
                for offset, number in enumerate(value):
                    s.step(L.poke(target, number, offset))
            before = state(s)
            event(s, 'down')
            event(s, 'down')
            assert expected in ' '.join(rows(s)), rows(s)
            assert state(s) == before
            event(s, 'ok', READY)
            assert int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little') == choice, rows(s)
            assert state(s) == before
            event(s, 'cancel', IDLE)
            assert state(s) == before
    print('Native BEAT/TIRED thresholds suggest 8 h/2 h without resting: OK')


def rest_menu_cancel():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        before = open_guide(s)
        event(s, 'down')
        event(s, 'down')
        event(s, 'ok', READY)
        assert 'DURATION 30 MIN' in ' '.join(rows(s)), rows(s)
        assert int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little') == 30, rows(s)
        assert state(s) == before, 'Opening REST must not execute its duration'
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('Guide opens native REST duration choice; cancellation spends no time: OK')


if __name__ == '__main__':
    direct_status_needs()
    direct_health()
    cancellation()
    missing_matches()
    no_food()
    low_stock()
    hot_body()
    comfortable_body()
    fatigue_advice()
    rest_menu_cancel()
