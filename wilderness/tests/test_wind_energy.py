#!/usr/bin/env python3
"""Wind chill, signed extremes and original per-step shivering calories."""
import math, sys, tempfile
from common import HERE,L,DISK,a2test,disk_with,fp,text_screen
from gendata import fp as encode
from test_thermal import poke,call


def main():
    failures=[]
    def check(name,ok):
        print(f'  {name}: {"OK" if ok else "FAIL"}')
        if not ok: failures.append(name)
    idle=L.until('idle',20000)
    done=f'until:{L["idle"]+3:04X}:6000'
    # Real module loader, then isolated calls on the same ROM as the original.
    steps=[idle]+call(['thermal'])+poke('s_metabolic',1.65)+poke('s_step',0)+[done,idle]
    steps+=call(['thermal_wind'])
    cases=[(air,wind) for air in (-128,-100,-50,-20,0,42,99,100,110,127)
           for wind in (0,1,7,16,36,100)]
    k=fp(encode(1/12))
    expected=[]
    for air,wind in cases:
        expected.append(air-math.floor(math.sqrt(wind)*k*(100-air)))
        steps+=[L.poke('airtemp',air),L.poke('wind',wind),done,L.peek('felt_temp',2),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    actual=[int.from_bytes(r.mem(L['felt_temp'],2,i),'little',signed=True) for i in range(len(cases))]
    check('60 wind cases: zero, negative air, above 100 F, ROM rounding',actual==expected)
    check('extreme cold remains negative and extreme heat remains positive',
          actual[cases.index((-128,100))]<-128 and actual[cases.index((127,100))]>127)
    check('original 42 F / 7 mph fixture gives 30 F',actual[cases.index((42,7))]==30)
    if actual!=expected:
        print([(c,a,e) for c,a,e in zip(cases,actual,expected) if a!=e])

    # Same 84 cases measured on original m098 by re_wind_energy_probe.py.
    # Decode/round the 5-byte effective rate before INT, as the original does.
    steps=[idle]+call(['spend_energy'])
    energy=[]
    for weight in (123,165,200):
        for activity,rate in ((0,1.65),(4,5.2)):
            for shiver in (0,2):
                for minutes in (0,1,5,19,30,60,255):
                    effective=fp(encode(fp(encode(rate))+(shiver==2)*fp(encode(.04))*weight))
                    energy.append((math.floor(minutes*effective),rate))
                    steps+=[L.poke('body_weight',weight),L.poke('body_weight',weight>>8,1),
                            L.poke('act',activity),L.poke('thermal_mode',shiver)]
                    # Reaction effort supplies a fixed rate; land travel uses native load.
                    steps+=poke('s_metabolic',rate)+poke('s_step',minutes)+poke('s_spent',600)
                    steps+=[done,L.peek('s_spent',5),L.peek('s_metabolic',5),idle]
    # Sweating has no energy bonus; compare to the same base integer rule.
    steps+=[L.poke('act',0),L.poke('thermal_mode',1)]+poke('s_step',30)+poke('s_spent',600)
    steps+=[done,L.peek('s_spent',5),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    check('84 integer energy cases match original rounding and body weights',all(
        fp(r.mem(L['s_spent'],5,i))==600+cost for i,(cost,rate) in enumerate(energy)))
    check('shivering preserves base metabolism for thermal thresholds',all(
        abs(fp(r.mem(L['s_metabolic'],5,i))-rate)<1e-8 for i,(cost,rate) in enumerate(energy)))
    check('sweating adds no calorie cost',fp(r.mem(L['s_spent'],5,len(energy)))==649)

    # Same dry outfit: only wind changes the thermal result.
    steps=[idle]+call(['thermal'])+poke('s_metabolic',1.65)+poke('s_step',0)+[done,idle]
    steps+=call(['thermal_wind','thermal'])
    end=f'until:{L["idle"]+6:04X}:6000'
    for wind in (0,36):
        steps+=poke('s_body',98.6)+poke('s_step',60)
        steps+=[L.poke('airtemp',32),L.poke('wind',wind),end,L.peek('s_body',5),L.peek('thermal_mode'),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    check('wind alone triggers shivering and cools the clothed body',
          fp(r.mem(L['s_body'],5))>fp(r.mem(L['s_body'],5,1))
          and r.mem(L['thermal_mode'],1)==b'\0' and r.mem(L['thermal_mode'],1,1)==b'\x02')

    # Actual REST commands: cold flags feed the following 30-minute step.
    mapbin=bytearray((HERE/'build/map.bin').read_bytes())
    mapbin[10]=0;mapbin[15]=0;mapbin[64:]=bytes(112*84)
    results=[]
    with tempfile.TemporaryDirectory() as tmp:
        for mean in (0,60):
            mapbin[13]=mapbin[14]=mean
            disk=disk_with(tmp,mapbin)
            steps=[idle,L.poke('nature_frequency',0),'key:REST','press:\r',L.until('number_idle',6000),'key:3\r','wait:1',idle]
            steps += [L.peek(n,5) for n in ('s_spent','s_deff','s_elap','s_metabolic')]
            steps+= [L.peek('felt_temp',2),'key:STATUS\r',L.until('wait_key',6000),'peek:0400:1024']
            r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
            results.append([fp(r.mem(L[n],5)) for n in ('s_spent','s_deff','s_elap','s_metabolic')])
            felt=int.from_bytes(r.mem(L['felt_temp'],2),'little',signed=True)
            screen='\n'.join(text_screen(r.mem(0x400,1024)))
            check(f'STATUS ({mean} F climate): signed FEEL temperature',f'FEEL {felt}F' in screen)
    check('cold REST: initial shivering and adaptive 60-minute steps',results[0][0]==600+2*247+2*495)
    check('warm REST: saved initial shivering, then 150-minute base step',results[1][0]==600+247+247)
    check('extra calorie cost increases hunger without changing elapsed time',
          results[0][1]>results[1][1] and all(abs(row[2]-3)<1e-7 for row in results)
          and all(abs(row[3]-1.65)<1e-8 for row in results))
    print(f'{len(failures)} failures')
    sys.exit(bool(failures))


if __name__=='__main__': main()
