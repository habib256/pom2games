#!/usr/bin/env python3
"""Find the cabin through MAP, walk there, rest inside, exit and return."""
import tempfile
import re
from common import HERE, L, DISK, a2test, disk_with, fp, text_screen, view_rows, text_writes, text_changes, map_rows, map_cue
from test_thermal import call, poke, scalar

IDLE = L.until('idle', 20000)


def command(text):
    return [f'key:{text}\r', 'wait:1', IDLE]


def hours(text, value):
    return [f'key:{text}\r', 'wait:1', L.until('wait_key', 6000),
            f'key:{value}\r', 'wait:1', IDLE]


def mapbin():
    m = bytearray((HERE / 'build/map.bin').read_bytes())
    m[2:8] = bytes((0,4,0,4,140,0))
    m[8:12] = bytes((20,4,0,90))
    m[13:16] = bytes((0,0,20))
    m[16:22] = bytes((1,7,4,140,0,11))
    m[23] = 100  # Keep encounters outside this deterministic shelter route.
    m[24] = 0  # Isolate cabin/terrain here; magnetic MAP headings have dedicated UI tests.
    m[64:] = bytes([10])*9408
    m[64+6*112+9] |= 128          # water visible on MAP, outside the route
    return bytes(m)


def playable(disk):
    snap = [L.peek('px',6), L.peek('s_hour',5), L.peek('shelter_inside')]
    steps = [IDLE, 'peek:2000:8192'] + snap
    steps += command('ENTER SHELTER') + snap + ['peek:0400:1024']
    steps += command('ENTER HUT') + snap
    steps += ['key:MAP\r', 'wait:1', L.until('topo_key',20000),
              'peek:0400:1024', 'peek:2000:8192']
    for key, count in [('L',12),('I',20),('J',20),('K',20)]:   # MAP: I/J/K/L scroll
        for _ in range(count):
            steps += [f'key:{key}','wait:1',L.until('topo_key',6000)]
        steps += [L.peek('topo_x'), L.peek('topo_y'), 'peek:0400:1024']
    steps += ['key:\r','wait:1',IDLE,'peek:2000:8192']
    steps += command('WALK 54 MIN') + snap + ['peek:2000:8192']
    steps += command('ENTER SHELTER') + snap + ['peek:2000:8192','peek:0400:1024']
    steps += command('ENTER SHELTER') + snap
    steps += command('WALK') + snap + ['peek:0400:1024']
    steps += command('SWIM') + snap
    steps += command('LOOK R') + [L.peek('shelter_inside'),'peek:2000:8192']
    steps += ['key:STATUS\r','wait:1',L.until('wait_key',6000), 'peek:0400:1024',
              'key: ','wait:1',IDLE]
    steps += hours('REST',2) + [L.peek('s_body',5), L.peek('s_hour',5),
                              L.peek('shelter_inside'),L.peek('animal_kind'),'peek:2000:8192']
    steps += ['key:MAP\r','wait:1',L.until('topo_key',20000),
              'key:\x1b','wait:1',IDLE,L.peek('shelter_inside'),'peek:2000:8192']
    steps += command('EXIT SHELTER') + snap + ['peek:2000:8192']
    # Ordinary commands leave the cabin cell, return to it and enter again.
    # REST changes health and therefore walking pace. Two short admitted
    # half-steps leave the cabin cell; the same two steps return to it.
    steps += command('LOOK L') + command('WALK 9 MIN') * 2 + [L.peek('px',6)]
    steps += command('LOOK B') + command('WALK 9 MIN') * 2
    steps += command('ENTER SHELTER') + snap
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=1800)
    dumps = iter(r.dumps)
    def take(): return next(dumps)
    def state(): return take(),fp(take()),take()[0]
    initial_hgr = take()
    initial = state()
    assert state() == initial
    assert 'NO SHELTER HERE' in '\n'.join(text_screen(take()))
    assert state() == initial, 'ENTER HUT must not create or enter a found cabin'
    screen = text_screen(take())
    assert map_cue(screen).startswith(' 4,4 HEAD ')
    rows = map_rows(screen)
    assert rows[23-4][4] == 'P' and rows[23-4][7] == 'H' and rows[23-4][20] == 'R'
    assert rows[23-6][9] == '='
    assert take() == initial_hgr, 'MAP must preserve the HGR page'
    origins = [(72,0),(72,60),(0,60),(0,0)]    # GW-40, GH-24
    for x,y in origins:
        assert take() == bytes((x,y)), 'MAP scrolling must clamp to the grid'
        rows=map_rows(text_screen(take()))
        assert len(rows) == 24 and all(len(row) == 40 for row in rows)
    assert take() == initial_hgr
    at_cabin = state()
    assert at_cabin[0] == bytes((0,7,0,4,140,0)) and at_cabin[2] == 0
    assert abs(at_cabin[1]-initial[1]-.9) < 1e-6, 'MAP and refused commands consume no time'
    assert any(view_rows(take()))
    inside = state()
    assert inside[:2] == at_cabin[:2] and inside[2] == 1
    assert view_rows(take()) == bytes(6400)
    assert 'INSIDE THE CABIN' in '\n'.join(text_screen(take()))
    assert state() == inside, 'entering twice must preserve clock and position'
    assert state() == inside, 'WALK inside must not ask for hours or move'
    assert 'EXIT SHELTER BEFORE' in '\n'.join(text_screen(take()))
    assert state() == inside, 'SWIM inside must not alter immersion or position'
    assert take()[0] == 1 and view_rows(take()) == bytes(6400)
    assert 'INSIDE SHELTER' in '\n'.join(text_screen(take()))
    temperature, hour = fp(take()), fp(take())
    assert abs(hour-at_cabin[1]-2) < 1e-6
    assert take()[0] == 1 and take()[0] == 0, 'indoor REST cannot spawn fauna'
    assert view_rows(take()) == bytes(6400)
    assert take()[0] == 1 and view_rows(take()) == bytes(6400)
    exited = state()
    assert exited[2] == 0 and exited[1] == hour
    assert any(view_rows(take())), 'exit must restore the outdoor scene'
    assert take()[:4] == bytes((0,8,0,4)), 'outward walk must leave the cabin cell'
    returned = state()
    assert returned[0][:4] == at_cabin[0][:4] and returned[2] == 1
    assert next(dumps,None) is None
    print('  MAP relief, water, markers, scrolling bounds and HGR preservation: OK')
    print('  walk to cabin, enter, refusals, STATUS, REST, exit and return: OK')

    # Same route, equipment and clock, but rest outside instead of entering.
    steps = [IDLE] + command('WALK 54 MIN') + hours('REST',2) + [L.peek('s_body',5)]
    outside = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    assert temperature > fp(outside.dumps[0]) + .1, (temperature,fp(outside.dumps[0]))
    print('  shelter retains more body heat than the same cold outdoor rest: OK')


def topo_refresh(disk):
    """Reopen after browsing/travel: read live position, bearing and map cells."""
    ready = L.until('topo_show', 20000)
    snap = [L.peek('topo_x'), L.peek('topo_y'), 'peek:0400:1024']
    steps = [IDLE, 'peek:2000:8192', 'key:MAP', 'press:\\r', ready] + snap
    steps += [L.until('topo_key', 20000)]
    for key in ('L', 'L', 'I', 'I'):
        steps += [f'key:{key}', 'wait:1', L.until('topo_key', 20000)]
    steps += ['key:\\r', 'wait:1', IDLE] + command('WALK 54 MIN')
    steps += [L.peek('px', 6), 'peek:2000:8192']
    # Change a visible terrain cell and markers while the map is closed.
    # MAP must read the live map, even when its overlay was previously used.
    steps += [f'poke:{0x7040+6*112+9:04X}:40', 'poke:7008:0A', 'poke:7011:0B',
              'key:MAP', 'press:\\r', ready] + snap
    steps += [L.until('topo_key', 20000), 'key:\\r', 'wait:1', IDLE]
    steps += command('LOOK B') + ['peek:2000:8192', 'key:MAP', 'press:\\r', ready] + snap
    steps += [L.until('topo_key', 20000), 'key:\\r', 'wait:1', IDLE, 'peek:2000:8192']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    initial, origin, screen = r.dumps[0], r.dumps[1], text_screen(r.dumps[2])
    assert origin == bytes((0, 0))
    assert map_rows(screen)[23-4][4] == 'P' and map_rows(screen)[23-6][9] == '='
    assert map_cue(screen).startswith(' 4,4 HEAD 140 ')
    position, after_walk = r.dumps[3:5]
    assert position[:4] == bytes((0, 7, 0, 4))
    assert after_walk != initial
    assert r.dumps[5] == bytes((0, 0)), 'reopening must discard the old scrolled window'
    screen = text_screen(r.dumps[6])
    assert map_cue(screen).startswith(' 7,4 HEAD 140 ')
    row = map_rows(screen)[23-4]
    assert row[4] == 'C' and row[7] == 'P' and row[10] == 'R' and row[11] == 'H'
    assert row[20] == '.', 'old ranger marker must disappear'
    assert map_rows(screen)[23-6][9] == '+', 'terrain must be reread when MAP opens'
    turned = r.dumps[7]
    assert r.dumps[8] == bytes((0, 0))
    assert map_cue(text_screen(r.dumps[9])).startswith(' 7,4 HEAD 420 ')
    assert r.dumps[10] == turned, 'opening/closing MAP must preserve current HGR and compass'
    print('  MAP ready before display; reopen after scrolling/travel/turn refreshes position, window, terrain and markers: OK')


def cardinal_walks():
    """North on the compass moves north on MAP, with the crash as an anchor."""
    from test_hud import header, expected as compass_pixels
    m = bytearray(mapbin())
    m[2:8] = bytes((0,40,0,40,0,0))
    m[8:10] = bytes((60,60))
    m[13:16] = bytes((70,70,0))
    m[16:19] = bytes((1,42,44))
    m[24] = 0                   # true and magnetic north coincide in this fixture
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp,m)
        steps = [IDLE,L.poke('nature_frequency',0)]+command('USE COMPASS')   # lot 7: aid in use
        cases = [('N',0,3,0),('E',3,0,140),('S',0,-3,280),('W',-3,0,420)]
        for name,dx,dy,heading in cases:
            for label,value in [('px',40*256),('py',40*256)]:
                steps += [L.poke(label,value),L.poke(label,value>>8,1)]
            steps += command('LOOK '+name)+command('WALK 54 MIN')
            steps += [L.peek('px',6),L.peek('s_hour',5),'peek:2000:8192',
                      'key:MAP','press:\\r',L.until('topo_show',20000),'peek:0400:1024',
                      L.until('topo_key',20000),'key:\\r','wait:1',IDLE,L.peek('s_hour',5),'peek:2000:8192']
        result = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    for i,(name,dx,dy,heading) in enumerate(cases):
        pos,hour,view,maptext,returned_hour,returned_view = result.dumps[i*6:i*6+6]
        got=tuple(int.from_bytes(pos[j:j+2],'little') for j in (0,2,4))
        error=(got[2]-heading)%560   # the compass error (+-2 degrees) of the original
        assert got[:2]==((40+dx)*256,(40+dy)*256) and min(error,560-error)<=4,(name,got)
        assert header(view)==compass_pixels(got[2],0),name
        rows=map_rows(text_screen(maptext))
        marks={c:(x,y) for y,row in enumerate(rows) for x,c in enumerate(row) if c in 'PC'}
        assert set(marks)=={'P','C'},(name,marks)
        px_,py_=marks['P'];cx_,cy_=marks['C']
        assert (px_-cx_,py_-cy_)==(dx,-dy), (name,marks)
        assert hour==returned_hour and view==returned_view, 'MAP must spend no time and preserve the current compass/view'
    print('  real WALK N/E/S/W: compass, world displacement and north-up MAP agree; WALK follows the facing direction: OK')


def temperatures():
    done=f'until:{L["idle"]+3:04X}:6000'
    steps=[IDLE]+call(['thermal'])+poke('s_metabolic',1.65)+poke('s_step',0)+[done,IDLE]
    steps += call(['thermal_rate'])
    cases=[]
    for air in (-20,0,42,100,127):
        for inside in (0,1):
            cases.append((air,inside))
            felt=air-20
            steps += poke('s_insul',47)+poke('s_metabolic',1.65)+poke('s_body',98.6)
            steps += [L.poke('airtemp',air), L.poke('felt_temp',felt),
                      L.poke('felt_temp',felt>>8,1),L.poke('shelter_inside',inside),done,
                      L.peek('s_therm_rate',5),L.peek('thermal_zone'),IDLE]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    for k,(air,inside) in enumerate(cases):
        rate,zone=scalar(air+15 if inside else air-20,47,1.65)
        assert abs(fp(r.dumps[2*k])-rate)<2e-7, (air,inside,fp(r.dumps[2*k]),rate)
        assert r.dumps[2*k+1][0] == zone
    print('  original ambient + 15 F shelter rule, outdoor wind and signed limits: OK')


def overnight(disk):
    steps=[IDLE]+command('WALK 54 MIN')+command('ENTER SHELTER')+hours('REST',12)
    steps += [L.peek('night',2),L.peek('dead'),'peek:2000:8192']
    steps += command('LOOK R')+[L.peek('shelter_inside'),'peek:2000:8192']
    steps += command('LEAVE SHELTER')+[L.peek('shelter_inside'),'peek:0400:1024']
    steps += command('ENTER SHELTER')+[L.peek('shelter_inside'),'peek:2000:8192']
    r=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
    assert r.dumps[0:2] == [b'\1\1',b'\0']
    assert view_rows(r.dumps[2]) == bytes(6400)
    assert r.dumps[3] == b'\1' and view_rows(r.dumps[4]) == bytes(6400)
    assert r.dumps[5] == b'\0'
    assert 'NOT ENOUGH LIGHT' in '\n'.join(text_screen(r.dumps[6]))
    assert r.dumps[7] == b'\1' and view_rows(r.dumps[8]) == bytes(6400)
    print('  overnight shelter, indoor turns, night exit and re-entry: OK')


def topo_delta(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        for step in ('key:MAP', 'press:\\r', L.until('topo_key',20000)):
            s.step(step)
        for key in ('J','K','L','I','J','K','J','K'):
            before = s.step('peek:0400:1024').data
            s.step(f'press:{key}')
            s.step(L.until('topo_redraw',6000))
            profile = s.step(f'pcprof:{L["topo_key"]:04X}:6000')
            after = s.step('peek:0400:1024').data
            pcs = {int(a,16): int(c) for a,c in re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', profile.out, re.M)}
            writes = text_writes(pcs)
            changes = text_changes(before, after)
            assert writes == changes, (key,writes,changes)
            if key in ('J','K') and before == after:
                assert writes == 0, 'clamped scroll must not write a single screen character'
        s.step('key:\\r')
        s.step(IDLE)
    print('  MAP scroll: exactly one write per changed character; unchanged/clamped map: zero writes OK')


MAP_CHARS = set('.,:;+*^#=TtPCHR')


def full_screen(disk):
    """MAP fills the 80 x 24 text screen (40 x 24 cells): only the cue of row 0
    is not map; at the four corners of the travel area and after scrolling
    against each edge the player stays visible where the clamped window puts
    it; the prompt rows come back intact; a walk against the east edge keeps
    P on screen at every half-step in a window centred once; a walk across
    the margin scrolls exactly once (src/sites.s topo_follow)."""
    GW, GH = 112, 84
    with a2test.Session(disk) as s:
        s.step(IDLE)
        prompt = text_screen(s.step('peek:0400:1024').data)[20:]
        for x, y, keys in ((2, 2, 'JK'), (GW-3, 2, 'LK'), (2, GH-3, 'JI'), (GW-3, GH-3, 'LI')):
            for name, value in (('px', x), ('py', y)):
                s.step(L.poke(name, 128)); s.step(L.poke(name, value, 1))
            for step in ('key:MAP', 'press:\\r', L.until('topo_key', 20000)):
                s.step(step)
            for key in keys * 3 + 'C' + keys * 3:   # clamped: the window stays put
                s.step(f'press:{key}'); s.step(L.until('topo_key', 6000))
                ox, oy = s.step(L.peek('topo_x', 2)).data
                assert (ox, oy) == (min(max(x - 20, 0), GW - 40), min(max(y - 12, 0), GH - 24)), (x, y, key, ox, oy)
                screen = text_screen(s.step('peek:0400:1024').data)
                cue = map_cue(screen)
                assert cue and cue.startswith(f' {x},{y} HEAD '), screen[0]
                rows = map_rows(screen)
                assert len(rows) == 24 and all(len(row) == 40 for row in rows)
                assert set(''.join(rows[1:])) <= MAP_CHARS, ('stray row', screen)
                assert set(rows[0][len(cue)//2:]) <= MAP_CHARS and len(cue) < 40, screen[0]
                where = [(c, r) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == 'P']
                assert where == [(x - ox, 23 - (y - oy))], (x, y, key, where)
            s.step('press:\\e'); s.step(IDLE)
            back = text_screen(s.step('peek:0400:1024').data)[20:]
            # The grid comes back; the result column is cleared, as before
            # the full-screen MAP (back_to_view_now), and keeps column 79.
            assert [row[39:] for row in back] == [row[39:] for row in prompt], ('prompt rows after MAP', prompt, back)
            assert not any(row[:39].strip() for row in back[:3]) and back[3].startswith('FOOD'), back
            assert all(row[79] == ' ' for row in back), back
        # East edge: WALK east from x = 104 stops before the outer band. The
        # last MAP left the window at (72, 60): P (row 40) is outside it, so
        # the first update centres it once (clamped: 72, 28); then it stays.
        for name, value in (('px', 104), ('py', 40)):
            s.step(L.poke(name, 128)); s.step(L.poke(name, value, 1))
        s.step(L.poke('heading', 140)); s.step(L.poke('heading', 0, 1))
        s.step('key:WALK 100 MIN\\r')
        seen = 0
        for _ in range(12):
            s.step(L.until('topo_moving_done', 6000))
            px = s.step(L.peek('px', 2)).data[1]
            ox, oy = s.step(L.peek('topo_x', 2)).data
            assert (ox, oy) == (GW - 40, 40 - 12), (px, ox, oy)
            rows = map_rows(text_screen(s.step('peek:0400:1024').data))
            assert rows[11][px - ox] == 'P' and set(''.join(rows[1:])) <= MAP_CHARS, (px, rows[11])
            seen += 1
            if px >= GW - 3:
                break
            s.step('wait:1')            # leave topo_moving_done before the next until
        assert seen >= 6, seen
        s.step(IDLE)
        screen = text_screen(s.step('peek:0400:1024').data)
        assert [row[39:] for row in screen[20:]] == [row[39:] for row in prompt], ('grid after the walk', screen[20:])
        assert 'TRAVEL:' in '\n'.join(screen) and all(row[79] == ' ' for row in screen[20:]), screen[20:]
        # Margin: P inside the window keeps it. P in column 35 walks east;
        # reaching column 36 (4 cells from the edge) scrolls the window by
        # a quarter (10 cells), once: one full differential redraw. Every
        # other half-step writes P's two cells and the cue only. (This
        # route finds insects after 36 minutes: four half-steps.)
        for name, value in (('px', 80), ('py', 40)):
            s.step(L.poke(name, 128)); s.step(L.poke(name, value, 1))
        s.step(L.poke('topo_x', 45)); s.step(L.poke('topo_y', 28))
        s.step('key:WALK 100 MIN\\r')
        scrolls, origin = [], (45, 28)
        for step in range(4):           # 9-minute half-steps: P reaches x = 82
            s.step(L.until('walk_progress', 6000))
            before = s.step('peek:0400:1024').data
            profile = s.step(f'pcprof:{L["topo_moving_done"]:04X}:6000')
            after = s.step('peek:0400:1024').data
            pcs = {int(a, 16): int(c) for a, c in re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', profile.out, re.M)}
            writes = text_writes(pcs)
            assert writes == text_changes(before, after), (step, writes)
            px = s.step(L.peek('px', 2)).data[1]
            ox, oy = s.step(L.peek('topo_x', 2)).data
            assert map_rows(text_screen(after))[23 - (40 - oy)][px - ox] == 'P', (px, ox, oy)
            assert 4 <= px - ox < 36 and oy == 28, (px, ox, oy)
            if (ox, oy) != origin:
                scrolls.append((px, origin, (ox, oy)))
                origin = (ox, oy)
            elif step:                  # the first update draws the whole map
                assert text_changes(before, after, rows=range(1, 24)) <= 4, (step, px)
                assert writes <= 4 + text_changes(before, after, rows=(0,)), (step, writes)
            s.step('wait:1')
        assert scrolls == [(81, (45, 28), (55, 28))], scrolls
        s.step(IDLE)
    print(f'  full-screen MAP: 40 x 24 cells, cue only on row 0, P visible at the four corners and against '
          f'every edge, prompt rows restored; east-edge walk keeps P on screen ({seen} half-steps) in a window '
          f'centred once; a walk across the 4-cell margin scrolls once (x = 81, origin 45 -> 55): OK')


def shelter_fixed(disk):
    """A natural shelter found by TRAVEL's resource scan (species 12) moves
    the cabin only on a native map (MAP+37): a generated map keeps its cabin
    in its cell (header 16-20, here (7, 4) facing 140) and the walk goes on.
    The idle loop holds the probe LDA #12, JSR overlay_load, LDX #12,
    JMP rs_resource, stopped at resource_next."""
    I, ol, rr = L['idle'], L['overlay_load'], L['rs_resource']
    probe = bytes((0xA9, 12, 0x20, ol & 255, ol >> 8, 0xA2, 12, 0x4C, rr & 255, rr >> 8))
    got = []
    with a2test.Session(disk, timeout=600) as s:
        s.step(IDLE)
        px = s.step(L.peek('px', 4)).data
        rocky = 0x7040 + px[3] * 112 + px[1]
        for native in (0, 1, 2):
            if native:
                s.step(f'until:{I:04X}:100')
            if native == 2:             # rocky ground (level 96 and more): the rock
                s.step(f'poke:{rocky:04X}:64')
            s.step(f'poke:7025:{min(native, 1):02X}')
            s.step(L.poke('act', 1))
            s.step(L.poke('fauna_alert', 0))
            for i, b in enumerate(probe):
                s.step(f'poke:{I + i:04X}:{b:02X}')
            s.step(L.until('resource_next', 6000))
            got.append((s.step('peek:7010:5').data, s.step(L.peek('fauna_alert')).data[0],
                        s.step(L.peek('px', 4)).data, s.step(L.peek('heading', 2)).data))
            if native < 2:
                for i, b in enumerate((0x4C, I & 255, I >> 8)):    # the next run stops at idle
                    s.step(L.poke('resource_next', b, i))
    (cabin, alert, _, _), (moved, alert2, pos, head), (rock, _, pos2, head2) = got
    assert cabin == bytes((1, 7, 4, 140, 0)) and alert == 0, (cabin, alert)
    assert moved == bytes((1, pos[1], pos[3])) + head and alert2 == 1, (moved, pos, head, alert2)
    assert rock == bytes((2, pos2[1], pos2[3])) + head2, (rock, pos2, head2)
    print('  natural shelter: the generated map keeps its cabin at (7, 4); a native map records '
          'the current cell, a log (MAP+16 = 1) below level 96, a rock (2) on rocky ground: OK')


def native_mapbin():
    """mapbin() made native (MAP+37 = 1, flat fine geography appended): the
    cabin header becomes a natural shelter found at (7, 4), a log; the ground
    is at level 94, the cell (12, 4) rocky (level 97)."""
    m = bytearray(mapbin())
    m[37] = 1
    for k in range(64, 64 + 9408):                  # high ground, just below rocky
        m[k] = 94 | (m[k] & 128)
    m[64+4*112+12] = 97
    m[21] = 98
    fine = bytearray([94]) * (224*168)
    for y in (8, 9):
        for x in (24, 25):
            fine[y*224+x] = 97
        for x in (18, 19):
            fine[(y+4)*224+x] = 94 | 128            # the water cell (9, 6)
    return bytes(m) + bytes(294) + bytes(fine) + bytes(28*168)   # no woodland


def native_shelter():
    """Lot 6 on a native map: the natural shelter draws the log (MAP+16 = 1)
    or the rock (2) instead of the hut, locally and as a billboard, pixel for
    pixel against tools/dhgr_ref; NEOWILD.BLK is read once per sprite shown;
    SAVE/RESTORE keeps MAP+16."""
    from common import terrain_boot, dhgr_view, dhgr_scene
    import scene_ref
    from test_save import Game
    m = bytearray(native_mapbin())
    frames = [((7, 4, 140), None), ((7, 4, 70), None),
              ((12, 4, 210), (2, 12, 4, 210)), ((10, 4, 140), None), ((9, 3, 140), None),
              ((10, 4, 0), (1, 10, 4, 0)), ((14, 4, 140), None)]
    got = []
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, bytes(m))
        with a2test.Session(disk, timeout=900) as s:
            for step in terrain_boot(20000):
                s.step(step)
            g = Game(s)
            for (x, y, head), shelter in frames:
                if shelter:
                    kind, cx, cy, bearing = shelter
                    for i, b in enumerate((kind, cx, cy, bearing & 255, bearing >> 8)):
                        s.step(f'poke:{0x7010+i:04X}:{b:02X}')
                    s.step('poke:7022:00')
                    s.step('poke:7023:00')
                for name, value in (('px', x*256), ('py', y*256), ('heading', head)):
                    s.step(L.poke(name, value & 255))
                    s.step(L.poke(name, value >> 8, 1))
                reads = g.word('mli_reads')
                for step in command('V'):
                    s.step(step)
                page = s.step('peek:2000:8192').dumps[0]
                header = s.step('peek:7000:64').dumps[0]
                got.append((page, g.word('mli_reads') - reads, header, s.step(L.peek('sky_mood')).dumps[0]))
            g.type('SAVE', answer='1\\r')
            s.step('poke:7010:00')
            g.type('RESTORE', answer='1\\r')
            restored = s.step('peek:7010:5').dumps[0]
    assets = []
    for ((x, y, head), _), (page, reads, header, mood) in zip(frames, got):
        live = header + bytes(m[64:])
        sel = scene_ref.select(live, x*256, y*256, head)
        ref = dhgr_scene(live, x*256, y*256, head, mood)
        n = sum(a != b for r_, w in zip(dhgr_view(page), ref) for a, b in zip(r_, w))
        assert not n, ((x, y, head), n, sel, [(r, c, g_[c], w[c]) for r, (g_, w) in enumerate(zip(dhgr_view(page), ref)) for c in range(140) if g_[c] != w[c]][:10])
        assets.append((sel and sel['asset'], reads))
    assert assets == [(33, 3), (33, 0), (34, 3), (34, 0), (34, 0), (33, 3), (35, 5)], assets
    assert restored == bytes((1, 10, 4, 0, 0)), restored.hex()
    print('  native map: the found shelter is a log on low ground, a rock on rocky ground, locally and '
          'as a billboard (exact frames); each sprite read once from NEOWILD.BLK; SAVE keeps MAP+16: OK')


def generated_shelter():
    """The fixed cabin of a generated map (MAP+37 = 0) is drawn as the
    original's natural shelter: tools/mkmap.py writes MAP+16 = 1 (the log)
    below level 96, 2 (the rock) on rocky ground, and PROJECT draws asset
    32 + MAP+16, locally and as a billboard, pixel for pixel against
    tools/dhgr_ref. The control map raised to level 90: its cabin (7, 4) is a
    log; moved to the rocky cell (12, 4) (level 97) with MAP+16 = 2, the rock.
    Then billboards whose cell towers over the eye, anchored at view row 0
    where only their bottom row shows (once rejected by PROJECT, leaving the
    ridge black), and billboards cut by the side and bottom edges."""
    import mkmap
    from common import terrain_boot, dhgr_view, dhgr_scene
    import scene_ref
    W, H = 2 * mkmap.GW, 2 * mkmap.GH
    for level, kind in ((10, 1), (95, 1), (96, 2), (110, 2)):
        h = [[level] * W for _ in range(H)]
        water = [[False] * W for _ in range(H)]
        made = mkmap.map_bin(h, water, (20, 20), (180, 140), 140)
        assert made[16] == kind and made[17:19] != bytes(2), (level, made[16:21].hex())
    m = bytearray(mapbin())
    for k in range(64, 64 + 9408):                  # high ground, below rocky
        m[k] = 90 | (m[k] & 128)
    m[64 + 4*112 + 12] = 97
    m[21] = 98
    rocky = bytearray(m)
    rocky[16:19] = bytes((2, 12, 4))
    frames = [(m, (7, 4, 140)), (m, (10, 4, 420)), (rocky, (12, 4, 140)), (rocky, (15, 4, 420))]

    def cliff(base, *cells):
        """base with these cells at level 125 (MAP+21 = 126): a billboard
        site 33+ levels above the eye, anchored at view row 0."""
        live = bytearray(base)
        live[21] = 126
        for cx, cy in cells:
            live[64 + cy*112 + cx] = 125
        return live
    # Clipped at the top (3*q/16 >= 256: PROJECT rejected these sites
    # until 2026-10-15): the rock at depths 2 to 4, the log, the wreck (start
    # cell (4, 4)) and the outpost (20, 4); the rock cut by the right and left
    # edges; the rock 8 levels below a raised eye, cut by the bottom of the view.
    rock_cliff, log_cliff = cliff(rocky, (12, 4)), cliff(m, (7, 4))
    low_rock = bytearray(rocky)
    low_rock[21] = 126
    low_rock[64 + 4*112 + 15] = 103
    clipped = [(rock_cliff, (15, 4, 420)), (rock_cliff, (14, 4, 420)), (rock_cliff, (16, 4, 420)),
               (rock_cliff, (15, 4, 380)), (rock_cliff, (15, 4, 500)),
               (log_cliff, (10, 4, 420)), (cliff(m, (4, 4)), (1, 4, 140)),
               (cliff(m, (20, 4)), (23, 4, 420)), (low_rock, (15, 4, 420))]
    frames += clipped
    got = []
    with tempfile.TemporaryDirectory() as tmp, \
            a2test.Session(disk_with(tmp, bytes(m)), timeout=900) as s:
        for step in terrain_boot(20000):
            s.step(step)
        shown = m
        for live, (x, y, head) in frames:
            for i in range(16, len(live)):          # header 16..21 and changed cells
                if live[i] != shown[i] or i < 19:
                    s.step(f'poke:{0x7000 + i:04X}:{live[i]:02X}')
            if live[22:] != shown[22:]:             # the scene cache keys on the position
                s.step(L.poke('scene_cache_valid', 0))
            shown = live
            for name, value in (('px', x*256), ('py', y*256), ('heading', head)):
                s.step(L.poke(name, value & 255))
                s.step(L.poke(name, value >> 8, 1))
            for step in command('V'):
                s.step(step)
            got.append((s.step('peek:2000:8192').dumps[0], s.step('peek:7000:64').dumps[0],
                        s.step(L.peek('sky_mood')).dumps[0]))
    assets = []
    for (live, (x, y, head)), (page, header, mood) in zip(frames, got):
        assert header[:22] == bytes(live[:22]), (header[:22].hex(), bytes(live[:22]).hex())
        sel = scene_ref.select(bytes(live), x*256, y*256, head)
        ref = dhgr_scene(bytes(live), x*256, y*256, head, mood)
        n = sum(a != b for r_, w in zip(dhgr_view(page), ref) for a, b in zip(r_, w))
        assert not n, ((x, y, head), n, sel)
        assets.append(sel and sel['asset'])
    assert assets == [33, 33, 34, 34, 34, 34, 34, 34, 34, 33, 5, 35, 34], assets
    for (live, (x, y, head)) in clipped[:-1]:
        assert scene_ref.select(bytes(live), x*256, y*256, head)['anchor'] == 0, (x, y, head)
    edges = [scene_ref.select(bytes(live), x*256, y*256, head) for live, (x, y, head) in clipped]
    assert edges[3]['left'] + edges[3]['width'] > 140 and edges[4]['left'] < 0, edges[3:5]
    assert 160 <= edges[-1]['anchor'] < 252, edges[-1]
    print('  generated map: mkmap writes the log (MAP+16 = 1) below level 96, the rock (2) from 96; '
          'the fixed cabin is drawn as that log or rock, locally and as a billboard; billboards '
          'clipped at row 0 (rock, log, wreck, outpost), at the edges and the bottom (exact frames): OK')


def poke_built(s, cr_sx, cr_sy, tent):
    """craft_state's shelters (cr_sx, cr_sy) and the tent (item 9) on the
    ground at tent = (x, y), or not (None), then a fresh projection."""
    for i in range(3):
        s.step(L.poke('cr_sx', cr_sx[i], i))
        s.step(L.poke('cr_sy', cr_sy[i], i))
    s.step(L.poke('it_place', 0 if tent else 0xFF, 9))
    if tent:
        s.step(L.poke('it_x', tent[0], 9))
        s.step(L.poke('it_y', tent[1], 9))
    s.step(L.poke('scene_cache_valid', 0))


def built_shelter_sprites():
    """Lot 3 step 3 (XL): the built tent, hut (cabin.bin), igloo and trench
    are site sprites, drawn on their cell and as billboards, pixel for pixel
    against tools/dhgr_ref (scene_ref.built_shelters); the original's local
    order (wreck, outpost, igloo, hut, tent, natural shelter, trench), ties
    of billboards to the first (tent, hut, igloo, trench after the others);
    no pitched tent at the wreck; NEOWILD.BLK read once per sprite shown.
    Then MAKE TRENCH, DROP TENT and GET TENT redraw the view with the
    shelter (scene_prepare's cache dropped), and the 140 KB edition, which
    has none of these sprites, draws nothing for a built shelter."""
    from common import terrain_boot, dhgr_view, dhgr_scene, DISK140
    import json
    import scene_ref
    from test_save import Game
    m = bytearray(native_mapbin())
    NO = (255, 255, 255)
    hut = ((10, 255, 255), (3, 255, 255))
    hut_igloo = ((10, 10, 255), (3, 3, 255))
    trench = ((10, 10, 7), (3, 3, 4))           # the trench on the log's cell
    trench2 = ((10, 10, 14), (3, 3, 6))
    hut_log = ((7, 10, 14), (4, 3, 6))
    frames = [((10, 3, 140), hut, None, 37, 3), ((13, 3, 420), hut, None, 37, 0),
              ((10, 3, 140), hut_igloo, None, 38, 2), ((10, 6, 280), hut_igloo, None, 37, 3),
              ((7, 4, 140), trench, None, 33, 3),
              ((14, 8, 280), trench2, None, 39, 1), ((14, 6, 280), trench2, None, 39, 0),
              ((16, 3, 140), trench2, (16, 3), 36, 2), ((18, 3, 420), trench2, (16, 3), 36, 0),
              ((5, 6, 280), (NO, NO), (4, 4), 5, 0), ((5, 6, 280), (NO, NO), (5, 5), 36, 0),
              ((7, 4, 210), hut_log, None, 37, 3)]
    got = []
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, bytes(m))
        layout = None
        with a2test.Session(disk, timeout=900) as s:
            for step in terrain_boot(20000):
                s.step(step)
            g = Game(s)
            for (x, y, head), (sx, sy), tent, _, _ in frames:
                poke_built(s, sx, sy, tent)
                for name, value in (('px', x*256), ('py', y*256), ('heading', head)):
                    s.step(L.poke(name, value & 255))
                    s.step(L.poke(name, value >> 8, 1))
                reads = g.word('mli_reads')
                for step in command('V'):
                    s.step(step)
                got.append((s.step('peek:2000:8192').dumps[0], g.word('mli_reads') - reads,
                            s.step('peek:7000:64').dumps[0], s.step(L.peek('sky_mood')).dumps[0],
                            s.step(L.peek('scene_asset')).dumps[0][0]))
            # The commands: MAKE TRENCH (anywhere but the water, the wreck and
            # the outpost), then the tent set down and picked up again.
            poke_built(s, NO, NO, None)
            for name, value in (('px', 14*256), ('py', 6*256)):
                s.step(L.poke(name, value & 255))
                s.step(L.poke(name, value >> 8, 1))
            for step in command('V'):
                s.step(step)
            before = s.step(L.peek('scene_asset')).dumps[0][0]
            for step in command('MAKE TRENCH'):
                s.step(step)
            made = (s.step(L.peek('cr_sx', 3)).dumps[0], s.step(L.peek('cr_sy', 3)).dumps[0],
                    s.step(L.peek('scene_asset')).dumps[0][0])
            for name, value in (('px', 16*256), ('py', 3*256)):
                s.step(L.poke(name, value & 255))
                s.step(L.poke(name, value >> 8, 1))
            s.step(L.poke('it_place', 2, 9))            # the tent in the pack
            for step in command('V') + command('DROP TENT') + command('V'):
                s.step(step)
            dropped = (s.step(L.peek('it_place', 1, 9)).dumps[0][0], s.step(L.peek('scene_asset')).dumps[0][0])
            for step in command('GET TENT') + command('V'):
                s.step(step)
            taken = (s.step(L.peek('it_place', 1, 9)).dumps[0][0], s.step(L.peek('scene_asset')).dumps[0][0])
    seen = []
    for ((x, y, head), (sx, sy), tent, asset, blocks), (page, reads, header, mood, shown) in zip(frames, got):
        live = header + bytes(m[64:])
        built = scene_ref.built_shelters(live, sx, sy, tent)
        sel = scene_ref.select(live, x*256, y*256, head, built=built)
        ref = dhgr_scene(live, x*256, y*256, head, mood, built=built)
        n = sum(a != b for r_, w in zip(dhgr_view(page), ref) for a, b in zip(r_, w))
        assert not n, ((x, y, head), n, sel)
        seen.append((sel and sel['asset'], shown, reads))
    assert seen == [(a, a, b) for _, _, _, a, b in frames], seen
    assert before != 39 and made == (bytes((255, 255, 14)), bytes((255, 255, 6)), 39), (before, made)
    assert dropped == (0, 36) and taken[0] != 0 and taken[1] != 36, (dropped, taken)
    print('  XL: the built tent, hut, igloo and trench drawn on their cell and as billboards (exact '
          'frames); local order igloo > hut > tent > log > trench; no tent at the wreck; each sprite '
          'read once; MAKE TRENCH, DROP TENT, GET TENT redraw the view: OK')

    # The 140 KB edition: no shelter sprite on NEOWILD.BLK, PROJECT cut at
    # its tail; a hut on the player's cell leaves the view as it was.
    lay = json.loads((HERE / 'build/layout-140.json').read_text())
    assert set(lay['disk']['sites']) == {'log', 'rock', 'outpost'}, lay['disk']['sites']
    assert lay['trunk_modules']['11']['length'] == L['project_tail'] - 0x5800
    xl = json.loads((HERE / 'build/layout.json').read_text())
    assert set(xl['disk']['sites']) == {'log', 'rock', 'outpost', 'tent', 'cabin', 'igloo', 'trench'}
    assert xl['trunk_modules']['11']['length'] == L['project_end'] - 0x5800
    out = []
    for disk in (DISK140, DISK):
        with a2test.Session(disk, timeout=600, menu=False) as s:
            s.step(L.until('menu_key', 40000))
            s.step('key:1\r')         # the Sierra Nevada (common.MENU_KEY)
            s.step(L.until('idle', 60000))
            s.step(L.poke('nature_frequency', 0))
            g = Game(s)
            pos = s.step(L.peek('px', 4)).dumps[0]
            x, y = pos[1] + 1, pos[3]               # beside the wreck
            s.step(L.poke('px', x, 1))
            for step in command('V'):
                s.step(step)
            plain = s.step('peek:2000:8192').dumps[0]
            poke_built(s, (x, 255, 255), (y, 255, 255), None)
            reads = g.word('mli_reads')
            for step in command('V'):
                s.step(step)
            out.append((plain, s.step('peek:2000:8192').dumps[0], g.word('mli_reads') - reads,
                        s.step(L.peek('scene_asset')).dumps[0][0]))
    (plain, hut140, reads140, asset140), (_, hutxl, readsxl, assetxl) = out
    assert view_rows(hut140) == view_rows(plain) and reads140 == 0 and asset140 != 37, (reads140, asset140)
    assert assetxl == 37 and readsxl == 3 and view_rows(hutxl) != view_rows(out[1][0]), (assetxl, readsxl)
    print('  140 KB edition: three site sprites, PROJECT ends at its tail, a hut on the cell draws '
          'nothing and reads nothing; the same hut on NeoWildernessXL: the hut sprite (3 blocks): OK')


def main():
    cardinal_walks()
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,mapbin())
        shelter_fixed(disk)
        topo_refresh(disk)
        topo_delta(disk)
        full_screen(disk)
        playable(disk)
        overnight(disk)
    temperatures()
    generated_shelter()
    native_shelter()
    built_shelter_sprites()
    assert 0 < (HERE/'build/wildsit.bin').stat().st_size <= 2048
    print('Cabin and MAP: OK')


if __name__ == '__main__':
    main()
