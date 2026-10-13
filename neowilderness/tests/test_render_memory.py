#!/usr/bin/env python3
"""Terrain clears (both DHGR banks) preserve HUD, holes and untouched pan columns."""
import re
from common import DISK, L, a2test, DHGR_BANKS
from test_thermal import call


def main():
    idle=L.until('idle',20000)
    done=f'until:{L["idle"]+3:04X}:6000'
    # Distinct patterns in the main and aux banks (aux written through PAGE2).
    original=[bytes((i*37+19)&255 for i in range(8192)), bytes((i*53+7)&255 for i in range(8192))]
    steps=[idle]+call(['clear_rows'])
    steps += [f'poke:{0x2000+i:04X}:{v:02X}' for i,v in enumerate(original[0])]
    steps += ['poke:C055:00']+[f'poke:{0x2000+i:04X}:{v:02X}' for i,v in enumerate(original[1])]+['poke:C054:00']
    ranges=[(0,10),(30,40),(10,30),(0,40)]
    for first,last in ranges:
        steps += [L.poke('tmp',first),L.poke('tmp2',last),
                  L.until('clear_rows',6000),done,*DHGR_BANKS,idle]
    result=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=180)
    expected=[bytearray(bank) for bank in original]
    for index,(first,last) in enumerate(ranges):
        for bank in expected:
            for row in range(16,176):
                offset=a2test.hgr_offset(row)
                bank[offset+first:offset+last]=bytes(last-first)
        assert result.dumps[2*index]==expected[0],(first,last,'main: HUD/hole/cache/pan corruption')
        assert result.dumps[2*index+1]==expected[1],(first,last,'aux: HUD/hole/cache/pan corruption')
        elapsed=result.cycles[2+3*index]-result.cycles[1+3*index]
        if (first,last)==(0,40):
            # Two 8 KB banks, still under the HGR bound: bands of eight rows
            # with absolute,X stores (src/dhgr.s clear_rows).
            assert elapsed<100000,('full clear too slow',elapsed)
            print(f'  full terrain/cache clear of both banks: {elapsed:,} cycles, under 100,000')
    print('  partial/full clears preserve HUD, HGR holes, hidden rows and retained pan columns: OK')
    # Re-enable probes between frames: a stopped ray must not disable the next.
    with a2test.Session(DISK) as s:
        s.step(idle)
        for enabled in (0,1,0,1):
            s.step(L.poke('forest_enabled',enabled))
            s.step('key:VIEW');s.step('press:\\r')
            s.step(L.until('view_full',20000))
            profile=s.step(f'pcprof:{L["idle"]:04X}:20000')
            pcs={int(a,16):int(c) for a,c in
                 re.findall(r'^pc ([0-9A-F]{4}) (\d+)$',profile.out,re.M)}
            probes=pcs.get(L['forest_probe'],0)//3  # entry PHP takes three cycles
            assert (0<probes<=140*9) if enabled else probes==0,(enabled,probes)
    print('  woodland probes bounded per ray; disabled/re-enabled frames reset correctly: OK')


if __name__=='__main__':
    main()
