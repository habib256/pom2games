#!/usr/bin/env python3
"""Distant original sites: geometry, depth, rotation, clipping and caching."""
import tempfile
from common import terrain_boot, HERE,L,a2test,disk_with,hgr_rows,dhgr_view,dhgr_scene,mood_name
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
        steps += [L.peek('sky_mood')]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    mood=r.dumps[-1]
    for (x,y,head),page in zip(positions,r.dumps):
        ref=dhgr_scene(m,x,y,head,mood)
        got=dhgr_view(page)
        differences=sum(a!=b for g,w in zip(got,ref) for a,b in zip(g,w))
        assert not differences,(label,x,y,head,differences,scene_ref.select(m,x,y,head))
    assert len(r.dumps)==len(positions)+1
    print(f'  {label}: {len(positions)} exact frames OK')


def main():
    m=mapbin()
    positions=[]
    # All quadrants, cardinal/diagonal bearings, fractional positions and
    # distance buckets. Wreck uses the original crash coordinate; cabin is
    # fixed at the cell centre.
    for sx,sy in [(8*256,8*256),(20*256+128,20*256+128)]:
        for dx,dy,h in [(1,0,420),(-2,0,140),(0,3,280),(0,-4,0),
                        (3,3,350),(-3,-3,70),(7,0,420),(8,0,420)]:
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
    # A nearby cabin below a steep cliff must not wrap back into the view.
    # Include the exact 3*q overflow boundary and the maximum map height.
    for level in (80,81,82,83,84,85,86,87,125):
        cliff=bytearray(m)
        cliff[64:]=bytes([level])*9408
        cliff[64+20*112+20]=0
        cliff[21]=min(127,level+1)
        positions=[(19*256+250,20*256+128,head) for head in (105,140,175)]
        assert all(scene_ref.select(cliff,*position) is None for position in positions)
        cases(cliff,positions,f'cabin below cliff level {level}')
    transitions(m)
    walking()
    outpost()
    print('Distant sites: OK')


# Directions from the player toward the outpost: (east, north) and heading.
EIGHT=[((0,1),0),((1,1),70),((1,0),140),((1,-1),210),((0,-1),280),((-1,-1),350),((-1,0),420),((-1,1),490)]


def outpost():
    """The ranger outpost (lot 6): a billboard from 1 to 8 cells in the eight
    directions, the local view on the goal cell, pixel for pixel against
    tools/dhgr_ref; read from NEOWILD.BLK once per appearance (5 blocks into
    the SIM window): never again while it stays there (more views, a turn,
    STATUS and back), once more after the simulation took the window."""
    m=bytearray(mapbin())
    m[8:10]=bytes((40,40))
    gx,gy=40*256+128,40*256+128
    positions=[(gx,gy,140),(gx,gy,0)]
    for (dx,dy),h in EIGHT:
        for k in range(1,9 if 0 in (dx,dy) else 6):
            positions.append((gx-k*dx*256,gy-k*dy*256,h))
    positions.append((gx-9*256,gy,140))             # out of range: no sprite
    # 8 cells is the limit itself (distance < 8): four positions see nothing.
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,m)
        steps=[*terrain_boot(20000),L.peek('mli_reads',2)]
        for x,y,head in positions:
            for name,value in [('px',x),('py',y),('heading',head)]:
                steps += [L.poke(name,value),L.poke(name,value>>8,1)]
            steps += ['key:V\r','wait:1',L.until('idle',20000),'peek:2000:8192',L.peek('mli_reads',2)]
        x,y,head=positions[2]
        for name,value in [('px',x),('py',y),('heading',head)]:
            steps += [L.poke(name,value),L.poke(name,value>>8,1)]
        steps += command('V')+[L.peek('mli_reads',2)]
        steps += ['key:\\>','wait:1',L.until('idle',20000),L.peek('mli_reads',2)]
        steps += ['key:STATUS\r','wait:1',L.until('wait_key',6000),
                  'key: ','wait:1',L.until('idle',20000),L.peek('mli_reads',2)]
        steps += command('V')+[L.peek('mli_reads',2)]
        steps += hours('REST',1)+[L.peek('mli_reads',2)]
        steps += [L.peek('sky_mood'),L.peek('scene_asset')]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    words=[int.from_bytes(d,'little') for d in r.dumps if len(d)==2]
    pages=[d for d in r.dumps if len(d)==16384]
    mood=r.dumps[-2]
    assert len(pages)==len(positions)
    seen=0
    for (x,y,head),page in zip(positions,pages):
        g=scene_ref.select(m,x,y,head)
        ref=dhgr_scene(m,x,y,head,mood)
        got=dhgr_view(page)
        differences=sum(a!=b for gg,w in zip(got,ref) for a,b in zip(gg,w))
        assert not differences,(x,y,head,differences,g)
        seen+=bool(g and g['asset']==35)
    assert seen==len(positions)-5,seen
    reads=[b-a for a,b in zip(words,words[1:])]
    frames=reads[:len(positions)]
    assert frames[0]==5 and not any(frames[1:]),frames
    turn,status_back,view,rest=reads[len(positions)+1:]
    assert reads[len(positions)]==0 and (turn,status_back,view)==(0,0,5) and rest==5,reads[len(positions):]
    assert r.dumps[-1]==bytes((35,))
    print(f'  ranger outpost: {seen} exact frames (1 to 7 cells, nothing at 8, eight directions, local at the goal); '
          f'read once (5 blocks) per appearance, none for views, turns or STATUS, again after REST: OK')


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
                  'key: ','wait:1',L.until('idle',20000),'peek:2000:8192',L.peek('sky_mood')]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    for head,page in zip(range(0,281,35),r.dumps[:9]):
        assert dhgr_view(page)==dhgr_scene(m,x,y,head,r.dumps[-1]),head
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
        # Six separately requested native half-steps travel exactly three cells.
        leg=command('WALK 9 MIN')*6
        for cmd in (leg,leg,leg,command('LOOK B'),leg):
            steps += cmd+[L.peek('px',6),'peek:2000:8192',L.peek('sky_mood')]
        r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    for k,p in enumerate(positions):
        got=tuple(int.from_bytes(r.dumps[3*k][o:o+2],'little') for o in (0,2,4))
        assert got==p,(got,p)
        assert dhgr_view(r.dumps[3*k+1])==dhgr_scene(m,*p,r.dumps[3*k+2])
    print('  walk toward the cabin, arrive, leave, turn and return without teleportation: OK')


if __name__=='__main__':
    main()
