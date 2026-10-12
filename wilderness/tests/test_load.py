#!/usr/bin/env python3
"""Capacity boundaries, atomic refusals, containers and remaining quantities."""
import sys
from common import L, DISK, a2test, text_screen
from gendata import ITEMS, PLACE

FIELDS = ('it_place', 'it_pack_lo', 'it_pack_hi', 'it_gnd_lo', 'it_gnd_hi')
IDLE = L.until('idle', 6000)
INITIAL_WEIGHT = sum(pk if 22 <= i < 38 else oz
                     for i, name, place, oz, vol, gd, pk, kcal in ITEMS
                     if place is not None and place != 'GND')


def command(cmd):
    return [f'key:{cmd}\r', 'wait:1', IDLE]


def snapshot():
    return [L.peek(n, 76) for n in FIELDS] + [L.peek('load_used', 8), 'peek:0400:1024']


def limit(index, value):
    return [L.poke('load_limits', value, index * 2),
            L.poke('load_limits', value >> 8, index * 2 + 1)]


def usage(r, occurrence=0):
    b = r.mem(L['load_used'], 8, occurrence)
    return [int.from_bytes(b[k:k + 2], 'little') for k in range(0, 8, 2)]


def run(steps):
    return a2test.run(DISK, [L.until('idle', 20000)] + steps,
                      emulator=a2test.A2SHOT, timeout=1800)


def main():
    failures = []

    def check(name, ok):
        print(f'  {name}: {"OK" if ok else "FAIL"}')
        if not ok:
            failures.append(name)

    # Derive usage independently from item weights/volumes and initial places.
    initial = [INITIAL_WEIGHT, 0, 0, 0]
    for i, name, place, oz, vol, gd, pk, kcal in ITEMS:
        if place is None or place == 'GND':
            continue
        if 22 <= i < 38:
            destination = PLACE[ITEMS[63][2]] if i == 22 else 2
            initial[destination] += pk * vol
        else:
            initial[PLACE[place]] += vol
    r = run(snapshot())
    check('initial usage matches independent model', usage(r) == initial)
    check('initial weight includes all carried and worn equipment', initial[0] == 836)

    # Exact boundary succeeds; one extra ounce is refused without any mutation.
    r = run(limit(0, INITIAL_WEIGHT + 2) + command('CARRY HAT') + snapshot()
            + command('GET SUNSCREEN') + snapshot())
    check('weight at exact limit accepted', r.mem(L['it_place'], 76)[19] == 3
          and usage(r)[0] == INITIAL_WEIGHT + 2)
    check('overweight transfer is atomic', all(r.mem(L[n], 76) == r.mem(L[n], 76, 1) for n in FIELDS))
    check('refusal keeps cached usage correct', usage(r) == usage(r, 1))
    check('capacity refusal has useful message', 'TRANSFER REFUSED: WEIGHT' in
          '\n'.join(text_screen(r.mem(0x400, 1024, 1))))

    # Independently constrain each destination while allowing all the others.
    for idx, cmd, item, volume in ((1, 'WEAR PARKA', 2, 180),
                                   (2, 'PACK HAT', 19, 35),
                                   (3, 'CARRY HAT', 19, 35)):
        r = run(limit(idx, initial[idx] + volume - 1) + snapshot() + command(cmd) + snapshot())
        check(f'{cmd}: volume refusal preserves every item field',
              all(r.mem(L[n], 76) == r.mem(L[n], 76, 1) for n in FIELDS))
        r = run(limit(idx, initial[idx] + volume) + command(cmd) + snapshot())
        check(f'{cmd}: exact volume accepted', usage(r)[idx] == initial[idx] + volume)

    # Food must use carried ounces, not the item's total ground + pack ounces.
    r = run(limit(0, INITIAL_WEIGHT + 48) + command('GET APPLES') + snapshot())
    check('food pickup adds ounces and per-ounce volume', usage(r)[0] == initial[0] + 48
          and usage(r)[2] == initial[2] + 96)
    r = run(snapshot() + command('GET APPLES') + snapshot())
    check('default overloaded food pickup preserves pack and ground stock',
          all(r.mem(L[n], 76) == r.mem(L[n], 76, 1) for n in FIELDS))
    r = run(command('DROP AXE') + command('GET APPLES') + snapshot())
    check('dropping equipment frees weight and pack space', usage(r)[0] == initial[0] - 32 + 48
          and usage(r)[2] == initial[2] - 52 + 96)

    r = run(command('PACK CANTEEN') + snapshot() + command('CARRY CANTEEN') + snapshot())
    check('moving the canteen moves its water volume too',
          usage(r) == [initial[0], initial[1], initial[2] + 272, initial[3] - 272]
          and usage(r, 1) == initial)

    steps = ['key:EAT CHEESE', 'press:\r', L.until('number_idle', 6000), 'key:8\r', 'wait:1', IDLE,
             'key:DRINK WATER', 'press:\r', L.until('number_idle', 6000), 'key:10\r', 'wait:1', IDLE] + snapshot()
    r = run(steps)
    check('meals and drinks release weight and container volume',
          usage(r) == [initial[0] - 18, initial[1], initial[2] - 16, initial[3] - 20])

    # No wrapping a >65535-ounce transfer or its volume into a valid load.
    r = run([L.poke('it_gnd_lo', 255, 37), L.poke('it_gnd_hi', 255, 37)] + snapshot()
            + command('GET APPLES') + snapshot())
    check('quantity addition overflow rolls back all fields',
          all(r.mem(L[n], 76) == r.mem(L[n], 76, 1) for n in FIELDS))
    r = run([L.poke('it_gnd_lo', 255, 37), L.poke('it_gnd_hi', 255, 37)] + snapshot()
            + command('DROP APPLES') + snapshot())
    check('ground stock addition overflow rolls back all fields',
          all(r.mem(L[n], 76) == r.mem(L[n], 76, 1) for n in FIELDS))
    r = run([L.poke('it_gnd_lo', 0, 37), L.poke('it_gnd_hi', 128, 37)] + snapshot()
            + command('GET APPLES') + snapshot())
    check('16-bit volume/weight overflow cannot bypass limits',
          all(r.mem(L[n], 76) == r.mem(L[n], 76, 1) for n in FIELDS))

    for cmd in ('DROP BACKPACK', 'PACK BACKPACK', 'DROP CANTEEN'):
        r = run(snapshot() + command(cmd) + snapshot())
        check(f'{cmd}: container refusal is atomic',
              all(r.mem(L[n], 76) == r.mem(L[n], 76, 1) for n in FIELDS))

    # Empty a backpack/canteen, then verify pickups require the container.
    steps = []
    for i, name, place, oz, vol, gd, pk, kcal in ITEMS:
        if place not in ('PACK', 'BOTH') and not (22 <= i < 38 and pk):
            continue
        # Existing vocabulary aliases are handled explicitly where needed.
        names = {2: 'PARKA', 12: 'RAINCOAT', 42: 'SNAKEBITE KIT', 47: 'FLAGYL',
                 53: 'COMPASS', 55: 'ALTIMETER', 66: 'FLASHLIGHT', 67: 'GEAR',
                 69: 'THERMOMETER', 73: 'UTENSILS'}
        noun = names.get(i, name)
        steps += command(f'DROP {noun}')
    steps += command('DROP BACKPACK') + command('DROP CANTEEN') + snapshot()
    steps += command('GET AXE') + snapshot()
    steps += command('GET WATER') + snapshot()
    steps += command('CARRY BACKPACK') + command('GET AXE') + snapshot()
    steps += command('CARRY CANTEEN') + command('GET WATER') + snapshot()
    r = run(steps)
    check('empty containers can be dropped', r.mem(L['it_place'], 76)[21] == 0
          and r.mem(L['it_place'], 76)[64] == 0)
    check('no backpack: PACK/GET refused', r.mem(L['it_place'], 76, 1)[58] == 0)
    check('no canteen: water pickup refused', r.mem(L['it_pack_lo'], 76, 2)[22] == 0)
    check('backpack recovered: packing resumes', r.mem(L['it_place'], 76, 3)[58] == 2)
    check('canteen recovered: water pickup resumes', r.mem(L['it_pack_lo'], 76, 4)[22] == 128)

    water_only = []
    for step in steps[:steps.index('key:DROP BACKPACK\r')]:
        if step != 'key:DROP WATER\r':
            water_only.append(step)
    r = run(water_only + command('DROP BACKPACK') + snapshot())
    check('water in a carried canteen does not occupy the backpack',
          r.mem(L['it_place'], 76)[21] == 0 and r.mem(L['it_pack_lo'], 76)[22] == 64)

    # Every inventory group keeps the same four remaining capacities visible.
    steps = ['key:INVENTORY\r', 'wait:1', L.until('wait_key')]
    for group in '12345':
        steps += [f'key:{group}', 'wait:1', L.until('wait_key'), 'peek:0400:1024']
    r = run(steps)
    expected = ('FREE WEIGHT 43 OZ', 'FREE WEAR VOL 1525 IN3',
                'FREE PACK VOL 4134 IN3', 'FREE HAND VOL 2542 IN3')
    check('inventory displays all four remaining capacities in every group', all(
          tuple(' '.join(row.split()) for row in text_screen(page)[2:6]) == expected
          for page in r.dumps))
    print(f'{len(failures)} failures')
    sys.exit(bool(failures))


if __name__ == '__main__':
    main()
