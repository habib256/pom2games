#!/usr/bin/env python3
"""Persistent clothing cache across garment changes and HGR/DOS reuse."""
from common import DISK, L, a2test
from test_thermal import call, poke

IDLE=L.until('idle',20000)
DONE=f'until:{L["idle"]+3:04X}:6000'


def main():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        for step in poke('s_step',0)+poke('s_metabolic',1.65)+call(['thermal']):
            s.step(step)
        s.step(DONE);s.step(IDLE)
        for step in call(['thermal_clothes']):
            s.step(step)
        def clothes():
            start=s.step(L.until('thermal_clothes',6000)).cycles[-1]
            end=s.step(DONE).cycles[-1]
            value=s.step(L.peek('s_insul',5)).data
            s.step(IDLE)
            return end-start,value
        # Change every clothing position, including all three packed key bytes.
        # Both garment changes and each wet-mode transition must invalidate.
        cases=0
        for wet in (0,1,2,0):
            s.step(L.poke('wet_mode',wet))
            for item in range(2,21):
                old=s.step(L.peek('it_place',1,item)).data[0]
                s.step(L.poke('it_place',2 if old==1 else 1,item))
                changed,value=clothes()
                cached,again=clothes()
                assert again==value and cached<changed/10,(wet,item,changed,cached)
                s.step(L.poke('clothing_cache_valid',0))
                forced,fresh=clothes()
                assert fresh==value and cached<forced/10,(wet,item,'fresh comparison')
                cases+=1
        # A non-worn garment moved between pack/hand is the same thermal input.
        s.step(L.poke('it_place',2,2));clothes()
        s.step(L.poke('it_place',3,2))
        unchanged,value=clothes()
        assert unchanged<1000,'non-worn transfer must retain the cache'
        # Re-reading SIM overwrites HGR, but must retain the key and s_insul.
        key=s.step(L.peek('clothing_cache',5)).data
        s.step(L.poke('sim_loaded',0))
        for step in call(['thermal']):
            s.step(step)
        s.step(DONE);s.step(IDLE)
        assert s.step(L.peek('clothing_cache',5)).data==key
        assert s.step(L.peek('s_insul',5)).data==value
    print(f'  {cases} garment/wet transitions: cache equals fresh ROM result; repeated calculation >10x faster')
    print('  non-worn pack/hand transfer and DOS/SIM reload preserve cached insulation: OK')


if __name__=='__main__':
    main()
