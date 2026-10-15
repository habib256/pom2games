#!/usr/bin/env python3
"""Disease progression and care prerequisites against native Journey routines.

The ordinary test checks gameplay, persistence and boundary conditions.
--original also runs T0B/S0D and T06/S00 on ROM, using only local originals.
"""
import sys
from common import HERE, L, DISK, a2test, fp, text_screen
from gendata import fp as encode
from test_thermal import call, poke
from test_weather_cycle import probe_disk

FLOORS = [75,70,40,20,75,75,60,20,50,70,50,85,40,1,100]
INCUBATION = [0,0,0,0,8,3,6,3,4,24,6,24,240,0,1]
UNTREATED = [240,1008,1344,336,96,24,336,168,336,30000,120,336,1008,100,3]
TREATED = [60,672,672,72,48,8,48,24,48,24,48,48,672,100,2]


def byte_pokes(address, data):
    return [f'poke:{address+i:04X}:{b:02X}' for i,b in enumerate(data)]


def progression(original):
    cases = []
    for i,t in enumerate(INCUBATION):
        for treated in (0,1):
            duration = (TREATED if treated else UNTREATED)[i]
            for h in sorted(set((0,t/2,t,t+.5,t+duration,t+duration+.5))):
                cases.append((i,treated,h))
    idle = L.until('idle',20000)
    done = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle]+call(['injury_health'])+[done,idle]+call(['module_injury_health'])
    for i,treated,h in cases:
        steps += byte_pokes(L['injury_active'],bytes(15))
        steps += byte_pokes(L['injury_treated'],bytes(15))
        steps += [L.poke('injury_active',1,i),L.poke('injury_treated',treated,i)]
        steps += byte_pokes(L['injury_since']+5*i,encode(0))+poke('s_elap',h)
        steps += [done,L.peek('injury_percent',15),L.peek('injury_active',15),L.peek('injury_treated',15),idle]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    actual = [(r.mem(L['injury_percent'],15,k)[i],r.mem(L['injury_active'],15,k)[i],
               r.mem(L['injury_treated'],15,k)[i]) for k,(i,_,_) in enumerate(cases)]
    for (i,treated,h),(percent,active,care) in zip(cases,actual):
        assert 0 <= percent <= 100
        duration = (TREATED if treated else UNTREATED)[i]
        healed = h >= INCUBATION[i]+duration
        assert active == (not healed) and care == (treated if not healed else 0)
        if healed: assert percent == 100
        if h == 0 and i < 4: assert percent == FLOORS[i]
    if original:
        module = (HERE/'build/re_surv/m0BD.bin').read_bytes()
        # Only the message entry is neutralized; the health routine is intact.
        disk = probe_disk(HERE/'build/re_medical_health',module,
                          bytes.fromhex('20 50 58 4C 00 08'), [('QUIET',b'\x60',0x4D2A)])
        steps = ['until:0800:20000']
        for i,treated,h in cases:
            steps += byte_pokes(0x47F4,bytes(15))+byte_pokes(0x47E5,bytes(15))
            steps += byte_pokes(0x4821,bytes([100])*15)
            steps += byte_pokes(0x47F4+i,b'\x01')+byte_pokes(0x47E5+i,bytes([treated]))
            steps += byte_pokes(0x49CD+5*i,encode(h))
            steps += ['until:0803:1000',f'peek:{0x4821+i:04X}:1',
                      f'peek:{0x47F4+i:04X}:1',f'peek:{0x47E5+i:04X}:1','until:0800:1000']
        native = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        for k,((i,treated,h),value) in enumerate(zip(cases,actual)):
            expected = tuple(native.mem(address+i,1,sum(c[0]==i for c in cases[:k]))[0]
                             for address in (0x4821,0x47F4,0x47E5))
            assert value == expected, ((i,treated,h),value,expected)
    print(f'{len(cases)} injury/disease progression cases OK'+(' (native ROM)' if original else ''))


def treatment(original):
    # Exhaustive single actions plus combinations needed for shock/sunburn.
    cases = [(active,(selector,)) for active in (0,1) for selector in range(1,31)]
    cases += [(1,actions) for actions in ((4,5),(4,6),(5,6),(4,5,6),(6,9),(1,2))]
    idle = L.until('idle',20000); done = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle]+call(['injury_health'])+[done,idle]+call(['module_medical_apply'])
    for active,actions in cases:
        flags = bytes(int(i+1 in actions) for i in range(30))
        steps += byte_pokes(L['medical_actions'],flags)
        steps += byte_pokes(L['injury_active'],bytes([active])*15)
        steps += byte_pokes(L['injury_treated'],bytes(15))
        steps += byte_pokes(L['injury_prevented'],bytes(15))
        steps += [done,L.peek('injury_treated',13),L.peek('injury_prevented',13),idle]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    actual = [(r.mem(L['injury_treated'],13,k),r.mem(L['injury_prevented'],13,k)) for k in range(len(cases))]
    if original:
        # T06/S00 comes from Journey, not from an authored Python model.
        sys.path.insert(0,str(HERE/'tools'))
        from smalldos import Disk
        d = Disk((HERE/'build/JOURNEY.dsk').read_bytes()); d.flip=True
        disk = probe_disk(HERE/'build/re_medical_care',d.run(6,0,2),
                          bytes.fromhex('20 00 58 4C 00 08'), [('QUIET',b'\x60',0x4D06)])
        steps = ['until:0800:20000']
        for active,actions in cases:
            flags = bytes(int(i+1 in actions) for i in range(30))
            steps += byte_pokes(0x4ABC,flags)+byte_pokes(0x47F4,bytes([active])*15)
            steps += byte_pokes(0x47E5,bytes(15))+byte_pokes(0x47D6,bytes(15))
            steps += ['poke:4B41:01',f'poke:4B42:{actions[0]:02X}',
                      'until:0803:1000','peek:47E5:13','peek:47D6:13','until:0800:1000']
        native = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        for k,(case,value) in enumerate(zip(cases,actual)):
            expected = native.mem(0x47E5,13,k),native.mem(0x47D6,13,k)
            assert value == expected,(case,[v.hex() for v in value],[v.hex() for v in expected])
    # A lone warming action must not treat shock; its three prerequisites do.
    assert actual[cases.index((1,(4,5,6)))][0][3] == 1
    assert actual[cases.index((1,(4,5)))][0][3] == 0
    print(f'{len(cases)} prevention/treatment combinations OK'+(' (native ROM)' if original else ''))


def gameplay():
    idle = L.until('idle',20000)
    # Infection fixture: command, actual elapsed time, medical page and reload.
    steps = [idle,L.poke('injury_active',1,8),L.poke('it_place',2,41),
             'key:USE FIRSTAID KIT\r','wait:1',idle,L.peek('injury_treated',15),L.peek('s_elap',5),
             'key:STATUS\r',L.until('wait_key',6000),'key:M','wait:1',L.until('wait_key',6000),
             'peek:0400:1024','key:S','wait:1',L.until('wait_key',6000),
             'key:\x1b','wait:1',idle,L.peek('injury_treated',15),
             'key:STOP BLEEDING\r','wait:1',idle,L.peek('medical_actions',30),L.peek('s_elap',5)]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    assert r.mem(L['injury_treated'],15)[8] == 1
    assert r.mem(L['injury_treated'],15,1)[8] == 1
    assert abs(fp(r.mem(L['s_elap'],5))-.5)<1e-6
    assert abs(fp(r.mem(L['s_elap'],5,1))-1)<1e-6
    assert r.mem(L['medical_actions'],30)[0] == 1
    screen = '\n'.join(text_screen(r.mem(0x400,1024)))
    # STATUS's MEDICAL rows (15 October 2026): the mark after the percent,
    # XL's check mark for TREATED (docs/MENUS.md 9)
    assert 'INFECTION' in screen and '\u2713 TREATED' in screen and ' MEDICAL ' in screen
    assert __import__('re').search(r'INFECTION +\d+% +\u2713', screen), screen
    print('USE FIRSTAID, STOP BLEEDING, STATUS pagination and resident persistence OK')


def altitude(original):
    cases = [(height, health, oxygen) for height in (0,100,104,105,106,139,140,180,227,255)
             for health in (0,1,7.8666) for oxygen in (0,1)]
    idle = L.until('idle',20000); done = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle]+call(['injury_health'])+[done,idle]+call(['med_altitude'])
    # A single flat cell isolates absolute altitude from map generation.
    steps += [L.poke('px',10,1),L.poke('py',10,1),'poke:74AA:00',L.poke('it_place',2,49)]
    for height,health,oxygen in cases:
        steps += [f'poke:700A:{height:02X}',L.poke('oxygen_active',oxygen)]+poke('s_health',health)
        steps += poke('s_injury_factor',1)+[done,L.peek('altitude_percent'),idle]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    actual = [r.mem(L['altitude_percent'],1,k)[0] for k in range(len(cases))]
    assert all(value == 100 for case,value in zip(cases,actual) if case[2])
    if original:
        disk = probe_disk(HERE/'build/re_medical_altitude',(HERE/'build/re_surv/m0BD.bin').read_bytes(),
                          bytes.fromhex('20 50 58 4C 00 08'),[('QUIET',b'\x60',0x4D2A)])
        steps = ['until:0800:20000']
        for height,health,oxygen in cases:
            steps += byte_pokes(0x4C34,encode(health))
            steps += [f'poke:00D4:{height:02X}','poke:60A1:00',f'poke:40C9:{oxygen:02X}',
                      'until:0803:1000','peek:48AB:1','until:0800:1000']
        native = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        for k,(case,value) in enumerate(zip(cases,actual)):
            expected = native.mem(0x48AB,1,k)[0]
            assert value == expected,(case,value,expected)
    print(f'{len(cases)} altitude/health/oxygen cases OK'+(' (native ROM)' if original else ''))


def cadence(original):
    cases = [(i,age,health) for i in (0,5,6,7,8,9,10,11)
             for age in (0,.5,7.99,8,8.01) for health in (.99,1)]
    idle = L.until('idle',20000)
    steps = [idle]+call(['injury_health'])+[f'until:{L["idle"]+3:04X}:6000',idle]
    # Return A is the duration; no copy of the cap algorithm in the driver.
    driver = bytes((0xA9,240,0x20,L['module_medical_cap']&255,L['module_medical_cap']>>8,
                    0x8D,0x00,0x95,0x4C,L['idle']&255,L['idle']>>8))
    steps += byte_pokes(L['idle'],driver)
    for i,age,health in cases:
        steps += byte_pokes(L['injury_active'],bytes(15))+[L.poke('injury_active',1,i)]
        steps += byte_pokes(L['injury_since']+5*i,encode(0))+poke('s_elap',age)+poke('s_health',health)
        steps += [f'until:{L["idle"]+8:04X}:6000','peek:9500:1',idle]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    actual = [r.mem(0x9500,1,k)[0] for k in range(len(cases))]
    for (i,age,health),value in zip(cases,actual):
        assert value == (30 if health < 1 or 5 <= i <= 10 and age < 8 else 240)
    if original:
        disk = probe_disk(HERE/'build/re_medical_cadence',(HERE/'build/re_surv/m0BD.bin').read_bytes(),
                          bytes.fromhex('20 40 5C 4C 00 08'),[('QUIET',b'\x60',0x4D2A)])
        steps = ['until:0800:20000']
        for i,age,health in cases:
            steps += byte_pokes(0x47F4,bytes(15))+byte_pokes(0x47F4+i,b'\1')
            steps += byte_pokes(0x49CD+5*i,encode(age))+byte_pokes(0x4C34,encode(health))
            steps += byte_pokes(0x4C20,encode(1.65))+byte_pokes(0x4C25,encode(1.65))
            steps += byte_pokes(0x4C70,encode(98.6))+byte_pokes(0x5BC3,encode(98.6))
            steps += byte_pokes(0x4C75,encode(0))
            steps += ['poke:4BCC:F0','poke:4BCD:00','poke:48B2:64','poke:4B87:00',
                      'until:0803:1000','peek:4BCC:2','until:0800:1000']
        native = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        for k,(case,value) in enumerate(zip(cases,actual)):
            expected = int.from_bytes(native.mem(0x4BCC,2,k),'little')
            assert value == expected,(case,value,expected)
    print(f'{len(cases)} critical-health/illness cadence cases OK'+(' (native ROM)' if original else ''))


def clothing(original):
    from itertools import combinations
    gear = (1,2,3,4,5,7,8,9,11,12,14,15)
    outfits = [()] + [(i,) for i in gear] + list(combinations(gear,2))
    outfits += [(3,5,7),(3,5),(5,7),(3,7),(3,4,5,6,7,8,14)]
    idle = L.until('idle',20000); done = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle]+call(['injury_health'])+[done,idle]+call(['module_medical_clothing'])
    for outfit in outfits:
        steps += byte_pokes(L['it_place'],bytes([255])*76)
        steps += [L.poke('it_place',1,i) for i in outfit]
        steps += [done,L.peek('medical_actions',30),idle]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    actual = [(r.mem(L['medical_actions'],30,k)[7],r.mem(L['medical_actions'],30,k)[26])
              for k in range(len(outfits))]
    assert actual[0] == (0,0) and actual[-1] == (1,1)
    if original:
        # The real inventory routine delegates the final action flag to
        # the dispatcher. This adapter records that action without loading
        # another module over the routine under test.
        adapter = bytes.fromhex('AD 41 4B F0 09 AE 42 4B CA A9 01 9D BC 4A 60')
        disk = probe_disk(HERE/'build/re_medical_clothing',(HERE/'build/re_surv/m0EA.bin').read_bytes(),
                          bytes.fromhex('20 0A 5B 4C 00 08'),
                          [('ACTION',adapter,0x0700),('HANDOFF',bytes.fromhex('4C 00 07'),0x4D03),
                           ('QUIET',b'\x60',0x4D2A),('RESULT',b'\x60',0x4D21)])
        steps = ['until:0800:20000']
        for outfit in outfits:
            steps += byte_pokes(0x404C,bytes([255])*76)+byte_pokes(0x4098,bytes(76))
            steps += byte_pokes(0x4ABC,bytes(30))
            steps += [f'poke:{0x404C+i:04X}:01' for i in outfit]
            steps += ['poke:0005:2B','poke:0014:01','poke:4B4F:00','poke:4B41:00',
                      'until:0803:1000','peek:4ABC:30','until:0800:1000']
        native = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        for k,(outfit,value) in enumerate(zip(outfits,actual)):
            flags = native.mem(0x4ABC,30,k)
            expected = flags[7],flags[26]
            assert value == expected,(outfit,value,expected)
    print(f'{len(outfits)} clothing/prevention cases OK'+(' (native ROM)' if original else ''))


def oxygen_gameplay():
    idle = L.until('idle',20000)
    steps = [idle,L.poke('nature_frequency',0),L.poke('px',10,1),L.poke('py',10,1),
             'poke:74AA:00','poke:700A:B4',L.poke('it_place',2,49),
             'key:REST 30 MIN\r','wait:1',idle,L.peek('altitude_percent'),L.peek('s_health',5),
             'key:USE OXYGEN\r','wait:1',idle,L.peek('oxygen_active'),L.peek('s_elap',5),
             'key:REST 30 MIN\r','wait:1',idle,L.peek('altitude_percent'),L.peek('s_health',5)]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    assert r.mem(L['altitude_percent'],1)[0] == 53
    assert r.mem(L['oxygen_active'],1) == b'\1'
    assert abs(fp(r.mem(L['s_elap'],5))-.75) < 1e-6
    assert r.mem(L['altitude_percent'],1,1)[0] == 100
    assert fp(r.mem(L['s_health'],5,1)) > fp(r.mem(L['s_health'],5))
    print('USE OXYGEN spends 15 minutes and suppresses altitude loss at the next health update OK')


if __name__ == '__main__':
    original = '--original' in sys.argv
    progression(original)
    treatment(original)
    altitude(original)
    cadence(original)
    clothing(original)
    gameplay()
    oxygen_gameplay()
