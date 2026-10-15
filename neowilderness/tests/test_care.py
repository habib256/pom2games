#!/usr/bin/env python3
"""Medical command gates, signed dose counters and real command persistence;
lot 13: SPLINT, PRESSURE, WET/DRY/HANG, CUT BODY, automatic placement, the
original alerts, the forced sleep and the infection/malaria onsets.

--original executes the local Journey routines on Apple II ROM. Only their
message/clock/disk dispatch endpoints are replaced by returns in the probes.
"""
import sys
from common import HERE, L, DISK, a2test, fp, text_screen, result_text, result_rows
from test_thermal import call, poke
from test_medical import byte_pokes
from gendata import fp as encode
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


def numeric_refusals():
    def snapshot(s):
        fields = [('s_hour', L['s_t0'] + 5 - L['s_hour']),
                  ('medical_state', L['medical_state_end'] - L['medical_state'])]
        fields += [(name, 76) for name in
                   ('it_place', 'it_pack_lo', 'it_pack_hi', 'it_gnd_lo', 'it_gnd_hi')]
        return tuple(s.step(L.peek(name, size)).data for name, size in fields)
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        for item in (47, 48, 50):
            s.step(L.poke('it_place', 2, item))
            s.step(L.poke('it_pack_lo', 2, item))
            s.step(L.poke('it_pack_hi', 0, item))
        before = snapshot(s)
        for command in ('EAT FLAGYL 0 OZ', 'EAT FLAGYL 1 OZ',
                        'DRINK FLAGYL 1 H', 'EAT QUININE 30 MIN',
                        'DRINK SALT TABLETS 255 OZ'):
            s.step(f'key:{command}')
            s.step('press:\\r')
            s.step('wait:1')
            s.step(IDLE)
            assert snapshot(s) == before, command
            text = '\n'.join(text_screen(s.step('peek:0400:1024').data))
            assert 'OMIT THE NUMBER AND UNIT.' in text, (command, text)
        # A refusal must not contaminate the next valid, unqualified dose.
        s.step('key:EAT FLAGYL')
        s.step('press:\\r')
        s.step('wait:1')
        s.step(IDLE)
        assert s.step(L.peek('it_pack_lo', 1, 47)).data == b'\x01'
        assert fp(s.step(L.peek('s_elap', 5)).data) == 0
    print('Numeric medicine arguments: atomic refusal; next single dose remains usable', flush=True)


def doses(original):
    cases=[(item,stock) for item in (41,42,44,45,46,47,48,49,50,51)
           for stock in (0,1,2,255,256,257,32767,32768,65535)]
    done=f'until:{L["idle"]+3:04X}:6000'
    # do_medical loads WILDMVI; SHIELD (30) of no noun ends in MVI itself
    # (since lot 2 an unhandled USE goes on to the CAMP module).
    steps=[IDLE,L.poke('verb',30),L.poke('noun',0)]+call(['do_medical'])+[done,IDLE]+call(['module_care_dose'])
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


# ---------------------------------------------------------------------------
# Lot 13: care commands, alerts, forced sleep and disease onsets.

def journey_disk():
    sys.path.insert(0,str(HERE/'tools'))
    from smalldos import Disk
    journey=Disk((HERE/'build/JOURNEY.dsk').read_bytes())
    journey.flip=True
    return journey


# Message and loader exits of the native modules, captured instead of run:
# $4D21 (message, back to the parser) -> $FA, $4D2A (message, continue) -> $F9,
# $03DB (next module) -> X/Y in $FB/$FC, $4D00/$4D03 (clock, care) return.
LOT13_EXITS=[('MSG',bytes.fromhex('86 FA 60'),0x4D21),('MSG2',bytes.fromhex('86 F9 60'),0x4D2A),
             ('CLOCK',b'\x60',0x4D00),('DONE',b'\x60',0x4D03),
             ('DISK',bytes.fromhex('86 FB 84 FC 60'),0x03DB)]
LOT13_CLEAR=byte_pokes(0x4B41,bytes(2))+byte_pokes(0xF9,bytes(4))


def wet_dry_rule(verb,noun,family,front,terrain,shore):
    """T15/S0A as ported: (care pair, message, next module)."""
    if verb==13:
        return ((0,0),0,(0x12,8)) if family==1 else ((0,0),2,(0,0))
    if family!=15 or noun!=158:
        return ((0,0),2,(0,0))
    if front==2 or (terrain>=3 and shore in (0,3)):
        return ((1,9),11,(0,0))
    return ((0,0),0,(0x0F,0))     # water module, noun WATER


def native_wet_dry():
    """T15/S0A: WET BODY in rain/water, otherwise the water module; DRY/WARM
    reaches T12/S08 for clothing only."""
    module=journey_disk().run(0x15,0xA,1)
    disk=probe_disk(HERE/'build/re_care_wet',module,bytes.fromhex('20 00 58 4C 00 08'),LOT13_EXITS)
    cases=[(33,158,15,front,terrain,shore) for front in (0,1,2)
           for terrain,shore in ((0,0),(1,0),(2,0),(3,0),(3,1),(3,2),(3,3),(4,0),(4,1),(4,2))]
    cases+=[(33,160,15,2,4,0),(33,22,2,2,4,0)]
    cases+=[(13,noun,family,0,0,0) for noun,family in ((2,1),(21,1),(94,1),(23,3),(136,13),(158,15))]
    steps=['until:0800:20000']
    for verb,noun,family,front,terrain,shore in cases:
        steps+=byte_pokes(3,bytes([verb,0,noun,family]))+LOT13_CLEAR
        steps+=[f'poke:4B4D:{front:02X}',f'poke:4B56:{terrain:02X}',f'poke:4B6B:{shore:02X}',
                'poke:001E:00','until:0803:1000','peek:4B41:2','peek:00FA:3','peek:0005:2','peek:001E:1',
                'until:0800:1000']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    for i,case in enumerate(cases):
        care,msg,(track,sector)=wet_dry_rule(*case)
        got=(tuple(r.mem(0x4B41,2,i)),r.mem(0xFA,3,i)[0],tuple(r.mem(0xFA,3,i)[1:]))
        assert got==(care,msg,(track,sector)),(case,got)
        if case[0]==13 and track:
            assert r.mem(0x1E,1,i)[0]==13
        if case[0]==33 and track:
            assert tuple(r.mem(5,2,i))==(22,2),case     # WATER, family 2
    print(f'{len(cases)} original WET BODY / DRY gates OK (native ROM)',flush=True)


def dry_rule(wet,hypothermia,noun):
    if wet==0 and hypothermia>=86:
        return 2
    return 118 if noun>=95 else 117


def cut_rule(verb,family,noun,tools):
    """T12/S08 selector 14 (COOL, CUT): (care pair, message, next module)."""
    if family<4:
        return (0,0),18,0
    if family<10:
        return (0,0),(2 if verb==14 else 39),0
    if family!=15:
        return ((0,0),17,0) if verb==14 else ((0,0),0,0x0F)
    if noun!=158:
        return (0,0),2,0
    return ((1,7),0,0) if tools else ((0,0),25,0)


def hang_rule(tree,noun,wet,rain,sun,fire,place):
    """T12/S08 $58F9 for clothing: (message, $4B70, verb, $4B73)."""
    if not tree:
        return 16,wet,34,1
    if noun>=95:
        return 21,wet,34,1
    if wet==0 or rain>=2:
        return 49,wet,34,1
    dry=0 if sun==1 or fire==0 else wet
    return 0,dry,8,(0 if place==0 else 1)


def native_misc():
    """T12/S08: DRY/WARM messages, COOL/CUT BODY and HANG clothing."""
    module=journey_disk().run(0x12,8,6)
    disk=probe_disk(HERE/'build/re_care_misc',module,bytes.fromhex('20 00 58 4C 00 08'),LOT13_EXITS)
    dry=[(wet,hyp,noun) for wet in (0,1,2) for hyp in (0,85,86,100) for noun in (2,94,95,97)]
    cut=[(verb,family,noun,tools) for verb in (14,31)
         for family,noun in ((1,2),(3,23),(4,38),(9,64),(10,110),(11,76),(13,136),(15,158),(15,160))
         for tools in ((),(41,),(42,),(58,),(59,),(41,59))]
    hang=[(tree,noun,wet,rain,sun,fire,place) for tree in (0,1) for noun in (2,95)
          for wet in (0,1,2) for rain in (0,2) for sun in (0,1) for fire in (0,255) for place in (0,1)
          if tree or (noun,wet,rain,sun,fire,place)==(2,1,0,1,255,1)]
    steps=['until:0800:20000']
    for wet,hyp,noun in dry:
        steps+=byte_pokes(3,bytes([13,0,noun,1]))+LOT13_CLEAR+[f'poke:001E:0D',f'poke:4B70:{wet:02X}',
                f'poke:48AC:{hyp:02X}','until:0803:1000','peek:00FA:1','until:0800:1000']
    for verb,family,noun,tools in cut:
        steps+=byte_pokes(3,bytes([verb,0,noun,family]))+LOT13_CLEAR+['poke:001E:0E']
        steps+=byte_pokes(0x4098+41,bytes(19))+[f'poke:{0x4098+t:04X}:01' for t in tools]
        steps+=['until:0803:1000','peek:4B41:2','peek:00FA:3','until:0800:1000']
    for tree,noun,wet,rain,sun,fire,place in hang:
        steps+=byte_pokes(3,bytes([34,0,noun,1]))+LOT13_CLEAR+['poke:001E:22',f'poke:00D7:{tree:02X}',
                f'poke:4B70:{wet:02X}',f'poke:4B4C:{rain:02X}',f'poke:4B49:{sun:02X}',
                f'poke:45CD:{fire:02X}',f'poke:{0x404C+noun:04X}:{place:02X}','poke:4B73:01',
                'until:0803:1000','peek:00FA:1','peek:4B70:1','peek:0003:1','peek:4B73:1','until:0800:1000']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    # r.mem(address, size, k): the k-th dump at that address.
    for k,case in enumerate(dry):
        assert r.mem(0xFA,1,k)[0]==dry_rule(*case),(case,r.mem(0xFA,1,k)[0])
    for k,case in enumerate(cut):
        care,msg,track=cut_rule(*case)
        got=(tuple(r.mem(0x4B41,2,k)),r.mem(0xFA,3,len(dry)+k)[0],r.mem(0xFA,3,len(dry)+k)[1])
        assert got==(care,msg,track),(case,got)
    for k,case in enumerate(hang):
        got=(r.mem(0xFA,1,len(dry)+len(cut)+k)[0],r.mem(0x4B70,1,k)[0],r.mem(3,1,k)[0],r.mem(0x4B73,1,k)[0])
        assert got==hang_rule(*case),(case,got)
    print(f'{len(dry)} DRY/WARM, {len(cut)} COOL/CUT and {len(hang)} HANG clothing cases OK (native ROM)',
          flush=True)


def native_use():
    """T11/S00: USE SPLINT (selector 3, WEAR, W7 30 min, .02 x weight effort),
    the medical items (CARRY, WEAR for the sunglasses) and AXE/KNIFE (CARRY)."""
    module=journey_disk().run(0x11,0,7)
    disk=probe_disk(HERE/'build/re_care_use',module,bytes.fromhex('20 00 58 4C 00 08'),LOT13_EXITS)
    cases=[(93,5,1)]+[(item,5,light) for item in range(41,52) for light in (0,1)]+[(58,7,1),(59,7,1)]
    steps=['until:0800:20000']
    for noun,family,light in cases:
        steps+=byte_pokes(3,bytes([2,0,noun,family]))+LOT13_CLEAR+['poke:001E:00',f'poke:0D5D:{light:02X}']
        steps+=byte_pokes(0x4098,bytes(76))+byte_pokes(0x45DC,bytes(28))+byte_pokes(0x4BC6,bytes(2))
        steps+=byte_pokes(0x4C20,encode(1.65))
        steps+=['until:0803:1000','peek:4B41:2','peek:00FA:1','peek:0003:1','peek:4BC6:2',
                'peek:4098:76','peek:45DC:28','peek:4C20:5','until:0800:1000']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    weight=int.from_bytes((HERE/'build/game.bin').read_bytes()[0x4C02:0x4C04],'little')
    w7=[30,30,0,0,0,30,0,0,15,0,0]
    for i,(noun,family,light) in enumerate(cases):
        pair=tuple(r.mem(0x4B41,2,i));msg=r.mem(0xFA,1,i)[0];verb=r.mem(3,1,i)[0]
        minutes=int.from_bytes(r.mem(0x4BC6,2,i),'little');rate=fp(r.mem(0x4C20,5,i))
        if noun==93:
            assert (pair,verb,minutes,r.mem(0x45DC,28,i)[18])==((1,3),5,30,1),(noun,pair,verb,minutes)
            assert abs(rate-(1.65+.02*weight))<1e-6,rate
        elif noun==41 and not light:
            assert (pair,msg)==((0,0),53),(noun,pair,msg)
        elif family==5:
            assert (pair,verb,minutes,r.mem(0x4098,76,i)[noun])==((1,noun-30),5 if noun==43 else 7,w7[noun-41],1),\
                (noun,pair,verb,minutes)
            assert abs(rate-1.65)<1e-6
        else:
            assert (pair,verb,minutes,r.mem(0x4098,76,i)[noun])==((0,0),7,0,1),(noun,pair,verb,minutes)
    print(f'{len(cases)} original USE SPLINT / medical item / tool cases OK (native ROM, total weight {weight} lb)',
          flush=True)


def jsr(label):
    return bytes((0x20,L[label]&255,L[label]>>8))


def diseases(original):
    """T0B/S07 onsets: infection after 6 h of untreated cuts, malaria in
    Burma, New Guinea and Bolivia; one native random draw each, in order."""
    seeds=(1,2,9080894,44385572,1234567,67099546)
    cases=[(seed,cuts,hours,minutes,region,shelter,prevent)
           for seed in seeds for cuts,hours in ((0,20),(1,5.9),(1,6),(1,20))
           for minutes in (30,3000,30000) for region in (2,3,5,6)
           for shelter in (0,1) for prevent in (0,1)
           if not (shelter and (region in (2,6) or cuts==0)) and not (prevent and minutes!=30000)]
    idle=L.until('idle',20000);done=f'until:{L["idle"]+3:04X}:6000'
    start=a2test.run(DISK,[idle,L.peek('px',4)],emulator=a2test.A2SHOT,timeout=600).mem(L['px'],4)
    cell=0x7040+start[3]*112+start[1]
    level=a2test.run(DISK,[idle,f'peek:{cell:04X}:1'],emulator=a2test.A2SHOT,timeout=600).mem(cell,1)[0]
    # Sea level and a lake under the player: malaria terrain ($4B56 != 0).
    steps=[idle,L.poke('nature_frequency',0),'poke:700A:00',f'poke:{cell:04X}:{level|0x80:02X}']
    steps+=call(['env_hour'])+[done,idle]+call(['injury_health'])+[done,idle]
    # Terrain of the start cell, as the native module reads it ($D4, $4B56).
    probe=jsr('level_here')+bytes((0x8D,L['al_w']&255,L['al_w']>>8))+jsr('woods_here')
    probe+=bytes((0x2E,(L['al_w']+1)&255,(L['al_w']+1)>>8))+jsr('native_here')
    probe+=bytes((0x8D,L['al_i']&255,L['al_i']>>8,0x4C,L['idle']&255,L['idle']>>8))
    steps+=byte_pokes(L['idle'],probe)+[f'until:{L["idle"]+len(probe)-3:04X}:6000',
                                         L.peek('al_w',2),L.peek('al_i'),'peek:700A:1',idle]
    driver=bytes((0xA9,18))+jsr('overlay_load')+jsr('module_hazards')+bytes((0x4C,L['idle']&255,L['idle']>>8))
    steps+=byte_pokes(L['idle'],driver)
    end=f'until:{L["idle"]+8:04X}:6000'
    for seed,cuts,hours,minutes,region,shelter,prevent in cases:
        steps+=byte_pokes(L['injury_active'],bytes([cuts])+bytes(14))
        steps+=byte_pokes(L['injury_prevented'],bytes([1])*8+bytes([prevent,1,1,1,prevent,1,1]))
        steps+=[L.poke('shelter_inside',shelter),L.poke('region_number',region)]
        steps+=poke('s_elap',30)+poke('s_step',minutes)
        steps+=[L.poke('injury_since',b,i) for i,b in enumerate(encode(30-hours))]
        steps+=[L.poke('weather_seed',b,i) for i,b in enumerate(seed.to_bytes(4,'little'))]
        steps+=[end,L.peek('injury_active',15),L.peek('weather_seed',4),idle]
    port=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    level=port.mem(L['al_w'],2)[0];woods=port.mem(L['al_w'],2)[1]&1;water=port.mem(L['al_i'],1)[0]>>7
    base=port.mem(0x700A,1)[0]
    terrain=3 if water else 1 if woods else 2 if level>=96 else 0
    actual=[(port.mem(L['injury_active'],15,i)[8],port.mem(L['injury_active'],15,i)[12],
             port.mem(L['weather_seed'],4,i)) for i in range(len(cases))]
    assert any(a[0] for a in actual) and any(a[1] for a in actual),('some onsets',level,woods,water,base,[(c,a) for c,a in zip(cases,actual) if c[1] and c[2]==20][:6])
    assert all(a[0]==0 for a,c in zip(actual,cases) if c[1]==0 or c[2]<6 or c[6])
    assert all(a[1]==0 for a,c in zip(actual,cases) if c[4] in (2,6) or c[5] or c[6])
    if original:
        rng=(HERE/'build/re/smalldos_lo.bin').read_bytes()[0x21:0x9D]
        module=journey_disk().run(0xB,7,6)
        disk=probe_disk(HERE/'build/re_care_disease',module,bytes.fromhex('20 11 58 4C 00 08'),
                        [('QUIET',b'\x60',0x4D2A),('RNG',rng,0x0321)])
        steps=['until:0800:20000',f'poke:00D4:{level:02X}',f'poke:60A1:{base:02X}',
               f'poke:4B56:{terrain:02X}','poke:4C09:00']
        for seed,cuts,hours,minutes,region,shelter,prevent in cases:
            steps+=byte_pokes(0x47F4,bytes([cuts])+bytes(14))
            steps+=byte_pokes(0x47D6,bytes([1])*8+bytes([prevent,1,1,1,prevent,1,1]))
            steps+=[f'poke:0D5E:{shelter:02X}',f'poke:601F:{region:02X}']
            steps+=byte_pokes(0x4C61,encode(30))+byte_pokes(0x49CD,encode(hours))
            steps+=byte_pokes(0x4C08,minutes.to_bytes(2,'little'))
            steps+=byte_pokes(0x03B9,seed.to_bytes(4,'little'))
            steps+=['until:0803:1000','peek:47F4:15','peek:03B9:4','until:0800:1000']
        native=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
        expected=[(native.mem(0x47F4,15,i)[8],native.mem(0x47F4,15,i)[12],native.mem(0x03B9,4,i))
                  for i in range(len(cases))]
        bad=[(c,a,e) for c,a,e in zip(cases,actual,expected) if a!=e]
        assert not bad,bad[:5]
    print(f'{len(cases)} infection/malaria onset and draw cases OK (terrain {terrain}, level {level})'
          +(' (native ROM)' if original else ''),flush=True)


SWEAT=0.5833333334885538      # saved $4C7A


def gauge_rule(flags,a2_17,eaten,balance,a2_16,drunk,a1_24,a2_18,exhaustion,rest):
    """T0A/S0C $5BED: (hunger 173, thirst 174, forced sleep, tired 175)."""
    hunger=not flags&1 and (a2_17>12 or (3*eaten<8*165 and balance<-850))
    thirst=not flags&2 and (a2_16*SWEAT>6 or drunk<a2_16*SWEAT*SWEAT*2)
    tired=not flags&4 and (a2_18>16 or (exhaustion<95 and 4*rest<a2_18))
    return int(hunger),int(thirst),int(a1_24>=60),int(tired)


def gauge_cases():
    import itertools,random
    grid=list(itertools.product((0,7),(11,13),(100,500),(-900,-800),(1,6,11),(1,10),
                                (40,59,60.5),(3,9,17),(90,96),(0,1,7)))
    random.Random(13).shuffle(grid)
    return grid[:96]


def alerts_native(original):
    """Gauge alerts and the forced sleep decision: the port's health_alerts
    against the native T0A/S0C $5BED (hour 7, 165 lb, saved $4C7A)."""
    cases=gauge_cases()
    idle=L.until('idle',20000);done=f'until:{L["idle"]+3:04X}:6000'
    steps=[idle,L.poke('nature_frequency',0)]+call(['env_hour'])+[done,idle]+call(['health_alerts'])
    for flags,a2_17,eaten,balance,a2_16,drunk,a1_24,a2_18,exhaustion,rest in cases:
        steps+=[L.poke('al_daily',flags),L.poke('al_forced',0),L.poke('al_events',0),L.poke('dead',0),
                L.poke('al_last',exhaustion,17),L.poke('al_drunk',drunk),L.poke('al_drunk',0,1),
                L.poke('al_rest_h',rest),L.poke('al_rest_h',0,1)]
        steps+=poke('s_hour',7)+poke('s_eat',a2_17)+poke('s_eaten',eaten)+poke('s_spent',eaten-balance)
        steps+=poke('al_eaten0',0)+poke('al_spent0',0)+poke('s_drink',a2_16)+poke('s_defr',a1_24)
        steps+=poke('s_rest',a2_18)+poke('s_defw',0)+poke('s_deff',0)
        steps+=[done,L.peek('al_daily'),L.peek('al_forced'),L.peek('al_events'),L.peek('dead'),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    actual=[]
    for i,case in enumerate(cases):
        assert r.mem(L['dead'],1,i)[0]==0,case
        daily=r.mem(L['al_daily'],1,i)[0];flags=case[0]
        actual.append((int(bool(daily&1&~flags)),int(bool(daily&2&~flags)),r.mem(L['al_forced'],1,i)[0],
                       int(bool(r.mem(L['al_events'],1,i)[0]&2))))
        assert actual[-1]==gauge_rule(*case),(case,actual[-1])
    if original:
        module=journey_disk().run(0xA,0xC,6)
        disk=probe_disk(HERE/'build/re_care_gauges',module,bytes.fromhex('20 ED 5B 4C 00 08'),
                        [('QUIET',b'\x60',0x4D2A)])
        steps=['until:0800:20000','poke:4BF6:A5','poke:4BF7:00']+byte_pokes(0x4C57,encode(7))
        steps+=byte_pokes(0x4C20,encode(1.65))
        for flags,a2_17,eaten,balance,a2_16,drunk,a1_24,a2_18,exhaustion,rest in cases:
            steps+=byte_pokes(0x4B88,bytes([flags&1,flags>>1&1,flags>>2&1]))+['poke:000B:00']
            steps+=byte_pokes(0x0DB8,bytes(4))+byte_pokes(0x4A1D,encode(a2_17))
            steps+=byte_pokes(0x4BDC,eaten.to_bytes(2,'little'))
            steps+=byte_pokes(0x4BD8,(balance&0xFFFF).to_bytes(2,'little'))
            steps+=byte_pokes(0x4A18,encode(a2_16))+byte_pokes(0x4BD4,drunk.to_bytes(2,'little'))
            steps+=byte_pokes(0x49C3,encode(a1_24))+byte_pokes(0x4A22,encode(a2_18))
            steps+=[f'poke:48AA:{exhaustion:02X}']+byte_pokes(0x4BE2,rest.to_bytes(2,'little'))
            steps+=['until:0803:1000','peek:4B88:3','peek:000B:1','peek:0DB8:4','until:0800:1000']
        native=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
        for i,case in enumerate(cases):
            got=native.mem(0x4B88,3,i);flags=case[0]
            expected=(int(got[0] and not flags&1),int(got[1] and not flags&2),native.mem(0xB,1,i)[0],
                      int(bool(native.mem(0x0DB8,4,i)[0]) and not flags&4))
            assert expected==actual[i],(case,expected,actual[i])
            assert native.mem(0x0DB8,4,i)[3]==expected[2],case
    assert all(len({a[j] for a in actual})==2 for j in range(4)),'each rule fires and holds'
    print(f'{len(cases)} hunger/thirst/tired alert and forced sleep decisions OK'
          +(' (native ROM)' if original else ''),flush=True)


def forced_sleep(original):
    """An exhausted player (A1[24] >= 60) sleeps 180 + INT(RND x 300) minutes
    without input, after message 178; the deficit is credited as for REST."""
    seeds=(1,9080894,44385572,67099546)
    port=[]
    with a2test.Session(DISK,timeout=1200) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency',0))
        for seed in seeds:
            for step in poke('s_defr',62)+['key:REST 30 MIN\r',L.until('al_sleep',20000)]:
                s.step(step)
            text=result_text(text_screen(s.step('peek:0400:1024').data))
            assert 'EXHAUSTED: INVOLUNTARY SLEEP.' in text,text
            assert s.step(L.peek('al_forced')).data==b'\1'
            before=fp(s.step(L.peek('s_elap',5)).data)
            for i,b in enumerate(seed.to_bytes(4,'little')):
                s.step(L.poke('weather_seed',b,i))
            s.step(IDLE)
            minutes=int.from_bytes(s.step(L.peek('msgnum',2)).data,'little')
            elapsed=(fp(s.step(L.peek('s_elap',5)).data)-before)*60
            assert abs(elapsed-minutes)<.01 and s.step(L.peek('al_forced')).data==b'\0',(seed,minutes,elapsed)
            text=result_text(text_screen(s.step('peek:0400:1024').data))
            assert f'YOU RESTED {minutes} MINUTES' in text,text
            assert fp(s.step(L.peek('s_defr',5)).data)<60
            port.append(minutes)
    assert all(180<=m<480 for m in port),port
    if original:
        rng=(HERE/'build/re/smalldos_lo.bin').read_bytes()[0x21:0x9D]
        module=journey_disk().run(0x15,0xB,5)
        disk=probe_disk(HERE/'build/re_care_sleep',module,bytes.fromhex('20 00 58 4C 00 08'),
                        LOT13_EXITS+[('RNG',rng,0x0321)])
        steps=['until:0800:20000']
        for seed in seeds:
            steps+=['poke:0003:14','poke:000B:01','poke:4B56:00']+byte_pokes(0x4BC6,bytes(2))
            steps+=byte_pokes(0x03B9,seed.to_bytes(4,'little'))
            steps+=['until:0803:4000','peek:4BC6:2','peek:000B:1','until:0800:1000']
        native=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        expected=[int.from_bytes(native.mem(0x4BC6,2,i),'little') for i in range(len(seeds))]
        assert port==expected,(port,expected)
        assert all(native.mem(0xB,1,i)==b'\0' for i in range(len(seeds)))
    print(f'{len(seeds)} forced sleeps of {port} minutes OK'+(' (native ROM)' if original else ''),flush=True)


def care_commands():
    """The port's lot-13 commands: SPLINT, PRESSURE, WET/DRY/HANG, CUT BODY."""
    import tempfile
    from common import disk_with
    from test_forest import map_fixture
    def result(s):
        return result_text(text_screen(s.step('peek:0400:1024').data))
    def command(s,text):
        s.step(f'key:{text}\r');s.step('wait:1');s.step(IDLE)
        return result(s)
    def actions(s):
        return s.step(L.peek('medical_actions',30)).data
    def elapsed(s):
        return fp(s.step(L.peek('s_elap',5)).data)
    with a2test.Session(DISK,timeout=1800) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        # USE SPLINT: absent until lot 3 crafts one; then selector 3, worn, 30 min.
        assert 'NOT ACCESSIBLE' in command(s,'USE SPLINT')
        s.step(L.poke('injury_active',1,1));s.step(L.poke('splint_place',2))
        before=elapsed(s)
        assert 'OK' in command(s,'USE SPLINT')
        assert actions(s)[2]==1 and s.step(L.peek('splint_place')).data==b'\1'
        assert abs(elapsed(s)-before-.5)<1e-6
        assert s.step(L.peek('injury_treated',15)).data[1]==1,'broken arm splinted'
        # USE PRESSURE: the second cut treatment, 30 minutes.
        s.step(L.poke('injury_active',1,0));before=elapsed(s)
        assert 'OK' in command(s,'USE PRESSURE')
        assert actions(s)[1]==1 and abs(elapsed(s)-before-.5)<1e-6
        assert s.step(L.peek('injury_treated',15)).data[0]==1
        # WET BODY: rain front or water: already wet, selector 9, no time.
        s.step(L.poke('injury_active',1,4));s.step(L.poke('medical_actions',1,5))
        s.step(L.poke('weather_inside_front',1));before=elapsed(s)
        assert 'YOU ALREADY HAVE' in command(s,'WET BODY')
        assert actions(s)[8]==1 and elapsed(s)==before
        assert s.step(L.peek('injury_treated',15)).data[4]==1,'sunburn: water drunk (6) and body wet (9)'
        s.step(L.poke('weather_inside_front',0));s.step(L.poke('medical_actions',0,8))
        # From the canteen: the ounces are poured out; no more than it holds.
        s.step(L.poke('it_gnd_lo',0,22));s.step(L.poke('it_gnd_hi',0,22))
        water=s.step(L.peek('it_pack_lo',1,22)).data[0]
        assert 'AMOUNT OF' in command(s,f'WET BODY {water+20} OZ') and actions(s)[8]==0
        assert 'OK' in command(s,'WET BODY 4 OZ') and actions(s)[8]==1
        assert s.step(L.peek('it_pack_lo',1,22)).data[0]==water-4
        s.step(L.poke('it_pack_lo',0,22));s.step(L.poke('it_gnd_lo',0,22))
        assert 'NO WATER AT HAND' in command(s,'WET BODY')
        assert 'NOT APPLY' in command(s,'WET HEAD')
        # DRY/WARM: wet clothing, or a cold body (hypothermia under 86 %).
        s.step(L.poke('wet_mode',1))
        assert 'TO WARM BY THE SUN' in command(s,'DRY PARKA')
        s.step(L.poke('wet_mode',0))
        assert 'NOT APPLY' in command(s,'WARM PARKA')
        for step in poke('s_body',95)+poke('s_therm_factor',.8):
            s.step(step)
        assert 'TO WARM BY THE SUN' in command(s,'WARM PARKA')
        assert 'NOT APPLY' in command(s,'DRY CLOTHES') and 'NOT APPLY' in command(s,'DRY BODY')
        # CUT/COOL BODY: a knife or an axe in use (USE KNIFE) on this square.
        assert 'APPROPRIATE ITEM' in command(s,'CUT BODY') and actions(s)[6]==0
        assert 'OK' in command(s,'USE KNIFE')
        assert s.step(L.peek('it_place',76)).data[59]==3
        before=elapsed(s)
        assert 'OK' in command(s,'CUT BODY') and actions(s)[6]==1 and elapsed(s)==before
        s.step(L.poke('medical_actions',0,6))
        assert 'OK' in command(s,'COOL BODY') and actions(s)[6]==1
        assert 'NOT VERY WISE' in command(s,'CUT AXE') and 'TURNS YOU ON' in command(s,'CUT CHEESE')
        s.step(L.poke('px',(s.step(L.peek('px',2)).data[1]+1)&255,1))
        s.step(L.poke('medical_actions',0,6))
        assert 'APPROPRIATE ITEM' in command(s,'CUT BODY'),'a tool in use stays on its square'
    # HANG clothing: a tree; wet clothes outside the rain dry in the Sun.
    with tempfile.TemporaryDirectory() as tmp:
        with a2test.Session(disk_with(tmp,map_fixture()),timeout=1800) as s:
            s.step(IDLE);s.step(L.poke('nature_frequency',0))
            assert 'THINK' in command(s,'HANG PARKA')
            s.step(L.poke('wet_mode',1));s.step(L.poke('weather_sky',2))
            assert 'THINK' in command(s,'HANG PARKA')
            s.step(L.poke('weather_sky',0))
            for step in poke('s_hour',23):
                s.step(step)
            assert 'OK' in command(s,'HANG PARKA')
            assert s.step(L.peek('wet_mode')).data==b'\1','no Sun at night: still wet'
            assert s.step(L.peek('it_place',76)).data[2]==0,'the parka hangs (ground)'
            for step in poke('s_hour',12):
                s.step(step)
            assert 'OK' in command(s,'HANG SWEATER')
            assert s.step(L.peek('wet_mode')).data==b'\0','dried by the Sun'
            assert 'TOO MUCH' not in command(s,'HANG FOOD')       # tree module kept
            assert s.step(L.peek('it_place',76)).data[21]==5
    print('USE SPLINT/PRESSURE, WET BODY, DRY/WARM, CUT/COOL BODY and HANG clothing OK',flush=True)


def medical_gestures():
    """STATUS's care gestures (src/status.s, src/care.s): the focus on an
    active condition, RETURN types its gesture: the same state as typed. The
    FRSTAID KIT in the dark types USE FLASHLIGHT first (the grid's queue)."""
    READY = L.until('keyboard_wait', 20000)

    def state(s):
        return [s.step(L.peek(n, k)).data for n, k in (('medical_actions', 30), ('s_elap', 5),
                ('injury_treated', 15), ('it_place', 76), ('it_pack_lo', 76), ('camp_use', 1), ('light', 1))]

    def gesture(s, rights=0):
        s.step('key:\\^'); s.step(READY)
        for k in ['\\v'] + ['\\>'] * rights:      # (STATUS holds MEDICAL's rows: 15 October 2026)
            s.step('press:' + k); s.step(L.until('page_top', 40000)); s.step(READY)
        line = text_screen(s.step('peek:0400:1024').data)[23]
        s.step('press:\\r')
        s.step(L.until('do_command', 40000))
        return line, s.step(L.peek('inbuf', 20)).data.split(b'\0')[0].decode()

    results = []
    for by_page in (True, False):
        with a2test.Session(DISK, timeout=1800) as s:
            s.step(IDLE); s.step(L.poke('nature_frequency', 0))
            s.step(L.poke('injury_active', 1, 0))           # SEVERE CUTS
            if by_page:
                line, typed = gesture(s)
                assert line.startswith(' \u2190\u2192 STOP BLEEDING  USE PRESSURE') and typed == 'STOP BLEEDING', (line, typed)
                s.step(IDLE)
            else:
                s.step('key:STOP BLEEDING\r'); s.step('wait:1'); s.step(IDLE)
            results.append(state(s))
            assert results[-1][0][0] == 1 and results[-1][2][0] == 1, 'selector 1: the bleeding stopped'
            # INFECTION in the dark, the kit and the flashlight in the pack.
            s.step(L.poke('injury_active', 0, 0)); s.step(L.poke('injury_active', 1, 8))
            for item in (41, 66):
                s.step(L.poke('it_place', 2, item))
            s.step(L.poke('light', 0))
            if by_page:
                line, typed = gesture(s)
                assert line.startswith(' \u2190\u2192 USE FRSTAID KIT') and typed == 'USE FLASHLIGHT', (line, typed)
                s.step(L.until('get_line', 400000)); s.step(L.until('do_command', 40000))
                assert s.step(L.peek('inbuf', 20)).data.startswith(b'USE FRSTAID KIT\0')
                s.step(IDLE)
            else:
                for text in ('USE FLASHLIGHT', 'USE FRSTAID KIT'):
                    s.step(f'key:{text}\r'); s.step('wait:1'); s.step(IDLE)
            results.append(state(s))
            assert results[-1][0][10] == 1, 'selector 11: the infection treated (the kit, with light)'
    assert results[0] == results[2] and results[1] == results[3], 'the gestures = the commands typed'
    print('MEDICAL gestures: STOP BLEEDING, USE FRSTAID KIT in the dark (USE FLASHLIGHT first) = typed: OK',
          flush=True)


def alerts_display():
    """Alerts are appended under the result; the crossing messages 187, 160
    and 176 follow the native thresholds; shivering is announced once."""
    with a2test.Session(DISK,timeout=1800) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        for i,b in enumerate(encode(-20)):
            s.step(L.poke('s_last',b,5+i))          # last meal 27 h ago: hunger
        s.step('key:REST 30 MIN\r');s.step('wait:1');s.step(IDLE)
        rows=result_rows(text_screen(s.step('peek:0400:1024').data))
        assert rows[0].startswith('YOU RESTED 30 MINUTES'),rows
        assert any(r.startswith('YOU ARE HUNGRY ENOUGH TO EAT A HORSE.') for r in rows[1:]),rows
        assert s.step(L.peek('al_daily')).data[0]&1
        s.step('key:REST 30 MIN\r');s.step('wait:1');s.step(IDLE)
        rows=result_rows(text_screen(s.step('peek:0400:1024').data))
        assert not any('HORSE' in r for r in rows),'once a day'
    idle=L.until('idle',20000);done=f'until:{L["idle"]+3:04X}:6000'
    steps=[idle,L.poke('nature_frequency',0)]+call(['env_hour'])+[done,idle]+call(['health_alerts'])
    cases=[]
    # (al_last[15], dehydration deficit, thermal mode, health above 1, food deficit)
    for last,deficit,mode,strong,food in ((97,47,0,1,0),(97,20,0,1,0),(60,140,0,1,0),(40,140,0,1,0),
                                          (100,0,2,1,0),(100,0,1,1,0),(100,0,0,1,460),(100,0,0,0,460)):
        cases.append((last,deficit,mode,strong,food))
        steps+=[L.poke('al_count',0),L.poke('al_events',0),L.poke('al_once',0),L.poke('al_daily',7),
                L.poke('al_last',last,15),L.poke('thermal_mode',mode),L.poke('al_strong',strong),
                L.poke('dead',0)]
        steps+=poke('s_defw',deficit)+poke('s_deff',food)+poke('s_defr',0)+poke('s_metabolic',1.65)
        steps+=[done,L.peek('al_queue',8),L.peek('al_count'),L.peek('al_events'),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    got=[(list(r.mem(L['al_queue'],8,i)[:r.mem(L['al_count'],1,i)[0]]),r.mem(L['al_events'],1,i)[0])
         for i in range(len(cases))]
    # Dehydration 1-(47/190.5)^2 = 93.9 % (187 from 97), 1-(20/190.5)^2 = 98.9 %;
    # 1-(140/190.5)^2 = 45.9 %: from 60 the event 160, from 40 nothing.
    assert got[0]==([4],0) and got[1]==([],0),got[:2]
    assert got[2]==([],1) and got[3]==([],0),got[2:4]
    assert got[4][0]==[2] and got[5][0]==[3],'203 shivering, 204 sweating'
    assert got[6][1]&4 and not got[7][1]&4,'176 once health passes under 1'
    print('Alert display, daily hunger, crossings 160/176 and shiver/sweat messages OK',flush=True)


PLACED=(41,42,43,44,45,46,47,48,49,50,51,58,59)


def placement(original):
    """Automatic placement: a used item ends in the hand (CARRY), the
    sunglasses on the face (WEAR), through the native transaction chain."""
    names={41:'FIRSTAID KIT',42:'SNAKEBITE KIT',43:'SUNGLASSES',44:'SUNSCREEN',45:'REPELLENT',
           46:'IODINE TABLETS',47:'FLAGYL',48:'SALT TABLETS',49:'OXYGEN',50:'QUININE',51:'SOAP',
           58:'AXE',59:'KNIFE'}
    steps=[IDLE,L.poke('nature_frequency',0)]
    for item in PLACED:
        steps+=[L.poke('it_place',2,item),L.poke('it_pack_lo',1,item),L.poke('it_pack_hi',0,item),
                f'key:USE {names[item]}\r','wait:1',IDLE,L.peek('it_place',76)]
    # Oral doses: T12/S08 $58D1 continues with CARRY as well.
    for item,command in ((47,'EAT FLAGYL'),(48,'EAT SALT TABLETS'),(50,'DRINK QUININE')):
        steps+=[L.poke('it_place',2,item),L.poke('it_pack_lo',1,item),
                f'key:{command}\r','wait:1',IDLE,L.peek('it_place',76)]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    port=[r.mem(L['it_place'],76,i)[item] for i,item in enumerate(PLACED+(47,48,50))]
    assert port==[1 if item==43 else 3 for item in PLACED+(47,48,50)],port
    if original:
        journey=journey_disk()
        modules=[journey.run(0x11,0,7),journey.run(0xE,2,8),journey.run(0xE,0xA,6),journey.run(6,0,2)]
        disk=probe_disk(HERE/'build/re_care_place',modules[0],bytes.fromhex('20 00 58 4C 00 08'),
                        [(name,b'\x60',address) for name,address in
                         [('CLOCK',0x4D00),('NEXT',0x4D03),('DONE',0x4D06),('DISK',0x03DB),
                          ('MSG',0x4D21),('MSG1',0x4D24),('MSG2',0x4D27),('MSG3',0x4D2A)]])
        expected=[]
        with a2test.Session(disk,timeout=1800) as s:
            for step in ['until:0800:20000','poke:0D5D:01']:
                s.step(step)
            for item in PLACED:
                steps=byte_pokes(3,bytes([2,0,item,7 if item>51 else 5]))+byte_pokes(0x1E,b'\0')
                steps+=byte_pokes(0x4344+2*item,(1).to_bytes(2,'little'))
                steps+=byte_pokes(0x404C+item,b'\2')+byte_pokes(0x4098+item,b'\0')
                steps+=byte_pokes(0x4B41,bytes(4))+byte_pokes(0x4ABC,bytes(30))+['poke:4B73:01']
                steps+=byte_pokes(0x4BEE,(10000).to_bytes(2,'little')*3)
                steps+=byte_pokes(0x4BF8,(10000).to_bytes(2,'little'))
                for module in modules:
                    steps+=byte_pokes(0x5800,module)+['until:0803:4000','until:0800:1000']
                for step in steps:
                    s.step(step)
                expected.append(s.step(f'peek:{0x404C+item:04X}:1').data[0])
        assert port[:len(PLACED)]==expected,(port,expected)
    print(f'{len(PLACED)+3} automatic placements after USE/EAT/DRINK OK'+(' (native ROM)' if original else ''),
          flush=True)


if __name__=='__main__':
    original='--original' in sys.argv
    commands()
    numeric_refusals()
    doses(original)
    oxygen_last_dose()
    if original:
        native_gates()
        empty_compatibility()
        native_wet_dry()
        native_misc()
        native_use()
    # Lot 13: care commands, placement, alerts, forced sleep, disease onsets.
    care_commands()
    medical_gestures()
    alerts_display()
    placement(original)
    alerts_native(original)
    forced_sleep(original)
    diseases(original)
