#!/usr/bin/env python3
"""Random commands: native raster displacement, headings and exact HGR.

The completed half-step counter selects the path length; an independent
sine raster computes its coordinates. Pace and elapsed time are covered by
test_walk.py. Usage: test_play.py [SEED] [COMMANDS]
"""
import math, random, sys
from common import terrain_boot, HERE, L, DISK, a2test, view_ref, view_rows, state

MAP = (HERE / 'build/map.bin').read_bytes()
GRID = MAP[64:]
TURNS = {'\\<': -35, '\\>': 35, 'LOOK L\\r': -70, 'LOOK R\\r': 70, 'LOOK B\\r': 280}
CARD = {'LOOK N\\r': 0, 'LOOK E\\r': 140, 'LOOK S\\r': 280, 'LOOK W\\r': 420}


MAG = int.from_bytes(MAP[24:25], 'little', signed=True)
CARD = {key: (heading + round(MAG*560/360)) % 560 for key, heading in CARD.items()}


def cell(x, y):
    return GRID[(y >> 8) * 112 + (x >> 8)]


def walk(st, halfsteps):
    x,y,h=st
    angle=(90-math.floor(h*360/560+.5))%360
    axis=int(46<=angle<135 or 226<=angle<315)
    sign=-1 if 135<=angle<315 else 1
    delta=math.sin(math.pi/2-math.radians(angle) if axis else math.radians(angle))
    coords=[x//128,y//128]
    minor=coords[1-axis]
    for _ in range(halfsteps):
        coords[axis]+=sign
        minor+=delta
        coords[1-axis]=math.floor(minor+.5)
        assert 2<=coords[0]/2<110 and 2<=coords[1]/2<82
        assert not cell(coords[0]*128,coords[1]*128)&128
    return coords[0]*128,coords[1]*128,h


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
        steps += cmd + ['wait:1', L.until('idle', 6000), L.peek('px', 6),
                        'peek:2000:8192',L.peek('journey_halfcells',2)]
        expect.append((label.replace('\\r', ''), st))
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=3600)
    fails = 0
    previous=(MAP[2] | MAP[3]<<8,MAP[4] | MAP[5]<<8,MAP[6] | MAP[7]<<8)
    completed=0
    for i, (label, want) in enumerate(expect):
        got = state(r.dumps[3 * i])
        total=int.from_bytes(r.dumps[3*i+2],'little')
        base=(previous[0],previous[1],want[2])
        if label.startswith('WALK'):
            want=walk(base,total-completed)
        else:
            assert total==completed,'turn spent a travel step'
            want=base
        completed=total
        previous=got
        bad = sum(a != b for a, b in zip(view_rows(r.dumps[3 * i + 1]), view_ref.render(MAP, *got)))
        if got != want or bad:
            fails += 1
            print(f'  {i} {label}: state {got} model {want}, {bad} view bytes differ')
    print(f'{count} commands, final {previous}: ' + ('FAIL' if fails else 'OK'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
