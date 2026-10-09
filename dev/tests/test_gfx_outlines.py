#!/usr/bin/env python3
"""Outline uniqueness on the host and real cc65 rendering on both HGR pages."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile
import test_hgr

DEV = test_hgr.DEV
CIRCLES = [(140, 96, r) for r in (0, 1, 2, 3, 4, 8, 16, 64, 255)] + [
    (0, 0, 16), (279, 191, 16), (280, 100, 1), (5, 255, 64),
    (5, 255, 63), (65535, 100, 255)]
RECTS = [(10, 20, 10, 20), (10, 20, 50, 20), (10, 20, 10, 80),
         (10, 20, 50, 80), (11, 21, 10, 20), (0, 0, 279, 191),
         (270, 180, 300, 210), (300, 210, 270, 180),
         (279, 191, 65535, 255), (280, 0, 65535, 255),
         (0, 192, 279, 255), (0, 0, 65535, 255)]


def reference_circle(cx, cy, radius):
    # Collect the historical midpoint outline as a set, independent of how
    # often its symmetry cases used to send the same point to the backend.
    points = set()
    x, y, d = 0, radius, 1 - radius
    while x <= y:
        for dx, dy in ((x, y), (y, x)):
            for sx in (-1, 1):
                for sy in (-1, 1):
                    points.add((cx + sx * dx, cy + sy * dy))
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1
    return points


def check(work):
    binary = work / 'host'
    subprocess.run([*shlex.split(os.environ.get('CC', 'cc')), '-O1', '-g',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-D__fastcall__=', '-I', str(DEV / 'lib/gfx'),
                    str(DEV / 'tests/gfx_outline_fixture.c'),
                    str(DEV / 'lib/gfx/gfx_circle.c'), str(DEV / 'lib/gfx/gfx_rect.c'),
                    '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
    scenes = [('gfx_circle', case) for case in CIRCLES] + [('gfx_rect', case) for case in RECTS]
    calls = '\n'.join('hgr_clear(42u);\n' + name + '(' + ','.join(f'{v}u' for v in case) +
                      f');\n*(volatile unsigned char *)0x1000={i}u; apple2_getkey();'
                      for i, (name, case) in enumerate(scenes))
    source = work / 'outlines.c'
    source.write_text('#include "hgr.h"\n#include "gfx.h"\nint main(void) {\n'
                      'unsigned char page; hgr_init();\n'
                      'hgr_set_draw_page(1u); hgr_clear(42u);\n'
                      'hgr_set_draw_page(2u); hgr_clear(42u);\n'
                      'for(page=1;page<=2;++page) {hgr_set_draw_page(page);\n' + calls +
                      '\n}\nfor (;;) {}\nreturn 0;\n}\n')
    disk = test_hgr.build(work, source)
    steps = ['wait:1100']
    for _ in range(2 * len(scenes)):
        steps += ['peek:1000:1', 'peek:2000:16384', 'key: ', 'wait:60']
    data = test_hgr.a2test.run(disk, steps).data
    previous = bytearray([42]) * 16384
    for index in range(2 * len(scenes)):
        scene = index % len(scenes)
        page = index // len(scenes)
        chunk = data[index * 16385:(index + 1) * 16385]
        assert chunk[0] == scene, ('fixture did not finish', index)
        name, case = scenes[scene]
        if name == 'gfx_circle':
            points = reference_circle(*case)
        else:
            x0, x1 = sorted((case[0], case[2]))
            y0, y1 = sorted((case[1], case[3]))
            points = {(x, y) for y in range(192) for x in range(280)
                      if x0 <= x <= x1 and y0 <= y <= y1 and
                      (x in (x0, x1) or y in (y0, y1))}
        expected = previous[:]
        view = bytearray([42]) * 8192
        for x, y in points:
            if 0 <= x < 280 and 0 <= y < 192:
                test_hgr.pixel(view, x, y, 1, white=True)
        expected[page * 8192:(page + 1) * 8192] = view
        assert chunk[1:] == expected, ('outline pixels or inactive page', page + 1, name, case)
        previous = expected
    assert len(data) == 2 * len(scenes) * 16385
    print('cc65 outlines: 54 scenes preserve pixels, clipping, both pages and screen holes.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='gfx-outlines-') as tmp:
        check(Path(tmp))
