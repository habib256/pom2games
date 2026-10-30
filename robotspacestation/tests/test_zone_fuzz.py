#!/usr/bin/env python3
"""ROBOT SPACE STATION, the rooms' physics with random drone boards (make
test-long): a random board for each drone (sensors, claw and radio
included) in a random mission, the technician out of the room; after a
while, at one frame wait, the turn count and the drones, objects, held
objects and doors == tools/model.py's Zone after as many turns. //e, then
//c with --iic.

    tests/test_zone_fuzz.py --disk ../dist/ROBOTSTATION.po --labels build/game.lbl [--iic] [--seed N]
"""
import argparse
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tests'))
import a2test
from model import MISSIONS, NONE, Board, Chip, Zone, compile_board, part_inputs, save_bytes
from test_campaign import tech_at, title_click
from test_fuzz import KINDS
from test_lab import BOOT, MACHINE, POKE, SYNC, check, idle, run
from test_zone import disk_with_save

RUNS = 10
EMPTY = [Chip() for _ in range(8)]


def drone_board(rng):
    """Random parts and wires over the drone's six sources and sinks."""
    b = Board()
    for c, r in rng.sample([(c, r) for c in range(5) for r in range(5)], rng.randint(2, 10)):
        b.place(rng.choice(KINDS), c, r)
    parts = [i for i, p in enumerate(b.parts) if p]
    sources = list(range(6)) + [8 + i * 4 for i in parts]
    for i in parts:
        for k in range(part_inputs(b.parts[i][0])):
            b.connect(rng.choice(sources), 8 + i * 4 + k)
    for k in range(6):
        if rng.random() < 0.7:
            b.connect(rng.choice(sources), k)
    return b


def one(n, rng, L):
    m = rng.randrange(len(MISSIONS))
    two = any('E' in row for row in MISSIONS[m][2])
    a, b = drone_board(rng), drone_board(rng) if two else None
    disk = disk_with_save(save_bytes(EMPTY, reached=m, drone=a, drone2=b), f'zfuzz{n}')
    wait = rng.randint(300, 900)
    steps = [BOOT, 'wait:60'] + title_click(m) + ['wait:150', idle(L), L.peek('_tick_count', 2)]
    steps += tech_at(L, None) + ['key:M', f'wait:{wait}', idle(L), L.peek('_tick_count', 2),
                                 L.peek('_drone_x', 2), L.peek('_drone_y', 2), L.peek('_holding', 2),
                                 L.peek('_obj_x', 4), L.peek('_obj_y', 4), L.peek('_door_open', 2)]
    r = run(disk, steps)
    turns = int.from_bytes(r.mem(L['_tick_count'], 2, 1), 'little') - \
        int.from_bytes(r.mem(L['_tick_count'], 2, 0), 'little')
    z = Zone(m, compile_board(a, EMPTY), compile_board(b, EMPTY) if b else None)
    z.tech = None
    for _ in range(turns):
        z.tick()
        if z.won():
            break
    d, k = len(z.drones), len(z.objects)
    want = (bytes(x.x for x in z.drones) + bytes(x.y for x in z.drones)
            + bytes(NONE if x.holding is None else x.holding for x in z.drones)
            + bytes(o[1] for o in z.objects) + bytes(o[2] for o in z.objects) + bytes(z.door_open))
    got = (r.mem(L['_drone_x'], 2)[:d] + r.mem(L['_drone_y'], 2)[:d] + r.mem(L['_holding'], 2)[:d]
           + r.mem(L['_obj_x'], 4)[:k] + r.mem(L['_obj_y'], 4)[:k] + r.mem(L['_door_open'], 2))
    return check(f'run {n}: mission {m + 1} {MISSIONS[m][0]}, {turns} turns == the model', got, want)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', required=True)
    ap.add_argument('--labels', required=True)
    ap.add_argument('--iic', action='store_true')
    ap.add_argument('--seed', type=int, default=30)
    args = ap.parse_args()
    if args.iic:
        MACHINE[:] = ['--iic']
    L = a2test.labels(args.labels)
    SYNC[:] = [idle(L, 3000)]
    POKE[:] = [L]
    rng = random.Random(args.seed)
    sys.exit(1 if sum(one(n, rng, L) for n in range(RUNS)) else 0)


if __name__ == '__main__':
    main()
