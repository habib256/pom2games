#!/usr/bin/env python3
"""The joystick and the keyboard, in the game (a2run's joy:X,Y and btn:N,b).

  * the stick's X leans the bike, analog: in_lean = stick_lean(joy_x -
    joy_mx) at several deflections both ways (the formula below is
    src/input.inc's), from 0 in the dead zone to LEAN_MAX;
  * button 0 = full throttle, button 1 = brake; both: the brake wins (the
    bike, sped up with button 0, stops with both held and stays stopped);
  * the stick in the menus: a button leaves the title and starts track 1;
    in the main menu one push = one item, back to the centre for the next,
    held it repeats (stops at the last item), a button chooses;
  * no stick plugged (both paddle timers open, the buttons floating
    "pressed"): no stick found, the keyboard device, nothing taken from the
    buttons (no throttle, no brake, the title stays), the keys drive;
  * INPUT in the main menu: the keyboard alone (the stick no longer leans),
    kept in DIRTHOF; the next boot starts with it.
"""
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test  # noqa: E402
import dos33  # noqa: E402
import physics  # noqa: E402

DISK = GAME.parent / 'dist/DIRTBIKE.dsk'
JOY_DEAD, JOY_STEP = 6, 3                    # = src/input.inc
INP_STICK, INP_KEYS = 0, 1
RACE = ['wait:1000', 'key: ', 'wait:60', 'key:\r']


def stick_lean(d):
    """Stick X minus its centre (read_stick_fast counts) -> lean level."""
    m = abs(d)
    lv = 0 if m < JOY_DEAD else min(physics.LEAN_MAX, ((m - JOY_DEAD) >> JOY_STEP) + 1)
    return lv if d >= 0 else -lv


def s8(v):
    return v - 256 if v & 0x80 else v


def main():
    L = a2test.labels(GAME / 'build/dirtbike.lbl')
    bad = 0
    JOY, IN = L['joy_ok'], L['in_throttle']          # joy_ok, x, y, mx, my / throttle, brake, lean

    def look():
        return [L.until('main_loop', 60), f'peek:{JOY:04X}:5', f'peek:{IN:04X}:3']

    # analog lean, the countdown held (count_t) so the bike stays still
    xs = (0, 0.1, 0.2, 0.3, 0.45, 0.6, 1, -0.1, -0.2, -0.35, -0.6, -1)
    steps = RACE + [L.until('new_race', 900)]
    for x in xs:
        steps += [L.poke('count_t', 60), f'joy:{x},0', 'wait:6'] + look()
    r = a2test.run(DISK, steps)
    seen, ok = [], True
    for i, x in enumerate(xs):
        j, inp = r.mem(JOY, 5, i), r.mem(IN, 3, i)
        d = j[1] - j[3]
        want, have = stick_lean(d), s8(inp[2])
        seen.append(have)
        ok &= j[0] == 1 and want == have
        print(f'  stick {x:+5}: count {j[1]:3} (centre {j[3]}), d {d:+4}: lean {have:+} (model {want:+})')
    ok &= set(seen) == set(range(-4, 5)) and seen == sorted(seen[:7]) + sorted(seen[7:], reverse=True)
    print('stick X: analog lean, every level both ways, 6502 == stick_lean: ' + ('ok' if ok else 'DIFF'))
    bad += not ok

    # buttons; then a ride: button 0 speeds up, both buttons stop the bike
    steps = RACE + [L.until('new_race', 900), L.poke('count_t', 60), 'joy:0,0', 'btn:0,1', 'wait:4'] + look() + \
        [L.poke('count_t', 60), 'btn:0,0', 'btn:1,1', 'wait:4'] + look() + \
        [L.poke('count_t', 60), 'btn:0,1', 'wait:4'] + look() + \
        ['btn:0,0', 'btn:1,0', L.poke('count_t', 1), 'btn:0,1', 'wait:80', L.peek('pt_xl', 2), L.peek('pt_xh', 2),
         'btn:1,1', 'wait:200', L.peek('pt_xl', 2), L.peek('pt_xh', 2), L.peek('in_throttle', 1),
         'wait:60', L.peek('pt_xl', 2), L.peek('pt_xh', 2), L.peek('crashed', 1)]
    r = a2test.run(DISK, steps)
    b0, b1, both = (r.mem(IN, 3, i) for i in range(3))
    x = [r.mem(L['pt_xl'], 2, k)[0] + 256 * r.mem(L['pt_xh'], 1, k)[0] for k in range(3)]
    ok = (b0[0] == physics.THROTTLE_MAX and b0[1] == 0 and b1[0] == 0 and b1[1] != 0 and both[1] != 0
          and x[0] > 100 and x[1] > x[0] and abs(x[2] - x[1]) <= 1 and r.mem(L['crashed'], 1)[0] == 0)
    print(f'buttons: 0 -> throttle {b0[0]}, 1 -> brake {b1[1]:#x}; ridden to x {x[0]}, both held: '
          f'stopped at {x[1]}, still {x[2]} a second later: ' + ('ok' if ok else 'DIFF'))
    bad += not ok

    # the stick in the menus: title -> track menu -> track 1 with the button;
    # main menu: one push, one item; held: repeats up to the last
    btn = ['btn:0,1', 'wait:3', 'btn:0,0']
    r = a2test.run(DISK, ['wait:1000'] + btn + [L.until('menu_input', 300), 'wait:20'] + btn +
                   [L.until('new_race', 900), 'wait:100', 'key:\x1b', L.until('mm_key', 300), 'wait:10',
                    L.peek('mm_sel', 1),
                    'joy:0,1', 'wait:6', 'joy:0,0', 'wait:6', L.until('mm_key', 60), L.peek('mm_sel', 1),
                    'joy:0,1', 'wait:6', 'joy:0,0', 'wait:6', L.until('mm_key', 60), L.peek('mm_sel', 1),
                    'joy:0,1', 'wait:90', 'joy:0,0', 'wait:6', L.until('mm_key', 60), L.peek('mm_sel', 1),
                    'joy:0,-1', 'wait:6', 'joy:0,0', 'wait:6', L.until('mm_key', 60), L.peek('mm_sel', 1),
                    'joy:-1,0', 'wait:6', 'joy:0,0', 'wait:6', L.until('mm_key', 60), L.peek('mm_sel', 1)]
                   + btn + [L.until('mm_hof', 60), 'wait:30'] + btn + ['wait:30'] + btn +
                   [L.until('mm_key', 300), L.peek('mm_sel', 1)])
    sel = [d[0] for d in r.dumps]
    ok = sel == [0, 1, 2, 5, 4, 4, 4]
    print(f'stick in the menus: button: title, track 1; main menu items {sel} (push, push, held, up, '
          f'left ignored, button: hall of fame and back): ' + ('ok' if ok else 'DIFF'))
    bad += not ok

    # no stick: both timers open, both buttons floating high
    r = a2test.run(DISK, ['joy:9,9', 'btn:0,1', 'btn:1,1', 'wait:1000', L.peek('joy_found', 1),
                          L.peek('inp_dev', 1)] + RACE +
                   [L.until('new_race', 900), 'wait:100'] + look() + ['key:A', 'wait:2'] + look())
    found, dev = r.dumps[0][0], r.dumps[1][0]
    still, keys = r.mem(IN, 3, 0), r.mem(IN, 3, 1)
    ok = (found == 0 and dev == INP_KEYS and r.mem(JOY, 1, 0)[0] == 0 and still == bytes(3)
          and keys[0] == physics.THROTTLE_MAX)
    print(f'no stick: found {found}, device {dev}, buttons "pressed": throttle {still[0]} brake {still[1]}, '
          f'key A: throttle {keys[0]}: ' + ('ok' if ok else 'DIFF'))
    bad += not ok

    # INPUT: keyboard alone, saved; the next boot keeps it
    with tempfile.TemporaryDirectory(prefix='dirtbike-inp-') as tmp:
        saved = Path(tmp) / 'inp.dsk'
        r = a2test.run(DISK, RACE + [L.until('new_race', 900), 'wait:20', L.peek('inp_dev', 1),
                                     'key:\x1b', L.until('mm_key', 300), 'key:3', 'wait:10', L.peek('inp_dev', 1),
                                     'key:\x1b', L.until('main_loop', 900), L.poke('count_t', 60), 'joy:1,0',
                                     'btn:0,1', 'wait:6'] + look() + ['btn:0,0', 'wait:100', f'dsk:{saved}'])
        hof = dos33.read_file(saved.read_bytes(), 'DIRTHOF')
        pref = hof[L['inp_pref'] - L['hof_img']]
        r2 = a2test.run(saved, ['wait:600', L.until('attract', 3000), L.peek('inp_dev', 1)])
        inp = r.mem(IN, 3, 0)
        ok = (r.dumps[0][0] == INP_STICK and r.dumps[1][0] == INP_KEYS and inp == bytes(3)
              and pref == INP_KEYS and r2.dumps[0][0] == INP_KEYS)
        print(f'INPUT: stick -> keyboard alone (stick right + button: lean {s8(inp[2])}, throttle {inp[0]}), '
              f'saved ({pref}), next boot: device {r2.dumps[0][0]}: ' + ('ok' if ok else 'DIFF'))
        bad += not ok
    if bad:
        sys.exit('input: failures')


if __name__ == '__main__':
    main()
