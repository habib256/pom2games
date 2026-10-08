#!/usr/bin/env python3
"""Exercise game-port events, held inputs and keyboard priority in the DOS game."""
from check_ergonomics import a2test, L, DISK, START, DUMP, row


def run(steps):
    return a2test.run(DISK, START + steps, emulator=a2test.A2SHOT)


def main():
    # Idle polling cannot consume random numbers, move, or redraw the view.
    r = run(['joy:0,0', 'wait:60', L.peek('p_col', 4), 'peek:0056:2',
             'wait:600', L.peek('p_col', 4), 'peek:0056:2'])
    assert r.mem(L['p_col'], 4, 0) == r.mem(L['p_col'], 4, 1)
    assert r.mem(0x56, 2, 0) == r.mem(0x56, 2, 1)
    r = run(['joy:0.1,-0.1', 'wait:300', L.peek('p_col'), L.peek('p_face'),
             'joy:-1,-1', 'wait:60', L.peek('p_col'), L.peek('p_face')])
    assert r.mem(L['p_col'], 1, 0) == b'\0' and r.mem(L['p_face'], 1, 0) == b'\1'
    assert r.mem(L['p_col'], 1, 1) == b'\1' and r.mem(L['p_face'], 1, 1) == b'\1'
    # BEEF begins facing east in an open corridor. Forward/back restore position.
    r = run(['joy:0,-1', 'wait:60', L.peek('p_col'),
             'wait:300', L.peek('p_col'), 'joy:0,0', 'wait:30',
             'joy:0,1', 'wait:60', L.peek('p_col')])
    assert [r.mem(L['p_col'], 1, i)[0] for i in range(3)] == [1, 1, 0]
    # No keypress is needed to turn, and holding a direction never spins the player.
    r = run(['joy:-1,0', 'wait:60', L.peek('p_face'), 'wait:300', L.peek('p_face'),
             'joy:0,0', 'wait:30', 'joy:1,0', 'wait:60', L.peek('p_face')])
    assert [r.mem(L['p_face'], 1, i)[0] for i in range(3)] == [0, 0, 1]
    r = run(['btn:0,1', 'wait:60', L.peek('view_mode'),
             'wait:300', L.peek('view_mode'), 'btn:0,0', 'wait:30',
             'btn:0,1', 'wait:60', L.peek('view_mode')])
    assert [r.mem(L['view_mode'], 1, i)[0] for i in range(3)] == [1, 1, 0]
    r = run(['btn:1,1', 'wait:60', L.peek('p_hp'), L.peek('p_potions'),
             'wait:300', L.peek('p_potions')])
    assert r.mem(L['p_hp'], 1) == b'\x1e'
    assert r.mem(L['p_potions'], 1, 0) == r.mem(L['p_potions'], 1, 1) == b'\0'
    # Enter a real combat and compare each stick action with its keyboard action,
    # including deterministic fleeing and identical random rolls.
    combat = [L.poke('gstate', 4), L.poke('cur_mob', 0), L.poke('prev_state', 2),
              'poke:10b0:01', 'poke:10b8:1e', L.poke('p_hp', 20), 'key:L', 'wait:60']
    for event, key in [('joy:0,-1', 'A'), ('joy:0,1', 'F'), ('joy:-1,0', 'G'),
                       ('joy:1,0', 'P'), ('btn:0,1', 'A'), ('btn:1,1', 'G')]:
        dump = [L.peek('p_col', L['ev_dmg'] - L['p_col'] + 1), 'peek:10a0:32',
                L.peek('gstate'), 'peek:0056:2']
        stick = run(combat + [event, 'wait:300'] + dump)
        keyboard = run(combat + ['key:' + key, 'wait:300'] + dump)
        assert stick.data == keyboard.data, f'{event} differs from {key}'
    # A pause must retain the stick latch: resume with a held direction is inert.
    r = run(['joy:-1,0', 'wait:60', 'key:\x1b', 'wait:60', 'key:R', 'wait:60',
             'wait:300', L.peek('p_face'), 'joy:0,0', 'wait:30', 'key:L', 'wait:60',
             L.peek('p_face')])
    assert r.mem(L['p_face'], 1, 0) == b'\0' and r.mem(L['p_face'], 1, 1) == b'\1'
    r = run(['key:H', 'wait:60'] + DUMP + ['shot:/tmp/maze3d-joystick-help.png'])
    assert 'STICK MOVE' in row(r, 19) and 'FIGHT:' in row(r, 20)
    print('joystick: movement, map, potion, six combat inputs, held controls, idle RNG and pause/resume')


if __name__ == '__main__':
    main()
