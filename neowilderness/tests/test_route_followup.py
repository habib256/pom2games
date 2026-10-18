#!/usr/bin/env python3
"""Tracked trip remains explicit after care; far readjust and terrain guidance."""
from common import DISK, L, fp, a2test
from test_fit_quantities import boot
from test_guidance import state
from test_survival_flows import choose_source
from test_joystick_journey import GamePortSession, byte, event, grid, rows, IDLE, READY


def setup(s, tracked=True):
    boot(s)
    for name, value in (('nature_frequency', 0), ('shelter_inside', 0),
                        ('fire_on', 0), ('night', 0), ('route_x', 70),
                        ('route_y', 60), ('route_active', int(tracked)),
                        ('travel_pending', 1), ('travel_remaining', 90),
                        ('travel_next_minutes', 0)):
        s.step(L.poke(name, value))
    s.step(L.poke('travel_remaining', 0, 1))


def target(s):
    return tuple(s.step(L.peek(name, size)).data for name, size in
                 (('route_x', 1), ('route_y', 1), ('route_active', 1),
                  ('travel_pending', 1), ('travel_remaining', 2), ('travel_heading', 2)))


def far_readjust():
    for tracked in (False, True):
        with GamePortSession(DISK, menu=False) as s:
            setup(s, tracked)
            before, trip = state(s), target(s)
            grid(s, 'WALK', ready=READY)
            screen = ' '.join(rows(s))
            assert 'RESUME 90 MIN' in screen and 'SAME CAP' in screen and 'WALK:LAND' in screen and 'SWIM:WATER' in screen, rows(s)
            assert state(s) == before and target(s) == trip
            if tracked:
                for _ in range(3):
                    event(s, 'down', READY)
                visible = ' '.join(row[:39] for row in rows(s)[20:24])
                assert 'READJUST CAP' in visible and 'WALK:LAND' in visible and 'SWIM:WATER' in visible, rows(s)
                assert 'TO POINT 70,60' in visible, rows(s)
                event(s, 'ok', L.until('nav_key', 60000))
                assert state(s) == before and target(s) == trip
                event(s, 'cancel', READY)
            event(s, 'cancel', IDLE)
            assert state(s) == before and target(s) == trip
    print('Trip: tracked/untracked same cap and terrain guidance; far readjust/cancel retain target, remainder and RNG')


def after_wear():
    with GamePortSession(DISK, menu=False) as s:
        setup(s)
        s.step(L.poke('it_place', 2, 2))
        trip = target(s)
        grid(s, 'WEAR', ready=IDLE)
        choose_source(s, 2, READY)
        assert byte(s, 'it_place', 2) == 1
        assert 'TRACKED TRIP: TARGET / TIME RETAINED' in ' '.join(rows(s)), rows(s)
        after = state(s)
        for _ in range(4):
            event(s, 'down', READY)
            assert state(s) == after and target(s) == trip
        event(s, 'down', READY)  # WALK native confirmation
        event(s, 'ok', READY)
        assert 'SAME CAP' in ' '.join(rows(s)), rows(s)
        assert state(s) == after and target(s) == trip
        event(s, 'cancel', IDLE)
        assert state(s) == after and target(s) == trip
    print('Trip after care: WEAR retained; browse/open/cancel native resumption spend no time or RNG')


def after_rest():
    with GamePortSession(DISK, menu=False) as s:
        setup(s)
        trip = target(s)
        position = s.step(L.peek('px', 4)).data
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        grid(s, 'REST', ready=READY)
        for _ in range(6):
            if int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little') == 1:
                break
            event(s, 'down', READY)
        assert int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little') == 1
        event(s, 'ok', READY)
        assert 'TRACKED TRIP: TARGET / TIME RETAINED' in ' '.join(rows(s)), rows(s)
        assert target(s) == trip and s.step(L.peek('px', 4)).data == position
        assert abs((fp(s.step(L.peek('s_elap', 5)).data) - elapsed) * 60 - 1) < 1e-5
        after = state(s)
        event(s, 'cancel', IDLE)
        assert state(s) == after and target(s) == trip
    print('Trip after direct REST: exactly one native minute; no automatic movement or repeated rest')


def typed_rest():
    with a2test.Session(DISK, menu=False) as s:
        setup(s)
        trip = target(s)
        s.step('key:REST 1 MIN\\r')
        s.step(IDLE)
        assert target(s) == trip
        assert 'TRACKED TRIP: TARGET / TIME RETAINED' not in ' '.join(rows(s))
    print('Typed REST: native return without an added trip prompt')


if __name__ == '__main__':
    far_readjust()
    after_wear()
    after_rest()
    typed_rest()
