#!/usr/bin/env python3
"""Salt loss and cold exposure increments/onset against native T0B/S07."""
import sys
from common import HERE,L,DISK,a2test
from gendata import fp as encode
from test_thermal import call,poke
from test_medical import byte_pokes
from test_weather_cycle import probe_disk


def main():
    cases=[]
    for i,threshold in ((0,500),(3,7200)):
        for air in (-20,20,30,70,71,90):
            for metabolic in (1.65,5.2):
                for counter in (0,threshold):
                    cases.append((i,air,metabolic,counter,0,0))
    cases += [(0,90,1.65,490,1,0),(0,70,1.65,500,1,0),(3,40,1.65,100,0,0)]
    cases += [(i,30,1.65,counter,0,1) for i in (0,3) for counter in (1,20,500,7200)]
    idle=L.until('idle',20000);done=f'until:{L["idle"]+3:04X}:6000'
    # Load the simulation, then hazards through their real resident wrappers.
    steps=[idle]+call(['env_hour'])+[done,idle]+call(['injury_health'])+[done,idle]
    # injury_health leaves the medical image loaded. Explicitly load hazards.
    driver=bytes((0xA9,18,0x20,L['overlay_load']&255,L['overlay_load']>>8,
                  0x20,L['module_hazards']&255,L['module_hazards']>>8,
                  0x4C,L['idle']&255,L['idle']>>8))
    steps+=byte_pokes(L['idle'],driver)
    end=f'until:{L["idle"]+8:04X}:6000'
    for i,air,metabolic,counter,sweating,protected in cases:
        condition=9 if i==0 else 6
        steps+=byte_pokes(L['injury_active'],bytes(15))+byte_pokes(L['injury_prevented'],bytes([1])*15)
        steps+=[L.poke('injury_prevented',protected,condition),L.poke('shelter_inside',0),
                L.poke('thermal_mode',sweating),L.poke('felt_temp',air),L.poke('felt_temp',air>>8,1)]
        steps+=byte_pokes(L['exposure_counter'],bytes(8))
        steps+=byte_pokes(L['exposure_counter']+2*i,counter.to_bytes(2,'little'))
        steps+=poke('s_step',60)+poke('s_metabolic',metabolic)+poke('s_elap',10)
        steps+=[end,L.peek('exposure_counter',8),L.peek('injury_active',15),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    actual=[(int.from_bytes(r.mem(L['exposure_counter'],8,k)[2*i:2*i+2],'little'),
             r.mem(L['injury_active'],15,k)[9 if i==0 else 6]) for k,(i,_,_,_,_,_) in enumerate(cases)]
    if '--original' in sys.argv:
        disk=probe_disk(HERE/'build/re_exposure',(HERE/'build/re_surv/m0B7.bin').read_bytes(),
                        bytes.fromhex('20 11 58 4C 00 08'),[('QUIET',b'\x60',0x4D2A)])
        steps=['until:0800:20000']
        for i,air,metabolic,counter,sweating,protected in cases:
            condition=9 if i==0 else 6
            # Native exposure index 4 (unused) separates frost from snow.
            index=4 if i==3 else i
            steps+=byte_pokes(0x47F4,bytes(15))+byte_pokes(0x47D6,bytes([1])*15)
            steps+=byte_pokes(0x47D6+condition,bytes([protected]))
            steps+=byte_pokes(0x4A4A,bytes(12))+byte_pokes(0x4A4A+2*index,counter.to_bytes(2,'little'))
            steps+=byte_pokes(0x4C20,encode(metabolic))+byte_pokes(0x4C61,encode(10))
            steps+=byte_pokes(0x4C70,encode(98.6))+byte_pokes(0x4C75,encode(0))
            steps+=[f'poke:4B9D:{air&255:02X}',f'poke:4B7B:{sweating:02X}',
                    'poke:0D5E:00','poke:4C08:3C','poke:4C09:00',
                    'until:0803:1000','peek:4A4A:12','peek:47F4:15','until:0800:1000']
        native=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        for k,(case,value) in enumerate(zip(cases,actual)):
            i=4 if case[0]==3 else case[0]
            expected=(int.from_bytes(native.mem(0x4A4A,12,k)[2*i:2*i+2],'little'),
                      native.mem(0x47F4,15,k)[9 if i==0 else 6])
            assert value==expected,(case,value,expected)
    assert actual[cases.index((3,20,1.65,7200,0,0))][1]==1
    assert actual[cases.index((3,30,1.65,7200,0,0))][1]==0
    assert all(value[1] == 0 and value[0] < case[3] for case,value in zip(cases,actual) if case[5])
    print(f'{len(cases)} salt/cold exposure and onset cases OK'+(' (native ROM)' if '--original' in sys.argv else ''))
    shelters()


def shelters():
    """Lot 3: inside a shelter the hazards take the air + 15 F, inside the
    igloo (shelter_inside 2) 35 F, as THERMAL (T0B/S02): the frostbite
    counter in the igloo at -20 F equals the one outside at 35 F."""
    idle=L.until('idle',20000);done=f'until:{L["idle"]+3:04X}:6000'
    steps=[idle]+call(['env_hour'])+[done,idle]+call(['injury_health'])+[done,idle]
    driver=bytes((0xA9,18,0x20,L['overlay_load']&255,L['overlay_load']>>8,
                  0x20,L['module_hazards']&255,L['module_hazards']>>8,
                  0x4C,L['idle']&255,L['idle']>>8))
    steps+=byte_pokes(L['idle'],driver)
    end=f'until:{L["idle"]+8:04X}:6000'
    cases=[(0,35,35),(2,-20,-20),(0,-5,-5),(1,-20,-20),(0,-20,-20)]   # shelter, felt, air
    for shelter,felt,air in cases:
        steps+=byte_pokes(L['injury_active'],bytes(15))+byte_pokes(L['injury_prevented'],bytes([1])*15)
        steps+=[L.poke('injury_prevented',0,6),L.poke('shelter_inside',shelter),L.poke('thermal_mode',0),L.poke('felt_temp',felt&255),
                L.poke('felt_temp',(felt>>8)&255,1),L.poke('airtemp',air&255)]
        steps+=byte_pokes(L['exposure_counter'],bytes(8))
        steps+=poke('s_step',60)+poke('s_metabolic',1.65)+poke('s_elap',10)
        steps+=[end,L.peek('exposure_counter',8),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    frost=[int.from_bytes(r.mem(L['exposure_counter'],8,k)[6:8],'little') for k in range(len(cases))]
    assert frost[1]==frost[0] and frost[3]==frost[2] and frost[4]>frost[2]>frost[0], frost
    print(f'shelters: frostbite counter at 35 F {frost[0]} = igloo at -20 F {frost[1]}; '
          f'-5 F {frost[2]} = shelter at -20 F + 15 {frost[3]}; outside -20 F {frost[4]}: OK')


if __name__=='__main__':main()
