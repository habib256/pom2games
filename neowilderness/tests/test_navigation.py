#!/usr/bin/env python3
"""Real game-port events, modal choices, spinners and map exploration.

Both shipping editions; navigation must leave simulation/RNG unchanged.
"""
from common import L, DISK, DISK140, a2test, text_screen
from test_input import snapshot

IDLE = L.until('idle', 60000)
READY = L.until('keyboard_wait', 60000)


def key(s, k, ready=READY):
    s.step('press:'+k)
    s.step('wait:1')
    s.step(ready)


def command(s, line, ready=READY):
    s.step('key:'+line)
    key(s, '\\r', ready)


def rows(s):
    return text_screen(s.step('peek:0400:1024').data)


def byte(s, name, offset=0):
    return s.step(L.peek(name, 1, offset)).data[0]


def state(s):
    return snapshot(s), s.step(L.peek('weather_seed', 4)).data


def joystick(disk):
    with a2test.Session(disk, menu=False) as s:
        s.step(L.until('menu_key', 60000))
        assert 'TMAP' not in '\n'.join(rows(s))
        assert 'ARCHIPELAGO' not in '\n'.join(rows(s))
        key(s, '\\<', L.until('menu_key', 60000))
        assert byte(s, 'ld_nav_cur') == 9  # wrap from Sierra to QUIT
        key(s, '\\>', L.until('menu_key', 60000))
        assert byte(s, 'ld_nav_cur') == 0
        key(s, 'T', L.until('menu_key', 60000))
        assert 'LEVEL 1-10' not in rows(s)[12]
        s.step('btn:0,1'); s.step('wait:8')
        s.step(L.until('menu_key', 60000))
        assert 'LEVEL 1-10' in rows(s)[12]
        # A held button cannot submit the level too.
        s.step('wait:30')
        assert 'LEVEL 1-10' in rows(s)[12]
        s.step('btn:0,0'); s.step('wait:6')
        s.step('btn:0,1'); s.step('wait:1'); s.step(IDLE)
        assert byte(s, 'mn_mode') == 0
        s.step('btn:0,0'); s.step('wait:8')
        before = state(s)
        for x, y in ((0, 0), (.2, .2), (-.2, -.2)):
            heading = s.step(L.peek('heading', 2)).data
            s.step(f'joy:{x},{y}'); s.step('wait:20'); s.step(IDLE)
            assert s.step(L.peek('heading', 2)).data == heading
        s.step('joy:1,0'); s.step('wait:8'); s.step(IDLE)
        assert s.step(L.peek('heading', 2)).data != heading
        # Rotation changes position's heading, so compare physiology/stock.
        assert state(s)[0][1:] == before[0][1:]
        s.step('joy:0,0'); s.step('wait:6')
        s.step('btn:0,1'); s.step('wait:8'); s.step(IDLE)
        assert byte(s, 'mn_mode') == 1 and byte(s, 'mn_level') == 1
        s.step('wait:30'); s.step(IDLE)
        assert byte(s, 'mn_level') == 1
        s.step('btn:0,0'); s.step('wait:6')
        s.step('btn:1,1'); s.step('wait:8'); s.step(IDLE)
        assert byte(s, 'mn_mode') == 0
        s.step('btn:1,0'); s.step('wait:6')
        # A bumped stick does not edit a typed command.
        s.step('key:LOOK'); s.step('wait:1'); s.step(IDLE)
        s.step('joy:-1,0'); s.step('wait:30'); s.step(IDLE)
        assert byte(s, 'linelen') == 4
    print(f'  {disk.name}: joystick boot, dead zone, rotation, button edges, cancel, typing: OK')


def source(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        for name, value in (('fg_gl', 8), ('fg_gh', 0), ('fg_pl', 8),
                            ('fg_ph', 0), ('fg_b1', 4)):
            s.step(L.poke(name, value, 6))
        for axis in ('x', 'y'):
            s.step(L.poke('fg_'+axis, byte(s, 'p'+axis, 1)))
        command(s, 'LOOK AHEAD', IDLE)
        before = state(s)
        command(s, 'EAT INSECTS 1 OZ')
        assert 'GROUND [G]' in '\n'.join(rows(s)[20:])
        key(s, '\\>')
        assert state(s) == before
        key(s, '\\e', IDLE)
        assert state(s) == before
        command(s, 'EAT INSECTS 1 OZ')
        key(s, '\\>'); key(s, '\\r', IDLE)
        assert byte(s, 'fg_gl', 6) == 7 and byte(s, 'fg_pl', 6) == 8
    print(f'  {disk.name}: mixed PACK/GROUND, arrows select GROUND; cancel atomic: OK')


def numbers_and_map(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        before = state(s)
        command(s, 'SAVE')
        key(s, '\\^'); key(s, '\\^')
        assert rows(s)[23].startswith('> 2') and state(s) == before
        key(s, '\\r', IDLE)
        assert 'GAME 2 SAVED.' in '\n'.join(rows(s))
        command(s, 'SAVE 2')
        key(s, '\\r', IDLE)  # safe default N
        assert 'KEPT' in '\n'.join(rows(s))
        assert state(s) == before
        command(s, 'QUIT')
        key(s, '\\>', READY); key(s, '\\e', IDLE)
        assert state(s) == before
        command(s, 'MAP')
        assert 'RETURN EXPLORE MAP' in rows(s)[23]
        key(s, '\\r')
        assert byte(s, 'topo_explore') == 1
        position = (byte(s, 'topo_x'), byte(s, 'topo_y'))
        key(s, '\\<'); key(s, '\\v')
        assert (byte(s, 'topo_x'), byte(s, 'topo_y')) != position
        key(s, '\\r')
        assert (byte(s, 'topo_x'), byte(s, 'topo_y')) == position
        key(s, '\\e')
        assert byte(s, 'topo_explore') == 0
        key(s, '\\e', IDLE)
        assert state(s) == before
    print(f'  {disk.name}: numeric SAVE, overwrite/QUIT cancel, MAP exploration/recenter: OK')


def hall_name(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        goal = s.step(f'peek:{0x7000+8:04X}:2').data
        s.step(L.poke('px', goal[0]-3, 1))
        s.step(L.poke('py', goal[1], 1))
        command(s, 'QUIT')
        key(s, '\\>', READY)
        end = L.until('hof_key_wait', 60000)
        key(s, '\\r', end)
        assert byte(s, 'hof_rank') == 0
        for k in ('\\^', '\\>', '\\^'):
            key(s, k, end)
        assert byte(s, 'hof_len') == 2
        name = s.step('peek:5870:8').data
        assert bytes(c & 127 for c in name) == b'AB      ', name
        key(s, '\\r', end)
        assert 'HALL OF FAME SAVED.' in '\n'.join(rows(s))
    print(f'  {disk.name}: HOF letter wheel and recording without typed letters: OK')


if __name__ == '__main__':
    for disk in (DISK,):
        joystick(disk)
        source(disk)
        numbers_and_map(disk)
        hall_name(disk)
    from test_input import flat, interrupted
    interrupted(flat(), button=True)
    interrupted(flat(), swimming=True, button=True)
