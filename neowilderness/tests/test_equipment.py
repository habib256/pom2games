#!/usr/bin/env python3
"""XL equipment roles, native activation flags, actions and page context."""
from common import L, DISK, a2test, text_screen, postit_errors
from test_object_actions import key, command, confirm, IDLE
from test_objects import state


def byte(s, name, k=0):
    return s.step(L.peek(name, 1, k)).data[0]


def rows(s):
    return text_screen(s.step('peek:0400:1024').data)


def open_page(s):
    s.step('key:EQUIPMENT\\r')
    s.step('wait:1')
    s.step(L.until('keyboard_wait', 200000))
    assert byte(s, 'pg_cur') == 2


def selected(s):
    return byte(s, 'overlay_text', byte(s, 'eq_cur'))


def go(s, item):
    if not byte(s, 'pg_focus'):
        key(s, '\\r')
    for _ in range(4):
        entries = s.step(L.peek('overlay_text', byte(s, 'eq_n'))).data
        if item in entries:
            target = entries.index(item)
            for _ in range(140):
                if byte(s, 'eq_cur') == target:
                    return
                key(s, '\\^' if byte(s, 'eq_cur') > target else '\\v')
        key(s, '\\>')
    raise AssertionError(('equipment not listed', item, rows(s)))


def act(s, item, action):
    go(s, item)
    key(s, '\\r')
    for _ in range(8):
        if byte(s, 'om_action') == action:
            break
        key(s, '\\v')
    assert byte(s, 'om_action') == action
    confirm(s)
    assert byte(s, 'pg_cur') == 2 and byte(s, 'pg_focus') == 1
    assert byte(s, 'eq_selected') == item


def read_only():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        before = state(s)
        rng = s.step(L.peek('fauna_rng')).data
        key(s, '\\^')
        key(s, '\\>')  # OBJECTS initializes its selections on first visit.
        objects = tuple(s.step(L.peek(n, size)).data for n, size in
                        [('obj_side', 1), ('obj_cur', 2), ('obj_selected', 2)])
        key(s, '\\>')
        assert byte(s, 'pg_cur') == 2
        assert byte(s, 'pg_focus') == 0
        assert 'EQUIPMENT' in rows(s)[0]
        mem = s.step('peek:0400:1024').data
        assert not postit_errors(mem, 'EQUIPMENT'), postit_errors(mem, 'EQUIPMENT')
        entries = s.step(L.peek('overlay_text', byte(s, 'eq_n'))).data
        assert entries and all(byte(s, 'it_place', item) == 1 for item in entries)
        assert 'WORN' in '\n'.join(rows(s)[2:19])
        assert 'HANDS' in '\n'.join(rows(s)[2:19])
        assert 'HANDS VOLUME:' in rows(s)[8]
        assert 'TRAP PREPARED: NO' in rows(s)[13]
        assert state(s) == before and s.step(L.peek('fauna_rng')).data == rng
        go(s, 5)
        assert 'LOCATION: WORN' in rows(s)[5] and 'ACTIVE: NO' in rows(s)[7]
        key(s, '\\r'); key(s, '\\e')
        assert byte(s, 'pg_cur') == 2
        assert tuple(s.step(L.peek(n, size)).data for n, size in
                     [('obj_side', 1), ('obj_cur', 2), ('obj_selected', 2)]) == objects
        assert state(s) == before and s.step(L.peek('fauna_rng')).data == rng
        s.step('press:\\e'); s.step('wait:1'); s.step(IDLE)
        key(s, '\\^')
        assert byte(s, 'pg_cur') == 2 and byte(s, 'pg_focus') == 0
    print('  EQUIPMENT tab, roles, hand volume, read-only browsing/cancel and remembered page: OK')


def placement_and_use():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        open_page(s)
        act(s, 59, 1)           # CARRY KNIFE
        assert byte(s, 'it_place', 59) == 3 and byte(s, 'care_tools') & 2 == 0
        assert 'LOCATION: HANDS' in rows(s)[5] and 'ACTIVE: NO' in rows(s)[7]
        act(s, 59, 4)           # USE KNIFE
        assert byte(s, 'care_tools') & 2
        assert 'LOCATION: HANDS' in rows(s)[5] and 'ACTIVE: YES' in rows(s)[7]
        act(s, 2, 3)            # WEAR DOWN PARKA
        assert byte(s, 'it_place', 2) == 1 and 'LOCATION: WORN' in rows(s)[5]
        act(s, 2, 1)            # CARRY removes the layer
        assert byte(s, 'it_place', 2) == 3 and 'LOCATION: HANDS' in rows(s)[5]
        act(s, 2, 0)            # PACK restores the hand room
        assert byte(s, 'it_place', 2) == 2 and 'LOCATION: PACK' in rows(s)[5]
    print('  Holding a knife does not activate it; native USE, WEAR, REMOVE/CARRY and PACK return to the same item: OK')


def trap():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        s.step(L.poke('it_place', 2, 72))
        open_page(s)
        go(s, 72)
        assert 'LOCATION: PACK' in rows(s)[5] and 'ACTIVE: NO' in rows(s)[7]
        assert 'RETURN: CHOOSE AN ACTION' in rows(s)[4]
        before = state(s)
        act(s, 72, 4)
        assert byte(s, 'fg_use') & 1 == 0
        assert state(s) == before
        assert 'BAIT' in ' '.join(r[:39] for r in rows(s)[20:23])
        s.step('press:\\e'); s.step('wait:1'); s.step(IDLE)
        command(s, 'USE BAIT')
        open_page(s)
        act(s, 72, 4)
        assert byte(s, 'it_place', 72) == 2  # prepared does not mean held
        assert byte(s, 'fg_use') & 1
        assert 'LOCATION: PACK' in rows(s)[5] and 'ACTIVE: YES' in rows(s)[7]
        assert 'TRAP PREPARED: YES' in rows(s)[13]
    print('  A trap in PACK is not prepared; missing bait refusal, then native preparation without pretending it is held: OK')


if __name__ == '__main__':
    read_only()
    placement_and_use()
    trap()
    print('EQUIPMENT: OK')
