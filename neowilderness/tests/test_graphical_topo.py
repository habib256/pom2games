#!/usr/bin/env python3
"""TOPO draws its disk's global terrain in DHGR; MAP keeps the live local map.

Lot 4: the sheet is computed from the resident map by TOPOGEN (module 0 in
the SIM window, src/topo_dhgr.s) and must equal tools/topo_dhgr_ref.sheet
on rows 0..159 of both banks; the legend fills the four 80-column rows; no
disk access; the return copies back the snapshot of the view (no raycast):
view, band, state and clock unchanged. The snapshot is compressed
(docs/MEMORY.md section 12): a view that does not fit its area (here, noise
poked into the main bank) is not kept, and the return redraws it. On a
native map (fine geography
resident in the auxiliary language card, where the snapshot would go:
src/geoaux.s) the return redraws the view instead: displayed rows identical.
"""
import tempfile
from common import HERE, L, DISK, a2test, disk_with, hgr_rows, text_screen, dhgr_page, map_cue
import topo_dhgr_ref as R

IDLE = L.until('idle', 20000)
STATE = (('px', 6), ('s_hour', 5), ('s_health', 5), ('it_place', 76), ('heading', 2))


def screens(disk, mapdata, snapshot=True):
    want = R.sheet(mapdata)[:R.ROWS]
    timings = []
    with a2test.Session(disk) as s:
        s.step(IDLE)
        state = [s.step(L.peek(name, count)).data for name, count in STATE]
        view = s.step('peek:2000:8192').data
        mli = s.step(L.peek('mli_calls', 2)).data
        for command, exit_key in (('TOPO', '\\e'), ('T', '\\r'), ('TOPO', ' ')):
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
        assert s.step(L.peek('mli_calls', 2)).data == mli, 'TOPO must not read the disk'
        s.step('key:MAP')
        s.step('press:\\r')
        s.step(L.until('topo_key', 20000))
        assert map_cue(text_screen(s.step('peek:0400:1024').data))
        assert hgr_rows(s.step('peek:2000:8192').data) == hgr_rows(view)
        s.step('press:\\e')
        s.step(IDLE)
    opening = [t / a2test.CPU_HZ for t in timings[0::2]]
    closing = [t / a2test.CPU_HZ for t in timings[1::2]]
    print(f'  TOPO/T: DHGR sheet = topo_dhgr_ref (rows 0..159, both banks), legend, no disk read; '
          f'open {min(opening):.2f}-{max(opening):.2f} s, return {max(closing):.2f} s '
          f'({"snapshot, no raycast" if snapshot else "native map: redrawn"}); view/state preserved; '
          f'MAP: local text: OK')


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
