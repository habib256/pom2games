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
    for key, count in [('D',12),('W',20),('A',20),('S',20)]:
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
    for key in ('D', 'D', 'W', 'W'):
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
        steps = [IDLE,L.poke('nature_frequency',0)]
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
        want=((40+dx)*256,(40+dy)*256,heading)
        assert tuple(int.from_bytes(pos[j:j+2],'little') for j in (0,2,4))==want,name
        assert header(view)==compass_pixels(heading,0),name
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
        for key in ('A','S','D','W','A','S','A','S'):
            before = s.step('peek:0400:1024').data
            s.step(f'press:{key}')
            s.step(L.until('topo_redraw',6000))
            profile = s.step(f'pcprof:{L["topo_key"]:04X}:6000')
            after = s.step('peek:0400:1024').data
            pcs = {int(a,16): int(c) for a,c in re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', profile.out, re.M)}
            writes = text_writes(pcs)
            changes = text_changes(before, after)
            assert writes == changes, (key,writes,changes)
            if key in ('A','S') and before == after:
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
        for x, y, keys in ((2, 2, 'AS'), (GW-3, 2, 'DS'), (2, GH-3, 'AW'), (GW-3, GH-3, 'DW')):
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
            assert [row[:40] for row in back] == [row[:40] for row in prompt], ('prompt rows after MAP', prompt, back)
            assert not any(row[40:79].strip() for row in back[:3]) and back[3][40:].startswith('FOOD'), back
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
        assert [row[:40] for row in screen[20:]] == [row[:40] for row in prompt], ('grid after the walk', screen[20:])
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


def main():
    cardinal_walks()
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,mapbin())
        topo_refresh(disk)
        topo_delta(disk)
        full_screen(disk)
        playable(disk)
        overnight(disk)
    temperatures()
    assert 0 < (HERE/'build/wildsit.bin').stat().st_size <= 2048
    print('Cabin and MAP: OK')


if __name__ == '__main__':
    main()
