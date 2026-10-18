#!/usr/bin/env python3
"""Optional group preparation uses native transfers and leaves cancel exact."""
from common import DISK, L, a2test, text_screen
from test_input import snapshot

IDLE = L.until('idle', 60000)
READY = L.until('keyboard_wait', 60000)


def key(s, k, ready=READY):
    s.step('press:' + k)
    s.step('wait:1')
    s.step(ready)


def byte(s, name, offset=0):
    return s.step(L.peek(name, 1, offset)).data[0]


def state(s):
    return snapshot(s), s.step(L.peek('weather_seed', 4)).data


def start(s):
    menu = L.until('menu_key', 60000)
    s.step(menu)
    key(s, '\\r', menu)
    for _ in range(3):
        key(s, '\\^', menu)
    key(s, '\\r', IDLE)
    s.step(L.poke('nature_frequency', 0))


def open_checklist(s):
    s.step('key:STATUS')
    key(s, '\\r')
    key(s, '\\<')  # STATUS -> MENU, tab focus
    for _ in range(4):
        key(s, '\\v')
    key(s, '\\r')
    assert 'PREPARE DEPARTURE' in '\n'.join(text_screen(s.step('peek:0400:1024').data))


def review(s):
    while byte(s, 'dep_cursor') != 14:
        key(s, '\\v')
    key(s, '\\r')
    assert byte(s, 'dep_running') == 4


def cancellation():
    with a2test.Session(DISK, menu=False) as s:
        start(s)
        before = state(s)
        open_checklist(s)
        key(s, '\\r')  # select backpack
        review(s)
        assert state(s) == before
        key(s, '\\e')  # leave review
        key(s, '\\e', IDLE)
        assert state(s) == before
    print('Departure selection, review and cancellation preserve native state: OK')


def capacity_refusal():
    with a2test.Session(DISK, menu=False) as s:
        start(s)
        s.step(L.poke('load_limits', 1))
        s.step(L.poke('load_limits', 0, 1))
        before = state(s)
        open_checklist(s)
        key(s, '\\r')
        review(s)
        key(s, '\\r')
        assert byte(s, 'dep_running') == 2
        assert state(s) == before
        assert byte(s, 'dep_mask') == 1  # refused item remains pending
        assert 'TRANSFER REFUSED: WEIGHT.' in '\n'.join(text_screen(s.step('peek:0400:1024').data))
        key(s, '\\e', IDLE)
    print('Departure native capacity refusal stops group without moving stock: OK')


def essentials():
    with a2test.Session(DISK, menu=False) as s:
        start(s)
        open_checklist(s)
        for _ in range(5):
            key(s, '\\r')
            key(s, '\\v')
        review(s)
        expected = s.step(L.peek('dep_after', 8)).data
        key(s, '\\r')
        assert byte(s, 'dep_running') == 3
        assert s.step(L.peek('dep_mask', 2)).data == bytes(2)
        assert byte(s, 'it_place', 21) == 3
        assert byte(s, 'it_place', 64) == 3
        assert byte(s, 'it_pack_lo', 22) == 64
        assert byte(s, 'it_place', 53) == 2
        assert s.step(L.peek('load_used', 8)).data == expected
        key(s, '\\e', IDLE)
        s.step('key:STATUS')
        key(s, '\\r')
        key(s, '\\e', IDLE)
    print('Departure essentials execute native transfers; preview matches actual load: OK')


def all_equipment():
    with a2test.Session(DISK, menu=False) as s:
        start(s)
        open_checklist(s)
        for _ in range(14):
            key(s, '\\r')
            key(s, '\\v')
        key(s, '\\r')
        expected = s.step(L.peek('dep_after', 8)).data
        key(s, '\\r')
        assert byte(s, 'dep_running') == 3
        assert s.step(L.peek('dep_mask', 2)).data == bytes(2)
        assert s.step(L.peek('load_used', 8)).data == expected
        for item in (53, 38, 40, 41, 59, 66, 67, 73, 11, 12):
            assert byte(s, 'it_place', item) == 2, item
        key(s, '\\e', IDLE)
    print('All 14 checklist entries use valid native names and match load preview: OK')


if __name__ == '__main__':
    cancellation()
    capacity_refusal()
    essentials()
    all_equipment()
