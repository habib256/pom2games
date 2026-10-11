#!/usr/bin/env python3
"""Survival panels, transition events, grouped inventory and magnetic TOPO."""
import tempfile
from common import HERE, L, DISK, a2test, disk_with, text_screen
from test_thermal import call, poke
from fonts import glyph

IDLE=L.until('idle',20000)
DONE=f'until:{L["idle"]+3:04X}:6000'

def panels(page):
    alphabet={bytes(glyph(chr(c))[:7]):chr(c) for c in range(32,91)}
    return tuple(''.join(alphabet.get(bytes(page[a2test.hgr_offset(y+r)+x] & 127 for r in range(7)), '?')
                         for x in range(start,end)).rstrip()
                 for y,start,end in ((0,0,13),(8,0,13),(0,27,40),(8,27,40)))

def summary_display():
    steps=[IDLE,'peek:2000:8192',L.peek('s_hour',5),L.peek('s_health',5),
           'key:\\>','wait:1',IDLE,'peek:2000:8192']
    steps += call(['summary_refresh']) + [L.poke('scene_asset',0)]
    alerts={1:'HUNGER WORSE',2:'THIRST WORSE',3:'HEALTH WORSE',4:'BODY WORSE',
            5:'NOW IMMERSED',6:'DEHYDRATION',9:'HUNGER BETTER',10:'THIRST BETTER',
            11:'HEALTH BETTER',12:'BODY BETTER',13:'OUT OF WATER',14:'ILL IMPROVED'}
    for event in alerts:
        steps += [L.poke('ui_previous',1,5),L.poke('ui_pending',event),L.poke('ui_dirty',1),
                  DONE,'peek:2000:8192',L.peek('ui_pending'),IDLE]
    for mode in (1,2):
        steps += [L.poke('thermal_mode',mode),L.poke('ui_previous',0,3),L.poke('ui_previous',0,5),
                  L.poke('ui_dirty',1),DONE,'peek:2000:8192',IDLE]
    steps += [L.peek('s_hour',5),L.peek('s_health',5)]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    initial=panels(r.dumps[0])
    assert initial==('7:00 H=100%','HUNGER OKAY','THIRST OKAY','SHIVERING'),initial
    assert panels(r.dumps[3])==initial,'arrows must preserve side panels'
    for k,expected in enumerate(alerts.values()):
        assert panels(r.dumps[4+2*k])[3]==expected,(expected,panels(r.dumps[4+2*k]))
        assert r.dumps[5+2*k]==b'\0','displayed transition must be consumed once'
    assert panels(r.dumps[-4])[3]=='SWEATING' and panels(r.dumps[-3])[3]=='SHIVERING'
    assert r.dumps[1]==r.dumps[-2] and r.dumps[2]==r.dumps[-1]
    print('  exact panel glyphs, arrow persistence, twelve transition messages and thermal hint priority: OK')

def monitor():
    # Execute real overlay arithmetic without a simulation step. Event checks
    # include repeated classes and simultaneous condition replacement.
    steps=[IDLE]+call(['thermal'])+poke('s_step',0)+[DONE,IDLE]+call(['ui_monitor'])
    cases=[(0,0,0,0,0),(7,0,0,0,1),(7,0,0,0,0),(13,0,0,0,1),
           (0,0,0,0,9),(0,13,0,0,2),(0,0,0,0,10),
           (0,0,60,0,6),(0,0,60,0,0),(0,0,0,120,6),(0,0,0,0,14)]
    size=L['s_therm_factor']+5-L['s_hour']
    for eat,drink,defw,deff,event in cases:
        steps+=poke('s_eat',eat)+poke('s_drink',drink)+poke('s_defw',defw)+poke('s_deff',deff)+poke('s_defr',0)
        steps += [L.poke('ui_pending',0),L.peek('s_hour',size),DONE,L.peek('ui_pending'),L.peek('s_hour',size),IDLE]
    thermal_cases=[(.5,105,0,4),(.5,90,0,4),(.5,90,0,0),(1,98.6,0,12),
                   (1,98.6,2,5),(1,98.6,2,0),(1,98.6,0,13)]
    for factor,body,wet,event in thermal_cases:
        steps+=poke('s_therm_factor',factor)+poke('s_body',body)
        steps += [L.poke('wet_mode',wet),L.poke('ui_pending',0),L.peek('s_hour',size),
                  DONE,L.peek('ui_pending'),L.peek('s_hour',size),IDLE]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    for k,case in enumerate(cases+thermal_cases):
        before,event,after=r.dumps[k*3:k*3+3]
        assert event[0]==case[-1], (case,event)
        assert before==after, 'interface classification must not mutate simulation'
    print('  hunger/thirst/thermal/immersion, repeat suppression, recovery and replaced illness; simulation unchanged: OK')


def inventory_status():
    steps=[IDLE]
    # Empty groups, then 15 ground foods spanning two pages, with water split.
    for i in range(1,76): steps += [L.poke('it_place',255,i),L.poke('it_pack_lo',0,i),L.poke('it_pack_hi',0,i)]
    steps += ['key:INVENTORY\\r','wait:1',L.until('inventory_key',20000),'peek:0400:1024']
    for key in ('2','3','4'):
        steps += [f'key:{key}','wait:1',L.until('inventory_key',6000),'peek:0400:1024']
    steps += ['key:\\e','wait:1',IDLE]
    for i in range(22,38):
        steps += [L.poke('it_place',2,i),L.poke('it_pack_lo',10,i),L.poke('it_gnd_lo',20,i),L.poke('it_gnd_hi',0,i),
                  L.poke('it_x',0,i),L.poke('it_y',0,i)]
    steps += [L.poke('px',0,1),L.poke('py',0,1),L.peek('s_hour',5),L.peek('s_health',5),
              'key:INVENTORY\\r','wait:1',L.until('inventory_key',6000),'key:3','wait:1',L.until('inventory_key',6000),'peek:0400:1024',
              'key:N','wait:1',L.until('inventory_key',6000),'peek:0400:1024',
              'key:B','wait:1',L.until('inventory_key',6000),'peek:0400:1024',
              'key:4','wait:1',L.until('inventory_key',6000),'peek:0400:1024',
              'key:N','wait:1',L.until('inventory_key',6000),'peek:0400:1024',
              'key:\\e','wait:1',IDLE]
    # Worst simultaneous STATUS: all illnesses, cold, shelter, immersion.
    steps+=poke('s_defw',60)+poke('s_deff',120)+poke('s_defr',40)+poke('s_therm_factor',.5)+poke('s_body',90)
    steps += [L.poke('thermal_mode',2),L.poke('shelter_inside',1),L.poke('wet_mode',2),
              'key:STATUS\\r','wait:1',L.until('wait_key',20000),'peek:0400:1024',
              'key:\\e','wait:1',IDLE,L.peek('s_hour',5),L.peek('s_health',5)]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    for k,group in enumerate(('WORN','IN HAND','IN PACK','GROUND HERE')):
        screen=text_screen(r.dumps[k]); assert screen[1].startswith(group) and screen[7].startswith('NONE'),screen
        assert screen[0].startswith('INVENTORY PAGE 1/1')
    pages=[text_screen(d) for d in r.dumps[6:11]]
    for screen in pages:
        assert all(unit in screen[row] for row,unit in ((2,' OZ'),(3,' IN3'),(4,' IN3'),(5,' IN3')))
        assert screen[19].startswith('1 WORN') and screen[21].startswith('SPACE/N NEXT')
    assert pages[0][0].startswith('INVENTORY PAGE 1/2') and pages[1][0].startswith('INVENTORY PAGE 2/2')
    assert pages[0]==pages[2], 'B must return to previous page'
    for pair,qty in ((pages[:2],'10 OZ'),(pages[3:],'20 OZ')):
        rows=[line for screen in pair for line in screen[7:19] if line.strip()]
        assert len(rows)==16 and len(set(line[:15] for line in rows))==16, rows
        assert all(qty in line for line in rows),rows
    screen=text_screen(r.dumps[11]); joined='\n'.join(screen)
    assert screen[0].startswith('STATUS:'), 'worst STATUS must not scroll away its heading'
    for word in ('DEHYDRATION','STARVATION','EXHAUSTION','HYPOTHERMIA','SHIVERING','INSIDE SHELTER','IMMERSED',
                 'CARRIED FOOD 150 OZ WATER 10 OZ','HERE FOOD 300 OZ WATER 20 OZ','ENVIRONMENT:','M MEDICAL','ESC/RETURN/SPACE: VIEW'):
        assert word in joined, (word,joined)
    assert r.dumps[4]==r.dumps[12] and r.dumps[5]==r.dumps[13], 'consultation must not spend time or health'
    print('  empty groups, split ounces, unique two-page rows, capacities, back/escape; worst STATUS fits 24 rows: OK')


def map_controls():
    original=bytearray((HERE/'build/map.bin').read_bytes())
    original[2:6]=bytes((0,40,0,40)); original[13:15]=bytes((40,40));original[16:19]=bytes((1,40,40));original[8:10]=bytes((40,40))
    for decl in (-17,17):
        original[24]=decl&255
        with tempfile.TemporaryDirectory() as tmp:
            disk=disk_with(tmp,original)
            steps=[IDLE,L.peek('hud_offset',2),L.peek('s_hour',5), 'peek:2000:8192']
            for i in range(8):
                steps += [f'poke:7008:{(40 if i%3==2 else 60):02X}', f'poke:7009:{(40 if i%3==2 else 60):02X}',
                          f'poke:7011:{(40 if i%3==1 else 60):02X}', f'poke:7012:{(40 if i%3==1 else 60):02X}',
                          L.poke('heading',i*70),L.poke('heading',i*70>>8,1),
                          'key:TOPO\\r','wait:1',L.until('topo_key',20000),'peek:0400:1024',
                          'key:D','wait:1',L.until('topo_key',6000),'key:W','wait:1',L.until('topo_key',6000),
                          'key:C','wait:1',L.until('topo_key',6000),L.peek('topo_x',2),
                          'key:\\e','wait:1',IDLE]
            steps += [L.peek('s_hour',5),'peek:2000:8192']
            r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        offset=int.from_bytes(r.dumps[0],'little')
        for i in range(8):
            screen=text_screen(r.dumps[3+2*i]); head=(i*70-offset)%560
            label=('N','NE','E','SE','S','SW','W','NW')[((head+35)%560)//70]
            assert f'HEAD {head} {label} MAG' in ' '.join(screen[1].split()), screen[1]
            assert ('P+C','P+H','P+R')[i%3] in screen[3],screen[3]
            if i%3==1: assert 'ENTER SHELTER' in screen[3]
            assert r.dumps[4+2*i]==bytes((24,33)), 'C must restore player-centred map'
        assert r.dumps[1]==r.dumps[-2] and r.dumps[2]==r.dumps[-1], 'TOPO must preserve time and HGR'
    print('  eight bearings with both magnetic declinations, C recenter, player/site overlaps, clock/HGR preserved: OK')

if __name__=='__main__':
    summary_display();monitor();inventory_status();map_controls()
