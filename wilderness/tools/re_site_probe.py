#!/usr/bin/env python3
"""Probe original SHELTER transitions and its effective-temperature branch.

Needs local build/game.bin, JOURNEY.dsk and re_surv/m0B2.bin. Only the
message endpoint and the exits of the isolated thermal branch are stubbed.
Original data and generated disks stay in ignored build/re_sites/.
"""
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
import a2test  # noqa: E402
HERE = a2test.game_dir(Path(__file__).resolve().parents[1], __doc__)  # --game DIR
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test, smalldos


poke = a2test.pokes


def disk(out, name, module, entry):
    state = bytearray((HERE / 'build/game.bin').read_bytes()[0x4000:0x5000])
    state[0xD21:0xD25] = bytes.fromhex('8E 00 09 60')  # capture message X; RTS
    (out / 'state.bin').write_bytes(state)
    (out / f'{name}.bin').write_bytes(module)
    (out / 'driver.bin').write_bytes(bytes((0x20, entry & 255, entry >> 8, 0x4C, 0, 8)))
    result = out / f'{name}.dsk'
    a2test.build_disk(out, 'DRIVER', out / "driver.bin", 0x0800, disk=result,
                      bload=[('STATE', out / "state.bin", 0x4000), ('MODULE', out / (name+".bin"), 0x5800)])
    return result


def main():
    out = HERE / 'build/re_sites'
    out.mkdir(exist_ok=True)
    journey = smalldos.Disk((HERE / 'build/JOURNEY.dsk').read_bytes())
    journey.flip = True
    actions = disk(out, 'actions', journey.run(0x12, 8, 6), 0x5800)
    cases = [(40,0,0,0,17), (40,1,0,1,10), (40,1,1,1,11),
             (39,1,1,0,10), (39,1,0,0,11), (39,0,0,0,17)]
    steps = ['until:0800:20000']
    for verb, present, inside, _, _ in cases:
        steps += poke(0x1E,bytes([verb])) + poke(5,b'\x89')
        steps += poke(0x4BA1,bytes([present])) + poke(0xD5E,bytes([inside]))
        steps += ['until:0803:1000','peek:0D5E:1','peek:0900:1','until:0800:1000']
    r = a2test.run(actions, steps, emulator=a2test.A2SHOT, timeout=900)
    results = []
    for k,(verb,present,inside,expected,message) in enumerate(cases):
        got, msg = r.dumps[2*k][0], r.dumps[2*k+1][0]
        assert (got,msg) == (expected,message), (verb,present,inside,got,msg)
        results.append(dict(verb=verb,present=present,before=inside,after=got,message=msg))
    print('Original ENTER/EXIT SHELTER: six state/message fixtures OK')

    module = bytearray((HERE / 'build/re_surv/m0B2.bin').read_bytes())
    module[0x186] = 0x60  # stop before the separate fire adjustment
    module[0x19C] = 0x60  # water branch exit (outside these air fixtures)
    thermal = disk(out, 'temperature', module, 0x5948)
    temps = [(air,inside,igloo) for air in (-20,0,42,100)
             for inside,igloo in ((0,0),(1,0),(1,1))]
    steps = ['until:0800:20000']
    for air,inside,igloo in temps:
        steps += poke(0x4B9B,bytes([air & 255])) + poke(0x4B9D,bytes([(air-20) & 255]))
        steps += poke(0xD5E,bytes([inside])) + poke(0x45F1,bytes([igloo])) + poke(0x4B70,b'\0')
        steps += ['until:0803:1000','peek:00EE:1','until:0800:1000']
    r = a2test.run(thermal, steps, emulator=a2test.A2SHOT, timeout=900)
    for (air,inside,igloo), b in zip(temps,r.dumps):
        value = b[0] if b[0] < 128 else b[0]-256
        expected = (35 if igloo else air+15) if inside else air-20
        assert value == expected, (air,inside,igloo,value,expected)
        results.append(dict(air=air,inside=inside,igloo=igloo,effective=value))
    (out / 'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Original shelter/igloo temperature: twelve fixtures OK')


if __name__ == '__main__':
    main()
