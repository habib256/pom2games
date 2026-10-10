#!/usr/bin/env python3
"""Random key sequences on dist/WILDERNESS.dsk against a Python model.

The model applies each key to (x, y, heading) as src/wild.s should: turns
of 35 / 70 units modulo 560, a walk of one 8.8 step along the heading (or
back) only when it stays on the map. After every key it checks the position
and heading, the view (tools/view_ref.py, bit for bit, so the scrolled turns
too) and the status line under it. The DIVTAB filled at start-up is checked
entry by entry. Usage: test_keys.py [SEED] [KEYS]   or   test_keys.py --keys SEQUENCE
"""
from pathlib import Path
import random, sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test       # noqa: E402
import view_ref     # noqa: E402

L = a2test.labels(HERE / 'build/wild.lbl')
DISK = HERE.parent / 'dist/WILDERNESS.dsk'
MAP = (HERE / 'build/map.bin').read_bytes()
TURN = {'J': -35, 'K': 35, 'A': -70, 'Z': 70, '\\<': -35, '\\>': 35}
STATUS_ROW = 0x0400 + (21 % 8) * 128 + (21 // 8) * 40


def model(state, key):
    x, y, h = state
    if key in TURN:
        return x, y, (h + TURN[key]) % 560
    if key in ('I', 'M'):
        dx, dy = view_ref.direction(h)
        if key == 'M':
            dx, dy = -dx, -dy
        nx, ny = (x + dx) & 0xFFFF, (y + dy) & 0xFFFF
        if nx >> 8 < 112 and ny >> 8 < 84:
            return nx, ny, h
    return x, y, h


def status(state):
    x, y, h = state
    level = MAP[64 + (y >> 8) * 112 + (x >> 8)] & 0x7F
    return f'POS {2 * (x >> 8)},{2 * (y >> 8)}  HDG {h * 9 // 14}  ALT {MAP[10] + level}00 FT'


def divtab_ok(mem):
    bad = 0
    for n in range(2, 128):
        base = (n - 1) * n // 2 - 1
        for r in range(n):
            bad += mem[base + r] != (r * 256) // n
    return bad


def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--keys':
        keys = list(sys.argv[2])
        count = len(keys)
    else:
        seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 40
        rnd = random.Random(seed)
        # bias toward walking so the edges get reached
        keys = [rnd.choice('IIIIIMJKAZV') if rnd.random() < .9 else rnd.choice(('\\<', '\\>'))
                for _ in range(count)]
    steps = [L.until('idle', 4000), 'peek:4000:8128']
    for k in keys:
        steps += [f'key:{k}', 'wait:1', L.until('idle', 4000),
                  L.peek('px', 6), 'peek:2000:8192', f'peek:{STATUS_ROW:04X}:40']
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=3600)
    fails = 0
    bad = divtab_ok(r.dumps[0])
    if bad:
        print(f'  DIVTAB: {bad} wrong entries')
        fails += 1
    state = (MAP[2] | MAP[3] << 8, MAP[4] | MAP[5] << 8, MAP[6] | MAP[7] << 8)
    for i, k in enumerate(keys):
        state = model(state, k)
        regs, page, text = r.dumps[1 + 3 * i: 4 + 3 * i]
        got = tuple(int.from_bytes(regs[o:o + 2], 'little') for o in (0, 2, 4))
        problems = []
        if got != state:
            problems.append(f'state {got} != model {state}')
            state = got                  # follow the program to keep checking
        view = b''.join(page[a2test.hgr_offset(y):a2test.hgr_offset(y) + 40] for y in range(160))
        diff = sum(a != b for a, b in zip(view, view_ref.render(MAP, *state)))
        if diff:
            problems.append(f'{diff} view bytes differ')
        line = bytes(c & 0x7F for c in text).decode().rstrip()
        if line != status(state):
            problems.append(f'status {line!r} != {status(state)!r}')
        if problems:
            fails += 1
            print(f'  key {i} {k}: ' + '; '.join(problems))
    print(f'{count} keys, final {state}: ' + ('FAIL' if fails else 'OK'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
