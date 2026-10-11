#!/usr/bin/env python3
"""Distant original sites: geometry, depth, rotation, clipping and caching."""
import tempfile
from common import terrain_boot, HERE,L,a2test,disk_with,view_rows,hgr_rows
import scene_ref
from test_sites import command,hours


def mapbin():
    m=bytearray((HERE/'build/map.bin').read_bytes())
    m[2:8]=bytes((0,8,0,8,140,0))
    m[8:10]=bytes((100,40))
    m[16:22]=bytes((1,20,20,140,0,11))
    m[64:]=bytes([10])*9408
    return bytes(m)


def cases(m,positions,label):
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,m)
        steps=[*terrain_boot(20000)]
        for x,y,head in positions:
            for name,value in [('px',x),('py',y),('heading',head)]:
                steps += [L.poke(name,value),L.poke(name,value>>8,1)]
            steps += ['key:V\r','wait:1',L.until('idle',20000),'peek:2000:8192']
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    for (x,y,head),page in zip(positions,r.dumps):
        ref=scene_ref.render(m,x,y,head)
        differences=sum(a!=b for a,b in zip(view_rows(page),ref))
        assert not differences,(label,x,y,head,differences,scene_ref.select(m,x,y,head))
    assert len(r.dumps)==len(positions)
    print(f'  {label}: {len(positions)} exact frames OK')


def main():
    m=mapbin()
    positions=[]
    # All quadrants, cardinal/diagonal bearings, fractional positions and
    # distance buckets. Wreck uses the original crash coordinate; cabin is
    # fixed at the cell centre.
    for sx,sy in [(8*256,8*256),(20*256+128,20*256+128)]:
        for dx,dy,h in [(1,0,420),(-2,0,140),(0,3,0),(0,-4,280),
                        (3,3,490),(-3,-3,210),(7,0,420),(8,0,420)]:
            positions.append((sx+dx*256,sy+dy*256,h))
    for head in (0,35,70,105,140,175,210,280,420,525):
        positions.append((18*256+128,20*256+128,head))
    positions += [(18*256+64,20*256+192,140),(20*256+128,20*256+128,140)]
    positions += [(12*256+192,20*256+128,140),(28*256+64,20*256+128,420),
                  (12*256+128,20*256+128,140),(28*256+128,20*256+128,420)]
    cases(m,positions,'bearings, scales, viewport edges and distance limit')

    partial=bytearray(m)
    # A foreground ridge covers the lower cabin, while its roof is visible.
    for y in range(18,23): partial[64+y*112+19]=11
    partial[21]=12
    p=(18*256+128,20*256+128,140)
    assert scene_ref.render(partial,*p)!=scene_ref.view_ref.render(partial,*p)
    assert scene_ref.render(partial,*p)!=scene_ref.render(m,*p)
    cases(partial,[(18*256+128,20*256+128,h) for h in (105,140,175)],'partial foreground occlusion')
    blocked=bytearray(m)
    for y in range(16,25): blocked[64+y*112+19]=30
    blocked[21]=31
    p=(18*256+128,20*256+128,140)
    assert scene_ref.render(blocked,*p)==scene_ref.view_ref.render(blocked,*p)
    cases(blocked,[p,(18*256+128,20*256+128,105)],'fully hidden site')

    both=bytearray(m)
    both[2:8]=bytes((128,22,128,20,164,1))
    cases(both,[(18*256+128,20*256+128,140),
                (21*256+128,20*256+128,420)],'nearest of two visible sites')
    behind=bytearray(m)
    for y in range(16,25): behind[64+y*112+23]=30
    behind[21]=31
    cases(behind,[p],'ridge behind the site keeps its sprite visible')
    for level in (5,9,13,25):
        height=bytearray(m)
        height[64+20*112+20]=level
        height[21]=max(10,level)+1
        cases(height,[p],f'site ground level {level}')
    transitions(m)
    walking()
    print('Distant sites: OK')


def transitions(m):
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,m)
        x,y=18*256+128,20*256+128
        steps=[*terrain_boot(20000)]
        for name,value in [('px',x),('py',y),('heading',0)]:
            steps += [L.poke(name,value),L.poke(name,value>>8,1)]
        steps += command('V')+['peek:2000:8192']
        for _ in range(8): steps += ['key:\\>','wait:1',L.until('idle',20000),'peek:2000:8192']
        for name,value in [('heading',140)]:
            steps += [L.poke(name,value),L.poke(name,value>>8,1)]
        steps += command('V')+[L.peek('overlay_reads',2),'peek:2000:8192']
        steps += command('V')+[L.peek('overlay_reads',2),'peek:2000:8192']
        steps += ['key:STATUS\r','wait:1',L.until('wait_key',6000),
                  'key: ','wait:1',L.until('idle',20000),'peek:2000:8192']
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    for head,page in zip(range(0,281,35),r.dumps[:9]):
        assert view_rows(page)==scene_ref.render(m,x,y,head),head
    assert int.from_bytes(r.dumps[11],'little')-int.from_bytes(r.dumps[9],'little')==2
    assert hgr_rows(r.dumps[10],16)==hgr_rows(r.dumps[12],16)==hgr_rows(r.dumps[13],16)
    print('  keyboard turns enter/leave the field; repeated VIEW skips projection reads; STATUS preserves it: OK')


def walking():
    m=bytearray(mapbin())
    m[16:21]=bytes((1,14,8,140,0))
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,m)
        steps=[*terrain_boot(20000)]
        positions=[(11*256,8*256,140),(14*256,8*256,140),
                   (17*256,8*256,140),(17*256,8*256,420),(14*256,8*256,420)]
        for cmd in (hours('WALK',1),hours('WALK',1),hours('WALK',1),command('LOOK B'),hours('WALK',1)):
            steps += cmd+[L.peek('px',6),'peek:2000:8192']
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    for k,p in enumerate(positions):
        got=tuple(int.from_bytes(r.dumps[2*k][o:o+2],'little') for o in (0,2,4))
        assert got==p,(got,p)
        assert view_rows(r.dumps[2*k+1])==scene_ref.render(m,*p)
    print('  walk toward the cabin, arrive, leave, turn and return without teleportation: OK')


if __name__=='__main__':
    main()
