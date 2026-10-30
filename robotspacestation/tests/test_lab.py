#!/usr/bin/env python3
"""The lab on an enhanced //e with an AppleMouse (a2shot): build a half adder
with mouse clicks, burn it, reuse it, and compare the machine's board and
simulation with tools/model.py byte for byte."""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parents[0] / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test
from model import (AND, OR, XOR, NOT, FLIP, CHIP0, SAVE_SIZE, Board, Chip, Sim, burn,
                   compile_board, flat_bytes, layout_bytes, save_bytes)

BOOT = 'wait:1200'
SHOTS = HERE / 'build/shots'

# Screen points (src/board_ui.c).
PALETTE = {AND: 6, OR: 18, XOR: 30, NOT: 42, FLIP: 54}


def chip_x(c):
    return 64 + 10 * c


def cell(col, row):
    return 14 + 22 * col, 12 + 26 * row


def pin_in(col, row, dy):
    x, y = cell(col, row)
    return x + 3, y + dy


def pin_out(col, row, dy=12):
    x, y = cell(col, row)
    return x + 18, y + dy


def term(k, out):
    return (128 if out else 11), 14 + 21 * k + 5


def toggle(k):
    return 4, 14 + 21 * k + 5


BUTTONS = {'marche': 10, 'pas': 38, 'grave': 60, 'efface': 90, 'essai': 120}


# Where the test left the mouse. a2shot's mouse: step is a closed loop (one
# correction of up to 127 per axis each frame, from what the program last
# read): long moves go in hops of 40 so that no correction can overflow the
# card's 8-bit counter, then the pointer settles and the button is pressed.
POS = [None]
SYNC = []                       # main(): wait for the main loop before a move


POKE = []                       # [labels]: click through the test hook instead


def click(x, y):
    if POKE:
        L = POKE[0]
        return SYNC + [L.poke('_test_x', x), L.poke('_test_y', y), L.poke('_test_click', 1),
                       'wait:30']
    steps = list(SYNC)
    if POS[0] is not None:
        px, py = POS[0]
        n = max(abs(x - px), abs(y - py)) // 40
        for k in range(1, n + 1):
            steps += [f'mouse:{px + (x - px) * k // (n + 1)},{py + (y - py) * k // (n + 1)},0',
                      'wait:6']
    POS[0] = (x, y)
    return steps + [f'mouse:{x},{y},0', 'wait:6', f'mouse:{x},{y},0', f'mouse:{x},{y},1',
                    'wait:8', f'mouse:{x},{y},0', 'wait:30']


def title(button):
    """From the title screen (just booted): JOUER (0) or LABO (1)."""
    POS[0] = None
    return click((12, 38)[button], 167) + ['wait:120']


def clicks(*points):
    return [s for p in points for s in click(*p)]


def button(name):
    return click(BUTTONS[name], 167)


MACHINE = ['--iie', '--mouse']         # --iic: the //c and its own mouse


def run(disk, steps):
    out = subprocess.run([str(a2test.A2SHOT)] + MACHINE + ['--disk', str(disk)]
                         + a2test.escape(steps), capture_output=True, text=True, timeout=300)
    if out.returncode:
        raise RuntimeError(out.stdout + out.stderr)
    return a2test.Result(out.stdout)


def half_adder_steps():
    """XOR in cell (0,0), AND in (0,1): S1 = E1 xor E2, S2 = E1 and E2."""
    return (clicks((PALETTE[XOR], 156), cell(0, 0))
            + clicks((PALETTE[AND], 156), (cell(0, 1)[0] + 10, cell(0, 1)[1] + 12))
            + clicks(term(0, 0), pin_in(0, 0, 9), term(1, 0), pin_in(0, 0, 16),
                     term(0, 0), pin_in(0, 1, 9), term(1, 0), pin_in(0, 1, 16),
                     pin_out(0, 0), term(0, 1), pin_out(0, 1), term(1, 1)))


def half_adder():
    b = Board()
    x = b.place(XOR, 0, 0)
    a = b.place(AND, 0, 1)
    for g in (x, a):
        b.connect(0, 8 + g * 4)
        b.connect(1, 8 + g * 4 + 1)
    b.connect(8 + x * 4, 0)
    b.connect(8 + a * 4, 1)
    return b


def idle(L, limit=200):
    """Peeks read through the current bank switches: take them in the main
    loop's frame wait, never in the middle of an aux-memory drawing."""
    return L.until('_a2_frame_wait', limit)


def state(L):
    return [idle(L), L.peek('_parts', 48), L.peek('_wires', 72), L.peek('_fl_count', 1),
            L.peek('_fl_kind', 64), L.peek('_fl_a', 64), L.peek('_fl_b', 64),
            L.peek('_fl_sinks', 8), L.peek('_values', 72)]


def decode(r, L, n):
    """The n-th state() snapshot (contiguous peeks merge into one dump)."""
    def m(name, length, offset=0):
        return r.mem(L[name] + offset, length, n)
    layout = m('_parts', 48) + m('_wires', 72)
    flat = m('_fl_count', 1) + m('_fl_kind', 64) + m('_fl_a', 64) + m('_fl_b', 64) \
        + m('_fl_sinks', 8)
    return layout, flat, m('_values', 72)


def check(name, got, want):
    if got != want:
        print(f'FAIL {name}\n  got  {got.hex()}\n  want {want.hex()}')
        return 1
    print(f'ok   {name}')
    return 0


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
    SHOTS.mkdir(parents=True, exist_ok=True)
    chips = [Chip() for _ in range(8)]
    board = half_adder()
    fails = 0

    # 1. Build it, set E1 = E2 = 1, one step: S1 = 0, S2 = 1.
    steps = [BOOT] + title(1) + half_adder_steps() + clicks(toggle(0), toggle(1)) + button('pas') \
        + state(L) + [f'shot:{SHOTS}/half_adder.png']
    # 2. Burn it into P3, clear the board, place P3, wire E1/E2 -> S1/S2.
    steps += button('grave') + click(chip_x(2), 156) + ['wait:60', idle(L, 3000),
                                                       L.peek('_persist', SAVE_SIZE),
                                                       L.peek('_saved_ok')]
    steps += button('efface') + button('efface') + clicks((chip_x(2), 156), cell(1, 1)) \
        + clicks(term(0, 0), pin_in(1, 1, 5), term(1, 0), pin_in(1, 1, 10),
                 pin_out(1, 1, 5), term(0, 1), pin_out(1, 1, 10), term(1, 1))
    # E1 and E2 are still 1: S1 = 0, S2 = 1; then E2 = 0: S1 = 1, S2 = 0.
    steps += button('pas') + state(L) + clicks(toggle(1)) + button('pas') + state(L) \
        + [f'shot:{SHOTS}/chip.png']
    r = run(args.disk, steps)

    layout, flat, values = decode(r, L, 0)
    fails += check('half adder layout', layout, layout_bytes(board))
    fails += check('half adder flat', flat, flat_bytes(compile_board(board, chips)))
    sim = Sim(compile_board(board, chips))
    sim.tick([1, 1, 0, 0, 0, 0, 0, 0])
    fails += check('half adder values', values, bytes(sim.values))
    fails += check('half adder outputs', bytes(sim.sinks()[:2]), bytes((0, 1)))

    chips[2] = burn(board, chips)
    # The whole save record: P3 burned, the lab board copied in by the save.
    fails += check('save record', r.mem(L['_persist'], SAVE_SIZE),
                   save_bytes(chips, lab=board))
    fails += check('saved to disk', r.mem(L['_saved_ok'], 1, 0), b'\x01')

    user = Board()
    c = user.place(CHIP0 + 2, 1, 1)
    user.connect(0, 8 + c * 4)
    user.connect(1, 8 + c * 4 + 1)
    user.connect(8 + c * 4, 0)
    user.connect(8 + c * 4 + 1, 1)
    sim = Sim(compile_board(user, chips))
    for n, inputs in enumerate(([1, 1], [1, 0])):
        sim.tick(inputs + [0] * 6)
        layout, flat, values = decode(r, L, 1 + n)
        fails += check(f'chip layout {n}', layout, layout_bytes(user))
        fails += check(f'chip flat {n}', flat, flat_bytes(compile_board(user, chips)))
        fails += check(f'chip values {n}', values, bytes(sim.values))
    fails += check('chip outputs', bytes(sim.sinks()[:2]), bytes((1, 0)))
    print(f'shots in {SHOTS}')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
