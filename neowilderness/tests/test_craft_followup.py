#!/usr/bin/env python3
"""Native MAKE result and explicit recipe/product follow-up at the game port."""
import tempfile
from common import L, disk_with, fp
from test_forest import map_fixture
from test_fit_quantities import boot
from test_thermal import poke
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, IDLE, action, object_item
from test_save import differing, DERIVED_BYTES

RESULT = L.until('q_craft_wait', 100000)
RECIPES = (95, 96, 97, 91, 90, 89, 58, 93, 43, 44)


def open_recipe(s, index):
    event(s, 'up')
    while byte(s, 'pg_cur') != 2:
        event(s, 'right')
    for _ in range(index+1):
        event(s, 'down')
    assert byte(s, 'cp_focus') == index+1
    assert byte(s, 'cp_st', index) == 0, rows(s)


def setup(s, item):
    boot(s)
    # Short, deterministic native builds; all durations are still computed
    # by CRAFT and compared to the elapsed simulation clock below.
    for name in ('s_health', 'f_hmax'):
        for step in poke(name, 100):
            s.step(step)
    if item < 76:
        s.step(L.poke('it_place', 255, item))
    s.step(L.poke('nature_frequency', 0))
    s.step(L.poke('px', 25, 1)); s.step(L.poke('py', 25, 1))
    s.step(L.poke('cr_still', 0))


def make(s, index):
    open_recipe(s, index)
    minutes = byte(s, 'cp_mlo', index)+256*byte(s, 'cp_mhi', index)
    clock = fp(s.step(L.peek('s_elap', 5)).data)
    # The same address belongs to SIM during MAKE: wait for the resident
    # command-completion entry before stopping in the reloaded GRID.
    s.step('btn:0,1'); s.step(L.until('get_line', 100000))
    s.step('btn:0,0'); s.step(RESULT); s.step('wait:6')
    assert 'RETURN RECIPES' in rows(s)[23], rows(s)[23]
    assert any(row[:39].strip() for row in rows(s)[20:23])
    spent = 60*(fp(s.step(L.peek('s_elap', 5)).data)-clock)
    assert abs(spent-minutes) < .001, (spent, minutes)
    assert byte(s, 'mq_n') == 0
    return saved_state(s)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        with GamePortSession(disk, menu=False) as s:
            setup(s, 90); before = make(s, 4)
            event(s, 'right', RESULT)
            assert 'RETURN OBJECTS' in rows(s)[23], rows(s)[23]
            event(s, 'left', RESULT)
            assert saved_state(s) == before
            event(s, 'ok')
            assert byte(s, 'pg_cur') == 2 and byte(s, 'cp_focus') == 5
            assert byte(s, 'cp_st', 4) == 2
            assert not differing(before, saved_state(s), DERIVED_BYTES)
            event(s, 'cancel', IDLE)
            event(s, 'up')
            assert byte(s, 'cp_focus') == 0, 'no stale forced focus'
            print('  MAKE SPEAR: readable result, choice/cancel read-only, same recipe DONE, next ordinary arrival on tab: OK', flush=True)
        for index in (3, 4, 5, 6, 7, 8, 9):
            item = RECIPES[index]
            with GamePortSession(disk, menu=False) as s:
                setup(s, item); make(s, index)
                event(s, 'right', RESULT); event(s, 'ok')
                assert byte(s, 'pg_cur') == 1 and byte(s, 'pg_focus') == 1
                side = byte(s, 'obj_side')
                assert byte(s, 'obj_selected', side) == item
                assert byte(s, 'overlay_text', byte(s, 'ob_at', side)+byte(s, 'obj_cur', side)) == item
                event(s, 'ok')
                assert byte(s, 'menu_noun') == item and byte(s, 'om_phase') == 0
                print(f'  Product {item}: focused OBJECTS item, native actions accessible: OK', flush=True)
        for index in (0, 1, 2):
            with GamePortSession(disk, menu=False) as s:
                setup(s, RECIPES[index])
                if index == 1:
                    s.step('poke:700B:0A')  # snow required for IGLOO
                make(s, index)
                event(s, 'right', RESULT)
                assert 'RETURN ENTER' in rows(s)[23], rows(s)[23]
                clock = s.step(L.peek('s_elap', 5)).data
                event(s, 'ok', IDLE)
                assert byte(s, 'shelter_inside') == (2 if index == 1 else 1)
                assert s.step(L.peek('s_elap', 5)).data == clock
                print(f'  Shelter {RECIPES[index]}: explicit native USE enters without replaying MAKE or extra time: OK', flush=True)
        with GamePortSession(disk, menu=False) as s:
            setup(s, 90)
            s.step(L.poke('load_limits', 0xD0)); s.step(L.poke('load_limits', 7, 1))
            make(s, 4); event(s, 'right', RESULT); event(s, 'ok')
            clock = s.step(L.peek('s_elap', 5)).data
            action(s, 1)  # explicit CARRY SPEAR from OBJECTS
            assert byte(s, 'cr_b1', 1) == 3
            object_item(s, 1, 90)  # follow the spear into HANDS
            action(s, 4)  # explicit USE SPEAR, possession alone is insufficient
            assert byte(s, 'fg_use') & 8
            assert s.step(L.peek('s_elap', 5)).data == clock
            print('  MAKE -> OBJECTS -> CARRY -> USE SPEAR: native placement/activation, no extra MAKE: OK', flush=True)
        with GamePortSession(disk, menu=False) as s:
            setup(s, 90); open_recipe(s, 4)
            s.step('btn:0,1'); s.step(L.until('get_line', 100000)); s.step(RESULT)
            s.step('wait:20')
            assert 'RETURN RECIPES' in rows(s)[23], 'held MAKE button acknowledged result'
            before = saved_state(s)
            s.step('btn:0,0'); s.step('wait:6'); event(s, 'cancel', IDLE)
            assert saved_state(s) == before and byte(s, 'mq_n') == 0
            event(s, 'up'); assert byte(s, 'cp_focus') == 0
            print('  Held validate cannot dismiss result; ESC keeps native state and clears forced return: OK', flush=True)
        with GamePortSession(disk, menu=False) as s:
            setup(s, 90); open_recipe(s, 4)
            s.step('btn:0,1'); s.step(L.until('get_line', 100000)); s.step('btn:0,0')
            s.step(L.until('module_queue', 100000))
            s.step(L.poke('journey_encounters', (byte(s, 'journey_encounters')+1) & 255))
            s.step(IDLE)
            assert byte(s, 'mq_n') == 0 and 'RETURN RECIPES' not in rows(s)[23]
            event(s, 'up'); assert byte(s, 'cp_focus') == 0
            print('  Encounter stops the follow-up queue; no stale recipe return: OK', flush=True)
        with GamePortSession(disk, menu=False) as s:
            setup(s, 90); open_recipe(s, 4)
            for item in (60, 67):
                s.step(L.poke('it_place', 255, item))
            clock = s.step(L.peek('s_elap', 5)).data
            s.step('btn:0,1'); s.step(L.until('get_line', 100000))
            s.step('btn:0,0'); s.step(RESULT); s.step('wait:6')
            assert 'ROPE' in '\n'.join(r[:39] for r in rows(s)[20:23])
            before = saved_state(s)
            event(s, 'right', RESULT)
            assert 'RETURN RECIPES' in rows(s)[23] and saved_state(s) == before
            event(s, 'ok')
            assert byte(s, 'cp_focus') == 5 and byte(s, 'cp_st', 4) == 1
            assert byte(s, 'cr_b1', 1) == 255
            assert s.step(L.peek('s_elap', 5)).data == clock
            print('  Native MAKE refusal: readable reason, no phantom product, same missing recipe, no time: OK', flush=True)
    print('CRAFT follow-up: OK')


if __name__ == '__main__':
    main()
