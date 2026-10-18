#!/usr/bin/env python3
"""Joystick gesture count for night review and proposed native REST form."""
from common import DISK
from test_guidance import start, state
from test_night import open_night
from test_joystick_journey import GamePortSession, event, byte, IDLE


class CountedSession(GamePortSession):
    gestures = 0
    counting = False

    def step(self, step):
        if self.counting and ((step.startswith('joy:') and step != 'joy:0,0')
                              or (step.startswith('btn:') and step.endswith(',1'))):
            self.gestures += 1
        return super().step(step)


with CountedSession(DISK, menu=False) as s:
    start(s)
    s.counting = True
    before = open_night(s)
    review = s.gestures
    for _ in range(5):
        event(s, 'down')
    event(s, 'ok', IDLE)
    assert byte(s, 'mn_verb') == 3
    assert state(s) == before
    print(f'VIEW -> NIGHT review: {review} joystick gestures')
    print(f'VIEW -> NIGHT -> editable REST: {s.gestures} joystick gestures; native state and RNG preserved')
