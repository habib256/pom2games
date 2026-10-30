#!/usr/bin/env python3
"""ROBOT SPACE STATION, the logic simulation on random boards (make test-long):
each board (up to 16 gates of every kind, random wires, loops included) is
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
from model import AND, BUF, FLIP, NOT, OR, XOR, GATE_INPUTS, Board, Sim, compile_board, save_bytes
from test_lab import BOOT, MACHINE, POKE, SYNC, check, click, idle, run, title
from test_model import EMPTY
from test_zone import disk_with_save

BOARDS, TURNS = 12, 12
KINDS = (AND, OR, XOR, NOT, FLIP)          # (BUF is a chip's input, not in the palette)


def random_board(rng):
    b = Board()
    cells = rng.sample([(c, r) for c in range(5) for r in range(5)], rng.randint(4, 16))
    for c, r in cells:
        b.place(rng.choice(KINDS), c, r)
    parts = [i for i, p in enumerate(b.parts) if p]
    sources = list(range(4)) + [8 + i * 4 for i in parts]
    for i in parts:
        for k in range(GATE_INPUTS[b.parts[i][0]]):
            if rng.random() < 0.9:
                b.connect(rng.choice(sources), 8 + i * 4 + k)
    for k in range(4):
        b.connect(rng.choice(sources), k)
    return b


def board_run(n, b, rng, L):
    inputs = [[rng.randint(0, 1) for _ in range(4)] for _ in range(TURNS)]
    disk = disk_with_save(save_bytes(EMPTY, lab=b), f'fuzz{n}')
    steps = [BOOT] + title(1) + ['wait:60', idle(L)]
    for ins in inputs:
        steps += [L.poke('_lab_inputs', v, k) for k, v in enumerate(ins)]
        steps += ['key:P', 'wait:20', idle(L), L.peek('_values', 72)]
    r = run(disk, steps)
    sim = Sim(compile_board(b, EMPTY))
    fails = 0
    for t, ins in enumerate(inputs):
        sim.tick(ins + [0] * 4)
        if r.mem(L['_values'], 72, t) != bytes(sim.values):
            fails += check(f'board {n} ({len([p for p in b.parts if p])} gates): turn {t + 1}',
                           r.mem(L['_values'], 72, t), bytes(sim.values))
            break
    else:
        fails += check(f'board {n}: {TURNS} turns == the model', b'', b'')
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
    fails = sum(board_run(n, random_board(rng), rng, L) for n in range(BOARDS))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
