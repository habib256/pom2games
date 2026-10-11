#!/usr/bin/env python3
"""Real WALK/SWIM stop two cells before each edge, retaining travel time."""
import tempfile
from common import HERE,L,a2test,disk_with,state,fp,text_screen
from test_thermal import poke


def main():
    m=bytearray((HERE/'build/map.bin').read_bytes())
    m[2:8]=bytes((0,50,0,40,140,0));m[8:10]=bytes((50,70));m[16]=0
    idle=L.until('idle',20000)
    # Each WALK approach has one valid 19-minute step, then a refused
    # step. Fractional coordinates stay intact. Also refuse an immediate
    # outward step at the safe limit, diagonals and unsigned wraparound.
    cases=[(108*256+128,40*256,140,109*256+128,40*256,19),
           (3*256+128,40*256,420,2*256+128,40*256,19),
           (50*256,3*256+128,280,50*256,2*256+128,19),
           (50*256,80*256+128,0,50*256,81*256+128,19),
           (109*256+128,40*256,140,109*256+128,40*256,0),
           (2*256+128,40*256,420,2*256+128,40*256,0),
           (50*256,2*256,280,50*256,2*256,0),
           (50*256,81*256+128,0,50*256,81*256+128,0),
           (2*256+128,2*256+128,490,2*256+128,2*256+128,0),
           (0,40*256,420,0,40*256,0)]
    for verb,water in [('WALK',0),('SWIM',128)]:
        trial_cases=cases
        if verb=='SWIM':
            trial_cases=[(109*256,40*256,140,109*256+128,40*256,28),
                         (2*256+128,40*256,420,2*256,40*256,28),
                         (50*256,2*256+128,280,50*256,2*256,28),
                         (50*256,81*256,0,50*256,81*256+128,28),
                         (109*256+128,40*256,140,109*256+128,40*256,0),
                         (2*256,40*256,420,2*256,40*256,0),
                         *cases[6:8],
                         (2*256,2*256,490,2*256,2*256,0),cases[9]]
        m[64:]=bytes([10|water])*9408;m[21]=11
        with tempfile.TemporaryDirectory() as tmp:
            disk=disk_with(tmp,m)
            steps=[L.until('game_start',20000),L.poke('scenes_enabled',0),idle]
            for x,y,h,*_ in trial_cases:
                steps += [L.poke('shown',0)]
                if verb=='SWIM':
                    steps += poke('s_health',7.866609670221806)
                for name,value in [('px',x),('py',y),('heading',h)]:
                    steps += [L.poke(name,value),L.poke(name,value>>8,1)]
                steps += [L.peek('s_elap',5),f'key:{verb}\r','wait:1',L.until('wait_key',6000),
                          'key:1\r','wait:1',idle,'peek:0400:1024',L.peek('px',6),L.peek('s_elap',5)]
            r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        assert len(r.dumps)==4*len(trial_cases)
        for k,(x,y,h,nx,ny,minutes) in enumerate(trial_cases):
            before,text,pose,after=r.dumps[4*k:4*k+4]
            assert state(pose)==(nx,ny,h),(verb,k,state(pose),(nx,ny,h))
            assert abs((fp(after)-fp(before))*60-minutes)<1e-5,(verb,k,fp(before),fp(after))
            assert 'MAP ENDS AHEAD' in '\n'.join(text_screen(text))
        print(f'  {verb}: four sides, fractional coordinates, diagonals and no time on refused steps OK')
    print('Travel boundary: OK')


if __name__=='__main__': main()
