#!/usr/bin/env python3
"""XL game port: deliberate camp prerequisites retain source and portion."""
from common import DISK, L, fp
from test_fit_quantities import boot
from test_guidance import state
from test_save import differing, DERIVED_BYTES
from test_survival_flows import choose_source, open_flow
from test_joystick_journey import GamePortSession, event, byte, rows, grid, READY, IDLE


def collected_water(s):
    boot(s)
    for stem, value in (('it_place', 0), ('it_pack_lo', 0), ('it_pack_hi', 0),
                        ('it_gnd_lo', 20), ('it_gnd_hi', 0)):
        s.step(L.poke(stem, value, 22))
    s.step(L.poke('it_x', byte(s, 'px', 1), 22))
    s.step(L.poke('it_y', byte(s, 'py', 1), 22))
    for item in (64, 73, 38):
        s.step(L.poke('it_place', 2, item))
    s.step(L.poke('it_pack_lo', 10, 38))
    s.step(L.poke('fire_on', 0))
    s.step(L.poke('camp_use', 0))
    event(s, 'right', IDLE)
    event(s, 'left', IDLE)
    grid(s, 'GET')
    choose_source(s, 22, READY)
    assert 'WATER COLLECTED' in ' '.join(rows(s))
    assert byte(s, 'dep_mask', 1) == 20


def unchanged(before, s):
    after = state(s)
    assert not differing(before[0], after[0], DERIVED_BYTES)
    assert before[1] == after[1]


def cancellation():
    with GamePortSession(DISK, menu=False) as s:
        collected_water(s)
        before = state(s)
        native_result = [line[:39] for line in rows(s)[20:24]]
        event(s, 'ok')
        assert byte(s, 'camp_pending') == 128
        assert 'USE MATCHES' in ' '.join(rows(s))
        assert [line[:39] for line in rows(s)[20:24]] == native_result
        event(s, 'right')
        event(s, 'left')
        unchanged(before, s)
        event(s, 'cancel', IDLE)
        assert not byte(s, 'camp_pending')
        unchanged(before, s)
    print('CAMP: inspect/browse/cancel preserve simulation, RNG and native result')


def deliberate_chain():
    with GamePortSession(DISK, menu=False) as s:
        collected_water(s)
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok')
        assert byte(s, 'it_pack_lo', 38) == 10
        assert not byte(s, 'fire_on') and not byte(s, 'camp_use')
        event(s, 'ok')                    # one USE MATCHES
        assert byte(s, 'it_pack_lo', 38) == 9
        assert not byte(s, 'fire_on') and byte(s, 'camp_use') == 1
        assert 'MAKE FIRE' in ' '.join(rows(s))
        event(s, 'ok')                    # one MAKE FIRE
        assert byte(s, 'fire_on') == 1 and not byte(s, 'camp_use')
        assert byte(s, 'it_place', 73) == 2
        assert 'USE UTENSILS' in ' '.join(rows(s))
        event(s, 'ok')                    # one USE UTENSILS
        assert byte(s, 'it_place', 73) == 0 and byte(s, 'camp_use') == 32
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-.75) < .001
        assert byte(s, 'it_pack_lo', 22) == 20 and byte(s, 'it_gnd_lo', 22) == 0
        assert 'PREPARATION READY' in ' '.join(rows(s))
        before = state(s)
        event(s, 'ok')                    # review original native quantity
        assert not byte(s, 'camp_pending')
        assert byte(s, 'menu_noun') == 22 and byte(s, 'obj_side') == 1
        assert byte(s, 'input_value') == 20
        assert 'HOW MANY OZ?' in ' '.join(rows(s))
        right = ' '.join(line[41:] for line in rows(s)[20:24])
        assert 'PREPARATION READY' not in right and 'CONTINUE ORIGINAL' not in right
        unchanged(before, s)
        event(s, 'cancel', IDLE)
        unchanged(before, s)
    print('CAMP: matches/fire/utensils each explicit; original 20 OZ canteen restored')


def boil_drink():
    with GamePortSession(DISK, menu=False) as s:
        collected_water(s)
        for _ in range(5):
            event(s, 'ok')       # BOIL proposal, matches, fire, utensils, review
        assert 'HOW MANY OZ?' in ' '.join(rows(s))
        event(s, 'ok')           # accept exactly the original 20 OZ
        assert 'BOILED PORTION' in ' '.join(rows(s))
        assert 'WATER 20 OZ GROUND' in ' '.join(rows(s))
        assert byte(s, 'it_pack_lo', 22) == 0 and byte(s, 'it_gnd_lo', 22) == 20
        before = state(s)
        event(s, 'ok')           # deliberate DRINK, exact ground source
        assert byte(s, 'obj_side') == 0 and byte(s, 'menu_noun') == 22
        assert byte(s, 'input_value') == 8
        after = state(s)
        assert not differing(before[0], after[0], DERIVED_BYTES | {L["ui_dirty"]})
        assert before[1] == after[1]
        event(s, 'ok', IDLE)
        assert 'YOU DRANK 8 OUNCES' in ' '.join(rows(s))
        assert byte(s, 'it_pack_lo', 22) == 0 and byte(s, 'it_gnd_lo', 22) == 12
    print('CAMP: guided BOIL yields deliberate DRINK of exact ground portion')


def grid_boil_prerequisite():
    with GamePortSession(DISK, menu=False) as s:
        boot(s)
        s.step(L.poke('fire_on', 1))
        s.step(L.poke('camp_use', 0))
        s.step(L.poke('it_place', 2, 73))
        s.step(L.poke('it_place', 2, 22))
        s.step(L.poke('it_pack_lo', 20, 22))
        s.step(L.poke('it_pack_hi', 0, 22))
        s.step(L.poke('it_gnd_lo', 0, 22))
        s.step(L.poke('it_gnd_hi', 0, 22))
        event(s, 'right', IDLE)
        event(s, 'left', IDLE)
        before = state(s)
        grid(s, 'BOIL', ready=READY)
        assert 'USE UTENSILS' in ' '.join(rows(s))
        assert byte(s, 'it_place', 73) == 2 and not byte(s, 'camp_use')
        unchanged(before, s)
        event(s, 'cancel', IDLE)
        unchanged(before, s)
        grid(s, 'BOIL', ready=READY)
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok')               # only now set utensils down
        assert byte(s, 'it_place', 73) == 0 and byte(s, 'camp_use') == 32
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-.25) < .001
        assert byte(s, 'it_pack_lo', 22) == 20 and byte(s, 'it_gnd_lo', 22) == 0
        assert 'PREPARATION READY' in ' '.join(rows(s))
        event(s, 'ok', IDLE)         # review original BOIL quantity list
        assert byte(s, 'it_pack_lo', 22) == 20 and byte(s, 'it_gnd_lo', 22) == 0
        assert byte(s, 'camp_pending') == 0
        event(s, 'cancel', IDLE)
    print('CAMP: direct BOIL requires deliberate utensils; inspect/cancel frozen')


def gray_intents():
    for water, choice, verb in ((False, 2, 17), (True, 1, 18)):
        with GamePortSession(DISK, menu=False) as s:
            boot(s)
            s.step(L.poke('fire_on', 0))
            s.step(L.poke('camp_use', 0))
            s.step(L.poke('it_place', 2, 38))
            s.step(L.poke('it_pack_lo', 10, 38))
            open_flow(s, water=water, choice=choice)
            before = state(s)
            event(s, 'ok')
            assert byte(s, 'camp_intent') == verb
            assert not byte(s, 'menu_noun')   # native source form still needed
            assert 'USE MATCHES' in ' '.join(rows(s))
            unchanged(before, s)
            event(s, 'cancel', IDLE)
            unchanged(before, s)
    print('CAMP: unavailable COOK/BOIL offer deliberate setup; cancel frozen')


if __name__ == '__main__':
    cancellation()
    deliberate_chain()
    boil_drink()
    gray_intents()
    grid_boil_prerequisite()
