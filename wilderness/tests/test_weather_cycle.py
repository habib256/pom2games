#!/usr/bin/env python3
"""Original integer endpoints, three slopes and 24-hour temperature cycle."""
import json
import subprocess
import sys
from common import HERE, L, DISK, a2test, fp
from gendata import fp as encode
from test_thermal import call, poke

CASES = [(54, 32, 5.11618, 18.88382), (-20, 33, 8, 16),
         (0, 15, 6, 18), (90, 45, 4, 20), (12, 24, 10, 14),
         (60, 30, 2, 22)]


def probe_disk(out, module, driver, extras=()):
    out.mkdir(exist_ok=True)
    (out / 'state.bin').write_bytes((HERE / 'build/game.bin').read_bytes()[0x4000:0x5000])
    (out / 'module.bin').write_bytes(module)
    (out / 'driver.bin').write_bytes(driver)
    for name, data, addr in extras:
        (out / f'{name}.bin').write_bytes(data)
    lines = ['BLOAD STATE', 'BLOAD MODULE'] + [f'BLOAD {name}' for name, _, _ in extras] + ['BRUN DRIVER']
    (out / 'hello.bas').write_text(''.join(f'{10*(i+1)} PRINT CHR$(4);"{line}"\n' for i, line in enumerate(lines)))
    disk = out / 'probe.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'),
                    '--out', str(disk), '--bas', f'HELLO={out / "hello.bas"}',
                    '--bin', f'STATE={out / "state.bin"}@0x4000',
                    '--bin', f'MODULE={out / "module.bin"}@0x5800',
                    '--bin', f'DRIVER={out / "driver.bin"}@0x0800',
                    *[arg for name, _, addr in extras for arg in
                      ('--bin', f'{name}={out / (name+".bin")}@{addr:#x}')]],
                   check=True, capture_output=True)
    return disk


def native():
    out = HERE / 'build/re_weather_cycle'
    disk = probe_disk(out, (HERE / 'build/re_env/ch/t0Cs03.bin').read_bytes(),
                      bytes.fromhex('20 88 5C 4C 00 08'))
    steps = ['until:0800:20000']
    for mean, span, rise, setting in CASES:
        for addr, data in ((0x1C, bytes([mean & 255, span])), (0x4C66, encode(rise)),
                           (0x4C6B, encode(setting))):
            steps += [f'poke:{addr+i:04X}:{b:02X}' for i, b in enumerate(data)]
        steps += ['until:0803:1000', 'peek:4CB1:30', 'peek:4BB6:8', 'until:0800:1000']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    coefficients = [(r.mem(0x4CB1, 30, i), r.mem(0x4BB6, 8, i)) for i in range(len(CASES))]
    disk = probe_disk(out, (HERE / 'build/re_env/ch/t09s08.bin').read_bytes(),
                      bytes.fromhex('20 B9 58 4C 00 08'))
    steps = ['until:0800:20000', 'poke:00D4:00', 'poke:60A1:00', 'poke:4B91:F0', 'poke:4B9F:00']
    for mean_span, (slopes, offsets) in zip(CASES, coefficients):
        for addr, data in ((0x4CB1, slopes), (0x4BB6, offsets), (0x4C66, encode(mean_span[2])),
                           (0x4C61, encode(0)), (0x4CCF, encode(0))):
            steps += [f'poke:{addr+i:04X}:{b:02X}' for i, b in enumerate(data)]
        for hour in range(48):
            steps += [f'poke:{0x4C57+i:04X}:{b:02X}' for i, b in enumerate(encode(hour/2))]
            steps += ['until:0803:1000', 'peek:4B9B:1', 'until:0800:1000']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    temperatures = [r.mem(0x4B9B, 1, i)[0] for i in range(48*len(CASES))]
    (out / 'results.json').write_text(json.dumps(dict(cases=CASES, temperatures=temperatures), indent=2)+'\n')
    return coefficients, temperatures


def main():
    original = '--original' in sys.argv
    idle = L.until('idle', 20000)
    done = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle] + call(['env_hour']) + [done, idle] + call(['weather_cycle'])
    for mean, span, rise, setting in CASES:
        steps += poke('s_rise', rise) + poke('s_set', setting)
        steps += [L.poke('wc_min', mean-span//2), L.poke('wc_max', mean+span//2),
                  L.poke('wc_range', span), done, L.peek('wc_dawn', 30), idle]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    coefficients = [r.mem(L['wc_dawn'], 30, i) for i in range(len(CASES))]
    steps = [idle] + call(['env_hour']) + [done, idle] + call(['weather_evaluate'])
    for (mean, span, rise, _), values in zip(CASES, coefficients):
        steps += poke('s_rise', rise)
        steps += [L.poke('wc_min', mean-span//2), L.poke('wc_max', mean+span//2)]
        steps += [L.poke('wc_dawn', b, i) for i, b in enumerate(values)]
        for hour in range(48):
            steps += poke('s_hour', hour/2) + [done, L.peek('airtemp'), idle]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    temperatures = [r.mem(L['airtemp'], 1, i)[0] for i in range(48*len(CASES))]
    if original:
        native_coefficients, native_temperatures = native()
        assert coefficients == [c[0] for c in native_coefficients], [
            (case, a.hex(), b[0].hex()) for case, a, b in zip(CASES, coefficients, native_coefficients) if a != b[0]]
        assert temperatures == native_temperatures, [(i, a, b) for i, (a, b) in
            enumerate(zip(temperatures, native_temperatures)) if a != b]
        print('Six daily cycles and 288 hourly temperatures match original routines on ROM')
    else:
        for case, c in zip(CASES, coefficients):
            assert fp(c[5:10]) >= 14, (case, fp(c[5:10]))
            assert fp(c[15:20]) >= 0 and fp(c[20:25]) <= 0 and fp(c[25:30]) <= 0
        print('Six daily cycles: maximum at/after 14h; warming, evening and night slopes OK')


if __name__ == '__main__':
    main()
