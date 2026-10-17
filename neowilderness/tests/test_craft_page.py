#!/usr/bin/env python3
"""The CRAFT page and the second set in the grid (lot 3 step 2,
docs/CRAFT.md 8.6; src/craft.s craft_page, src/pages.s pg_craft,
src/grid.s, src/menu.s member, src/summary.s).

Page: a top page between OBJECTS and HELP; the recipes of MAKE that the
port carries out (A1, A2) in three groups (SHELTERS, WEAPONS AND TOOLS,
PROTECTION), each with its state in MouseText (ALTCHARSET on for the whole
game, docs/MENUS.md 9: a check mark possible, an inverse X missing,
a diamond done) and the minutes MAKE would spend here; on the right the
recipe chosen, each check of craft.s with its state, the effect, the time
and what makes it slower; row 23 says what RETURN types. Checked: the
layout and the glyphs (text and raw codes), one store per changed cell
when the selection moves, the states against the typed MAKE in three
places, the time shown = the game clock's delta after RETURN in five
conditions (day, night, axe or knife in use, low health), RETURN = the
same commands typed (both editions), RETURN on a missing or done recipe
beeps and changes nothing, the focus and the page keys of the cycle.
Pictures: build/craft_page_v2.png (HUT, possible), build/craft_page_v2_missing.png
(IGLOO, missing), and build/craft_page*.txt.

Grid: GET, DROP and USE name the BOW, SPEAR, CLUB, ROCK and SPLINT (GET x
into the hand, as the original's GET), the KILL queue takes the BOW or the
SPEAR before the AXE and nothing when a crafted weapon is in use; every
choice equals the typed commands. The panel's ITEMS hint counts the BOW,
SPEAR, SPLINT and CLUB on the ground here, not the ROCK.

  python3 tests/test_craft_page.py
"""
import math
import re
import sys
from common import HERE, L, DISK, DISK140, a2test, text_screen, result_rows, fp, page_frame
from test_input import IDLE, command
from test_craft import Port
from test_menu_bar import grid_cells, move_to, press, state, RET, DOWN

READY = L.until('keyboard_wait', 60000)
DO_COMMAND = L.until('do_command', 60000)
MAP = 0x7000
RECIPES = ['HUT', 'IGLOO', 'TRENCH', 'CLUB', 'SPEAR', 'BOW', 'AXE', 'SPLINT', 'SUNGLASSES', 'SUNSCREEN']
fails = []


# NeoWildernessXL (docs/MENUS.md 9): the halves begin on row 2, under the
# tabs' line, each group a post-it (a row between them: its last row, 15
# October 2026); the 140 KB edition: from row 1, no row between the groups.
GROUPS = {2: ' SHELTERS', 7: ' WEAPONS AND TOOLS', 14: ' PROTECTION'}
GROUPS140 = {1: ' SHELTERS', 5: ' WEAPONS AND TOOLS', 11: ' PROTECTION'}
ROW = {'HUT': 3, 'IGLOO': 4, 'TRENCH': 5, 'CLUB': 8, 'SPEAR': 9, 'BOW': 10, 'AXE': 11, 'SPLINT': 12,
       'SUNGLASSES': 15, 'SUNSCREEN': 16}
ROW140 = {'HUT': 2, 'IGLOO': 3, 'TRENCH': 4, 'CLUB': 6, 'SPEAR': 7, 'BOW': 8, 'AXE': 9, 'SPLINT': 10,
          'SUNGLASSES': 12, 'SUNSCREEN': 13}
FRAME = str.maketrans('\u258f\u2595\u203e_', '    ')     # the post-its' bars and lines (XL)
CHK, DIA = '\u2713', '\u25c6'   # the check mark and the diamond as text_screen reads them
OK, NO, DONE = 0x44, 0x18, 0x5B          # MouseText check mark, inverse X, MouseText diamond
STATE = {OK: 'possible', NO: 'missing', DONE: 'done'}
ALTCHAR = 0xC01E                         # RDALTCHAR: bit 7 on


def check(name, ok, detail=''):
    print(f'  {name}: {"OK" if ok else "FAIL"}' + (f' {detail}' if not ok and detail else ''))
    if not ok:
        fails.append(name)


def rows(s):
    """The text rows; rows 2-20 without the post-its' frames (XL), so that
    both editions read alike."""
    return [(r.translate(FRAME) if 2 <= k <= 20 else r).rstrip()
            for k, r in enumerate(text_screen(s.step('peek:0400:1024').data))]


def raw(s):
    """24 rows of 80 screen codes (aux even, main odd columns)."""
    mem = s.step('peek:0400:1024').data
    out = []
    for r in range(24):
        o = (r % 8) * 128 + (r // 8) * 40
        out.append(bytes(b for pair in zip(mem[1024 + o:1024 + o + 40], mem[o:o + 40]) for b in pair))
    return out


def altchar(s):
    return s.step(f'peek:{ALTCHAR:04X}').data[0] >> 7


def mbf(x):
    """Python float -> Applesoft 5-byte float."""
    if x == 0:
        return [0] * 5
    e = math.floor(math.log2(abs(x))) + 1
    m = round(abs(x) / 2 ** e * 2 ** 32)
    if m >> 32:
        m >>= 1
        e += 1
    m = m & 0x7FFFFFFF | (0x80000000 if x < 0 else 0)
    return [e + 0x80] + list(m.to_bytes(4, 'big'))


def minutes(text):
    """'2 H 49' or '21 MIN' (the page's times) -> minutes."""
    m = re.search(r'(\d+) H (\d+)|(\d+) MIN', text)
    return int(m[1]) * 60 + int(m[2]) if m[1] else int(m[3])


def woods_cell(s, port):
    """A dry woods cell below the snow line, away from the wreck and the
    goal, with no water in the 5 x 5 cells around (no SWIM in the grid)."""
    forest = s.step('peek:0800:294').data
    grid = s.step(f'peek:{MAP + 64:04X}:9408').data
    snow = s.step(f'peek:{MAP + 11:04X}:1').data[0]
    wx, wy = port.wreck

    def wooded(x, y):
        return forest[(y >> 1) * 7 + (x >> 4)] >> ((x >> 1) & 7) & 1

    for y in range(4, 80):
        for x in range(4, 108):
            if not wooded(x, y) or abs(x - wx) + abs(y - wy) < 3 or (x, y) == port.goal:
                continue
            around = [grid[(y + dy) * 112 + x + dx] for dy in range(-2, 3) for dx in range(-2, 3)]
            if any(c & 0x80 for c in around) or not (grid[y * 112 + x] & 0x7F) < min(snow, 96):
                continue
            return x, y
    raise AssertionError('no woods cell')


def setup(s, where, rope=True):
    """A fresh state (test_craft Port.reset) on a cell: 'woods' (the ROPE
    and the FISHNG GEAR gone unless rope), or 'wreck'."""
    port = Port(s)
    port.poke('nature_frequency', 0)
    cell = woods_cell(s, port) if where == 'woods' else port.wreck
    port.reset(cell)
    if not rope:
        for n in (60, 67):
            port.poke('it_place', 255, n)
    port.poke('wb_key', 0xFF, 5)                 # water_bits: a new position
    command(s, 'V')
    return port


def open_page(s):
    """From the view: UP (STATUS), then RIGHT through OBJECTS and EQUIPMENT: CRAFT."""
    s.step('key:STATUS\\r')
    s.step(READY)
    for _ in range(3):
        s.step('key:\\>')
        s.step('wait:2')
        s.step(READY)
    return rows(s)


def key(s, k):
    s.step(f'key:{k}')
    s.step('wait:2')
    s.step(READY)
    return rows(s)


def is_craft(page, xl=True):
    """The CRAFT page: XL one row lower, its legend on row 21 (docs/MENUS.md 9)."""
    if xl:
        return page[2].startswith(' SHELTERS') and page[21].startswith(f' {CHK} POSSIBLE')
    return page[1].startswith(' SHELTERS') and page[22].startswith(f' {CHK} POSSIBLE')


def verdicts(s):
    """{recipe: 'possible' | 'missing' | 'done'} from the glyphs of column 15."""
    scr = raw(s)
    return {r: STATE.get(scr[row][15], hex(scr[row][15])) for r, row in ROW.items()}


def made(s, recipe):
    """MAKE recipe typed: True when it was made (msg 15 or 28/205)."""
    command(s, f'MAKE {recipe}')
    text = ' '.join(result_rows(rows(s)))
    return 'IT TOOK A WHILE' in text


def formula(recipe, health, light=1, axe=1, knife=1):
    """docs/CRAFT.md 3.1, 4, 5 (the ROM's, measured)."""
    r = math.sqrt(health)
    if recipe in ('HUT', 'IGLOO', 'TRENCH'):
        k = {'TRENCH': 1, 'HUT': 2, 'IGLOO': 3}[recipe]
        return int(4000 * k / ((light + 2) * (axe + 2) * health))
    if recipe == 'CLUB':
        return int(60 / r)
    if recipe in ('SPEAR', 'AXE', 'BOW'):
        t = int(600 / (r * (3 * knife + 1)))
        return int(4 * t / (light + 1)) if recipe == 'BOW' else t
    if recipe == 'SPLINT':
        return int(300 / (r * (light + 1) * (knife + 1)))
    return 30


def page_view(disk, tag):
    """The page on one edition: NeoWildernessXL draws it under the folder
    tabs of the pages (docs/MENUS.md 9: one row lower, the legend on 21, the
    footer of the pages on 22-23, ALTCHARSET on for the whole game); the
    140 KB edition keeps its plain page (rows 1-22, ALTCHARSET on while it
    is shown)."""
    xl = disk == DISK
    d = 1 if xl else 0                   # the rows of the halves: 2.. (XL), 1.. (140 KB)
    legend = 21 if xl else 22
    print(f'The page ({tag}):')
    with a2test.Session(disk) as s:
        s.step(IDLE)
        port = setup(s, 'woods', rope=False)
        health = fp(s.step(L.peek('s_health', 5)).data)
        page = open_page(s)
        scr = raw(s)
        (HERE / f'build/craft_page{tag}.txt').write_text('\n'.join(page) + '\n')
        if xl:
            check('the frame (docs/MENUS.md 9): CRAFT between EQUIPMENT and HELP, R in the letters, its line '
                  'open under it, the footer line', page_frame(text_screen(s.step('peek:0400:1024').data), 'CRAFT'),
                  page[:2] + page[22:])
        else:
            from common import TAB_ROW_140
            check('tab row: CRAFT between EQUIPMENT and HELP, R in the letters', page[0] == TAB_ROW_140, page[0])
        check('ALTCHARSET on (MouseText) on the page', altchar(s) == 1)
        groups, rowmap = (GROUPS, ROW) if xl else (GROUPS140, ROW140)
        check('three groups, headers in column 1', all(page[r][:29].rstrip() == g for r, g in groups.items()),
              [page[r] for r in groups])
        state = {'HUT': OK, 'IGLOO': NO, 'TRENCH': OK, 'CLUB': OK, 'SPEAR': NO, 'BOW': NO, 'AXE': DONE,
                 'SPLINT': OK, 'SUNGLASSES': DONE, 'SUNSCREEN': OK}
        good = []
        for recipe, row in rowmap.items():
            left = page[row][:30]
            glyph = scr[row][15]
            want = '' if glyph == DONE else str(formula(recipe, health))
            shown = '' if glyph == DONE else str(minutes(left[16:]))
            good.append(left[:15] == f'   {recipe:<12}' and glyph == state[recipe] and shown == want
                        and (glyph == DONE or left[16:].rstrip().endswith(('MIN',)) == (int(want) < 60)))
        check('woods without rope: name, state glyph (check mark, inverse X, diamond) and the ROM time of each recipe',
              all(good), '\n'.join(page[1 + d:14 + d]))
        if xl:
            from common import postit_errors
            mem = s.step('peek:0400:1024').data
            check('the post-its (docs/MENUS.md 9.3): SHELTERS, WEAPONS AND TOOLS, PROTECTION, the recipe',
                  not postit_errors(mem, 'CRAFT'), postit_errors(mem, 'CRAFT'))
        else:
            check('the separator: MouseText $5A in column 30, rows 1..21', all(scr[r][30] == 0x5A for r in range(1, 22)))
        check(f'the legend on row {legend}: check mark POSSIBLE, inverse X MISSING, diamond DONE',
              scr[legend][:32] == bytes([0xA0, OK]) + b' POSSIBLE   '.translate(HI) + bytes([NO]) +
              b' MISSING   '.translate(HI) + bytes([DONE]) + b' DONE'.translate(HI), scr[legend][:33])
        if xl:
            check('row 23 on the tab row: pages, recipes, RETURN VIEW, ESC VIEW',
                  scr[23][:3] == b' '.translate(HI)+bytes([0x48,0x55])
                  and 'PAGE ↓ RECIPES ↵ VIEW' in page[23] and page[23].endswith('ESC VIEW'), page[23])
        else:
            check('row 23 on the tab row: arrows (MouseText), RETURN: VIEW, ESC: VIEW',
                  scr[23][:2] == bytes([0x4B, 0x4A]) and page[23][2:].startswith(' CHOOSE   RETURN: VIEW')
                  and page[23].endswith('ESC: VIEW'), page[23])

        def footer(text):
            """Row 23: RETURN's text."""
            if xl:
                return text in page[23] and page[23].endswith('ESC VIEW')
            return page[23][2:].startswith(' CHOOSE   RETURN: ' + text) and page[23].endswith('ESC: VIEW')
        # The focus: DOWN on HUT, the panel, one store per changed cell.
        before = raw(s)
        mark = len(s.out)
        s.step('storewatch:0400:07FF')
        page = key(s, '\\v')
        s.step('unstorewatch')
        after = raw(s)
        stores = [ln for ln in s.out[mark:].splitlines() if ln.startswith('store ')]
        changed = sum(a != b for x, y in zip(before, after) for a, b in zip(x, y))
        check(f'DOWN: the marker on HUT, {changed} cells changed, as many stores',
              page[2 + d].startswith(' > HUT') and s.step(L.peek('cp_focus')).data[0] == 1
              and 0 < len(stores) == changed, (page[2 + d], len(stores), changed))
        scr = raw(s)
        hut = [r[31:] for r in page[2:9]]
        check('HUT summary: effect, ready, native time, available tool and estimated finish',
              hut[1] == '   SHELTER: AIR +15 F, ANIMALS 10X SAFER'
              and hut[2] == '   READY TO MAKE'
              and hut[3] == '   TIME: '+fmt(formula('HUT', health))
              and 'AXE: AUTO USE WHEN MAKING' in hut[4] and 'EST. FINISH:' in hut[5]
              and 'SLOWER:' not in '\n'.join(page), '\n'.join(hut))
        summary = page
        page = key(s, '\\>')
        check('RIGHT shows factors and slower conditions on demand',
              'FACTORS: DAY, AXE ON' in '\n'.join(page) and 'SLOWER: NIGHT' in '\n'.join(page))
        page = key(s, '\\<')
        check('LEFT restores exactly the readable summary', page == summary)
        check('row 23: RETURN: MAKE HUT', footer('MAKE HUT'), page[23])
        s.step(f'shot:{HERE / f"build/craft_page_v2{tag}.png"}')
        (HERE / f'build/craft_page_v2{tag}.txt').write_text('\n'.join(page) + '\n')
        page = key(s, '\\v')
        scr = raw(s)
        s.step(f'shot:{HERE / f"build/craft_page_v2_missing{tag}.png"}')
        check('the panel of IGLOO: MISSING, SNOW with an inverse X, RETURN: NOTHING (MISSING)',
              page[1 + d][31:].startswith(' > IGLOO') and page[1 + d].endswith('MISSING')
              and page[5][31:] == '    X SNOW' and scr[5][35] == NO and footer('NOTHING (MISSING)'),
              '\n'.join(page[1 + d:9 + d] + page[23:]))
        # A missing recipe: RETURN beeps, nothing runs.
        before = state_of(s)
        s.step('key:\\r')
        r = s.step(f'until:{L["do_command"]:04X},{L["keyboard_wait"]:04X}:60000')
        check('RETURN on a missing recipe (IGLOO): no command, the page stays',
              f'PC={L["keyboard_wait"]:04X}' in r.out and rows(s)[3 + d].startswith(' > IGLOO'))
        for _ in range(5):
            page = key(s, '\\v')
        check('the AXE: DONE, YOU HAVE ONE ALREADY (diamond), no time',
              page[rowmap['AXE']].startswith(' > AXE') and page[1 + d].endswith('DONE')
              and page[5][31:] == f'    {DIA} YOU HAVE ONE ALREADY'
              and 'TIME' not in ''.join(page[1 + d:20 + d]), '\n'.join(page[1 + d:9 + d]))
        s.step('key:\\r')
        r = s.step(f'until:{L["do_command"]:04X},{L["keyboard_wait"]:04X}:60000')
        check('RETURN on a done recipe (AXE): no command', f'PC={L["keyboard_wait"]:04X}' in r.out)
        page = key(s, '\\v')
        check('SPLINT shortcut: ready without listing optional missing ingredients',
              page[4][31:] == '   READY TO MAKE' and 'KNIFE: AUTO USE WHEN MAKING' in page[6]
              and page[2].endswith('POSSIBLE') and 'MISSING HERE:' not in '\n'.join(page), '\n'.join(page[2:9]))
        page = key(s, '\\v')
        page = key(s, '\\v')
        check('SUNSCREEN: 30 MIN (ALWAYS), no SLOWER',
              page[5][31:] == '   TIME: 30 MIN' and page[6][31:].startswith('   EST. FINISH: '), '\n'.join(page[1 + d:7 + d]))
        # The page keys of the cycle. XL keeps ALTCHARSET on for the whole
        # game; the 140 KB edition only while the page is shown.
        on = 1 if xl else 0
        for _ in range(s.step(L.peek('cp_focus')).data[0]):     # up to the tab row
            page = key(s, '\\^')                           # (UP there: TOPO)
        page = key(s, '\\<')
        check(f'LEFT on the tab row: EQUIPMENT, ALTCHARSET {"on" if xl else "off"}',
              'HANDS VOLUME:' in page[8] and (page_frame(page, 'EQUIPMENT') or not xl)
              and all(row.ljust(80)[40] == ' ' for row in page[2:20]) and altchar(s) == on, '\n'.join(page[2:20]))
        page = key(s, '\\>')
        check('RIGHT from EQUIPMENT: CRAFT again', is_craft(page, xl) and altchar(s) == 1, page[1 + d])
        page = key(s, '\\>')
        check(f'RIGHT: HELP, ALTCHARSET {"on" if xl else "off"}', not is_craft(page, xl)
              and (page_frame(page, 'HELP') if xl else 'S/O/R/H' not in page[0]) and altchar(s) == on, page[2])
        page = key(s, 'R')
        check('R: CRAFT', is_craft(page, xl), page[1 + d])
        for _ in range(10):
            key(s, '\\v')
        s.step('key:\\v')
        s.step(IDLE)
        check(f'DOWN past SUNSCREEN: the view, nothing changed, ALTCHARSET {"on" if xl else "off"}',
              state_of(s) == before and altchar(s) == on, (altchar(s), diff(state_of(s), before)))
        open_page(s)
        s.step('key:\\e')
        s.step(IDLE)
        check(f'ESC: the view, ALTCHARSET {"on" if xl else "off"}', state_of(s) == before and altchar(s) == on,
              (altchar(s), diff(state_of(s), before)))


HI = bytes((c | 0x80) for c in range(256))


def fmt(m):
    return f'{m // 60} H {m % 60:02d}' if m >= 60 else f'{m} MIN'


def hmax(s):
    return fp(s.step(L.peek('f_hmax', 5)).data)


def state_of(s):
    """The journey's state (test_menu_bar.state without the result rows:
    the page covers them)."""
    return state(s)[0]


def diff(a, b):
    return [k for k, (x, y) in enumerate(zip(a, b)) if x != y]


def agreement():
    """The page's states = the typed MAKE, recipe by recipe, in three places."""
    print('The states against the typed MAKE:')
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        for where, rope in (('woods', False), ('woods', True), ('wreck', True)):
            setup(s, where, rope)
            open_page(s)
            v = verdicts(s)
            s.step('key:\\e')
            s.step(IDLE)
            got = {}
            for recipe in RECIPES:
                setup(s, where, rope)
                got[recipe] = made(s, recipe)
            want = {r: x == 'possible' for r, x in v.items()}
            check(f'{where}{"" if rope else " without rope"}: {sum(want.values())} possible, '
                  f'{list(v.values()).count("done")} done', want == got and set(v.values()) <= set(STATE.values()),
                  (v, got))


def times():
    """The time shown (list and panel) = the clock's delta after RETURN."""
    print('The time shown = the time MAKE spends (game clock):')
    # The stationary scan of T0A/S05 may bring an animal during the time
    # (away from the wreck, whatever nature_frequency), which stops it, as
    # typed: such a draw is replayed from another state of the Lehmer
    # generator (weather_seed) until the time runs to its end.
    cases = [('day', dict(), ('HUT', 'TRENCH', 'CLUB', 'SPLINT', 'SUNSCREEN')),
             ('night', dict(light=0), ('BOW', 'TRENCH', 'SPLINT')),
             ('axe in use', dict(tools=1), ('HUT', 'TRENCH')),
             ('knife in use, night', dict(tools=2, light=0), ('SPEAR', 'BOW', 'SPLINT')),
             ('health 2.5, axe and knife in use', dict(health=2.5, tools=3), ('HUT', 'CLUB', 'SPEAR', 'SPLINT'))]
    with a2test.Session(DISK, timeout=1800) as s:
        s.step(IDLE)
        seed = s.step(L.peek('weather_seed', 4)).data
        for name, cond, recipes in cases:
            for recipe in recipes:
                for retry in range(8):
                    got = make_timed(s, cond, recipe, bytes([seed[0] ^ retry * 29]) + seed[1:])
                    if not got[-1]:
                        break
                listed, panel, line, delta, rom, animal = got
                check(f'{name}: {recipe} shown {fmt(listed)}, panel {line.strip()[6:]}, clock +{delta} min'
                      + (f' ({retry} draws replayed)' if retry else ''),
                      listed == panel == delta == rom and not animal, got)


def finish_page_make(s):
    # Native intermediate messages may pause before resident get_line.
    stop = f'until:{L["get_line"]:04X},{L["keyboard_wait"]:04X}:400000'
    r = s.step(stop)
    while f'PC={L["get_line"]:04X}' not in r.out:
        s.step('key: ')
        r = s.step(stop)
    r = s.step(f'until:{L["idle"]:04X},{L["q_craft_wait"]:04X}:400000')
    if f'PC={L["q_craft_wait"]:04X}' in r.out:
        s.step('key:\\e')
        s.step(IDLE)


def make_timed(s, cond, recipe, seed):
    """The recipe chosen on the page in conditions cond, RETURN: (listed,
    panel minutes, TIME line, clock delta, ROM formula, an animal came)."""
    port = setup(s, 'woods')
    port.poke('weather_seed', seed)
    if 'light' in cond:
        port.poke('light', cond['light'])
    if 'tools' in cond:
        port.poke('care_tools', cond['tools'])
        port.poke('care_tool_x', port.byte('px', 1))
        port.poke('care_tool_y', port.byte('py', 1))
    if 'health' in cond:
        port.poke('s_health', mbf(cond['health']))
    health = fp(s.step(L.peek('s_health', 5)).data)
    open_page(s)
    for _ in range(RECIPES.index(recipe) + 1):
        page = key(s, '\\v')
    listed = minutes(page[ROW[recipe]][16:30])
    line = next((r[31:] for r in page[2:21] if r[31:].startswith('   TIME: ')), '')
    panel = minutes(line) if line else None
    assert raw(s)[ROW[recipe]][15] == OK, (recipe, page[2:11])
    t0 = fp(s.step(L.peek('s_elap', 5)).data)
    s.step('press:\\r')
    s.step(DO_COMMAND)
    finish_page_make(s)
    delta = round((fp(s.step(L.peek('s_elap', 5)).data) - t0) * 60)
    rom = formula(recipe, health, cond.get('light', 1), 1, 1)
    return listed, panel, line, delta, rom, bool(port.byte('fauna_alert'))


def page_equals_keyboard(disk, tag):
    print(f'RETURN on the page = the keyboard ({tag}):')
    picks = [('HUT', 1), ('CLUB', 4), ('SPLINT', 8)]
    with a2test.Session(disk, timeout=900) as s:
        s.step(IDLE)
        setup(s, 'woods')
        typed_in = []
        for recipe, k in picks:
            open_page(s)
            for _ in range(k):
                key(s, '\\v')
            s.step('press:\\r')
            s.step(DO_COMMAND)
            typed_in.append(s.step(L.peek('inbuf', 16)).data.split(b'\0')[0].decode())
            finish_page_make(s)
        page = state(s), craft(s)
    with a2test.Session(disk, timeout=900) as s:
        s.step(IDLE)
        setup(s, 'woods')
        for recipe, _ in picks:
            s.step('key:\\^')                    # STATUS (its journey_left, a
            s.step(READY)                          # cache of the page) as the
            s.step('key:\\e')                    # page's way there
            s.step(IDLE)
            if recipe == 'HUT':
                command(s, 'USE AXE')
            elif recipe == 'SPLINT':
                command(s, 'USE KNIFE')
            command(s, f'MAKE {recipe}')
        typed = state(s), craft(s)
    check('the page prepares the needed tools before MAKE', typed_in == ['USE AXE', 'MAKE CLUB', 'USE KNIFE'], typed_in)
    check('same journey state as typed (clock, body, items, crafted things, messages)', page == typed)


def craft(s):
    return (s.step(L.peek('craft_state', L['craft_state_end'] - L['craft_state'])).data,
            s.step(L.peek('craft_cells', 6)).data, s.step(L.peek('fg_use')).data)


def grid_items(s):
    """Every item of the open list: its rows scrolled through by DOWN."""
    seen = []
    for _ in range(20):
        for c in [c.strip(' \u2595') for r in rows(s)[20:24] for c in (r[41:53], r[53:65], r[65:79]) if c.strip()]:
            if c not in seen:
                seen.append(c)
        press(s, DOWN)
    return seen


def choose(s, verb, item=None):
    """The grid: verb, then item (None: a list of one entry, chosen at
    once); returns the steps typed (inbuf)."""
    press(s, RET)
    move_to(s, verb)
    if item:
        press(s, RET)
        move_to(s, item)
    s.step(f'press:{RET}')
    steps = []
    while True:
        s.step(DO_COMMAND)
        steps.append(s.step(L.peek('inbuf', 20)).data.split(b'\0')[0].decode())
        if not s.step(L.peek('mq_n')).data[0]:
            break
        s.step(L.until('get_line', 400000))
    s.step(IDLE)
    press(s, '\\e')
    return steps


def game_here(s, port):
    port.poke('animal_kind', 0)                 # (the KILL of game, not an animal's)
    x, y = port.byte('px', 1), port.byte('py', 1)
    port.poke('fg_b2', 0, 4)
    port.poke('resource_seen', port.byte('resource_seen') | 1)
    port.poke('fg_x', x)
    port.poke('fg_y', y)


def grid(disk, tag):
    print(f'The grid and the second set ({tag}):')
    with a2test.Session(disk, timeout=900) as s:
        s.step(IDLE)
        port = setup(s, 'woods')
        command(s, 'DROP TENT')         # (lot 14: room in the load for the BOW)
        command(s, 'MAKE BOW')
        command(s, 'MAKE SPEAR')
        press(s, RET)
        move_to(s, 'GET')
        press(s, RET)
        items = grid_items(s)
        press(s, '\\e', '\\e')
        check('GET: the BOW, the SPEAR and the ROCK on the ground here', {'BOW', 'SPEAR', 'ROCK'} <= set(items), items)
        steps = [choose(s, 'GET', 'BOW')]
        check('GET BOW: typed GET BOW, in hand', steps[-1] == ['GET BOW'] and port.byte('cr_b1') == 3, steps)
        press(s, RET)
        move_to(s, 'USE')
        press(s, RET)
        items = grid_items(s)
        press(s, '\\e', '\\e')
        check('USE: the BOW, the SPEAR, the ROCK', {'BOW', 'SPEAR', 'ROCK'} <= set(items), items)
        press(s, RET)
        move_to(s, 'DROP')
        press(s, RET)
        items = grid_items(s)
        press(s, '\\e', '\\e')
        check('DROP: the BOW (in hand), not the SPEAR nor the ROCK (on the ground)',
              'BOW' in items and 'SPEAR' not in items and 'ROCK' not in items, items)
        game_here(s, port)
        command(s, 'V')
        steps.append(choose(s, 'KILL'))
        check('KILL GAME, nothing in use: USE BOW first (before the AXE), then KILL GAME',
              steps[-1] == ['USE BOW', 'KILL GAME'], steps[-1])
        steps.append(choose(s, 'USE', 'SPEAR'))
        game_here(s, port)
        command(s, 'V')
        steps.append(choose(s, 'KILL'))
        check('KILL GAME with the SPEAR in use: KILL GAME alone', steps[-1] == ['KILL GAME'], steps[-1])
        steps.append(choose(s, 'DROP', 'BOW'))
        final = state(s), craft(s)
        flat = [t for st in steps for t in st]
    with a2test.Session(disk, timeout=900) as s:
        s.step(IDLE)
        port = setup(s, 'woods')
        command(s, 'DROP TENT')
        command(s, 'MAKE BOW')
        command(s, 'MAKE SPEAR')
        for k, text in enumerate(flat):
            if text.startswith('KILL') or text == 'USE BOW':
                if text == 'USE BOW' or flat[k - 1] != 'USE BOW':
                    game_here(s, port)
                    command(s, 'V')
            command(s, text)
        typed = state(s), craft(s)
    check(f'the grid = the same commands typed ({", ".join(flat)})', final == typed)


def hint():
    print('The panel:')
    sys.path.insert(0, str(HERE / 'tests'))
    from test_interface import panels
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        port = setup(s, 'woods')
        port.poke('load_limits', [2000 & 255, 2000 >> 8])   # (lot 14: room for the BOW in hand)
        command(s, 'MAKE BOW')

        def panel(text):
            command(s, text)
            for name, v in (('thermal_mode', 0), ('ui_pending', 0), ('ui_dirty', 1)):
                port.poke(name, v)
            for field in (3, 5):
                port.poke('ui_previous', 0, field)
            command(s, 'VIEW')
            return panels(s.step('peek:2000:8192').data)[1]

        check('the BOW on the ground here: ITEMS: INV', panel('V') == 'ITEMS: INV', panel('V'))
        got = panel('GET BOW')
        check('the BOW in hand, the ROCK on the ground: no ITEMS hint', got != 'ITEMS: INV', got)
        got = panel('DROP BOW')
        check('dropped again: ITEMS: INV', got == 'ITEMS: INV', got)


def main():
    page_view(DISK, '')
    agreement()
    times()
    page_equals_keyboard(DISK, 'XL')
    grid(DISK, 'XL')
    hint()
    if fails:
        print(f'CRAFT page: {len(fails)} FAIL: {fails}')
        sys.exit(1)
    print('CRAFT page and the second set in the grid: OK')


if __name__ == '__main__':
    main()
