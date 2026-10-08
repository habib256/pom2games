#!/usr/bin/env python3
"""Verify map wall knowledge and readable feedback on the actual DOS game."""
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
from check_rendering import pixel, native

L = a2test.labels(ROOT / 'maze3d/build/maze3d.lbl')
DISK = ROOT / 'dist/MAZE3D.dsk'
START = ['wait:2200', 'key:S', 'wait:30', 'key:B', 'wait:30', 'key:E',
         'wait:30', 'key:E', 'wait:30', 'key:F', 'wait:30', 'key:\r', 'wait:700']
DUMP = [L.peek('front_page'), 'peek:2000:16384', L.peek('font_base', 512)]

def run(steps):
    return a2test.run(DISK, START + steps, emulator=a2test.A2SHOT)

def page(r):
    index = int(r.mem(L['front_page'], 1)[0] != 0)
    return r.mem(0x2000, 16384)[index*8192:(index+1)*8192]

def row(r, n):
    memory = page(r)
    font = r.mem(L['font_base'], 512)
    # The font's high seven bits are reversed into each native HGR byte.
    glyphs = {bytes(int(f'{b:08b}'[:7][::-1], 2) for b in font[i:i+8]): chr(32+i//8)
              for i in range(0, 512, 8)}
    return ''.join(glyphs.get(bytes(memory[a2test.hgr_offset(n*8+y)+4+x] & 127
                                    for y in range(8)), '?') for x in range(32))

def map_walls():
    # Stairs are visible on every floor before the player explores the exit.
    for floor in (1, 2, 3):
        r = run([L.poke('p_floor', floor), 'key:M', 'wait:60'] + DUMP + ['peek:104c:1'])
        assert not r.mem(0x104c, 1)[0] & 128, 'test requires unexplored stairs'
        assert 'E' in row(r, 15), row(r, 15)
        assert 'E STAIRS' in row(r, 20), row(r, 20)
    # A revealed dragon cannot obscure the stairs marker with an M.
    r = run([L.poke('p_floor', 3), 'poke:10a7:0a', 'poke:10af:06',
             'poke:10b7:03', 'poke:104c:40', 'key:M', 'wait:60'] + DUMP)
    assert 'E' in row(r, 15), row(r, 15)
    # Only one central cell has been visited: its four walls must all appear.
    setup = [f'poke:{0x1000+i:04x}:{128 if i == 38 else 0:02x}' for i in range(77)]
    setup += [L.poke('p_col', 5), L.poke('p_row', 3), 'key:M', 'wait:60']
    r = run(setup + DUMP)
    mem = page(r)
    for x, y in ((116, 76), (124, 68), (132, 76), (124, 84)):
        assert pixel(mem, native(x), y), f'missing player wall at {x},{y}'
    for x, y in ((100, 60), (108, 52), (148, 100)):
        assert not pixel(mem, native(x), y), 'unexplored wall leaked onto map'
    # Opening all four passages must remove those wall segments.
    openings = ['poke:1026:83', 'poke:1025:02', 'poke:1031:01']
    r = run(setup + openings + ['key:M', 'wait:30', 'key:M', 'wait:60'] + DUMP)
    for x, y in ((116, 76), (124, 68), (132, 76), (124, 84)):
        assert not pixel(page(r), native(x), y), 'open passage rendered as wall'
    # Revealed boundaries survive moving away, without marking neighbours visited.
    r = run(setup + [L.poke('p_col', 0), L.poke('p_row', 0), 'key:L', 'wait:60'] + DUMP)
    for x, y in ((116, 76), (124, 68), (132, 76), (124, 84)):
        assert pixel(page(r), native(x), y), 'known wall disappeared'

def feedback():
    r = run(DUMP)
    assert 'FIND RELIC' in row(r, 3)
    for floor in (1, 2, 3):
        for face, direction in enumerate('NESW'):
            header = run([L.poke('p_floor', floor), L.poke('p_face', (face+3) & 3),
                          'key:L', 'wait:60'] + DUMP)
            assert f'F{floor} {direction}' in row(header, 1), row(header, 1)
    assert 'HP 20/30' in row(r, 21), row(r, 21)
    assert 'POTIONS' in row(r, 21) and 'GOLD' in row(r, 21)
    assert row(r, 22).strip() == 'IJKL MOVE M MAP P POTION H HELP', row(r, 22)
    map_screen = run(['key:M', 'wait:60'] + DUMP)
    assert row(map_screen, 21) == row(r, 21), 'map hides exploration resources'
    help_screen = run(['key:H', 'wait:60'] + DUMP)
    assert 'ATK' in row(help_screen, 17) and 'XP' in row(help_screen, 17)
    resumed = run(['key:H', 'wait:60', 'key: ', 'wait:60'] + DUMP)
    assert row(resumed, 22) == row(r, 22), 'help left statistics in the exploration HUD'
    for available, expected in ((0, 'RETURN NEW GAME'), (1, 'C CONTINUE')):
        title = a2test.run(DISK, [L.until('title_footer'), L.poke('save_available', available),
                                'wait:60'] + DUMP,
                           emulator=a2test.A2SHOT)
        assert expected in row(title, 22), row(title, 22)

    for prefix, expected in (([L.poke('p_relic', 1)], 'REACH STAIRS'),
                             ([L.poke('p_relic', 1), L.poke('p_floor', 3)], 'SLAY DRAGON'),
                             ([L.poke('p_relic', 1), L.poke('p_floor', 3), 'poke:10b7:ff'], 'REACH STAIRS')):
        r = run(prefix + ['key:L', 'wait:60'] + DUMP)
        assert expected in row(r, 3), row(r, 3)
    for prefix, expected in (([L.poke('p_potions', 0)], 'NO POTIONS LEFT'),
                             ([L.poke('p_hp', 30)], 'HEALTH ALREADY FULL'),
                             ([L.poke('p_hp', 25)], 'POTION USED: UP TO +10 HP')):
        r = run(prefix + ['key:P', 'wait:60'] + DUMP)
        assert expected in row(r, 23), row(r, 23)
    # Real combat, with a living orc and a controlled starting health.
    combat = [L.poke('gstate', 4), L.poke('cur_mob', 0), L.poke('prev_state', 2),
              'poke:10b0:01', 'poke:10b8:1e', L.poke('p_hp', 20), 'key:L', 'wait:60']
    r = run(combat + ['key:G', 'wait:60'] + DUMP + [L.peek('p_focus'), L.peek('mob_phase')])
    assert 'HIT' in row(r, 22) and 'TAKEN' in row(r, 22)
    assert 'GUARD: HALF HIT, NEXT ATK +2' in row(r, 23), row(r, 23)
    assert r.mem(L['p_focus'], 1) == b'\2' and r.mem(L['mob_phase'], 1) == b'\1'
    r = run(combat + ['key:A', 'wait:60'] + DUMP)
    assert 'HIT' in row(r, 22) and 'ATTACK COMPLETE' in row(r, 23)
    r = run(combat + [L.poke('p_potions', 0), 'key:P', 'wait:60'] + DUMP + [L.peek('mob_phase')])
    assert 'NO POTIONS LEFT' in row(r, 22)
    assert r.mem(L['mob_phase'], 1) == b'\0', 'refused potion advanced the fight'
    # Readiness is independent of last-round feedback and persists through healing.
    critical = [L.poke('p_hp', 8) if step == L.poke('p_hp', 20) else step for step in combat]
    for actions, expected in (([], 'LOW HEALTH'),
                              (['key:G', 'wait:60'], 'LOW HEALTH / NEXT ATTACK +2'),
                              (['key:G', 'wait:60', 'key:P', 'wait:60'], 'NEXT ATTACK +2'),
                              (['key:G', 'wait:60', 'key:P', 'wait:60', 'key:A', 'wait:60'], '')):
        r = run(critical + actions + DUMP + [L.peek('p_hp')])
        assert row(r, 17).strip() == expected, row(r, 17)
        assert 'HP' in row(r, 14) and '/30' in row(r, 14)
        assert 'POTIONS' in row(r, 14) and 'GOLD' in row(r, 14)
        assert 'ATK' in row(r, 16) and 'DEF' in row(r, 16)
    r = run(critical + ['key:G', 'wait:60', L.poke('p_potions', 0), 'key:P', 'wait:60']
            + DUMP + [L.peek('mob_phase'), L.peek('p_focus')])
    assert 'NO POTIONS LEFT' in row(r, 22) and not row(r, 23).strip()
    assert row(r, 17).strip() == 'LOW HEALTH / NEXT ATTACK +2'
    assert r.mem(L['mob_phase'], 1) == b'\1' and r.mem(L['p_focus'], 1) == b'\2'
    # Force a goblin's steal roll, then read the actual updated gold on screen.
    goblin = ['poke:10b0:00' if step == 'poke:10b0:01' else step for step in combat]
    r = run(goblin + [L.poke('p_gold', 5), 'poke:0056:c5', 'poke:0057:00',
                      'key:G', 'wait:60'] + DUMP + [L.peek('p_gold')])
    assert r.mem(L['p_gold'], 1) == b'\4'
    assert row(r, 14).split('GOLD')[1].strip() == '4', row(r, 14)
    # Enter the shop through an unlocked exit, then check each refusal.
    shop = [L.poke('p_col', 9), L.poke('p_row', 6), L.poke('p_face', 1),
            L.poke('p_relic', 1), 'poke:104b:02', L.poke('p_gold', 0), 'key:I', 'wait:60']
    for prefix, key, expected in (([], 'A', 'NOT ENOUGH GOLD'),
                                  ([L.poke('p_hp', 30)], 'H', 'HEALTH ALREADY FULL'),
                                  ([L.poke('p_potions', 9)], 'P', 'POTION BAG FULL')):
        r = run(shop + prefix + ['key:' + key, 'wait:60'] + DUMP)
        assert expected in row(r, 22), row(r, 22)
    # Purchase effects are visible without leaving the shop or opening help.
    r = run(shop + [L.poke('p_gold', 24), 'key:A', 'wait:60', 'key:D', 'wait:60']
            + DUMP + [L.peek('p_atk'), L.peek('p_def')])
    assert int(row(r, 7).split('ATK')[1].split('DEF')[0]) == r.mem(L['p_atk'], 1)[0]
    assert int(row(r, 7).split('DEF')[1].split('LVL')[0]) == r.mem(L['p_def'], 1)[0]
    # Ergonomic changes must preserve the two exit locks.
    exit_setup = [L.poke('p_col', 9), L.poke('p_row', 6), L.poke('p_face', 1),
                  'poke:104b:02']
    for extra, expected in (([], 'FIND THE CHAMBER RELIC'),
                            ([L.poke('p_floor', 3), L.poke('p_relic', 1)],
                             'THE DRAGON GUARDS THE EXIT')):
        r = run(exit_setup + extra + ['key:I', 'wait:60'] + DUMP + [L.peek('gstate')])
        assert r.mem(L['gstate'], 1) == b'\2', 'locked exit advanced the game'
        assert expected in row(r, 23), row(r, 23)
    original = set(re.findall(r'ph_\w+: .byte "([^"]*)",0',
                             (ROOT / 'maze3d/src/narrator.asm').read_text()))
    r = run([L.peek('narrator_buffer', 32)])
    assert r.mem(L['narrator_buffer'], 32).split(b'\0')[0].decode() in original

if __name__ == '__main__':
    map_walls()
    feedback()
    print('ergonomics: map knowledge/resources, objectives, combat readiness, healing, theft, shop upgrades and feedback')
