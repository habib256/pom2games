#!/usr/bin/env python3
"""TOPO displays its disk's global terrain; MAP keeps the live local map."""
import tempfile
from common import HERE, L, DISK, a2test, disk_with, hgr_rows, text_screen
from graphical_topo import render

IDLE = L.until('idle', 20000)


def screens(disk, mapdata):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        state = [s.step(L.peek(name, count)).data for name,count in
                 (('px',6),('s_hour',5),('s_health',5),('it_place',76))]
        view = s.step('peek:2000:8192').data
        for command, exit_key in (('TOPO','\\e'),('T','\\r'),('TOPO',' ')):
            s.step(f'key:{command}')
            s.step('press:\\r')
            s.step(L.until('graphical_topo_key',20000))
            # TOPO is copied into the main half of the DHGR page and shown in
            # single HGR (80COL off: RD80VID bit 7 clear); the view returns in DHGR.
            assert s.step('peek:2000:8192').data[:8192] == render(mapdata)
            assert s.step('peek:C01F:1').data[0] < 0x80, 'TOPO must be single HGR'
            assert 'TOPO' in '\n'.join(text_screen(s.step('peek:0400:1024').data)[20:])
            s.step(f'press:{exit_key}')
            s.step(IDLE)
            assert s.step('peek:C01F:1').data[0] >= 0x80, 'the view must return in DHGR'
            assert hgr_rows(s.step('peek:2000:8192').data) == hgr_rows(view)
            assert state == [s.step(L.peek(name,count)).data for name,count in
                             (('px',6),('s_hour',5),('s_health',5),('it_place',76))]
        s.step('key:MAP')
        s.step('press:\\r')
        s.step(L.until('topo_key',20000))
        assert text_screen(s.step('peek:0400:1024').data)[0].startswith('MAP P YOU')
        assert hgr_rows(s.step('peek:2000:8192').data) == hgr_rows(view)
        s.step('press:\\e')
        s.step(IDLE)
    print('  TOPO/T: global HGR (80COL off), repeated open/close, three exit keys, DHGR view redrawn; '
          'MAP: local text; state/view preserved: OK')


if __name__ == '__main__':
    data = (HERE/'build/map.bin').read_bytes()
    screens(DISK, data)
    alternate = bytearray(data)
    alternate[64:64+9408] = bytes((x//4 + y//6) | (128 if 45 <= x <= 48 else 0)
                                      for y in range(84) for x in range(112))
    assert render(alternate) != render(data)
    with tempfile.TemporaryDirectory() as tmp:
        screens(disk_with(tmp,alternate), alternate)
    print('Graphical TOPO and local MAP: OK')
