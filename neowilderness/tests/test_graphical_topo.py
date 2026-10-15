#!/usr/bin/env python3
"""TOPO draws its disk's global terrain in DHGR; MAP keeps the live local map.

Lot 4: the sheet is computed from the resident map by TOPOGEN (module 0 in
the SIM window, src/topo_dhgr.s) and must equal tools/topo_dhgr_ref.sheet
(the player's arrow only with bit 7 of game_options, the OPTIONS page) on rows 0..159 of both banks; the legend fills the four 80-column rows; the
only disk access is TOPOGEN itself, read from NEOWILD.BLK at each opening
on every disk (docs/MEMORY.md 18): exactly its blocks; the return copies back the snapshot of the view (no raycast):
view, band, state and clock unchanged. The snapshot is compressed
(docs/MEMORY.md section 12): a view that does not fit its area (here, noise
poked into the main bank) is not kept, and the return redraws it. On a
native map (fine geography
resident in the auxiliary language card, where the snapshot would go:
src/geoaux.s) the return redraws the view instead: displayed rows identical.
UP on the tab row of a top page opens TOPO (15 October 2026), closing the
loop of the storeys. The bottom pages (14 October 2026): DOWN on the view opens the grid of
commands, DOWN past its last row opens TOPO, LEFT/RIGHT
switch to MAP over the sheet and back without a module load or redrawing
the sheet, MAP scrolls by I/J/K/L, MAP turned off (bit 6) keeps TOPO, UP
returns to the view copied back.
"""
import tempfile
from common import HERE, L, DISK, a2test, disk_with, hgr_rows, text_screen, dhgr_page, map_cue, is_status
import topo_dhgr_ref as R

IDLE = L.until('idle', 20000)
STATE = (('px', 6), ('s_hour', 5), ('s_health', 5), ('it_place', 76), ('heading', 2))


def topo_reads(s):
    """READ_BLOCK calls of one TOPO opening: TOPOGEN's blocks when the
    directory puts module 0 on NEOWILD.BLK (bank $40), else none."""
    if s.step(L.peek('module_dir', 1, 0)).data[0] != 0x40:
        return 0
    return -(-int.from_bytes(s.step(L.peek('module_dir', 2, 3)).data, 'little') // 512)


def mli_calls(s):
    return int.from_bytes(s.step(L.peek('mli_calls', 2)).data, 'little')


def screens(disk, mapdata, snapshot=True):
    timings = []
    with a2test.Session(disk) as s:
        s.step(IDLE)
        state = [s.step(L.peek(name, count)).data for name, count in STATE]
        pos = state[0]          # px, py, heading: the player's arrow
        arrow = R.sheet(mapdata, player=(pos[1], pos[3], pos[4] | pos[5] << 8))[:R.ROWS]
        want = R.sheet(mapdata)[:R.ROWS]       # the player hidden by default (OPTIONS page: A)
        view = s.step('peek:2000:8192').data
        mli, reads = mli_calls(s), topo_reads(s)
        # Exits: ESC, RETURN, SPACE and UP (the bottom pages: UP is the view).
        for k, (command, exit_key) in enumerate((('TOPO', '\\e'), ('T', '\\r'), ('TOPO', ' '), ('T', '\\^'))):
            if k == 1:
                s.step(L.poke('game_options', 0x80))
                want = arrow
            s.step(f'key:{command}')
            s.step('press:\\r')
            start = s.step(L.until('do_command', 20000)).cycles[-1]
            end = s.step(L.until('graphical_topo_key', 20000)).cycles[-1]
            timings.append(end - start)
            page = s.step('peek:2000:8192').data
            got = dhgr_page(page)[:R.ROWS]
            bad = [(y, x) for y in range(R.ROWS) for x in range(R.COLS) if got[y][x] != want[y][x]]
            assert not bad, ('TOPO sheet differs from tools/topo_dhgr_ref', len(bad), bad[:5])
            assert s.step('peek:C01F:1').data[0] >= 0x80, 'TOPO is DHGR (80COL on)'
            assert s.step('peek:C01A:1').data[0] < 0x80, 'graphics, mixed with the legend'
            legend = text_screen(s.step('peek:0400:1024').data)[20:]
            assert [row.rstrip() for row in legend] == list(R.LEGEND), legend
            s.step(f'press:{exit_key}')
            back = s.step(IDLE).cycles[-1]
            timings.append(back - end)
            assert s.step('peek:C01F:1').data[0] >= 0x80, 'the view must return in DHGR'
            if snapshot:
                assert s.step('peek:2000:8192').data == view, 'view and band copied back'
            else:       # redrawn: screen holes keep simulation scratch
                assert hgr_rows(s.step('peek:2000:8192').data) == hgr_rows(view), 'view and band redrawn'
            assert state == [s.step(L.peek(name, count)).data for name, count in STATE]
        assert mli_calls(s) == mli + 4 * reads, ('TOPO reads TOPOGEN alone', mli_calls(s) - mli, reads)
        s.step('key:MAP')
        s.step('press:\\r')
        s.step(L.until('topo_key', 20000))
        assert map_cue(text_screen(s.step('peek:0400:1024').data))
        assert hgr_rows(s.step('peek:2000:8192').data) == hgr_rows(view)
        s.step('press:\\e')
        s.step(IDLE)
    opening = [t / a2test.CPU_HZ for t in timings[0::2]]
    closing = [t / a2test.CPU_HZ for t in timings[1::2]]
    print(f'  TOPO/T: DHGR sheet = topo_dhgr_ref (rows 0..159, both banks), legend, TOPOGEN read alone; '
          f'open {min(opening):.2f}-{max(opening):.2f} s, return {max(closing):.2f} s '
          f'({"snapshot, no raycast" if snapshot else "native map: redrawn"}); view/state preserved; '
          f'MAP: local text: OK')


def bottom_pages():
    data = (HERE/'build/map.bin').read_bytes()
    want = R.sheet(data)[:R.ROWS]
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        view = s.step('peek:2000:8192').data
        state = [s.step(L.peek(name, count)).data for name, count in STATE]
        mli, reads = mli_calls(s), topo_reads(s)
        for _ in range(8):      # DOWN: the grid, its rows, then past the last one: TOPO
            s.step('key:\\v')
            if f'PC={L["graphical_topo_key"]:04X}' in s.step(
                    f'until:{L["graphical_topo_key"]:04X},{L["idle"]:04X}:20000').out:
                break
        else:
            raise AssertionError('DOWN never reached TOPO')
        sheet = s.step('peek:2000:8192').data
        assert dhgr_page(sheet)[:R.ROWS] == want, 'DOWN: the TOPO sheet'
        loads = s.step(L.peek('xfer_count', 2)).data
        fetch = L['mem_fetch']
        s.step(f'watch:{fetch:04X}')
        mark = len(s.out)
        s.step('key:\\>')
        s.step(L.until('topo_key', 20000))
        assert s.step('peek:C01A:1').data[0] >= 0x80, 'MAP: full text'
        first = text_screen(s.step('peek:0400:1024').data)
        assert map_cue(first), first[0]
        assert s.step('peek:2000:8192').data == sheet, 'MAP writes the text page only'
        x0 = s.step(L.peek('topo_x')).data[0]
        s.step('key:L')
        s.step(L.until('topo_key', 20000))
        assert s.step(L.peek('topo_x')).data[0] == min(x0 + 10, 112 - 40), 'L: a quarter window east'
        assert text_screen(s.step('peek:0400:1024').data) != first, 'L scrolls the map'
        s.step('key:\\<')
        s.step(L.until('graphical_topo_key', 20000))
        assert s.step('peek:2000:8192').data == sheet, 'back to TOPO: the same sheet'
        assert s.step('peek:C01A:1').data[0] < 0x80, 'TOPO: graphics, mixed'
        legend = text_screen(s.step('peek:0400:1024').data)[20:]
        assert [row.rstrip() for row in legend] == list(R.LEGEND), legend
        s.step(L.poke('game_options', 0x40))     # MAP off: LEFT/RIGHT stay on TOPO
        s.step('key:\\>')
        s.step('wait:2')
        s.step(L.until('graphical_topo_key', 20000))
        assert s.step('peek:C01A:1').data[0] < 0x80, 'MAP off: TOPO stays'
        s.step(L.poke('game_options', 0))
        assert f'watch {fetch:04X}' not in s.out[mark:], 'no module load between TOPO and MAP'
        assert s.step(L.peek('xfer_count', 2)).data == loads
        s.step('unwatch')
        s.step('key:\\^')
        s.step(IDLE)
        assert s.step('peek:2000:8192').data == view, 'UP: the view copied back'
        assert state == [s.step(L.peek(name, count)).data for name, count in STATE]
        assert mli_calls(s) == mli + reads, ('one TOPO opening: TOPOGEN alone', mli_calls(s) - mli, reads)
        # 15 October 2026: DOWN on a bottom page turns to the top pages
        # (STATUS), the view closed as UP closes it; from TOPO, then from MAP.
        for via_map in (False, True):
            s.step('key:T\\r')
            s.step(L.until('graphical_topo_key', 40000))
            if via_map:
                s.step('key:\\>')
                s.step(L.until('topo_key', 20000))
            s.step('key:\\v')
            s.step(L.until('status_key', 40000))
            s.step('wait:2')
            rows = text_screen(s.step('peek:0400:1024').data)
            assert is_status(rows), rows[:3]
            if via_map:     # UP on the tab row: TOPO again, the loop closed
                s.step('key:\\^')
                s.step(L.until('graphical_topo_key', 40000))
                assert dhgr_page(s.step('peek:2000:8192').data)[:R.ROWS] == want, 'STATUS, UP: the TOPO sheet'
                s.step('key:\\^')
            else:
                s.step('key:\\e')
            s.step(IDLE)
            assert s.step('peek:2000:8192').data == view, ('DOWN, then ESC: the view intact', via_map)
            assert state == [s.step(L.peek(name, count)).data for name, count in STATE]
    print('  bottom pages: DOWN TOPO, RIGHT MAP over the sheet, L scrolls, LEFT TOPO (no load, no redraw), '
          'MAP off keeps TOPO, UP: the view intact; DOWN from TOPO or MAP: STATUS, UP on its tab row: TOPO: OK')


def overflow():
    """An incompressible view: no snapshot, the return redraws the view."""
    import random
    rnd = random.Random(7)
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        view = s.step('peek:2000:8192').data
        for y in range(16, 160):
            base = 0x2000 + a2test.hgr_offset(y)
            for i in range(40):
                s.step(f'poke:{base + i:04X}:{rnd.randrange(128):02X}')
        s.step('key:TOPO')
        s.step('press:\\r')
        s.step(L.until('graphical_topo_key', 20000))
        assert s.step(L.peek('tp_valid', 1)).data[0] == 0, 'the noisy view must not fit'
        s.step('press:\\e')
        s.step(IDLE)
        assert hgr_rows(s.step('peek:2000:8192').data) == hgr_rows(view), 'view redrawn'
    print('  TOPO over an incompressible view: no snapshot, the view is redrawn: OK')


if __name__ == '__main__':
    bottom_pages()
    overflow()
    data = (HERE/'build/map.bin').read_bytes()
    screens(DISK, data)
    alternate = bytearray(data)
    alternate[64:64+9408] = bytes((x//4 + y//6) | (128 if 45 <= x <= 48 else 0)
                                      for y in range(84) for x in range(112))
    alternate[21] = 0           # legacy header: the sheet scans the grid maximum
    assert R.sheet(alternate) != R.sheet(data)
    with tempfile.TemporaryDirectory() as tmp:
        screens(disk_with(tmp, alternate), alternate)
    # A native map (mkmap --native): no snapshot, the return redraws.
    from test_geo_resident import generated_native
    native = generated_native()[0]
    with tempfile.TemporaryDirectory() as tmp:
        screens(disk_with(tmp, native), native, snapshot=False)
    print('Graphical TOPO and local MAP: OK')
