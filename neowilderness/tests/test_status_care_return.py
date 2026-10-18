#!/usr/bin/env python3
"""Real joystick care: acknowledge native feedback, restore condition identity/gesture."""
import tempfile
from common import L, disk_with, fp
from test_forest import map_fixture
from test_fit_quantities import boot
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, IDLE, READY
from test_save import differing, DERIVED_BYTES

# GRID shares its address with running simulation overlays; wait at the
# resident input routine and verify the visible care callback before accepting.
RESULT = READY


def open_care(s, conditions, selected, gesture=0):
    for condition in conditions:
        s.step(L.poke('injury_active', 1, condition))
    event(s, 'up')
    event(s, 'down'); event(s, 'ok')  # HEALTH -> first active care
    for _ in range(conditions.index(selected)):
        event(s, 'down')
    for _ in range(gesture):
        event(s, 'right')
    assert byte(s, 'pg_act', byte(s, 'pg_focus')-1) == selected
    assert byte(s, 'pg_g') == gesture


def returned(s, condition, gesture):
    assert 'RETURN CARE' in rows(s)[23] and 'ESC VIEW' in rows(s)[23], rows(s)[20:24]
    event(s, 'ok')
    assert byte(s, 'pg_cur') == 0
    focus = byte(s, 'pg_focus')
    assert focus > 0 and byte(s, 'pg_act', focus-1) == condition
    assert byte(s, 'pg_g') == gesture
    assert byte(s, 'mq_n') == 0 and byte(s, 'pg_open') == 0


def simple(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s); open_care(s, [0, 3, 7], 0, 1)
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok', RESULT)
        assert 'RETURN CARE' in rows(s)[23] and 'ESC VIEW' in rows(s)[23], rows(s)[23]
        assert any(r[:39].strip() for r in rows(s)[20:23]), rows(s)[20:23]
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-.5) < 1e-6
        before = saved_state(s)
        returned(s, 0, 1)
        assert not differing(before, saved_state(s), DERIVED_BYTES)
        event(s, 'cancel', IDLE)
        print('  Timed USE PRESSURE: native feedback retained, same condition/second gesture, no repeated treatment: OK', flush=True)


def identity(disk, gone=False, empty=False):
    with GamePortSession(disk, menu=False) as s:
        boot(s); open_care(s, [3, 7], 7, 1)
        event(s, 'ok', RESULT)  # native CUT BODY, with automatic knife preparation
        assert byte(s, 'care_tools') & 2
        if gone:
            s.step(L.poke('injury_active', 0, 7))
            if empty:
                s.step(L.poke('injury_active', 0, 3))
        else:
            s.step(L.poke('injury_active', 1, 0))  # earlier active item reorders the list
        if empty:
            event(s, 'ok')
            assert byte(s, 'pg_focus') == 0 and byte(s, 'pg_levels') == 6
        else:
            returned(s, 3 if gone else 7, 0 if gone else 1)
        assert byte(s, 'mq_n') == 0
        print(f'  Knife -> CUT -> care return: identity/reordered list, gone={gone}, empty={empty}: OK', flush=True)


def kit(disk, flash=2, missing=False):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('light', 0))
        for item, stock in ((41, 2), (66, flash)):
            s.step(L.poke('it_place', 2, item))
            s.step(L.poke('it_pack_lo', stock, item)); s.step(L.poke('it_pack_hi', 0, item))
        if missing:
            s.step(L.poke('it_place', 255, 41))
        open_care(s, [8], 8)
        before = saved_state(s)
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok', RESULT)
        accepted = flash > 0 and not missing
        assert byte(s, 'it_pack_lo', 41) == (1 if accepted else 2)
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-(.5 if accepted else 0)) < 1e-6
        assert 'RETURN CARE' in rows(s)[23]
        if not accepted:
            assert any(word in '\n'.join(r[:39] for r in rows(s)[20:23]) for word in ('LIGHT', 'BATTER', 'HAVE', 'HERE')), rows(s)[20:23]
        returned(s, 8, 0)
        print(f'  First aid: flash={flash}, missing kit={missing}, accepted={accepted}; refusal/preparation does not repeat care: OK', flush=True)


def leave(disk, encounter=False):
    with GamePortSession(disk, menu=False) as s:
        boot(s); open_care(s, [0], 0)
        if encounter:
            s.step('btn:0,1')
            s.step(L.until('module_queue', 60000))
            s.step('btn:0,0')
            s.step(L.poke('journey_encounters', (byte(s, 'journey_encounters')+1) & 255))
            s.step(IDLE)
            assert 'RETURN CARE' not in rows(s)[23]
        else:
            event(s, 'ok', RESULT)
            before = saved_state(s)
            event(s, 'cancel', IDLE)
            assert not differing(before, saved_state(s), DERIVED_BYTES)
        assert byte(s, 'mq_n') == 0 and byte(s, 'pg_open') == 0
        event(s, 'up'); assert byte(s, 'pg_cur') == 0 and byte(s, 'pg_focus') == 0
        print(f'  Stay in view, encounter={encounter}: queue cleared, no stale care return: OK', flush=True)


def held(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s); open_care(s, [0], 0)
        s.step('btn:0,1')
        s.step(L.until('do_command', 60000))
        s.step(RESULT)
        assert 'RETURN CARE' in rows(s)[23], rows(s)[20:24]
        before = saved_state(s)
        s.step('wait:30')
        assert 'RETURN CARE' in rows(s)[23] and saved_state(s) == before
        s.step('btn:0,0'); s.step('wait:6')
        returned(s, 0, 0)
        print('  Held action button does not acknowledge the result or repeat the care: OK', flush=True)


def water_cancel(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s); open_care(s, [3], 3, 1)
        before = saved_state(s)
        event(s, 'ok', L.until('input_number_idle', 60000))
        event(s, 'cancel', RESULT)
        assert not differing(before, saved_state(s), DERIVED_BYTES)
        returned(s, 3, 1)
        assert not differing(before, saved_state(s), DERIVED_BYTES)
        print('  Cancel DRINK WATER quantity: no stock/time change, same water care gesture restored: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        simple(disk)
        identity(disk)
        identity(disk, gone=True)
        identity(disk, gone=True, empty=True)
        kit(disk)
        kit(disk, flash=0)
        kit(disk, missing=True)
        leave(disk)
        leave(disk, encounter=True)
        held(disk)
        water_cancel(disk)
    print('STATUS care return: OK')
