#!/usr/bin/env python3
"""Geometry sanitizers and real 16-bit cc65 numeric-field bounds."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile
import test_hgr

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / 'dev'


def geometry(work):
    binary = work / 'geometry'
    subprocess.run([*shlex.split(os.environ.get('CC', 'cc')), '-O1', '-g',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-D__fastcall__=', '-I', str(DEV / 'lib/gfx'),
                    str(DEV / 'tests/gfx_geometry_fixture.c'),
                    *[str(DEV / 'lib/gfx' / ('gfx_' + name + '.c'))
                      for name in ('circle', 'ellipse', 'line')],
                    '-o', str(binary)], check=True)
    for mode in ('circle', 'ellipse'):
        subprocess.run([str(binary), mode], check=True)


def fields(work):
    source = work / 'fields.c'
    source.write_text('''#include "hgr.h"
int main(void) {
    hgr_init();
    hgr_set_draw_page(2u); hgr_clear(42u);
    hgr_set_draw_page(1u); hgr_clear(0u);
    hgr_putu_field(65530u, 20u, 9u, 3u);
    hgr_putu_field(65535u, 40u, 9u, 14u);
    hgr_putu_field(280u, 60u, 9u, 3u);
    *(volatile unsigned char *)0x1000 = 1u;
    for (;;) {}
    return 0;
}
''')
    disk = test_hgr.build(work, source)
    result = test_hgr.a2test.run(disk, ['wait:1100', 'peek:1000:1', 'peek:2000:16384'])
    assert result.dumps[0] == b'\x01', 'fixture did not finish'
    assert result.dumps[1] == bytes(8192) + bytes([42]) * 8192, 'off-screen numeric field wrapped into visible RAM'
    print('cc65 numeric field: off-screen coordinates leave both pages intact.')


def circles(work):
    source = work / 'circles.c'
    source.write_text('''#include "hgr.h"
#include "gfx.h"
int main(void) {
    unsigned char page;
    for (page=1u; page<=2u; ++page) {
        hgr_set_draw_page(page); hgr_clear(0u);
        hgr_circle(65535u, 100u, 1u);
        gfx_circle(65534u, 100u, 2u);
        gfx_circle(65281u, 100u, 255u);
        gfx_circle(32768u, 100u, 255u);
    }
    *(volatile unsigned char *)0x1000 = 1u;
    apple2_getkey();
    hgr_set_draw_page(1u);
    gfx_circle(280u, 100u, 1u);
    *(volatile unsigned char *)0x1000 = 2u;
    for (;;) {}
    return 0;
}
''')
    disk = test_hgr.build(work, source)
    result = test_hgr.a2test.run(disk, ['wait:1100', 'peek:1000:1', 'peek:2000:16384',
                                      'key: ', 'wait:60', 'peek:1000:1', 'peek:2000:16384'])
    assert result.dumps[0] == b'\x01', 'circle fixture did not finish'
    assert result.dumps[1] == bytes(16384), 'far-off circle centre wrapped into visible RAM'
    assert result.dumps[2] == b'\x02', 'partially visible circle did not finish'
    expected = bytearray(16384)
    expected[test_hgr.offset(100) + 39] = 64  # (279,100), the one visible point
    assert result.dumps[3] == expected, 'partially visible circle was rejected or misdrawn'
    print('cc65 circles: distant centres leave both pages intact; near-edge arcs remain visible.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='gfx-boundaries-') as tmp:
        work = Path(tmp)
        geometry(work)
        fields(work)
        circles(work)
