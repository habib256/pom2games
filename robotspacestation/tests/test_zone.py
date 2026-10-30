#!/usr/bin/env python3
"""The test zone on an enhanced //e with an AppleMouse, or a //c (a2shot);
clicks go through the game's test hook (src/ui.c test_click).

1. Mission 1 from a fresh disk: walk into the drone, wire a NOT to its
   west thruster, step it (positions against tools/model.py), run it to the
   charger: won, saved; out of the drone, SUITE opens mission 2.
2. Mission 4 from a save file made by the model (missions 1-3 won): wire the
   fetch-the-cell board from the inside, run it: the drone grabs the cell,
   brings it back and lets it go on the charger, tick for tick like the
   model."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tests'))
sys.path.insert(0, str(HERE / 'tools'))
from test_lab import POKE, SYNC, BOOT, title, MACHINE, SHOTS, PALETTE, cell, check, click, idle, pin_in, pin_out, run
import a2test
from model import (AND, FLIP, NOT, OR, MISSIONS, Board, Chip, Zone, compile_board, layout_bytes,
                   room_start, save_bytes)

ROOM_Y = 10
WALK = 'wait:80'                # the technician crosses the board
EMPTY = [Chip() for _ in range(8)]


def zone_button(i):
    """MARCHE 0-29, PAS 33-47, REPLACER/SUITE 51-90, LABO 94-113 / SORTIR 51-80."""
    return click((10, 38, 60, 100)[i], 167)


def inside(*points):
    """Board clicks inside: the technician walks to each one first, then the
    board is redrawn (the main loop idle again: SYNC)."""
    return [s for p in points for s in click(*p) + [WALK] + SYNC]


def src(k):
    return 11, 14 + 21 * k + 5


def sink(k):
    return 128, 14 + 21 * k + 5


def enter_drone(L, mission):
    x, y = room_start('D', MISSIONS[mission][2])
    return click(x + 5, y + ROOM_Y + 6) + ['wait:150', idle(L), L.peek('_screen')]


def disk_with_save(data, name, rooms=True):
    """The game's volume plus an RSS.SAVE file (data None: none); rooms
    False drops RSS.ROOMS."""
    stage = HERE / 'build' / f'stage_{name}'
    shutil.rmtree(stage, ignore_errors=True)
    shutil.copytree(HERE / 'build/stage', stage)
    if data is not None:
        (stage / 'RSS.SAVE#060000').write_bytes(data)
    if not rooms:
        (stage / 'RSS.ROOMS#060000').unlink()
    out = HERE / 'build' / f'{name}.po'
    dev = HERE.parent / 'dev/tools/prodos'
    subprocess.run([sys.executable, str(dev / 'build_volume.py'), str(stage), str(out),
                    '--volume', 'ROBOT.STATION', '--boot', str(dev / 'boot.bin'),
                    '--blocks', '280'], check=True, capture_output=True)
    return out


def mission_one(disk, L):
    fails = 0
    steps = [BOOT] + title(0) + [idle(L), L.peek('_screen'), L.peek('_mission')]
    steps += enter_drone(L, 0)
    steps += click(PALETTE[NOT], 156) + inside(cell(0, 0)) + inside(pin_out(0, 0), sink(3))
    steps += [idle(L), L.peek('_wires', 4)]
    steps += ['key:P', 'wait:2', idle(L)] * 5 + [L.peek('_drone_x'), L.peek('_drone_y')]
    steps += ['key:M', 'wait:900', idle(L, 3000), L.peek('_drone_x'), L.peek('_drone_y'), L.peek('_won', 2),
              L.peek('_persist', 5), f'shot:{SHOTS}/m1_won.png']
    steps += zone_button(2) + ['wait:150', idle(L), L.peek('_screen')]     # SORTIR
    steps += zone_button(2) + ['wait:30', idle(L), L.peek('_mission'),     # SUITE
                               f'shot:{SHOTS}/m2.png']
    r = run(disk, steps)
    screens = [r.mem(L['_screen'], 1, n)[0] for n in range(3)]

    b = Board()
    i = b.place(NOT, 0, 0)
    b.connect(8 + i * 4, 3)
    z = Zone(0, compile_board(b, EMPTY))
    for _ in range(5):
        z.tick()
    fails += check('lab -> zone -> drone -> zone', bytes(screens), bytes((1, 2, 1)))
    fails += check('wired inside', r.mem(L['_wires'], 4)[3:], bytes((8 + i * 4,)))
    fails += check('5 turns', (r.mem(L['_drone_x'], 1, 0) + r.mem(L['_drone_y'], 1, 0)), bytes((z.x, z.y)))
    t = 5
    while not z.won():
        z.tick()
        t += 1
    fails += check(f'on the charger (turn {t})', (r.mem(L['_drone_x'], 1, 1) + r.mem(L['_drone_y'], 1, 1)), bytes((z.x, z.y)))
    fails += check('won and saved', r.mem(L['_won'], 2), b'\x01\x01')
    fails += check('mission 1 recorded', r.mem(L['_persist'], 5), b'RSS2\x01')
    fails += check('SUITE: mission 2', bytes(r.mem(L['_mission'], 1, n)[0] for n in range(2)),
                   bytes((0, 1)))
    return fails


def fetch_board():
    """tests/test_model.py solution(3), placed in the same order."""
    b = Board()
    f = b.place(FLIP, 1, 0)
    k = b.place(NOT, 2, 0)
    j = b.place(NOT, 2, 1)
    a = b.place(AND, 3, 1)
    out = lambda i: 8 + i * 4
    b.connect(1, out(f))
    b.connect(out(f), out(k))
    b.connect(out(k), 3)
    b.connect(out(f), 1)
    b.connect(3, out(j))
    b.connect(out(f), out(a))
    b.connect(out(j), out(a) + 1)
    b.connect(out(a), 4)
    return b


def mission_four(disk, L):
    fails = 0
    steps = [BOOT] + title(0) + ['wait:20', 'key:4', 'wait:120', idle(L),
                                          L.peek('_mission'), f'shot:{SHOTS}/m4.png']
    steps += enter_drone(L, 3)
    steps += click(PALETTE[FLIP], 156) + inside(cell(1, 0))
    steps += click(PALETTE[NOT], 156) + inside(cell(2, 0), cell(2, 1))
    steps += click(PALETTE[AND], 156) + inside(cell(3, 1))
    steps += inside(src(1), pin_in(1, 0, 9), pin_out(1, 0), pin_in(2, 0, 12),
                    pin_out(2, 0), sink(3), pin_out(1, 0), sink(1),
                    src(3), pin_in(2, 1, 12), pin_out(1, 0), pin_in(3, 1, 9),
                    pin_out(2, 1), pin_in(3, 1, 16), pin_out(3, 1), sink(4))
    steps += [idle(L), L.peek('_parts', 48), L.peek('_wires', 72),
              f'shot:{SHOTS}/m4_inside.png']
    steps += ['key:M', 'wait:2400', idle(L, 3000), L.peek('_drone_x'), L.peek('_drone_y'), L.peek('_obj_x', 1),
              L.peek('_obj_y', 1), L.peek('_holding'), L.peek('_won', 2),
              L.peek('_persist', 5), L.peek('_sfx_count'), L.peek('_sound_on')]
    steps += zone_button(2) + ['wait:150', f'shot:{SHOTS}/m4_won.png']
    steps += ['key:S', 'wait:30', idle(L), L.peek('_sound_on')]
    r = run(disk, steps)

    b = fetch_board()
    z = Zone(3, compile_board(b, EMPTY))
    t = 0
    while not z.won() and t < 2000:
        z.tick()
        t += 1
    fails += check('key 4: mission 4', r.mem(L['_mission'], 1), b'\x03')
    fails += check('fetch board wired', r.mem(L['_parts'], 48) + r.mem(L['_wires'], 72),
                   layout_bytes(b))
    fails += check(f'drone back (turn {t})', (r.mem(L['_drone_x'], 1) + r.mem(L['_drone_y'], 1)), bytes((z.x, z.y)))
    fails += check('cell on the charger', r.mem(L['_obj_x'], 1) + r.mem(L['_obj_y'], 1),
                   bytes(z.objects[0][1:]))
    fails += check('cell let go', r.mem(L['_holding'], 1), b'\xff')
    fails += check('won and saved', r.mem(L['_won'], 2), b'\x01\x01')
    fails += check('mission 4 recorded', r.mem(L['_persist'], 5), b'RSS2\x04')
    # sounds: at least the claw's grab and drop, the contacts, the win
    sounds = r.mem(L['_sfx_count'], 1)[0]
    fails += check(f'sounds played ({sounds})', bytes((sounds >= 4, r.mem(L['_sound_on'], 1, 0)[0])), b'\x01\x01')
    fails += check('S: sound off', r.mem(L['_sound_on'], 1, 1), b'\x00')
    return fails


def doors(disk, L):
    """Missions 5 and 6 from a save with 5 missions won."""
    fails = 0
    prog = ['wait:20', 'key:5', 'wait:120', idle(L)]
    steps = [BOOT] + title(0) + prog + enter_drone(L, 4)
    steps += click(PALETTE[NOT], 156) + inside(cell(0, 0)) + inside(pin_out(0, 0), sink(3))
    steps += zone_button(2) + ['wait:150']                          # SORTIR
    steps += click(62, 74) + ['wait:200', idle(L), L.peek('_door_open'),
                              f'shot:{SHOTS}/m5_plate.png']          # onto the plate
    steps += ['key:M', 'wait:900', idle(L, 3000), L.peek('_drone_x'), L.peek('_drone_y'), L.peek('_won', 2),
              f'shot:{SHOTS}/m5_won.png']
    # Mission 6: the same board; the drone parks on the plate, he walks on.
    steps += zone_button(2) + ['wait:30', idle(L), L.peek('_mission')]   # SUITE
    steps += enter_drone(L, 5) + zone_button(2) + ['wait:150']        # nothing to change
    steps += click(118, 66) + ['wait:250', idle(L), L.peek('_door_open'), L.peek('_act_x', 2),
                               L.peek('_won', 2)]                  # door closed: stuck
    steps += ['key:M', 'wait:600', idle(L, 3000), L.peek('_drone_x'), L.peek('_drone_y'), L.peek('_door_open'),
              f'shot:{SHOTS}/m6_parked.png']
    steps += click(118, 66) + ['wait:250', idle(L, 3000), L.peek('_won', 2),
                               L.peek('_persist', 5), f'shot:{SHOTS}/m6_won.png']
    r = run(disk, steps)
    fails += check('5: plate pressed', r.mem(L['_door_open'], 1, 0), b'\x01')
    b = Board()
    b.connect(8 + b.place(NOT, 0, 0) * 4, 3)
    z = Zone(4, compile_board(b, EMPTY))
    z.tech = (60, 60)
    t = 0
    while not z.won():
        z.tick()
        t += 1
    fails += check(f'5: through the door (turn {t})', (r.mem(L['_drone_x'], 1, 0) + r.mem(L['_drone_y'], 1, 0)), bytes((z.x, z.y)))
    fails += check('5: won', r.mem(L['_won'], 1, 0), b'\x01')
    fails += check('SUITE: mission 6', r.mem(L['_mission'], 1), b'\x05')
    fails += check('6: door shut on him', r.mem(L['_door_open'], 1, 1) + r.mem(L['_won'], 1, 1),
                   b'\x00\x00')
    fails += check('6: drone parked, door open', (r.mem(L['_drone_x'], 1, 1) + r.mem(L['_drone_y'], 1, 1)) + r.mem(L['_door_open'], 1, 2),
                   bytes((60, 16, 1)))
    fails += check('6: he reached the charger', r.mem(L['_won'], 2, 2), b'\x01\x01')
    fails += check('all six recorded', r.mem(L['_persist'], 5), b'RSS2\x06')
    return fails


def relay(disk, L):
    """Mission 7, LE RELAIS: wire drone A, crawl through the tunnel, wire
    drone B, run: B parks on its plate and calls, A crosses the second door."""
    fails = 0
    steps = [BOOT] + title(0) + ['wait:30', idle(L), L.peek('_mission'), L.peek('_drone_n')]
    steps += click(40, 32) + ['wait:150', idle(L), L.peek('_screen'), L.peek('_cur_drone')]
    steps += click(PALETTE[FLIP], 156) + inside(cell(0, 0))
    steps += click(PALETTE[NOT], 156) + inside(cell(1, 0))
    steps += click(PALETTE[OR], 156) + inside(cell(2, 0))
    steps += inside(src(5), pin_in(0, 0, 9), pin_out(0, 0), pin_in(1, 0, 12),
                    pin_out(0, 0), sink(0), pin_out(1, 0), pin_in(2, 0, 9),
                    src(2), pin_in(2, 0, 16), pin_out(2, 0), sink(3))
    steps += [f'shot:{SHOTS}/m7_a.png']
    steps += zone_button(2) + ['wait:150']                          # out of A
    steps += click(66, 98) + ['wait:200']                           # into the tunnel
    steps += click(82, 135) + ['wait:250', idle(L), L.peek('_screen'), L.peek('_cur_drone')]
    steps += click(PALETTE[NOT], 156) + inside(cell(0, 0))
    steps += inside(pin_out(0, 0), sink(2), src(0), sink(5))
    steps += [f'shot:{SHOTS}/m7_b.png']
    steps += zone_button(2) + ['wait:150']                          # out of B
    steps += ['key:M', 'wait:3000', idle(L, 3000), L.peek('_drone_x', 2), L.peek('_drone_y', 2),
              L.peek('_won', 2), L.peek('_persist', 5), f'shot:{SHOTS}/m7_won.png']
    r = run(disk, steps)
    from test_model import relay as boards
    a, b = boards()
    z = Zone(6, compile_board(a, EMPTY), compile_board(b, EMPTY))
    t = 0
    while not z.won() and t < 2000:
        z.tick()
        t += 1
    fails += check('mission 7, two drones', r.mem(L['_mission'], 1) + r.mem(L['_drone_n'], 1),
                   b'\x06\x02')
    fails += check('inside A, then B', bytes(r.mem(L['_screen'], 1, n)[0] for n in (0, 1))
                   + bytes(r.mem(L['_cur_drone'], 1, n)[0] for n in (0, 1)), b'\x02\x02\x00\x01')
    fails += check(f'relay done (turn {t})', r.mem(L['_drone_x'], 2) + r.mem(L['_drone_y'], 2),
                   bytes((z.drones[0].x, z.drones[1].x, z.drones[0].y, z.drones[1].y)))
    fails += check('won and saved', r.mem(L['_won'], 2), b'\x01\x01')
    fails += check('seven missions', r.mem(L['_persist'], 5), b'RSS2\x07')
    return fails


def module_two(disk, L):
    """Missions 8-10 (2026-10-30): the title lists ten in two columns; a
    click on the 10th (LE GARDIEN, second column) plays it; key 8 plays LE
    ZIGZAG; key 0 the 10th again. The model proves them (tests/test_model.py)."""
    steps = [BOOT, 'wait:60', f'shot:{SHOTS}/title10.png'] + click(72 + 30, 92 + 2 * 9 + 2) \
        + ['wait:120', idle(L), L.peek('_screen'), L.peek('_mission'), f'shot:{SHOTS}/m10.png']
    steps += ['key:8', 'wait:120', idle(L), L.peek('_mission'), f'shot:{SHOTS}/m8.png']
    steps += ['key:0', 'wait:120', idle(L), L.peek('_mission'), f'shot:{SHOTS}/m10_key.png', 'key:9', 'wait:120', idle(L),
              L.peek('_mission'), f'shot:{SHOTS}/m9.png']
    r = run(disk, steps)
    fails = check('title: the 10th mission clicked', r.mem(L['_screen'], 1) + r.mem(L['_mission'], 1, 0),
                  b'\x01\x09')
    return fails + check('keys 8, 0, 9', bytes(r.mem(L['_mission'], 1, n)[0] for n in (1, 2, 3)),
                         b'\x07\x09\x08')


def missing_rooms(disk, L):
    """Without RSS.ROOMS, JOUER comes back to the title with a message."""
    r = run(disk, [BOOT] + title(0) + ['wait:60', idle(L, 3000), L.peek('_screen')])
    return check('no RSS.ROOMS: back to the title', r.mem(L['_screen'], 1), b'\x03')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', required=True)
    ap.add_argument('--labels', required=True)
    ap.add_argument('--iic', action='store_true')
    args = ap.parse_args()
    if args.iic:
        MACHINE[:] = ['--iic']
    L = a2test.labels(args.labels)
    SYNC[:] = [idle(L, 3000)]
    # The missions click through the game's test hook (ui.c test_click): the
    # mouse itself is exercised by tests/test_lab.py.
    POKE[:] = [L]
    SHOTS.mkdir(parents=True, exist_ok=True)
    fails = mission_one(args.disk, L)
    fails += mission_four(disk_with_save(save_bytes(EMPTY, reached=3), 'reached3'), L)
    fails += doors(disk_with_save(save_bytes(EMPTY, reached=4), 'reached4'), L)
    fails += relay(disk_with_save(save_bytes(EMPTY, reached=6), 'reached6'), L)
    fails += module_two(disk_with_save(save_bytes(EMPTY, reached=9), 'reached9'), L)
    fails += missing_rooms(disk_with_save(None, 'norooms', rooms=False), L)
    print(f'shots in {SHOTS}')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
