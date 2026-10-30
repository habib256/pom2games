#!/usr/bin/env python3
"""ROBOT SPACE STATION, the logic simulation on random boards (make test-long):
each board (up to 16 parts of every kind, random wires, loops included;
every other one with a random chip burned in P1, once or twice) is
the lab's board in RSS.SAVE; a random sequence of E1-E4 values is poked
into lab_inputs and played turn by turn (key P); the 72 values after each
turn == tools/model.py's Sim. //e, then //c with --iic.

    tests/test_fuzz.py --disk ../dist/ROBOTSTATION.po --labels build/game.lbl [--iic] [--seed N]
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
from model import (AND, CHIP0, FLIP, NOT, OR, POWER, XOR, Board, Chip, Sim, burn, compile_board, part_inputs,
                   part_outputs, save_bytes)
from test_lab import BOOT, MACHINE, POKE, SYNC, check, click, idle, run, title
from test_zone import disk_with_save

BOARDS, TURNS = 12, 12
KINDS = (AND, OR, XOR, NOT, FLIP)          # (BUF is a chip's input, not in the palette)


def random_board(rng, chips=(), most=16):
    """chips: the burned chip slots it may place (P1 = CHIP0)."""
    b = Board()
    cells = rng.sample([(c, r) for c in range(5) for r in range(5)], rng.randint(4, most))
    for n, (c, r) in enumerate(cells):
        b.place(CHIP0 + chips[n] if n < len(chips) else rng.choice(KINDS), c, r)
    parts = [i for i, p in enumerate(b.parts) if p]
    sources = list(range(4)) + [POWER] + [8 + i * 4 + o for i in parts for o in range(part_outputs(b.parts[i][0]))]
    for i in parts:
        for k in range(part_inputs(b.parts[i][0])):
            if rng.random() < 0.9:
                b.connect(rng.choice(sources), 8 + i * 4 + k)
    for k in range(4):
        b.connect(rng.choice(sources), k)
    return b


def board_run(n, rng, L):
    """Board n: odd ones place one or two copies of a random chip burned
    in P1 (its gates flattened into the board's)."""
    chips = [Chip() for _ in range(8)]
    if n % 2:
        chips[0] = burn(random_board(rng, most=6), chips)
        b = random_board(rng, chips=(0,) * rng.randint(1, 2), most=10)
    else:
        b = random_board(rng)
    if compile_board(b, chips) is None:          # (over 64 gates: not this one)
        b = random_board(rng)
    inputs = [[rng.randint(0, 1) for _ in range(4)] for _ in range(TURNS)]
    disk = disk_with_save(save_bytes(chips, lab=b), f'fuzz{n}')
    steps = [BOOT] + title(1) + ['wait:60', idle(L)]
    for ins in inputs:
        steps += [L.poke('_lab_inputs', v, k) for k, v in enumerate(ins)]
        steps += ['key:P', 'wait:20', idle(L), L.peek('_values', 72)]
    r = run(disk, steps)
    sim = Sim(compile_board(b, chips))
    fails = 0
    for t, ins in enumerate(inputs):
        sim.tick(ins + [0] * 4)
        if r.mem(L['_values'], 72, t) != bytes(sim.values):
            fails += check(f'board {n} ({len(sim.flat.gates)} gates): turn {t + 1}',
                           r.mem(L['_values'], 72, t), bytes(sim.values))
            break
    else:
        fails += check(f'board {n} ({len(sim.flat.gates)} gates{", a chip" if n % 2 else ""}): '
                       f'{TURNS} turns == the model', b'', b'')
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', required=True)
    ap.add_argument('--labels', required=True)
    ap.add_argument('--iic', action='store_true')
    ap.add_argument('--seed', type=int, default=2026)
    args = ap.parse_args()
    if args.iic:
        MACHINE[:] = ['--iic']
    L = a2test.labels(args.labels)
    SYNC[:] = [idle(L, 3000)]
    POKE[:] = [L]
    rng = random.Random(args.seed)
    fails = sum(board_run(n, rng, L) for n in range(BOARDS))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
