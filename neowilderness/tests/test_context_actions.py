#!/usr/bin/env python3
"""Context defaults and reversible hunting preparation through the game port."""
import tempfile
from common import L, disk_with, a2test
from test_forest import map_fixture
from test_joystick_journey import (
    GamePortSession, event, byte, saved_state, rows, grid, object_item, IDLE, READY,
)
from test_forage import seed_for
from common import fp


def check_context(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu)
        event(s, 'ok', IDLE)
        s.step(L.poke('nature_frequency', 0))
        s.step(L.poke('it_place', 2, 58))  # carried axe, never implicitly active
        s.step(L.poke('care_tools', 0))
        event(s, 'up')
        event(s, 'right')
        object_item(s, 1, 58)
        before = saved_state(s)
        event(s, 'ok')
        assert byte(s, 'om_action') == 4, rows(s)
        assert saved_state(s) == before
        event(s, 'ok')
        assert byte(s, 'om_phase') == 2
        event(s, 'cancel')
        event(s, 'cancel')
        assert saved_state(s) == before
        event(s, 'cancel', IDLE)

        # Fix a visible GAME encounter, remove higher priority weapons.
        for item in (57,):
            s.step(L.poke('it_place', 255, item))
        for slot in (4, 5):
            s.step(L.poke('fg_b2', 0 if slot == 4 else 255, slot))
        for item in (0, 1):
            s.step(L.poke('cr_b1', 255, item))
        s.step(L.poke('fg_use', 0))
        s.step(L.poke('resource_seen', 1))
        s.step(L.poke('light', 1))
        for axis in ('x', 'y'):
            s.step(L.poke('fg_'+axis, byte(s, 'p'+axis, 1)))
        event(s, 'right', IDLE)
        event(s, 'left', IDLE)
        before = saved_state(s)
        grid(s, 'KILL', ready=READY)
        assert 'NEXT: AXE (OWNED)' in ' '.join(rows(s)), rows(s)
        assert 'NO CHANCE' in ' '.join(rows(s)), rows(s)
        assert saved_state(s) == before
        event(s, 'cancel', IDLE)
        assert byte(s, 'mq_n') == 0 and saved_state(s) == before
        # Choosing an owned effective weapon is an explicit UI proposal.
        # An active axe remains the actual native means until confirmation.
        s.step(L.poke('cr_b1', 3, 1))
        s.step(L.poke('care_tools', 1))
        s.step(L.poke('care_tool_x', byte(s, 'px', 1)))
        s.step(L.poke('care_tool_y', byte(s, 'py', 1)))
        before = saved_state(s)
        grid(s, 'KILL', ready=READY)
        assert 'IN USE: AXE' in ' '.join(rows(s)), rows(s)
        event(s, 'right', READY)
        assert '> CHANGE WEAPON' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', READY)
        assert 'NEXT: SPEAR (OWNED)' in ' '.join(rows(s)), rows(s)
        assert 'IN USE: AXE' in ' '.join(rows(s)), rows(s)
        assert saved_state(s) == before
        event(s, 'cancel', IDLE)
        assert byte(s, 'mq_n') == 0 and saved_state(s) == before
        s.step(L.poke('cr_b1', 255, 1))
        # A remembered tool activation at another cell is unavailable here.
        s.step(L.poke('care_tools', 1))
        s.step(L.poke('care_tool_x', (byte(s, 'px', 1)+1) & 255))
        s.step(L.poke('care_tool_y', byte(s, 'py', 1)))
        before = saved_state(s)
        grid(s, 'KILL', ready=READY)
        assert 'NEXT: AXE (OWNED)' in ' '.join(rows(s)), rows(s)
        assert 'NO CHANCE' in ' '.join(rows(s)), rows(s)
        assert saved_state(s) == before
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok', READY)  # activate only, then retained prey review
        assert byte(s, 'mq_n') == 0
        assert byte(s, 'fg_b2', 4) == 0
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed) < .001
        assert 'PREPARATION RESULT' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', READY)
        assert 'IN USE: AXE' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', READY)
        assert 'TRY A BOW, SPEAR OR GUN.' in ' '.join(rows(s)), rows(s)
        assert byte(s, 'fg_b2', 4) == 0  # native axe probability is zero
        assert 'HUNT RESULT: PREY STILL ALIVE' in ' '.join(rows(s)), rows(s)
        after_miss = saved_state(s)
        event(s, 'right', READY)
        assert '> CHANGE WEAPON' in ' '.join(rows(s)), rows(s)
        event(s, 'right', READY)
        assert '> ABANDON' in ' '.join(rows(s)), rows(s)
        assert saved_state(s) == after_miss
        event(s, 'cancel', IDLE)
        assert saved_state(s) == after_miss

        # A prepared bow in daylight is reviewed before its native attempt.
        # The only injected values are fixtures and the native RNG seed.
        s.step(L.poke('care_tools', 0))
        s.step(L.poke('cr_b1', 3, 0))
        s.step(L.poke('fg_use', 4))
        s.step(L.poke('light', 1))
        seed = seed_for(.001, position=1)
        for i in range(4):
            s.step(L.poke('weather_seed', seed >> (8*i) & 255, i))
        s.step(L.poke('travel_pending', 22))  # interrupted native WALK
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        grid(s, 'KILL', ready=READY)
        assert 'IN USE: BOW' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', READY)
        assert byte(s, 'mq_n') == 0 and not byte(s, 'fg_use') & 4
        assert byte(s, 'fg_b2', 4) == 1, rows(s)
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-.25) < .001
        assert 'BITTEN THE DUST' in ' '.join(rows(s)), rows(s)
        assert byte(s, 'travel_pending') == 22
        assert '> SKIN THIS CARCASS' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', READY)  # retained exact carcass, native SKIN
        assert not byte(s, 'fg_skin') & 16
        assert '> GET THIS MEAT' in ' '.join(rows(s)), rows(s)
        before_get = byte(s, 'fg_gl', 4) + 256*byte(s, 'fg_gh', 4)
        event(s, 'ok', READY)
        assert byte(s, 'fg_b1', 4) == 2, rows(s)
        assert byte(s, 'fg_pl', 4) + 256*byte(s, 'fg_ph', 4) == before_get
        assert 'FOOD RECOVERED' in ' '.join(rows(s)), rows(s)
        assert byte(s, 'dep_mask') == 80
        assert byte(s, 'dep_mask', 1) == before_get
        assert byte(s, 'mq_n') == 0
        assert byte(s, 'travel_pending') == 22
        from test_survival_flows import decline_result_followup
        decline_result_followup(s)
        print('Hunt: atomic review, known failure, native attempt, explicit miss choices, SKIN/GET continuity: OK')


def spear_fixture(s):
    from test_fit_quantities import boot
    boot(s)
    for item in (57, 58, 59):
        s.step(L.poke('it_place', 255, item))
    s.step(L.poke('it_place', 2, 60))  # native rope prerequisite
    for slot in (0, 1):
        s.step(L.poke('cr_b1', 255, slot))
    s.step(L.poke('care_tools', 0))
    s.step(L.poke('camp_use', 0))
    s.step(L.poke('fg_use', 0))
    s.step(L.poke('fg_b2', 0, 4))
    s.step(L.poke('fg_b2', 255, 5))
    s.step(L.poke('resource_seen', 1))
    s.step(L.poke('light', 1))
    for axis in ('x', 'y'):
        s.step(L.poke('fg_'+axis, byte(s, 'p'+axis, 1)))
    event(s, 'right', IDLE)
    event(s, 'left', IDLE)


def check_spear_crafting(disk):
    # A native keyboard command supplies the authoritative comparison. The
    # player-facing journey itself uses only game-port events.
    from test_input import command
    with a2test.Session(disk, menu=False) as native:
        spear_fixture(native)
        native_before = saved_state(native)
        native_elapsed = fp(native.step(L.peek('s_elap', 5)).data)
        command(native, 'MAKE SPEAR')
        native_after = saved_state(native)
        native_minutes = (fp(native.step(L.peek('s_elap', 5)).data)-native_elapsed)*60
        assert byte(native, 'cr_b1', 1) == 0
        assert native_minutes > 0
    with GamePortSession(disk, menu=False) as s:
        spear_fixture(s)
        assert saved_state(s) == native_before
        grid(s, 'KILL', ready=READY)
        event(s, 'left', READY)
        assert '> MAKE SPEAR' in ' '.join(rows(s)), rows(s)
        assert saved_state(s) == native_before
        event(s, 'cancel', IDLE)
        assert saved_state(s) == native_before
        grid(s, 'KILL', ready=READY)
        event(s, 'left', READY)
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok', READY)
        assert 'PREPARATION RESULT' in ' '.join(rows(s)), rows(s)
        assert byte(s, 'cr_b1', 1) == 0
        assert byte(s, 'fg_b2', 4) == 0
        assert not byte(s, 'fg_use') & 8
        assert abs((fp(s.step(L.peek('s_elap', 5)).data)-elapsed)*60-native_minutes) < 1e-6
        assert saved_state(s) == native_after, 'Guided MAKE differs from native MAKE'
        after = saved_state(s)
        event(s, 'ok', READY)
        assert 'NEXT: SPEAR (OWNED)' in ' '.join(rows(s)), rows(s)
        assert saved_state(s) == after
        event(s, 'cancel', IDLE)
        assert saved_state(s) == after
        print('Hunt preparation: joystick MAKE SPEAR matches native state/time, then reviews retained prey: OK')



if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        check_context(disk)
        check_spear_crafting(disk)
