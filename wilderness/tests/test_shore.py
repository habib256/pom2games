#!/usr/bin/env python3
"""Real WALK -> repeated SWIM -> WALK crossings and atomic shore refusal."""
import tempfile
from common import HERE, L, a2test, disk_with, fp, state, text_screen

IDLE = L.until('idle', 20000)
READY = f'until:{L["idle"]:04X},{L["wait_key"]:04X}:20000'


def command(s, text):
    s.step('key:'+text)
    s.step('press:\\r')
    s.step('wait:1')
    s.step(READY)
    position=state(s.step(L.peek('px',6)).data)
    elapsed=fp(s.step(L.peek('s_elap',5)).data)*60
    message='\n'.join(text_screen(s.step('peek:0400:1024').data)[20:])
    # ESC acknowledges a report or clears an already idle command line.
    s.step('key:\\e')
    s.step('wait:1')
    s.step(IDLE)
    return position,elapsed,message


def terrain(m, position):
    return m[64+(position[1]>>8)*112+(position[0]>>8)] & 128


def lake(heading=140, fraction=0):
    m=bytearray((HERE/'build/map.bin').read_bytes())
    m[2:8]=(2560+fraction).to_bytes(2,'little')+(10240).to_bytes(2,'little')+heading.to_bytes(2,'little')
    m[8:12]=bytes((100,70,0,90))
    m[13:17]=bytes((90,90,20,0))
    m[23]=100
    m[64:]=bytes([10])*9408
    for y in range(2,82):
        for x in range(2,110):
            water=(x in (12,13) if heading in (70,140) else
                   x in (7,8) if heading==420 else
                   y in (42,43) if heading==0 else y in (37,38))
            if water: m[64+y*112+x] |= 128
    return m


def main():
    for heading,fraction in ((140,0),(140,64),(420,0),(0,0),(280,0),(70,0)):
        m=lake(heading,fraction)
        with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,m)) as s:
            s.step(IDLE)
            bank,t0,message=command(s,'WALK 1 H')
            assert not terrain(m,bank) and 'USE SWIM' in message,(heading,bank,message)
            request='SWIM 150 MIN' if heading==70 else 'SWIM 100 MIN'
            first,t1,message=command(s,request)
            assert terrain(m,first) and first!=bank and t1>t0,(heading,first,message)
            far,t2,message=command(s,request)
            assert not terrain(m,far) and far!=first and t2>t1,(heading,far,message)
            assert 'REACHED LAND. USE WALK.' in message,(heading,message)
            assert s.step(L.peek('wet_mode')).data==b'\0'
            # Repeating SWIM on the far bank cannot spend time or walk inland.
            refused,t3,message=command(s,request)
            assert refused==far and t3==t2 and 'NO WATER AHEAD' in message
            inland,t4,message=command(s,'WALK 19 MIN')
            assert inland!=far and not terrain(m,inland) and abs(t4-t3-19)<1e-5
        print(f'  heading {heading}, fraction {fraction}: WALK -> two SWIM -> dry far bank -> WALK OK')
    m=lake()
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE)
        command(s,'WALK 1 H')
        approach,t1,message=command(s,'SWIM 15 MIN')
        assert approach[:2]==(11*256+128,40*256) and not terrain(m,approach)
        assert t1>19 and s.step(L.peek('wet_mode')).data==b'\0'
        far,t2,message=command(s,'SWIM 4 H')
        assert far[:2]==(14*256,40*256) and t2>t1
        assert 'REACHED LAND' in message
    print('  A short SWIM ending on the approach half-cell can resume and cross OK')
    m=lake()
    m[64:]=bytes([10])*9408
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE)
        before=s.step(L.peek('px',6)).data
        items=s.step(L.peek('it_place',76)).data
        position,elapsed,message=command(s,'SWIM 4 H')
        assert s.step(L.peek('px',6)).data==before and elapsed==0
        assert s.step(L.peek('it_place',76)).data==items
        assert 'NO WATER AHEAD' in message
    print('  SWIM without nearby water: no movement, time or inventory changes OK')


if __name__=='__main__':
    main()
