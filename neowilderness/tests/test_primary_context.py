#!/usr/bin/env python3
"""Safe useful defaults change once; explicit choices and simulation survive."""
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_save import differing, DERIVED_BYTES, diff
from test_joystick_journey import GamePortSession, event, byte, saved_state, IDLE


def check_context(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu)
        event(s, 'ok', IDLE)
        s.step(L.poke('nature_frequency', 0))

        def refresh():
            # Turning refreshes offered verbs without spending simulation time.
            event(s, 'right', IDLE)
            event(s, 'left', IDLE)

        def selected():
            return byte(s, 'mn_idx', byte(s, 'mn_cur'))

        def choose_look():
            event(s, 'down', IDLE)
            for _ in range(27):
                if selected() == 2:
                    break
                event(s, 'right', IDLE)
            assert selected() == 2
            event(s, 'cancel', IDLE)
            refresh()
            assert selected() == 2

        # A pending land journey selects WALK once, without resuming it.
        s.step(L.poke('travel_pending', 22))
        s.step(L.poke('mn_anim', 0))
        before = saved_state(s)
        refresh()
        assert selected() == 1
        assert not differing(before, saved_state(s), DERIVED_BYTES), diff(before, saved_state(s))
        # An explicit alternative persists across refreshes in this context.
        choose_look()
        s.step(L.poke('travel_pending', 0))
        refresh()

        # A dead local catch suggests GET, never KILL on live game.
        for axis in ('x', 'y'):
            s.step(L.poke('fg_'+axis, byte(s, 'p'+axis, 1)))
        s.step(L.poke('fg_b2', 1, 4))
        s.step(L.poke('fg_b1', 0, 4))
        s.step(L.poke('fg_gl', 8, 4))
        before = saved_state(s)
        refresh()
        assert selected() == 7
        assert not differing(before, saved_state(s), DERIVED_BYTES), diff(before, saved_state(s))
        choose_look()
        s.step(L.poke('fg_b2', 0, 4))
        refresh()
        assert selected() != 12 and selected() != 21
        # A reachable drink after four native hours suggests DRINK once.
        s.step(L.poke('it_place', 2, 22))
        s.step(L.poke('it_pack_lo', 8, 22))
        s.step(L.poke('it_pack_hi', 0, 22))
        s.step(L.poke('s_drink', 0x83))
        before = saved_state(s)
        refresh()
        assert selected() == 6
        assert not differing(before, saved_state(s), DERIVED_BYTES), diff(before, saved_state(s))
        choose_look()
        print('Useful primary defaults, stable explicit choice, no implicit attack: OK')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        check_context(disk_with(tmp, map_fixture()))
