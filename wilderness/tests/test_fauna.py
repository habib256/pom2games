#!/usr/bin/env python3
"""Native filter fixtures, probability arithmetic and playable NATURE rolls."""
import math, tempfile
from common import HERE,L,DISK,a2test,disk_with,fp,view_rows,text_screen
from test_thermal import call,poke
from test_sites import command,hours
from fauna_cases import cases
import scene_ref


def stationary_lifetime():
    from test_input import command
    with a2test.Session(DISK) as s:
        s.step(L.until('idle',20000))
        s.step(L.poke('nature_frequency',100))
        s.step(L.poke('animal_kind',6))
        s.step(L.poke('animal_age',0))
        for axis in ('x','y'):
            s.step(L.poke('animal_'+axis,s.step(L.peek('p'+axis,1,1)).data[0]))
        rng=s.step(L.peek('fauna_rng')).data
        for text,age,kind in (('WAIT 29 MIN',29,6),('EAT CHEESE 1 OZ',45,6),
                              ('SLEEP 14 MIN',59,6),('REST 1 MIN',59,0)):
            command(s,text)
            assert s.step(L.peek('animal_kind')).data==bytes((kind,)),text
            assert s.step(L.peek('animal_age')).data==bytes((age,)),text
            assert s.step(L.peek('fauna_rng')).data==rng, 'stationary activity drew an encounter'
        assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-60)<1e-6
        assert s.step(L.peek('fauna_alert')).data==b'\0'
    print('  WAIT, meal and sleep age an existing encounter; expiry at exactly 60 minutes; no wildlife draws OK')


def main():
    stationary_lifetime()
    idle = L.until('idle',20000)
    done = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle] + call(['env_day']) + [done,idle]
    addr,target = L['idle'],L['fauna_eligible']
    code = bytes((0x20,target&255,target>>8,0x08,0x68,0x8D,0xFF,0x95,0x4C,addr&255,addr>>8))
    steps += [f'poke:{addr+i:04X}:{b:02X}' for i,b in enumerate(code)]
    fixtures = cases()
    for species,env,_ in fixtures:
        steps += [L.poke('fauna_species',species)]
        steps += [L.poke('fauna_env',v,i) for i,v in enumerate(env)]
        steps += [f'until:{addr+8:04X}:6000','peek:95FF:1',idle]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    assert len(r.dumps)==len(fixtures)
    for fixture,data in zip(fixtures,r.dumps):
        assert bool(data[0]&1)==fixture[2],(fixture,data)
    print('  162 original filter fixtures: all species and six criteria OK')

    steps = [idle] + call(['env_day']) + [done,idle] + call(['fauna_probability'])
    probabilities = []
    for species,rate in enumerate((80,40,100)):
        for level in (1,4,10):
            for frequency,minutes in ((0,60),(1,1),(1,60),(5,255),(100,255)):
                probabilities.append(256*minutes*frequency*math.sqrt(level)*rate*1e-5)
                steps += [L.poke('fauna_species',species),f'poke:7016:{level:02X}',
                          L.poke('nature_frequency',frequency),L.poke('scene_minutes',minutes),
                          done,L.peek('fauna_threshold',5),idle]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    for expected,data in zip(probabilities,r.dumps):
        assert abs(fp(data)-expected)<max(1e-7,expected*1e-8),(expected,fp(data))
    assert len(r.dumps)==len(probabilities)
    print('  45 probability cases: elapsed minutes, NATURE and difficulty OK')

    # Derive the environment from real map cells, including diagonal relief,
    # water and the legacy header, then exercise each species' seeded roll.
    steps=[idle]+call(['env_day'])+[done,idle]+call(['module_fauna'])
    roll_cases=[(.5,6,10,10,4,31,1,7),   # cougar replaces bear
                (0,6,10,10,4,31,1,7),   # winter excludes bear and snake
                (.5,12,10,10,4,31,1,8), # midday excludes bear and cougar
                (0,12,10,10,4,31,1,0),  # no species matches
                (.5,12,138,10,4,31,1,0),# water excludes all three
                (.5,12,80,80,4,31,1,0), # too high
                (.5,12,10,100,4,31,1,0),# diagonal slope too steep
                (.5,12,10,10,4,51,1,0), # regional index out of range
                (.5,12,10,10,0,0,1,8),  # legacy: difficulty 4, Sierra 31
                (.5,12,10,10,4,31,0,0)]
    for date,hour,cell,diagonal,level,climate,frequency,_ in roll_cases:
        steps+=poke('s_date',date)+poke('s_hour',hour)
        steps += [L.poke('px',0),L.poke('px',50,1),L.poke('py',0),L.poke('py',40,1),
                  'poke:700A:18',f'poke:7016:{level:02X}',f'poke:7017:{climate:02X}',
                  L.poke('nature_frequency',frequency),L.poke('scene_minutes',60),
                  L.poke('animal_kind',0),L.poke('fauna_rng',4)]
        for y in range(39,42):
            for x in range(49,52):
                value=diagonal if (x,y)==(51,41) else cell
                steps += [f'poke:{0x7040+y*112+x:04X}:{value:02X}']
        steps += [done,L.peek('animal_kind'),L.peek('fauna_env',6),L.peek('scene_minutes'),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    for k,(_,hour,cell,diagonal,level,climate,frequency,kind) in enumerate(roll_cases):
        animal=r.mem(L['animal_kind'],1,k)
        env=r.mem(L['fauna_env'],6,k)
        remaining=r.mem(L['scene_minutes'],1,k)
        assert animal==bytes([kind]) and remaining==b'\0',(k,animal,kind,remaining)
        assert env[1:]==bytes((hour,40 if cell&128 else 10,24+(cell&127),
                             abs(diagonal-(cell&127)),climate or 31)),(k,env)
    print('  map-derived environment, diagonal slope, all three seeded species and exclusions OK')

    m = bytearray((HERE/'build/map.bin').read_bytes())
    m[2:8]=bytes((0,8,0,8,140,0));m[8:10]=bytes((100,40));m[16]=0
    m[10]=24;m[21:24]=bytes((11,4,31));m[64:]=bytes([10])*9408
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,m)
        steps=[idle,L.poke('sky_enabled',0),L.poke('px',12,1)]
        steps+=hours('NATURE',0)+[L.peek('nature_frequency')]
        steps+=hours('REST',1)+[L.peek('animal_kind')]
        steps+=hours('NATURE',5)+[L.peek('nature_frequency')]
        # Dawn permits bear/cougar; a second successful roll replaces the bear.
        steps+=poke('s_hour',5)+[L.poke('fauna_rng',4)]
        steps+=hours('REST',1)+[L.peek('animal_kind'),'peek:2000:8192',
                              L.peek('s_elap',5),L.peek('scene_minutes')]
        steps+=['key:STATUS\r','wait:1',L.until('wait_key',6000),'key: ','wait:1',idle,
                L.peek('nature_frequency'),L.peek('animal_kind'),'peek:2000:8192']
        steps+=hours('NATURE',101)+[L.peek('nature_frequency'),'peek:0400:1024']
        steps+=hours('NATURE',100)+[L.peek('nature_frequency')]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    assert r.dumps[0:4]==[b'\0',b'\0',b'\5',b'\0'],r.dumps[0:4]
    expected=scene_ref.render(m,12*256,8*256,140)
    assert view_rows(r.dumps[4])==expected
    assert abs(fp(r.dumps[5])-2)<1e-6 and r.dumps[6]==b'\0'
    assert r.dumps[7:9]==[b'\5',b'\0'],r.dumps[7:9]
    # STATUS borrows HGR for the goal calculation. Compare displayed rows
    # and the retained terrain cache; unused bytes can contain SIM scratch.
    before = [r.dumps[4][a2test.hgr_offset(y):a2test.hgr_offset(y)+40] for y in range(176)]
    after = [r.dumps[9][a2test.hgr_offset(y):a2test.hgr_offset(y)+40] for y in range(176)]
    assert before==after, ('STATUS return changed HGR/header/cache rows',
                          [y for y,(a,b) in enumerate(zip(before,after)) if a!=b])
    assert r.dumps[10]==b'\5' and 'FREQUENCY MUST' in '\n'.join(text_screen(r.dumps[11]))
    assert r.dumps[12]==b'\x64'
    print('  NATURE settings persist; original REST skips encounter draws and STATUS preserves the view OK')
    print('Fauna: OK')


if __name__=='__main__': main()
