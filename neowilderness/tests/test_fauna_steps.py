#!/usr/bin/env python3
"""Encounters inside actions: replacement, interruption and long durations."""
import tempfile
from common import HERE,L,DISK,a2test,disk_with,fp,state,text_screen
from test_thermal import call
from test_sites import hours,command


def main():
    idle=L.until('idle',20000);done=f'until:{L["idle"]+3:04X}:6000'
    steps=[idle]+call(['env_day'])+[done,idle]+call(['fauna_accept'])
    fixtures=[]
    for old in (0,6,7,8):
        for candidate in range(3):
            for seed in (4,4095,4096):  # Lehmer draws below and above .5
                accepted=not old or (seed*8192 % 67099547)/67099547 >= .5
                fixtures.append((old,candidate,seed,accepted))
                for name,value in [('px',0),('py',0),('heading',140)]:
                    steps += [L.poke(name,value)]
                steps += [L.poke('px',50,1),L.poke('py',40,1),L.poke('heading',0,1),
                          L.poke('animal_kind',old),L.poke('animal_x',20),L.poke('animal_y',30),
                          L.poke('animal_bearing',70),L.poke('animal_bearing',0,1),L.poke('animal_age',17),
                          L.poke('fauna_species',candidate),L.poke('fauna_rng',4),L.poke('fauna_alert',0)]
                steps += [L.poke('weather_seed',b,i) for i,b in enumerate(seed.to_bytes(4,'little'))]
                steps += [done,L.peek('animal_kind',6),L.peek('fauna_alert'),
                          L.peek('fauna_rng'),L.peek('weather_seed',4),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    for k,(old,candidate,seed,accepted) in enumerate(fixtures):
        expected=bytes((candidate+6,50,40,140,0,0)) if accepted else bytes((old,20,30,70,0,17))
        assert r.mem(L['animal_kind'],6,k)==expected,(k,expected,r.mem(L['animal_kind'],6,k))
        assert r.mem(L['fauna_alert'],1,k)==bytes([2*int(accepted)])
        assert r.mem(L['fauna_rng'],1,k)==b'\4'
        expected_seed=seed*8192 % 67099547 if old else seed
        assert int.from_bytes(r.mem(L['weather_seed'],4,k),'little')==expected_seed
    print('  keep/replace all species, presence, bearing, age and interruption flag OK')

    m=bytearray((HERE/'build/map.bin').read_bytes())
    m[2:8]=bytes((0,12,0,8,140,0));m[8:10]=bytes((100,40));m[16]=0
    m[10]=24;m[21:24]=bytes((11,4,31));m[64:]=bytes([10])*9408
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,m)
        steps=[idle,L.poke('px',12,1),L.poke('nature_frequency',1),L.poke('fauna_rng',0xB7)]
        steps+=hours('REST',6)+[L.peek('s_elap',5),L.peek('fauna_rng'),L.peek('animal_kind'),L.peek('scene_minutes')]
        for _ in range(3): steps+=command('V')
        steps += [L.peek('s_elap',5),L.peek('fauna_rng')]
        steps += [L.poke('nature_frequency',0)]+hours('REST',1)+[L.peek('s_elap',5),L.peek('fauna_rng')]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        seed=0xB7
        assert fp(r.mem(L['s_elap'],5))==6
        assert r.mem(L['fauna_rng'],1)==bytes([seed])
        assert r.mem(L['animal_kind'],1)==b'\0', r.mem(L['animal_kind'],1)
        assert r.mem(L['scene_minutes'],1)==b'\0', r.mem(L['scene_minutes'],1)
        assert r.mem(L['fauna_rng'],1,1)==bytes([seed]) and fp(r.mem(L['s_elap'],5,1))==6
        assert r.mem(L['fauna_rng'],1,2)==bytes([seed]) and fp(r.mem(L['s_elap'],5,2))==7
        print('  REST 6 at crash: no encounters; VIEW spends no time/RNG OK')
        print('  NATURE 0 without a presence keeps the RNG unchanged during REST OK')

        steps=[idle,L.poke('px',12,1)]
        steps += [L.poke('weather_seed',0,i) for i in range(4)]
        steps+=hours('WALK',1)+[L.peek('px',6),L.peek('s_elap',5),L.peek('animal_kind'),L.peek('scene_minutes')]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        assert state(r.mem(L['px'],6))==(12*256+128,8*256,140)
        assert abs(fp(r.mem(L['s_elap'],5))-9/60)<1e-6
        assert r.mem(L['animal_kind'],1)==b'\10' and r.mem(L['scene_minutes'],1)==b'\11'
        print('  WALK 1: rattlesnake stops the action after one half-cell and exactly 9 minutes OK')

        steps=[idle,L.poke('px',12,1)]+[L.poke('weather_seed',0,i) for i in range(4)]
        steps+=hours('REST',1)+[L.peek('s_elap',5),L.peek('animal_kind'),'peek:0400:1024']
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        assert fp(r.mem(L['s_elap'],5))==1 and r.mem(L['animal_kind'],1)==b'\0'
        assert 'APPEARS' not in '\n'.join(text_screen(r.mem(0x400,1024)))
        print('  REST keeps running with a seed that would interrupt WALK OK')

        m[16:21]=bytes((1,12,8,140,0));disk=disk_with(tmp,m)
        steps=[idle,L.poke('px',12,1),L.poke('nature_frequency',100),L.poke('fauna_rng',4)]
        steps+=command('ENTER SHELTER')+hours('REST',6)
        steps+=[L.peek('s_elap',5),L.peek('fauna_rng'),L.peek('animal_kind'),L.peek('scene_minutes')]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        assert fp(r.mem(L['s_elap'],5))==6 and r.mem(L['fauna_rng'],1)==b'\4'
        assert r.mem(L['animal_kind'],1)==b'\0' and r.mem(L['scene_minutes'],1)==b'\0'
        print('  shelter blocks outdoor encounters even at NATURE 100 OK')
    print('Fauna during actions: OK')


if __name__=='__main__': main()
