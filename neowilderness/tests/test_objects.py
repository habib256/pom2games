#!/usr/bin/env python3
"""The OBJECTS page of transfers (16 October 2026, docs/MENUS.md 5 and 9,
src/inventory.s) on both editions.

  - layout, from the raw screen codes: the tab row, LOCAL (left) and
    CARRIED (right: HANDS, PACK, WORN) as post-its on XL (POSTITS), each
    item with its weight (the remedies with their uses), the cursor '>' in
    the half's column 1, the headings and MORE in inverse, CARRYING and
    LOAD, the gauge's cells (MouseText blocks on XL, inverse spaces on
    140 KB, no MouseText code there), what RETURN and H type on rows 20-21,
    the keys on row 23;
  - every transfer of the page is the typed command: RETURN on LOCAL (PACK,
    GET WATER, a refusal of the load), on CARRIED (DROP), H (CARRY), the
    second set (PACK ROCK refused, then accepted), a pile of the second set
    (PACK INSECTS: the whole pile, no question): after the page, the state
    equals the state after typing the same line at the prompt, and the page
    comes back with the game's answer in rows 20-22 and the cursor kept;
  - the gauge against the ROM (tools/re_load_probe.py, results.json): the
    limit is the original's $4BFA (815 oz: 43 left at the start, as $4BF8),
    the walk slowed by 100 x INT(ounces / 16) / (body + 2) percent (T08/S07's
    factor, no threshold before the limit), a thing taken from the ground
    refused when the weight left is below its W5 (GET ROCK with 100 oz left
    accepted, 99 refused), on the port as on the ROM;
  - GET of a source without the original's question (water: the canteen's
    room, then the weight left);
  - the time of a transfer (cycles from RETURN to the page again).
Screenshots: build/objects_v2_xl.png, build/objects_v2_140.png.
"""
import json
import re
import sys

from common import (HERE, L, DISK, DISK140, a2test, text_screen, raw_cell, postit_errors, page_frame,
                    TAB_ROW_140)

IDLE = L.until('idle', 20000)
READY = L.until('inventory_key', 60000)
LIMIT = 815                         # the original's $4BFA (re_load_probe: START)
fails = []
ORIGINAL = '--original' in sys.argv


def check(name, ok, detail=''):
    print(f'  {name}: {"OK" if ok else "FAIL " + str(detail)[:1500]}', flush=True)
    if not ok:
        fails.append(name)


def word(s, name, k=0):
    d = s.step(L.peek(name, 2, k)).data
    return d[0] | d[1] << 8


def rows(s):
    return text_screen(s.step('peek:0400:1024').data)


def open_page(s):
    s.step('key:INVENTORY\\r')
    s.step('wait:1')
    s.step(READY)


def entry(s, side):
    """The item under side's cursor (or None)."""
    at = s.step(L.peek('ob_at', 2)).data[side]
    cur = s.step(L.peek('obj_cur', 1, side)).data[0]
    e = s.step(L.peek('overlay_text', 1, at + cur)).data[0]
    return None if e >= 0x80 else e


def go(s, side, item):
    """The cursor on `item` of `side` (the lists focused)."""
    if s.step(L.peek('pg_focus')).data[0] == 0:
        press(s, '\\r')
    if s.step(L.peek('obj_side')).data[0] != side:
        press(s, '\\>')
    for _ in range(80):
        if entry(s, side) == item:
            return True
        press(s, '\\v')
    return False


def press(s, k):
    s.step('press:' + k)
    s.step('wait:1')
    s.step(READY)
    if s.step(L.peek('overlay_current')).data == b'\x14':
        # Old page tests accept the default action and its explicit preview.
        for _ in range(3 if s.step(L.peek('om_many')).data[0] else 2):
            s.step('press:\\r')
            s.step('wait:1')
            s.step(READY)


STATE = (('it_place', 76), ('it_pack_lo', 76), ('it_pack_hi', 76), ('it_gnd_lo', 76), ('it_gnd_hi', 76),
         ('it_x', 76), ('it_y', 76), ('cr_b1', 5), ('cr_cx', 6), ('fg_b1', 12), ('fg_gl', 12), ('fg_pl', 12),
         ('fg_use', 1), ('camp_use', 1), ('s_elap', 5), ('s_hour', 5), ('load_used', 8), ('water_untreated', 1),
         ('medical_actions', 30))


def state(s):
    return {name: s.step(L.peek(name, n)).data for name, n in STATE}


def setup(s, prep):
    for name, value, k in prep:
        s.step(L.poke(name, value, k))


def pile_here(s):
    """INSECTS (k 7, pile 6), 20 oz on the ground of this cell."""
    x, y = s.step(L.peek('px', 1, 1)).data[0], s.step(L.peek('py', 1, 1)).data[0]
    return [('fg_x', x, 0), ('fg_y', y, 0), ('fg_gl', 20, 6), ('fg_gh', 0, 6), ('fg_b1', 0, 6)]


def transfer(disk, side, item, key, prep=(), pile=False, expected=None):
    """The page's transfer (`key` on `item` of `side`) and the same line
    typed: (command, page state, typed state, rows after the page, cycles)."""
    with a2test.Session(disk) as s:
        s.step(IDLE)
        setup(s, list(prep) + (pile_here(s) if pile else []))
        open_page(s)
        assert go(s, side, item), (side, item)
        before = state(s)
        r = s.step(f'until:{L["keyboard_wait"]:04X}:20000')
        start = int(re.findall(r'cycles=(\d+)', r.out)[-1])
        s.step('press:' + key)
        s.step('wait:1'); s.step(READY)
        command = expected
        assert command is not None
        # These cases test the named transfer, independently of the useful
        # contextual default (carried tools now open USE).
        target = {'PACK': 0, 'CARRY': 1, 'DROP': 2, 'WEAR': 3,
                  'USE': 4, 'EAT': 5, 'DRINK': 6, 'GET': 7}[command.split()[0]]
        if item == 22 and side == 0:
            target = 7          # source-aware water editor uses GET internally
        for _ in range(8):
            if s.step(L.peek('om_action')).data[0] == target:
                break
            s.step('press:\\v'); s.step('wait:1'); s.step(READY)
        assert s.step(L.peek('om_action')).data[0] == target
        many = s.step(L.peek('om_many')).data[0]
        if many:
            amount = int.from_bytes(s.step(L.peek('om_qty', 2)).data, 'little')
            command += ' ' + str(amount)
        for _ in range(3 if many else 2):
            s.step('press:\\r'); s.step('wait:1'); s.step(READY)
        r = s.step(READY)
        cycles = int(re.findall(r'cycles=(\d+)', r.out)[-1]) - start
        page = state(s)
        screen = rows(s)
        kept = (s.step(L.peek('pg_focus')).data[0], s.step(L.peek('obj_side')).data[0],
                s.step(L.peek('obj_cur', 1, side)).data[0])
        # The header of the view waited (summary_refresh, while the page
        # comes back): drawn once the page is left.
        dirty = s.step(L.peek('ui_dirty')).data[0]
        s.step('press:\\e'); s.step('wait:1'); s.step(IDLE)
        kept += (dirty, s.step(L.peek('ui_dirty')).data[0], s.step(L.peek('obj_keep')).data[0])
    with a2test.Session(disk) as s:
        s.step(IDLE)
        setup(s, list(prep) + (pile_here(s) if pile else []))
        s.step(f'key:{command}\\r')
        s.step('wait:2')
        for _ in range(8):
            r = s.step(f'until:{L["idle"]:04X},{L["keyboard_wait"]:04X}:400000')
            if f'PC={L["idle"]:04X}' in r.out:
                break
            s.step('key: ')
        typed = state(s)
        answer = ' '.join(' '.join(r_[:39].split()) for r_ in rows(s)[20:23]).strip()
    return command, before, page, typed, screen, kept, cycles, answer


def transfers():
    print('Transfers of the page = the typed commands (XL):')
    cases = (
        ('PACK a thing of the wreck', 0, 10, '\\r', (), False),             # ENSOL PAD, 24 oz
        ('PACK refused: weight (+2 oz)', 0, 11, '\\r', (), False),          # GND COVER, 45 oz
        ('DROP from the pack', 1, 9, '\\r', (), False),                     # TENT
        ('H: CARRY from the pack', 1, 2, 'H', (), False),                   # DOWN PARKA
        ('GET WATER of the wreck\'s pile', 0, 22, '\\r', (), False),
        ('PACK ROCK refused: weight (100 oz, 43 left)', 0, 92, '\\r', (), False),
        ('PACK ROCK, the TENT down first', 0, 92, '\\r', (('it_place', 0, 9),), False),
        ('PACK INSECTS: the whole pile, no question', 0, 82, '\\r', (), True),
    )
    expected = ('PACK ENSOL PAD', 'PACK GND COVER', 'DROP TENT',
                'CARRY DOWN PARKA', 'PACK WATER', 'PACK ROCK',
                'PACK ROCK', 'PACK INSECTS')
    times = []
    for (name, side, item, key, prep, pile), wanted in zip(cases, expected):
        command, before, page, typed, screen, kept, cycles, answer = transfer(DISK, side, item, key, prep, pile, wanted)
        same = page == typed
        diff = {k: (page[k].hex(), typed[k].hex()) for k in page if page[k] != typed[k]}
        left = ' '.join(' '.join(r[:39].split()) for r in screen[20:23]).strip()
        check(f'{name}: the page typed {command!r}, the same state as typed; the answer {left!r}; '
              f'the lists focused, the cursor kept; the header drawn at the exit',
              same and left == answer and kept[0] == 1 and kept[1] == side and kept[3:] == (1, 0, 0),
              (diff, left, answer, kept))
        if cycles:
            times.append((name, cycles))
    for name, cycles in times:
        print(f'    {name}: {cycles} cycles ({cycles / 1_023_000:.2f} s) from RETURN to the page')
    return times


def hung():
    print('LOCAL HUNG (16 October 2026):')
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        x, y = s.step(L.peek('px', 1, 1)).data[0], s.step(L.peek('py', 1, 1)).data[0]
        setup(s, [('it_place', 5, 21), ('it_x', x, 21), ('it_y', y, 21)])     # the pack hung here
        open_page(s)
        assert go(s, 0, 21)
        before = state(s)
        s.step('press:\\r'); s.step('wait:2')
        r = s.step(f'until:{L["inventory_key"]:04X},{L["do_command"]:04X}:60000')
        check('RETURN on the hung BACKPACK: nothing typed (LOWER FOOD takes time: the grid\'s)',
              f'PC={L["inventory_key"]:04X}' in r.out and state(s) == before, r.out[-200:])


def layout(disk, xl):
    tag = 'xl' if xl else '140'
    print(f'Layout ({tag}):')
    with a2test.Session(disk) as s:
        s.step(IDLE)
        setup(s, [('it_place', 2, 45), ('it_pack_lo', 3, 45)])  # a remedy in the pack: its uses
        open_page(s)
        press(s, '\\r')
        mem = s.step('peek:0400:1024').data
        screen = text_screen(mem)
        s.step(f'shot:{HERE / f"build/objects_v2_{tag}.png"}')
        (HERE / f'build/objects_v2_{tag}.txt').write_text('\n'.join(screen) + '\n')
        if xl:
            keys = '↵ LIST/ACTIONS ←→↑↓ MOVE'
            check('tabs, post-its (LOCAL, CARRIED, CARRYING, LOAD) from the raw codes, keys',
                  page_frame(screen, 'OBJECTS', keys, 'ESC VIEW') and not postit_errors(mem, 'OBJECTS'),
                  (postit_errors(mem, 'OBJECTS'), screen))
            cells = [raw_cell(mem, 17, c) for c in range(42, 52)]
            used, limit = word(s, 'load_used'), word(s, 'load_limits')
            full = used * 10 // limit
            check(f'the gauge: {full} MouseText blocks then checkerboards ({used} of {limit} oz)',
                  cells == [0x4E] * full + [0x56] * (10 - full), [hex(c) for c in cells])
            check('row 23: LIST focus and MouseText return glyph', screen[23].startswith(' LIST  ') and raw_cell(mem, 23, 7) == 0x4D)
            check('RETURN\'s hint: the return glyph', raw_cell(mem, 21, 41) == 0x4D, hex(raw_cell(mem, 21, 41)))
        else:
            check('tab row of 140 KB, no MouseText code on the page',
                  screen[0].rstrip() == TAB_ROW_140.rstrip() and not any(0x40 <= c < 0x60 for c in mem[:2048]), screen[0])
            used, limit = word(s, 'load_used'), word(s, 'load_limits')
            full = used * 10 // limit
            cells = [raw_cell(mem, 17, c) for c in range(41, 51)]
            check(f'the gauge: {full} inverse spaces then dots', cells == [0x20] * full + [0xAE] * (10 - full),
                  [hex(c) for c in cells])
            check('the keys on row 23', screen[23].startswith('RETURN LIST/ACT  ARROWS MOVE H HANDS')
                  and screen[23].rstrip().endswith('ESC: VIEW'), screen[23])
        o = 1 if xl else 0                                   # (XL: the bars of the post-its)
        check('titles in inverse: LOCAL, CARRIED, CARRYING, LOAD',
              screen[2].startswith(' LOCAL ') and screen[2][41:].startswith(' HANDS ')
              and screen[16].startswith(' CARRYING ') and screen[16][41:].startswith(' LOAD ')
              and all(raw_cell(mem, r, c) < 0x40 for r, c in ((2, 1), (2, 42), (16, 1), (16, 42))), screen[2])
        check('the cursor ">" in column 1 of LOCAL\'s first item, the name in 3, the weight in 18',
              screen[3][1] == '>' and screen[3][3:17].strip() and re.match(r'\d+ OZ', screen[3][18:]), screen[3])
        check('separate HANDS and PACK post-its', screen[2][41:].startswith(' HANDS ')
              and any(' PACK ' in row[41:] for row in screen[3:15]), screen[2:15])
        check('MORE in inverse under both lists (the wreck and the pack)', len(re.findall(r'\d+-\d+/\d+', screen[15])) == 2
              and raw_cell(mem, 15, 31) < 0x40, screen[14])
        check('CARRYING: food and water carried, local, in reach', [r[o:o + 8].strip() for r in screen[17:20]]
              == ['CARRIED', 'LOCAL', 'IN REACH'], screen[17:20])
        check('LOAD: the carried ounces, the walk, the volumes left',
              screen[17][41:79].split()[-2:] == [f'{used}/{limit}', 'OZ'] and 'WALK TIME +28%' in screen[18]
              and 'FREE IN3 WEAR' in screen[18] and 'PACK ' in screen[19] and 'HANDS ' in screen[19], screen[15:20])
        hint = screen[21][41:].strip()
        name = screen[3][3:17].strip()
        check('RETURN and H open item actions without promising a transfer',
              hint.endswith('ITEM ACTIONS')
              and screen[22][41:].strip().endswith('ITEM ACTIONS'), screen[20:22])
        go(s, 1, 45)                                 # the remedy: its uses
        screen = rows(s)
        line = next((r for r in screen[3:15] if r[42] == '>'), '')
        check('a remedy with its uses', re.search(r'\b3 USES', line[41:]), line)



def selection_memory():
    for disk in (DISK,):
        with a2test.Session(disk) as s:
            s.step(IDLE)
            open_page(s)
            at = s.step(L.peek('ob_at', 2)).data[1]
            n = s.step(L.peek('ob_n', 2)).data[1]
            items = s.step(L.peek('overlay_text', n, at)).data
            target = [i for i in items if 0 < i < 76][-2]
            assert go(s, 1, target)
            cursors = s.step(L.peek('obj_cur', 2)).data
            before = rows(s)[3:16]
            press(s, '\\<')
            left_target = s.step(L.peek('overlay_text', s.step(L.peek('ob_n')).data[0])).data
            left_target = [i for i in left_target if i < 128][-2]
            assert go(s, 0, left_target)
            left_cursor = s.step(L.peek('obj_cur')).data
            press(s, '\\>')
            before = rows(s)[3:16]
            s.step('press:\\e'); s.step(IDLE)
            s.step('key:REST 1 MIN\\r'); s.step('wait:1'); s.step(IDLE)
            current = state(s)
            s.step('press:\\^'); s.step(READY)
            assert s.step(L.peek('pg_focus')).data == b'\0'
            assert s.step(L.peek('obj_side')).data == b'\1'
            assert s.step(L.peek('obj_cur')).data == left_cursor
            assert s.step(L.peek('obj_cur', 1, 1)).data == cursors[1:]
            press(s, '\\r')
            assert entry(s, 1) == target and rows(s)[3:16] == before
            assert state(s) == current
            # HELP evicts the module; an earlier carried item disappears.
            s.step('press:\\e'); s.step(IDLE)
            s.step('key:HELP\\r'); s.step('wait:1'); s.step(READY)
            s.step('press:\\e'); s.step(IDLE)
            earlier = next(i for i in items if 0 < i < 76 and i != target)
            s.step(L.poke('it_place', 255, earlier))
            open_page(s)
            press(s, '\\r')
            assert entry(s, 1) == target, 'selection follows the object when indices change'
            s.step('press:\\e'); s.step(IDLE)
            s.step(L.poke('it_place', 255, target))
            open_page(s)
            press(s, '\\r')
            assert entry(s, 1) is not None and entry(s, 1) != target
    print('  XL: both selections, side and scroll survive VIEW/SIM/HELP; stable item identity; removed item fallback: OK')


def volume_gauges():
    cases = ((0, 6000, 0, 2686), (3000, 6000, 1343, 2686),
             (6000, 6000, 2686, 2686), (65000, 6000, 60000, 2686),
             (0, 0, 0, 0), (1000, 6000, 448, 2686))
    for disk, xl in ((DISK, True),):
        with a2test.Session(disk) as s:
            s.step(IDLE); open_page(s); press(s, '\\r')
            for pu, pc, hu, hc in cases:
                for name, offset, value in (('load_used', 4, pu), ('load_limits', 4, pc),
                                            ('load_used', 6, hu), ('load_limits', 6, hc)):
                    s.step(L.poke(name, value & 255, offset))
                    s.step(L.poke(name, value >> 8, offset + 1))
                # Redraw through the keyboard without recomputing these synthetic loads.
                press(s, '\\>')
                mem = s.step('peek:0400:1024').data
                line = text_screen(mem)[19]
                for label, used, capacity in (('PACK', pu, pc), ('HANDS', hu, hc)):
                    col = line.index(label) + len(label) + 1
                    full = min(6, used * 6 // capacity) if capacity else 0
                    filled, empty = (0x4E, 0x56) if xl else (0x20, 0xAE)
                    cells = [raw_cell(mem, 19, c) for c in range(col, col + 6)]
                    assert cells == [filled] * full + [empty] * (6 - full), (disk, label, used, cells)
                    free = line[col + 7:].split()[0]
                    assert int(free) == max(0, capacity - used), (line, label, used, capacity)
                if xl:
                    assert not postit_errors(mem, 'OBJECTS')
    print('  PACK/HANDS gauges: empty, half, full, over capacity, zero capacity, sixths; exact free IN3 on XL: OK')


def scrolling_frames():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        open_page(s)
        press(s, '\\r')
        press(s, '\\>')
        for n in range(22):
            mem = s.step('peek:0400:1024').data
            assert not postit_errors(mem, 'OBJECTS'), (n, postit_errors(mem, 'OBJECTS'))
            screen = text_screen(mem)
            assert not (screen[2][41:].startswith(' PACK ') and ' PACK ' in screen[3][41:])
            press(s, '\\v')
    print('  22 scrolling HANDS/PACK frames, a single PACK title: OK')


def gauge_against_rom():
    print('The gauge against the ROM (build/re_load/results.json):')
    path = HERE / 'build/re_load/results.json'
    if not path.exists():
        print('  SKIP (run tools/re_load_probe.py)')
        if ORIGINAL:
            fails.append('re_load results missing')
        return
    rom = json.loads(path.read_text())
    start = rom['game'][0]['state']
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        used, limit, body = word(s, 'load_used'), word(s, 'load_limits'), word(s, 'body_weight')
        check(f'the limit = the original\'s $4BFA ({start["max"]} oz), the weight left = $4BF8 ({start["left"]})',
              limit == start['max'] == LIMIT and limit - used == start['left'], (limit, used, start))
        # The walk: the page's percent for loads across the range, against the
        # ROM's factor ($4C84) for the same ounces.
        walk = {r['ounces']: r['slower_pct'] for r in rom['walk']}
        loads = (0, 16, 300, 772, 815)
        got = {}
        for oz in loads:
            # (the canteen empty and set down, the weight made by the water
            # of a pile in the pack: load_totals counts provisions' ounces)
            s.step(L.poke('it_place', 255, 22))
            s.step(L.poke('it_place', 0, 64))
            for k in range(1, 76):
                if k not in (22, 64):
                    s.step(L.poke('it_place', 255, k))
            s.step(L.poke('it_place', 2, 21))           # the BACKPACK carried
            s.step(L.poke('it_place', 2, 23))           # NUTS in the pack: oz
            pack = max(0, oz - 64)
            s.step(L.poke('it_pack_lo', pack & 255, 23))
            s.step(L.poke('it_pack_hi', pack >> 8, 23))
            s.step(L.poke('it_oz_lo', 64, 21))          # the backpack's own 64 oz
            s.step(L.poke('cr_b1', 255, 3))
            open_page(s)
            screen = rows(s)
            carried = word(s, 'load_used')
            m = re.search(r'WALK TIME \+(\d+)%', screen[18])
            got[oz] = (carried, int(m[1]) if m else None)
            s.step('press:\\e')
            s.step('wait:1')
            s.step(IDLE)
        ok = all(got[oz][0] == max(oz, 64) for oz in loads[1:]) and all(
            got[oz][1] == int(walk[got[oz][0] // 16 * 16] + 1e-9) for oz in loads if got[oz][0] // 16 * 16 in walk)
        check(f'WALK TIME +n% = INT(the ROM\'s slowing) at {sorted({v[0] for v in got.values()})} oz', ok,
              (got, {k: walk.get(v[0] // 16 * 16) for k, v in got.items()}))
    # The limit: GET ROCK with exactly 100 oz left, then 99 (the ROM's game).
    want = [(r['left_before'], r['state']['rock']) for r in rom['game'][1:] if r['command'] == 'GET ROCK']
    for left, rock in want:
        if left is None:
            continue
        with a2test.Session(DISK) as s:
            s.step(IDLE)
            used = word(s, 'load_used')
            s.step(L.poke('load_limits', (used + left) & 255))
            s.step(L.poke('load_limits', (used + left) >> 8, 1))
            s.step('key:GET ROCK\\r')
            s.step('wait:2')
            s.step(IDLE)
            got = s.step(L.peek('cr_b1', 1, 3)).data[0]
        check(f'GET ROCK with {left} oz left: {"in hand" if rock == 3 else "refused"}, as the ROM',
              (got == 3) == (rock == 3), (got, rock))


def water_get():
    print('GET of a source, no question (16 October 2026):')
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        s.step('key:DRINK WATER 30 OZ\\r'); s.step('wait:1'); s.step(IDLE)
        s.step(L.poke('weather_sky', 2))                        # rain
        used = word(s, 'load_used')
        s.step(L.poke('load_limits', (used + 10) & 255))        # 10 oz of weight left,
        s.step(L.poke('load_limits', (used + 10) >> 8, 1))      # 30 of room in the canteen
        can = s.step(L.peek('it_pack_lo', 1, 22)).data[0]
        s.step('key:GET RAIN\\r'); s.step('wait:2')
        r = s.step(f'until:{L["idle"]:04X},{L["number_idle"]:04X}:60000')
        asked = f'PC={L["idle"]:04X}' not in r.out
        text = ' '.join(' '.join(x[:39].split()) for x in rows(s)[20:23])
        got = s.step(L.peek('it_pack_lo', 1, 22)).data[0]
    check('GET RAIN: no question, the canteen takes what the weight left allows (10 of 30 oz), said',
          not asked and got == can + 10 and 'YOU TOOK 10 OUNCES' in text, (asked, can, got, text))


def main():
    layout(DISK, True)
    selection_memory()
    volume_gauges()
    scrolling_frames()
    transfers()
    hung()
    gauge_against_rom()
    water_get()
    print(f'OBJECTS: {"OK" if not fails else f"{len(fails)} FAIL: {fails}"}')
    sys.exit(bool(fails))


if __name__ == '__main__':
    main()
