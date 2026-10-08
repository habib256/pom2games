#!/usr/bin/env python3
"""Packed levels, unobstructed-shot exclusion, transitions and actual campaign."""
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
import a2test

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'light3dball'
L = a2test.labels(GAME / 'build/game.lbl', strip=True)
DISK = ROOT / 'dist/LIGHT3DBALL.dsk'
LEVELS = json.loads((GAME / 'levels.json').read_text())


def polygon_clip(points, a, b, c):
    """Keep a*start_x+b*target_x >= c, using exact rational intersections."""
    result = []
    for p, q in zip(points, points[1:]+points[:1]):
        dp, dq = a*p[0]+b*p[1]-c, a*q[0]+b*q[1]-c
        if dp >= 0:
            result.append(p)
        if (dp < 0) != (dq < 0):
            t = Fraction(dp, dp-dq)
            result.append((p[0]+t*(q[0]-p[0]), p[1]+t*(q[1]-p[1])))
    return result


def opening(obstacle, phase):
    if obstacle is None:
        return 0, 127, 0
    width = obstacle['width']
    if obstacle['kind'] == 'R':
        return 0, width, 0
    if obstacle['kind'] == 'L':
        return 128-width, 127, 0
    t = (phase+2*obstacle['phase']) & 31
    left = 8+4*(t if t < 16 else 31-t)
    return left, left+width, 1


def word(value):
    return list((value & 65535).to_bytes(2, 'little'))


def write(address, values):
    return [f'poke:{address+i:04X}:{value:02X}' for i, value in enumerate(values)]


for index, level in enumerate(LEVELS):
    assert level['length'] == [1536, 1792, 2048, 2560, 3072][index]
    obstacles = level['obstacles']
    assert len(obstacles) == [8, 10, 12, 14, 18][index]
    assert len([o for o in obstacles if o['kind'] == 'D']) == [0, 0, 3, 0, 4][index]
    assert obstacles[-1]['z'] == level['length']-256
    assert all(o['z'] % 128 == 0 and 0 < o['z'] < level['length'] for o in obstacles)
    assert len({o['z'] for o in obstacles}) == len(obstacles)
    # At most two doors in the four-slot horizon: six rectangles plus back
    # wall/target need at most 32 contour records per page.
    doors = {o['z']//128-1 for o in obstacles if o['kind'] == 'D'}
    assert max(sum(slot in doors for slot in range(first, first+4))
               for first in range(24)) <= 2
    polygon = [(Fraction(x), Fraction(y)) for x, y in [(0, 56), (127, 56), (127, 72), (0, 72)]]
    for obstacle in obstacles:
        if obstacle['kind'] == 'D':
            continue  # fixed walls alone must block every possible straight shot
        left, right, _ = opening(obstacle, 0)
        z, length = obstacle['z']-2, level['length']-2
        polygon = polygon_clip(polygon, length-z, z, (left+2)*length)
        polygon = polygon_clip(polygon, -(length-z), -z, -(right-2)*length)
        if not polygon:
            break
    assert not polygon, ('direct shot possible', index+1)

# Inspect native opening() for every grid cell and representative door phases.
for index, level in enumerate(LEVELS):
    obstacles = {o['z']//128-1:o for o in level['obstacles']}
    body = [0xAD,0,7,0x20,L['opening']&255,L['opening']>>8,
            0x20,L['frame_mark']&255,L['frame_mark']>>8,0x4C,0,4]
    steps = ['wait:1100', f'key:{index+1}', L.until('physics'), L.until('frame_mark'),
             L.peek('level_length',2), L.peek('level_slots')]
    steps += write(0x0400,body) + write(L['physics'], [0x4C,0,4])
    expected = []
    for slot in range(level['length']//128):
        obstacle=obstacles.get(slot)
        phases=range(32) if obstacle and obstacle['kind']=='D' else (0,)
        for phase in phases:
            steps += ['poke:0700:%02X'%slot, L.poke('door_phase',phase),
                      L.until('opening'), L.until('frame_mark'),
                      L.peek('plane',2), L.peek('aperture_l'), L.peek('aperture_r'), L.peek('aperture_moving')]
            expected.append((slot, opening(obstacles.get(slot),phase)))
    r = a2test.run(DISK,steps)
    assert int.from_bytes(r.mem(L['level_length'],2),'little') == level['length']
    assert r.mem(L['level_slots'],1) == bytes([level['length']//128])
    for occurrence,(slot,values) in enumerate(expected):
        assert r.mem(L['plane'],2,occurrence) == bytes(word((slot+1)*128))
        for name,value in zip(('aperture_l','aperture_r','aperture_moving'),values):
            assert r.mem(L[name],1,occurrence) == bytes([value]), (index,slot,name,values)

# Campaign progression requires a target hit, then a deliberate new input.
steps = ['wait:1100', L.until('frame_mark')]
for index,level in enumerate(LEVELS):
    steps += [L.until('physics'), L.poke('launched',1), L.poke('advancing',0),
              L.poke('vel_z',1)]
    for name,value in [('camera_z',level['length']-256), ('ball_z',level['length']-3),
                       ('ball_x',1024), ('ball_y',1024), ('vel_x',0), ('vel_y',0)]:
        steps += write(L[name],word(value))
    steps += [L.until('frame_mark'), L.until('physics'), L.until('frame_mark'),
              L.peek('won'),L.peek('level')]
    if index < 4:
        steps += ['key:\\r',L.until('physics'),L.until('frame_mark'),L.peek('level'),L.peek('camera_z',2)]
steps += ['key:R',L.until('physics'),L.until('frame_mark'),L.peek('won'),L.peek('level')]
r = a2test.run(DISK,steps)
for index in range(5):
    assert r.mem(L['won'],1,index) == b'\x01'
    assert r.mem(L['level'],1,2*index if index<4 else 8) == bytes([index])
    if index < 4:
        assert r.mem(L['level'],1,2*index+1) == bytes([index+1])
        assert r.mem(L['camera_z'],2,index) == b'\0\0'
assert r.mem(L['won'],1,5) == b'\0' and r.mem(L['level'],1,9) == b'\0'

# Complete all five levels by steering only simulated mouse input. The
# production ball, lives, obstacles, timing and win conditions stay intact.
with tempfile.TemporaryDirectory(prefix='light3d-pilot-') as tmp:
    work = Path(tmp)
    names = ['frame_mark','mouse_enabled','mouse_poll','mouse_x','mouse_y','mouse_buttons',
             'level','level_length','level_slots','door_phase','level_maps','lives','won',
             'launched','camera_z','ball_x','ball_y','ball_z','vel_x','vel_y','vel_z']
    (work/'game_labels.h').write_text(''.join(f'#define {n.upper()} 0x{L[n]:04X}\n' for n in names))
    native = ROOT/'dev/tools/a2run'
    pilot = work/'pilot'
    subprocess.run(['cc','-O2','-std=c99','-DA2RUN_LIB','-I'+str(native),'-I'+str(work),
                    str(GAME/'tests/pilot.c'),str(native/'a2run.c'),str(native/'cpu6502.c'),
                    '-lz','-o',str(pilot)],check=True)
    r = subprocess.run([str(pilot),str(DISK),str(ROOT/'dev/tools/a2shot/roms')],
                       capture_output=True,text=True,timeout=120)
    print(r.stdout,end='')
    assert r.returncode == 0, r.stdout+r.stderr
print('LIGHT3DBALL levels: all layouts, no direct shots, moving doors, progression and actual five-level campaign passed.')
