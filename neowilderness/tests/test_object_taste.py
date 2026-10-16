#!/usr/bin/env python3
"""TASTE inspects the selected pile without stock, time or RNG consumption."""
from common import L, DISK, a2test
from test_objects import rows, state, setup, pile_here
from test_object_actions import select, key, confirm, stock, IDLE
from test_object_care import action, byte


def simulation(s):
    return (state(s), s.step(L.peek('forage_state', L['forage_state_end']-L['forage_state'])).data,
            s.step(L.peek('weather_seed', 4)).data, s.step(L.peek('fauna_rng')).data)


def inspect(side, wild):
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        item = 82 if wild else 25
        if not wild:
            stock(s, 8, 8)
        if wild:
            setup(s, pile_here(s))
            s.step(L.poke('fg_pl', 8, 6))
            s.step(L.poke('fg_b1', 4, 6))
            s.step(L.poke('fg_cl', 6, 17))  # ground insects fresh
            s.step(L.poke('fg_gt', 1, 1))   # ground bitter, carried okay
            s.step(L.poke('fg_pt', 0, 1))
        select(s, side, item)
        before = simulation(s)
        action(s, 6)
        assert rows(s)[20].startswith('ACTION: TASTE '), rows(s)[20]
        assert 'NO STOCK USED / 0 MIN' in rows(s)[21], rows(s)[21]
        assert simulation(s) == before
        key(s, '\\r')
        assert byte(s, 'om_phase') == 2
        key(s, '\\>')  # a held/right quantity gesture cannot consume ALL
        assert byte(s, 'om_phase') == 2 and simulation(s) == before
        key(s, '\\e'); key(s, '\\e')
        assert byte(s, 'pg_focus') == 1 and simulation(s) == before
        key(s, '\\r'); action(s, 6); confirm(s)
        assert simulation(s) == before
        assert byte(s, 'pg_cur') == 1 and byte(s, 'pg_focus') == 1
        assert byte(s, 'obj_selected', side) == item
        assert s.step(L.peek('inbuf', 37)).data.startswith(b'INVENTORY\0')
        result = ' '.join(r[:39] for r in rows(s)[20:23])
        want = 'BITTER' if wild and side == 0 else 'TASTE IS OKAY'
        assert want in result, (want, result)
    print(f'  {"wild" if wild else "provision"}, {"LOCAL" if side == 0 else "CARRIED"}: native taste, source, no quantity, atomic cancel and unchanged simulation: OK')


def applicability():
    for side, item in ((1, 5), (1, 41), (0, 92)):
        with a2test.Session(DISK) as s:
            s.step(IDLE)
            if item == 41:
                s.step(L.poke('it_place', 2, item))
            select(s, side, item)
            assert not byte(s, 'om_mask') & 64, (item, rows(s)[20:])
    print('  No TASTE on boots, medical kits or crafted weapons: OK')


if __name__ == '__main__':
    for wild in (False, True):
        for side in (0, 1):
            inspect(side, wild)
    applicability()
