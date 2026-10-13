#!/usr/bin/env python3
"""Site directions checked against live MAP markers, not scene_ref math."""
import tempfile
from common import L,a2test,disk_with,banks,dhgr_view,dhgr_scene,map_rows
from test_input import IDLE,command,flat,screen
from test_hud import header,expected as compass_pixels


def main():
    m=bytearray(flat());m[24]=0
    with tempfile.TemporaryDirectory() as tmp,a2test.Session(disk_with(tmp,m)) as s:
        s.step(L.until('game_start',20000))
        s.step(L.poke('forest_enabled',0));s.step(L.poke('sky_enabled',0))
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        for asset,marker in ((9,'H'),(5,'C')):
            for dx,dy,heading in ((0,4,0),(4,4,70),(4,0,140),(4,-4,210),
                                  (0,-4,280),(-4,-4,350),(-4,0,420),(-4,4,490)):
                x,y=40+dx,40+dy
                # Isolate the target; both sprites share the same projector.
                for address,value in ((0x7002,128),(0x7003,x if asset==5 else 80),
                                      (0x7004,128),(0x7005,y if asset==5 else 70),
                                      (0x7010,int(asset==9)),(0x7011,x),(0x7012,y)):
                    s.step(f'poke:{address:04X}:{value:02X}')
                for name in ('px','py'):
                    s.step(L.poke(name,128));s.step(L.poke(name,40,1))
                s.step(L.poke('scene_cache_valid',0))
                s.step('key:MAP');s.step('press:\\r');s.step(L.until('topo_key',20000))
                rows=map_rows(screen(s).splitlines())
                marks={char:(col,row) for row,line in enumerate(rows)
                       for col,char in enumerate(line) if char in ('P',marker)}
                assert set(marks)=={'P',marker},(asset,dx,dy,marks,rows)
                p,target=marks['P'],marks[marker]
                assert (target[0]-p[0],p[1]-target[1])==(dx,dy)
                s.step('press:\\r');s.step(IDLE)
                s.step(L.poke('heading',heading));s.step(L.poke('heading',heading>>8,1))
                command(s,'V')
                page=s.step('peek:2000:8192').data
                assert header(*banks(page))==compass_pixels(heading,0)
                mood=s.step(L.peek('sky_mood')).data
                left=int.from_bytes(s.step(L.peek('sprite_left',2)).data,'little',signed=True)
                assert s.step(L.peek('scene_asset')).data==bytes((asset,))
                assert 40<=left<=75,(asset,dx,dy,heading,left,'sprite must face its MAP marker')
                assert dhgr_view(page)!=dhgr_scene(m,40*256+128,40*256+128,heading,mood,sprites=False), 'site must actually appear'
                command(s,'LOOK B')
                left=int.from_bytes(s.step(L.peek('sprite_left',2)).data,'little',signed=True)
                assert left<0 or left>=140,(asset,dx,dy,heading,left,'site behind must leave the viewport')
                behind=s.step('peek:2000:8192').data
                assert dhgr_view(behind)==dhgr_scene(m,40*256+128,40*256+128,(heading+280)%560,mood,sprites=False), 'site behind must not draw pixels'
    print('  Cabin/wreck: eight live MAP directions, compass, centered sprites and opposite views: OK',flush=True)

if __name__=='__main__': main()
