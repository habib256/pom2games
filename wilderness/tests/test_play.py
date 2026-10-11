#!/usr/bin/env python3
"""Random commands on dist/WILDERNESS.dsk against a Python model of the player.

Commands: turns (LEFT / RIGHT on the empty line, LOOK L / R / B)
then LOOK N / E / S / W, and WALK h. The model walks like src/game.s:
one cell (an 8.8 step along the heading) after another, 19 minutes a cell
plus 6 per level climbed, stopping at the map edge, at water, or when the
hours asked for are spent. After every command it checks the position, the
heading and the view (tools/view_ref.py, bit for bit). Walks stay short so
the game remains in daylight. Usage: test_play.py [SEED] [COMMANDS]
"""
import random, sys
from common import terrain_boot, HERE, L, DISK, a2test, view_ref, view_rows, state

MAP = (HERE / 'build/map.bin').read_bytes()
GRID = MAP[64:]
TURNS = {'\\<': -35, '\\>': 35, 'LOOK L\\r': -70, 'LOOK R\\r': 70, 'LOOK B\\r': 280}
CARD = {'LOOK N\\r': 0, 'LOOK E\\r': 140, 'LOOK S\\r': 280, 'LOOK W\\r': 420}


MAG = int.from_bytes(MAP[24:25], 'little', signed=True)
CARD = {key: (heading + round(MAG*560/360)) % 560 for key, heading in CARD.items()}


def cell(x, y):
    return GRID[(y >> 8) * 112 + (x >> 8)]


def walk(st, hours):
    """New state after the requested duration or a refused next step."""
    x, y, h = st
    minutes = hours * 60
    dx, dy = view_ref.direction(h)
    while True:
        nx, ny = (x + dx) & 0xFFFF, (y + dy) & 0xFFFF
        if not (2 <= nx >> 8 < 110 and 2 <= ny >> 8 < 82):
            break
        c = cell(nx, ny)
        if c & 0x80:
            break
        d = (c & 0x7F) - (cell(x, y) & 0x7F)
        step = 19 + (6 * d if d > 0 else 0)
        if step > 255 or minutes < step:
            break
        minutes -= step
        x, y = nx, ny
    return (x, y, h)


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    rnd = random.Random(seed)
    st = (MAP[2] | MAP[3] << 8, MAP[4] | MAP[5] << 8, MAP[6] | MAP[7] << 8)
    steps, expect, walked = [L.until('game_start', 4000), L.poke('forest_enabled', 0), L.poke('sky_enabled', 0), L.poke('scenes_enabled', 0), L.until('idle', 4000)], [], 0
    for _ in range(count):
        r = rnd.random()
        if r < 0.45 and walked < 8:
            hours = rnd.choice((1, 1, 2))
            walked += hours
            st = walk(st, hours)
            cmd = ['key:WALK', 'press:\\r', L.until('number_idle', 6000), f'key:{hours}\\r']
            label = f'WALK {hours}'
        elif r < 0.6:
            k = rnd.choice(list(CARD))
            st = (st[0], st[1], CARD[k])
            cmd, label = [f'key:{k}'], k
        else:
            k = rnd.choice(list(TURNS))
            st = (st[0], st[1], (st[2] + TURNS[k]) % 560)
            cmd, label = [f'key:{k}'], k
        steps += cmd + ['wait:1', L.until('idle', 6000), L.peek('px', 6), 'peek:2000:8192']
        expect.append((label.replace('\\r', ''), st))
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=3600)
    fails = 0
    for i, (label, want) in enumerate(expect):
        got = state(r.dumps[2 * i])
        bad = sum(a != b for a, b in zip(view_rows(r.dumps[2 * i + 1]), view_ref.render(MAP, *got)))
        if got != want or bad:
            fails += 1
            print(f'  {i} {label}: state {got} model {want}, {bad} view bytes differ')
    print(f'{count} commands, final {st}: ' + ('FAIL' if fails else 'OK'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
