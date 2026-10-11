#!/usr/bin/env python3
"""Native tree profiles, woodland masks, ridges, water, treeline and pans."""
import tempfile
from common import HERE,L,DISK,a2test,disk_with,view_ref,view_rows,text_screen
from mkmap import forest_contours,forests,forest_bits,forest_at,MAP_BYTES,FOREST_BYTES


def reference(m, px, py, heading):
    fb=bytearray(view_ref.render(m,px,py,heading))
    eye=(m[64+(py>>8)*112+(px>>8)]&127)+2
    for col in range(140):
        dx,dy=view_ref.direction(heading-70+col)
        x,y=px,py;thr=-32768;inc=0;top=160;tree=None
        for n in range(1,129):
            x=(x+dx)&65535;y=(y+dy)&65535
            cx,cy=x>>8,y>>8
            if cx>=112 or cy>=84:break
            cell=m[64+cy*112+cx];dz=(cell&127)-eye
            if n<=8 and tree is None and not cell&128 and (cell&127)+m[10]<(m[27] or 110) and forest_at(m,cx,cy):
                p=((x if abs(dy)>=abs(dx) else y)&255)-96
                p//=2
                if 0<=p<31:
                    p=min(p,30-p)
                    kind=(cx^cy)&2
                    lo=max(31,42-2*((p+1)//2)) if kind else 31
                    hi=47+7*p if kind else 24+8*p
                    q=(abs(dz)*256)//n;off=(q*3)>>4
                    base=95-off if dz>=0 else 95+off
                    if off<256 and base>=0:
                        begin=max(0,base-hi//n)
                        end=min(top,base-(0 if p>=14 else lo)//n)
                        if begin<160 and end>begin:tree=(begin,end,cx,base-32//n)
            thr+=inc
            if thr>32767:break
            thr=max(thr,-32768)
            if dz<=thr>>8:continue
            q=(abs(dz)<<8)//n;inc=-q if dz<0 else q;thr=dz<<8
            if inc>=512:off=95
            elif inc < -512:continue
            else:
                off=min((inc*3)>>4,95)
                if off < -64:continue
            row=95-off
            if row<top:
                top=row
                if not top:break
        if tree:
            for r in range(max(16,tree[0]),tree[1]):
                for p in (2*col,2*col+1):
                    fb[r*40+p//7]&=~(1<<(p%7))
                    if tree[0]<r<tree[3] and (r^tree[2])&1 and p&1:fb[r*40+p//7]|=1<<(p%7)
    return bytes(fb)


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
    with tempfile.TemporaryDirectory() as tmp:
        return a2test.run(disk_with(tmp,m),steps,emulator=a2test.A2SHOT,timeout=900)


def assert_foliage(page):
    # Visual regression: foliage must include native green stipple and clear
    # gaps above a flat horizon. The former all-black wall fails this check.
    colors=[]
    for row in range(16,95):
        line=[]
        for col in range(140):
            p=2*col
            even=(page[row*40+p//7]>>(p%7))&1
            odd=(page[row*40+(p+1)//7]>>((p+1)%7))&1
            line.append(even+2*odd)
        colors.append(line)
    assert sum(line.count(2) for line in colors)>50,'native green foliage missing'
    assert all(line.count(1)>=20 for line in colors),'crowns merged into a wall'


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
    assert view_rows(r.dumps[0])==reference(m,20*256+93,20*256+173,140)
    assert view_rows(r.dumps[0])!=view_ref.render(m,20*256+93,20*256+173,140),'trees missing'
    assert_foliage(view_rows(r.dumps[0]))
    h=140
    reads=int.from_bytes(r.dumps[1],'little')
    for i in range(32):
        h=(h+(35 if i<16 else -35))%560
        pan,counter,full,after=r.dumps[2+4*i:6+4*i]
        assert pan==full,('forest pan/full',i,h)
        assert view_rows(full)==reference(m,20*256+93,20*256+173,h),('forest projection',i,h)
        current=int.from_bytes(counter,'little')
        assert current==reads,'tree turns read the disk'
        reads=int.from_bytes(after,'little')
    print('  32 turns: world anchoring, cardinal rays, exact full/pan pixels, no disk reads: OK')
    trunk=map_fixture()
    trunk[4]=126
    trunk[MAP_BYTES:]=bytes(FOREST_BYTES)
    trunk[MAP_BYTES+10*7+11//8]=1<<(11%8)
    page=view_rows(frames(trunk).dumps[0])
    assert page==reference(trunk,5213,20*256+126,140),'trunk projection'
    def pixel(row,x):return (page[row*40+x//7]>>(x%7))&1
    assert all(pixel(row,x)==0 for row in range(128,143) for x in (140,141)), 'trunk must reach ground'
    assert any(pixel(row,141) for row in range(67,128)), 'raised crown must retain green foliage'
    assert pixel(67,140)==pixel(67,141)==0, 'crown outline missing against sky'
    assert pixel(127,140)==pixel(127,141)==0, 'crown lower rim missing against terrain'
    # Type 0 used to leave solid black side fringes below the foliage.
    fringe=bytearray(trunk)
    fringe[5]=22
    fringe[4]=104
    fringe[MAP_BYTES:]=bytes(FOREST_BYTES)
    fringe[MAP_BYTES+11*7+11//8]=1<<(11%8)
    page=view_rows(frames(fringe).dumps[0])
    bare=view_ref.render(fringe,5213,22*256+104,140)
    assert page==reference(fringe,5213,22*256+104,140),'level canopy underside'
    assert all(pixel(row,x)==((bare[row*40+x//7]>>(x%7))&1)
               for row in range(128,143) for x in (140,141)), 'black side spikes remain below canopy'
    # A nearby tree on lower ground has its crown bottom below row 255.
    # Clipping must preserve foliage rather than wrapping it into a black trunk.
    slope=map_fixture(8)
    slope[4]=126
    slope[64+20*112+20]=10
    page=view_rows(frames(slope).dumps[0])
    assert page==reference(slope,5213,20*256+126,140),'below-screen canopy boundary'
    assert any((page[row*40+141//7]>>(141%7))&1 for row in range(144,160)), 'clipped crown lost its foliage'
    print('  solid trunks to ground, raised crowns and below-screen clipping: OK')
    for name,case in [('water',map_fixture(wet=True)),('treeline',map_fixture(86)),('legacy',map_fixture()[:MAP_BYTES])]:
        page=view_rows(frames(case).dumps[0])
        assert page==view_ref.render(case,20*256+93,20*256+173,140),name
    sparse=map_fixture()
    sparse[MAP_BYTES:]=bytes(FOREST_BYTES)
    for y in range(42):
        for x in range(56):
            if (x+3*y)%5==0 and x>=12:
                sparse[MAP_BYTES+y*7+x//8]|=1<<(x%8)
    assert view_rows(frames(sparse).dumps[0])==reference(sparse,5213,5293,140),'sparse forest indexing/depth'
    ridge=map_fixture()
    for y in range(84):ridge[64+y*112+21]=125
    assert view_rows(frames(ridge).dumps[0])==reference(ridge,20*256+93,20*256+173,140),'ridge/tree clipping'
    behind=map_fixture()
    behind[MAP_BYTES:]=bytes(FOREST_BYTES)
    for y in range(42):
        for x in range(12,56):behind[MAP_BYTES+y*7+x//8]|=1<<(x%8)
    for y in range(84):behind[64+y*112+21]=12
    actual=view_rows(frames(behind).dumps[0]);bare=view_ref.render(behind,5213,5293,140)
    assert actual==reference(behind,5213,5293,140),'canopy above foreground ground'
    assert actual[95*40:]==bare[95*40:],'trees leaked through foreground ground'
    print('  water, alpine treeline, old maps and foreground ridge: OK')
    for height,word,char,terrain in ((10,'WOODS','T',20),(86,'SCRUB','t',30)):
        case=map_fixture(height)
        steps=[L.until('idle',20000),'key:STATUS\\r','wait:1',L.until('wait_key',20000),'peek:0400:1024',
               'key:\\e','wait:1',L.until('idle',20000),'key:TOPO\\r','wait:1',L.until('topo_key',20000),'peek:0400:1024',
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
    print('  STATUS, TOPO and fauna use woodland/scrub classification: OK')
    view_ref.to_png(str(HERE/'build/forest-view.png'),reference(sparse,20*256+93,20*256+173,140))
    print('Trees and forests: OK')

if __name__=='__main__':main()
