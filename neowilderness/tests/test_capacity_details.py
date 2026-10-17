#!/usr/bin/env python3
"""Capacity figures from real joystick confirmation, without mutating the journey."""
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, IDLE
from test_fit_quantities import boot
from test_transfer_weight_preview import word, put_word, open_action
from test_save import differing, DERIVED_BYTES

SLOTS = (0, 4, 6, 2)
NAMES = ('WEIGHT', 'PACK', 'HANDS', 'WORN')


def details(s):
    before = saved_state(s)
    summary = rows(s)[22]
    assert byte(s, 'om_phase') == 2 and byte(s, 'om_detail') == 0
    for i, (slot, name) in enumerate(zip(SLOTS, NAMES), 1):
        used = word(s, 'load_used', slot)
        total = word(s, 'om_total', slot)
        limit = word(s, 'load_limits', slot)
        need, free, missing = max(0, total-used), max(0, limit-used), max(0, total-limit)
        event(s, 'right')
        unit = 'OZ' if slot == 0 else 'IN3'
        line = f'{name} NEED {need} FREE {free} MISSING {missing} {unit}'
        assert byte(s, 'om_detail') == i and line in rows(s)[22], (line, rows(s)[22])
        assert 'RETURN CONFIRM' in rows(s)[23]
        assert saved_state(s) == before
    event(s, 'right'); assert rows(s)[22] == summary and byte(s, 'om_detail') == 0
    event(s, 'left'); assert byte(s, 'om_detail') == 4
    for i in (3, 2, 1, 0):
        event(s, 'left'); assert byte(s, 'om_detail') == i
    assert rows(s)[22] == summary and saved_state(s) == before
    return before


def run(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s); event(s, 'up'); event(s, 'right')
        # Both independent constraints remain visible in the summary.
        for target, slot in ((0, 4), (1, 6)):
            for off in (0, slot):
                put_word(s, 'load_limits', word(s, 'load_used', off), off)
            open_action(s, 0, 11, target); event(s, 'ok')
            before = details(s)
            event(s, 'right'); event(s, 'ok')  # Confirm from a detail, native rejection.
            assert not differing(before, saved_state(s), DERIVED_BYTES)
            assert byte(s, 'it_place', 11) == 0
            print(f'  Simultaneous weight/volume refusal, destination {slot}: NEED/FREE/MISSING and native atomic rejection OK', flush=True)

        # Large values fit the line; successful execution remains available from details.
        for slot in (0, 2, 4, 6):
            put_word(s, 'load_limits', 65535, slot)
        s.step(L.poke('it_oz_lo', 40000 & 255, 11)); s.step(L.poke('it_oz_hi', 40000 >> 8, 11))
        open_action(s, 0, 11, 1); event(s, 'ok'); details(s)
        event(s, 'right'); event(s, 'ok')
        assert byte(s, 'it_place', 11) == 3
        print('  40000 OZ need and 65535 capacities: no wrapping/scroll, accepted from detail OK', flush=True)

        # Internal move needs destination space, but no additional carried weight.
        open_action(s, 1, 11, 0); event(s, 'ok'); details(s)
        event(s, 'right'); assert 'WEIGHT NEED 0' in rows(s)[22]
        event(s, 'right'); event(s, 'ok'); assert byte(s, 'it_place', 11) == 2
        open_action(s, 1, 11, 2); event(s, 'ok'); details(s)
        event(s, 'left'); event(s, 'ok'); assert byte(s, 'it_place', 11) == 0
        print('  PACK internal move and DROP release: zero additional weight/space as appropriate OK', flush=True)

        # Existing overload is still missing even if this transfer adds nothing to that slot.
        put_word(s, 'load_limits', word(s, 'load_used', 6)-1, 6)
        open_action(s, 0, 11, 0); event(s, 'ok'); details(s)
        event(s, 'right'); event(s, 'right'); event(s, 'right')
        assert 'HANDS NEED 0 FREE 0 MISSING 1 IN3' in rows(s)[22]
        before = saved_state(s)
        event(s, 'cancel'); assert byte(s, 'om_detail') == 0
        event(s, 'cancel')
        assert not differing(before, saved_state(s), DERIVED_BYTES)
        assert byte(s, 'obj_selected') == 11
        print('  Existing unrelated overload and cancellation preserve selection/state OK', flush=True)

        # Arithmetic overflow retains its explicit refusal instead of misleading numbers.
        for slot in (0, 2, 4, 6):
            put_word(s, 'load_limits', 65535, slot)
        s.step(L.poke('it_gnd_lo', 255, 25)); s.step(L.poke('it_gnd_hi', 255, 25))
        open_action(s, 0, 25, 0); event(s, 'ok'); event(s, 'ok')
        assert byte(s, 'om_phase') == 2 and byte(s, 'om_bad')
        before = saved_state(s)
        event(s, 'right'); assert 'OVERFLOW' in rows(s)[22]
        assert saved_state(s) == before
        print('  Overflow remains explicit; no wrapped capacity details OK', flush=True)


def pages(disk):
    # Text banking to recover modal space must preserve the exact visible pages.
    with GamePortSession(disk, menu=False) as s:
        boot(s); event(s, 'up')
        screen = '\n'.join(rows(s))
        for name in ('SEVERE CUTS', 'BROKEN ARM', 'BROKEN LEG', 'SHOCK', 'SUNBURN',
                     'SNOWBLINDNESS', 'FROSTBITE', 'POISON BITE', 'INFECTION',
                     'SALT DEFICIENCY', 'FOOD POISONING', 'GIARDIA', 'MALARIA', 'ALTITUDE SICKNESS'):
            assert name in screen, (name, screen)
        for _ in range(3):
            event(s, 'left')
        assert byte(s, 'pg_cur') == 4
        event(s, 'down')
        for i, text in enumerate(('HOW OFTEN ANIMALS APPEAR, 0 TO 100 (NATURE).',
                                  'YOUR POSITION ON THE TOPO SHEET.',
                                  'THE TEXT MAP, NEXT TO TOPO.',
                                  'STOP AT FOOD FOUND ON THE WAY (GET FOOD).'), 1):
            assert byte(s, 'pg_focus') == i and text in rows(s)[8], rows(s)[8]
            if i < 4:
                event(s, 'down')
        print('  Four OPTIONS descriptions and fourteen MEDICAL names retain their exact text OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        run(disk)
        pages(disk)
    print('Capacity details: OK')
