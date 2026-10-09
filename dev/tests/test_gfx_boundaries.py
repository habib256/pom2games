#!/usr/bin/env python3
"""Geometry sanitizers and real 16-bit cc65 numeric-field bounds."""
from pathlib import Path
import os
import shlex
import subprocess
import struct
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


def ellipses(work):
    source = work / 'ellipses.c'
    source.write_text('''#include "hgr.h"
#include "gfx.h"
int main(void) {
    unsigned char page;
    for (page=1u; page<=2u; ++page) {
        hgr_set_draw_page(page); hgr_clear(0u);
        hgr_ellipse(280u, 20u, 310u, 40u);
        hgr_ellipse(310u, 40u, 280u, 20u);
        gfx_ellipse(0u, 192u, 10u, 210u);
        gfx_ellipse(10u, 210u, 0u, 192u);
        hgr_ellipse(65535u, 20u, 65535u, 20u);
        gfx_ellipse(32768u, 40u, 65535u, 60u);
    }
    *(volatile unsigned char *)0x1000 = 1u;
    for (;;) {}
    return 0;
}
''')
    disk = test_hgr.build(work, source)
    result = test_hgr.a2test.run(disk, ['wait:1100', 'peek:1000:1', 'peek:2000:16384'])
    assert result.dumps[0] == b'\x01', 'ellipse fixture did not finish'
    assert result.dumps[1] == bytes(16384), 'wholly off-screen ellipse painted a screen edge'
    print('cc65 ellipses: off-screen boxes, reversed corners, degenerate and distant boxes preserve both pages.')


def ellipse_coordinates(work):
    # Compare the actual cc65 chord endpoints with an arbitrary-precision
    # reference. Host sanitizers cannot expose cc65's 16-bit int overflow.
    quarter = (64, 64, 63, 61, 59, 56, 53, 49, 45, 41, 36, 30, 24, 19, 12, 6)
    cosine = quarter + (0,) + tuple(-v for v in reversed(quarter[1:]))
    cosine += tuple(-v for v in cosine)
    sine = cosine[48:] + cosine[:48]
    cases = [(10, 20, 200, 100), (0, 0, 559, 191),
             (0, 20, 1022, 100), (0, 20, 1024, 100),
             (0, 20, 32767, 100), (10, 20, 32768, 100),
             (0, 20, 65535, 100), (279, 20, 65535, 100),
             (0, 50, 65535, 50), (10, 20, 11, 100)]
    cases += [(x1, y1, x0, y0) for x0, y0, x1, y1 in cases]
    calls = '\n'.join(f'count = 0; gfx_ellipse({x0}u,{y0}u,{x1}u,{y1}u); apple2_getkey();'
                      for x0, y0, x1, y1 in cases)
    source = work / 'ellipse_coordinates.c'
    source.write_text('''#include "gfx.h"
#include "apple2io.h"
const unsigned gfx_width = TEST_WIDTH;
const unsigned char gfx_height = 192;
unsigned records[64][4];
unsigned char count;
void gfx_line(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1) {
    if (count < 64u) {
        records[count][0] = x0; records[count][1] = y0;
        records[count][2] = x1; records[count][3] = y1;
    }
    ++count;
}
int main(void) {
''' + calls + '\nfor (;;) {}\nreturn 0;\n}\n')
    for width in (140, 280, 560):
        target = work / str(width)
        target.mkdir()
        disk = test_hgr.build(target, source, cflags=(f'-DTEST_WIDTH={width}',))
        labels = test_hgr.a2test.labels(target / 'test.lbl', strip=True)
        steps = ['wait:1100']
        for _ in cases:
            steps += [labels.peek('count'), labels.peek('records', 512), 'key: ', 'wait:60']
        result = test_hgr.a2test.run(disk, steps)
        clamp = lambda x, y: (min(x, width - 1), min(y, 191))
        scale = lambda c, r: (1 if c >= 0 else -1) * (abs(c) * r // 64)
        for i, (x0, y0, x1, y1) in enumerate(cases):
            xc, yc = (x0 + x1) // 2, (y0 + y1) // 2
            rx, ry = abs(x1 - x0) // 2, abs(y1 - y0) // 2
            if min(x0, x1) >= width:
                expected = []
            elif rx == 0 and (x0 == x1 or y0 != y1):
                expected = [clamp(xc, y0) + clamp(xc, y1)]
            elif ry == 0:
                expected = [clamp(min(x0, x1), yc) + clamp(max(x0, x1), yc)]
            else:
                points = [clamp(xc + scale(c, rx), yc + scale(s, ry))
                          for c, s in zip(cosine, sine)]
                expected = [points[j] + points[(j + 1) % 64] for j in range(64)]
            record = result.data[i * 513:(i + 1) * 513]
            count = record[0]
            assert count == len(expected), (width, cases[i], count)
            actual = list(struct.iter_unpack('<4H', record[1:1 + count * 8]))
            assert actual == expected, (width, cases[i], actual, expected)
    print('cc65 ellipse coordinates: 60 boxes match the reference in HGR and both DHGR dimensions.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='gfx-boundaries-') as tmp:
        work = Path(tmp)
        geometry(work)
        fields(work)
        circles(work)
        ellipses(work)
        ellipse_coordinates(work)
