#!/usr/bin/env python3
"""CATCH durations: arrow-only queue, inline syntax and original hour prompt."""
from common import L, DISK, DISK140, a2test
from test_input import command, snapshot, screen, IDLE
from test_menu_bar import choose, press, move_to, selected, grid_cells, RET, ESC


def setup(s, target):
    s.step(IDLE)
    s.step(L.poke('nature_frequency', 0))
    for slot in (4, 5):
        s.step(L.poke('fg_b2', 0 if slot == (4 if target == 'GAME' else 5) else 255, slot))
    s.step(L.poke('resource_seen', 1 if target == 'GAME' else 2))
    for axis in ('x', 'y'):
        s.step(L.poke('fg_'+axis, s.step(L.peek('p'+axis, 1, 1)).data[0]))
    s.step(L.poke('it_place', 2, 72 if target == 'GAME' else 67))
    command(s, 'LOOK AHEAD')


def state(s):
    return (snapshot(s), s.step(L.peek('s_hour', L['s_t0']+5-L['s_hour'])).data,
            s.step(L.peek('forage_state', L['forage_state_end']-L['forage_state'])).data,
            s.step(L.peek('weather_seed', 4)).data)


def durations(disk):
    for target, duration, answer in (('GAME', '10 MIN', '.167'), ('GAME', '1 H', '1'),
                                      ('FISH', '30 MIN', '.5'), ('FISH', '8 H', '8')):
        outcomes = []
        for mode in ('grid', 'inline', 'prompt'):
            with a2test.Session(disk) as s:
                setup(s, target)
                if mode == 'grid':
                    press(s, RET)
                    before = state(s)
                    move_to(s, 'CATCH'); press(s, RET)
                    assert sum(grid_cells(s), []) == ['10', 'MIN', '20', 'MIN', '30', 'MIN',
                                                     '1', 'H', '2', 'H', '4', 'H', '8', 'H']
                    assert state(s) == before
                    press(s, ESC, ESC)
                    assert state(s) == before, 'cancelled duration changed the journey'
                    if selected(s) is None:
                        press(s, RET)
                    first, _ = choose(s, 'CATCH', duration)
                    assert first == 'USE BAIT', first
                    assert s.step(L.peek('mq_n')).data == b'\0'
                    assert s.step(L.peek('inbuf', 16)).data.startswith(('CATCH '+target+'\0').encode())
                else:
                    command(s, 'USE BAIT')
                    command(s, 'USE TRAP' if target == 'GAME' else 'USE FISHNG GEAR')
                    if mode == 'inline':
                        command(s, f'CATCH {target} {duration}')
                    else:
                        s.step('key:CATCH '+target); s.step('press:\\r')
                        s.step(L.until('keyboard_wait', 40000))
                        s.step('key:'+answer); s.step('press:\\r'); s.step('wait:1'); s.step(IDLE)
                outcomes.append(state(s))
        assert outcomes[0] == outcomes[1] == outcomes[2], (disk, target, duration)
    print(f'  {disk.name}: CATCH GAME/FISH, 10 MIN to 8 H; grid queue = inline = decimal prompt; ESC atomic: OK')


def invalid(disk):
    with a2test.Session(disk) as s:
        setup(s, 'GAME')
        command(s, 'USE BAIT'); command(s, 'USE TRAP')
        for suffix, expected in (('25 H', 'TOO LONG'), ('1500 MIN', 'TOO LONG'),
                                  ('1 OZ', 'INVALID VALUE OR UNIT'), ('65535 MIN', 'INVALID VALUE OR UNIT'),
                                  ('0 MIN', 'ACTION CANCELLED')):
            before = state(s)
            command(s, 'CATCH GAME '+suffix)
            assert expected in screen(s), (suffix, screen(s))
            assert state(s) == before, (suffix, 'invalid duration changed state')
    print(f'  {disk.name}: zero, wrong unit and excessive inline durations refused without state changes: OK')


def prerequisites(disk):
    for mode in ('missing', 'encounter', 'ready'):
        with a2test.Session(disk) as s:
            setup(s, 'GAME')
            if mode == 'missing':
                s.step(L.poke('it_place', 255, 72))
            elif mode == 'ready':
                command(s, 'USE BAIT'); command(s, 'USE TRAP')
            press(s, RET)
            move_to(s, 'CATCH'); press(s, RET)
            move_to(s, '10 MIN'); s.step('press:\\r')
            s.step(L.until('do_command', 40000))
            first = s.step(L.peek('inbuf', 30)).data.split(b'\0')[0].decode()
            assert first == ('CATCH GAME 10 MIN' if mode == 'ready' else 'USE BAIT'), first
            before = s.step(L.peek('s_elap', 5)).data
            if mode == 'encounter':
                s.step(L.poke('journey_encounters', peek(s, 'journey_encounters')+1))
            s.step(IDLE)
            assert s.step(L.peek('mq_n')).data == b'\0'
            if mode != 'ready':
                assert s.step(L.peek('s_elap', 5)).data == before, mode
                assert not peek(s, 'fg_use') & 1, mode
    print(f'  {disk.name}: missing trap/new encounter stops the queue; ready prerequisites skipped: OK')


def peek(s, name):
    return s.step(L.peek(name)).data[0]


if __name__ == '__main__':
    for disk in (DISK,):
        durations(disk)
        invalid(disk)
        prerequisites(disk)
