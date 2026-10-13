#!/usr/bin/env python3
"""Original encounter acceptance: keep/replace an animal and stop activity.

Runs $5B5A of T0A S00 unchanged. Only RND ($0321) is made deterministic;
its ROM float comparison, presence fields and event flags run normally.
"""
import json, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE.parent/'dev/tools'))
sys.path.insert(0,str(HERE/'tools'))
import a2test
from gendata import fp


def main():
    out=HERE/'build/re_fauna_accept';out.mkdir(exist_ok=True)
    (out/'state.bin').write_bytes((HERE/'build/game.bin').read_bytes()[0x4000:0x8000])
    (out/'module.bin').write_bytes((HERE/'build/re_env/ch/t0As00.bin').read_bytes())
    (out/'driver.bin').write_bytes(bytes.fromhex('20 5A 5B 4C 00 08'))
    (out/'rng.bin').write_bytes(bytes.fromhex('A9 00 A0 09 4C F9 EA'))
    (out/'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n20 PRINT CHR$(4);"BLOAD MODULE"\n'
                               '30 PRINT CHR$(4);"BLOAD RNG"\n40 PRINT CHR$(4);"BRUN DRIVER"\n')
    disk=out/'probe.dsk'
    subprocess.run([sys.executable,str(HERE.parent/'dev/tools/dos33.py'),
        '--out',str(disk),'--bas',f'HELLO={out/"hello.bas"}',
        '--bin',f'STATE={out/"state.bin"}@0x4000','--bin',f'MODULE={out/"module.bin"}@0x5800',
        '--bin',f'RNG={out/"rng.bin"}@0x0321','--bin',f'DRIVER={out/"driver.bin"}@0x0800'],
        check=True,capture_output=True)
    cases=[(old,new,rnd) for old in range(4) for new in range(1,4) for rnd in (.25,.5,.75)]
    steps=['until:0800:20000']
    for old,new,rnd in cases:
        steps += [f'poke:00FD:{new:02X}',f'poke:00FC:{new+1:02X}',
                  f'poke:0D81:{old:02X}','poke:4B5F:00','poke:0DB0:00']
        steps += [f'poke:{0x4B0E+i:04X}:{int(old==i+1):02X}' for i in range(3)]
        steps += [f'poke:{0x900+i:04X}:{b:02X}' for i,b in enumerate(fp(rnd))]
        steps += ['until:0803:1000','peek:0D81:1','peek:4B0E:3','peek:4B5F:1','peek:0DB0:1','until:0800:1000']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    rows=[]
    for k,(old,new,rnd) in enumerate(cases):
        current=r.mem(0xD81,1,k)[0];present=list(r.mem(0x4B0E,3,k));stop=r.mem(0x4B5F,1,k)[0]
        expected=new if not old or rnd>=.5 else old
        accepted=int(not old or rnd>=.5)
        assert (current,present,stop)==(expected,[int(expected==i+1) for i in range(3)],accepted),(old,new,rnd,current,present,stop)
        assert r.mem(0xDB0,1,k)[0]==accepted
        rows.append(dict(old=old,new=new,roll=rnd,current=current,stop=stop))
    (out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('36 original keep/replace and action-interruption fixtures: OK')


if __name__=='__main__': main()
