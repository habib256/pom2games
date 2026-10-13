#!/usr/bin/env python3
"""Run isolated original thermal branches on the Apple II ROM.

Requires local build/game.bin and build/re_surv/m0B2.bin; no original bytes
are stored in the repository. Generates a private DOS disk under build/.
"""
import json, math, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test
from gendata import fp as encode
from re_surv_fp import fp


def poke(addr, data):
    return [f'poke:{addr+i:04X}:{v:02X}' for i, v in enumerate(data)]


def main():
    out = HERE / 'build/re_thermal'
    out.mkdir(exist_ok=True)
    state = bytearray((HERE / 'build/game.bin').read_bytes()[0x4000:0x5000])
    state[0xD2A] = 0x60  # suppress messages only; do not enter the disk loader
    (out / 'state.bin').write_bytes(state)
    (out / 'driver.bin').write_bytes(bytes.fromhex('20 11 58 4C 00 08'))
    (out / 'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n20 PRINT CHR$(4);"BLOAD THERMAL"\n30 PRINT CHR$(4);"BRUN DRIVER"\n')
    disk = out / 'probe.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'), '--out', str(disk),
                    '--bas', f'HELLO={out / "hello.bas"}', '--bin', f'STATE={out / "state.bin"}@0x4000',
                    '--bin', f'THERMAL={HERE / "build/re_surv/m0B2.bin"}@0x5800',
                    '--bin', f'DRIVER={out / "driver.bin"}@0x0800'], check=True, capture_output=True)
    steps = ['until:0800:20000']
    cases = []
    # Integration alone: the signed rate may move toward or away from normal.
    for temp, rate in [(98.6,-.2),(98.6,-.3),(98.6,-.4),(97,-.2),(97,.2),(100,-.2),(100,.2),
                       (98.5,-.4),(98.5,.4),(98.7,-.4),(98.7,.4)]:
        cases.append(dict(kind='integration', temp=temp, rate=rate))
        steps += poke(0x801,bytes.fromhex('FE 5B'))
        steps += poke(0x4C70,encode(temp)) + poke(0x4C75,encode(rate))
        steps += poke(0x5C91,encode(temp-98.6)) + poke(0x4C08,(60).to_bytes(2,'little'))
        steps += poke(0xEF,bytes([1 if rate>0 else 255])) + poke(3,b'\x14')
        steps += ['until:0803:1000', 'peek:4C70:10', 'until:0800:1000']
    # Full routine, its original areas/resistances and controlled temperature.
    for metabolic in (1.65, 5.2):
        for air in (-20,0,20,42,60,80,100):
            cases.append(dict(kind='full', air=air, metabolic=metabolic))
            steps += poke(0x801,bytes.fromhex('11 58')) + poke(0x4B9D,bytes([air & 255]))
            steps += poke(0x4C20,encode(metabolic))
            steps += poke(0x4C70,encode(98.6)) + poke(0x4C08,(60).to_bytes(2,'little'))
            steps += poke(0x0D5E,b'\0') + poke(0x4B70,b'\0') + poke(0x4B73,b'\0') + poke(0x4B8B,b'\0')
            steps += ['until:0803:1000', 'peek:4C70:10','peek:4BE8:2','peek:00EE:2','until:0800:1000']
    for temp, minutes in ((97,60),(100,60),(97,2400),(100,2400),(98.6,60)):
        cases.append(dict(kind='neutral', temp=temp, minutes=minutes))
        steps += poke(0x801,bytes.fromhex('11 58')) + poke(0x4B9D,b'\x2a')
        steps += poke(0x4C20,encode(1.65)) + poke(0x4C70,encode(temp))
        steps += poke(0x4C08,minutes.to_bytes(2,'little'))
        steps += ['until:0803:1000','peek:4C70:10','until:0800:1000']
    r = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    for k, case in enumerate(cases):
        mem = r.mem(0x4C70,10,k)
        case.update(result=fp(mem[:5]), computed_rate=fp(mem[5:]))
        if case['kind']=='full':
            j=k-11
            case.update(index=int.from_bytes(r.mem(0x4BE8,2,j),'little'),
                        effective=list(r.mem(0xEE,2,j)))
    for case in cases:
        if case['kind']=='full':
            e,m,i=case['air'],case['metabolic'],case['index']
            ratio=math.sqrt(m/1.65)
            threshold=ratio*(20+(max(e,0)/10)**3)/6
            rate=(abs(.2-55*.0006058*max(e,0)*ratio/math.sqrt(i)) if threshold>i
                  else -.0006058*math.sqrt(i)*abs(e-80) if 9*threshold<i else 0)
            assert abs(case['computed_rate']-rate)<2e-7,case
        elif case['kind']=='neutral':
            delta=(98.6-case['temp'])*min(1,.1*.017*case['minutes'])
            assert abs(case['result']-(case['temp']+delta))<3e-7,case
    (out/'results.json').write_text(json.dumps(cases,indent=2)+'\n')
    print(json.dumps(cases,indent=2))
    print('14 original scalar cases and 5 neutral recoveries: OK')


if __name__=='__main__':
    main()
