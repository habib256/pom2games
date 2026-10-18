#!/usr/bin/env python3
"""Real game port CAMP: reversible inspection and explicit local departure actions."""
from common import DISK, L
from test_fit_quantities import boot
from test_guidance import state
from test_campguide import unchanged
from test_joystick_journey import GamePortSession, event, byte, rows, grid, READY, IDLE


def setup(s):
    boot(s)
    s.step(L.poke('it_place', 0, 9))
    s.step(L.poke('it_x', byte(s, 'px', 1), 9))
    s.step(L.poke('it_y', byte(s, 'py', 1), 9))
    s.step(L.poke('shelter_inside', 1))
    s.step(L.poke('fire_on', 1))
    for index in range(8):
        s.step(L.poke('load_limits', 255, index))
    for name, value in (('route_x', 40), ('route_y', 35), ('route_active', 1),
                        ('travel_remaining', 30), ('travel_pending', 1)):
        s.step(L.poke(name, value))


def target(s):
    return tuple(byte(s, name) for name in ('route_x', 'route_y', 'route_active',
                                           'travel_remaining', 'travel_pending'))


def open_camp(s):
    grid(s, 'QUICK', ready=READY)
    assert 'NEXT ACTION' in ' '.join(rows(s))
    while byte(s, 'menu_duration'):
        event(s, 'left')
    event(s, 'ok')
    assert 'CAMP - CHOOSE ONE ACTION' in ' '.join(rows(s))


def choose(s, text):
    for _ in range(6):
        if text in rows(s)[21][41:]:
            return
        event(s, 'down')
    raise AssertionError((text, rows(s)))


def departure():
    with GamePortSession(DISK, menu=False) as s:
        setup(s)
        expected = target(s)
        before = state(s)
        open_camp(s)
        for text in ('PREPARE NIGHT', 'EXIT SHELTER', 'PACK LOCAL TENT', 'DOUSE FIRE', 'REVIEW TRACKED TRIP', 'BACK'):
            choose(s, text)
            unchanged(before, s)
            assert target(s) == expected
        event(s, 'cancel', IDLE)
        unchanged(before, s)
        assert target(s) == expected
        assert byte(s, 'shelter_inside') == 1 and byte(s, 'fire_on') == 1
        assert byte(s, 'it_place', 9) == 0

        open_camp(s)
        choose(s, 'PREPARE NIGHT')
        event(s, 'ok', READY)
        assert 'PREPARE NIGHT' in ' '.join(rows(s)), rows(s)
        unchanged(before, s)
        assert target(s) == expected
        event(s, 'cancel', IDLE)
        unchanged(before, s)
        assert target(s) == expected, 'Night cancellation replays a stale command'

        open_camp(s)
        choose(s, 'EXIT SHELTER')
        event(s, 'ok', READY)
        assert byte(s, 'shelter_inside') == 0
        assert byte(s, 'fire_on') == 1 and byte(s, 'it_place', 9) == 0
        assert target(s) == expected

        assert 'CAMP: REVIEW UPDATED CHECKLIST' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', READY)
        choose(s, 'PACK LOCAL TENT')
        event(s, 'ok', READY)
        assert byte(s, 'it_place', 9) == 2
        assert byte(s, 'fire_on') == 1 and target(s) == expected

        assert 'CAMP: REVIEW UPDATED CHECKLIST' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', READY)
        choose(s, 'DOUSE FIRE')
        event(s, 'ok', READY)
        assert byte(s, 'fire_on') == 0 and target(s) == expected
        assert 'CAMP: REVIEW UPDATED CHECKLIST' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', READY)
        assert byte(s, 'cg_count') == 3      # NIGHT, tracked trip and BACK
        before_review = state(s)
        choose(s, 'REVIEW TRACKED TRIP')
        event(s, 'ok', READY)
        assert byte(s, 'nav_review') == 2
        assert target(s) == expected
        assert state(s) == before_review, 'Trip inspection advances the simulation'
        event(s, 'cancel', READY)
        event(s, 'cancel', IDLE)
        assert target(s) == expected
        assert state(s) == before_review

    print('CAMP departure: inspect/cancel frozen; EXIT/PACK TENT/DOUSE explicit; tracked trip retained')


if __name__ == '__main__':
    departure()
