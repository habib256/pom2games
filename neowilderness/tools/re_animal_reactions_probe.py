#!/usr/bin/env python3
"""Measure original Sierra reaction thresholds on ROM; no artwork is committed.

Run the original arithmetic and table accessor. Replace message output with RTS
and stop before RND, so no combat/inventory transactions are stubbed as evidence.
"""
import json, math, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE.parent/'dev/tools'), str(HERE/'tools')]
import a2test, smalldos
from re_state_fp import fp


def main():
    out = HERE/'build/re_animal_reactions'; out.mkdir(exist_ok=True)
    disk = smalldos.Disk((HERE/'build/JOURNEY.dsk').read_bytes()); disk.flip = True
    state = bytearray((HERE/'build/game.bin').read_bytes()[0x4000:0x8000])
    state[0xD2A] = 0x60 # $4D2A: suppress numbered messages
    rows = []
    for name, track, sector, count, entry, stop, value in (
        ('noise',15,7,6,0x586E,0x5898,0x5C0B),
        ('injury',6,4,6,0x5800,0x58C5,0x98),
        ('posture',6,4,6,0x584A,0x58C5,0x98),
        ('defence',6,4,6,0x593A,0x5968,0xFB),
        ('theft',6,4,6,0x5A94,0x5AC8,0xFB)):
        module = bytearray(disk.run(track,sector,count))
        module[stop-0x5800:stop-0x5800+3] = bytes.fromhex('4C 03 08')
        (out/'state.bin').write_bytes(state); (out/'module.bin').write_bytes(module)
        (out/'driver.bin').write_bytes(bytes((0x4C,entry&255,entry>>8,0x4C,0,8)))
        (out/'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n20 PRINT CHR$(4);"BLOAD MODULE"\n30 PRINT CHR$(4);"BRUN DRIVER"\n')
        probe=out/'probe.dsk'
        subprocess.run([sys.executable,str(HERE.parent/'dev/tools/dos33.py'),'--out',str(probe),
            '--bas',f'HELLO={out/"hello.bas"}','--bin',f'STATE={out/"state.bin"}@0x4000',
            '--bin',f'MODULE={out/"module.bin"}@0x5800','--bin',f'DRIVER={out/"driver.bin"}@0x0800'],check=True,capture_output=True)
        if name=='posture':
            cases=[(species,16 if tree else (13 if command<22 else 15),0,tree,cover,command)
                   for species in (1,2,3) for command in (20,37)
                   for tree in (0,1) for cover in (0,1)]
        else:
            cases = [(species,tool,hung,tree,0,17) for species in ((1,2) if name=='theft' else (1,2,3))
                     for tool in ((14,15,18) if name=='injury' else ((18,) if name=='defence' else (15,)))
                     for hung,tree in ([(0,0),(1,0),(0,1)] if name=='theft' else [(0,0)])]
        steps=['until:0800:20000']
        for species,tool,hung,tree,cover,command in cases:
            steps += [f'poke:0005:{species+75:02X}', f'poke:0015:{species:02X}', f'poke:0004:{tool:02X}',
                'poke:0019:02',f'poke:0003:{command:02X}','poke:0D5D:00',f'poke:0D5E:{cover:02X}','poke:4B71:01',
                'poke:0018:00',f'poke:4B71:{int(name=="posture"):02X}',
                'poke:4B59:00','poke:00F6:81','poke:00F7:00','poke:00F8:00','poke:00F9:00','poke:00FA:00',f'poke:4B40:{tree:02X}',f'poke:4B46:{tree:02X}',f'poke:4B4E:{hung:02X}',
                'until:0803:2000',f'peek:{value:04X}:5','until:0800:1000']
        r=a2test.run(probe,steps,emulator=a2test.A2SHOT,timeout=900)
        assert len(r.dumps)==len(cases),(name,len(r.dumps),len(cases))
        for case,b in zip(cases,r.dumps):
            species,tool,hung,tree,cover,command=case
            # Direct theft entry expects the native protection float $F6=1.
            rows.append(dict(rule=name,species=species,tool=tool,hung=hung,tree=tree,cover=cover,command=command,threshold=fp(b)))
    native = ((10,2,35,3),(10,2,25,10),(30,3,20,30))
    for row in rows:
        species,tool=row['species'],row['tool']
        noise,passive,blade,blade_win=native[species-1]
        if row['rule']=='noise': expected=.8-.03*noise
        elif row['rule']=='injury': expected={14:noise,15:passive,18:blade}[tool]*.02
        elif row['rule']=='posture':
            expected=({13:(1,1,2)[species-1],15:passive,16:passive}[tool])*.02
            if row['cover']: expected*=.1
        elif row['rule']=='defence': expected=blade_win*.005
        else: expected=.01 if row['hung'] else (.1 if row['tree'] else .05)
        assert abs(row['threshold']-expected)<1e-8,(row,expected)
    # Execute native weapon selection as well: axe and knife share method 18.
    module=bytearray(disk.run(15,7,6))
    module[0x15E:0x161]=bytes.fromhex('4C 03 08') # $595E: after method stored in $04
    (out/'module.bin').write_bytes(module)
    (out/'driver.bin').write_bytes(bytes.fromhex('4C DE 58 4C 00 08'))
    subprocess.run([sys.executable,str(HERE.parent/'dev/tools/dos33.py'),'--out',str(probe),
        '--bas',f'HELLO={out/"hello.bas"}','--bin',f'STATE={out/"state.bin"}@0x4000',
        '--bin',f'MODULE={out/"module.bin"}@0x5800','--bin',f'DRIVER={out/"driver.bin"}@0x0800'],check=True,capture_output=True)
    steps=['until:0800:20000']
    weapons=[(1,0),(0,1),(1,1)]
    for axe,knife in weapons:
        steps += ['poke:0005:4C','poke:0003:11','poke:40D1:00',
                  f'poke:40D2:{axe:02X}',f'poke:40D3:{knife:02X}',
                  'poke:45EA:00','poke:45EB:00','poke:45EC:00','poke:45ED:00',
                  'until:0803:2000','peek:0004:1','until:0800:1000']
    r=a2test.run(probe,steps,emulator=a2test.A2SHOT,timeout=900)
    assert len(r.dumps)==3 and all(b==b'\x12' for b in r.dumps),r.dumps
    (out/'weapons.json').write_text(json.dumps([dict(axe=a,knife=k,method=18) for a,k in weapons],indent=2)+'\n')
    (out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    # Execute severity arithmetic with a supplied RND; stop before applying
    # conditions. This proves the distribution, not the native fatal aftermath.
    module=bytearray(disk.run(6,4,6))
    module[0x521:0x524]=bytes.fromhex('4C 03 08') # $5D21, after severity stored
    (out/'module.bin').write_bytes(module)
    driver=bytearray(0x45)
    driver[:6]=bytes.fromhex('4C 82 5C 4C 00 08')
    driver[0x20:0x28]=bytes.fromhex('A9 40 A0 08 20 F9 EA 60') # FAC = supplied RND
    (out/'driver.bin').write_bytes(driver)
    subprocess.run([sys.executable,str(HERE.parent/'dev/tools/dos33.py'),'--out',str(probe),
        '--bas',f'HELLO={out/"hello.bas"}','--bin',f'STATE={out/"state.bin"}@0x4000',
        '--bin',f'MODULE={out/"module.bin"}@0x5800','--bin',f'DRIVER={out/"driver.bin"}@0x0800'],check=True,capture_output=True)
    steps=['until:0800:20000','poke:0321:4C','poke:0322:20','poke:0323:08']
    severity_cases=[]
    for species in (1,2):
        values=[.01,.99]
        for boundary in (.2,.4,.6,.8):
            edge=boundary**(1/species)
            values += [edge-.001,edge+.001]
        severity_cases += [(species,value) for value in sorted(values)]
    for species,value in severity_cases:
        mantissa,exponent=math.frexp(value)
        packed=bytes((exponent+128,))+((round(mantissa*2**32)&0x7FFFFFFF).to_bytes(4,'big'))
        steps += [f'poke:0015:{species:02X}']
        steps += [f'poke:{0x840+i:04X}:{b:02X}' for i,b in enumerate(packed)]
        steps += ['until:0803:2000','peek:4B90:1','until:0800:1000']
    r=a2test.run(probe,steps,emulator=a2test.A2SHOT,timeout=900)
    assert len(r.dumps)==len(severity_cases)
    severity=[]
    for (species,value),b in zip(severity_cases,r.dumps):
        expected=int(1+5*value**species)
        assert b==bytes((expected,)),(species,value,b,expected)
        severity.append(dict(species=species,rnd=value,severity=b[0]))
    (out/'severity.json').write_text(json.dumps(severity,indent=2)+'\n')
    # Observe the native clock/reaction dispatcher without loading the next
    # module. The presence gate is checked for every nonzero duration; this
    # does not establish a complete cadence across an uninterrupted activity.
    (out/'state.bin').write_bytes(state)
    driver=bytes.fromhex('4C 56 4D 8D 00 09 8E 01 09 8C 02 09 4C 00 08')
    (out/'driver.bin').write_bytes(driver)
    subprocess.run([sys.executable,str(HERE.parent/'dev/tools/dos33.py'),'--out',str(probe),
        '--bas',f'HELLO={out/"hello.bas"}','--bin',f'STATE={out/"state.bin"}@0x4000',
        '--bin',f'MODULE={out/"module.bin"}@0x5800','--bin',f'DRIVER={out/"driver.bin"}@0x0800'],check=True,capture_output=True)
    cases=[(phase,present,minutes) for phase in (0,1) for present in (0,1) for minutes in (1,5,60)]
    steps=['until:0800:20000','poke:03DB:4C','poke:03DC:03','poke:03DD:08']
    for phase,present,minutes in cases:
        steps += [f'poke:4B71:{phase:02X}',f'poke:4B72:{present:02X}',
                  f'poke:4BC6:{minutes:02X}','poke:4BC7:00','until:0803:2000',
                  'until:0800:1000','peek:0900:3','peek:4B71:1']
    r=a2test.run(probe,steps,emulator=a2test.A2SHOT,timeout=900)
    assert len(r.dumps)==2*len(cases)
    dispatch=[]
    for index,(phase,present,minutes) in enumerate(cases):
        selected=r.dumps[index*2]
        expected=bytes((6,6,4)) if phase and present else bytes((3,9,5)) # count/track/sector
        assert selected==expected,(phase,present,minutes,selected,expected)
        assert r.dumps[index*2+1]==bytes((255 if phase else 1,))
        dispatch.append(dict(phase=phase,present=present,minutes=minutes,selected=list(selected)))
    (out/'dispatch.json').write_text(json.dumps(dispatch,indent=2)+'\n')
    print(f"{len(rows)} original Sierra thresholds + 3 axe/knife selections + {len(severity)} wound severities + {len(dispatch)} dispatch cases: OK")

if __name__=='__main__': main()
