#!/usr/bin/env python3
"""The simulation and the STATUS screen of src/game.s.

- REST 3: hour 7 -> 10, 3 hours elapsed, date + 180/525600, STATUS shows
  MAY6, 10:00A and GOAL = floor(100 e^(-2.5 x 3 / D0)) (no move: v = 0).
- EAT CHEESE 8 (from the pack), DRINK WATER 10, GET APPLES: ounces, place,
  and the FOOD / WATER totals of STATUS.
- REST 200 without supplies: port stress test, death near the exhaustion
  tolerance after the initial rest credit is clamped. This exceeds the
  original's accepted command duration and does not prove native parity.
The floats are read from RAM and decoded (tests/common.fp).
Synthetic maps also exercise climbing time overflow, travel at night and
arrival at the ranger outpost.
"""
import math, re, sys, tempfile
from common import HERE, L, DISK, a2test, disk_with, fp, state, text_screen, view_rows

MAP = (HERE / 'build/map.bin').read_bytes()
fails = 0


def check(name, ok, detail=''):
    global fails
    print(f'  {name:42} {"ok" if ok else "FAIL " + str(detail)}')
    fails += not ok


def floats(r, name, occurrence=0):
    return fp(r.mem(L[name], 5, occurrence))


def travel_limits():
    """Reject unrepresentable climbs and travel begun after sunset."""
    mapbin = bytearray(MAP[:64]) + bytearray(112 * 84)
    mapbin[2:8] = bytes((0, 10, 0, 10, 140, 0))  # east on flat, dry ground
    idle = L.until('idle', 20000)
    with tempfile.TemporaryDirectory() as tmp:
        for climb in (6, 40, 86, 125):
            mapbin[64 + 10 * 112 + 11] = climb
            disk = disk_with(tmp, mapbin)
            r = a2test.run(disk, [idle, 'key:WALK', 'press:\r', L.until('number_idle', 6000), 'key:1\r',
                                 'wait:400', L.peek('px', 6), L.peek('s_elap', 5)],
                           emulator=a2test.A2SHOT)
            want = (11 if climb == 6 else 10) << 8
            check(f'WALK 1: climb {climb}, correct position',
                  state(r.mem(L['px'], 6)) == (want, 10 << 8, 140))
            check(f'WALK 1: climb {climb}, correct time',
                  abs(floats(r, 's_elap') - (55 / 60 if climb == 6 else 0)) < 1e-6)
        mapbin[64 + 10 * 112 + 11] = 0
        disk = disk_with(tmp, mapbin)
        r = a2test.run(disk, [idle, L.poke('nature_frequency',0), 'key:REST', 'press:\r', L.until('number_idle', 6000), 'key:16\r',
                             'wait:400', idle,
                             L.peek('s_elap', 5), 'key:WALK\r',
                             'wait:400', L.peek('px', 6), L.peek('s_elap', 5),
                             'peek:0400:1024', 'peek:2000:8192'],
                       emulator=a2test.A2SHOT)
        check('WALK at night: position unchanged',
              state(r.mem(L['px'], 6)) == (10 << 8, 10 << 8, 140))
        check('WALK at night: no time spent',
              floats(r, 's_elap', 1) == floats(r, 's_elap'))
        check('WALK at night: dark travel message',
              'TOO DARK TO TRAVEL' in '\n'.join(text_screen(r.mem(0x400, 1024))))
        check('Night view: black', not any(view_rows(r.mem(0x2000, 8192))))
        mapbin[8:10] = bytes((12, 10))  # first eastward step reaches the outpost
        disk = disk_with(tmp, mapbin)
        r = a2test.run(disk, [idle, 'key:WALK', 'press:\r', L.until('number_idle', 6000), 'key:1\r',
                             'wait:400', L.until('wait_key'),
                             L.peek('won'), L.peek('dead'), L.peek('px', 6),
                             'peek:0400:1024'], emulator=a2test.A2SHOT)
        check('Arrival: victory and player alive',
              r.mem(L['won'], 1) == b'\x01' and r.mem(L['dead'], 1) == b'\x00')
        check('Arrival: travel stops near the outpost',
              state(r.mem(L['px'], 6)) == (11 << 8, 10 << 8, 140))
        check('Arrival: victory message',
              'YOU SURVIVED' in '\n'.join(text_screen(r.mem(0x400, 1024))))


def main():
    idle = L.until('idle', 20000)
    snap = [L.peek(n, 5) for n in ('s_hour', 's_elap', 's_date', 's_defw', 's_health')]
    status = ['key:STATUS\\r', L.until('wait_key', 6000), 'peek:0400:1024', 'key: ', 'wait:2', idle]
    steps = [idle, L.poke('nature_frequency',0), 'key:REST', 'press:\\r', L.until('number_idle', 6000), 'key:3\\r', idle] + snap + status
    steps += ['key:EAT CHEESE', 'press:\\r', L.until('number_idle', 6000), 'key:8\\r', idle,
              'key:DRINK WATER', 'press:\\r', L.until('number_idle', 6000), 'key:10\\r', idle,
              'key:GET APPLES\\r', 'wait:1', idle,
              L.peek('it_pack_lo', 76), L.peek('it_pack_hi', 76), L.peek('it_place', 76)] + status
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=1800)

    hour, elap, date = floats(r, 's_hour'), floats(r, 's_elap'), floats(r, 's_date')
    check('REST 3: hour 10', abs(hour - 10) < 1e-6, hour)
    check('REST 3: 3 hours elapsed', abs(elap - 3) < 1e-6, elap)
    check('REST 3: date + 180 / 525600', abs(date - (0.3444240 + 180 / 525600)) < 1e-6, date)
    screen = '\n'.join(text_screen(r.mem(0x400, 1024)))
    sx, sy = (MAP[3] * 2 + MAP[2] / 128), (MAP[5] * 2 + MAP[4] / 128)
    gx, gy = MAP[8] * 2, MAP[9] * 2
    d0 = math.hypot(gx - 2 * MAP[3], gy - 2 * MAP[5])
    goal = int(100 * math.exp(-2.5 * 3 / d0))
    check('STATUS: DATE MAY6, TIME 10:00A', 'DATE MAY6' in screen and 'TIME 10:00A' in screen, screen[:200])
    got = re.search(r'GOAL=(\d+)%', screen)
    check(f'STATUS: GOAL={goal}%', got and abs(int(got.group(1)) - goal) <= 1, got and got.group(1))
    check('STATUS: HEALTH=98% (original integer conditions)', 'HEALTH=98%' in screen)

    lo, hi, places = (r.mem(L[n], 76) for n in ('it_pack_lo', 'it_pack_hi', 'it_place'))
    pack = lambda i: lo[i] | hi[i] << 8
    place = lambda i: places[i]
    check('EAT CHEESE 8: pack 32 -> 24', pack(28) == 24, pack(28))
    check('DRINK WATER 10: canteen 64 -> 54', pack(22) == 54, pack(22))
    check('GET APPLES: 32 + 48 in the pack', pack(37) == 80 and place(37) == 2, (pack(37), place(37)))
    screen = '\n'.join(text_screen(r.mem(0x400, 1024, 1)))
    check('STATUS: FOOD 432 OZ, WATER 118 OZ', 'FOOD 432 OZ' in screen and 'WATER 118 OZ' in screen,
          re.findall(r'(FOOD \d+ OZ|WATER \d+ OZ)', screen))

    r = a2test.run(DISK, [idle, L.poke('nature_frequency',0), 'key:REST', 'press:\\r', L.until('number_idle', 6000), 'key:200\\r', L.until('wait_key', 180000),
                          L.peek('dead', 1), L.peek('s_defw', 5), L.peek('s_elap', 5), 'peek:0400:1024'],
                   emulator=a2test.A2SHOT, timeout=1800)
    dead, defw, elap = r.mem(L['dead'], 1)[0], floats(r, 's_defw'), floats(r, 's_elap')
    check('REST 200 without water: dead', dead == 1, dead)
    check('  deficits cause death before requested 200 hours', 0 < defw <= elap < 200, (defw,elap))
    lines = text_screen(r.mem(0x400, 1024))
    check('  the death message, not the rest one', any('NOT SURVIVE' in l for l in lines), lines[21:23])
    travel_limits()
    print('FAIL' if fails else 'OK')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
