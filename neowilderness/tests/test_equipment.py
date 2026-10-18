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
        assert byte(s, 'fg_bait')
        assert byte(s, 'it_place', 72) == 2  # prepared does not mean held
        assert byte(s, 'fg_use') & 1
        assert 'LOCATION: PACK' in rows(s)[5] and 'ACTIVE: YES' in rows(s)[7]
        assert 'TRAP PREPARED: YES' in rows(s)[13]
    print('  A trap in PACK is not prepared; automatic bait and native preparation without pretending it is held: OK')


def two_columns():
    from test_joystick_journey import GamePortSession, event, saved_state, READY
    from test_fit_quantities import boot
    for crowded in (False, True):
        with GamePortSession(DISK, menu=False) as s:
            boot(s)
            if crowded:
                # More than a screenful, including long names, in one role.
                for item in (*range(1,22), *range(38,76)):
                    s.step(L.poke('it_place', 1, item))
            event(s, 'up'); event(s, 'right'); event(s, 'right')
            event(s, 'ok')
            before = saved_state(s)
            count = byte(s, 'eq_n')
            split = (count+1)//2 if count < 28 else 14
            assert count > 28 if crowded else 1 < count <= 28
            for index in range(count):
                assert byte(s, 'eq_cur') == index
                top = max(0, index-27)
                offset = index-top
                row, column = 5+offset % split, 1+20*(offset//split)
                page = rows(s)
                assert page[row][column] == '>', (index, row, column, page)
                full_name = page[3][42:79].strip()
                expected = full_name if len(full_name) <= 16 else full_name[:15]+'.'
                assert page[row][column+2:column+18].strip() == expected, (index, expected, page[row])
                assert not postit_errors(s.step('peek:0400:1024').data, 'EQUIPMENT')
                if index+1 < count:
                    event(s, 'down')
            event(s, 'down'); assert byte(s, 'eq_cur') == count-1
            if not crowded:
                s.step('wait:3'); s.step(READY)
                s.step('shot:/tmp/neowilderness-equipment-columns.png')
            for _ in range(count):
                event(s, 'up')
            assert byte(s, 'pg_focus') == 0
            assert saved_state(s) == before
    print('  Two balanced columns: every joystick selection, long names, overflow scrolling, borders and readonly browsing: OK')


def focus_hints_and_cancel():
    from test_joystick_journey import GamePortSession, event, saved_state
    from test_fit_quantities import boot
    with GamePortSession(DISK, menu=False) as s:
        boot(s)
        event(s, 'up'); event(s, 'right'); event(s, 'right')
        before = saved_state(s)
        assert byte(s, 'pg_focus') == 0
        assert 'RETURN: ENTER THE LIST' in rows(s)[4]
        assert 'PAGE' in rows(s)[23] and 'ROLE' not in rows(s)[23]
        event(s, 'ok')
        item = selected(s)
        assert 'RETURN: CHOOSE AN ACTION' in rows(s)[4]
        assert 'ROLE' in rows(s)[23]
        event(s, 'ok')
        assert byte(s, 'om_phase') == 0
        event(s, 'ok')
        assert byte(s, 'om_phase') == 2  # indivisible equipment: explicit confirmation
        event(s, 'cancel')
        assert byte(s, 'om_phase') == 0
        event(s, 'cancel')
        assert byte(s, 'pg_cur') == 2 and byte(s, 'pg_focus') == 1
        assert selected(s) == item
        assert saved_state(s) == before
        event(s, 'right'); event(s, 'right')  # ACTIVE initially has no item
        assert byte(s, 'eq_view') == 2 and byte(s, 'eq_n') == 0
        assert 'NO ACTION: CHOOSE A NONEMPTY ROLE' in rows(s)[4]
        event(s, 'ok')
        assert byte(s, 'pg_cur') == 2 and byte(s, 'eq_n') == 0
        assert saved_state(s) == before
        event(s, 'up')
        assert byte(s, 'pg_focus') == 0 and 'PAGE' in rows(s)[23]
    print('  Joystick hints follow focus; confirmation cancel preserves item and stock; empty role cannot act: OK')


if __name__ == '__main__':
    read_only()
    placement_and_use()
    trap()
    two_columns()
    focus_hints_and_cancel()
    print('EQUIPMENT: OK')
