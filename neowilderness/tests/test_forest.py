#!/usr/bin/env python3
"""Native tree profiles, woodland masks, ridges, water, treeline and pans.

DHGR: the frames are compared colour pixel for colour pixel with
tools/dhgr_ref.view (terrain of view_ref.columns, canopies of
tools/forest_ref.trees, colours of the mood of the frame).
"""
import tempfile
from common import HERE,L,DISK,a2test,disk_with,view_ref,text_screen,dhgr,dhgr_view,mood_name
import dhgr_palette as P
from mkmap import forest_contours,forests,forest_bits,forest_at,MAP_BYTES,FOREST_BYTES
import forest_ref


def reference(m, px, py, heading):
    """HGR bytes of the view with its canopies (tools/forest_ref.hgr)."""
    return forest_ref.hgr(m, px, py, heading)


MOOD=['day']                    # mood of the last frames() run (sky_mood)


def dref(m, px, py, heading, forest=True):
    """DHGR logical view expected by the frames of this test (no sky body)."""
    R=dhgr()
    return R.view(m,px,py,heading,R.Sky(mood_name=MOOD[0]),forest=forest,sprites=False)


def colours(mood=None):
    t=P.MOOD[mood or MOOD[0]]
    return dict(outline=t['outline'],trunk=t['trunk'],crown=t['crown'][0],crown_even=t['crown'][1])


def map_fixture(height=10,wet=False):
    m=bytearray((HERE/'build/map.bin').read_bytes())
    m[2:8]=bytes((93,20,173,20,140,0));m[16]=0;m[21]=min(height+1,126)
    m[26]=1;m[27]=110
    m[64:MAP_BYTES]=bytes([height | (128 if wet else 0)])*9408
    m[MAP_BYTES:]=bytes([255])*FOREST_BYTES
    return m


def frames(m, turns=False):
    steps=[L.until('game_start',20000),L.poke('sky_enabled',0),L.poke('ui_enabled',0),L.poke('scenes_enabled',0),L.until('idle',20000),'peek:2000:8192',L.peek('overlay_reads',2)]
    if turns:
        for key in (r'\>',r'\<'):
            for _ in range(16):
                steps+= [f'press:{key}',L.until('turn_view',20000),L.until('idle',20000),'peek:2000:8192',L.peek('overlay_reads',2),'key:V\\r','wait:1',L.until('idle',20000),'peek:2000:8192',L.peek('overlay_reads',2)]
    steps.append(L.peek('sky_mood'))
    with tempfile.TemporaryDirectory() as tmp:
        r=a2test.run(disk_with(tmp,m),steps,emulator=a2test.A2SHOT,timeout=900)
    MOOD[0]=mood_name(r.dumps[-1])
    return r


def assert_foliage(view):
    # Visual regression: foliage must include the crown stipple and clear
    # gaps above a flat horizon. The former all-black wall fails this check.
    t=P.MOOD[MOOD[0]]
    sky={c for e in t['sky'] for c in (e if isinstance(e,tuple) else (e,))}
    crown=colours()['crown']
    assert crown not in sky
    assert sum(view[row].count(crown) for row in range(16,95))>50,'crown stipple missing'
    assert all(sum(c in sky for c in view[row])>=20 for row in range(16,95)),'crowns merged into a wall'


def main():
    native=HERE/'build/re/page1f.bin'
    if native.exists():
        data=native.read_bytes()
        for kind in range(2):
            expected=[]
            for p in range(32):
                x=min(p,30-p)
                if p==31:expected += [255,255];continue
                expected += [max(31,42-2*((x+1)//2)) if kind else (31 if x>=12 else 18+2*(x//2)),47+7*x if kind else 24+8*x]
            assert bytes(expected)==data[kind*64:(kind+1)*64]
    for level in (1,4,10):
        assert len(forest_contours(1985,level))==max(5,int(1.5*level))
        a=forests(1985,level);assert a==forests(1985,level)
        bits=forest_bits(a);assert len(bits)==294 and any(bits)
        m=map_fixture();m[MAP_BYTES:]=bits
        assert all(forest_at(m,x,y)==a[(y//2)*4+2][(x//2)*4+2] for y in range(84) for x in range(112))
    print('  native Sierra profiles and deterministic TMAKE woodland zones: OK')
    m=map_fixture()
    r=frames(m,True)
    assert dhgr_view(r.dumps[0])==dref(m,20*256+93,20*256+173,140)
    assert dhgr_view(r.dumps[0])!=dref(m,20*256+93,20*256+173,140,False),'trees missing'
    assert_foliage(dhgr_view(r.dumps[0]))
    h=140
    reads=int.from_bytes(r.dumps[1],'little')
    for i in range(32):
        h=(h+(35 if i<16 else -35))%560
        pan,counter,full,after=r.dumps[2+4*i:6+4*i]
        assert pan==full,('forest pan/full',i,h)
        assert dhgr_view(full)==dref(m,20*256+93,20*256+173,h),('forest projection',i,h)
        current=int.from_bytes(counter,'little')
        assert current==reads,'tree turns read the disk'
        reads=int.from_bytes(after,'little')
    print('  32 turns: world anchoring, cardinal rays, exact full/pan pixels, no disk reads: OK')
    trunk=map_fixture()
    trunk[4]=126
    trunk[MAP_BYTES:]=bytes(FOREST_BYTES)
    trunk[MAP_BYTES+10*7+11//8]=1<<(11%8)
    page=dhgr_view(frames(trunk).dumps[0])
    assert page==dref(trunk,5213,20*256+126,140),'trunk projection'
    c=colours()
    # Ray 70 (screen pixels 140..141 in HGR) crosses the central stem.
    assert all(page[row][70]==c['trunk'] for row in range(128,143)), 'trunk must reach ground'
    assert any(page[row][70]==c['crown'] for row in range(67,128)), 'raised crown must retain its foliage'
    assert page[67][70]==c['outline'], 'crown outline missing against sky'
    assert page[127][70]==c['trunk'], 'crown lower rim missing against terrain'
    # Type 0 used to leave solid black side fringes below the foliage.
    fringe=bytearray(trunk)
    fringe[5]=22
    fringe[4]=104
    fringe[MAP_BYTES:]=bytes(FOREST_BYTES)
    fringe[MAP_BYTES+11*7+11//8]=1<<(11%8)
    page=dhgr_view(frames(fringe).dumps[0])
    bare=dref(fringe,5213,22*256+104,140,False)
    assert page==dref(fringe,5213,22*256+104,140),'level canopy underside'
    assert all(page[row][70]==bare[row][70] for row in range(128,143)), 'black side spikes remain below canopy'
    # A nearby tree on lower ground has its crown bottom below row 255.
    # Clipping must preserve foliage rather than wrapping it into a black trunk.
    slope=map_fixture(8)
    slope[4]=126
    slope[64+20*112+20]=10
    page=dhgr_view(frames(slope).dumps[0])
    assert page==dref(slope,5213,20*256+126,140),'below-screen canopy boundary'
    assert any(page[row][70]==colours()['crown'] for row in range(144,160)), 'clipped crown lost its foliage'
    print('  solid trunks to ground, raised crowns and below-screen clipping: OK')
    # 3 * the 16-bit slope quotient used to wrap on a one-step cliff,
    # projecting a tree thousands of pixels below us back into the sky.
    for camera,ground in ((125,38),(125,39),(125,41),(0,88),(0,90)):
        cliff=map_fixture(ground)
        cliff[10]=0
        cliff[4]=126
        cliff[64+20*112+20]=camera
        page=dhgr_view(frames(cliff).dumps[0])
        assert page==dref(cliff,5213,20*256+126,140),('extreme woodland slope',camera,ground)
    print('  extreme uphill/downhill cliffs: no wrapped or floating trees OK')
    for name,case in [('water',map_fixture(wet=True)),('treeline',map_fixture(86)),('legacy',map_fixture()[:MAP_BYTES])]:
        page=dhgr_view(frames(case).dumps[0])
        assert page==dref(case,20*256+93,20*256+173,140,False),name
    sparse=map_fixture()
    sparse[MAP_BYTES:]=bytes(FOREST_BYTES)
    for y in range(42):
        for x in range(56):
            if (x+3*y)%5==0 and x>=12:
                sparse[MAP_BYTES+y*7+x//8]|=1<<(x%8)
    assert dhgr_view(frames(sparse).dumps[0])==dref(sparse,5213,5293,140),'sparse forest indexing/depth'
    ridge=map_fixture()
    for y in range(84):ridge[64+y*112+21]=125
    assert dhgr_view(frames(ridge).dumps[0])==dref(ridge,20*256+93,20*256+173,140),'ridge/tree clipping'
    behind=map_fixture()
    behind[MAP_BYTES:]=bytes(FOREST_BYTES)
    for y in range(42):
        for x in range(12,56):behind[MAP_BYTES+y*7+x//8]|=1<<(x%8)
    for y in range(84):behind[64+y*112+21]=12
    actual=dhgr_view(frames(behind).dumps[0]);bare=dref(behind,5213,5293,140,False)
    assert actual==dref(behind,5213,5293,140),'canopy above foreground ground'
    assert actual[95:]==bare[95:],'trees leaked through foreground ground'
    print('  water, alpine treeline, old maps and foreground ridge: OK')
    for height,word,char,terrain in ((10,'WOODS','T',20),(86,'SCRUB','t',30)):
        case=map_fixture(height)
        steps=[L.until('idle',20000),'key:STATUS\\r','wait:1',L.until('wait_key',20000),'peek:0400:1024',
               'key:\\e','wait:1',L.until('idle',20000),'key:MAP\\r','wait:1',L.until('topo_key',20000),'peek:0400:1024',
               'key:\\e','wait:1',L.until('idle',20000)]
        # Load the simulation directly: this checks woodland classification,
        # without also running an unrelated weather/thermal recomputation.
        addr,load,target=L['idle'],L['overlay_load'],L['fauna_environment']
        code=bytes((0xA9,3,0x20,load&255,load>>8,0x20,target&255,target>>8,0x4C,addr&255,addr>>8))
        steps += [f'poke:{addr+i:04X}:{value:02X}' for i,value in enumerate(code)]
        steps += [f'until:{addr+8:04X}:20000',L.peek('fauna_env',6)]
        with tempfile.TemporaryDirectory() as tmp:
            result=a2test.run(disk_with(tmp,case),steps,emulator=a2test.A2SHOT,timeout=900)
        assert f'GRND {word}' in '\n'.join(text_screen(result.dumps[0])),word
        screen=text_screen(result.dumps[1])
        assert any(line.count(char)>20 for line in screen),('woodland map',char)
        assert result.dumps[2][2]==terrain,('woodland fauna',terrain,result.dumps[2])
    print('  STATUS, MAP and fauna use woodland/scrub classification: OK')
    view_ref.to_png(str(HERE/'build/forest-view.png'),reference(sparse,20*256+93,20*256+173,140))
    R=dhgr()
    R.to_png(HERE/'build/forest-view-dhgr.png',dref(sparse,20*256+93,20*256+173,140))
    print('Trees and forests: OK')

if __name__=='__main__':main()
