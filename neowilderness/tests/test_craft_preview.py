#!/usr/bin/env python3
"""CRAFT tool readiness and finish estimates through the real game port."""
import re
import tempfile
from common import L, disk_with, fp
from test_forest import map_fixture
from test_craft_followup import setup, open_recipe, make
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, IDLE, action
from test_save import differing, DERIVED_BYTES
from test_thermal import poke


def clock(s, hour):
    for step in poke('s_hour', hour):
        s.step(step)


def estimate(s, index):
    page = rows(s)
    line = next(r for r in page if 'EST. FINISH:' in r)
    match = re.search(r'EST. FINISH: (\d\d):(\d\d)(?: \+(\d+)D)?', line)
    assert match, line
    duration = byte(s, 'cp_mlo', index) + 256*byte(s, 'cp_mhi', index)
    total = round(fp(s.step(L.peek('s_hour', 5)).data)*60) + duration
    assert (int(match[1]), int(match[2]), int(match[3] or 0)) == (total//60 % 24, total % 60, total//1440), (line, total)
    return line.strip(), duration


def main():
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        # Presence never implies activation. Stale activation on another
        # square is OFF, without clearing the saved native activation flag.
        for item, index in ((58, 0), (59, 4)):
            for place, active, stale in ((255, 0, False), (0, 0, False), (2, 0, False), (3, 0, False), (2, 1, False), (3, 1, True)):
                with GamePortSession(disk, menu=False) as s:
                    setup(s, 90)
                    s.step(L.poke('it_place', place, item))
                    s.step(L.poke('it_x', 25, item)); s.step(L.poke('it_y', 25, item))
                    s.step(L.poke('care_tools', (item-57)*active))
                    s.step(L.poke('care_tool_x', 24 if stale else 25)); s.step(L.poke('care_tool_y', 25))
                    open_recipe(s, index)
                    text = '\n'.join(rows(s))
                    name = 'AXE' if item == 58 else 'KNIFE'
                    status = 'IN USE HERE' if active and not stale else 'MISSING HERE' if place == 255 else 'AVAILABLE - USE IN EQUIPMENT'
                    assert name+': '+status in text, text
                    assert name+(' ON' if active and not stale else ' OFF') in text, text
                    estimate(s, index)
                    before = saved_state(s)
                    event(s, 'down'); event(s, 'up')
                    assert not differing(before, saved_state(s), DERIVED_BYTES), differing(before, saved_state(s), DERIVED_BYTES)
                    assert byte(s, 'care_tools') == (item-57)*active
                    print(f'  {name} place={place} active={active} stale={stale}: {status}; navigation read-only: OK', flush=True)
        # Integer minute boundaries, midnight, low-health multi-day jobs,
        # and fixed duration recipes share the HUD rounding convention.
        for hour, health, index in ((7+1/60, 100, 0), (7.99999999, 100, 0), (23+59/60, 100, 0), (23.99999999, 100, 0), (0, .5, 0), (23.75, 100, 9)):
            with GamePortSession(disk, menu=False) as s:
                setup(s, 90); clock(s, hour)
                for step in poke('s_health', health):
                    s.step(step)
                open_recipe(s, index)
                line, duration = estimate(s, index)
                assert duration > 1440 if health < 1 else duration >= 0
                if health == 100:
                    event(s, 'cancel', IDLE)
                    make(s, index)  # independently checks actual native elapsed time
                print(f'  hour={hour} health={health}: {line}; {duration} native minutes: OK', flush=True)
        with GamePortSession(disk, menu=False) as s:
            setup(s, 90)
            s.step(L.poke('it_place', 3, 59))
            open_recipe(s, 4)
            _, slow = estimate(s, 4)
            assert 'KNIFE: AVAILABLE' in '\n'.join(rows(s))
            event(s, 'cancel', IDLE); event(s, 'up')
            for _ in range(3):
                event(s, 'left')
            assert byte(s, 'pg_cur') == 6
            event(s, 'ok')
            for _ in range(140):
                if byte(s, 'overlay_text', byte(s, 'eq_cur')) == 59:
                    break
                event(s, 'down')
            else:
                raise AssertionError('KNIFE missing from EQUIPMENT')
            action(s, 4)
            assert byte(s, 'care_tools') & 2
            event(s, 'cancel', IDLE)
            open_recipe(s, 4)
            assert 'KNIFE: IN USE HERE' in '\n'.join(rows(s))
            _, fast = estimate(s, 4)
            assert fast == slow//4 and fast < slow, (slow, fast)
            s.step('shot:/tmp/nw-craft-preview.png')
            print('  CRAFT -> EQUIPMENT -> USE KNIFE -> CRAFT: held is OFF, explicit USE is ON, native duration /4: OK', flush=True)
        with GamePortSession(disk, menu=False) as s:
            setup(s, 90); open_recipe(s, 0)
            event(s, 'down')  # IGLOO has no snow
            assert byte(s, 'cp_st', 1) == 1
            assert 'EST. FINISH:' not in '\n'.join(rows(s))
            print('  Missing recipe: duration shown, no completion estimate promised: OK', flush=True)
    print('CRAFT preview: OK')


if __name__ == '__main__':
    main()
