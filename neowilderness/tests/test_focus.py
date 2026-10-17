#!/usr/bin/env python3
"""Focus levels of the top pages (src/pages.s page_keys, src/inventory.s).

The tab row holds the focus on arrival; DOWN goes down a level (OBJECTS'
lists, LEFT/RIGHT their sides; the cursor of OPTIONS and MENU, MEDICAL's
active conditions), UP comes back up, DOWN below the lowest level returns to the
view; UP on the tab row opens TOPO (15 October 2026: the maps' storey, also
from CRAFT's own key loop), where UP returns to the view. Each focus move redraws its page differentially: one store per
changed cell. MEDICAL's focus shows the treatment gestures of the condition
on row 23 (LEFT/RIGHT choose one, RETURN types it; src/care.s); OPTIONS'
line F types IGNORE FOOD or GET FOOD; the grid's CARE opens MEDICAL on the
first active condition."""
import re
import sys
from common import MENU_STORES, L, DISK, DISK140, a2test, text_screen, text_writes, text_changes, page_frame

IDLE = L.until('idle', 20000)
READY = L.until('keyboard_wait', 20000)
SHOW = '-v' in sys.argv


def inverse(mem, row):
    """The inverse columns of a row of the 80-column page (bytes below $80
    but MouseText, $40-$5F: ALTCHARSET is on, docs/MENUS.md 9)."""
    o = (row % 8) * 128 + (row // 8) * 40
    cells = [b for pair in zip(mem[1024 + o:1024 + o + 40], mem[o:o + 40]) for b in pair]
    return [c for c, b in enumerate(cells) if b < 0x80 and not 0x40 <= b < 0x60]


def raw_cell(mem, row, col):
    """The screen code of a cell of the 80-column page."""
    o = (row % 8) * 128 + (row // 8) * 40
    return (mem[1024 + o + col // 2] if col % 2 == 0 else mem[o + col // 2])


def walk():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        options = s.step(L.peek('game_options')).data

        def key(k, redraw=True):
            """One key that redraws its page (page_top): one store per changed
            cell; the screen after it."""
            before = s.step('peek:0400:1024').data
            s.step('press:' + k)
            s.step(L.until('page_top', 20000) if redraw else 'wait:2')
            profile = s.step(f'pcprof:{L["keyboard_wait"]:04X}:20000')
            after = s.step('peek:0400:1024').data
            pcs = {int(a, 16): int(c) for a, c in
                   re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', profile.out, re.M)}
            writes, changes = text_writes(pcs, MENU_STORES), text_changes(before, after)
            rows = text_screen(after)
            if SHOW:
                print(f'--- {k}: {writes} stores, {changes} changed cells')
                print('\n'.join(r.rstrip() for r in rows))
            return rows, writes, changes

        def focus():
            return s.step(L.peek('pg_focus')).data[0]

        def view():
            """True when the view's command line comes before a page's key loop."""
            s.step('wait:2')
            out = s.step(f'until:{L["keyboard_wait"]:04X},{L["idle"]:04X}:20000').out
            return f'PC={L["idle"]:04X}' in out

        # OBJECTS (16 October 2026): the tab row, then the lists: the cursor
        # '>' on LOCAL's first item, RIGHT to CARRIED (its first item under
        # HANDS), what RETURN and H type on rows 20-21, UP back to the tabs.
        s.step('key:\\^'); s.step(READY)
        assert focus() == 0
        rows, _, _ = key('\\>')
        keys = '\u21b5 LIST/ACT \u2190\u2192\u2191\u2193 MOVE  H HANDS'
        assert page_frame(rows, 'OBJECTS', keys, 'ESC VIEW'), rows
        assert not any('>' in r[1:3] or '>' in r[42:44] for r in rows[3:14]) and not rows[21][41:].strip(), rows
        rows, writes, changes = key('\\r')
        assert focus() == 1 and rows[3][1:3] == '> ' and writes == changes, (rows[3], writes, changes)
        name = rows[3][3:17].strip()
        assert rows[21][41:].rstrip() == f'\u21b5 PACK {name}' and rows[22][41:].rstrip() == f'H CARRY {name}', rows[20:22]
        rows, writes, changes = key('\\>')
        assert rows[3][1] == ' ' and rows[3][42] == '>' and writes == changes, (rows[3:5], writes, changes)
        assert s.step(L.peek('obj_side')).data[0] == 1 and rows[21][41:].startswith('\u21b5 DROP '), rows[21]
        rows, writes, changes = key('\\<')
        assert rows[3][1] == '>' and writes == changes
        rows, writes, changes = key('\\^')               # back to the tab row
        assert focus() == 0 and rows[3][1] == ' ' and not rows[21][41:].strip() and writes == changes, rows[21]
        s.step('press:\\e')
        assert view(), 'ESC returns to the view'

        # OPTIONS: select STATUS explicitly; UP remembers OBJECTS.
        s.step('key:STATUS'); s.step('press:\\r'); s.step(READY)
        for _ in range(4):
            key('\\>')
        rows, _, _ = key('\\v')
        # XL (docs/MENUS.md 9.3): one post-it, a line an option, rows 3-6,
        # the focused option's sentence on row 8
        assert focus() == 1 and rows[3].startswith('\u258f >C  WILDLIFE'), rows[3]
        assert rows[8].startswith('\u258f HOW OFTEN ANIMALS APPEAR'), rows[8]
        assert page_frame(rows, 'OPTIONS', '\u2191\u2193 CHOOSE  \u21b5 SELECT', 'ESC VIEW'), rows[23]
        rows, writes, changes = key('\\v')
        assert rows[3].startswith('\u258f  C') and rows[4].startswith('\u258f >A  PLAYER ON TOPO'), rows[3:7]
        assert rows[8].startswith('\u258f YOUR POSITION ON THE TOPO SHEET.'), rows[8]
        assert writes == changes, (writes, changes)      # differential: the marker, the inverse, the sentence
        rows, writes, changes = key('\\r')
        assert s.step(L.peek('game_options')).data[0] & 0x80, 'RETURN on A turns the player on TOPO on'
        assert focus() == 2 and rows[4].startswith('\u258f >A') and rows[4][31:34] == '[\u2713]' and writes == changes, rows[4]
        key('\\^')
        rows, writes, changes = key('\\^')
        assert focus() == 0 and not any('>' in r[:3] for r in rows[3:13]) and writes == changes, rows[3:13]
        # MENU: down to Q, then ESC (nothing typed)
        rows, _, _ = key('\\>')
        assert rows[2].startswith(' RANGERS \u005f') and rows[6].startswith(' SAVE / RESTORE \u005f') and focus() == 0, rows[2]
        for _ in range(3):
            rows, writes, changes = key('\\v')
            assert writes == changes
        assert focus() == 3 and rows[11].startswith('\u258f >Q  QUIT'), rows[3:12]
        s.step('press:\\e')
        assert view(), 'ESC returns to the view'
        rows = text_screen(s.step('peek:0400:1024').data)
        assert not any('UNSAVED' in r for r in rows), rows

        # STATUS has no level: DOWN leaves; MENU's cursor below Q leaves too
        s.step('key:STATUS'); s.step('press:\\r'); s.step(READY)
        rows = text_screen(s.step('peek:0400:1024').data)
        assert page_frame(rows, 'STATUS', '\u2191 TOPO', 'ESC/\u2193 VIEW'), rows[23]
        s.step('press:\\v')
        assert view()
        s.step('key:\\^'); s.step(READY)
        key('\\<')
        key('\\<')
        for _ in range(3):
            key('\\v')
        s.step('press:\\v')
        assert view(), 'DOWN below the last line of MENU returns to the view'

        # UP on the tab row: TOPO, the maps' storey; UP there: the view.
        # STATUS (page_keys), then CRAFT (its own key loop, src/craft.s).
        view_page = s.step('peek:2000:8192').data
        for turns in (0, 3):
            s.step('key:STATUS'); s.step('press:\\r'); s.step(READY)
            for _ in range(turns):
                s.step('key:\\>'); s.step('wait:2'); s.step(READY)
            assert focus() == 0 or turns
            s.step('key:\\^')
            s.step(L.until('graphical_topo_key', 40000))
            assert s.step('peek:C01F:1').data[0] >= 0x80 and s.step('peek:C01A:1').data[0] < 0x80, \
                'UP on the tab row: TOPO, DHGR mixed'
            legend = text_screen(s.step('peek:0400:1024').data)[20]
            assert legend.startswith('TOPO, NORTH UP'), legend
            s.step('press:\\^')
            assert view(), 'UP on TOPO returns to the view'
            assert s.step('peek:2000:8192').data == view_page, 'the view copied back'
        s.step(L.poke('game_options', options[0]))
    print('  focus: tab row, OBJECTS lists and sides, OPTIONS/MENU cursor, RETURN; one store per changed cell;'
          ' UP on the tab row (STATUS, CRAFT): TOPO: OK')


def inventory_pages():
    """OBJECTS (16 October 2026): a transfer typed by the page (RETURN on a
    CARRIED item: DROP x, through do_command) comes back to the page, the
    focus on the lists, the cursor on the same entry (the next item came
    under it), the game's answer kept in rows 20-22, columns 0-38."""
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        s.step('key:INVENTORY\\r'); s.step('wait:1'); s.step(READY)
        for k in ('\\r', '\\>', '\\v', '\\v', '\\v'):   # the lists, CARRIED, down to PACK's first
            s.step('press:' + k); s.step('wait:1'); s.step(READY)
        rows = text_screen(s.step('peek:0400:1024').data)
        name = rows[8][44:58].strip()
        cur = s.step(L.peek('obj_cur', 1, 1)).data[0]
        s.step('press:\\r'); s.step('wait:2')
        from test_object_actions import confirm
        s.step(READY)
        confirm(s)
        s.step(READY)
        rows = text_screen(s.step('peek:0400:1024').data)
        assert focus_of(s) == 1 and s.step(L.peek('obj_cur', 1, 1)).data[0] == cur and rows[8][42] == '>' \
            and rows[8][44:58].strip() != name, rows[3:10]
        assert rows[20][:39].strip() == f'GROUND: {name}' and name in '\n'.join(r[:40] for r in rows[3:14]), \
            (name, rows[21], rows[3:14])
        assert s.step(L.peek('mq_n')).data[0] == 0, 'the queue done'
    print('  OBJECTS: RETURN types DROP x, the page again with its answer, the cursor kept: OK')


def focus_of(s):
    return s.step(L.peek('pg_focus')).data[0]


def medical():
    """MEDICAL's care: the focus on the active conditions (the name in
    inverse), their gestures on row 23 (the chosen one in inverse), RETURN
    types it; CUT BODY without a blade types USE KNIFE first and queues the
    gesture; OPTIONS' line F; CARE from the grid."""
    from test_menu_bar import press, move_to, RET
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        for k in (0, 7):                            # SEVERE CUTS, POISON BITE
            s.step(L.poke('injury_active', 1, k))

        def key(k):
            before = s.step('peek:0400:1024').data
            s.step('press:' + k)
            s.step(L.until('page_top', 20000))
            profile = s.step(f'pcprof:{L["keyboard_wait"]:04X}:40000')
            after = s.step('peek:0400:1024').data
            pcs = {int(a, 16): int(c) for a, c in
                   re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', profile.out, re.M)}
            return text_screen(after), text_writes(pcs, MENU_STORES), text_changes(before, after), after

        s.step('key:\\^'); s.step(READY)
        rows = text_screen(s.step('peek:0400:1024').data)
        assert page_frame(rows, 'STATUS', '\u2191 TOPO', 'ESC VIEW'), rows
        rows, writes, changes, mem = key('\\v')
        # STATUS's MEDICAL rows (docs/MENUS.md 9, 15 October 2026): SEVERE CUTS
        # on row 16 (column 1 in its post-it, XL), POISON BITE on row 18 from
        # column 27; the inverse X of the ACTIVE ones (columns 23 and 50).
        assert raw_cell(mem, 16, 23) == raw_cell(mem, 18, 50) == 0x18, 'ACTIVE: an inverse X'
        assert s.step(L.peek('pg_focus')).data[0] == 1 and inverse(mem, 16) == list(range(1, 12)) + [23], inverse(mem, 16)
        assert rows[23].startswith(' \u2190\u2192 STOP BLEEDING  USE PRESSURE') and inverse(mem, 23) == list(range(4, 17)) \
            and rows[23][70:].rstrip() == 'ESC VIEW' and '30 MIN; NO ITEM NEEDED' in rows[22], rows[22:]
        assert writes == changes, (writes, changes)
        rows, writes, changes, mem = key('\\>')
        assert inverse(mem, 23) == list(range(19, 31)) and writes == changes, (inverse(mem, 23), writes, changes)
        rows, writes, changes, mem = key('\\v')            # POISON BITE: three gestures, the first
        assert inverse(mem, 16) == [23] and inverse(mem, 18) == list(range(27, 38)) + [50] and rows[23].startswith(
            ' \u2190\u2192 USE SNAKEBT KIT  CUT BODY  SUCK VENOM') and inverse(mem, 23) == list(range(4, 19)), rows[23]
        assert writes == changes, (writes, changes)
        rows, writes, changes, mem = key('\\<')            # LEFT wraps: SUCK VENOM
        assert inverse(mem, 23) == list(range(31, 41)), inverse(mem, 23)
        rows, _, _, mem = key('\\<')                       # CUT BODY: no blade in use
        s.step('press:\\r')
        s.step(L.until('do_command', 40000))
        assert s.step(L.peek('inbuf', 20)).data.startswith(b'USE KNIFE\0') and \
            [s.step(L.peek(n)).data[0] for n in ('mq_n', 'mq_i')] == [2, 1], 'USE KNIFE, then CUT BODY queued'
        s.step(L.until('get_line', 400000))
        s.step(L.until('do_command', 40000))
        assert s.step(L.peek('inbuf', 20)).data.startswith(b'CUT BODY\0'), s.step(L.peek('inbuf', 20)).data
        s.step(IDLE)
        assert s.step(L.peek('care_tools')).data[0] & 2 and s.step(L.peek('mq_n')).data[0] == 0
        # OPTIONS' line F: IGNORE FOOD typed, then GET FOOD.
        for want in (1, 0):
            s.step('key:STATUS'); s.step('press:\\r'); s.step(READY)
            for _ in range(3):
                key('\\<')                         # STATUS, EQUIPMENT, MENU, OPTIONS
            rows, _, _, _ = key('\\v')
            assert rows[2].startswith(' OPTIONS ') and rows[6].startswith('\u258f  F  FOOD SOURCES ON THE WAY') and \
                rows[6][31:34] == ('[\u2713]' if want else '[ ]'), rows[2:9]
            for _ in range(3):
                key('\\v')
            s.step('press:\\r')
            s.step(L.until('do_command', 40000))
            line = s.step(L.peek('inbuf', 20)).data.split(b'\0')[0]
            assert line == (b'IGNORE FOOD' if want else b'GET FOOD'), line
            s.step(f'until:{L["idle"]:04X},{L["keyboard_wait"]:04X}:400000')
            s.step('key: '); s.step('wait:1'); s.step(f'until:{L["idle"]:04X}:400000')
            assert s.step(L.peek('fg_ignore')).data[0] == want
        # CARE from the grid: STATUS, the focus on the first active condition.
        s.step(L.poke('injury_active', 0, 0))
        s.step('key:V\\r'); s.step('wait:1'); s.step(IDLE)
        press(s, RET)
        move_to(s, 'CARE')
        s.step(f'press:{RET}')
        s.step(L.until('page_top', 40000)); s.step(READY)
        rows = text_screen(s.step('peek:0400:1024').data)
        assert s.step(L.peek('pg_focus')).data[0] == 1 and rows[23].startswith(' \u2190\u2192 USE SNAKEBT KIT'), rows[23]
        s.step('press:\\e')
    print('  STATUS care: the focus on the active conditions, their gestures (LEFT/RIGHT), RETURN types one '
          '(CUT BODY: USE KNIFE first, queued); OPTIONS line F; CARE from the grid: OK')


def remembered_pages():
    from test_input import command, snapshot
    for disk in (DISK,):
        with a2test.Session(disk) as s:
            s.step(IDLE)
            s.step('press:\\^'); s.step(READY)
            assert s.step(L.peek('pg_cur')).data == b'\0'
            s.step('press:\\e'); s.step(IDLE)
            for page, keys in ((0, ()), (1, ('O',)), (2, ('R',)),
                               (3, ('H',)), (4, ('\\<','\\<','\\<')), (5, ('\\<','\\<')), (6, ('\\<',))):
                command_text = 'STATUS'
                s.step('key:'+command_text); s.step('press:\\r'); s.step(READY)
                for key in keys:
                    s.step('press:'+key); s.step('wait:2'); s.step(READY)
                assert s.step(L.peek('pg_cur')).data == bytes((page,)), (disk,page)
                if page == 1:
                    before = snapshot(s)
                    s.step('press:\\v'); s.step(IDLE)
                    s.step('press:\\^'); s.step(READY)
                    assert s.step(L.peek('pg_cur')).data == b'\1'
                    assert s.step(L.peek('pg_focus')).data == b'\0'
                    assert snapshot(s) == before
                s.step('press:\\e'); s.step(IDLE)
                command(s, 'REST 1 MIN')      # SIM overwrites the page module
                before = snapshot(s)
                view = s.step('peek:2000:8192').data
                s.step('press:\\^'); s.step(READY)
                assert s.step(L.peek('pg_cur')).data == bytes((page,)), (disk,page,'forgotten')
                assert snapshot(s) == before
                s.step('press:\\e'); s.step(IDLE)
                assert s.step('peek:2000:8192').data == view
            s.step('key:STATUS'); s.step('press:\\r'); s.step(READY)
            assert s.step(L.peek('pg_cur')).data == b'\0', 'typed STATUS is explicit'
    print('  XL: UP reopens each of the seven last top pages after SIM; typed STATUS explicit; state and view preserved')


if __name__ == '__main__':
    remembered_pages()
    walk()
    inventory_pages()
    medical()
    print('Focus levels: OK')
