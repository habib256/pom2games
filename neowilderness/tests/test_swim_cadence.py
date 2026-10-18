#!/usr/bin/env python3
"""Normal swimming durations against original preparation and step ROM code."""
import argparse
import json
import subprocess
import sys
import tempfile
from common import HERE, L, DISK, a2test, fp, disk_with, state
from gendata import fp as encode
from test_thermal import call, poke

CASES = [(body, ounces, health, diagonal)
         for body in (123, 165, 200)
         for ounces in (0, 15, 16, 708, 772, 1535)
         for health in (.3, 1., 4., 7.866609670221806)
         for diagonal in (0, 1)
         # The current spend interface supports 1..255-minute steps.
         if not (body == 123 and ounces == 1535 and health == .3 and diagonal)]


def writes(addr, data):
    return [f'poke:{addr+i:04X}:{v:02X}' for i, v in enumerate(data)]


def native():
    out = HERE / 'build/re_swim_cadence'
    out.mkdir(exist_ok=True)
    (out / 'state.bin').write_bytes((HERE / 'build/game.bin').read_bytes()[0x4000:0x5000])
    hello = out / 'hello.bas'
    hello.write_text('10 PRINT CHR$(4);"BLOAD STATE"\n'
                     '20 PRINT CHR$(4);"BLOAD MODULE"\n'
                     '30 PRINT CHR$(4);"BRUN DRIVER"\n')

    def disk(name, module, entry, return_at):
        data = bytearray((HERE / module).read_bytes())
        data[return_at-0x5800] = 0x60  # omit disk dispatch after the measured calculation
        (out / f'{name}.bin').write_bytes(data)
        (out / f'{name}-driver.bin').write_bytes(bytes((0x20, entry & 255, entry >> 8, 0x4C, 0, 8)))
        d = out / f'{name}.dsk'
        subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'),
                        '--out', str(d), '--bas', f'HELLO={hello}',
                        '--bin', f'STATE={out / "state.bin"}@0x4000',
                        '--bin', f'MODULE={out / (name+".bin")}@0x5800',
                        '--bin', f'DRIVER={out / (name+"-driver.bin")}@0x0800'],
                       check=True, capture_output=True)
        return d

    d = disk('prepare', 'build/re_env/ch/t08s07.bin', 0x5B51, 0x5BC7)
    steps = ['until:0800:20000']
    for body, oz, _, _ in CASES:
        steps += writes(0x4BF6, body.to_bytes(2, 'little'))
        steps += writes(0x4C02, (body+oz//16).to_bytes(2, 'little'))
        steps += writes(0x4BBE, (2).to_bytes(2, 'little'))
        steps += writes(0x5CCE, encode(1)) + writes(0x4C7F, encode(1))
        steps += ['until:0803:1000', 'peek:4CD4:5', 'until:0800:1000']
    r = a2test.run(d, steps, emulator=a2test.A2SHOT, timeout=1800)
    factors = [r.mem(0x4CD4, 5, k) for k in range(len(CASES))]
    d = disk('duration', 'build/re_env/ch/t09s00.bin', 0x5909, 0x59CF)
    steps = ['until:0800:20000']
    for (_, _, health, diagonal), factor in zip(CASES, factors):
        steps += writes(0x4CD4, factor) + writes(0x4C34, encode(health))
        steps += writes(0x4B49, bytes([1])) + writes(0x4B4C, bytes([0]))
        steps += writes(0x4BAD, bytes([0])) + writes(0x1D, bytes([diagonal]))
        steps += ['until:0803:1000', 'peek:4BCA:2', 'until:0800:1000']
    r = a2test.run(d, steps, emulator=a2test.A2SHOT, timeout=1800)
    durations = [int.from_bytes(r.mem(0x4BCA, 2, k), 'little') for k in range(len(CASES))]
    (out / 'results.json').write_text(json.dumps([
        dict(body=body, ounces=oz, health=h, diagonal=diag,
             prepared_factor=fp(factor), minutes=dt)
        for (body, oz, h, diag), factor, dt in zip(CASES, factors, durations)], indent=2)+'\n')
    return durations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', action='store_true')
    args = parser.parse_args()
    idle = L.until('idle', 20000)
    end = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle] + call(['swim_step'])
    for body, oz, health, diagonal in CASES:
        for name, value in (('body_weight', body), ('load_used', oz), ('wdx', 128),
                            ('wdy', 128 if diagonal else 0)):
            steps += [L.poke(name, value), L.poke(name, value >> 8, 1)]
        steps += [L.poke('it_place', 3, 64), L.poke('it_oz_lo', 80, 64), L.poke('it_oz_hi', 0, 64)]
        steps += poke('s_health', health) + [end, L.peek('stepmin'), idle]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=1800)
    actual = [r.mem(L['stepmin'], 1, k)[0] for k in range(len(CASES))]
    # Independent sanity calculation; original execution supplies the oracle
    # when requested. All cases fit the current byte-duration spend interface.
    import math
    expected = [math.floor(.5+( .567 if diag else .4)*5*180*(body+oz//16+2)/body/(6*math.sqrt(h)))
                for body, oz, h, diag in CASES]
    assert actual == expected, [(c, a, b) for c, a, b in zip(CASES, actual, expected) if a != b]
    if args.original:
        oracle = native()
        assert actual == oracle, [(c, a, b) for c, a, b in zip(CASES, actual, oracle) if a != b]
        print(f'{len(CASES)} swimming durations match original ROM preparation and steps: OK')
    else:
        print(f'{len(CASES)} health/load/diagonal swimming durations: OK')

    # Real command: after a first 39-minute step at H=4 the health update
    # returns near Hmax. Its second 28-minute step cannot fit the remaining
    # 21-minute budget. Keep native step costs without overshooting 60.
    m = bytearray((HERE / 'build/map.bin').read_bytes())
    m[2:8] = (10 << 8).to_bytes(2, 'little') * 2 + (140).to_bytes(2, 'little')
    m[8:10] = bytes((80, 70))
    m[10] = 0
    m[13:16] = bytes((60, 60, 0))
    m[64:] = bytes([128]) * 9408
    with tempfile.TemporaryDirectory() as tmp:
        d = disk_with(tmp, m)
        steps = [L.until('game_start', 20000), L.poke('scenes_enabled', 0), idle]
        steps += poke('s_health', 4)
        steps += ['key:SWIM\r', L.until('number_idle', 6000), 'key:1\r',
                  'wait:1', L.until('idle', 20000), L.peek('px', 6), L.peek('s_elap', 5)]
        r = a2test.run(d, steps, emulator=a2test.A2SHOT, timeout=1800)
        assert state(r.mem(L['px'], 6)) == ((10 << 8)+128, 10 << 8, 140)
        assert abs(fp(r.mem(L['s_elap'], 5)) * 60 - 39) < 1e-5
    print('SWIM 1: native first step spends 39 minutes without exceeding 60: OK')


if __name__ == '__main__':
    main()
