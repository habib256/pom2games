#!/usr/bin/env python3
"""Isolate original wind and energy branches on the ROM, using local assets."""
import json, math, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE.parent/'dev/tools'))
sys.path.insert(0,str(HERE/'tools'))
import a2test
from gendata import fp as encode
from re_surv_fp import fp


def poke(addr,data):
    return [f'poke:{addr+i:04X}:{b:02X}' for i,b in enumerate(data)]


def main():
    out=HERE/'build/re_wind_energy'
    out.mkdir(exist_ok=True)
    (out/'state.bin').write_bytes((HERE/'build/game.bin').read_bytes()[0x4000:0x5000])
    module=bytearray((HERE/'build/re_surv/m098.bin').read_bytes())
    module[0x27B]=0x60  # return after energy update; omit disk dispatch only
    (out/'module.bin').write_bytes(module)
    (out/'driver.bin').write_bytes(bytes.fromhex('20 E5 59 4C 00 08'))
    (out/'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n20 PRINT CHR$(4);"BLOAD MODULE"\n30 PRINT CHR$(4);"BRUN DRIVER"\n')
    disk=out/'probe.dsk'
    subprocess.run([sys.executable,str(HERE.parent/'dev/tools/dos33.py'),'--out',str(disk),
                    '--bas',f'HELLO={out/"hello.bas"}','--bin',f'STATE={out/"state.bin"}@0x4000',
                    '--bin',f'MODULE={out/"module.bin"}@0x5800','--bin',f'DRIVER={out/"driver.bin"}@0x0800'],
                   check=True,capture_output=True)
    steps=['until:0800:20000']
    cases=[]
    for air in (-50,-20,0,42,99,100,110):
        for wind in (0,1,7,16,36):
            cases.append(dict(kind='wind',air=air,wind=wind))
            steps+=poke(0x4B9B,bytes([air&255]))+poke(0x4B9F,bytes([wind]))
            steps+=['until:0803:1000','peek:4B9D:1','until:0800:1000']
    steps+=poke(0x801,bytes.fromhex('22 58'))
    for weight in (123,165,200):
        for rate in (1.65,5.2):
            for shivering in (0,1):
                for minutes in (0,1,5,19,30,60,255):
                    cases.append(dict(kind='energy',weight=weight,rate=rate,shivering=shivering,minutes=minutes))
                    steps+=poke(0x4BF6,weight.to_bytes(2,'little'))+poke(0x4C20,encode(rate))
                    steps+=poke(0x4BC6,minutes.to_bytes(2,'little'))+poke(0x4B87,bytes([shivering]))
                    steps+=poke(0x4BDA,(600).to_bytes(2,'little'))
                    steps+=['until:0803:1000','peek:4BDA:2','until:0800:1000']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    wind_k=energy_k=0
    for c in cases:
        if c['kind']=='wind':
            actual=r.mem(0x4B9D,1,wind_k)[0];wind_k+=1
            # AYINT floors signed values, including above 100 F.
            expected=c['air']-math.floor(math.sqrt(c['wind'])*fp(module[0x23B:0x240])*(100-c['air']))
            c.update(result=actual if actual<128 else actual-256,expected=expected)
            assert actual==expected&255,c
        else:
            actual=int.from_bytes(r.mem(0x4BDA,2,energy_k),'little')-600;energy_k+=1
            rate=fp(encode(fp(encode(c['rate'])) + c['shivering']*fp(module[0x236:0x23B])*c['weight']))
            expected=math.floor(c['minutes']*rate)
            c.update(result=actual,expected=expected)
            assert actual==expected,c
    (out/'results.json').write_text(json.dumps(cases,indent=2)+'\n')
    print(f'{wind_k} original wind cases and {energy_k} energy cases: OK')


if __name__=='__main__': main()
