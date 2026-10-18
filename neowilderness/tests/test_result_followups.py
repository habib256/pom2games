#!/usr/bin/env python3
"""Real game-port continuation: native results, exact piles, editable portions."""
import tempfile
from common import L, disk_with
from test_care_water_preview import fixture
from test_fit_quantities import boot
from test_forage import seed_for
from test_guidance import state
from test_save import differing, DERIVED_BYTES
from test_joystick_journey import GamePortSession, event, byte, rows, grid, IDLE, READY
from test_survival_flows import choose_source, stock


def followup(s, title):
    """The native result and actionable choice appear on the first screen."""
    s.step(READY)
    screen = ' '.join(rows(s))
    assert title in screen, rows(s)
    assert 'RET:CONTINUE' not in screen, rows(s)
    assert 'RET:SELECT ESC:CANCEL' in screen, rows(s)


def detail(s, source):
    screen = ' '.join(rows(s))
    assert f"{byte(s, 'dep_mask', 1)} OZ {source}" in screen, rows(s)



def quantity(s, amount, ready=READY):
    for _ in range(6):
        if byte(s, 'linelen') == 0:
            break
        event(s, 'left')
    assert byte(s, 'linelen') == 0, rows(s)
    for _ in range(amount):
        event(s, 'up')
    event(s, 'ok', ready)


def food(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        grid(s, 'MAKE', 'FIRE')
        event(s, 'cancel', IDLE)
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
        for stem in ('fg_b1', 'fg_gl', 'fg_gh', 'fg_pl', 'fg_ph'):
            s.step(L.poke(stem, 0, 4))
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
        grid(s, 'GET')
        choose_source(s, 80, READY)
        followup(s, 'FOOD RECOVERED')
        detail(s, 'PACK')
        assert stock(s, 'fg_p', 4) == caught and stock(s, 'fg_g', 4) == 0
        before = state(s)
        native_result = [line[:39] for line in rows(s)[20:24]]
        assert any(line.strip() for line in native_result), rows(s)
        event(s, 'right'); event(s, 'left')
        assert [line[:39] for line in rows(s)[20:24]] == native_result, rows(s)
        assert not differing(before[0], state(s)[0], DERIVED_BYTES)
        assert before[1] == state(s)[1]
        event(s, 'ok')             # explicit COOK; native editable ounces
        assert byte(s, 'obj_side') == 1 and byte(s, 'menu_noun') == 80
        quantity(s, 1)
        event(s, 'right'); event(s, 'right')   # native 20 minute duration
        event(s, 'ok')
        followup(s, 'COOKED PORTION')
        detail(s, 'GROUND')
        assert stock(s, 'fg_p', 4) == caught-1
        assert stock(s, 'fg_g', 4) == 1
        before = state(s)
        event(s, 'ok')             # explicit EAT, exact GROUND source
        assert byte(s, 'obj_side') == 0 and byte(s, 'menu_noun') == 80
        assert byte(s, 'input_value') == 1, rows(s)
        event(s, 'ok', IDLE)
        assert stock(s, 'fg_p', 4) == caught-1  # raw pack portion survives
        assert stock(s, 'fg_g', 4) == 0
        print('RESULT FOLLOWUP: HUNT -> GET -> COOK -> EAT, exact ground portion: OK')


def water(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('it_place', 2, 64))
        s.step(L.poke('it_pack_lo', 0, 22))
        s.step(L.poke('it_pack_hi', 0, 22))
        event(s, 'right', IDLE); event(s, 'left', IDLE)
        grid(s, 'MAKE', 'FIRE')
        grid(s, 'GET')
        choose_source(s, 22, READY)
        followup(s, 'WATER COLLECTED')
        detail(s, 'CANTEEN')
        packed = byte(s, 'it_pack_lo', 22)
        assert packed > 1
        event(s, 'ok')             # explicit BOIL opens useful preparation
        assert 'USE UTENSILS' in ' '.join(rows(s)), rows(s)
        event(s, 'ok')             # explicitly set utensils down
        assert 'PREPARATION READY' in ' '.join(rows(s)), rows(s)
        event(s, 'ok')             # original editable native portion
        event(s, 'ok')
        followup(s, 'BOILED PORTION')
        detail(s, 'GROUND')
        packed_after = byte(s, 'it_pack_lo', 22)
        ground_after = byte(s, 'it_gnd_lo', 22)
        before = state(s)
        event(s, 'cancel', IDLE)
        assert not differing(before[0], state(s)[0], DERIVED_BYTES)
        assert before[1] == state(s)[1]
        assert packed_after < packed and ground_after > 0
        # A second explicit native BOIL yields a fresh deliberate proposal.
        grid(s, 'BOIL', ready=IDLE)
        event(s, 'ok')
        followup(s, 'BOILED PORTION')
        detail(s, 'GROUND')
        packed_after = byte(s, 'it_pack_lo', 22)
        event(s, 'ok')
        assert byte(s, 'obj_side') == 0
        event(s, 'ok', IDLE)
        assert byte(s, 'it_pack_lo', 22) == packed_after
        print('RESULT FOLLOWUP: GET -> BOIL -> DRINK, ground source and cancel: OK')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, fixture(water=(20, 20, 64)))
        food(disk)
        water(disk)
