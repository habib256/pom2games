#!/usr/bin/env python3
"""Run unchanged native CLIMB and HANG gates on Apple II ROM.
Only message and clock-dispatch endpoints are stubbed; proprietary inputs
and generated probe disks remain in ignored build/.
"""
import json, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE.parent/'dev/tools'))
sys.path.insert(0,str(HERE/'tools'))
import a2test, smalldos
from gendata import fp

def poke(addr,values): return [f'poke:{addr+i:04X}:{b:02X}' for i,b in enumerate(values)]
def disk(out,name,entry,module=None):
    state=bytearray((HERE/'build/game.bin').read_bytes()[0x4000:0x8000])
    state[0xD21:0xD25]=bytes.fromhex('8E 00 09 60')
    state[0xD2A:0xD2E]=bytes.fromhex('8E 01 09 60')
    state[0xD00]=0x60
    if module is not None: state[0x1800:0x1800+len(module)]=module
    (out/'state.bin').write_bytes(state)
    (out/'driver.bin').write_bytes(bytes((0x20,entry&255,entry>>8,0x4c,0,8)))
    (out/'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n20 PRINT CHR$(4);"BRUN DRIVER"\n')
    d=out/(name+'.dsk')
    subprocess.run([sys.executable,str(HERE.parent/'dev/tools/dos33.py'),'--out',str(d),'--bas',f'HELLO={out/"hello.bas"}','--bin',f'STATE={out/"state.bin"}@0x4000','--bin',f'DRIVER={out/"driver.bin"}@0x0800'],check=True,capture_output=True)
    return d

def main():
    out=HERE/'build/re_trees';out.mkdir(exist_ok=True)
    d=disk(out,'climb',0x5156)
    cases=[(near,inside,health,noun) for near in (0,1) for inside in (0,1) for health in (0,2.5,2.5001,4) for noun in (173,150) if noun==173 or inside]
    steps=['until:0800:20000']
    for near,inside,h,noun in cases:
        steps+=poke(5,[noun])+poke(0xd7,[near])+poke(0x4b40,[inside])+poke(0x4c34,fp(h))+poke(0x900,[0])
        steps+=['until:0803:1000','peek:4B40:1','peek:0900:1','until:0800:1000']
    r=a2test.run(d,steps,emulator=a2test.A2SHOT,timeout=900);rows=[]
    for i,(near,inside,h,noun) in enumerate(cases):
        expected=(0,10) if inside else ((0,16) if not near else ((1,10) if h>2.5 else (0,59)))
        got=(r.dumps[2*i][0],r.dumps[2*i+1][0]);assert got==expected,(cases[i],got,expected)
        rows.append(dict(near=near,before=inside,health=h,noun=noun,after=got[0],message=got[1]))
    print(f'{len(cases)} original CLIMB TREE/DOWN health and state fixtures: OK',flush=True)
    journey=smalldos.Disk((HERE/'build/JOURNEY.dsk').read_bytes())
    journey.flip=True
    module=journey.run(0x12,8,6)
    d=disk(out,'hang',0x58f9,module)
    # B1 pointer native $4D0C index 1 = $404C, backpack offset 21.
    state=(HERE/'build/game.bin').read_bytes()
    ptr=state[0x4dbd]+256*state[0x4dc9]
    steps=['until:0800:20000'];cases=[(near,place,weight) for near in (0,1) for place in (255,0,1,3) for weight in (165,213)]
    for near,place,weight in cases:
        steps+=poke(5,[135])+poke(0xd7,[near])+poke(ptr+21,[place])+poke(0x4c02,[weight&255,weight>>8])+poke(0x4c20,fp(1.65))+poke(0x4b4e,[0])+poke(0x4bc6,[0,0])+poke(0x900,[0,0])
        steps+=['until:0803:1000','peek:4B4E:1','peek:4BC6:2','peek:0900:2','peek:4C20:5','peek:0003:3','until:0800:1000']
    r=a2test.run(d,steps,emulator=a2test.A2SHOT,timeout=900)
    for i,(near,place,weight) in enumerate(cases):
        flag,minutes,msg,rate,command=r.dumps[5*i:5*i+5]
        success=bool(near and place!=255)
        assert flag[0]==success and int.from_bytes(minutes,'little')==(30 if success else 0),(cases[i],flag,minutes)
        assert msg[0]==(0 if success else (193 if near else 16)),(cases[i],msg)
        if success:
            assert abs(decode(rate)-(1.65+.02*weight))<1e-7
            assert command[0]==8 and command[2]==21
    (out/'climb.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(f'{len(cases)} original HANG FOOD gates, 30-minute clock and weight-dependent effort fixtures: OK')

def decode(b):
    if not b[0]: return 0.
    m=int.from_bytes(b[1:],'big');return (-1 if m&0x80000000 else 1)*(m|0x80000000)/2**32*2**(b[0]-128)
if __name__=='__main__': main()
