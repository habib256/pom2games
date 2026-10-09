#!/usr/bin/env python3
"""Compare native Q4 arithmetic to a reference at wall and aiming boundaries."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
import a2test

ROOT = Path(__file__).resolve().parents[2]
L = a2test.labels(ROOT / 'light3dball/build/game.lbl', strip=True)
DISK = ROOT / 'dist/LIGHT3DBALL.dsk'


def absolute(op, address):
    return [op, address & 255, address >> 8]


def poke(address, values):
    return [f'poke:{address+i:04X}:{value:02X}' for i, value in enumerate(values)]


def word(value):
    return list((value & 65535).to_bytes(2, 'little'))


def fixture(body):
    program = body + absolute(0x20, L['frame_mark']) + absolute(0x4C, 0x0400)
    return ['wait:1100', L.until('physics')] + poke(0x0400, program) + \
        poke(L['physics'], absolute(0x4C, 0x0400))


def reference(position, velocity):
    result = position+velocity
    if result < 32:
        return 64-result, -velocity, 1
    if result > 2000:
        return 4000-result, -velocity, 1
    return result, velocity, 0


positions = list(range(32, 49)) + [255, 256, 257, 1023, 1024] + list(range(1984, 2001))
cases = [(position, velocity) for position in positions for velocity in range(-8, 9)]
costs = []
for start in range(0, len(cases), 160):
    batch = cases[start:start+160]
    steps = fixture(absolute(0x20, L['step_xy']))
    for position, velocity in batch:
        for name, value in [('ball_x', position), ('vel_x', velocity),
                            ('ball_y', 2032-position), ('vel_y', -velocity)]:
            steps += poke(L[name], word(value))
        steps += [L.poke('wall_hits', 0), L.until('step_xy'), L.until('frame_mark')]
        steps += [L.peek(name, 2) for name in ('ball_x', 'ball_y', 'vel_x', 'vel_y')]
        steps += [L.peek('wall_hits')]
    r = a2test.run(DISK, steps)
    for index, (position, velocity) in enumerate(batch):
        x, vx, xhit = reference(position, velocity)
        y, vy, yhit = reference(2032-position, -velocity)
        for name, wanted in [('ball_x', x), ('ball_y', y), ('vel_x', vx), ('vel_y', vy)]:
            assert r.mem(L[name], 2, index) == bytes(word(wanted)), (name, position, velocity)
        assert r.mem(L['wall_hits'], 1, index) == bytes([xhit+yhit])
    costs += [r.cycles[i+1]-r.cycles[i] for i in range(1, len(r.cycles), 2)]
assert max(costs) < 600, ('native XY cycle budget', max(costs))

body = absolute(0xAD, 0x0700) + absolute(0xAE, 0x0701) + absolute(0x20, L['aim_bias'])
body += absolute(0x8D, 0x0702) + absolute(0x8E, 0x0703)
steps = fixture(body)
for offset in range(-312, 313):
    steps += poke(0x0700, word(offset)) + [L.until('aim_bias'), L.until('frame_mark'), 'peek:0702:2']
r = a2test.run(DISK, steps)
for index, offset in enumerate(range(-312, 313)):
    expected = abs(offset)//32 * (-1 if offset < 0 else 1)
    assert r.mem(0x0702, 2, index) == bytes(word(expected)), ('aiming symmetry', offset)
contacts = []
for px in (8, 16, 40, 64, 88, 112, 120):
    for py in (12, 24, 48, 64, 80, 104, 116):
        rx, ry = 256+abs(px-64), 240+abs(py-64)
        offsets = [(dx, 0) for dx in (-rx-1, -rx, -256, -255, 255, 256, rx, rx+1)]
        offsets += [(0, dy) for dy in (-ry-1, -ry, -256, -255, -240, 240, 255, 256, ry, ry+1)]
        offsets += [(dx, dy) for dx in (-rx, rx) for dy in (-ry, ry)]
        for dx, dy in offsets:
            bx, by = px*16+dx, py*16+dy
            if 32 <= bx <= 2000 and 32 <= by <= 2000:
                contacts.append((px, py, bx, by, abs(dx) <= rx and abs(dy) <= ry))
body = absolute(0x20, L['paddle_contact']) + absolute(0x8D, 0x0702) + absolute(0x8E, 0x0703)
for start in range(0, len(contacts), 160):
    batch = contacts[start:start+160]
    steps = fixture(body)
    for px, py, bx, by, hit in batch:
        steps += [L.poke('paddle_x', px), L.poke('paddle_y', py)]
        steps += poke(L['ball_x'], word(bx)) + poke(L['ball_y'], word(by))
        steps += [L.until('paddle_contact'), L.until('frame_mark'), 'peek:0702:2']
    r = a2test.run(DISK, steps)
    for index, (px, py, bx, by, hit) in enumerate(batch):
        assert r.mem(0x0702, 2, index) == bytes([int(hit), 0]), \
            ('perspective contact boundary', px, py, bx, by, hit)
print(f'LIGHT3DBALL native physics: {len(cases)} XY boundary cases, 625 aiming offsets, '
      f'{len(contacts)} perspective contacts; '
      f'{min(costs)}–{max(costs)} cycles per XY substep.')
