#!/usr/bin/env python3
"""Completed-page reveals, clean redraw curtains and differential menus."""
import re
import tempfile
from pathlib import Path
import struct
import zlib
from common import MENU_SKIP, MENU_STORES, HERE, L, DISK, DISK140, a2test, hgr_rows, text_screen, text_writes, text_changes, map_rows, is_status
from test_thermal import call

ACTUAL = a2test.labels(HERE / 'build/wild.lbl')
IDLE = L.until('idle', 20000)
READY = L.until('keyboard_wait', 20000)


def picture(session, path):
    session.step(f'shot:{path}')
    # a2shot emits RGB PNGs with filter 0; inspect the visible HGR area
    # without image-library dependencies or relying on RAM mode flags.
    png = path.read_bytes()
    pos = 8
    compressed = bytearray()
    width = height = 0
    while pos < len(png):
        size = struct.unpack_from('>I', png, pos)[0]
        kind = png[pos + 4:pos + 8]
        data = png[pos + 8:pos + 8 + size]
        if kind == b'IHDR':
            width, height = struct.unpack_from('>II', data)
            assert data[8:] == bytes((8, 2, 0, 0, 0))
        elif kind == b'IDAT':
            compressed.extend(data)
        pos += size + 12
    assert (width, height) == (560, 384)
    raw = zlib.decompress(compressed)
    stride = width * 3 + 1
    assert all(raw[y * stride] == 0 for y in range(height))
    return b''.join(raw[y * stride + 1:(y + 1) * stride] for y in range(320))


def curtain(pixels):
    """The curtain of a long action on NeoWildernessXL (docs/MENUS.md 9): black
    but for the hourglass (MouseText) of text row 9, column 39 (dots 273-279
    of scanlines 144-159), which is lit."""
    width = 560 * 3
    cell = [(y, x) for y in range(144, 160) for x in range(273 * 3, 280 * 3)]
    inside = set(cell)
    lit = any(pixels[y * width + x] for y, x in cell)
    rest = any(v for i, v in enumerate(pixels) if (i // width, i % width) not in inside)
    return lit and not rest


def state(session):
    return [session.step(L.peek(name, count)).data for name, count in
            (('px', 6), ('s_hour', 5), ('s_health', 5), ('it_place', 76))]


def reveal():
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(DISK) as s:
        path = Path(tmp) / 'screen.png'
        # NEOWILD.SYSTEM has printed the introduction when it claims the
        # auxiliary memory, before preloading the modules.
        s.step(L.until('loader_claimed', 20000))
        s.step('wait:2')
        introduction = picture(s, path)
        rows = text_screen(s.step('peek:0400:1024').data)[:22]
        assert rows[0].strip() == 'NEOWILDERNESS' and rows[2].strip() == 'APPLE //E //C 128K - PRODOS - DHGR'
        assert any('YOU SURVIVED A PLANE CRASH' in row for row in rows)
        assert any('LOADING...' in row for row in rows)
        # Lot 7: the start menu follows the trunk; after the choice the
        # introduction comes back with the journey and stays up while the
        # region pack loads and the first view is computed.
        for step in MENU_SKIP[:1]:
            s.step(step)
        menu = text_screen(s.step('peek:0400:1024').data)
        assert 'CHOOSE A JOURNEY' in menu[0], menu
        s.step(MENU_SKIP[1])
        s.step(L.until('loader_pack', 2000))
        s.step('wait:2')
        introduction = picture(s, path)
        rows = text_screen(s.step('peek:0400:1024').data)[:22]
        assert rows[0].strip() == 'NEOWILDERNESS' and any('YOU SURVIVED A PLANE CRASH' in row for row in rows)
        assert any(row.startswith('SIERRA NEVADA, LEVEL 4') for row in rows), rows
        assert any('LOADING...' in row for row in rows)
        s.step(L.until('game_start', 20000))
        s.step('wait:2')
        assert picture(s, path) == introduction, 'the ProDOS preload must preserve the introduction'
        s.step(L.until('render_column', 20000))
        s.step('wait:2')
        assert picture(s, path) == introduction, 'keep the explanation during initialization and initial HGR rendering'
        s.step(f'tracepc:{L["render_column_done"]:04X}:20:20000')
        assert picture(s, path) == introduction, 'keep the explanation until the whole landscape is ready'
        s.step(IDLE)
        s.step('wait:2')
        original = s.step('peek:2000:8192').data
        initial = state(s)
        landscape = picture(s, path)
        s.step('key:STATUS'); s.step('press:\\r')
        s.step(ACTUAL.until('status_key', 20000))
        assert picture(s, path) == landscape, 'prepare STATUS behind the intact landscape'
        s.step(READY)
        s.step('wait:2')
        assert picture(s, path) != landscape
        screen = text_screen(s.step('peek:0400:1024').data)
        assert is_status(screen)
        s.step('key:\\e'); s.step(IDLE)
        s.step('wait:2')
        assert picture(s, path) == landscape
        assert state(s) == initial
        s.step('key:TOPO'); s.step('press:\\r'); s.step(READY)
        s.step('press:\\e')
        # Lot 4: the snapshot of the view is copied back; no raycast at all.
        profile = s.step(f'pcprof:{L["idle"]:04X}:20000')
        pcs = {int(a, 16): int(c) for a, c in re.findall(r'^pc ([0-9A-F]{4}) (\\d+)$', profile.out, re.M)}
        assert not pcs.get(L['render_column'], 0), 'TOPO return must not redraw the view'
        s.step('wait:2')
        assert picture(s, path) == landscape
        assert s.step('peek:2000:8192').data == original
        assert state(s) == initial
        s.step('key:VIEW'); s.step('press:\\r')
        s.step(L.until('render_column', 20000))
        s.step('wait:2')
        assert curtain(picture(s, path)), 'explicit VIEW must hide its full redraw'
        s.step(IDLE)
        s.step('wait:2')
        assert picture(s, path) == landscape
    print('  persistent loading introduction, prepared STATUS, clean text return, TOPO return without raycast, VIEW: incomplete frames hidden; view/state preserved')


def simulation_landscape():
    """SIM preserves the last complete frame; only drawing needs a curtain."""
    for disk in (DISK,):
        with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk) as s:
            path = Path(tmp) / 'simulation.png'
            s.step(IDLE)
            s.step('wait:2')
            landscape = picture(s, path)
            # Stale text above the command window must stay invisible while
            # SIM loads. Neither the live rows nor the cursor may be touched.
            for row in range(20):
                offset = (row % 8) * 128 + (row // 8) * 40
                for col in range(40):
                    s.step(f'poke:{0x400+offset+col:04X}:D8')
            before = s.step('peek:0400:1024').data
            cursor = s.step('peek:0024:2').data
            banks = s.step('peek:2000:8192').data
            for step in call(['thermal']):
                s.step(step)
            s.step(L.until('overlay_before_transfer', 20000))
            assert picture(s, path) == landscape, disk
            assert s.step('peek:0400:1024').data == before
            assert s.step('peek:0024:2').data == cursor
            assert s.step('peek:2000:8192').data == banks
        # Real keyboard path, including a page that evicts SIM first.
        for command, prepare, result in (
                ('REST 1 H', 'module_rest_prepare', 'YOU RESTED 1 HOUR.'),
                ('WAIT 10 MIN', 'module_rest_prepare', 'YOU WAITED 10 MINUTES.'),
                ('EAT CHEESE 4 OZ', 'module_meal_prepare', 'YOU ATE')):
            with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk) as s:
                path = Path(tmp) / 'rest.png'
                s.step(IDLE)
                s.step('key:STATUS'); s.step('press:\\r'); s.step(READY)
                s.step('key:\\e'); s.step(IDLE)
                s.step('wait:2')
                landscape = picture(s, path)
                s.step('key:' + command); s.step('press:\\r')
                s.step(L.until(prepare, 20000))
                assert picture(s, path) == landscape, disk
                s.step(L.until('render_column', 20000))
                s.step('wait:2')
                pixels = picture(s, path)
                assert curtain(pixels) if disk == DISK else not any(pixels)
                s.step(IDLE)
                s.step('wait:2')
                assert not curtain(picture(s, path))
                assert result in '\n'.join(text_screen(s.step('peek:0400:1024').data))
    print('  both editions: SIM keeps landscape, text, cursor and DHGR banks; REST/WAIT/EAT after STATUS hide only their redraw')


def differential_pages():
    # The pages of STATUS (src/pages.s) write their rows top to bottom
    # without clearing the screen: OBJECTS' cursor and sides (16 October
    # 2026) and HELP's own letter H (module_help) redraw them, the arrows turn the top pages
    # (STATUS, OBJECTS, EQUIPMENT, CRAFT, HELP, OPTIONS, MENU: page_top) and the
    # OPTIONS letters A and P redraw their page, one store per changed cell;
    # so do the focus moves (OBJECTS' lists, the OPTIONS and MENU
    # cursors, RETURN on OPTIONS' line A: four times, game_options kept;
    # STATUS's focus on two active conditions and their gestures).
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        initial = state(s)
        for k in (0, 7):                    # SEVERE CUTS, POISON BITE
            s.step(L.poke('injury_active', 1, k))
        for command, redraw, keys in (('INVENTORY', 'inventory_redraw', ['\\r', '\\v', '\\v', '\\>', '\\v', '\\<']),
                                       ('HELP', 'module_help', list('HHH')),
                                       ('STATUS', 'page_top', ['\\>'] * 7),
                                       ('STATUS', 'page_top', ['\\<', '\\<', 'P', 'A', 'P', 'A']),
                                       # focus moves: OBJECTS' lists,
                                       # the cursors of OPTIONS and MENU
                                       ('INVENTORY', 'inventory_redraw', ['\\r', '\\>', '\\<', '\\^', '\\^', '\\r', '\\>']),
                                       ('STATUS', 'page_top', ['\\<', '\\<', '\\v', '\\v', '\\^', '\\v', '\\r', '\\r', '\\r']),
                                       ('STATUS', 'page_top', ['\\<', '\\v', '\\v', '\\v', '\\^', '\\^']),
                                       # STATUS's MEDICAL rows: the conditions, their gestures
                                       ('STATUS', 'page_top', ['\\v'] * 6 + ['\\>', '\\>', '\\v', '\\<', '\\^', '\\^', '\\v'])):
            s.step('key:' + command); s.step('press:\\r'); s.step(READY)
            for key in keys + keys[-1:]:
                before = s.step('peek:0400:1024').data
                s.step('press:' + key)
                s.step(L.until(redraw, 20000))
                profile = s.step(f'pcprof:{L["keyboard_wait"]:04X}:20000')
                after = s.step('peek:0400:1024').data
                pcs = {int(a, 16): int(c) for a, c in
                       re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', profile.out, re.M)}
                writes = text_writes(pcs, MENU_STORES)
                changes = text_changes(before, after)
                assert writes == changes, (command, key, s.step(L.peek('pg_cur')).data, writes, changes)
                if before == after:
                    assert writes == 0
            s.step('key:\\e'); s.step(IDLE)
        assert s.step(L.peek('game_options')).data == b'\x80', 'P twice (MAP on again), A three times (on)'
        s.step(L.poke('game_options', 0))
        assert state(s) == initial
    print('  OBJECTS/HELP/the top pages/OPTIONS/focus moves (STATUS\'s care gestures too): one store per changed '
          'character, no stores for identical pages; state preserved')


if __name__ == '__main__':
    reveal(); simulation_landscape(); differential_pages()
    print('Visual transitions: OK')
