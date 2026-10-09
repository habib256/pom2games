#!/usr/bin/env python3
"""No corridor diagonal may continue inside a projected solid wall."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
import a2test

ROOT = Path(__file__).resolve().parents[2]
L = a2test.labels(ROOT/'light3dball/build/game.lbl', strip=True)
DISK = ROOT/'dist/LIGHT3DBALL.dsk'
levels = json.loads((ROOT/'light3dball/levels.json').read_text())


def diagonal(x0, y0, x1, y1):
    dx, dy = abs(x1-x0), -abs(y1-y0)
    sx, sy = (1 if x0<x1 else -1), (1 if y0<y1 else -1)
    error = dx+dy
    while True:
        yield x0, y0
        if (x0,y0) == (x1,y1):
            break
        e = error*2
        if e >= dy:
            error += dy; x0 += sx
        if e <= dx:
            error += dx; y0 += sy


pixels = set()
for edge in ((2,6,116,73), (254,6,140,73), (2,154,116,87), (254,154,140,87)):
    pixels.update(diagonal(*edge))
total = 0
for level, layout in enumerate(levels):
    poses = []
    for obstacle in layout['obstacles']:
        for phase in (range(32) if obstacle['kind']=='D' else (0,)):
            poses += [(obstacle['z']-10, phase), (obstacle['z']-2, phase)]
    for start in range(0, len(poses), 40):
        batch = poses[start:start+40]
        steps = ['wait:1100', f'key:{level+1}', L.until('physics')]
        expected = []
        for camera, phase in batch:
            for name, value, word in [('paused', 1, False), ('launched', 1, False),
                                     ('lives', 0, False), ('camera_z', camera, True),
                                     ('door_phase', phase, False), ('paddle_x', 64, False),
                                     ('paddle_y', 64, False)]:
                steps += [L.poke(name, value)]
                if word:
                    steps += [L.poke(name, value>>8, 1)]
            steps += [L.until('frame_mark'), L.until('physics'), L.until('frame_mark'),
                      'peek:2000:16384', L.until('physics')]
            forbidden = set()
            contours = set()
            first = camera//128
            for wall in layout['obstacles']:
                if not first <= wall['z']//128-1 < first+4:
                    continue
                d = min((wall['z']-camera)//2, 255)
                sx, sy = 252*32//(32+d), 148*32//(32+d)
                left, top = 128-sx//2, 80-sy//2
                width = wall['width']
                if wall['kind'] == 'L':
                    lo, hi = 128-width, 127
                elif wall['kind'] == 'R':
                    lo, hi = 0, width
                else:
                    t = (phase+2*wall['phase']) & 31
                    lo = 8+4*(t if t<16 else 31-t)
                    hi = lo+width
                a, b = left+lo*sx//128, left+hi*sx//128
                faces = []
                if lo:
                    faces.append((left, a))
                if hi<127:
                    faces.append((b, left+sx))
                for x0, x1 in faces:
                    contours.update((x, y) for x in range(x0,x1+1) for y in (top,top+sy))
                    contours.update((x, y) for y in range(top,top+sy+1) for x in (x0,x1))
                for x,y in pixels:
                    if 104 <= x <= 152 and 66 <= y <= 93:
                        continue  # the visible paddle can cover these pixels
                    if top < y < top+sy and ((lo and left < x < a) or
                                            (hi<127 and b < x < left+sx)):
                        forbidden.add((x,y))
            expected.append(forbidden-contours)
        result = a2test.run(DISK, steps)
        for index, (camera, phase) in enumerate(batch):
            pages = result.mem(0x2000, 16384, index)
            for base in (0,8192):
                for x,y in expected[index]:
                    assert not pages[base+a2test.hgr_offset(y)+x//7] & (1 << (x%7)), \
                        ('diagonal behind wall', level+1, camera, phase, base, x, y)
            total += 1
print(f'LIGHT3DBALL occlusion: {total} views on both pages, all levels and 32 door phases passed.')
