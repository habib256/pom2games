#!/usr/bin/env python3
"""Run original Sierra fauna filters in the Apple II ROM, before random rolls.

Only the success endpoint at $5AA3 is replaced with a recorder. The original
filter and table accessor run unchanged. Private data/results stay in build/.
"""
import json, math, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tests'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test
from fauna_cases import cases
from gendata import fp as encode
from re_env_fp import mbf


def main():
    out = HERE / 'build/re_fauna'
    out.mkdir(exist_ok=True)
    state = bytearray((HERE / 'build/game.bin').read_bytes()[0x4000:0x8000])
    module = bytearray((HERE / 'build/re_env/ch/t0As00.bin').read_bytes())
    module[0x2A3:0x2AB] = bytes.fromhex('A5 FD 8D 00 09 4C 9A 5A')
    (out / 'state.bin').write_bytes(state)
    (out / 'module.bin').write_bytes(module)
    (out / 'driver.bin').write_bytes(bytes.fromhex('A2 01 A0 02 20 2F 5A 4C 00 08'))
    (out / 'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n'
        '20 PRINT CHR$(4);"BLOAD MODULE"\n30 PRINT CHR$(4);"BRUN DRIVER"\n')
    disk = out / 'probe.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'),
        '--out', str(disk), '--bas', f'HELLO={out / "hello.bas"}',
        '--bin', f'STATE={out / "state.bin"}@0x4000',
        '--bin', f'MODULE={out / "module.bin"}@0x5800',
        '--bin', f'DRIVER={out / "driver.bin"}@0x0800'], check=True, capture_output=True)
    fixtures = cases()
    steps = ['until:0800:20000', 'poke:000A:00', 'poke:4B75:00']
    for species, env, _ in fixtures:
        steps += [f'poke:0801:{species+1:02X}', f'poke:0803:{species+2:02X}', 'poke:0900:00']
        steps += [f'poke:{0x4ADA+i:04X}:{v:02X}' for i,v in enumerate(env)]
        steps += ['until:0807:1000','peek:0900:1','until:0800:1000']
    result = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    rows = []
    for (species, env, expected), data in zip(fixtures, result.dumps):
        got = bool(data[0])
        assert got == expected, (species, env, got, expected)
        rows.append(dict(species=species, environment=env, eligible=got))
    assert len(result.dumps) == len(fixtures)
    (out / 'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(f'{len(rows)} original fauna filter fixtures: OK')

    # A second instrumented copy records probability before the RND call.
    module = bytearray((HERE / 'build/re_env/ch/t0As00.bin').read_bytes())
    module[0x346:0x34E] = bytes.fromhex('A2 A0 A0 09 20 2B EB 60')
    (out / 'module.bin').write_bytes(module)
    (out / 'driver.bin').write_bytes(bytes.fromhex('20 A3 5A 4C 00 08'))
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'),
        '--out', str(disk), '--bas', f'HELLO={out / "hello.bas"}',
        '--bin', f'STATE={out / "state.bin"}@0x4000',
        '--bin', f'MODULE={out / "module.bin"}@0x5800',
        '--bin', f'DRIVER={out / "driver.bin"}@0x0800'], check=True, capture_output=True)
    steps = ['until:0800:20000']
    probabilities = []
    for species,rate in enumerate((80,40,100)):
        for level in (1,4,10):
            for frequency,minutes in ((0,60),(1,1),(1,60),(5,255),(100,255)):
                probabilities.append(minutes*frequency*math.sqrt(level)*rate*1e-5)
                steps += [f'poke:00FD:{species+1:02X}',f'poke:603F:{level:02X}',
                          f'poke:4BC6:{minutes:02X}','poke:4BC7:00']
                steps += [f'poke:{0x4C4D+i:04X}:{v:02X}' for i,v in enumerate(encode(frequency))]
                steps += ['until:0803:1000','peek:09A0:5','until:0800:1000']
    result = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    assert len(result.dumps)==len(probabilities)
    for expected,data in zip(probabilities,result.dumps):
        assert abs(mbf(data)-expected)<max(1e-8,expected*1e-8),(expected,mbf(data))
    (out / 'probabilities.json').write_text(json.dumps([mbf(d) for d in result.dumps],indent=2)+'\n')
    print('45 original encounter probability fixtures: OK')


if __name__ == '__main__': main()
