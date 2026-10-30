#!/usr/bin/env python3
"""ROBOT SPACE STATION, the whole campaign in C (make test-long): each mission
played with tests/test_model.py's solution, its board(s) in RSS.SAVE (the
drone's layout, loaded when the mission starts), the technician poked where
the model has him (on a plate, or out of the room so that no drone takes
him in), then where the goal wants him; won, drones and objects == the
model at its winning turn. //e, then //c with --iic.

    tests/test_campaign.py --disk ../dist/ROBOTSTATION.po --labels build/game.lbl [--iic]
"""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tests'))
import a2test
from model import BEST_SLOTS, MISSIONS, SAVE_SIZE, Zone, compile_board, save_bytes
from test_lab import BOOT, MACHINE, POKE, SYNC, check, click, idle, run
from test_model import EMPTY, TECH, solution
from test_zone import ROOM_Y, disk_with_save

# The technician's second place in the goal-technician missions: the
# charger, once the drones have opened his way (tests/test_model.py).
TECH_GOAL = {5: (16 * 7 + 4, 6 * 8 + 4), 9: (16 * 7 + 2, 2 * 8 + 4), 11: (15 * 7 + 4, 14 * 8 + 4),
             17: (13 * 7 + 2, 15 * 8 + 3)}
TECH_FIRST = {**TECH, 11: (2 * 7 + 4, 8 * 8 + 4)}     # LE SAS: he holds the upper door
OPEN_TICKS = 400                                    # the drones settle, the door opens


def title_click(m):
    """Mission m on the title: two columns of seven a page, PAGE (x 120)
    for the second one (src/title.c)."""
    if m >= 14:
        return click(120, 167) + ['wait:120'] + title_click(m - 14)
    return click(20, 92 + 9 * m + 2) if m < 7 else click(72 + 30, 92 + 9 * (m - 7) + 2)


def tech_at(L, place):
    """Poke the technician (room coordinates; None: out of the room)."""
    x, y = place if place else (0, 0)
    return [L.poke('_act_x', x), L.poke('_act_y', y + ROOM_Y if place else 0)]


def model(m, boards):
    a, b = boards if isinstance(boards, tuple) else (boards, None)
    z = Zone(m, compile_board(a, EMPTY), compile_board(b, EMPTY) if b else None)
    z.tech = TECH_FIRST.get(m)
    for t in range(1, 3001):
        if t == OPEN_TICKS + 1 and m in TECH_GOAL:
            z.tech = TECH_GOAL[m]
        z.tick()
        if z.won():
            return t, z
    raise AssertionError(f'mission {m + 1}: the model does not win')


def mission(m, L):
    boards = solution(m)
    a, b = boards if isinstance(boards, tuple) else (boards, None)
    t, z = model(m, boards)
    disk = disk_with_save(save_bytes(EMPTY, reached=m, drone=a, drone2=b), f'campaign{m + 1}')
    steps = [BOOT, 'wait:60'] + title_click(m) + ['wait:150', idle(L), L.peek('_mission')]
    steps += tech_at(L, TECH_FIRST.get(m)) + ['key:M']
    # (4 to 7 frames a turn: more with an object held or two drones drawn;
    # the game stops at its win, so waiting longer changes nothing)
    if m in TECH_GOAL:
        steps += [f'wait:{OPEN_TICKS * 10}', L.peek('_door_open', 2)] + tech_at(L, TECH_GOAL[m])
    steps += [f'wait:{t * 10 + 600}', idle(L, 3000), L.peek('_won'),
              L.peek('_drone_x', 2), L.peek('_drone_y', 2), L.peek('_obj_x', 4), L.peek('_obj_y', 4),
              L.peek('_persist', SAVE_SIZE)]
    r = run(disk, steps)
    name = MISSIONS[m][0]
    fails = check(f'{m + 1} {name}: loaded', r.mem(L['_mission'], 1), bytes((m,)))
    fails += check(f'{m + 1} {name}: won (model turn {t})', r.mem(L['_won'], 1), b'\x01')
    if m in TECH_GOAL:          # the drones opened his door before he went
        fails += check(f'{m + 1} {name}: his door open', bytes((any(r.mem(L['_door_open'], 2)),)), b'\x01')
    n = len(z.drones)
    fails += check(f'{m + 1} {name}: drones == model',
                   r.mem(L['_drone_x'], 2)[:n] + r.mem(L['_drone_y'], 2)[:n],
                   bytes(d.x for d in z.drones) + bytes(d.y for d in z.drones))
    gates = sum(len(compile_board(x, EMPTY).gates) for x in (a, b) if x)
    best = r.mem(L['_persist'], SAVE_SIZE)[SAVE_SIZE - BEST_SLOTS + m]
    fails += check(f'{m + 1} {name}: record {gates} gates', bytes((best,)), bytes((gates + 1,)))
    k = len(z.objects)
    if k:
        fails += check(f'{m + 1} {name}: objects == model',
                       r.mem(L['_obj_x'], 4)[:k] + r.mem(L['_obj_y'], 4)[:k],
                       bytes(o[1] for o in z.objects) + bytes(o[2] for o in z.objects))
    return fails


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
    POKE[:] = [L]               # clicks through the game's test hook
    fails = sum(mission(m, L) for m in range(len(MISSIONS)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
