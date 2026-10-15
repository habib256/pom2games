#!/usr/bin/env python3
"""Thermal ROM arithmetic, original branch fixtures and playable clothing effects."""
import math, sys, tempfile
from common import HERE, L, DISK, a2test, disk_with, fp, text_screen
from gendata import fp as encode, ITEMS


def poke(name, value):
    return [L.poke(name, b, i) for i, b in enumerate(encode(value))]


def call(targets):
    addr = L['idle']
    code = bytearray()
    for target in targets:
        a = L[target]
        code += bytes((0x20, a & 255, a >> 8))
    code += bytes((0x4C, addr & 255, addr >> 8))
    return [f'poke:{addr+i:04X}:{b:02X}' for i, b in enumerate(code)]


def scalar(air, index, metabolic):
    r = math.sqrt(metabolic / 1.65)
    threshold = r * (20 + (max(air, 0) / 10) ** 3) / 6
    if threshold > index:
        return abs(.2 - 55 * .0006058 * max(air, 0) * r / math.sqrt(index)), 1
    if 9 * threshold < index:
        return -.0006058 * math.sqrt(index) * abs(air - 80), 2
    return 0, 0


def main():
    fails = []
    def check(name, ok):
        print(f'  {name}: {"OK" if ok else "FAIL"}')
        if not ok:
            fails.append(name)
    idle = L.until('idle', 20000)
    done = f'until:{L["idle"]+3:04X}:6000'
    # Load the real thermal overlay once through its resident wrapper.
    steps = [idle] + call(['thermal']) + poke('s_metabolic',1.65) + poke('s_step',0)
    steps += [done, idle] + call(['thermal_rate'])
    cases = []
    for index in (10,47,180):
        for metabolic in (1.65,5.2,8.25):
            for air in (-20,0,20,42,60,80,120):
                cases.append((air,index,metabolic))
                steps += poke('s_insul',index) + poke('s_metabolic',metabolic) + poke('s_body',98.6)
                steps += [L.poke('felt_temp',air), L.poke('felt_temp',air >> 8,1), done, L.peek('s_therm_rate',5),L.peek('thermal_zone'), idle]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    bad=[]
    for k,(air,index,m) in enumerate(cases):
        rate,zone=scalar(air,index,m)
        if abs(fp(r.mem(L['s_therm_rate'],5,k))-rate)>2e-7 or r.mem(L['thermal_zone'],1,k)[0]!=zone:
            bad.append((air,index,m))
    check('63 scalar cases: signed air, clothing, activity, thresholds',not bad)
    if bad: print('   ',bad)

    # Independent dry-layer calculation, including rounding and empty slots.
    losses={2:20,3:60,4:120,5:100,6:120,7:60,8:60,12:500,14:200,
            15:150,16:200,18:200,19:200,20:150}
    outfits=[(),(3,4,5,6,7,8,14),(2,3,4,5,6,7,8,14),tuple(losses),
             (14,15,18,19,20),(3,4,6,7,8)]
    steps=[idle]+call(['thermal'])+poke('s_metabolic',1.65)+poke('s_step',0)+[done,idle]
    steps+=call(['thermal_clothes'])
    expected=[]
    for outfit in outfits:
        parts=[500,200,500,500,500]
        for i in sorted(outfit):
            part=ITEMS[i-1][7]-2
            parts[part]=int(parts[part]*losses[i]/(parts[part]+losses[i])+.5)
        q=sum(p*a for p,a in zip(parts,(2638,2100,790,255,260)))/6058
        expected.append(max(10,int(500*q/(500+q)+.5)))
        for i in range(2,21):
            steps.append(L.poke('it_place',1 if i in outfit else 0,i))
        steps+=[done,L.peek('s_insul',5),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    check('six outfits: layer rounding, body areas and empty slots',all(
        abs(fp(r.mem(L['s_insul'],5,k))-v)<1e-6 for k,v in enumerate(expected)))

    # Measured from original m0B2 on the same ROM, via re_thermal_probe.py.
    fixtures=[(98.6,-.2,98.6),(98.6,-.3,98.3),(98.6,-.4,98.2),
              (97,-.2,97),(97,.2,97.2),(100,-.2,99.8),(100,.2,100),
              (98.5,-.4,98.1),(98.5,.4,98.6),(98.7,-.4,98.6),(98.7,.4,99.1)]
    steps=[idle]+call(['thermal'])+poke('s_metabolic',1.65)+poke('s_step',0)+[done,idle]
    steps+=call(['thermal_integrate'])
    for temp,rate,result in fixtures:
        steps+=poke('s_body',temp)+poke('s_therm_rate',rate)+poke('s_step',60)
        steps+=[L.poke('thermal_zone',1 if rate>0 else 2),done,L.peek('s_body',5),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    check('11 original integration fixtures, including exact .3 boundary',all(
        abs(fp(r.mem(L['s_body'],5,k))-result)<3e-7 for k,(_,_,result) in enumerate(fixtures)))

    # Neutral recovery uses its own minute factor and cannot overshoot.
    steps=[idle]+call(['thermal'])+poke('s_metabolic',1.65)+poke('s_step',0)+[done,idle]
    steps+=call(['thermal_rate','thermal_integrate','thermal_condition'])
    end=f'until:{L["idle"]+9:04X}:6000'
    for temp,mins in ((97,60),(100,60),(97,2400),(100,2400),(98.6,60)):
        steps+=poke('s_insul',47)+poke('s_metabolic',1.65)+poke('s_body',temp)+poke('s_step',mins)
        steps+=[L.poke('felt_temp',42),L.poke('felt_temp',0,1),end,L.peek('s_body',5),L.peek('s_therm_factor',5),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    check('neutral recovery: proportional step and no crossing 98.6 F',all(
        abs(fp(r.mem(L['s_body'],5,k))-v)<3e-7 for k,v in enumerate((97.1632,99.8572,98.6,98.6,98.6))))
    check('cold/hot health factors match untreated quadratic losses',all(
        abs(fp(r.mem(L['s_therm_factor'],5,k))-v)<3e-7
        for k,v in enumerate((1-.012*(98.6-97.1632)**2,1-.027*(99.8572-98.6)**2,1,1,1))))

    # Actual commands on a controlled cold, dry map. Disable encounter
    # interruptions so these fixtures measure the full requested exposure.
    mapbin=bytearray((HERE/'build/map.bin').read_bytes())
    mapbin[10]=0; mapbin[13]=mapbin[14]=0
    mapbin[64:]=bytes(112*84)
    cold=[]
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,mapbin)
        for dressed in (False,True):
            steps=[idle,L.poke('nature_frequency',0)]
            if dressed:
                steps+=['key:WEAR PARKA\r','wait:1',idle]
            else:
                for name in ('BALACLAVA','PANTS','BOOTS','WOOL SOCKS','MITTENS','SWEATER','JERSEY'):
                    steps += [f'key:DROP {name}\r','wait:1',idle]
            steps+=['key:REST','press:\r',L.until('number_idle',6000),'key:8\r','wait:1',idle,
                    L.peek('s_body',5),L.peek('s_insul',5),L.peek('s_health',5),L.peek('dead'),
                    'key:STATUS\r',L.until('wait_key',6000),'peek:0400:1024']
            r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
            cold.append([fp(r.mem(L[n],5)) for n in ('s_body','s_insul','s_health')])
            if not dressed:
                screen='\n'.join(text_screen(r.mem(0x400,1024)))
                check('STATUS shows actual temperature and SHIVERING',
                      f'BODY    {cold[-1][0]:.1f}F' in screen and 'SHIVERING' in screen and 'HYPOTHERMIA' in screen)
            check(f'cold REST 8 ({"parka" if dressed else "no clothes"}): alive',r.mem(L['dead'],1)==b'\0')
    check('wearing the parka reduces loss and preserves body heat and health',
          cold[1][1]<cold[0][1] and cold[1][0]>cold[0][0] and cold[1][2]>cold[0][2])
    hotmap=bytearray(mapbin)
    with tempfile.TemporaryDirectory() as tmp:
        for hours in (6,24):
            # The original slow wave cools this journey by 4 F. At 100 F
            # the overnight respite can now prevent death; keep the fatal
            # fixture at sustained extreme heat, below signed-byte wrap.
            hotmap[13]=hotmap[14]=100 if hours==6 else 110
            disk=disk_with(tmp,hotmap)
            steps=[idle,L.poke('nature_frequency',0),'key:WEAR PARKA\r','wait:1',idle,'key:REST','press:\r',
                   L.until('number_idle',6000),f'key:{hours}\r','wait:1']
            if hours==6:
                steps += [idle,'key:STATUS\r',L.until('wait_key',6000),'peek:0400:1024']
            else:
                steps += [L.until('wait_key',30000)]
            steps += [L.peek('s_body',5),L.peek('s_health',5),L.peek('s_elap',5),L.peek('dead')]
            r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
            if hours==6:
                screen='\n'.join(text_screen(r.mem(0x400,1024)))
                check('hot REST: higher body temperature, SWEATING and HYPERTHERMIA',
                      fp(r.mem(L['s_body'],5))>100 and 'SWEATING' in screen and 'HYPERTHERMIA' in screen)
            else:
                check('extreme heat: health reaches death threshold and REST stops early',
                      r.mem(L['dead'],1)==b'\x01' and fp(r.mem(L['s_health'],5))<.3
                      and fp(r.mem(L['s_elap'],5))<24)

    print(f'{len(fails)} failures')
    sys.exit(bool(fails))


if __name__=='__main__': main()
