#!/usr/bin/env python3
"""Check actual player clearance at every wall and every moving-door phase."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
import a2test

ROOT = Path(__file__).resolve().parents[2]
L = a2test.labels(ROOT/'light3dball/build/game.lbl', strip=True)
DISK = ROOT/'dist/LIGHT3DBALL.dsk'
levels = json.loads((ROOT/'light3dball/levels.json').read_text())
total = 0
for level, layout in enumerate(levels):
    cases = []
    for obstacle in layout['obstacles']:
        width = obstacle['width']
        assert width >= 48, ('large paddle has too little clearance', level+1, obstacle)
        phases = range(32) if obstacle['kind'] == 'D' else (0,)
        for phase in phases:
            if obstacle['kind'] == 'R':
                left, right = 0, width
            elif obstacle['kind'] == 'L':
                left, right = 128-width, 127
            else:
                t = (phase+2*obstacle['phase']) & 31
                left = 8+4*(t if t < 16 else 31-t)
                right = left+width
            lo = max(8, left+14) if left else 8
            hi = min(120, right-14) if right<127 else 120
            assert hi-lo >= 18, ('insufficient steering margin', level+1, phase, lo, hi)
            assert sum(lo <= 64+3*n <= hi for n in range(-19,20)) >= 6, \
                ('opening unreachable at keyboard step', level+1, phase, lo, hi)
            for x in (lo-1, lo, (lo+hi)//2, hi, hi+1):
                if 8 <= x <= 120:
                    cases.append((obstacle['z'], phase, x,
                                  2 if left and x-14 < left else
                                  1 if right<127 and x+14 > right else 0))
    for start in range(0, len(cases), 96):
        batch = cases[start:start+96]
        steps = ['wait:1100', f'key:{level+1}', L.until('physics')]
        for plane, phase, x, blocked in batch:
            values = [('camera_z', plane-10, True), ('ball_z', plane+40, True),
                      ('ball_x', 64*16, True), ('ball_y', 64*16, True),
                      ('vel_x', 0, True), ('vel_y', 0, True), ('vel_z', 1, False),
                      ('paddle_x', x, False), ('paddle_y', 64, False),
                      ('launched', 1, False), ('advancing', 1, False),
                      ('paused', 0, False), ('ticks', phase*8, False)]
            for name, value, word in values:
                steps += [L.poke(name, value)]
                if word:
                    steps += [L.poke(name, value>>8, 1)]
            steps += [L.until('frame_mark'), L.peek('camera_z', 2), L.peek('blocked'),
                      L.until('physics')]
        result = a2test.run(DISK, steps)
        for index, (plane, phase, x, blocked) in enumerate(batch):
            expected_camera = plane-10+(0 if blocked else 2)
            assert result.mem(L['camera_z'], 2, index) == expected_camera.to_bytes(2, 'little'), \
                ('player passage', level+1, plane, phase, x, blocked,
                 result.mem(L['camera_z'], 2, index), result.mem(L['blocked'], 1, index))
            assert result.mem(L['blocked'], 1, index) == bytes([blocked]), \
                ('alignment direction', level+1, plane, phase, x, blocked)
        total += len(batch)
print(f'LIGHT3DBALL passages: {total} native clearance cases, all five levels and 32 door phases passed.')
