#!/usr/bin/env python3
"""Real joystick: live USE prerequisites, read-only preview and native outcomes."""
import tempfile
from common import L, disk_with, fp
from test_forest import map_fixture
from test_joystick_journey import (
    GamePortSession, event, byte, rows, object_item, action, saved_state, IDLE,
)
from test_save import differing, DERIVED_BYTES


def choose_use(s, item, side=1):
    object_item(s, side, item)
    event(s, 'ok')
    for _ in range(8):
        if byte(s, 'om_action') == 4:
            break
        event(s, 'down')
    assert byte(s, 'om_action') == 4


def preview(s, item, expected, side=1):
    choose_use(s, item, side)
    before = saved_state(s)
    assert expected in rows(s)[22], rows(s)[22]
    event(s, 'up')
    assert byte(s, 'om_action') != 4 and expected not in rows(s)[22]
    event(s, 'down')
    assert byte(s, 'om_action') == 4 and expected in rows(s)[22]
    event(s, 'ok')
    assert byte(s, 'om_phase') == 2 and expected in rows(s)[22]
    assert saved_state(s) == before
    event(s, 'cancel'); event(s, 'cancel')
    assert not differing(before, saved_state(s), DERIVED_BYTES)


def requirements(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu); event(s, 'ok', IDLE)
        s.step(L.poke('nature_frequency', 0))
        s.step(L.poke('it_place', 2, 72))
        s.step(L.poke('it_place', 2, 41))
        s.step(L.poke('it_pack_lo', 3, 41))
        s.step(L.poke('it_pack_hi', 0, 41))
        event(s, 'up'); event(s, 'right')

        for item, bit in ((72, 1), (67, 2)):
            s.step(L.poke('fg_bait', 0)); s.step(L.poke('fg_use', 0))
            preview(s, item, 'BAIT MISSING. CATCH PREPARES BAIT FIRST.')
            before = saved_state(s)
            action(s, 4)
            assert not differing(before, saved_state(s), DERIVED_BYTES)
            assert not byte(s, 'fg_use') & bit
            assert 'BAIT' in '\n'.join(rows(s)[20:23])
            s.step(L.poke('fg_bait', 1))
            preview(s, item, 'BAIT READY. USE PREPARES TRAP/FISHING.')
            elapsed = s.step(L.peek('s_elap', 5)).data
            action(s, 4)
            assert byte(s, 'fg_use') & bit and byte(s, 'it_place', item) == 2
            assert s.step(L.peek('s_elap', 5)).data == elapsed
        print('  Trap/fishing: missing/ready bait shown before confirmation; cancel/refuse atomic; USE prepares: OK', flush=True)

        s.step(L.poke('light', 0))
        preview(s, 41, 'LIGHT MISSING. USE FLASHLIGHT FIRST.')
        before = saved_state(s)
        action(s, 4)
        assert not differing(before, saved_state(s), DERIVED_BYTES)
        assert byte(s, 'it_pack_lo', 41) == 3
        assert 'LIGHT' in '\n'.join(rows(s)[20:23])
        # Follow the proposed remedy through the same visible object dialog.
        object_item(s, 1, 66)
        batteries = byte(s, 'it_pack_lo', 66)
        action(s, 4)
        assert byte(s, 'light') and byte(s, 'it_place', 66) == 3
        assert byte(s, 'it_pack_lo', 66) == batteries-1
        preview(s, 41, 'LIGHT READY. CONFIRM TO APPLY FIRST AID.')
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        action(s, 4)
        assert byte(s, 'it_pack_lo', 41) == 2
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-.5) < .001
        print('  First aid: missing light, native refusal, USE FLASHLIGHT, ready hint, one dose/30 MIN: OK', flush=True)

        event(s, 'cancel', IDLE)
        event(s, 'up'); event(s, 'left'); event(s, 'left')
        assert byte(s, 'pg_cur') == 6
        event(s, 'ok')
        for _ in range(140):
            if byte(s, 'overlay_text', byte(s, 'eq_cur')) == 72:
                break
            event(s, 'down')
        assert byte(s, 'overlay_text', byte(s, 'eq_cur')) == 72
        for bait, text in ((0, 'BAIT MISSING'), (1, 'BAIT READY')):
            s.step(L.poke('fg_bait', bait))
            event(s, 'ok')
            for _ in range(8):
                if byte(s, 'om_action') == 4:
                    break
                event(s, 'down')
            assert byte(s, 'om_action') == 4
            before = saved_state(s)
            assert text in rows(s)[22]
            event(s, 'ok')
            assert text in rows(s)[22] and byte(s, 'om_phase') == 2
            event(s, 'cancel'); event(s, 'cancel')
            assert not differing(before, saved_state(s), DERIVED_BYTES)
            assert byte(s, 'pg_cur') == 6 and byte(s, 'eq_selected') == 72
        print('  EQUIPMENT uses the same live prerequisite hints and preserves selection on cancel: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        requirements(disk_with(tmp, map_fixture()))
    print('USE requirements: OK')
