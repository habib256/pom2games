#!/usr/bin/env python3
"""Verify wet clothing and immersion on local original m0B2, never redistributed."""
import json, math, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent/'dev/tools'))
sys.path.insert(0, str(HERE/'tools'))
import a2test
from gendata import fp as encode
from re_surv_fp import fp
from re_thermal_probe import poke


def main():
    out=HERE/'build/re_wet'
    out.mkdir(exist_ok=True)
    memory=(HERE/'build/game.bin').read_bytes()
    state=bytearray(memory[0x4000:0x5000])
    state[0xD2A]=0x60  # messages only
    (out/'state.bin').write_bytes(state)
    (out/'driver.bin').write_bytes(bytes.fromhex('20 11 58 4C 00 08'))
    (out/'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n20 PRINT CHR$(4);"BLOAD THERMAL"\n30 PRINT CHR$(4);"BRUN DRIVER"\n')
    disk=out/'probe.dsk'
    subprocess.run([sys.executable,str(HERE.parent/'dev/tools/dos33.py'),'--out',str(disk),
        '--bas',f'HELLO={out/"hello.bas"}','--bin',f'STATE={out/"state.bin"}@0x4000',
        '--bin',f'THERMAL={HERE/"build/re_surv/m0B2.bin"}@0x5800',
        '--bin',f'DRIVER={out/"driver.bin"}@0x0800'],check=True,capture_output=True)
    cases=[]
    steps=['until:0800:20000']
    for wet in (0,1,2):
        for altitude in (0,100,227):
            for air in (-20,42,100):
                for metabolic in (1.65,5.2):
                    cases.append(dict(wet=wet,altitude=altitude,air=air,metabolic=metabolic))
                    steps+=poke(0x4B70,bytes([wet]))+poke(0xD4,bytes([altitude]))+poke(0x60A1,b'\0')
                    steps+=poke(0x4B9D,bytes([air&255]))+poke(0x4C20,encode(metabolic))
                    steps+=poke(0x4C70,encode(98.6))+poke(0x4C08,(60).to_bytes(2,'little'))
                    steps+=poke(0x0D5E,b'\0')+poke(0x4B73,b'\0')+poke(0x4B8B,b'\0')
                    steps+=['until:0803:1000','peek:4BE8:2','peek:00EE:2','peek:4C75:5','peek:4B7B:1','until:0800:1000']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    areas=(2638,2100,790,255,260)
    composition=int.from_bytes(memory[0x4BBE:0x4BC0],'little')
    weight=int.from_bytes(memory[0x4BF6:0x4BF8],'little')
    for k,c in enumerate(cases):
        wet=c['wet']
        index=int.from_bytes(r.mem(0x4BE8,2,k),'little')
        base=0x4AF2 if wet else 0x4AE6
        parts=[int.from_bytes(memory[a:a+2],'little') for a in range(base,base+12,2)]
        q=sum(p*a for p,a in zip(parts[1:],areas))/6058*(wet if wet else 1)
        loss=parts[0]*(2 if wet==2 else 1)
        expected=max(10,math.floor(loss*q/(loss+q)*(1-composition/weight)+.5))
        assert index==expected,(c,index,expected)
        e=(70-math.floor(fp(encode(.3))*c['altitude'])) if wet==2 else c['air']
        actual_e=int.from_bytes(r.mem(0xEE,2,k)[:1],'little',signed=True)
        assert actual_e==e,(c,actual_e,e)
        ratio=math.sqrt(c['metabolic']/1.65)
        b=ratio*(20+(max(e,0)/10)**3)/6
        rate=(abs(.2-55*.0006058*max(e,0)*ratio/math.sqrt(index)) if b>index else
              -.0006058*math.sqrt(index)*abs(e-80)*(1+.5*wet) if 9*b<index else 0)
        actual=fp(r.mem(0x4C75,5,k))
        assert abs(actual-rate)<3e-7,(c,actual,rate)
        if wet: assert r.mem(0x4B7B,1,k)==b'\0',c
        c.update(index=index,effective=e,rate=actual)
    (out/'results.json').write_text(json.dumps(cases,indent=2)+'\n')
    print('54 original cases: wet index, immersion temperature, cold multiplier, sweating: OK')


if __name__=='__main__': main()
