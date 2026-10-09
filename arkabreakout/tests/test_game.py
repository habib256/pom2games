#!/usr/bin/env python3
"""Real NMOS 6502/48K regressions: ChromaBreak mechanics in native HGR."""
from pathlib import Path
import argparse
import importlib.util
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test
import dos33

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--disk',type=Path,default=ROOT/'dist/ARKABREAKOUT.dsk')
    ap.add_argument('--labels',type=Path,default=ROOT/'arkabreakout/build/game.lbl')
    args=ap.parse_args(); L=a2test.labels(args.labels)
    boot=[L.until('menu_loop',1500)]
    start=boot+['key: ',L.until('loop')]
    pause=start+['key:P','wait:15',L.until('loop'),L.poke('enemy_hold',1)]
    tick=['wait:1',L.until('loop')]
    def run(steps=(),names=(),prefix=pause):
        r=a2test.run(args.disk,list(prefix)+list(steps))
        return r
    def get(steps=(),names=(),prefix=pause):
        sizes={'score':6,'best_score':6,'bricks':96,'extra_balls':18,'level_name':11,'frames':2,'shot_live':2,'enemy_live':2}
        r=a2test.run(args.disk,list(prefix)+list(steps)+[L.peek(n,sizes.get(n,1)) for n in names])
        return {n:r.mem(L[n],sizes.get(n,1)) for n in names}
    def v(m,n): return m[n][0]
    def board(index=36,hp=1):
        return [L.poke('bricks',hp if i==index else 0,i) for i in range(96)]+[L.poke('remaining',1)]
    def ball(x,y,dx=0,dy=1,vx=0,vy=255):
        return [L.poke(n,z) for n,z in [('ball_x',x),('ball_y',y),('ball_live',1),('ball_dirx',dx),('ball_diry',dy),('ball_speed',vx),('ball_yspeed',vy),('ball_frac',255),('ball_yfrac',255),('speed',1)]]
    def play(steps): return list(steps)+['press:P']+tick
    m=get(names=['state','difficulty','pad_width','lives','ball_live','remaining','score'],prefix=start)
    assert [v(m,n) for n in ('state','difficulty','pad_width','lives','ball_live')]==[1,1,35,3,1],m
    assert m['score']==b'000000' and v(m,'remaining')>0
    for key,width,lives,speed,limit in [('1',42,5,2,4),('2',35,3,3,6),('3',28,2,4,7)]:
        m=get(names=['difficulty','pad_width','lives','speed','speed_limit'],prefix=boot+[f'key:{key}','key: ',L.until('loop')])
        assert [v(m,n) for n in ('pad_width','lives','speed','speed_limit')]==[width,lives,speed,limit],m
    m=get(['key:A','key:P','wait:8','key:S','wait:1',L.until('loop')],['pad_x','movement'])
    assert v(m,'pad_x')<112 and v(m,'movement')==0
    m=get(play([L.poke('vertical',1)]),['pad_y'])
    assert v(m,'pad_y')==172
    m=get(play([L.poke('pad_y',100),L.poke('pad_x',63)]),['pad_y'])
    assert v(m,'pad_y')>=128
    # Both pages converge once pause HUD has been presented, then remain frozen.
    r=run(['peek:2000:16384','wait:60','peek:2000:16384'])
    assert r.mem(0x2000,16384,0)==r.mem(0x2000,16384,1)
    frozen=r.mem(0x2000,16384)
    visible=[a2test.hgr_offset(y)+x for y in range(192) for x in range(40)]
    assert all(frozen[i]==frozen[i+8192] for i in visible)
    # New shared XOR renderer restores colour and bit 7 at all alignments.
    fixture=[L.poke('ball_live',0),'press:P']+tick+['key:P','wait:15',L.until('loop')]
    baseline=run(fixture+['peek:2000:16384']).mem(0x2000,16384)
    for kind in range(1,7):
        for align in range(7):
            steps=fixture+[L.poke('capsule',kind),L.poke('cap_x',98+align),L.poke('cap_y',48),'key:P','wait:5','key:P','wait:15',L.poke('capsule',0),'key:P','wait:5','key:P','wait:15','peek:2000:16384']
            data=run(steps).mem(0x2000,16384)
            assert all(data[i]==baseline[i] for i in visible),(kind,align,'XOR damaged background')
    # Axes, steel, resistant and piercing impacts, with a second target to avoid loading.
    for hp,effect,expected in [(1,0,0),(3,0,2),(255,0,255),(3,6,0),(255,6,255)]:
        steps=board(hp=hp)+[L.poke('bricks',1,95),L.poke('remaining',2)]+ball(10,68)+[L.poke('effect',effect)]
        m=get(play(steps),['bricks','score','ball_diry'])
        assert m['bricks'][36]==expected,(hp,effect,m)
        assert m['score']==(b'000000' if hp==255 else b'000010')
        if effect==6 and hp!=255: assert v(m,'ball_diry')==1
    for x,y,dx,dy,vx,expected in [(2,145,1,1,255,'ball_dirx'),(100,18,0,1,0,'ball_diry')]:
        m=get(play(board()+ball(x,y,dx,dy,vx)),[expected])
        assert v(m,expected)==0
    # A life is lost only after the last ball; catch and paddle rebound.
    for ypad in (175,140):
        m=get(play(board()+ball(113,ypad-4,dy=0)+[L.poke('pad_y',ypad)]),['ball_diry','ball_speed','multiplier'])
        assert v(m,'ball_diry')==1 and v(m,'ball_speed')==240 and v(m,'multiplier')==1,m
    m=get(play(board()+ball(125,171,dy=0)+[L.poke('effect',3)]),['ball_live','lives'])
    assert v(m,'ball_live')==0 and v(m,'lives')==3
    m=get(play(board()+ball(20,179,dy=0)),['ball_live','lives'])
    assert v(m,'ball_live')==0 and v(m,'lives')==2,m
    m=get(play(board()+ball(20,179,dy=0)+[L.poke('extra_balls',120,0),L.poke('extra_balls',140,1),L.poke('extra_balls',1,2)]),['lives','extra_balls'])
    assert v(m,'lives')==3
    # Space cannot revive a lost primary ball while an extra one is flying.
    fixture=board()+ball(20,179,dy=0)+[L.poke('extra_balls',120,0),L.poke('extra_balls',140,1),L.poke('extra_balls',1,2)]
    m=get(play(fixture)+['key: ']+tick,['lives','ball_x'])
    assert v(m,'lives')==3 and v(m,'ball_x')==120,m
    # Each of eight paddle zones remains symmetric at both widths.
    for width in (28,42):
        vectors=[]
        for zone in range(8):
            hit=width*(zone*2+1)//16
            m=get(play(board()+ball(112+hit-1,171,dy=0)+[L.poke('pad_width',width)]),['ball_dirx','ball_speed','ball_yspeed'])
            assert v(m,'ball_dirx')==(1 if zone<4 else 0)
            vectors.append((v(m,'ball_speed'),v(m,'ball_yspeed')))
        assert vectors==vectors[::-1],vectors
    # Combos advance every third destroyed tile, never on merely removing HP.
    for combo,mult in [(1,1),(2,2),(5,3),(20,8),(21,8)]:
        m=get(play(board()+[L.poke('bricks',1,95),L.poke('remaining',2)]+ball(10,68)+[L.poke('combo',combo)]),['multiplier','score'])
        assert v(m,'multiplier')==mult and m['score']==f'{mult*10:06}'.encode(),m
    # Difficulty ramps, Slow stays slow, and the cap never overflows.
    for effect,normal,expected in [(0,3,4),(2,3,2),(0,6,6)]:
        fixture=board()+[L.poke('bricks',1,95),L.poke('remaining',2)]+ball(10,68)
        fixture += [L.poke('ramp_hits',7),L.poke('normal_speed',normal),L.poke('effect',effect),L.poke('speed',2 if effect==2 else normal)]
        m=get(play(fixture),['speed','ramp_hits'])
        assert v(m,'speed')==expected and v(m,'ramp_hits')==0,m
    # All six capsule kinds occur in sequence, with only one falling at once.
    for kind in range(1,7):
        fixture=board()+[L.poke('bricks',1,95),L.poke('remaining',2)]+ball(10,68)+[L.poke('hit_count',4),L.poke('cap_next',kind)]
        m=get(play(fixture),['capsule','cap_next'])
        assert v(m,'capsule')==kind and v(m,'cap_next')==(kind%6)+1,m
    # Extra life at 5000, five-life cap and six-digit saturation at 650000.
    for lives,expected in [(3,4),(5,5)]:
        steps=board()+[L.poke('bricks',1,95),L.poke('remaining',2)]+ball(10,68)+[L.poke('life_hits',243),L.poke('life_hits',1,1),L.poke('lives',lives)]
        m=get(play(steps),['lives'])
        assert v(m,'lives')==expected
    steps=board()+[L.poke('bricks',1,95),L.poke('remaining',2)]+ball(10,68)+[L.poke('score',ord(c),i) for i,c in enumerate('649990')]+[L.poke('combo',20)]
    m=get(play(steps),['score']);assert m['score']==b'650000',m
    # All six capsules are collected at the moving paddle.
    for kind in range(1,7):
        m=get(play(board()+[L.poke('ball_live',0),L.poke('capsule',kind),L.poke('cap_x',120),L.poke('cap_y',169)]),['capsule','effect','pad_width','speed','extra_balls','ball_live'])
        assert v(m,'capsule')==0 and v(m,'effect')==kind,m
        assert v(m,'pad_width')==(49 if kind==1 else 35)
        if kind==2: assert v(m,'speed')==2
        if kind==4: assert m['extra_balls'][2]==m['extra_balls'][11]==v(m,'ball_live')==1,m
    # Laser damages a tile; a new bonus replaces active shots.
    m=get(play(board()+[L.poke('effect',5),L.poke('shot_live',1),L.poke('shot_x',10),L.poke('shot_y',68),L.poke('bricks',1,95),L.poke('remaining',2)]),['bricks','shot_live','score'])
    assert m['bricks'][36]==0 and m['shot_live'][0]==0 and m['score']==b'000010',m
    # Enemy contact awards 100 points and makes the ball bounce.
    m=get(play(board()+ball(100,140)+[L.poke('enemy_live',1),L.poke('enemy_x',101),L.poke('enemy_y',140),L.poke('enemy_dx',1)]),['enemy_live','score','ball_diry'])
    assert m['enemy_live'][0]==0 and m['score']==b'000100' and v(m,'ball_diry')==0,m
    # Each disk pack equals the authored boards; cross every decade in the real loader.
    spec=importlib.util.spec_from_file_location('arka_levels',ROOT/'arkabreakout/tools/pack_levels.py');packer=importlib.util.module_from_spec(spec);spec.loader.exec_module(packer)
    levels=packer.load();packer.check(levels)
    image=args.disk.read_bytes()
    for pack in range(6):
        assert dos33.read_file(image,f'LEVELS{pack+1}')==(args.labels.parent/f'levels{pack+1}.bin').read_bytes()
    for n,(name,cells) in enumerate(levels):
        # Force a sector clear before the next loop, including first and last pack.
        if n==0:
            m=get(names=['bricks','remaining','level_name'],prefix=start)
        else:
            steps=ball(100,140)+[L.poke('level',n-1),L.poke('remaining',0),'key:P','wait:3',L.until('loop')]
            m=get(steps,['level','bricks','remaining','level_name'])
            assert v(m,'level')==n
        assert list(m['bricks'])==cells,(n,name,m['bricks'])
        assert v(m,'remaining')==sum(0<c<255 for c in cells)
        assert m['level_name']==name.ljust(10).encode()+b'\0'
    m=get(ball(100,140)+[L.poke('level',59),L.poke('remaining',0),'press:P','wait:240'],['state'])
    assert v(m,'state')==3
    # Joystick/paddles, both buttons, height, optional X calibration.
    for axis,px in [(-1,2),(1,216)]:
        m=get([f'joy:{axis},1','wait:10'],['pad_x','pad_y','mode'],prefix=boot+['key:J',L.until('loop')])
        assert v(m,'pad_x')==px and v(m,'pad_y')==175 and v(m,'mode')==1,m
    m=get(['joy:0,-1','wait:10'],['pad_y'],prefix=boot+['key:J',L.until('loop')]);assert 100<=v(m,'pad_y')<=128
    # ESC freezes the simulation, R rebuilds pages, Q returns to DOS; RESET too.
    r=run(['key:\\e','wait:15','key:R','wait:8',L.peek('paused')]);assert r.mem(L['paused'],1)==b'\1'
    for steps in [('key:\\e','key:Q'),('reset',)]:
        r=run(list(steps)+['wait:300','peek:03F2:3','text'])
        assert r.mem(0x3f2,2)==bytes([0xbf,0x9d]) and ']' in r.out
    # Preview crosses packs without changing the running board or progress.
    boards=packer.load()
    for sector in (0,9,10,59):
        steps=[L.poke('furthest',59),'key:\\e',L.until('menu_input')]
        steps += ['key:D',L.until('menu_input')]*sector
        steps += [L.peek('menu_sector'),L.peek('level'),L.peek('bricks',96)]
        for row in range(8):
            y=48+row*6
            addr=0x2000+(y%8)*1024+((y//8)%8)*128+(y//64)*40+26
            steps += [f'peek:{addr:04X}:12']
        steps += ['key:R',L.until('loop'),L.peek('level_name',11),L.peek('bricks',96)]
        r=run(steps)
        assert r.mem(L['menu_sector'],1)==bytes([sector])
        assert r.mem(L['level'],1)==b'\0'
        assert list(r.mem(L['bricks'],96,0))==boards[0][1]
        assert r.mem(L['bricks'],96,0)==r.mem(L['bricks'],96,1)
        assert r.mem(L['level_name'],11)==boards[0][0].ljust(10).encode()+b'\0'
        colors={0:0,1:0x2a,2:0x55,3:0x3f,255:0xbf}
        for row in range(8):
            y=48+row*6
            addr=0x2000+(y%8)*1024+((y//8)%8)*128+(y//64)*40+26
            assert r.mem(addr,12)==bytes(colors[c] for c in boards[sector][1][row*12:row*12+12])
    m=get([L.poke("state",3),L.poke("level",60),L.poke("furthest",59),"key:\\e",L.until("menu_input"),"key:D",L.until("menu_input")],["menu_sector","level"])
    assert v(m,"menu_sector")==59 and v(m,"level")==60
    # Active and stressed frame rates on the 1 MHz 48K machine.
    for name,fixture in [('normal',[]),('multiball',[L.poke('effect',4),L.poke('capsule',4),L.poke('cap_x',120),L.poke('cap_y',169)]),('enemies',[L.poke('enemy_live',1),L.poke('enemy_live',1,1),L.poke('enemy_x',60),L.poke('enemy_x',180,1),L.poke('enemy_y',140),L.poke('enemy_y',145,1)])]:
        r=run(fixture+['press:P']+tick+[L.peek('frames',2),'wait:120',L.peek('frames',2)])
        hz=(int.from_bytes(r.mem(L['frames'],2,1),'little')-int.from_bytes(r.mem(L['frames'],2,0),'little'))/2
        assert hz>=26,(name,hz)
        print(f'{name}: {hz:g} updates/s')
    print('ARKABREAKOUT: 60 boards, six bonuses, multiball, laser, pierce, enemies, difficulty, combo, vertical paddle, HGR restoration and DOS exit passed.')
if __name__=='__main__': main()
