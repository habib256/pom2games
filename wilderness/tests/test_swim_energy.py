#!/usr/bin/env python3
"""Swimming effort, load truncation and calories; optional original ROM oracle."""
import argparse
import json
import math
import subprocess
import sys
from common import HERE, L, DISK, a2test, fp
from gendata import fp as encode
from test_thermal import call, poke


def original(cases):
    out = HERE / 'build/re_swim_energy'
    out.mkdir(exist_ok=True)
    (out / 'state.bin').write_bytes((HERE / 'build/game.bin').read_bytes()[0x4000:0x5000])
    # Execute the original helper unchanged. The private driver supplies its
    # coefficient pointer and returns to a breakpoint instead of dispatching DOS.
    module = (HERE / 'build/re_env/ch/t08s07.bin').read_bytes()
    (out / 'module.bin').write_bytes(module)
    (out / 'driver.bin').write_bytes(bytes.fromhex('A9 F6 A0 5C 20 3A 5D 4C 00 08'))
    (out / 'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n'
                                  '20 PRINT CHR$(4);"BLOAD MODULE"\n'
                                  '30 PRINT CHR$(4);"BRUN DRIVER"\n')
    disk = out / 'probe.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'),
                    '--out', str(disk), '--bas', f'HELLO={out / "hello.bas"}',
                    '--bin', f'STATE={out / "state.bin"}@0x4000',
                    '--bin', f'MODULE={out / "module.bin"}@0x5800',
                    '--bin', f'DRIVER={out / "driver.bin"}@0x0800'],
                   check=True, capture_output=True)
    steps = ['until:0800:20000']
    for body, ounces, *_ in cases:
        weight = body + ounces // 16  # original resident $50A1 shifts four times
        steps += [f'poke:4C02:{weight & 255:02X}', f'poke:4C03:{weight >> 8:02X}']
        steps += [f'poke:{0x4C20 + i:04X}:{b:02X}' for i, b in enumerate(encode(1.65))]
        steps += ['until:0807:1000', 'peek:4C20:5', 'until:0800:1000']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=1800)
    values = [r.mem(0x4C20, 5, k) for k in range(len(cases))]
    (out / 'results.json').write_text(json.dumps([
        dict(body=body, carried_ounces=oz, rate=fp(value))
        for (body, oz, *_), value in zip(cases, values)], indent=2) + '\n')
    energy = bytearray((HERE / 'build/re_surv/m098.bin').read_bytes())
    energy[0x27B] = 0x60  # return after the original energy branch, before DOS dispatch
    (out / 'energy.bin').write_bytes(energy)
    (out / 'energy-driver.bin').write_bytes(bytes.fromhex('20 22 58 4C 00 08'))
    energy_disk = out / 'energy.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'),
                    '--out', str(energy_disk), '--bas', f'HELLO={out / "hello.bas"}',
                    '--bin', f'STATE={out / "state.bin"}@0x4000',
                    '--bin', f'MODULE={out / "energy.bin"}@0x5800',
                    '--bin', f'DRIVER={out / "energy-driver.bin"}@0x0800'],
                   check=True, capture_output=True)
    steps = ['until:0800:20000']
    for (body, _, minutes, shiver), rate in zip(cases, values):
        for addr, data in ((0x4BF6, body.to_bytes(2, 'little')), (0x4C20, rate),
                           (0x4BC6, minutes.to_bytes(2, 'little')),
                           (0x4B87, bytes([int(shiver == 2)])),
                           (0x4BDA, (600).to_bytes(2, 'little'))):
            steps += [f'poke:{addr+i:04X}:{b:02X}' for i, b in enumerate(data)]
        steps += ['until:0803:1000', 'peek:4BDA:2', 'until:0800:1000']
    r = a2test.run(energy_disk, steps, emulator=a2test.A2SHOT, timeout=1800)
    spent = [int.from_bytes(r.mem(0x4BDA, 2, k), 'little') for k in range(len(cases))]
    (out / 'calories.json').write_text(json.dumps(spent) + '\n')
    return values, spent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--original', action='store_true', help='also run local original T08/S07')
    args = ap.parse_args()
    # Oz boundaries catch rounding instead of truncation; water changes catch
    # double counting the initially full canteen. Shivering is independent.
    cases = [(body, ounces, minutes, shiver)
             for body in (123, 165, 200)
             for ounces in (0, 15, 16, 17, 708, 762, 772, 836, 1535)
             for minutes, shiver in ((1, 0), (19, 2), (60, 0))]
    idle = L.until('idle', 20000)
    done = f'until:{L["idle"] + 3:04X}:6000'
    steps = [idle] + call(['spend_energy'])
    for body, ounces, minutes, shiver in cases:
        # load_used is already the native total carried ounces.
        for name, value in (('load_used', ounces), ('body_weight', body)):
            steps += [L.poke(name, value), L.poke(name, value >> 8, 1)]
        steps += [L.poke('it_place', 3, 64), L.poke('it_oz_lo', 80, 64),
                  L.poke('it_oz_hi', 0, 64), L.poke('verb', 24),
                  L.poke('act', 1), L.poke('thermal_mode', shiver)]
        steps += poke('s_step', minutes) + poke('s_spent', 600)
        steps += [done, L.peek('s_metabolic', 5), L.peek('s_spent', 5), idle]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=1800)
    rates, calories = [], []
    for k, (body, ounces, minutes, shiver) in enumerate(cases):
        rate = encode(fp(bytes.fromhex('7c75c28f5d')) * (body + ounces // 16) + fp(encode(1.65)))
        actual = r.mem(L['s_metabolic'], 5, k)
        assert actual == rate, (k, cases[k], fp(actual), fp(rate))
        effective = fp(encode(fp(rate) + (shiver == 2) * fp(encode(.04)) * body))
        assert fp(r.mem(L['s_spent'], 5, k)) == 600 + math.floor(minutes * effective), cases[k]
        rates.append(actual)
        calories.append(fp(r.mem(L['s_spent'], 5, k)))
    if args.original:
        native, native_calories = original(cases)
        assert rates == native, [(cases[k], fp(a), fp(b))
                                 for k, (a, b) in enumerate(zip(rates, native)) if a != b]
        assert calories == native_calories, [(cases[k], a, b)
            for k, (a, b) in enumerate(zip(calories, native_calories)) if a != b]
        print(f'{len(cases)} swimming rates match original ROM bytes exactly')
        print(f'{len(cases)} swimming calorie costs match original energy branch exactly')
    print(f'{len(cases)} swimming load, metabolic and integer calorie cases: OK')


if __name__ == '__main__':
    main()
