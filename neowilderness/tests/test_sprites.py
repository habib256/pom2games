#!/usr/bin/env python3
"""Original compressed assets against an independent compositor.

DHGR: original codes 0..3 take the day colours of tools/dhgr_palette.SPRITES,
shaded by the mood of the frame; the terrain comes from tools/dhgr_ref.view.
Logical rows 0..159 are compared, the cached rows 0..15 included.
"""
from common import terrain_boot, HERE, L, DISK, a2test, view_ref, view_rows, hgr_rows, fp, dhgr, dhgr_view, mood_name
from re_graphics import decode
import dhgr_palette as P

MAP=(HERE/'build/map.bin').read_bytes()
SX=int.from_bytes(MAP[2:4],'little');SY=int.from_bytes(MAP[4:6],'little')
HEAD=int.from_bytes(MAP[6:8],'little')


def expected(px,py,head,name=None,bearing=0,mapbin=MAP):
    page=bytearray(view_ref.render(mapbin,px,py,head))
    if name:
        im,_=decode((HERE/f'build/original_graphics/{name}.bin').read_bytes())
        left=70-len(im[0])//2+(bearing-head+280)%560-280
        for y,row in enumerate(im):
            y-=0 if name=='wreck' else 10
            if not 0<=y<160: continue
            for x,c in enumerate(row):
                x+=left
                if c<0 or not 0<=x<140: continue
                for bit in (0,1):
                    pixel=2*x+bit;off=y*40+pixel//7;mask=1<<(pixel%7)
                    if y<view_ref.HUD_ROWS: continue
                    page[off]=(page[off]&~mask)|(mask if c&(1<<bit) else 0)
    return bytes(page)


def expected_dhgr(px,py,head,name=None,bearing=0,mapbin=MAP,mood='day'):
    """160 rows x 140 colours: terrain of the mood, then the sprite pixels."""
    R=dhgr()
    sky=R.Sky(mood_name=mood)
    view=[list(row) for row in R.view(mapbin,px,py,head,sky,forest=False,sprites=False)]
    if name:
        lit=R.lighting(sky)
        im,_=decode((HERE/f'build/original_graphics/{name}.bin').read_bytes())
        left=70-len(im[0])//2+(bearing-head+280)%560-280
        for y,row in enumerate(im):
            y-=0 if name=='wreck' else 10
            if not 0<=y<160: continue
            for x,c in enumerate(row):
                x+=left
                if c<0 or not 0<=x<140: continue
                view[y][x]=lit.sprite(P.SPRITES[name][c])
    return view


def main():
    steps=[*terrain_boot(20000),'peek:2000:8192',L.peek('sky_mood')]
    cases=[('crash at startup',SX,SY,HEAD,'wreck',HEAD)]
    def frame(label,x,y,h,name=None,bearing=0,cmd='V\r'):
        for n,v in [('px',x),('py',y),('heading',h)]:
            steps.extend([L.poke(n,v),L.poke(n,v>>8,1)])
        steps.extend([f'key:{cmd}','wait:1',L.until('idle',20000),'peek:2000:8192',L.peek('sky_mood')])
        cases.append((label,x,y,h,name,bearing))
    for delta in (35,70,105,140,280,-105,-70,-35,0):
        frame(f'crash heading {delta:+}',SX,SY,(HEAD+delta)%560,'wreck',HEAD)
    # Turns through the keyboard must erase the previous sprite as well.
    steps.extend(['key:\\>','wait:1',L.until('idle',20000),'peek:2000:8192',L.peek('sky_mood')])
    cases.append(('keyboard turn',SX,SY,(HEAD+35)%560,'wreck',HEAD))
    frame('leave crash',SX+256,SY,HEAD)
    frame('return to crash',SX,SY,HEAD,'wreck',HEAD)
    cx,cy=MAP[17]<<8,MAP[18]<<8;bh=int.from_bytes(MAP[19:21],'little')
    frame('original cabin',cx,cy,bh,'cabin',bh)
    frame('cabin edge clipping',cx,cy,(bh+90)%560,'cabin',bh)
    x,y=SX+512,SY
    for kind,name in [(6,'bear'),(7,'cougar'),(8,'rattlesnake')]:
        steps.extend([L.poke('animal_kind',kind),L.poke('animal_x',x>>8),L.poke('animal_y',y>>8),
                      L.poke('animal_bearing',10),L.poke('animal_bearing',0,1)])
        frame(f'original {name}',x,y,10,name,10)
        frame(f'{name} bearing wrap',x,y,545,name,10)
    steps.extend([L.poke('night',1),L.poke('view_dark',1)])
    frame('night hides sprites',x,y,10)
    steps.extend([L.poke('night',0),L.poke('view_dark',0),L.poke('animal_kind',0)])
    # Rendering uses explicit animals above. Native RNG and timed reactions
    # are checked by test_resource_random, test_fauna and test_animal_reactions.
    steps.extend([L.poke('animal_kind',6),L.poke('scene_minutes',1),L.poke('fauna_rng',254)])
    frame('encounter left behind',x+256,y,10)
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    bad=0
    pages=[p for p in r.dumps if len(p)==16384]
    moods=[mood_name(p) for p in r.dumps if len(p)==1]
    for case,page,mood in zip(cases,pages,moods):
        label,px,py,h,name,bearing=case
        if label.startswith('night'):
            assert mood=='night dark',(label,mood)
        ref=expected_dhgr(px,py,h,name,bearing,mood=mood)
        got=dhgr_view(page)
        n=sum(a!=b for r_,w in zip(got,ref) for a,b in zip(r_,w))
        print(f'  {label} ({mood}): {n} differing pixels' if n else f'  {label} ({mood}): OK')
        bad+=bool(n)
    assert len(r.dumps)==2*len(cases)
    if bad: raise SystemExit(1)
    print('Original sprites: OK')

if __name__=='__main__':main()
