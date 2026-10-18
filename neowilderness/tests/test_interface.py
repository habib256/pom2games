#!/usr/bin/env python3
"""Survival panels, transition events, grouped inventory and magnetic TOPO."""
import tempfile
from common import HERE, L, DISK, a2test, disk_with, text_screen, dhgr_page, result_text, map_cue, page_frame, is_status
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
    alerts={1:'EAT SOON',2:'DRINK SOON',3:'HEALTH WORSE',4:'BODY WORSE',
            5:'NOW IMMERSED',6:'DRINK NOW',9:'HUNGER BETTER',10:'THIRST BETTER',
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
    assert initial==('HEALTH 100%','USE WARM GEAR','7:00 - DAY 1','HUNGER OKAY'),initial
    assert panels(r.dumps[3])==initial,'arrows must preserve side panels'
    for k,expected in enumerate(alerts.values()):
        assert panels(r.dumps[4+2*k])[1]==expected,(expected,panels(r.dumps[4+2*k]))
        inverse=list(alerts)[k]<9
        assert warned(r.dumps[4+2*k],1,expected)==inverse, (expected,'warning contrast')
        assert r.dumps[5+2*k]==b'\0','displayed transition must be consumed once'
    assert panels(r.dumps[-4])[1]=='SHED A LAYER' and panels(r.dumps[-3])[1]=='USE WARM GEAR'
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
           ((60,0,0),(60,0,0),'DRINK NOW'),
           ((60,0,0),(0,120,0),'EAT NOW'),
           ((0,120,0),(0,0,40),'REST NOW')]
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
            assert panels(s.step('peek:2000:8192').data)[1]==('DRINK NOW' if condition else 'USE WARM GEAR')
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
        for text,expected in (('DROP ROPE','ITEMS: INV'),('GET ROPE','TOPO'),
                              ('DROP ROPE','ITEMS: INV'),('CARRY ROPE','TOPO'),
                              ('DROP AXE','ITEMS: INV'),('GET AXE','TOPO'),
                              ('DROP EGGS','ITEMS: INV'),('EAT EGGS 255 OZ','TOPO'),
                              ('DROP WATER','CHECK WATER'),('DRINK WATER 32 OZ','CHECK WATER'),
                              ('DRINK WATER 32 OZ','CHECK WATER')):  # 33 oz at most (lot 2)
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
        screen=text_screen(s.step('peek:0400:1024').data)
        # The ROCK lies on every land cell (lot 3, docs/CRAFT.md 3.3): the
        # ground hint names the first set only. OBJECTS (16 October 2026):
        # LOCAL holds it alone.
        assert (screen[2].startswith(' LOCAL ') and screen[3].startswith('\u258f  ROCK           100 OZ')
                and not screen[4][1:39].strip()), screen[:6]   # XL: docs/MENUS.md 9
    print('  Ground hints agree with inventory after retrieving gear and exhausting food/water (the ROCK aside): OK')


def inventory_status():
    """OBJECTS, 80 columns (16 October 2026, docs/MENUS.md 5): LOCAL on the
    left, CARRIED on the right (HANDS, PACK, WORN, always headed), each item
    with its weight, eleven entries a side ("MORE" below a longer list),
    CARRYING and LOAD under them, the keys on row 23."""
    steps=[IDLE]
    # Empty groups, then 16 provisions split between the pack and the ground.
    for i in range(1,76): steps += [L.poke('it_place',255,i),L.poke('it_pack_lo',0,i),L.poke('it_pack_hi',0,i)]
    # No ROCK (lot 3): absent, and the cell of the lot 4 piles is this one
    # (forage_here leaves cr_still alone, inventory_settle brings none).
    start = (HERE / 'build/map.bin').read_bytes()
    steps += [L.poke('cr_b1',255,3),L.poke('cr_still',1),L.poke('fg_x',start[3]),L.poke('fg_y',start[5])]
    steps += ['key:INVENTORY\\r','wait:1',L.until('inventory_key',20000),'peek:0400:1024']
    steps += ['key:\\e','wait:1',IDLE]
    for i in range(22,38):
        steps += [L.poke('it_place',2,i),L.poke('it_pack_lo',10,i),L.poke('it_gnd_lo',20,i),L.poke('it_gnd_hi',0,i),
                  L.poke('it_x',0,i),L.poke('it_y',0,i)]
    steps += [L.poke('px',0,1),L.poke('py',0,1),L.poke('fg_x',0),L.poke('fg_y',0),L.peek('s_hour',5),L.peek('s_health',5),
              'key:INVENTORY\\r','wait:1',L.until('inventory_key',6000),'peek:0400:1024',
              'key:\\e','wait:1',IDLE]
    # Worst simultaneous STATUS: all illnesses, cold, shelter, immersion.
    steps+=poke('s_defw',60)+poke('s_deff',120)+poke('s_defr',40)+poke('s_therm_factor',.5)+poke('s_body',90)
    steps += [L.poke('thermal_mode',2),L.poke('shelter_inside',1),L.poke('wet_mode',2),
              'key:STATUS\\r','wait:1',L.until('wait_key',20000),'peek:0400:1024',
              'key:\\e','wait:1',IDLE,L.peek('s_hour',5),L.peek('s_health',5)]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    keys='\u21b5 LIST/ACT \u2190\u2192\u2191\u2193 MOVE  H HANDS'
    screen=text_screen(r.dumps[0])
    assert page_frame(screen, 'OBJECTS', keys, 'ESC VIEW'), screen
    assert screen[2].startswith(' LOCAL ') and screen[2][41:].startswith(' HANDS '), screen[2]
    assert not any(row[1:39].strip() for row in screen[3:14]), screen[3:14]        # nothing here
    assert ' PACK ' in screen[4][41:] and ' WORN ' in screen[5][41:] and \
        not any(row[42:78].strip() for row in screen[6:15]), screen[3:15]
    assert 'MORE' not in screen[15], screen[14]
    screen=text_screen(r.dumps[3])
    assert page_frame(screen, 'OBJECTS', keys, 'ESC VIEW'), screen
    left=[row[1:39].split() for row in screen[3:15]]
    assert all(cells[-2:] == ['20', 'OZ'] for cells in left), left                  # 11 of the 16 ground piles
    assert ' PACK ' in screen[4][41:], screen[3:5]
    assert all(row[42:78].split()[-2:] == ['10', 'OZ'] for row in screen[5:15]), screen[5:15]
    assert screen[15].count(' MORE ') == 2, screen[14]                              # both lists go on
    # CARRYING (from STATUS, 15 October 2026): food and water in their own columns.
    for row in (r'CARRIED +150 OZ +10 OZ',r'LOCAL +300 OZ +20 OZ'):
        assert __import__('re').search(row,'\n'.join(screen)), (row,screen[15:20])
    assert screen[16][41:].startswith(' LOAD ') and 'WALK TIME +' in screen[18], screen[15:20]
    screen=text_screen(r.dumps[4]); joined='\n'.join(screen)
    assert is_status(screen), 'worst STATUS must not scroll away its heading'
    assert page_frame(screen, 'STATUS', '\u2191 TOPO', 'ESC/\u2193 VIEW'), screen
    # LOCAL (15 October 2026): the date, the time, the air and the felt temperature.
    assert 'DATE    MAY 6' in screen[3] and ' FEELS ' in screen[4], screen[3:5]
    for word in ('DEHYDRATION','STARVATION','EXHAUSTION','HYPOTHERMIA','SHIVERING','INSIDE SHELTER','IMMERSED'):
        assert word in joined, (word,joined)
    assert r.dumps[1]==r.dumps[5] and r.dumps[2]==r.dumps[6], 'consultation must not spend time or health'
    print('  OBJECTS 80 columns: LOCAL and CARRIED, empty groups, split ounces on both sides, MORE, CARRYING, LOAD; worst STATUS: OK')


def help_pages():
    """HELP, a page of the STATUS cycle: four blocks (TRAVEL, EQUIPMENT,
    SURVIVAL, HEALTH) on one 80-column page under the tab row; other keys
    leave it as it is; ESC and RETURN return to the view, the journey and
    both DHGR banks (peek:2000:8192, tests/common.py) intact."""
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
                s.step('wait:1')
            s.step(L.until('help_key',20000))
            rows=text_screen(s.step('peek:0400:1024').data)
            assert page_frame(rows, 'HELP', '\u2191 TOPO', 'ESC/\u2193 VIEW'), rows
            assert s.step('peek:0032:1').data==b'\xff', 'normal text mode must be restored'
            return rows
        welcome=result_text(text_screen(s.step('peek:0400:1024').data))
        for word in ('CRASH IN', 'RANGERS', 'WILDLIFE'):
            assert word in welcome,(word,welcome)
        s.step('key:HELP\\r')
        rows=page()
        # XL (docs/MENUS.md 9.3): a post-it a block, its heading the title
        assert rows[2].startswith(' TRAVEL ') and rows[2][41:].startswith(' EQUIPMENT '), rows[2]
        assert rows[11].startswith(' SURVIVAL ') and rows[11][41:].startswith(' HEALTH '), rows[11]
        text='\n'.join(rows)
        for example in ('WALK 10 MIN / WALK 1 H','GET AXE: PACK','TAKE AXE: HAND','WEAR PARKA: WORN',
                        'DROP AXE: GROUND','DRINK WATER 4 OZ','REST 1 H','ENTER SHELTER','USE FIRSTAID KIT',
                        'LEFT/RIGHT: TURN  RETURN: COMMANDS','UP: PAGES  DOWN: COMMANDS, THEN TOPO','MAP: IJKL SCROLL, C CENTER',
                        'USE BAIT, USE TRAP, CATCH GAME 2 H','COOK GAME / TASTE / SKIN / PACK'):   # lot 4
            assert example in text, (example, text)
        assert page('X')==rows, 'unsupported keys must leave the page'
        s.step('key:\\e');s.step(IDLE)
        assert s.step('peek:2000:8192').data==view
        s.step('key:HELP\\r')
        assert page()==rows
        s.step('press:\\r');s.step(IDLE)
        assert s.step(L.peek('s_hour',size)).data==before
        assert tuple(s.step(L.peek(name,76)).data for name in ('it_place','it_pack_lo','it_gnd_lo'))==items
        assert s.step('peek:2000:8192').data==view
    print('  welcome, HELP in four blocks, examples, other keys ignored, ESC/RETURN; journey, supplies and both DHGR banks preserved: OK')


def option_pages():
    """OPTIONS and MENU (src/pages.s, 14 October 2026): MENU's Q (S, R alike) and
    OPTIONS' C type SAVE, RESTORE, QUIT and NATURE for the player (inbuf at
    do_command), OPTIONS' A and P flip bits 7 and 6 of game_options; MAP off
    answers on the view and points to OPTIONS."""
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        def page(*keys):
            s.step('key:STATUS\\r'); s.step(L.until('status_key',20000))
            for key in keys:
                s.step(f'key:{key}'); s.step('wait:1'); s.step(L.until('wait_key',20000))
            return text_screen(s.step('peek:0400:1024').data)
        rows=page('\\<')
        # XL (docs/MENUS.md 9.3): RANGERS first, then SAVE / RESTORE, then QUIT (15 October 2026)
        assert rows[2].startswith(' RANGERS ') and ' CELLS AWAY' in rows[3] and rows[4].startswith('\u258fJOURNEY DONE: 0%'), rows[2:5]
        assert rows[6].startswith(' SAVE / RESTORE ') and rows[7].startswith('\u258f  S  SAVE') and \
            rows[8].startswith('\u258f  R  RESTORE') and rows[11].startswith('\u258f  Q  QUIT'), rows[6:12]
        assert not any(r.strip() for r in rows[13:22]) and page_frame(rows, 'MENU', '\u2191\u2193 CHOOSE  \u21b5 SELECT', 'ESC VIEW'), rows
        s.step('press:Q'); s.step(L.until('do_command',20000))
        assert s.step(L.peek('inbuf',5)).data==b'QUIT\0'
        s.step(L.until('wait_key',20000))
        assert 'UNSAVED PROGRESS WILL BE LOST' in '\n'.join(text_screen(s.step('peek:0400:1024').data))
        s.step('key:N'); s.step(IDLE)
        rows=page('\\<','\\<')
        assert rows[2].startswith(' OPTIONS ') and rows[5].startswith('\u258f  P  MAP PAGE') and rows[5][31:34] == '[\u2713]', rows[:10]
        s.step('key:P'); s.step('wait:1'); s.step(L.until('wait_key',20000))
        rows=text_screen(s.step('peek:0400:1024').data)
        assert rows[5][31:34] == '[ ]' and s.step(L.peek('game_options')).data==b'\x40', rows[5]
        s.step('key:\\e'); s.step(IDLE)
        s.step('key:MAP\\r'); s.step('wait:1'); s.step(IDLE)
        assert 'MAP IS OFF (OPTIONS PAGE).' in result_text(text_screen(s.step('peek:0400:1024').data))
        page('\\<','\\<','P','A')
        assert s.step(L.peek('game_options')).data==b'\x80'
        s.step('press:C'); s.step(L.until('do_command',20000))
        assert s.step(L.peek('inbuf',7)).data==b'NATURE\0'
        s.step(L.until('input_number_idle',20000))
        s.step('key:\\e'); s.step(IDLE)
        s.step(L.poke('game_options',0))
    print('  MENU page: Q types QUIT; OPTIONS: C types NATURE, A and P flip, MAP off points to OPTIONS: OK')


def screen_links():
    from common import hgr_rows
    size=L['s_t0']+5-L['s_hour']
    keys={'HELP':'help_key','STATUS':'status_key','INVENTORY':'inventory_key','TOPO':'graphical_topo_key'}
    links=(('HELP','I','INVENTORY'),('HELP','O','INVENTORY'),('HELP','S','STATUS'),('HELP','T','TOPO'),
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
            assert {'INVENTORY': ' OBJECTS '}.get(target,target) in screen,(source,key,target,screen)
            s.step('key:\\e');s.step(IDLE)
            assert s.step(L.peek('s_hour',size)).data==before
            assert tuple(s.step(L.peek(name,76)).data for name in ('it_place','it_pack_lo','it_gnd_lo'))==items
            # Screen holes also hold simulation scratch; compare the displayed
            # rows 0-175 of both DHGR banks (HUD, view and its cache) instead.
            assert hgr_rows(s.step('peek:2000:8192').data)==hgr_rows(view)
    print('  ten direct HELP/OBJECTS/STATUS links, including TOPO; return preserves journey, stock and both DHGR banks: OK')


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
        view('TOPO')
        command(s,'HANG FOOD')
        view('LOWER FOOD')
        s.step(L.poke('px',21,1))
        view('TOPO')
        s.step(L.poke('night',1))
        view('REST')
        s.step(L.poke('night',0))
        before=[s.step(L.peek(name,5)).data for name in ('s_hour','s_health')]
        for step in poke('s_rest',13):
            s.step(step)
        view('REST')
        assert before==[s.step(L.peek(name,5)).data for name in ('s_hour','s_health')]
        for step in poke('s_rest',0):
            s.step(step)
        for step in poke('s_eat',13)+poke('s_drink',13):
            s.step(step)
        page=view('TOPO')
        # The lower right field shows the worse need, hunger when equal.
        assert panels(page)[3]=='HUNGER VERY',panels(page)
        assert warned(page,3,'VERY'),'critical gauges must stand out (white on red)'
        assert not warned(page,3,'HUNGER')
        for step in poke('s_eat',7):
            s.step(step)
        page=view('TOPO')
        assert panels(page)[3]=='THIRST VERY',panels(page)
        for step in poke('s_drink',0):
            s.step(step)
        page=view('TOPO')
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
    """OBJECTS (16 October 2026): every item in the pack, a list of 78
    entries on the right; DOWN moves the cursor and the window follows it
    (the cursor on its last row), UP back above the window's top shows the
    list from its first entry again; past the last item, the view. Time and
    stocks untouched."""
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        s.step(L.poke('px',0,1)); s.step(L.poke('py',0,1))
        for item in range(1,76):
            for name,v in (('it_place',2),('it_pack_lo',1),('it_pack_hi',0)):
                s.step(L.poke(name,v,item))
        for item in range(23,38):
            for name,v in (('it_gnd_lo',2),('it_gnd_hi',0),('it_x',0),('it_y',0)):
                s.step(L.poke(name,v,item))
        before=(s.step(L.peek('s_hour',5)).data,s.step(L.peek('it_pack_lo',76)).data)
        s.step('key:INVENTORY\\r'); s.step(L.until('inventory_key',20000))

        def key(k, times=1):
            for _ in range(times):
                s.step(f'press:{k}'); s.step('wait:1'); s.step(L.until('inventory_key',6000))
            return text_screen(s.step('peek:0400:1024').data)
        screen=key('\\r')                                   # the lists
        screen=key('\\>')                                   # CARRIED
        assert screen[5][42] == '>' and screen[2][41:].startswith(' HANDS ') and ' PACK ' in screen[4][41:], screen[3:6]
        screen=key('\\v',15)                                # 15 items down: the window follows
        assert screen[14][42] == '>' and not any(row[42] == '>' for row in screen[3:14]), screen[3:14]
        assert s.step(L.peek('obj_cur',1,1)).data[0] == 17 and screen[15].count(' MORE ') == 2, screen[14]
        screen=key('\\^',11)                                # above the window: from the first entry
        assert screen[9][42] == '>' and screen[2][41:].startswith(' HANDS '), screen[3:14]
        n=s.step(L.peek('ob_n',1,1)).data[0]                # (..., the last item, WORN)
        key('\\v',n-2-s.step(L.peek('obj_cur',1,1)).data[0])  # the last item of the pack
        s.step('press:\\v'); s.step('wait:2')
        out=s.step(f'until:{L["keyboard_wait"]:04X},{L["idle"]:04X}:20000').out
        assert f'PC={L["idle"]:04X}' in out, 'DOWN past the last item: the view'
        assert (s.step(L.peek('s_hour',5)).data,s.step(L.peek('it_pack_lo',76)).data) == before
    print('  OBJECTS: every item in the pack, the window follows the cursor, the view past the last item; '
          'time and stocks preserved: OK')


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
            assert 'GROUND '+('WOODS' if wooded else 'SCRUB') in screen,(timberline,height,screen)
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
                          'key:L','wait:1',L.until('topo_key',6000),'key:I','wait:1',L.until('topo_key',6000),
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
    summary_display();monitor();transient_alerts();transient_condition();drinking_recovery();ground_hint();inventory_status();help_pages();option_pages();screen_links();main_view_hints();inventory_backward();timberline_display();map_controls()
