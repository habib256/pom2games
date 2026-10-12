#!/usr/bin/env python3
"""Tree gates, clock, movement refusal, anchored pack and atomic retrieval."""
import tempfile
from common import L, a2test, disk_with, fp, text_screen
from test_forest import map_fixture
FIELDS = ('it_place','it_pack_lo','it_pack_hi','it_gnd_lo','it_gnd_hi','it_x','it_y')
IDLE=L.until('idle',12000)
def cmd(s): return [f'key:{s}\r','wait:1',IDLE]
def snap(): return [L.peek(n,76) for n in FIELDS]+[L.peek('tree_in'),L.peek('s_elap',5),L.peek('load_used',8),L.peek('px',4),L.peek('s_metabolic',5),'peek:0400:1024']
def run(steps,m=None):
    with tempfile.TemporaryDirectory() as tmp:
        return a2test.run(disk_with(tmp,m if m is not None else map_fixture()),[L.until('idle',20000)]+steps,emulator=a2test.A2SHOT,timeout=1800)
def data(r,i):
    d={n:r.mem(L[n],76,i) for n in FIELDS}
    d.update(tree=r.mem(L['tree_in'],1,i)[0],time=fp(r.mem(L['s_elap'],5,i)),load=r.mem(L['load_used'],8,i),pos=r.mem(L['px'],4,i),text='\n'.join(text_screen(r.mem(0x400,1024,i))))
    return d
def main():
    steps=[]
    for h in ((0x82,0x20,0,0,0),(0x82,0x20,0,0,1)):
        steps += [L.poke('s_health',b,j) for j,b in enumerate(h)]+cmd('CLIMB TREE')+snap()
    for c in ('WALK','SWIM','LOOK N','CLIMB DOWN'): steps+=cmd(c)+snap()
    steps+=cmd('CLIMB TREE')+[L.poke('s_health',0)]+cmd('CLIMB TREE')+snap()
    r=run(steps);d=[data(r,i) for i in range(7)]
    assert d[0]['tree']==0 and 'TOO POOR' in d[0]['text']
    assert [x['tree'] for x in d[1:]]==[1,1,1,1,0,0]
    assert all(x['time']==0 and x['pos']==d[0]['pos'] for x in d)
    assert all('YOU ARE IN A TREE' in d[i]['text'] for i in (2,3))
    assert all('CLIMB DOWN FIRST' in d[i]['text'] for i in (2,3)), 'tree refusal text corrupted by message placeholders'
    print('  native climb threshold, toggle/down, LOOK, WALK/SWIM refusal: OK',flush=True)
    cabin=map_fixture()
    cabin[16:19]=bytes((1,20,20))
    steps=cmd('CLIMB TREE')+snap()+cmd('ENTER SHELTER')+snap()+[L.peek('shelter_inside')]
    steps+=cmd('CLIMB DOWN')+cmd('ENTER SHELTER')+snap()+[L.peek('shelter_inside')]
    steps+=cmd('EXIT SHELTER')+snap()+[L.peek('shelter_inside')]
    r=run(steps,cabin);d=[data(r,i) for i in range(4)]
    assert [x['tree'] for x in d]==[1,1,0,0], 'cabin entry must not bypass tree descent'
    assert [r.mem(L['shelter_inside'],1,i) for i in range(3)]==[b'\0',b'\1',b'\0']
    assert 'CLIMB DOWN FIRST' in d[1]['text'] and 'INSIDE THE CABIN' in d[2]['text']
    assert all(x['time']==0 and x['pos']==d[0]['pos'] and x['it_place']==d[0]['it_place'] for x in d)
    print('  cabin entry from a tree refused atomically; descend, enter and exit OK',flush=True)
    steps=snap()+cmd('HANG FOOD')+snap()+cmd('HANG FOOD')+snap()+cmd('GET AXE')+cmd('DROP AXE')+cmd('DROP BACKPACK')+cmd('DROP EGGS')+snap()+cmd('EAT EGGS')+snap()
    steps+=[L.poke('px',21,1)]+cmd('GET BACKPACK')+snap()
    steps+=[L.poke('px',20,1),L.poke('load_limits',0),L.poke('load_limits',0,1)]+cmd('LOWER FOOD')+snap()
    steps+=[L.poke('load_limits',879&255),L.poke('load_limits',879>>8,1)]+cmd('GET BACKPACK')+snap()
    r=run(steps);d=[data(r,i) for i in range(8)];a,b=d[:2]
    assert b['it_place'][21]==5 and b['it_place'][58]==5
    assert b['it_place'][22]==a['it_place'][22]
    assert b['time']==0.5
    assert abs(fp(r.mem(L['s_metabolic'],5,1))-(1.65+.02*165))<1e-7
    assert int.from_bytes(b['load'][:2],'little')<int.from_bytes(a['load'][:2],'little')
    for n in ('it_pack_lo','it_pack_hi','it_gnd_lo','it_gnd_hi'): assert all(x[n]==a[n] for x in d),n
    for n in ('it_x','it_y'): assert b[n][22:38]==a[n][22:38]
    assert all(x['it_place']==b['it_place'] and x['time']==0.5 for x in d[2:7])
    assert 'LOAD CAPACITY' in d[6]['text']
    assert d[7]['it_place']==a['it_place'] and d[7]['load']==a['load']
    print('  30-minute hang, split stocks, inaccessible contents, remote/capacity refusals and GET recovery: OK',flush=True)
    r=run(cmd('PACK CANTEEN')+snap()+cmd('HANG BACKPACK')+snap()
          +cmd('DRINK WATER 1 OZ')+snap()+[L.peek('stock_available',2)]
          +cmd('EAT CHEESE 4 OZ')+snap()+[L.peek('stock_available',2)]
          +cmd('LOWER BACKPACK')+snap())
    d=[data(r,i) for i in range(5)]
    assert d[1]['it_place'][22]==d[1]['it_place'][64]==5
    assert d[2]['it_place']==d[1]['it_place'] and d[2]['it_pack_lo'][22]==64
    assert d[2]['it_gnd_lo'][22]==63
    assert d[3]['it_place'][28]==5 and d[3]['it_pack_lo'][28]==32 and d[3]['it_gnd_lo'][28]==12
    assert [int.from_bytes(r.mem(L['stock_available'],2,i),'little') for i in range(2)]==[64,16]
    assert d[4]['it_place']==d[0]['it_place'] and d[4]['load']==d[0]['load']
    print('  packed canteen, independent ground food/water, correct accessible ounces and recovery: OK',flush=True)
    steps=cmd('CLIMB TREE')+cmd('HANG FOOD')+snap()
    steps+=['key:INVENTORY\r','wait:1',L.until('inventory_key',12000),'key:5','wait:1',L.until('inventory_key',12000),'peek:0400:1024',r'press:\e','wait:1',IDLE]
    steps+=['key:STATUS\r','wait:1',L.until('status_key',12000),'peek:0400:1024',r'press:\e','wait:1',IDLE]+snap()+cmd('CLIMB DOWN')+cmd('LOWER FOOD')+snap()
    r=run(steps)
    # Extra screen peeks interleave only the text-screen occurrences.
    screens=['\n'.join(text_screen(r.mem(0x400,1024,i))) for i in range(5)]
    assert 'HUNG HERE' in screens[1] and 'BACKPACK' in screens[1]
    assert 'IN A TREE' in screens[2] and 'BACKPACK HUNG' in screens[2]
    assert r.mem(L['it_place'],76,0)==r.mem(L['it_place'],76,1)
    assert r.mem(L['tree_in'],1,2)==b'\0' and r.mem(L['it_place'],76,2)[21]==3
    print('  HUNG HERE inventory and STATUS across overlays: OK',flush=True)
    # Exercise real travel: the pack is not carried or teleported to the next cell.
    steps=cmd('NATURE 0')+snap()+cmd('HANG FOOD')+snap()
    steps+=cmd('WALK 19 MIN')+snap()+cmd('GET BACKPACK')+snap()
    steps+=cmd('LOOK W')+cmd('WALK 19 MIN')+cmd('LOWER FOOD')+snap()
    r=run(steps);d=[data(r,i) for i in range(5)]
    assert d[2]['pos'][1]==21 and d[2]['it_x'][21]==20
    assert d[3]['it_place']==d[2]['it_place'] and d[3]['time']==d[2]['time']
    assert d[4]['pos'][1]==20 and d[4]['it_place']==d[0]['it_place']
    assert d[4]['load']==d[0]['load']
    print('  real WALK away/return: anchored pack and recovered load: OK',flush=True)
    r=run([L.poke('it_place',0,21)]+cmd('HANG FOOD')+snap()+cmd('GET BACKPACK')+snap())
    assert data(r,0)['it_place'][21]==5 and data(r,1)['it_place'][21]==3
    print('  native acceptance of a nearby ground backpack: OK',flush=True)
    for name,m,setup in (('water',map_fixture(wet=True),[]),('treeline',map_fixture(height=110),[]),('bare',map_fixture(),[]),('shelter',map_fixture(),[L.poke('shelter_inside',1)]),('missing pack',map_fixture(),[L.poke('it_place',255,21)])):
        if name=='bare': m[-294:]=bytes(294)
        r=run(setup+cmd('CLIMB TREE')+snap()+cmd('HANG FOOD')+snap(),m);x,y=data(r,0),data(r,1)
        assert x['tree']==(1 if name=='missing pack' else 0),name
        assert y['time']==0 and y['it_place']==x['it_place'],name
        assert ('NEED A PACK' if name=='missing pack' else 'NOT NEAR A TREE') in y['text'],name
    print('  water, treeline, bare ground, shelter and absent pack gates: OK',flush=True)
    print('Tree actions: OK')
if __name__=='__main__': main()
