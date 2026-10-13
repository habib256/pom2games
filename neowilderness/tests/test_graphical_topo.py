#!/usr/bin/env python3
"""TOPO draws its disk's global terrain in DHGR; MAP keeps the live local map.

TOPO (module 0, src/topo.s) is generated at display time from the resident
map: both banks of rows 0..159 must equal tools/topo_ref.render, on the
default map, on an alternate map and after a WALK (moved P marker).
"""
import tempfile
from common import HERE, L, DISK, a2test, disk_with, hgr_rows, text_screen
import topo_ref

IDLE = L.until('idle', 20000)
STATE = (('px', 6), ('s_hour', 5), ('s_health', 5), ('it_place', 76))


def topo_banks(page):
    return topo_ref.rows_of(page[:8192]), topo_ref.rows_of(page[8192:])


def check_topo(s, mapdata, label):
    px, py = (int.from_bytes(s.step(L.peek(n, 2)).data, 'little') for n in ('px', 'py'))
    got = topo_banks(s.step('peek:2000:8192').data)
    want = tuple(topo_ref.rows_of(bank) for bank in topo_ref.render(mapdata, px, py))
    if got != want:
        page = topo_ref.page(mapdata, px, py)
        import dhgr_ref
        main, aux = s.step('peek:2000:8192').data[:8192], s.step('peek:2000:8192').data[8192:]
        real = dhgr_ref.decode(main, aux)
        bad = [(r, x, real[r][x], page[r][x]) for r in range(160) for x in range(140)
               if real[r][x] != page[r][x]]
        raise AssertionError(f'{label}: {len(bad)} pixels differ, first {bad[:8]}')
    # The view's mode: DHGR (80COL on) with the four mixed text rows.
    assert s.step('peek:C01F:1').data[0] >= 0x80, 'TOPO must be DHGR'
    assert s.step('peek:C01B:1').data[0] >= 0x80, 'TOPO keeps the mixed text rows'
    text = '\n'.join(text_screen(s.step('peek:0400:1024').data)[20:])
    assert 'TOPO' in text and 'RANGERS' in text, text
    return px, py


def screens(disk, mapdata, walk=False):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        positions = []
        if walk:
            s.step('key:WALK 1 H')
            s.step('press:\\r')
            s.step(L.until('do_command', 40000))
            stops = f'until:{L["idle"]:04X},{L["wait_key"]:04X}:40000'
            while s.step(stops).out.rstrip().endswith(f'PC={L["wait_key"]:04X}'):
                s.step('press: ')
                s.step('wait:1')
        state = [s.step(L.peek(name, count)).data for name, count in STATE]
        view = s.step('peek:2000:8192').data
        for command, exit_key in (('TOPO', '\\e'), ('T', '\\r'), ('TOPO', ' ')):
            s.step(f'key:{command}')
            s.step('press:\\r')
            s.step(L.until('graphical_topo_key', 20000))
            positions.append(check_topo(s, mapdata, command))
            s.step(f'press:{exit_key}')
            s.step(IDLE)
            assert s.step('peek:C01F:1').data[0] >= 0x80, 'the view must return in DHGR'
            assert hgr_rows(s.step('peek:2000:8192').data) == hgr_rows(view)
            assert state == [s.step(L.peek(name, count)).data for name, count in STATE]
        s.step('key:MAP')
        s.step('press:\\r')
        s.step(L.until('topo_key', 20000))
        assert text_screen(s.step('peek:0400:1024').data)[0].startswith('MAP P YOU')
        assert hgr_rows(s.step('peek:2000:8192').data) == hgr_rows(view)
        s.step('press:\\e')
        s.step(IDLE)
    return positions[0]


if __name__ == '__main__':
    data = (HERE / 'build/map.bin').read_bytes()
    start = (data[2] | data[3] << 8, data[4] | data[5] << 8)
    # At the crash site P's box takes C's orange (white P on top).
    page = topo_ref.page(data)
    r, x = topo_ref.top_row(data[5]), data[3]
    box = {page[r + dy][x + dx] for dy in (-3, 3) for dx in (-2, 2)}
    assert box == {topo_ref.P.ORANGE} and page[r - 2][x - 1] == topo_ref.P.WHITE, box
    assert screens(DISK, data) == start
    print('  TOPO/T/TOPO on the default map: both banks of rows 0..159 = topo_ref; '
          'DHGR + mixed text; three exit keys; view redrawn; state kept; MAP local text: OK')
    moved = screens(DISK, data, walk=True)
    assert moved[0] >> 8 != start[0] >> 8 or moved[1] >> 8 != start[1] >> 8, moved
    print(f'  after WALK 1 H: P at cell ({moved[0] >> 8}, {moved[1] >> 8}) = topo_ref: OK')
    alternate = bytearray(data)
    alternate[64:64+9408] = bytes((x//4 + y//6) | (128 if 45 <= x <= 48 else 0)
                                  for y in range(84) for x in range(112))
    # Low wooded cells (dark green tint): their dots must be black.
    for y in range(84):
        for x in range(56, 112):
            if topo_ref.woods(alternate, x, y) and not alternate[64 + y*112 + x] & 128:
                alternate[64 + y*112 + x] = 3
    alternate[21] = 1 + max(v & 0x7F for v in alternate[64:64+9408])   # highest level + 1
    black_woods = sum(1 for y in range(84) for x in range(112)
                      if alternate[64 + y*112 + x] == 3 and (x + y) & 1
                      and topo_ref.cell_colour(alternate, x, y) == topo_ref.P.BLACK)
    assert black_woods, 'no woods dot on the dark green tint'
    assert topo_ref.render(alternate) != topo_ref.render(data)
    with tempfile.TemporaryDirectory() as tmp:
        screens(disk_with(tmp, alternate), alternate)
    print(f'  alternate map disk = topo_ref (legend {topo_ref.legend_blocks(alternate)}, '
          f'{black_woods} black woods dots): OK')
    print('Graphical DHGR TOPO and local MAP: OK')
