#!/usr/bin/env python3
"""Pixel-reference checks of the actual native renderer on both HGR pages."""
from pathlib import Path
import random
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
import a2test

ROOT = Path(__file__).resolve().parents[2]
L = a2test.labels(ROOT / 'light3dball/build/game.lbl', strip=True)
DISK = ROOT / 'dist/LIGHT3DBALL.dsk'


def absolute(op, addr):
    return [op, addr & 255, addr >> 8]


def call(name):
    return absolute(0x20, L[name])


def write(address, data):
    return [f'poke:{address+i:04X}:{value:02X}' for i, value in enumerate(data)]


def fixture(body, clear=False):
    # Patch only this ephemeral emulator run. At the next physics entry, a
    # tiny RAM trampoline calls the production routine, then stops at its
    # normal frame marker. Repeating the trampoline avoids executing game C.
    program = []
    if clear:
        program += absolute(0xAD, L['hgr_base']) + [0x49, 0x60]
        program += absolute(0x8D, L['hgr_base']) + call('hgr_flip_rows')
        program += [0xA9, 0x55] + call('hgr_clear')
    program += body + call('frame_mark') + absolute(0x4C, 0x0400)
    return ['wait:1100', L.until('physics')] + write(0x0400, program) + \
        write(L['physics'], absolute(0x4C, 0x0400))


def paint(page, x, y, value):
    at = a2test.hgr_offset(y) + x // 7
    bit = 1 << (x % 7)
    page[at] = (page[at] | bit) if value else (page[at] & ~bit)


def check_pages(result, expected):
    previous = None
    for i, wanted in enumerate(expected):
        pages = result.mem(0x2000, 16384, i)
        selected = 0 if result.mem(L['hgr_base'], 1, i)[0] == 0x20 else 1
        actual = pages[selected*8192:(selected+1)*8192]
        assert actual == wanted, ('pixel reference mismatch', i, selected)
        if previous is not None:
            other = 1-selected
            assert pages[other*8192:(other+1)*8192] == previous[other*8192:(other+1)*8192], \
                ('other page changed', i)
        previous = pages


# Contours leave the interior untouched, including narrow one-byte rectangles,
# degenerate spans and the very last viewport row.
rects = [(0, 0, 255, 159), (7, 11, 8, 12), (2, 15, 4, 21),
         (254, 158, 255, 159), (70, 79, 70, 79), (3, 24, 201, 24)]
rng = random.Random(0x3DBA)
for _ in range(26):
    x0 = rng.randrange(256); y0 = rng.randrange(160)
    rects.append((x0, y0, rng.randrange(x0, 256), rng.randrange(y0, 160)))
steps = fixture(call('scene_rectangle'), clear=True)
expected = []
for x0, y0, x1, y1 in rects:
    steps += write(L['rect_cursor'], [0, 0x10])
    steps += [L.poke('scene_clip_left', 0), L.poke('scene_clip_right', 255)]
    for name, value in [('line_x0', x0), ('line_y0', y0), ('line_x1', x1), ('line_y1', y1)]:
        steps.append(L.poke(name, value))
    steps += [L.until('scene_rectangle'), L.until('frame_mark'), L.peek('hgr_base'), 'peek:2000:16384']
    page = bytearray([0x55] * 8192)
    for y in range(y0, y1+1):
        for x in range(x0, x1+1):
            if x in (x0, x1) or y in (y0, y1):
                paint(page, x, y, True)
    expected.append(page)
check_pages(a2test.run(DISK, steps), expected)

# The distant ball has twelve white pixels with a round 4x4 silhouette.
steps = fixture(call('hgr_msu_run') + call('clip_ball'), clear=True)
steps += write(L['hgr_ms_spr'], [L['ball4'] & 255, L['ball4'] >> 8])
steps += write(L['hgr_ms_under'], [0, 0x10])
expected = []
for phase in range(7):
    x0 = 70+phase
    steps += write(L['hgr_ms_x'], [x0, 0]) + [L.poke('hgr_ms_y', 57),
             L.poke('ball_clip_left', 0), L.poke('ball_clip_right', 255),
             L.until('hgr_msu_run'), L.until('frame_mark'), L.peek('hgr_base'), 'peek:2000:16384']
    page = bytearray([0x55] * 8192)
    for y, row in enumerate(['.##.', '####', '####', '.##.']):
        for x, pixel in enumerate(row):
            if pixel == '#':
                paint(page, x0+x, 57+y, True)
    expected.append(page)
check_pages(a2test.run(DISK, steps), expected)

# Actual missed balls must update the complete header on BOTH pages. Compare
# the numeral and its label to the font raster, catching overlapping glyphs,
# stale digits, the final zero and a reset back to four lives.
font = []
for row in (ROOT / 'dev/lib/font/bbfont_c.inc').read_text().splitlines():
    if row.lstrip().startswith('0x'):
        font.extend(int(value, 16) for value in re.findall(r'0x[0-9A-Fa-f]+', row.split('/*')[0]))
steps = ['wait:1100', L.until('frame_mark'), 'peek:2000:16384']
for _ in range(4):
    steps += [L.until('physics'), L.poke('launched', 1),
              L.poke('ball_z', 7), L.poke('ball_z', 0, 1),
              L.poke('ball_x', 192), L.poke('ball_x', 0, 1),
              L.poke('vel_x', 0), L.poke('vel_x', 0, 1),
              L.poke('vel_y', 0), L.poke('vel_y', 0, 1), L.poke('vel_z', 255),
              L.until('frame_mark'), L.until('physics'), L.until('frame_mark'),
              'peek:2000:16384', L.peek('lives')]
steps += ['key:R', L.until('physics'), L.until('frame_mark'),
          L.until('physics'), L.until('frame_mark'), 'peek:2000:16384']
r = a2test.run(DISK, steps)
for index, value in enumerate((4, 3, 2, 1, 0, 4)):
    if 1 <= index <= 4:
        assert r.mem(L['lives'], 1, index-1) == bytes([value])
    expected_header = bytearray(8192)
    for text, left in [('LIGHT3D L1 LIVES:', 7), (str(value), 168)]:
        for position, char in enumerate(text):
            glyph = font[(ord(char)-32)*8:(ord(char)-31)*8]
            for y, bits in enumerate(glyph):
                for x in range(7):
                    if bits & (1 << x):
                        paint(expected_header, left+position*8+x, 160+y, True)
    for x in range(184, 249):
        paint(expected_header, x, 163, True)
    for y in range(160, 163):
        paint(expected_header, 184, y, True)
    if value:
        for y in range(164, 167):
            paint(expected_header, 184, y, True)
    pages = r.mem(0x2000, 16384, index)
    for base in (0, 8192):
        for y in range(160, 168):
            row = a2test.hgr_offset(y)
            assert pages[base+row:base+row+40] == expected_header[row:row+40], \
                ('lives label/digit overlap or stale page', value, base, y)

# Updating many old contour histories must produce the same viewport as moving
# directly to each pose. Cross every obstacle, change the door, then return to
# the starting view; both pages include overlapping sprites and fixed rays.
def pose_steps(camera, door):
    ball=min(camera+40, 2046)
    steps = [L.until('physics'), L.poke('paused', 1), L.poke('launched', 1),
             L.poke('door_phase', door), L.poke('camera_z', camera),
             L.poke('camera_z', camera >> 8, 1), L.poke('ball_z', ball),
             L.poke('ball_z', ball >> 8, 1), L.until('frame_mark'),
             L.until('physics'), L.until('frame_mark'), 'peek:2000:16384']
    return steps


poses = [(0, 0), (32, 5), (112, 15), (120, 8), (128, 16), (240, 25),
         (248, 31), (256, 8), (368, 16), (380, 5), (384, 15),
         (500, 8), (512, 16), (1000, 24), (1024, 31), (1408, 8),
         (1536, 16), (1792, 31), (2016, 8), (0, 0)]
start = ['wait:1100', 'key:3', L.until('physics'), L.until('frame_mark')]
steps = list(start)
for pose in poses:
    steps += pose_steps(*pose)
updates = a2test.run(DISK, steps)
for index, pose in enumerate(poses):
    direct = a2test.run(DISK, start + pose_steps(*pose)).mem(0x2000, 16384)
    history = updates.mem(0x2000, 16384, index)
    for base in (0, 8192):
        for y in range(160):
            row = base+a2test.hgr_offset(y)
            assert history[row:row+40] == direct[row:row+40], ('stale contour/ray', pose, base, y)
    # HUD marker motion must leave only the current player/ball ticks on each
    # page. This also exercises HUD redraws while both markers stay still.
    camera, _ = pose
    reference = bytearray(8192)
    for x in range(184, 249):
        paint(reference, x, 163, True)
    for y in range(160, 163):
        paint(reference, 184+camera//32, y, True)
    for y in range(164, 167):
        paint(reference, 184+min(camera+40,2046)//32, y, True)
    for base in (0, 8192):
        for y in range(160, 168):
            row = a2test.hgr_offset(y)
            assert history[base+row+26:base+row+37] == reference[row+26:row+37], \
                ('depth gauge lost tick or residue', pose, base, y)

# The projection must match exact integer arithmetic for every legal world X/Y,
# at scales covering the near/far range. No approximation or drift is allowed.
steps = fixture(absolute(0xAD, 0x0700) + call('project_x') + absolute(0x8D, 0x0701) +
                absolute(0xAD, 0x0700) + call('project_y') + absolute(0x8D, 0x0702))
projected = []
for sx, sy in [(1, 1), (17, 16), (84, 49), (148, 87), (252, 148)]:
    left, top = 128-sx//2, 80-sy//2
    steps += [L.poke('sx', sx), L.poke('sy', sy), L.poke('left', left), L.poke('top', top)]
    for value in range(128):
        steps += ['poke:0700:%02X' % value, L.until('project_x'), L.until('frame_mark'), 'peek:0701:2']
        projected.append(bytes((left+value*sx//128, top+value*sy//128)))
r = a2test.run(DISK, steps)
for i, wanted in enumerate(projected):
    assert r.mem(0x0701, 2, i) == wanted, ('projection', i)

# Sphere clipping is checked from a fixed 8x8 geometric bitmap, across all
# seven byte phases, restoring the background on either side of the opening.
coverage = ['..####..', '.######.', '########', '########',
            '########', '########', '.######.', '..####..']
lit = ['........', '..####..', '.######.', '.######.',
       '.######.', '.#####..', '..###...', '........']
steps = fixture(call('hgr_msu_run') + call('clip_ball'), clear=True)
steps += write(L['hgr_ms_spr'], [L['ball8'] & 255, L['ball8'] >> 8])
steps += write(L['hgr_ms_under'], [0, 0x10])
expected = []
for phase in range(7):
    x0 = 70+phase
    for clip0, clip1 in [(0, 255), (x0+2, 255), (0, x0+3), (x0+1, x0+5), (x0+9, 255)]:
        steps += write(L['hgr_ms_x'], [x0, 0]) + [L.poke('hgr_ms_y', 57),
                 L.poke('ball_clip_left', clip0), L.poke('ball_clip_right', clip1),
                 L.until('hgr_msu_run'), L.until('frame_mark'), L.peek('hgr_base'), 'peek:2000:16384']
        page = bytearray([0x55] * 8192)
        for y in range(8):
            for x in range(8):
                if coverage[y][x] == '#' and clip0 <= x0+x <= clip1:
                    paint(page, x0+x, 57+y, lit[y][x] == '#')
        expected.append(page)
check_pages(a2test.run(DISK, steps), expected)
print('LIGHT3DBALL native renderer: projection, contours, life counters 4..0/reset on both pages and partial ball occlusion passed.')
