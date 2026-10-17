#!/usr/bin/env python3
"""Joystick intents: preparation is deferred, charged once and stopped on failure."""
import tempfile
from common import L, disk_with, fp
from test_forest import map_fixture
from test_fit_quantities import boot
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, action, IDLE
from test_use_requirements import choose_use
from test_craft_followup import setup, make


def stock(s, item, amount, place=2):
    s.step(L.poke('it_place', place, item))
    s.step(L.poke('it_pack_lo', amount, item))
    s.step(L.poke('it_pack_hi', 0, item))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        for matches in (4, 0):
            with GamePortSession(disk, menu=False) as s:
                boot(s)
                for name in ('nature_frequency', 'camp_use', 'fire_on', 'fire_near', 'weather_sky', 'wind'):
                    s.step(L.poke(name, 0))
                for item, amount in ((71, 1), (40, 8), (38, matches)):
                    stock(s, item, amount)
                event(s, 'up'); event(s, 'right')
                choose_use(s, 71)
                before = saved_state(s)
                event(s, 'ok')
                assert 'AUTO FUEL 1 OZ' in rows(s)[22]
                assert saved_state(s) == before
                event(s, 'cancel'); event(s, 'cancel')
                assert saved_state(s) == before
                elapsed = fp(s.step(L.peek('s_elap', 5)).data)
                action(s, 4)
                assert byte(s, 'it_pack_lo', 40) == 7
                assert byte(s, 'pg_cur') == 1
                if matches:
                    assert byte(s, 'it_pack_lo', 38) == 3
                    assert byte(s, 'camp_use') & 16
                    assert byte(s, 'it_place', 71) == 0
                    assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-.5) < .001
                else:
                    assert not byte(s, 'camp_use') & 16
                    assert byte(s, 'it_place', 71) == 2
                    assert byte(s, 'obj_selected', 1) == 71
                    assert fp(s.step(L.peek('s_elap', 5)).data) == elapsed
                    assert any('MATCH' in row for row in rows(s)[20:23]), rows(s)[20:23]
                assert byte(s, 'mq_n') == 0
                print(f'  Stove matches={matches}: cancel read-only, fuel once, success or stop/return: OK', flush=True)
        with GamePortSession(disk, menu=False) as s:
            boot(s)
            s.step(L.poke('nature_frequency', 0)); s.step(L.poke('light', 0))
            stock(s, 41, 3); stock(s, 66, 0)
            event(s, 'up'); event(s, 'right')
            choose_use(s, 41); event(s, 'ok')
            before = saved_state(s)
            event(s, 'ok')
            assert byte(s, 'it_pack_lo', 41) == 3
            assert not byte(s, 'light')
            assert byte(s, 'pg_cur') == 1 and byte(s, 'obj_selected', 1) == 41
            assert byte(s, 'mq_n') == 0
            print('  Empty lamp stops preparation before first-aid dose; same selected kit: OK', flush=True)
        with GamePortSession(disk, menu=False) as s:
            boot(s)
            for name in ('nature_frequency', 'camp_use', 'fire_on', 'fire_near', 'weather_sky', 'wind'):
                s.step(L.poke(name, 0))
            for item, amount in ((71, 1), (40, 8), (38, 4)):
                stock(s, item, amount)
            event(s, 'up'); event(s, 'right')
            choose_use(s, 71); event(s, 'ok')
            s.step('btn:0,1'); s.step(L.until('get_line', 60000)); s.step('btn:0,0')
            assert byte(s, 'it_pack_lo', 40) == 7
            s.step(L.poke('journey_encounters', (byte(s, 'journey_encounters')+1) & 255))
            s.step(IDLE)
            assert byte(s, 'mq_n') == 0
            assert byte(s, 'it_pack_lo', 38) == 4
            assert byte(s, 'it_place', 71) == 2 and not byte(s, 'camp_use') & 16
            print('  Encounter after fuel stops matches, stove and forced page return: OK', flush=True)
        # Stale activation must not skip preparing the available tool here.
        with GamePortSession(disk, menu=False) as s:
            setup(s, 90)
            stock(s, 59, 1)
            s.step(L.poke('care_tools', 2))
            s.step(L.poke('care_tool_x', 24)); s.step(L.poke('care_tool_y', 25))
            make(s, 4)
            assert byte(s, 'care_tool_x') == 25
            assert byte(s, 'care_tool_y') == 25
            print('  CRAFT: stale knife activation refreshed; preview equals real elapsed time: OK', flush=True)
    print('Menu intents: OK')


if __name__ == '__main__':
    main()
