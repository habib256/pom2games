#!/usr/bin/env python3
"""XL: transactional OBJECTS editor, quantities, source identity and preview."""
from common import L, DISK, a2test
from test_objects import open_page, go, rows, state, pile_here, setup

READY = L.until('keyboard_wait', 400000)
IDLE = L.until('idle', 400000)


def key(s, k):
    s.step('press:' + k)
    s.step('wait:1')
    s.step(READY)


def command(s, text):
    s.step('key:' + text + '\\r')
    s.step('wait:1')
    s.step(IDLE)


def new():
    return a2test.Session(DISK)


def stock(s, pk, gd):
    for name, value in [('it_place', 4), ('it_pack_lo', pk), ('it_gnd_lo', gd),
                        ('it_pack_hi', 0), ('it_gnd_hi', 0)]:
        s.step(L.poke(name, value, 25))


def select(s, side=0, item=25):
    open_page(s)
    assert go(s, side, item)
    key(s, '\\r')


def confirm(s):
    key(s, '\\r')
    if s.step(L.peek('om_phase')).data == b'\1':
        key(s, '\\r')
    key(s, '\\r')


def amounts():
    with new() as s:
        s.step(IDLE)
        command(s, 'PACK CANDYBARS 5 OZ')
        assert s.step(L.peek('it_pack_lo', 1, 25)).data == b'\5'
        assert s.step(L.peek('it_gnd_lo', 1, 25)).data == b'\x0b'
        command(s, 'DROP CANDYBARS 2')
        assert s.step(L.peek('it_pack_lo', 1, 25)).data == b'\3'
        assert s.step(L.peek('it_gnd_lo', 1, 25)).data == b'\x0d'
        for line, message in [('PACK CANDYBARS 14', 'SOURCE STOCK'),
                              ('DROP CANDYBARS 0', 'POSITIVE OZ'),
                              ('PACK CANDYBARS 1 H', 'POSITIVE OZ'),
                              ('PACK TENT 1', 'INDIVISIBLE')]:
            before = state(s)
            command(s, line)
            assert state(s) == before, line
            assert message in ' '.join(rows(s)), (line, rows(s)[20:])
    with new() as s:
        s.step(IDLE)
        stock(s, 0, 44)
        s.step(L.poke('it_gnd_hi', 1, 25))
        s.step(L.poke('load_limits', 0xD0))
        s.step(L.poke('load_limits', 7, 1))
        command(s, 'PACK CANDYBARS 257 OZ')
        assert s.step(L.peek('it_pack_lo', 1, 25)).data == b'\1'
        assert s.step(L.peek('it_pack_hi', 1, 25)).data == b'\1'
        assert s.step(L.peek('it_gnd_lo', 1, 25)).data == b'+'
        command(s, 'DROP CANDYBARS 256')
        assert s.step(L.peek('it_pack_lo', 1, 25)).data == b'\1'
        assert s.step(L.peek('it_pack_hi', 1, 25)).data == b'\0'
        assert s.step(L.peek('it_gnd_hi', 1, 25)).data == b'\1'
    print('  Typed partial PACK/DROP; excessive, zero, units and indivisible equipment are atomic: OK')


def wild_amounts():
    with new() as s:
        s.step(IDLE)
        setup(s, pile_here(s))
        command(s, 'PACK INSECTS 5 OZ')
        assert s.step(L.peek('fg_pl', 1, 6)).data == b'\5'
        assert s.step(L.peek('fg_gl', 1, 6)).data == b'\x0f'
        command(s, 'DROP INSECTS 2')
        assert s.step(L.peek('fg_pl', 1, 6)).data == b'\3'
        assert s.step(L.peek('fg_gl', 1, 6)).data == b'\x11'
        s.step(L.poke('fg_pl', 255, 6))
        s.step(L.poke('fg_ph', 255, 6))
        before = state(s)
        command(s, 'PACK INSECTS 1')
        assert state(s) == before
        assert 'VALUE TOO LARGE' in ' '.join(rows(s)[20:23])
    print('  Wild pile partial PACK/DROP and destination overflow without lost stock: OK')


def editor():
    with new() as s:
        s.step(IDLE)
        select(s)
        before = state(s)
        rng = s.step(L.peek('fauna_rng')).data
        key(s, '\\r')            # quantity
        key(s, '\\<')            # one
        for _ in range(4):
            key(s, '\\^')
        assert s.step(L.peek('om_qty', 2)).data == b'\5\0'
        assert 'AFTER: 38 OZ' in rows(s)[22], rows(s)[22]
        assert state(s) == before and s.step(L.peek('fauna_rng')).data == rng
        key(s, '\\r')            # confirmation still read-only
        assert state(s) == before
        key(s, '\\e'); key(s, '\\e'); key(s, '\\e')
        assert state(s) == before and s.step(L.peek('fauna_rng')).data == rng
        key(s, '\\r'); confirm(s)  # all stock, explicit confirmation
        assert s.step(L.peek('it_pack_lo', 1, 25)).data == b'\x10'
        assert s.step(L.peek('it_gnd_lo', 1, 25)).data == b'\0'
    with new() as s:
        s.step(IDLE)
        select(s, item=11)        # weight refusal, preview exposes excess
        assert 'OVER 2 OZ' in rows(s)[22], rows(s)[22]
        before = state(s)
        confirm(s)
        assert 'WEIGHT' in ' '.join(rows(s)[20:23])
        assert state(s) == before
    with new() as s:
        s.step(IDLE)
        stock(s, 0, 255)
        s.step(L.poke('it_gnd_hi', 255, 25))
        select(s)
        assert 'OVERFLOW' in rows(s)[22], rows(s)[22]
        key(s, '\\e')
    with new() as s:
        s.step(IDLE)
        select(s, 1, 21)
        actual = s.step(L.peek('load_used', 8)).data
        projected = s.step(L.peek('om_total', 8)).data
        assert projected[4:] == actual[4:], (actual, projected)
        key(s, '\\e')
    print('  Editor quantities, preview, cancellation, ALL, explicit confirmation and refusal: OK')


def water_transfer():
    with new() as s:
        s.step(IDLE)
        s.step(L.poke('it_pack_lo', 10, 22))
        command(s, 'GET WATER 5 OZ')
        assert s.step(L.peek('it_pack_lo', 1, 22)).data == b'\x0f'
        assert s.step(L.peek('it_gnd_lo', 1, 22)).data == b';'
        select(s, 0, 22)
        used = int.from_bytes(s.step(L.peek('load_used', 2, 6)).data, 'little')
        key(s, '\\r'); key(s, '\\<')
        for _ in range(4):
            key(s, '\\^')
        assert 'TO CANTEEN' in rows(s)[21] and 'NEED 10 IN3' in rows(s)[21], rows(s)[21]
        projected = int.from_bytes(s.step(L.peek('om_total', 2, 6)).data, 'little')
        assert projected == used + 10
        key(s, '\\r'); key(s, '\\r')
        assert s.step(L.peek('it_pack_lo', 1, 22)).data == b'\x14'
        s.step('press:\\e'); s.step('wait:1'); s.step(IDLE)
        s.step(L.poke('it_pack_lo', 63, 22))
        command(s, 'LOOK AHEAD')  # ordinary command does not settle load counters
        # Refusal itself must preserve both stock arrays and time.
        before_stock = tuple(s.step(L.peek(n, 76)).data for n in
                             ('it_pack_lo','it_pack_hi','it_gnd_lo','it_gnd_hi'))
        before_time = s.step(L.peek('s_elap', 5)).data
        command(s, 'GET WATER 2 OZ')
        assert tuple(s.step(L.peek(n, 76)).data for n in
                     ('it_pack_lo','it_pack_hi','it_gnd_lo','it_gnd_hi')) == before_stock
        assert s.step(L.peek('s_elap', 5)).data == before_time
        text = ' '.join(rows(s)[20:23])
        assert 'CANTEEN FULL' in text and 'NEED 2 OZ' in text and 'FREE 1 OZ' in text, text
        command(s, 'GET WATER 1 OZ')
        assert s.step(L.peek('it_pack_lo', 1, 22)).data == b'@'
    print('  Water: exact partial pickup, hand-held canteen volume preview and atomic capacity refusal: OK')


def consumption():
    for side in (0, 1):
        with new() as s:
            s.step(IDLE)
            stock(s, 5, 16)
            select(s, side)
            for _ in range(8):
                if s.step(L.peek('om_action')).data == b'\5':
                    break
                key(s, '\\v')
            assert s.step(L.peek('om_action')).data == b'\5'
            assert s.step(L.peek('om_qty', 2)).data == b'\1\0'
            key(s, '\\r')        # quantity of meal
            key(s, '\\>')        # ALL is unavailable when eating
            assert s.step(L.peek('om_qty', 2)).data == b'\1\0'
            key(s, '\\r'); key(s, '\\r')
            pk = s.step(L.peek('it_pack_lo', 1, 25)).data[0]
            gd = s.step(L.peek('it_gnd_lo', 1, 25)).data[0]
            assert (pk, gd) == ((5, 15) if side == 0 else (4, 16)), (side, pk, gd, rows(s)[20:])
    for side in (0, 1):
        with new() as s:
            s.step(IDLE)
            s.step(L.poke('water_untreated', 1))
            select(s, side, 22)
            for _ in range(8):
                if s.step(L.peek('om_action')).data == b'\6':
                    break
                key(s, '\\v')
            assert s.step(L.peek('om_action')).data == b'\6'
            before_pk = s.step(L.peek('it_pack_lo', 1, 22)).data[0]
            before_gd = s.step(L.peek('it_gnd_lo', 1, 22)).data[0]
            confirm(s)          # inline one-ounce DRINK, no second prompt
            assert s.step(L.peek('water_drinking_untreated')).data == bytes((side,))
            pk = s.step(L.peek('it_pack_lo', 1, 22)).data[0]
            gd = s.step(L.peek('it_gnd_lo', 1, 22)).data[0]
            assert (pk, gd) == ((before_pk, before_gd-1) if side == 0 else
                                (before_pk-1, before_gd)), (side, pk, gd, rows(s)[20:])
    print('  EAT/DRINK use LOCAL/CARRIED stock and water quality; EAT starts at one ounce, never ALL: OK')


if __name__ == '__main__':
    amounts()
    wild_amounts()
    editor()
    water_transfer()
    consumption()
    print('XL OBJECTS actions: OK')
