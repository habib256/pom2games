#!/usr/bin/env python3
"""Survival panels, transition events, grouped inventory and magnetic TOPO."""
import tempfile
from common import HERE, L, DISK, a2test, disk_with, text_screen, dhgr_page, result_text, map_cue
from test_thermal import call, poke
import dhgr_ui

IDLE=L.until('idle',20000)
DONE=f'until:{L["idle"]+3:04X}:6000'

def panels(page):
    """The four field texts (lot 4: native DHGR panels, tools/dhgr_ui.py)."""
    return dhgr_ui.panels(dhgr_page(page))


def warned(page, field, text):
    """True when the characters of `text` in a field are white on the red
    warning strip (the inverse strip of the HGR panels)."""
    chars = [c for c in dhgr_ui.styles(dhgr_page(page), field) if c[0] != ' ']
    want = [c for c in text if c != ' ']
    for i in range(len(chars) - len(want) + 1):
        if [c[0] for c in chars[i:i + len(want)]] == want:
            return all(ink == dhgr_ui.WHITE and bg == dhgr_ui.WARN for _, ink, bg in chars[i:i + len(want)])
    raise AssertionError((text, chars))

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
    assert initial==('HEALTH 100%','SHIVERING','7:00 DAY 1','HUNGER OKAY'),initial
    assert panels(r.dumps[3])==initial,'arrows must preserve side panels'
    for k,expected in enumerate(alerts.values()):
        assert panels(r.dumps[4+2*k])[1]==expected,(expected,panels(r.dumps[4+2*k]))
        inverse=list(alerts)[k]<9
        assert warned(r.dumps[4+2*k],1,expected)==inverse, (expected,'warning contrast')
        assert r.dumps[5+2*k]==b'\0','displayed transition must be consumed once'
    assert panels(r.dumps[-4])[1]=='SWEATING' and panels(r.dumps[-3])[1]=='SHIVERING'
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


def transient_alerts():
    # Several simulation intervals can run before the HUD consumes an event.
    # A recovery in the same class must replace its obsolete warning.
    from common import fp
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        maximum=fp(s.step(L.peek('s_health',5)).data)
    cases=[('s_eat',13,0,9,'HUNGER BETTER'),
           ('s_drink',13,0,10,'THIRST BETTER'),
           ('s_health',maximum/2,maximum,11,'HEALTH BETTER'),
           ('s_therm_factor',.5,1,12,'BODY BETTER'),
           ('wet_mode',2,0,13,'OUT OF WATER')]
    size=L['s_therm_factor']+5-L['s_hour']
    for name,worse,better,event,label in cases:
        steps=[IDLE]+call(['thermal'])+poke('s_step',0)+[DONE,IDLE]
        steps+=poke('s_eat',0)+poke('s_drink',0)+poke('s_therm_factor',1)
        steps+=call(['ui_monitor'])+[DONE,IDLE,L.poke('ui_pending',0)]
        for value in (worse,better):
            steps+=([L.poke(name,value)] if name=='wet_mode' else poke(name,value))
            steps += [L.peek('s_hour',size),DONE,L.peek('s_hour',size),L.peek('ui_pending'),IDLE]
        steps+=call(['summary_prepare'])+[DONE,'peek:2000:8192',L.peek('ui_pending')]
        r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
        assert r.dumps[0]==r.dumps[1] and r.dumps[3]==r.dumps[4]
        assert r.dumps[2]==bytes((event-8,)) and r.dumps[5]==bytes((event,)),(name,r.dumps[2],r.dumps[5])
        assert panels(r.dumps[6])[1]==label,(name,panels(r.dumps[6]))
        assert r.dumps[7]==b'\0'
    for name,value,event in (('s_deff',120,6),('s_drink',13,2)):
        steps=[IDLE]+call(['thermal'])+poke('s_step',0)+[DONE,IDLE]
        steps+=poke('s_eat',0)+poke('s_drink',0)+call(['ui_monitor'])+[DONE,IDLE,L.poke('ui_pending',0)]
        steps+=poke('s_eat',13)+poke(name,value)+[DONE,L.peek('ui_pending'),IDLE]
        steps+=poke('s_eat',0)+[DONE,L.peek('ui_pending')]
        r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
        assert r.dumps==[bytes((event,)),bytes((event,))], 'a recovery must preserve another active warning'
    print('  five matching recoveries replace pending warnings; other active warnings preserved, simulation unchanged: OK')


def transient_condition():
    # Keep the warning pending across two real monitor calls, as happens
    # during simulation between scene refreshes.
    cases=[((60,0,0),(0,0,0),'ILL IMPROVED'),
           ((0,120,0),(0,0,0),'ILL IMPROVED'),
           ((0,0,40),(0,0,0),'ILL IMPROVED'),
           ((60,0,0),(60,0,0),'DEHYDRATION'),
           ((60,0,0),(0,120,0),'STARVATION'),
           ((0,120,0),(0,0,40),'EXHAUSTION')]
    size=L['s_therm_factor']+5-L['s_hour']
    for before,after,expected in cases:
        steps=[IDLE]+call(['thermal'])+poke('s_step',0)+[DONE,IDLE]+call(['ui_monitor'])
        steps += [L.poke('ui_pending',0)]
        for values in (before,after):
            for name,value in zip(('s_defw','s_deff','s_defr'),values):
                steps += poke(name,value)
            steps += [L.peek('s_hour',size),DONE,L.peek('s_hour',size),L.peek('ui_pending'),IDLE]
        steps += call(['summary_prepare'])+[DONE,'peek:2000:8192',L.peek('ui_pending')]
        r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
        assert r.dumps[0]==r.dumps[1] and r.dumps[3]==r.dumps[4], 'monitor must preserve simulation'
        assert r.dumps[2]==b'\x06'
        assert r.dumps[5]==bytes((14 if expected=='ILL IMPROVED' else 6,)), 'retain current warning or its matching recovery'
        assert panels(r.dumps[6])[1]==expected,(before,after,panels(r.dumps[6]))
        assert r.dumps[7]==b'\0', 'displayed transition must be consumed once'
    print('  pending illness: three recoveries, persistent and replaced conditions display current state: OK')


def drinking_recovery():
    from test_input import command
    for deficit,thirst,expected,condition in ((50,13,'THIRST BETTER',0),
                                             (50,0,'ILL IMPROVED',0),
                                             (70,13,'THIRST BETTER',1)):
        with a2test.Session(DISK) as s:
            s.step(IDLE)
            for step in poke('s_defw',deficit)+poke('s_drink',thirst):
                s.step(step)
            command(s,'REST 1 MIN')
            assert s.step(L.peek('ui_previous',1,5)).data==b'\1'
            before=[s.step(L.peek(name,5)).data for name in ('s_hour','s_elap','s_health')]
            water=s.step(L.peek('it_pack_lo',1,22)).data[0]
            # At most .2 x 165 lb = 33 oz per drink (T0F/S00 $5C26, lot 2).
            command(s,'DRINK WATER 33 OZ')
            assert panels(s.step('peek:2000:8192').data)[1]==expected
            assert s.step(L.peek('ui_previous',1,1)).data==b'\0'
            assert s.step(L.peek('ui_previous',1,5)).data==bytes((condition,))
            assert s.step(L.peek('ui_pending')).data==b'\0'
            assert s.step(L.peek('it_pack_lo',1,22)).data[0]==water-33
            assert before==[s.step(L.peek(name,5)).data for name in ('s_hour','s_elap','s_health')]
            s.step(L.poke('ui_dirty',1))
            command(s,'VIEW')
            assert panels(s.step('peek:2000:8192').data)[1]==('DEHYDRATION' if condition else 'SHIVERING')
    print('  DRINK updates thirst/illness immediately, preserves clock/health and consumes recovery once: OK')


def ground_hint():
    from test_input import command
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        # Isolate ground hints from higher-priority survival messages and
        # from the crash's other objects. Use real transfers/consumption.
        command(s,'DRINK WATER 32 OZ');command(s,'DRINK WATER 32 OZ')
        command(s,'GET WATER')   # collect the crash's water pile before moving
        s.step(L.poke('px',30,1))
        s.step(L.poke('py',30,1))
        for text,expected in (('DROP ROPE','ITEMS: INV'),('GET ROPE','TOPO / HELP'),
                              ('DROP ROPE','ITEMS: INV'),('CARRY ROPE','TOPO / HELP'),
                              ('DROP AXE','ITEMS: INV'),('GET AXE','TOPO / HELP'),
                              ('DROP EGGS','ITEMS: INV'),('EAT EGGS 255 OZ','TOPO / HELP'),
                              ('DROP WATER','WATER LOW:INV'),('DRINK WATER 32 OZ','WATER LOW:INV'),
                              ('DRINK WATER 32 OZ','WATER LOW:INV')):  # 33 oz at most (lot 2)
            command(s,text)
            s.step(L.poke('thermal_mode',0))
            s.step(L.poke('ui_pending',0))
            s.step(L.poke('ui_dirty',1))
            for field in (3,5):
                s.step(L.poke('ui_previous',0,field))
            command(s,'VIEW')
            actual=panels(s.step('peek:2000:8192').data)[1]
            assert actual==expected,(text,actual)
        for item in (22,24):
            assert s.step(L.peek('it_gnd_lo',1,item)).data==b'\0'
            assert s.step(L.peek('it_pack_lo',1,item)).data==b'\0'
        s.step('key:INVENTORY\\r')
        s.step(L.until('inventory_key',20000))
        s.step('key:4')
        s.step('wait:1')
        s.step(L.until('inventory_key',6000))
        screen=text_screen(s.step('peek:0400:1024').data)
        assert screen[1].startswith('GROUND HERE') and screen[7].startswith('NONE')
    print('  Ground hints agree with inventory after retrieving gear and exhausting food/water: OK')


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
        assert screen[19].startswith('1 WORN') and screen[20].startswith('N/SPACE/RETURN NEXT')
        assert screen[21].startswith('ESC VIEW')
        assert '16 ITEMS' in screen[1]
        assert all(screen[row].startswith('FREE ') for row in range(2,6))
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


def help_pages():
    # Actual keyboard consultation must leave both the journey and the view
    # intact: peek:2000:8192 reads both DHGR banks (16 KB, tests/common.py).
    size=L['s_t0']+5-L['s_hour']
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        before=s.step(L.peek('s_hour',size)).data
        items=tuple(s.step(L.peek(name,76)).data for name in ('it_place','it_pack_lo','it_gnd_lo'))
        view=s.step('peek:2000:8192').data
        assert len(view)==16384,'main and auxiliary banks'
        def page(key=None):
            if key is not None:
                s.step(f'key:{key}')
            if key=='X':
                s.step('wait:1')  # ignored key returns straight into wait_key
            else:
                s.step(L.until('help_key',20000))
            raw=s.step('peek:0400:1024').data
            rows=text_screen(raw)
            assert rows[0].startswith(' NEOWILDERNESS - HELP ')
            assert rows[20].startswith('1 TRAVEL  2 GEAR  3 SURVIVAL')
            assert rows[22].startswith('ESC/RETURN: VIEW')
            assert all(c<128 for c in raw[:18]), 'title must be inverse'
            assert s.step('peek:0032:1').data==b'\xff', 'normal text mode must be restored'
            return rows
        welcome=result_text(text_screen(s.step('peek:0400:1024').data))
        for word in ('CRASH IN', 'RANGERS', 'WILDLIFE'):
            assert word in welcome,(word,welcome)
        s.step('key:HELP\\r')
        travel=page()
        assert travel[2].startswith('1/3  TRAVEL')
        for example in ('RANGER OUTPOST','INVENTORY, STATUS, TOPO','WALK 10 MIN / WALK 1 H'):
            assert example in '\n'.join(travel)
        gear=page('2')
        assert gear[2].startswith('2/3  EQUIPMENT')
        for example in ('GET AXE: PACK','TAKE AXE: HAND','WEAR PARKA: WORN',
                        'DROP AXE: GROUND HERE','DROP CHEESE: DROPS ALL ITS STOCK'):
            assert example in '\n'.join(gear)
        survival=page('3')
        assert survival[2].startswith('3/3  SURVIVAL')
        for example in ('DRINK WATER 4 OZ','REST 1 H','ENTER SHELTER','USE FIRSTAID KIT','OZ = OUNCES'):
            assert example in '\n'.join(survival)
        assert page('B')==gear and page('B')==travel
        assert page('B')==survival, 'back from first page must wrap to last'
        assert page('N')==travel, 'next from last page must wrap to first'
        assert page(' ')==gear and page('N')==survival
        assert page('1')==travel and page('2')==gear and page('3')==survival
        assert page('X')==survival, 'unsupported keys must leave the current page'
        s.step('key:\\e');s.step(IDLE)
        assert s.step('peek:2000:8192').data==view
        s.step('key:HELP\\r')
        assert page()==travel, 'HELP must reopen at its first page'
        s.step('press:\\r');s.step(IDLE)
        assert s.step(L.peek('s_hour',size)).data==before
        assert tuple(s.step(L.peek(name,76)).data for name in ('it_place','it_pack_lo','it_gnd_lo'))==items
        assert s.step('peek:2000:8192').data==view
    print('  welcome, three HELP pages, examples, selection/wrapping, ESC/RETURN; journey, supplies and both DHGR banks preserved: OK')


def screen_links():
    from common import hgr_rows
    size=L['s_t0']+5-L['s_hour']
    keys={'HELP':'help_key','STATUS':'status_key','INVENTORY':'inventory_key','TOPO':'graphical_topo_key'}
    links=(('HELP','I','INVENTORY'),('HELP','S','STATUS'),('HELP','T','TOPO'),
           ('INVENTORY','S','STATUS'),('INVENTORY','T','TOPO'),('INVENTORY','H','HELP'),
           ('STATUS','I','INVENTORY'),('STATUS','T','TOPO'),('STATUS','H','HELP'))
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        before=s.step(L.peek('s_hour',size)).data
        items=tuple(s.step(L.peek(name,76)).data for name in ('it_place','it_pack_lo','it_gnd_lo'))
        view=s.step('peek:2000:8192').data
        assert len(view)==16384,'main and auxiliary banks'
        for source,key,target in links:
            s.step(f'key:{source}\\r')
            s.step(L.until(keys[source],20000))
            s.step(f'key:{key}')
            s.step(L.until(keys[target],20000))
            screen='\n'.join(text_screen(s.step('peek:0400:1024').data))
            assert target in screen,(source,key,target,screen)
            s.step('key:\\e');s.step(IDLE)
            assert s.step(L.peek('s_hour',size)).data==before
            assert tuple(s.step(L.peek(name,76)).data for name in ('it_place','it_pack_lo','it_gnd_lo'))==items
            # Screen holes also hold simulation scratch; compare the displayed
            # rows 0-175 of both DHGR banks (HUD, view and its cache) instead.
            assert hgr_rows(s.step('peek:2000:8192').data)==hgr_rows(view)
    print('  nine direct HELP/INVENTORY/STATUS links, including TOPO; return preserves journey, stock and both DHGR banks: OK')


def main_view_hints():
    from test_input import command
    from test_forest import map_fixture
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,map_fixture())) as s:
        s.step(IDLE)
        for item in range(1,76):
            s.step(L.poke('it_place',255,item))
        s.step(L.poke('it_place',3,21))
        def view(expected):
            for name in ('thermal_mode','ui_pending'):
                s.step(L.poke(name,0))
            for offset in (3,5):
                s.step(L.poke('ui_previous',0,offset))
            s.step(L.poke('ui_dirty',1))
            command(s,'VIEW')
            page=s.step('peek:2000:8192').data
            assert panels(page)[1]==expected,(expected,panels(page))
            return page
        view('TOPO / HELP')
        command(s,'HANG FOOD')
        view('LOWER FOOD')
        s.step(L.poke('px',21,1))
        view('TOPO / HELP')
        s.step(L.poke('night',1))
        view('REST / HELP')
        s.step(L.poke('night',0))
        for step in poke('s_eat',13)+poke('s_drink',13):
            s.step(step)
        page=view('TOPO / HELP')
        # The lower right field shows the worse need, hunger when equal.
        assert panels(page)[3]=='HUNGER VERY',panels(page)
        assert warned(page,3,'VERY'),'critical gauges must stand out (white on red)'
        assert not warned(page,3,'HUNGER')
        for step in poke('s_eat',7):
            s.step(step)
        page=view('TOPO / HELP')
        assert panels(page)[3]=='THIRST VERY',panels(page)
        for step in poke('s_drink',0):
            s.step(step)
        page=view('TOPO / HELP')
        assert panels(page)[3]=='HUNGER SO-SO',panels(page)
        assert not warned(page,3,'SO-SO')
        for step in poke('s_eat',13)+poke('s_drink',13):
            s.step(step)
        s.step(L.poke('wet_mode',2))
        view('IMMERSED')
        from common import fp
        health=fp(s.step(L.peek('s_health',5)).data)
        for step in poke('s_health',health/4):
            s.step(step)
        page=view('IMMERSED')
        label=panels(page)[0]
        assert label.startswith('HEALTH '),label
        percent=label.index(' ')+1
        assert warned(page,0,label[percent:]),'poor health must stay a warning'
        assert not warned(page,0,label[:percent])
    print('  daylight/night/hung-pack hints, remote pack excluded; severe gauges and immersion visible: OK')


def inventory_backward():
    steps=[IDLE,L.poke('px',0,1),L.poke('py',0,1)]
    for item in range(1,76):
        steps += [L.poke('it_place',255,item)]
    for item in range(23,38):
        steps += [L.poke('it_place',2,item),L.poke('it_pack_lo',1,item),L.poke('it_pack_hi',0,item),
                  L.poke('it_gnd_lo',2,item),L.poke('it_gnd_hi',0,item),
                  L.poke('it_x',0,item),L.poke('it_y',0,item)]
    steps += [L.peek('s_hour',5),L.peek('it_pack_lo',76),
              'key:INVENTORY\\r','wait:1',L.until('inventory_key',20000)]
    for key in ('3','N','N','B','B','B'):
        steps += [f'key:{key}','wait:1',L.until('inventory_key',6000),'peek:0400:1024']
    steps += ['key:\\e','wait:1',IDLE,L.peek('s_hour',5),L.peek('it_pack_lo',76)]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    screens=[text_screen(d) for d in r.dumps[2:8]]
    assert screens[2][1].startswith('GROUND HERE')
    assert screens[3]==screens[1], 'B from ground page 1 must return to pack page 2'
    assert screens[4]==screens[0], 'B within the pack must return to page 1'
    assert screens[5][1].startswith('IN HAND')
    assert r.dumps[0]==r.dumps[-2] and r.dumps[1]==r.dumps[-1]
    print('  B across inventory groups returns to the previous last page; time and stocks preserved: OK')


def timberline_display():
    from test_forest import map_fixture
    from test_input import command
    for timberline,height,wooded in ((0,85,True),(0,86,False),
                                     (34,9,True),(34,10,False),
                                     (140,115,True),(140,116,False)):
        m=map_fixture(height=height)
        m[27]=timberline
        with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,m)) as s:
            s.step(IDLE)
            before=[s.step(L.peek(name,5)).data for name in ('s_hour','s_health')]
            s.step('key:STATUS\\r')
            s.step(L.until('status_key',20000))
            screen='\n'.join(text_screen(s.step('peek:0400:1024').data))
            assert 'GRND '+('WOODS' if wooded else 'SCRUB') in screen,(timberline,height,screen)
            s.step('key:\\e')
            s.step(IDLE)
            s.step('key:MAP\\r')
            s.step(L.until('topo_key',20000))
            row=text_screen(s.step('peek:0400:1024').data)[10][:32]
            mark='T' if wooded else 't'
            assert mark in row and set(row)<={mark,'P'},(timberline,height,row)
            s.step('key:\\e')
            s.step(IDLE)
            command(s,'CLIMB TREE')
            assert s.step(L.peek('tree_in')).data==bytes((int(wooded),))
            assert before==[s.step(L.peek(name,5)).data for name in ('s_hour','s_health')]
    print('  TOPO/STATUS/climbing agree below and at low, high and legacy timberlines; clock/health preserved: OK')


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
                          'key:MAP\\r','wait:1',L.until('topo_key',20000),'peek:0400:1024',
                          'key:D','wait:1',L.until('topo_key',6000),'key:W','wait:1',L.until('topo_key',6000),
                          'key:C','wait:1',L.until('topo_key',6000),L.peek('topo_x',2),
                          'key:\\e','wait:1',IDLE]
            steps += [L.peek('s_hour',5),'peek:2000:8192']
            r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        offset=int.from_bytes(r.dumps[0],'little')
        for i in range(8):
            screen=text_screen(r.dumps[3+2*i]); head=(i*70-offset)%560
            label=('N','NE','E','SE','S','SW','W','NW')[((head+35)%560)//70]
            cue=map_cue(screen)
            assert f'HEAD {head} {label}' in ' '.join(cue.split()), screen[0]
            assert cue.rstrip().endswith(('P+C','P+H','P+R')[i%3]),cue
            assert r.dumps[4+2*i]==bytes((20,28)), 'C must restore player-centred map (40-20, 40-12)'
        assert len(r.dumps[2])==16384,'main and auxiliary banks'
        assert r.dumps[1]==r.dumps[-2] and r.dumps[2]==r.dumps[-1], 'MAP must preserve time and both DHGR banks'
    print('  eight bearings with both magnetic declinations, C recenter, player/site overlaps, clock and both DHGR banks preserved: OK')

if __name__=='__main__':
    summary_display();monitor();transient_alerts();transient_condition();drinking_recovery();ground_hint();inventory_status();help_pages();screen_links();main_view_hints();inventory_backward();timberline_display();map_controls()
