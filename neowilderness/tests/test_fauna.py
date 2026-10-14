#!/usr/bin/env python3
"""Native filter fixtures, probability arithmetic and playable NATURE rolls.

Lot 7: the same fixtures for the probed records of the five other regions
(build/regions/fauna.json, loaded through the start menu), the fourth
species (module 23) and byte 29 (never in water) in the production scan,
and New Guinea's trinkets rule.
"""
import math, re, tempfile
from common import HERE,L,DISK,a2test,disk_with,fp,text_screen,dhgr_view,dhgr_scene,mood_name,menu_keys
from test_thermal import call,poke
from test_sites import command,hours
from fauna_cases import cases, region_cases, region_records
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
        for text,age in (('WAIT 29 MIN',29),('EAT CHEESE 1 OZ',31),('SLEEP 28 MIN',59)):
            command(s,text)
            assert s.step(L.peek('animal_kind')).data==b'\6',text
            assert s.step(L.peek('animal_age')).data==bytes((age,)),text
            assert s.step(L.peek('fauna_rng')).data==rng, 'stationary activity drew an encounter'
        from test_animal_reactions import seed_for, rng as reaction_rng
        seed=seed_for((0,6),(0,52))
        s.step(L.poke('fauna_rng',seed))
        command(s,'REST 1 MIN')
        assert s.step(L.peek('animal_kind')).data==b'\6'
        assert s.step(L.peek('animal_age')).data==b'\0'
        assert s.step(L.peek('fauna_rng')).data==bytes((reaction_rng(reaction_rng(seed)),))
        assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-60)<1e-6
        assert s.step(L.peek('fauna_alert')).data==b'\0'
        assert s.step(L.peek('injury_active')).data==b'\1'
    print('  WAIT, meal and sleep age the animal without encounter rolls; native-inspired reaction at exactly 60 minutes OK')



# The production scan of TRAVEL (src/travel.s resource_scan), entered at the
# phase of one species with fauna_env poked: it stops where the six filters
# accept the species (resource_eligible) or where the scan moves on
# (resource_next), or where the threshold of the roll is ready
# (resource_rolled). After the first stop, those addresses are patched with
# JMP idle (TRAVEL stays in the window: overlay_load finds it current), and
# the idle loop holds the probe: LDA #12, JSR overlay_load, LDA #phase,
# STA resource_phase, JMP resource_scan_species (stack balanced).
ANIMAL_K = fp(bytes((0x70,0x27,0xC5,0xAC,0x48)))   # travel.s resource_animal_k


def scan_probe(region, cases, stops):
    """cases: [(species, env, level, minutes)]; returns [(pc, threshold)].
    A session: a2test.run would insert a frame before every stop."""
    idle = L.until('idle',20000)
    done = f'until:{L["idle"]+3:04X}:6000'
    I, ol, ph, sc = L['idle'], L['overlay_load'], L['resource_phase'], L['resource_scan_species']
    probe = bytes((0xA9,12,0x20,ol&255,ol>>8,0xA9,0,0x8D,ph&255,ph>>8,0x4C,sc&255,sc>>8))
    targets = ','.join(f'{L[name]:04X}' for name in stops)
    out = []
    with a2test.Session(DISK,timeout=1800,menu=not region) as s:
        steps = (menu_keys(str(region)) if region else []) + [idle] + call(['env_day']) + [done,idle]
        steps += [f'poke:{I+i:04X}:{b:02X}' for i,b in enumerate(probe)]
        for step in steps:
            s.step(step)
        for k,(species,env,level,minutes) in enumerate(cases):
            if k:       # leave the trap (a stop at the current PC returns at once)
                s.step(f'until:{I:04X}:100')
            for step in ([f'poke:{I+6:04X}:{7+species:02X}',f'poke:7016:{level:02X}',
                          L.poke('scene_minutes',minutes)]
                         + [L.poke('fauna_env',v,i) for i,v in enumerate(env)]):
                s.step(step)
            pc = int(re.search(r'PC=([0-9A-F]{4})',s.step(f'until:{targets}:6000').out).group(1),16)
            out.append((pc,fp(s.step(L.peek('resource_threshold',5)).data)))
            if k == 0:
                for name in stops:
                    for i,b in enumerate((0x4C,I&255,I>>8)):
                        s.step(f'poke:{L[name]+i:04X}:{b:02X}')
    return out


def production_filters(region, fixtures):
    """Each fixture accepted or rejected by the production filters."""
    got = scan_probe(region,[(species,env,4,60) for species,env,_ in fixtures],
                     ('resource_eligible','resource_next'))
    for fixture,(pc,_) in zip(fixtures,got):
        assert pc in (L['resource_eligible'],L['resource_next']),(region,fixture,hex(pc))
        assert (pc==L['resource_eligible'])==fixture[2],(region,fixture,hex(pc))


def production_probabilities(region, fixtures, rates, levels, minutes_list):
    """threshold = sqrt(level) * minutes * 1e-5 * rate (legacy level 0 -> 4)
    on an environment each species accepts."""
    cases, expected = [], []
    for species,rate in enumerate(rates):
        if not rate:
            continue
        env = next(env for k,env,ok in fixtures if k==species and ok)
        for level in levels:
            for minutes in minutes_list:
                cases.append((species,env,level,minutes))
                expected.append(math.sqrt(level or 4)*minutes*ANIMAL_K*rate)
    got = scan_probe(region,cases,('resource_rolled','resource_next'))
    for case,want,(pc,threshold) in zip(cases,expected,got):
        assert pc==L['resource_rolled'],(region,case,hex(pc))
        assert abs(threshold-want)<max(1e-7,want*1e-8),(region,case,want,threshold)
    return len(cases)


def region_filters(region):
    """The production filters and probability on the loaded region's table."""
    fixtures = region_cases(region)
    production_filters(region,fixtures)
    records = region_records(region)['species']
    count = production_probabilities(region,fixtures,[x['rate'] for x in records],(1,10),(1,255))
    names = ', '.join(f"{x['name']} {x['rate']}" for x in records)
    print(f'  region {region}: {len(fixtures)} filter fixtures and {count} probabilities '
          f'({names}{", byte 29" if any(x["water_gate"] for x in records) else ""}) on the production scan OK',flush=True)


def region_scan(region, cell, expected, tries=12):
    """The production scan (TRAVEL resource_scan via module_fauna) on a 3x3
    patch of `cell` at 02:00, level 10, 255 minutes: every accepted
    encounter must be `expected` (kind, or 0 for none)."""
    idle = L.until('idle',20000)
    done = f'until:{L["idle"]+3:04X}:6000'
    steps = menu_keys(str(region)) + [idle] + call(['env_day']) + [done,idle] + call(['module_fauna'])
    steps += poke('s_date',.5)+poke('s_hour',2)
    steps += [L.poke('px',0),L.poke('px',50,1),L.poke('py',0),L.poke('py',40,1),
              'poke:700A:00','poke:7016:0A',L.poke('nature_frequency',1)]
    for y in range(39,42):
        for x in range(49,52):
            steps += [f'poke:{0x7040+y*112+x:04X}:{cell:02X}']
    for _ in range(tries):
        steps += [L.poke('scene_minutes',255),L.poke('animal_kind',0),done,L.peek('animal_kind'),
                  L.peek('fauna_env',6),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900,menu=False)
    kinds=[r.mem(L['animal_kind'],1,k)[0] for k in range(tries)]
    env=r.mem(L['fauna_env'],6,0)
    assert env[1:4]==bytes((2,40 if cell&128 else 10,cell&127)),(region,env.hex())
    assert set(kinds) <= {0,expected} and (expected==0 or expected in kinds),(region,kinds)
    return kinds


def trinkets():
    """New Guinea: with TRINKETS carried, the cannibal's injury needs a second
    roll below .02 (6/256); Burma's tiger has no such rule."""
    from test_animal_reactions import seed_for, prepare, injury
    from test_input import IDLE, command as play, screen
    spared, unlucky = seed_for((0,129),(6,256)), seed_for((0,129),(0,6))
    with a2test.Session(DISK,timeout=900,menu=False) as s:
        for step in menu_keys('4'):
            s.step(step)
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        results=[]
        for seed,carried in ((spared,0),(spared,1),(unlucky,1)):
            prepare(s,6,seed)
            s.step(L.poke('it_place',2 if carried else 0,74))
            play(s,'IGNORE CANNIBAL')
            hurt=injury(s,6)
            results.append(hurt)
            if hurt:
                assert 'THE CANNIBAL INJURES YOU' in screen(s),screen(s)
        assert results==[True,False,True],results
    tiger=seed_for((0,21),(6,256))
    with a2test.Session(DISK,timeout=900,menu=False) as s:
        for step in menu_keys('3'):
            s.step(step)
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        prepare(s,6,tiger)
        s.step(L.poke('it_place',2,74))
        play(s,'IGNORE TIGER')
        assert injury(s,6) and 'THE TIGER INJURES YOU' in screen(s),screen(s)
    print('  New Guinea trinkets: cannibal spared with TRINKETS unless RND < .02; Burma tiger unaffected OK',flush=True)


def regions():
    for region in (1,3,4,5,6):
        region_filters(region)
    # Fourth species (module 23 sprite, kind 9): a lake at 1,000 ft at night
    # in Burma suits only the python; in Bolivia only the anaconda.
    region_scan(3,128+10,9)
    region_scan(5,128+20,9)
    # Byte 29: a British Columbia lake would suit the moose (terrain 30 +- 12)
    # but for its water gate; neither grizzly nor wolf accepts water.
    region_scan(1,128+10,0)
    print('  production scan: Burma python and Bolivia anaconda (kind 9), no British Columbia moose in water OK')
    trinkets()


def main():
    stationary_lifetime()
    idle = L.until('idle',20000)
    done = f'until:{L["idle"]+3:04X}:6000'
    fixtures = cases()
    production_filters(None,fixtures)
    print(f'  {len(fixtures)} original filter fixtures: all species and six criteria on the production scan OK')
    count = production_probabilities(None,fixtures,(80,40,100),(0,1,4,10),(1,60,255))
    print(f'  {count} probability cases: elapsed minutes and difficulty (legacy 0 -> 4) on the production scan OK')

    # Derive the environment from real map cells, including diagonal relief,
    # water and the legacy header, then exercise each species' seeded roll.
    steps=[idle]+call(['env_day'])+[done,idle]+call(['module_fauna'])
    roll_cases=[(.5,6,10,10,4,31,1,7),   # cougar replaces bear
                (0,6,10,10,4,31,1,7),   # winter excludes bear and snake
                (.5,12,10,10,4,31,1,8), # midday excludes bear and cougar
                (0,12,10,10,4,31,1,0),  # no species matches
                (.5,12,138,10,4,31,1,0),# water excludes all three
                (.5,12,80,80,4,31,1,0), # too high
                (.5,12,10,30,4,31,1,0),# diagonal slope too steep
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
                value=diagonal if (x,y)==(49,39) else cell
                steps += [f'poke:{0x7040+y*112+x:04X}:{value:02X}']
        steps += [done,L.peek('animal_kind'),L.peek('fauna_env',6),L.peek('scene_minutes'),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    for k,(_,hour,cell,diagonal,level,climate,frequency,kind) in enumerate(roll_cases):
        animal=r.mem(L['animal_kind'],1,k)
        env=r.mem(L['fauna_env'],6,k)
        remaining=r.mem(L['scene_minutes'],1,k)
        # Production discovery now uses the native shared random stream.
        # The former fauna_rng=4 animal expectation belongs to the retired
        # byte generator; validate the map-derived eligibility here, and
        # compare the coupled stream in test_resource_random/adventure.
        assert remaining==b'\0' and animal[0] in (0,6,7,8),(k,animal,remaining)
        if kind == 0:
            assert animal == b'\0',(k,animal)
        assert env[1:]==bytes((hour,40 if cell&128 else 10,24+(cell&127),
                             math.floor(4 * math.degrees(math.atan(abs(diagonal-(cell&127))/24)) + .5) & 255,climate or 31)),(k,env)
    print('  map-derived environment, diagonal slope and excluded encounters OK')

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
        steps+=hours('REST',1)+[L.peek('animal_kind'),'peek:2000:8192',L.peek('sky_mood'),
                              L.peek('s_elap',5),L.peek('scene_minutes')]
        steps+=['key:STATUS\r','wait:1',L.until('wait_key',6000),'key: ','wait:1',idle,
                L.peek('nature_frequency'),L.peek('animal_kind'),'peek:2000:8192']
        steps+=hours('NATURE',101)+[L.peek('nature_frequency'),'peek:0400:1024']
        steps+=hours('NATURE',100)+[L.peek('nature_frequency')]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    assert r.dumps[0:4]==[b'\0',b'\0',b'\5',b'\0'],r.dumps[0:4]
    expected=dhgr_scene(m,12*256,8*256,140,r.dumps[5],forest=True)
    assert dhgr_view(r.dumps[4])==expected,mood_name(r.dumps[5])
    assert abs(fp(r.dumps[6])-2)<1e-6 and r.dumps[7]==b'\0'
    assert r.dumps[8:10]==[b'\5',b'\0'],r.dumps[8:10]
    # STATUS borrows HGR for the goal calculation. Compare displayed rows
    # and the retained terrain cache; unused bytes can contain SIM scratch.
    before = [bank[a2test.hgr_offset(y):a2test.hgr_offset(y)+40] for bank in (r.dumps[4][:8192], r.dumps[4][8192:]) for y in range(176)]
    after = [bank[a2test.hgr_offset(y):a2test.hgr_offset(y)+40] for bank in (r.dumps[10][:8192], r.dumps[10][8192:]) for y in range(176)]
    assert before==after, ('STATUS return changed DHGR/header/cache rows',
                          [y for y,(a,b) in enumerate(zip(before,after)) if a!=b])
    assert r.dumps[11]==b'\5' and 'FREQUENCY MUST' in '\n'.join(text_screen(r.dumps[12]))
    assert r.dumps[13]==b'\x64'
    print('  NATURE settings persist; original REST skips encounter draws and STATUS preserves the view OK')
    regions()
    print('Fauna: OK')


if __name__=='__main__': main()
