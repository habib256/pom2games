#!/usr/bin/env python3
"""Native food/water chains from the persistent SURVIVAL menu, joystick only."""
import tempfile
from common import L, disk_with
from test_care_water_preview import fixture
from test_fit_quantities import boot
from test_guidance import open_guide, state
from test_save import differing, DERIVED_BYTES
from test_forage import seed_for
from test_joystick_journey import GamePortSession, event, byte, rows, grid, IDLE, READY


def open_flow(s, water=False, choice=0):
    if byte(s, 'mn_mode'):
        event(s, 'cancel', IDLE)
    open_guide(s)
    if water:
        event(s, 'down')
    event(s, 'ok')
    assert ('COLLECT:' if water else 'RECOVER MEAT:') in ' '.join(rows(s)) or byte(s, 'flow_cursor') != 0, rows(s)
    for _ in range(4):
        if byte(s, 'flow_cursor') == choice:
            return
        event(s, 'down')
    raise AssertionError(rows(s))


def choose_source(s, noun, ready=IDLE):
    if byte(s, 'mn_items'):
        for _ in range(80):
            if byte(s, 'overlay_text', byte(s, 'mn_cur')) & 127 == noun:
                event(s, 'ok', ready)
                return
            event(s, 'down', IDLE)
        raise AssertionError(rows(s))


def stock(s, prefix, item):
    return byte(s, prefix+'l', item) + 256*byte(s, prefix+'h', item)


def decline_result_followup(s):
    """This test intentionally reopens SURVIVAL after declining continuity."""
    s.step(READY)
    titles = ('FOOD RECOVERED', 'WATER COLLECTED', 'COOKED PORTION', 'BOILED PORTION')
    assert any(title in ' '.join(rows(s)) for title in titles), rows(s)
    assert 'RET:SELECT ESC:CANCEL' in ' '.join(rows(s)), rows(s)
    event(s, 'cancel', IDLE)


def food(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('nature_frequency', 0))
        for axis in ('x', 'y'):
            s.step(L.poke('fg_'+axis, byte(s, 'p'+axis, 1)))
        s.step(L.poke('fg_b2', 0, 4))
        s.step(L.poke('fg_b2', 255, 5))
        s.step(L.poke('resource_seen', 1))
        s.step(L.poke('cr_b1', 3, 0))
        s.step(L.poke('fg_use', 4))
        s.step(L.poke('camp_use', 0))
        s.step(L.poke('care_tools', 0))
        s.step(L.poke('light', 1))
        s.step(L.poke('fg_b1', 0, 4))
        s.step(L.poke('fg_gl', 0, 4))
        s.step(L.poke('fg_gh', 0, 4))
        s.step(L.poke('fg_pl', 0, 4))
        s.step(L.poke('fg_ph', 0, 4))
        event(s, 'right', IDLE); event(s, 'left', IDLE)
        seed = seed_for(.001, position=1)
        for i in range(4):
            s.step(L.poke('weather_seed', seed >> (8*i) & 255, i))
        grid(s, 'KILL', ready=READY)
        assert 'IN USE: BOW' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', READY)  # confirm the native attempt
        assert '> SKIN THIS CARCASS' in ' '.join(rows(s)), rows(s)
        event(s, 'cancel', IDLE)  # this test continues through its manual GET flow
        assert byte(s, 'fg_b2', 4) == 1, rows(s)
        caught = stock(s, 'fg_g', 4)
        assert caught > 1
        if byte(s, 'mn_mode'):
            event(s, 'cancel', IDLE)
        open_guide(s)
        event(s, 'cancel', IDLE)
        before = state(s)
        open_flow(s)
        event(s, 'down'); event(s, 'down'); event(s, 'cancel', IDLE)
        assert not differing(before[0], state(s)[0], DERIVED_BYTES) and state(s)[1] == before[1]
        open_flow(s, choice=0)
        event(s, 'ok', IDLE)
        choose_source(s, 80, READY)
        decline_result_followup(s)
        assert stock(s, 'fg_p', 4) == caught and stock(s, 'fg_g', 4) == 0, rows(s)
        grid(s, 'MAKE', 'FIRE')
        assert byte(s, 'fire_on'), rows(s)
        open_flow(s, choice=2)
        event(s, 'ok')
        # Native COOK quantity then native duration (20 min cooks 1 oz).
        event(s, 'up'); event(s, 'ok')
        event(s, 'right'); event(s, 'right')
        event(s, 'ok')
        decline_result_followup(s)
        assert stock(s, 'fg_p', 4) == caught-1 and stock(s, 'fg_g', 4) == 1, rows(s)
        open_flow(s, choice=3)
        event(s, 'ok', IDLE)
        choose_source(s, 80)
        event(s, 'right', IDLE); event(s, 'ok', READY)
        event(s, 'right'); event(s, 'ok', IDLE)
        assert stock(s, 'fg_p', 4) + stock(s, 'fg_g', 4) < caught, rows(s)
        print('SURVIVAL food: cancel, native HUNT -> GET -> COOK (pack to ground) -> EAT: OK')


def water(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('nature_frequency', 0))
        s.step(L.poke('it_place', 2, 64))
        s.step(L.poke('it_pack_lo', 0, 22))
        s.step(L.poke('it_pack_hi', 0, 22))
        event(s, 'right', IDLE); event(s, 'left', IDLE)
        open_guide(s)
        event(s, 'cancel', IDLE)
        before = state(s)
        open_flow(s, water=True)
        event(s, 'down'); event(s, 'down'); event(s, 'cancel', IDLE)
        assert not differing(before[0], state(s)[0], DERIVED_BYTES) and state(s)[1] == before[1]
        open_flow(s, water=True, choice=0)
        event(s, 'ok', IDLE)
        choose_source(s, 22, READY)
        decline_result_followup(s)  # GET fills to native source/canteen/load capacity.
        packed = byte(s, 'it_pack_lo', 22)
        assert packed > 0, rows(s)
        total = packed + byte(s, 'it_gnd_lo', 22)
        before = state(s)
        open_flow(s, water=True, choice=1)
        assert 'NEED HEAT/UTENSILS' in ' '.join(rows(s)), rows(s)
        event(s, 'ok')  # BOIL explains the missing native heat.
        event(s, 'cancel', IDLE)
        assert not differing(before[0], state(s)[0], DERIVED_BYTES) and state(s)[1] == before[1]
        grid(s, 'MAKE', 'FIRE')
        open_flow(s, water=True, choice=1)
        prepared = state(s)
        event(s, 'ok')
        assert 'USE UTENSILS' in ' '.join(rows(s)), rows(s)
        assert not differing(prepared[0], state(s)[0], DERIVED_BYTES) and state(s)[1] == prepared[1]
        assert not byte(s, 'camp_use') & 32
        event(s, 'ok')              # explicitly activate utensils; no BOIL yet
        assert byte(s, 'camp_use') & 32
        assert 'PREPARATION READY' in ' '.join(rows(s)), rows(s)
        assert byte(s, 'it_pack_lo', 22) == packed
        event(s, 'ok', IDLE)        # explicitly review original BOIL ounces
        event(s, 'ok')
        decline_result_followup(s)
        assert byte(s, 'it_pack_lo', 22) < packed, rows(s)
        assert byte(s, 'it_gnd_lo', 22) + byte(s, 'it_pack_lo', 22) == total, rows(s)
        open_flow(s, water=True, choice=2)
        event(s, 'ok', IDLE)
        choose_source(s, 22)
        event(s, 'ok', IDLE)
        assert byte(s, 'it_gnd_lo', 22) + byte(s, 'it_pack_lo', 22) < total, rows(s)
        print('SURVIVAL water: cancel, native GET -> BOIL (canteen to ground) -> DRINK: OK')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, fixture(water=(20, 20, 64)))
        food(disk)
        water(disk)
