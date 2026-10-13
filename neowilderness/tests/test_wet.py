#!/usr/bin/env python3
"""Wet clothing, immersion, and real SWIM/shore commands on the Apple II ROM."""
import math, sys, tempfile
from common import HERE, L, DISK, a2test, disk_with, fp, text_screen, state
from gendata import fp as encode, ITEMS
from test_thermal import poke, call, scalar

DRY={2:20,3:60,4:120,5:100,6:120,7:60,8:60,12:500,13:250,14:200,
     15:150,16:200,17:350,18:200,19:200,20:150}
WET={2:60,3:80,4:160,5:150,6:160,7:80,8:80,12:600,13:500,14:2000,
     15:1500,16:2000,17:600,18:2000,19:2000,20:200}


def main():
    failures=[]
    def check(name,ok):
        print(f'  {name}: {"OK" if ok else "FAIL"}')
        if not ok: failures.append(name)
    idle=L.until('idle',20000)
    done=f'until:{L["idle"]+3:04X}:6000'
    setup=[idle]+call(['thermal'])+poke('s_metabolic',1.65)+poke('s_step',0)+[done,idle]
    outfits=[(),(3,4,5,6,7,8,14),(2,3,4,5,6,7,8,14),tuple(DRY),
             (14,15,18,19,20),(3,4,6,7,8)]
    steps=setup+call(['thermal_clothes'])
    expected=[]
    for wet in (0,1,2):
        for outfit in outfits:
            parts=[500,200,500,500,500]
            losses=WET if wet else DRY
            for item in sorted(outfit):
                part=ITEMS[item-1][7]-2
                parts[part]=int(parts[part]*losses[item]/(parts[part]+losses[item])+.5)
            q=sum(p*a for p,a in zip(parts,(2638,2100,790,255,260)))/6058*(2 if wet==2 else 1)
            global_loss=(4000 if wet==2 else 2000) if wet else 500
            expected.append(max(10,int(global_loss*q/(global_loss+q)+.5)))
            steps += [L.poke('wet_mode',wet)]
            for item in range(2,21):
                steps.append(L.poke('it_place',1 if item in outfit else 0,item))
            steps += [done,L.peek('s_insul',5),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    actual=[fp(r.mem(L['s_insul'],5,k)) for k in range(len(expected))]
    check('18 outfits: original wet garment losses, areas and global loss',actual==expected)
    check('cotton loses more insulation than wool when wet',
          actual[6+4]-actual[4]>actual[6+5]-actual[5])
    check('immersion increases loss again for every outfit',all(actual[12+k]>actual[6+k] for k in range(6)))

    steps=setup+call(['thermal_rate'])
    cases=[]
    coefficient=fp(encode(.3))
    for wet in (1,2):
        for index in (10,47,180,300):
            for altitude in (0,100,227,382):
                for metabolic in (1.65,5.2):
                    for air in (-20,100):
                        # Current map cell height=127; base altitude supplies the rest.
                        # Use height zero below 127 so all altitudes remain representable.
                        height=min(altitude,127)
                        base=altitude-height
                        addr=0x7000+64+10*112+10
                        steps += [L.poke('px',0),L.poke('px',10,1),L.poke('py',0),L.poke('py',10,1),
                                  f'poke:{addr:04X}:{height:02X}',f'poke:700A:{base:02X}',L.poke('wet_mode',wet),
                                  L.poke('felt_temp',air),L.poke('felt_temp',air>>8,1)]
                        steps += poke('s_insul',index)+poke('s_metabolic',metabolic)+poke('s_body',98.6)
                        steps += [done,L.peek('s_therm_rate',5),L.peek('thermal_zone'),L.peek('thermal_mode'),idle]
                        effective=70-math.floor(coefficient*altitude) if wet==2 else air
                        rate,zone=scalar(effective,index,metabolic)
                        if zone==2: rate*=1+.5*wet
                        cases.append((rate,zone,2 if zone==2 else 0))
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    bad=[]
    for k,(rate,zone,mode) in enumerate(cases):
        if (abs(fp(r.mem(L['s_therm_rate'],5,k))-rate)>5e-7
            or r.mem(L['thermal_zone'],1,k)!=bytes([zone])
            or r.mem(L['thermal_mode'],1,k)!=bytes([mode])): bad.append(k)
    check('128 wet scalar cases: water altitude, cold multiplier, no sweating',not bad)
    if bad: print('   ',bad[:12])

    # Cold mountain lake. Oxygen isolates immersion from the newly ported
    # altitude penalty, which otherwise changes both travel speed and health.
    # Altitude and oxygen are checked independently in test_medical.py;
    # exact loaded swimming duration is covered by test_swim_cadence.py.
    mapbin=bytearray((HERE/'build/map.bin').read_bytes())
    mapbin[2:8]=(10<<8).to_bytes(2,'little')+(10<<8).to_bytes(2,'little')+(140).to_bytes(2,'little')
    mapbin[10]=227; mapbin[13]=mapbin[14]=60; mapbin[15]=0
    mapbin[64:]=bytes(112*84)
    for x in (10,11,12): mapbin[64+10*112+x]=0x80
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,mapbin)
        # A previous long REST can leave a 240-minute health period. Native
        # swimming prepares a 15-minute first interval, so this must cool now.
        steps=[idle,L.poke('oxygen_active',1),L.poke('health_period',240),L.peek('it_place',76),
               'key:SWIM','press:\r',L.until('number_idle',6000),'key:3\r',
               'wait:1',idle]
        for name,size in (('px',6),('wet_mode',1),('s_elap',5),('s_body',5),('s_spent',5),('s_metabolic',5)):
            steps.append(L.peek(name,size))
        steps.append(L.peek('it_place',76))
        steps += ['key:STATUS\r',L.until('wait_key',6000),'peek:0400:1024','key: ','wait:1',idle,
                  'key:REST','press:\r',L.until('number_idle',6000),'key:1\r','wait:1',idle]
        steps += [L.peek(n,5) for n in ('s_body','s_spent')]+[L.peek('wet_mode'),L.peek('s_health',5),L.peek('injury_active',15),L.peek('dead')]
        steps += ['key:WALK','press:\r',L.until('number_idle',6000),'key:1\r','wait:1',idle,
                  L.peek('px',6),L.peek('wet_mode'),L.peek('s_elap',5),L.peek('s_body',5)]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
        swim_position = state(r.mem(L['px'],6))
        check('A time-limited SWIM uses half-cell steps and remains in water',
              10<<8 < swim_position[0] < 13<<8 and swim_position[0]%128 == 0
              and swim_position[1:] == (10<<8,140))
        check('SWIM uses loaded cadence instead of 19 minutes per cell, and activates immersion',
              2.5<fp(r.mem(L['s_elap'],5))<3.5 and r.mem(L['wet_mode'],1)==b'\x02')
        check('SWIM preserves all equipment places',r.mem(L['it_place'],76)==r.mem(L['it_place'],76,1))
        check('real SWIM uses original loaded swimming effort, not walking effort',
              abs(fp(r.mem(L['s_metabolic'],5))-14.43)<1e-8)
        check('STATUS reports immersion and cold effects',
              'IMMERSED' in '\n'.join(text_screen(r.mem(0x400,1024)))
              and fp(r.mem(L['s_body'],5))<98.6-1e-5)
        check('REST in water stays immersed, cools further and spends shivering calories',
              r.mem(L['wet_mode'],1,1)==b'\x02' and fp(r.mem(L['s_body'],5,1))<fp(r.mem(L['s_body'],5))
              # Adaptive health intervals depend on the preceding swimming
              # effort; integer rounding happens per interval, not per hour.
              and fp(r.mem(L['s_spent'],5,1))-fp(r.mem(L['s_spent'],5))>60*1.65)
        check('WALK exits onto land and restores the dry thermal selector',
              state(r.mem(L['px'],6,1))==(14*256,10<<8,140) and r.mem(L['wet_mode'],1,2)==b'\0'
              and abs(fp(r.mem(L['s_elap'],5,1))-fp(r.mem(L['s_elap'],5))-2.05)<1e-7)
        if failures and failures[-1]=='WALK exits onto land and restores the dry thermal selector':
            print('    swim / walk positions:',swim_position,state(r.mem(L['px'],6,1)))
            print('    elapsed:',fp(r.mem(L['s_elap'],5)),fp(r.mem(L['s_elap'],5,1)),
                  'wet:',r.mem(L['wet_mode'],1,2).hex(),'body:',fp(r.mem(L['s_body'],5,2)))
            print('    before walk: health',fp(r.mem(L['s_health'],5)),
                  'injuries',r.mem(L['injury_active'],15).hex(),'dead',r.mem(L['dead'],1).hex())
        # Land-only SWIM refuses without advancing time or changing inventory.
        mapbin[64:]=bytes(112*84)
        disk=disk_with(tmp,mapbin)
        steps=[idle,L.peek('it_place',76),'key:SWIM','press:\r',L.until('number_idle',6000),'key:1\r',
               'wait:1',idle,L.peek('px',6),L.peek('s_elap',5),L.peek('it_place',76)]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
        check('SWIM on land refuses with no time or equipment changes',
              state(r.mem(L['px'],6))==(10<<8,10<<8,140) and fp(r.mem(L['s_elap'],5))==0
              and r.mem(L['it_place'],76)==r.mem(L['it_place'],76,1))
    print(f'{len(failures)} failures')
    sys.exit(bool(failures))


if __name__=='__main__': main()
