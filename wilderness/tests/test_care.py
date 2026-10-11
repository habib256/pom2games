#!/usr/bin/env python3
"""Medical command gates, signed dose counters and real command persistence.

--original executes the local Journey routines on Apple II ROM. Only their
message/clock/disk dispatch endpoints are replaced by returns in the probes.
"""
import sys
from common import HERE, L, DISK, a2test, fp, text_screen
from test_thermal import call
from test_medical import byte_pokes
from test_weather_cycle import probe_disk

IDLE = L.until('idle',20000)
REFUSALS = ('SHIELD HEAD','SUCK EYES','EAT OXYGEN','DRINK SUNSCREEN','EAT SOAP')


def commands():
    cases = [('SHIELD EYES',9,0),('LOWER HEAD',3,0),('SUCK VENOM',22,15),
             ('EAT FLAGYL',16,0),('DRINK QUININE',19,0),('EAT SALT TABLETS',17,0),
             ('USE SUNSCREEN',13,0),('USE REPELLENT',14,0)]
    steps = [IDLE,L.poke('nature_frequency',0),L.poke('injury_active',1,7)]
    for item in (44,45,47,48,50):
        steps += [L.poke('it_place',2,item),L.poke('it_pack_lo',2,item),L.poke('it_pack_hi',0,item)]
    for command,_,_ in cases:
        steps += byte_pokes(L['medical_actions'],bytes(30))
        steps += [f'key:{command}\r','wait:1',IDLE,L.peek('medical_actions',30),L.peek('s_elap',5)]
    steps += ['key:USE SUNSCREEN\r','wait:1',IDLE,L.peek('it_pack_lo',76),L.peek('it_pack_hi',76)]
    # Failed operations leave every action, counter and inventory field intact.
    for command in REFUSALS:
        steps += [L.peek('medical_actions',30),L.peek('s_elap',5),L.peek('it_pack_lo',76),
                  f'key:{command}\r','wait:1',IDLE,
                  L.peek('medical_actions',30),L.peek('s_elap',5),L.peek('it_pack_lo',76)]
    steps += [L.poke('injury_active',0,7),L.peek('medical_actions',30),
              'key:SUCK VENOM\r','wait:1',IDLE,L.peek('medical_actions',30),L.peek('s_elap',5)]
    steps += ['key:INVENTORY\r','wait:1',L.until('inventory_key',12000),
              'key:3','wait:1',L.until('inventory_key',12000),
              'key:N','wait:1',L.until('inventory_key',12000),'peek:0400:1024']
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    elapsed=0
    for i,(_,selector,minutes) in enumerate(cases):
        assert r.mem(L['medical_actions'],30,i)[selector] == 1,cases[i]
        elapsed += minutes/60
        assert abs(fp(r.mem(L['s_elap'],5,i))-elapsed)<1e-7,cases[i]
    stocks=r.mem(L['it_pack_lo'],76)
    assert stocks[44]==0 and all(stocks[n]==1 for n in (45,47,48,50)),stocks[41:52]
    assert r.mem(L['it_pack_hi'],76)==bytes(76)
    for i in range(len(REFUSALS)):
        offset=len(cases)+2*i
        assert r.mem(L['medical_actions'],30,offset)==r.mem(L['medical_actions'],30,offset+1)
        assert r.mem(L['s_elap'],5,offset)==r.mem(L['s_elap'],5,offset+1)
        assert r.mem(L['it_pack_lo'],76,1+2*i)==r.mem(L['it_pack_lo'],76,2+2*i)
    last=len(cases)+2*len(REFUSALS)
    assert r.mem(L['medical_actions'],30,last)==r.mem(L['medical_actions'],30,last+1)
    assert abs(fp(r.mem(L['s_elap'],5,last))-elapsed)<1e-7
    screen='\n'.join(text_screen(r.mem(0x400,1024)))
    assert 'USES' in screen,screen
    print('Medical commands, oral medicines, doses, refusals and inventory quantities OK',flush=True)


def doses(original):
    cases=[(item,stock) for item in (41,42,44,45,46,47,48,49,50,51)
           for stock in (0,1,2,255,256,257,32767,32768,65535)]
    done=f'until:{L["idle"]+3:04X}:6000'
    steps=[IDLE]+call(['do_medical'])+[done,IDLE]+call(['module_care_dose'])
    for item,stock in cases:
        # Patch only the driver's LDX; the routine itself is unchanged.
        steps += byte_pokes(L['idle'],bytes((0xa2,item,0x20,L['module_care_dose']&255,
                            L['module_care_dose']>>8,0x4c,L['idle']&255,L['idle']>>8)))
        steps += [L.poke('it_pack_lo',stock,item),L.poke('it_pack_hi',stock>>8,item),
                  f'until:{L["idle"]+5:04X}:6000',L.peek('it_pack_lo',76),L.peek('it_pack_hi',76),
                  L.peek('care_consumed'),IDLE]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    actual=[]
    for i,(item,stock) in enumerate(cases):
        value=r.mem(L['it_pack_lo'],76,i)[item]+256*r.mem(L['it_pack_hi'],76,i)[item]
        consumed=r.mem(L['care_consumed'],1,i)[0]
        expected=0<stock<32768
        assert (value,consumed)==(stock-int(expected),int(expected)),(cases[i],value,consumed)
        actual.append((value,consumed))
    if original:
        module=bytearray((HERE/'build/re_surv/m0E2.bin').read_bytes())
        module[0x631]=0x60 # return at disk dispatch, after the actual dose operation
        disk=probe_disk(HERE/'build/re_care_doses',module,
                        bytes.fromhex('20 C7 5D 4C 00 08'),[('QUIET',b'\x60',0x4D2A)])
        steps=['until:0800:20000']
        for item,stock in cases:
            steps+=byte_pokes(5,bytes([item]))+byte_pokes(0x19,b'\1')
            steps+=byte_pokes(0xFA,stock.to_bytes(2,'little'))
            steps+=['until:0803:1000','peek:00FA:2','peek:0019:1','until:0800:1000']
        native=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
        expected=[(int.from_bytes(native.mem(0xFA,2,i),'little'),native.mem(0x19,1,i)[0]) for i in range(len(cases))]
        assert actual==expected,[(c,a,b) for c,a,b in zip(cases,actual,expected) if a!=b]
    print(f'{len(cases)} signed medicine dose cases OK'+(' (native ROM)' if original else ''),flush=True)


def oxygen_last_dose():
    steps=[IDLE,L.poke('nature_frequency',0),L.poke('px',10,1),L.poke('py',10,1),
           'poke:74AA:00','poke:700A:B4',L.poke('it_place',2,49),
           L.poke('it_pack_lo',1,49),L.poke('it_pack_hi',0,49)]
    for command in ('USE OXYGEN','REST 30 MIN','USE OXYGEN','REST 30 MIN'):
        steps += [f'key:{command}\r','wait:1',IDLE,L.peek('oxygen_active'),L.peek('it_pack_lo',76),
                  L.peek('altitude_percent'),L.peek('s_health',5),L.peek('s_elap',5)]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    assert [r.mem(L['oxygen_active'],1,i)[0] for i in range(4)]==[1,1,0,0]
    assert all(r.mem(L['it_pack_lo'],76,i)[49]==0 for i in range(4))
    assert r.mem(L['altitude_percent'],1,1)==b'\x64'
    assert r.mem(L['altitude_percent'],1,3)==b'\x35'
    assert fp(r.mem(L['s_health'],5,3))<fp(r.mem(L['s_health'],5,1))
    assert abs(fp(r.mem(L['s_elap'],5,3))-1.5)<1e-7
    print('Last oxygen dose protects; empty reuse restores altitude loss without wrapping stock OK',flush=True)


def native_gates():
    sys.path.insert(0,str(HERE/'tools'))
    from smalldos import Disk
    journey=Disk((HERE/'build/JOURNEY.dsk').read_bytes());journey.flip=True
    # LOWER HEAD and SHIELD EYES are immediate prerequisites, not timed actions.
    disk=probe_disk(HERE/'build/re_care_hands',journey.run(0x15,0xA,1),
                    bytes.fromhex('20 00 58 4C 00 08'),
                    [('DONE',b'\x60',0x4D03),('QUIET',b'\x60',0x4D21)])
    cases=[(verb,noun) for verb in (29,30) for noun in (158,160,163)]
    steps=['until:0800:20000']
    for verb,noun in cases:
        steps+=byte_pokes(3,bytes([verb,0,noun,15]))+byte_pokes(0x4B41,bytes(2))
        steps+=['until:0803:1000','peek:4B41:2','until:0800:1000']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    for i,(verb,noun) in enumerate(cases):
        expected=bytes([1,4 if verb==29 else 10]) if noun==(163 if verb==29 else 160) else bytes(2)
        assert r.mem(0x4B41,2,i)==expected,(cases[i],r.mem(0x4B41,2,i).hex())
    disk=probe_disk(HERE/'build/re_care_suck',journey.run(0x12,8,6),
                    bytes.fromhex('20 00 58 4C 00 08'),
                    [('DONE',b'\x60',0x4D00),('QUIET',b'\x60',0x4D21)])
    cases=[(noun,bitten) for noun in (158,160,161) for bitten in (0,1)]
    steps=['until:0800:20000']
    for noun,bitten in cases:
        steps+=byte_pokes(3,bytes([32,0,noun,15]))+byte_pokes(0x1E,b'\x20')
        steps+=byte_pokes(0x47FB,bytes([bitten]))+byte_pokes(0x4B41,bytes(2))+byte_pokes(0x4BC6,bytes(2))
        steps+=['until:0803:1000','peek:4B41:2','peek:4BC6:2','until:0800:1000']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    for i,(noun,bitten) in enumerate(cases):
        accepted=noun==161 and bitten==1
        assert r.mem(0x4B41,2,i)==(bytes([1,23]) if accepted else bytes(2))
        assert int.from_bytes(r.mem(0x4BC6,2,i),'little')==(15 if accepted else 0)
    print('12 original LOWER HEAD / SHIELD EYES / SUCK VENOM gates OK (native ROM)',flush=True)

    disk=probe_disk(HERE/'build/re_care_oral',journey.run(0x12,8,6),
                    bytes.fromhex('20 00 58 4C 00 08'),
                    [('DONE',b'\x60',0x4D00),('QUIET',b'\x60',0x4D21)])
    cases=[(verb,item) for verb in (10,12) for item in range(41,52)]
    steps=['until:0800:20000']
    for verb,item in cases:
        steps+=byte_pokes(3,bytes([verb,0,item,5]))+byte_pokes(0x1E,b'\x0a')
        steps+=byte_pokes(0x4B41,bytes(2))+byte_pokes(0x4BC6,bytes(2))
        steps+=['until:0803:1000','peek:4B41:2','peek:4BC6:2','until:0800:1000']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    for i,(verb,item) in enumerate(cases):
        accepted=item in (47,48,50)
        assert r.mem(0x4B41,2,i)==(bytes([1,item-30]) if accepted else bytes(2)),cases[i]
        assert r.mem(0x4BC6,2,i)==bytes(2),cases[i]
    print('22 original oral medicine / oxygen / soap / equipment gates OK (native ROM)',flush=True)


def empty_compatibility():
    """The original retains the selected prerequisite even when W8 is zero.

    Exercise all four native stages, including the inventory transaction,
    instead of inferring this behavior from the care matrix alone.
    """
    sys.path.insert(0,str(HERE/'tools'))
    from smalldos import Disk
    journey=Disk((HERE/'build/JOURNEY.dsk').read_bytes());journey.flip=True
    modules=[journey.run(0x11,0,7),journey.run(0xE,2,8),
             journey.run(0xE,0xA,6),journey.run(6,0,2)]
    disk=probe_disk(HERE/'build/re_care_empty',modules[0],
                    bytes.fromhex('20 00 58 4C 00 08'),
                    [(name,b'\x60',address) for name,address in
                     [('CLOCK',0x4D00),('NEXT',0x4D03),('DONE',0x4D06),
                      ('DISK',0x03DB),('MSG',0x4D21),('MSG1',0x4D24),
                      ('MSG2',0x4D27),('MSG3',0x4D2A)]])
    cases=[(item,count) for item in (44,47,49) for count in (0,1)]
    steps=['until:0800:20000']
    for item,count in cases:
        steps+=byte_pokes(3,bytes([2,0,item,5]))+byte_pokes(0x1E,b'\0')
        steps+=byte_pokes(0x4344+2*item,count.to_bytes(2,'little'))
        steps+=byte_pokes(0x404C+item,b'\2')+byte_pokes(0x4098+item,b'\0')
        steps+=byte_pokes(0x4B41,bytes(4))+byte_pokes(0x4ABC,bytes(30))
        # Generous capacities isolate the use/dose pipeline from item moves.
        steps+=byte_pokes(0x4BEE,(10000).to_bytes(2,'little')*3)
        steps+=byte_pokes(0x4BF8,(10000).to_bytes(2,'little'))
        for module in modules:
            steps+=byte_pokes(0x5800,module)+['until:0803:4000','until:0800:1000']
        steps += [f'peek:{0x4344+2*item:04X}:2','peek:4ABC:30','peek:40C9:1']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    native=[(int.from_bytes(r.mem(0x4344+2*item,2,i%2),'little'),
             r.mem(0x4ABC,30,i)[item-31],r.mem(0x40C9,1,i)[0] if item==49 else None)
            for i,(item,_) in enumerate(cases)]
    steps=[IDLE,L.poke('nature_frequency',0)]
    for item,count in cases:
        steps+=byte_pokes(L['medical_actions'],bytes(30))
        steps += [L.poke('it_place',2,item),L.poke('it_pack_lo',count,item),L.poke('it_pack_hi',0,item),
                  f'key:USE { {44:"SUNSCREEN",47:"FLAGYL",49:"OXYGEN"}[item]}\r','wait:1',IDLE,
                  L.peek('it_pack_lo',76),L.peek('medical_actions',30),L.peek('oxygen_active')]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    actual=[(r.mem(L['it_pack_lo'],76,i)[item],r.mem(L['medical_actions'],30,i)[item-31],
             r.mem(L['oxygen_active'],1,i)[0] if item==49 else None)
            for i,(item,_) in enumerate(cases)]
    assert actual==native, (actual,native)
    assert native==[(0,1,None)]*4+[(0,1,0),(0,1,1)],native
    print('6 zero/last-dose stock, care and oxygen cases match all four native stages (native ROM)',flush=True)


if __name__=='__main__':
    original='--original' in sys.argv
    commands()
    doses(original)
    oxygen_last_dose()
    if original:
        native_gates()
        empty_compatibility()
