#!/usr/bin/env python3
"""CAMP keeps the inspected step across one confirmed native preparation."""
from common import DISK, L
from test_guidance import start, state
from test_night import open_night
from test_survival_flows import choose_source
from test_joystick_journey import GamePortSession, event, byte, rows, READY, IDLE


def wear_return():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        s.step(L.poke('it_place', 2, 2))
        before = open_night(s)
        event(s, 'down')
        event(s, 'down')
        event(s, 'ok', IDLE)
        assert state(s) == before, 'Opening WEAR changes native state'
        choose_source(s, 2, READY)
        assert byte(s, 'it_place', 2) == 1
        assert 'CAMP: REVIEW UPDATED CHECKLIST' in ' '.join(rows(s)), rows(s)
        after = state(s)
        event(s, 'ok', READY)
        assert 'PREPARE NIGHT' in ' '.join(rows(s)), rows(s)
        assert byte(s, 'night_cursor') == 2
        assert state(s) == after, 'Returning to the checklist simulates another action'
        event(s, 'cancel', IDLE)
        assert state(s) == after
        assert byte(s, 'camp_pending') == 0
    print('CAMP progress: one native WEAR returns to the same observed step; review/cancel inert')


if __name__ == '__main__':
    wear_return()
