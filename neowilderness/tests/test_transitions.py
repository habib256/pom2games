#!/usr/bin/env python3
"""Completed-page reveals, clean redraw curtains and differential menus."""
import re
import tempfile
from pathlib import Path
import struct
import zlib
from common import MENU_SKIP, MENU_STORES, HERE, L, DISK, a2test, hgr_rows, text_screen, text_writes, text_changes, map_rows
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
        assert screen[0].startswith('STATUS:') and not screen[20].strip()
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
        assert not any(picture(s, path)), 'explicit VIEW must hide its full redraw'
        s.step(IDLE)
        s.step('wait:2')
        assert picture(s, path) == landscape
    print('  persistent loading introduction, prepared STATUS, clean text return, TOPO return without raycast, VIEW: incomplete frames hidden; view/state preserved')


def simulation_curtain():
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(DISK) as s:
        s.step(IDLE)
        # Plant an old full-screen menu above the live command/result rows.
        for row in range(20):
            offset = (row % 8) * 128 + (row // 8) * 40
            for col in range(40):
                s.step(f'poke:{0x400+offset+col:04X}:D8')
        before = text_screen(s.step('peek:0400:1024').data)[20:]
        cursor = s.step('peek:0024:2').data
        for step in call(['thermal']):
            s.step(step)
        s.step(L.until('overlay_before_transfer', 20000))
        screen = text_screen(s.step('peek:0400:1024').data)
        assert all(not row.strip() for row in screen[:20])
        assert screen[20:] == before and s.step('peek:0024:2').data == cursor
        s.step('wait:2')
        assert not any(picture(s, Path(tmp) / 'simulation.png'))
    print('  SIM hides stale menus before its RAM transfer; command, results and cursor preserved')


def differential_pages():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        initial = state(s)
        for command, redraw, keys in (('INVENTORY', 'inventory_redraw', '123451'),
                                       ('HELP', 'help_redraw', '1231')):
            s.step('key:' + command); s.step('press:\\r'); s.step(READY)
            for key in keys + keys[-1]:
                before = s.step('peek:0400:1024').data
                s.step('press:' + key)
                s.step(L.until(redraw, 20000))
                profile = s.step(f'pcprof:{L["keyboard_wait"]:04X}:20000')
                after = s.step('peek:0400:1024').data
                pcs = {int(a, 16): int(c) for a, c in
                       re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', profile.out, re.M)}
                writes = text_writes(pcs, MENU_STORES)
                changes = text_changes(before, after)
                assert writes == changes, (command, key, writes, changes)
                if before == after:
                    assert writes == 0
            s.step('key:\\e'); s.step(IDLE)
        assert state(s) == initial
    print('  INVENTORY/HELP: one store per changed character, no stores for identical pages; state preserved')


if __name__ == '__main__':
    reveal(); simulation_curtain(); differential_pages()
    print('Visual transitions: OK')
