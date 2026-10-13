#!/usr/bin/env python3
"""Slow air-temperature variation, optionally compared with original T09/S08."""
import argparse
import json
import math
import subprocess
import sys
from common import HERE, L, DISK, a2test, fp
from gendata import fp as encode
from test_thermal import call, poke


def original(cases):
    out = HERE / 'build/re_temperature_wave'
    out.mkdir(exist_ok=True)
    (out / 'state.bin').write_bytes((HERE / 'build/game.bin').read_bytes()[0x4000:0x5000])
    module = bytearray((HERE / 'build/re_env/ch/t09s08.bin').read_bytes())
    # Stop after the original wave addition, before its visibility correction.
    module[0x1B1] = 0x60
    (out / 'module.bin').write_bytes(module)
    (out / 'driver.bin').write_bytes(bytes.fromhex('20 86 59 4C 00 08'))
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
    for elapsed, phase, air in cases:
        for addr, data in ((0x4C61, encode(elapsed)), (0x4CCF, encode(phase)),
                           (0x4B9B, bytes([air & 255]))):
            steps += [f'poke:{addr+i:04X}:{b:02X}' for i, b in enumerate(data)]
        steps += ['until:0803:1000', 'peek:4B9B:1', 'until:0800:1000']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    values = [r.mem(0x4B9B, 1, k)[0] for k in range(len(cases))]
    (out / 'results.json').write_text(json.dumps([
        dict(elapsed=h, phase=p, base_air=a, result=v)
        for (h, p, a), v in zip(cases, values)], indent=2) + '\n')
    return values


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--original', action='store_true')
    args = ap.parse_args()
    initial_phase = fp(bytes.fromhex('8272B261CF'))
    cases = [(h * 12, p, (-128, -120, 0, 42, 127)[h % 5])
             for p in (initial_phase, .2, 1, 2, 5) for h in range(81)]
    idle = L.until('idle', 20000)
    done = f'until:{L["idle"] + 3:04X}:6000'
    steps = [idle, L.peek('s_temp_phase', 5)] + call(['env_hour']) + [done, idle]
    steps += call(['temperature_wave'])
    for elapsed, phase, air in cases:
        steps += poke('s_elap', elapsed) + poke('s_temp_phase', phase)
        steps += [L.poke('airtemp', air), done, L.peek('airtemp'), idle]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    assert r.mem(L['s_temp_phase'], 5) == bytes.fromhex('8272B261CF')
    values = [r.mem(L['airtemp'], 1, k)[0] for k in range(len(cases))]
    frequency = fp(bytes.fromhex('7B1930BE0E'))
    expected = [(air + math.floor(5 * math.sin(fp(encode(h)) * frequency + fp(encode(p))))) & 255
                for h, p, air in cases]
    assert values == expected, [(c, a, b) for c, a, b in zip(cases, values, expected) if a != b]
    assert ((values[0] - cases[0][2]) & 255) == 252  # Initial correction is -4 F.
    if args.original:
        native = original(cases)
        assert values == native, [(c, a, b) for c, a, b in zip(cases, values, native) if a != b]
        print(f'{len(cases)} temperature-wave cases match original T09/S08 on ROM')
    else:
        print(f'{len(cases)} temperature-wave cases: phases, elapsed time, signed air and floor OK')


if __name__ == '__main__':
    main()
