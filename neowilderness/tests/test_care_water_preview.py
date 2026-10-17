#!/usr/bin/env python3
"""STATUS water sources match native DRINK/WET ordering, using joystick only."""
import tempfile
from common import L, disk_with, fp
import geo_atlas
from mkmap import MAP_BYTES
from test_forest import map_fixture
from test_fit_quantities import boot
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, IDLE
from test_status_care_return import open_care, returned, RESULT
from test_save import differing, DERIVED_BYTES

STOCK = 'WATER STOCK HERE; OZ NEXT'
NEAR = 'RIVER/LAKE HERE'
NONE = 'NO WATER HERE; FIND WATER'
WET = 'ALREADY WET; NO OZ NEEDED'
QUANTITY = L.until('input_number_idle', 60000)


def fixture(native=False, water=None):
    m = map_fixture()
    m[2:6] = bytes((64, 20, 64, 20))
    if native:
        m[37] = 1
        fine = bytearray([10]) * (224*168)
        if water:
            x, y, kind = water
            fine[y*224+x] = kind
        woods = bytes(28*168)
        m[64:MAP_BYTES] = geo_atlas.Fine('care', bytes(fine), woods, (20, 20), (70, 70), True).coarse()
        m += fine + woods
    elif water:
        x, y, kind = water
        m[64+y*112+x] = kind
    return m


def check(disk, name, expected, gesture=0, place=2, packed=0, ground=0,
          local=True, front=0, wet=0, action='cancel'):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        event(s, 'up'); event(s, 'cancel', IDLE)  # settle native journey-distance cache
        s.step(L.poke('it_place', place, 22))
        for field, value in (('it_pack', packed), ('it_gnd', ground)):
            s.step(L.poke(field+'_lo', value & 255, 22))
            s.step(L.poke(field+'_hi', value >> 8, 22))
        s.step(L.poke('it_x', 20+int(not local), 22))
        s.step(L.poke('it_y', 20, 22))
        s.step(L.poke('weather_inside_front', front))
        s.step(L.poke('wet_mode', wet))
        s.step(L.poke('camp_untreated', 7))
        s.step(L.poke('geo_wooded', 91)); s.step(L.poke('geo_water_kind', 64))
        s.step(L.poke('injury_active', 1, 4))
        before = saved_state(s)
        event(s, 'up'); event(s, 'down')
        if gesture:
            event(s, 'right')
        line = rows(s)[22]
        assert f'0 MIN; {expected}' in line and 'DOSES' not in line, (name, line)
        assert not differing(before, saved_state(s), DERIVED_BYTES), (name, differing(before, saved_state(s), DERIVED_BYTES))
        before = saved_state(s)
        assert byte(s, 'camp_untreated') == 7
        assert byte(s, 'geo_wooded') == 91 and byte(s, 'geo_water_kind') == 64
        event(s, 'right'); event(s, 'left')
        assert rows(s)[22] == line and saved_state(s) == before
        event(s, 'cancel', IDLE)
        assert saved_state(s) == before
        open_care(s, [4], 4, gesture)
        clock = s.step(L.peek('s_elap', 5)).data
        hydration = fp(s.step(L.peek('s_defw', 5)).data)
        if action in ('quantity', 'consume'):
            event(s, 'ok', QUANTITY)
            if action == 'consume':
                # Eight-frame axis pulses repeat twice in the native spinner.
                for _ in range(2):
                    event(s, 'up', QUANTITY)
                assert byte(s, 'input_value') == 4
                assert byte(s, 'it_pack_lo', 22) == packed
                event(s, 'ok', RESULT)
                assert byte(s, 'medical_actions', 8 if gesture else 5) == int(bool(gesture))
                if not gesture:  # DRINK_FIDELITY=0 preserves the current reference
                    assert fp(s.step(L.peek('s_defw', 5)).data) < hydration
                packed -= 4
            else:
                event(s, 'cancel', RESULT)
        else:
            event(s, 'ok', RESULT)
            accepted = action == 'wet'
            assert byte(s, 'medical_actions', 8) == int(accepted), name
            if expected == NONE:
                text = '\n'.join(r[:39] for r in rows(s)[20:23])
                assert ('NO WATER AT HAND' if gesture else 'NOT ACCESSIBLE') in text, (name, text)
        assert s.step(L.peek('s_elap', 5)).data == clock
        returned(s, 4, gesture)
        # A confirmed native DRINK creates its 160-OZ local pile before asking
        # quantity. Cancelling that prompt retains the pile, as in typed play.
        made_pile = expected == NEAR and gesture == 0
        after_hint = STOCK if made_pile else expected
        assert after_hint in rows(s)[22], (name, rows(s)[22])
        if made_pile:
            ground = 160
        assert byte(s, 'it_pack_lo', 22) == packed & 255
        assert byte(s, 'it_pack_hi', 22) == packed >> 8
        assert byte(s, 'it_gnd_lo', 22) == ground & 255
        assert byte(s, 'it_gnd_hi', 22) == ground >> 8
        print(f'  {name}: {expected}; preview read-only, native {action}, 0 MIN, return: OK', flush=True)


def bearings(disk):
    # Direction words were banked to make room for the source predicate.
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        for dx, dy, label in ((0, 4, 'NORTH'), (0, -4, 'SOUTH'),
                              (4, 0, 'EAST'), (-4, 0, 'WEST'),
                              (4, 4, 'NORTH-EAST'), (-4, 4, 'NORTH-WEST'),
                              (4, -4, 'SOUTH-EAST'), (-4, -4, 'SOUTH-WEST')):
            s.step(f'poke:7008:{20+dx:02X}')
            s.step(f'poke:7009:{20+dy:02X}')
            event(s, 'up')
            while byte(s, 'pg_cur') != 6:  # bearings are on MENU
                event(s, 'left')
            assert label in '\n'.join(rows(s)), (label, rows(s))
            event(s, 'cancel', IDLE)
    print('  Eight goal bearings retain their banked direction words: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        dry = disk_with(tmp, fixture())
        for name, kwargs in (
            ('carried stock', dict(packed=4)),
            ('local stock', dict(place=0, ground=9)),
            ('mixed stock', dict(packed=4, ground=9)),
            ('full 16-bit stock', dict(packed=65535)),
            ('hung pack, local pile', dict(place=5, packed=4, ground=9)),
        ):
            for gesture in (0, 1):
                check(dry, f'{name}, gesture {gesture}', STOCK, gesture=gesture,
                      action='quantity', **kwargs)
        for gesture in (0, 1):
            check(dry, f'consume four ounces, gesture {gesture}', STOCK,
                  gesture=gesture, packed=9, action='consume')
        for name, kwargs in (
            ('empty', dict()), ('absent', dict(place=255, packed=4)),
            ('hung only', dict(place=5, packed=4)),
            ('remote ground', dict(place=0, ground=9, local=False)),
        ):
            for gesture in (0, 1):
                check(dry, f'{name}, gesture {gesture}', NONE, gesture=gesture, **kwargs)
        check(dry, 'weather front', WET, gesture=1, front=1, action='wet')
        check(dry, 'immersed', WET, gesture=1, wet=2, action='wet')
        check(dry, 'damp alone needs water', NONE, gesture=1, wet=1)
        for native, water, near, name in (
            (False, (21, 20, 128), True, 'legacy adjacent river'),
            (False, (21, 21, 192), True, 'legacy diagonal lake'),
            (False, (22, 20, 128), False, 'legacy distant river'),
            (True, (40, 40, 128), True, 'native current river'),
            (True, (40, 40, 192), True, 'native current lake'),
            (True, (41, 40, 128), False, 'native adjacent fine river'),
        ):
            disk = disk_with(tmp, fixture(native, water))
            for gesture in (0, 1):
                check(disk, f'{name}, gesture {gesture}', NEAR if near else NONE,
                      gesture=gesture, action=('wet' if gesture else 'quantity') if near else 'cancel')
            if near:
                check(disk, name+' drink prefers stock', STOCK, packed=4, action='quantity')
                check(disk, name+' wet prefers river', NEAR, gesture=1, packed=4, action='wet')
        bearings(dry)
    print('Care water preview: OK')
