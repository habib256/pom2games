#!/usr/bin/env python3
"""Unavailable intentions: read-only explanations and explicit CAMPUI setup."""
from common import DISK, L
from test_guidance import start, state
from test_screen_returns import visible
from test_joystick_journey import GamePortSession, event, byte, rows, IDLE


def mixed_graphics(s):
    text, mixed = s.step('peek:C01A:2').data
    assert not text & 0x80, 'Full text curtain hid the DHGR view'
    assert mixed & 0x80, 'Mixed graphics result rows are disabled'


def refusal(verb, edits, fragment, guided=False):
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        for name, value, offset in edits:
            s.step(L.poke(name, value, offset))
        event(s, 'ok', IDLE)
        # Reproduce the disabled intention identity consumed by RETURN. Cook
        # can also arrive here from a follow-up when absent from the grid.
        s.step(L.poke('mn_idx', verb | 0x80, byte(s, 'mn_cur')))
        before = state(s)
        pixels_before = visible(s.step('peek:2000:8192').data)
        # Reproduce a prior loader/page leaving full text visible. The
        # refusal must reveal the preserved picture without raycasting.
        s.step('poke:C051:00')
        grid_before = [row[41:79] for row in rows(s)[20:24]]
        result_before = [row[:39] for row in rows(s)[20:24]]
        event(s, 'ok')
        mixed_graphics(s)
        assert fragment in ' '.join(rows(s)), rows(s)
        if guided:
            assert byte(s, 'camp_pending') == 128
            assert [row[:39] for row in rows(s)[20:24]] == result_before, rows(s)
            assert 'RET:ACCEPT ESC:CANCEL' in ' '.join(rows(s)), rows(s)
        else:
            assert [row[41:79] for row in rows(s)[20:24]] == grid_before, rows(s)
            assert 'RETURN / ESC: VIEW' in ' '.join(rows(s)), rows(s)
        assert visible(s.step('peek:2000:8192').data) == pixels_before, 'Refusal changed picture'
        assert state(s) == before, 'Inspecting a refusal changed simulation state'
        # A stale text switch on the return path must also be repaired.
        s.step('poke:C051:00')
        event(s, 'cancel', IDLE)
        mixed_graphics(s)
        assert visible(s.step('peek:2000:8192').data) == pixels_before, 'Cancellation changed picture'
        assert state(s) == before, 'Cancelling a refusal changed simulation state'
    print(fragment + ': read-only explanation and cancellation OK')


if __name__ == '__main__':
    refusal(18, [('fire_on', 0, 0), ('camp_use', 0, 0)], 'NEEDS HEAT', guided=True)
    refusal(18, [('fire_on', 1, 0), ('camp_use', 0, 0), ('it_place', 5, 73)],
            'RECOVER UTENSILS', guided=True)
    refusal(18, [('fire_on', 1, 0), ('camp_use', 32, 0), ('it_place', 2, 73)] +
            [(name, 0, 22) for name in ('it_pack_lo', 'it_pack_hi',
                                      'it_gnd_lo', 'it_gnd_hi')],
            'NO WATER STOCK AVAILABLE TO BOIL')
    refusal(17, [('fire_on', 0, 0), ('camp_use', 0, 0)], 'NEEDS HEAT', guided=True)
    no_food = [('fire_on', 1, 0), ('it_oz_lo', 0, 23), ('it_oz_hi', 0, 23)]
    no_food += [(name, 0, i) for name in ('fg_gl', 'fg_gh', 'fg_pl', 'fg_ph')
                for i in range(11)]
    refusal(17, no_food, 'NO FOOD STOCK AVAILABLE TO COOK')
    refusal(1, [('night', 1, 0), ('light', 1, 0), ('camp_use', 8, 0)],
            'TRAVEL IS REFUSED AT NIGHT')
    refusal(0, [('night', 0, 0)], 'NO WATER HERE OR IN THE NEXT STEP')
