#!/usr/bin/env python3
"""world.py: decode a Robot Odyssey (Apple II) world into a readable dump and PNG maps.

    python3 -I tools/world.py --ram build/ram_robots.bin [--rooms] [--objects]
                              [--circuit] [--robots] [--text] [--png DIR]
    python3 -I tools/world.py --level 1..5 ...   (static: disk segments)

--ram IMAGE   64 KB RAM dump taken in game (a2shot peek:0000:0x10000 piped
              through dev/tools/re6502/peek2bin.py).  Everything is decoded from it.
--level N     no emulator: level 1 = world block $090 ($6000-$81FF) + the
              robots/circuit block $075 ($8200-$8ED4); levels 2-5 overlay
              their rooms+text block ($6E40-$81FF).  The object table of
              levels 2-5 is NOT on disk (objects are carried over from the
              previous level and placed by its exit code): with --level 2..5
              the objects shown are the level-1 ones, only rooms and text
              are meaningful.
--png DIR     one PNG per non-empty room (tiles + objects with their
              sprites + wires) and world.png (rooms laid out from the
              up/down/left/right links).  Stdlib only (zlib).

Layout (docs/logic/world.md): $6000 world = PC world file layout, $8618
circuit = PC circuit layout, $8200 robot tables, $8DC9 robot records.
"""
import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'dev', 'tools'))
from apple2img import png_write  # noqa: E402
ROOT = os.path.dirname(HERE)
FILES = os.path.join(ROOT, 'build', 'files', 'A_ROBOTROPOLIS')

# ----------------------------------------------------------------- tables
OBJ_NEXT, OBJ_SPRITE, OBJ_COLOR, OBJ_ROOM = 0x6000, 0x6100, 0x6200, 0x6300
OBJ_X, OBJ_Y, OBJ_MOVEDBY, OBJ_DX, OBJ_DY, OBJ_GRAB = (0x6400, 0x6500, 0x6600,
                                                       0x6700, 0x6800, 0x6900)
SPRITES = 0x6A00
ROOM_HEAD, ROOM_BG, ROOM_FG = 0x6E00, 0x6E40, 0x6E80
ROOM_UP, ROOM_DOWN, ROOM_RIGHT, ROOM_LEFT = 0x6EC0, 0x6F00, 0x6F40, 0x6F80
ROOM_TILES = 0x7000
TXT_ROOM, TXT_X, TXT_Y, TXT_STYLE = 0x7880, 0x7900, 0x7980, 0x7A00
TXT_FONT, TXT_COLOR, TXT_LO, TXT_HI = 0x7A80, 0x7B00, 0x7B80, 0x7C00
NOWHERE = 0x3F

# circuit ($8618 = offset 0 of the PC circuit structure)
W_DST, W_X1, W_X2, W_Y1, W_Y2 = 0x8618, 0x8718, 0x8818, 0x8918, 0x8A18
FF_STATE, FF_IN = 0x8AF3, 0x8B07            # indexed by object id $25-$38
N_SRC, N_DST2 = 0x8A6F, 0x8A7E              # indexed by object id $D1-$DF
N_X1, N_X2, N_Y1, N_Y2 = 0x8A8D, 0x8A9C, 0x8AAB, 0x8ABA
C_Y1, C_Y2, C_X1, C_X2, C_DST, C_PIN = 0x8B9A, 0x8BDA, 0x8C1A, 0x8C5A, 0x8C9A, 0x8CDA
GATE_TYPE = 0x8CB3                          # indexed by gate body object id
ROBOTS = 0x8DC9                             # 4 x 26 bytes, $FF after

SPRITE_NAMES = {
    0x00: 'player', 0x01: 'pin in/out L', 0x02: 'pin in/out R', 0x06: 'pin input v',
    0x07: 'AND ^', 0x08: 'AND v', 0x09: 'OR ^', 0x0A: 'OR v', 0x0B: 'XOR ^',
    0x0C: 'XOR v', 0x0D: 'NOT ^', 0x0E: 'NOT v', 0x0F: 'pin in2 v', 0x10: 'pin in2 ^',
    0x11: 'pin in3 v', 0x12: 'pin in3 ^', 0x13: 'flip-flop R', 0x14: 'flip-flop L',
    0x15: 'pin input <', 0x16: 'pin input >', 0x17: 'pin output <',
    0x18: 'pin output >', 0x19: 'node', 0x1A: 'blank', 0x1B: 'toolkit',
    0x1C: 'solder iron', 0x1D: 'solder tip', 0x1E: 'battery top', 0x1F: 'paintbrush',
    0x20: 'crystal charger', 0x29: 'chip blank / sentry', 0x2A: 'robot L',
    0x2B: 'robot R', 0x2C: 'sentry R', 0x30: 'thruster switch closed',
    0x31: 'thruster switch open', 0x32: 'sentry body', 0x33: 'keyhole',
    0x34: 'pin output ^', 0x35: 'pin output v', 0x36: 'remote control',
    0x37: 'button', 0x38: 'key', 0x39: 'crystal',
}
for _i in range(8):
    SPRITE_NAMES[0x21 + _i] = 'chip %d' % (_i + 1)

ROBOT_NAMES = ['Sparky', 'Checkers', 'Scanner', 'robot 4']
GATES = {0: '-', 1: 'AND', 2: 'OR', 3: 'XOR', 4: 'NOT'}


def object_name(o):
    """Role of object number o (fixed by the engine, see world.md)."""
    fixed = {
        0x00: 'player', 0x01: 'robot 4 L', 0x02: 'robot 4 R', 0x03: 'level object 03',
        0x04: 'level object 04', 0x09: 'robot 4 grabber in', 0x0A: 'robot 4 grabber out',
        0x0B: 'robot 4 antenna in', 0x0C: 'robot 4 antenna out',
        0x1C: 'Sparky grabber in', 0x1D: 'Checkers grabber in',
        0x1E: 'Scanner grabber in', 0x22: 'sentry L', 0x23: 'sentry R',
        0x24: 'level object 24', 0x59: 'Sparky antenna in', 0x66: 'Sparky antenna out',
        0xD0: 'Sparky grabber out', 0xE1: 'toolkit', 0xE2: 'Scanner antenna in',
        0xE3: 'Scanner antenna out', 0xE4: 'Scanner grabber out', 0xEF: 'Checkers grabber out',
        0xE5: 'Checkers antenna in', 0xE6: 'Checkers antenna out',
        0xF0: 'Sparky L', 0xF1: 'Sparky R', 0xF2: 'Checkers L', 0xF3: 'Checkers R',
        0xF4: 'Scanner L', 0xF5: 'Scanner R', 0xFC: 'remote control',
        0xFD: 'solder iron', 0xFE: 'cursor (hand)',
    }
    if o in fixed:
        return fixed[o]
    for k in range(3):
        if o == 0x0D + k:
            return 'direction sensor %d body' % (k + 1)
        if o == 0x10 + k:
            return 'room sensor %d body' % (k + 1)
        if o == 0x13 + k:
            return 'contact sensor %d body' % (k + 1)
        if o == 0x19 + k:
            return 'room sensor %d out' % (k + 1)
        if o == 0x1F + k:
            return 'contact sensor %d out' % (k + 1)
        if 0x5A + 4 * k <= o < 0x5E + 4 * k:
            return 'direction sensor %d out %d' % (k + 1, o - 0x5A - 4 * k)
    if 0x25 <= o <= 0x38:
        return 'flip-flop %d %s' % ((o - 0x25) // 2 + 1, 'L' if o & 1 else 'R')
    for base, rob in ((0x39, 'robot 4'), (0x41, 'Scanner'), (0x49, 'Checkers'), (0x51, 'Sparky')):
        if base <= o < base + 4:
            return '%s thruster %d' % (rob, o - base)
        if base + 4 <= o < base + 8:
            return '%s bumper %d' % (rob, o - base - 4)
    if 0x67 <= o <= 0xCF:
        g, r = divmod(o - 0x67, 3)
        return 'gate %d %s' % (g + 1, ('body/out', 'in 1', 'in 2')[r])
    if 0xD1 <= o <= 0xDF:
        return 'node %d' % (o - 0xD0)
    if 0xE7 <= o <= 0xEE:
        return 'chip %d' % (o - 0xE6)
    if 0xF6 <= o <= 0xFB:
        return 'level object %02X' % o
    return ''


# ----------------------------------------------------------------- image
def load_static(level):
    mem = bytearray(0x10000)

    def put(name, addr):
        # extract.py appends the segment's role: BBB_AAAA_role.bin
        path, = glob.glob(os.path.join(FILES, name[:-4] + '*.bin'))
        data = open(path, 'rb').read()
        mem[addr:addr + len(data)] = data
    put('090_6000.bin', 0x6000)
    put('075_8200.bin', 0x8200)
    if level > 1:
        blk = {2: '0AD', 3: '0C1', 4: '0D8', 5: '0EE'}[level]
        put('%s_6E40.bin' % blk, 0x6E40)
    return mem


def s8(v):
    return v - 256 if v & 0x80 else v


def tile(mem, room, col, row):
    """Tile (col 0-19 left to right, row 0-11 bottom to top): wall?"""
    r = 11 - row
    byte = mem[ROOM_TILES + 30 * room + (r >> 2) * 10 + (col >> 1)]
    return (byte >> ((col & 1) * 4 + (r & 3))) & 1


def room_objects(mem, room):
    out, o, n = [], mem[ROOM_HEAD + room], 0
    while o != 0xFF and n < 256:
        out.append(o)
        o, n = mem[OBJ_NEXT + o], n + 1
    return out


def text_of(mem, i):
    a = mem[TXT_LO + i] | mem[TXT_HI + i] << 8
    s = []
    while a < 0x10000 and mem[a] and len(s) < 400:
        c = mem[a] & 0x7F
        s.append('|' if c == 13 else chr(c) if 32 <= c < 127 else '.')
        a += 1
    return ''.join(s)


def used_rooms(mem):
    rooms = []
    for r in range(0x40):
        if any(mem[ROOM_TILES + 30 * r:ROOM_TILES + 30 * r + 30]) or mem[ROOM_HEAD + r] != 0xFF \
                or any(mem[TXT_ROOM + i] == r for i in range(0x80)):
            rooms.append(r)
    return rooms


# ----------------------------------------------------------------- dumps
def dump_rooms(mem):
    print('# Rooms (links: up down left right; bg/fg colour indices)')
    for r in used_rooms(mem):
        links = [mem[t + r] for t in (ROOM_UP, ROOM_DOWN, ROOM_LEFT, ROOM_RIGHT)]
        print('\nroom $%02X  up=$%02X down=$%02X left=$%02X right=$%02X  bg=%d fg=%d'
              % ((r,) + tuple(links) + (mem[ROOM_BG + r], mem[ROOM_FG + r])))
        for row in range(11, -1, -1):
            print('   ' + ''.join('#' if tile(mem, r, c, row) else '.' for c in range(20)))
        objs = room_objects(mem, r)
        if objs:
            print('   objects: ' + ' '.join('%02X' % o for o in objs))
        for i in range(0x80):
            if mem[TXT_ROOM + i] == r:
                print('   text %02X at (%d,%d): %s' % (i, mem[TXT_X + i], mem[TXT_Y + i], text_of(mem, i)))


def dump_objects(mem):
    print('# Objects (room $3F = nowhere); x in 2-pixel units, y upwards')
    print(' id room spr col   x   y attached(dx,dy) grab  role / sprite')
    for o in range(256):
        if mem[OBJ_ROOM + o] == NOWHERE and o not in (0,):
            continue
        mv = mem[OBJ_MOVEDBY + o]
        att = ' %02X(%+d,%+d)' % (mv, s8(mem[OBJ_DX + o]), s8(mem[OBJ_DY + o])) if mv != 0xFF else '      -     '
        print(' %02X  $%02X  %02X  %d  %3d %3d %-13s %s  %s / %s' % (
            o, mem[OBJ_ROOM + o], mem[OBJ_SPRITE + o], mem[OBJ_COLOR + o], mem[OBJ_X + o],
            mem[OBJ_Y + o], att, 'no ' if mem[OBJ_GRAB + o] else 'yes', object_name(o),
            SPRITE_NAMES.get(mem[OBJ_SPRITE + o], '?')))


def dump_text(mem):
    print('# Texts')
    for i in range(0x80):
        if mem[TXT_ROOM + i] != NOWHERE:
            print(' %02X room $%02X (%3d,%3d) style %d font %d col %d: %s' % (
                i, mem[TXT_ROOM + i], mem[TXT_X + i], mem[TXT_Y + i], mem[TXT_STYLE + i],
                mem[TXT_FONT + i], mem[TXT_COLOR + i], text_of(mem, i)))


def hot(mem, o):
    return mem[OBJ_COLOR + o] == 5


def dump_circuit(mem):
    print('# Wires (source -> destination, endpoints (x1,y1)-(x2,y2))')
    for s in range(1, 256):
        d = mem[W_DST + s]
        if d:
            print(' %02X %-28s -> %02X %-28s (%d,%d)-(%d,%d) %s' % (
                s, object_name(s), d, object_name(d), mem[W_X1 + s], mem[W_Y1 + s],
                mem[W_X2 + s], mem[W_Y2 + s], 'HOT' if hot(mem, s) else ''))
    for n in range(0xD1, 0xE0):
        if mem[N_DST2 + n]:
            print(' %02X %-28s => %02X (second output) (%d,%d)-(%d,%d)' % (
                n, object_name(n), mem[N_DST2 + n], mem[N_X1 + n], mem[N_Y1 + n],
                mem[N_X2 + n], mem[N_Y2 + n]))
    for k in range(64):
        if mem[C_DST + k]:
            print(' chip %d pin %d wire -> %02X pin %02X' % (k // 8 + 1, k % 8, mem[C_DST + k], mem[C_PIN + k]))
    print('# Gates (type at $8CB3+body)')
    for b in range(0x67, 0xD0, 3):
        t = mem[GATE_TYPE + b]
        if t or mem[OBJ_ROOM + b] != NOWHERE:
            print(' gate %2d body %02X type %s room $%02X out=%d in=%d,%d' % (
                (b - 0x67) // 3 + 1, b, GATES.get(t, t), mem[OBJ_ROOM + b], hot(mem, b),
                hot(mem, b + 1), hot(mem, b + 2)))
    print('# Flip-flops (state, input per half)')
    for o in range(0x25, 0x39, 2):
        if mem[OBJ_ROOM + o] != NOWHERE:
            print(' FF %d (%02X,%02X) room $%02X state %d/%d inputs %d/%d' % (
                (o - 0x25) // 2 + 1, o, o + 1, mem[OBJ_ROOM + o], mem[FF_STATE + o],
                mem[FF_STATE + o + 1], mem[FF_IN + o], mem[FF_IN + o + 1]))
    print('# Toolkit: %d flip-flops, %d nodes, %d gates left; closed=%d; remote=%d; tool=$%02X' % (
        mem[0x8DA8], mem[0x8DA9], mem[0x8DAA], mem[0x8DAB], mem[0x8DA7], mem[0x8DA6]))


def dump_robots(mem):
    print('# Robots ($8DC9 + 26 n)')
    for n in range(4):
        a = ROBOTS + 26 * n
        r = mem[a:a + 26]
        print(' %-8s L=%02X R=%02X room $%02X inside $%02X thrusters %s bumpers %s' % (
            ROBOT_NAMES[n], r[0], r[2], mem[OBJ_ROOM + r[0]], mem[0x8204 + n],
            ' '.join('%02X' % v for v in r[4:8]), ' '.join('%02X' % v for v in r[8:12])))
        print('          thruster anim %s bumper colour %s grabber %s battery %d switch %d acc $%02X%02X carries %02X' % (
            list(r[12:16]), list(r[16:20]), list(r[20:24]), r[24], r[25],
            mem[0x8E32 + 2 * n], mem[0x8E33 + 2 * n], mem[0x8DAD + n]))


# ----------------------------------------------------------------- png
PALETTE = {0: (0, 0, 0), 1: (200, 60, 230), 2: (60, 200, 60), 3: (255, 255, 255),
           4: (60, 200, 60), 5: (255, 120, 0), 6: (40, 120, 255), 7: (255, 255, 255),
           8: (120, 120, 120), 13: (150, 210, 255)}


def write_png(path, w, h, rgb):
    png_write(path, [bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h)])


def render_room(mem, room, scale=1):
    """280x192 image of a room: walls, objects (sprite bitmaps), wires."""
    W, H = 280, 192
    img = bytearray(W * H * 3)

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            img[(y * W + x) * 3:(y * W + x) * 3 + 3] = bytes(c)
    wall = PALETTE.get(mem[ROOM_FG + room], (150, 210, 255))
    for row in range(12):
        for col in range(20):
            if tile(mem, room, col, row):
                for yy in range(16):
                    for xx in range(14):
                        if (xx + yy) % 2 == 0:
                            px(col * 14 + xx, (11 - row) * 16 + yy, wall)

    def unit(x, y):            # object coordinate -> screen pixel
        return 2 * x, 191 - y
    for s in list(range(1, 256)):
        d = mem[W_DST + s]
        if d and mem[OBJ_ROOM + s] == room:
            line(px, unit(mem[W_X1 + s], mem[W_Y1 + s]), unit(mem[W_X2 + s], mem[W_Y2 + s]),
                 PALETTE[5] if hot(mem, s) else (200, 200, 200))
    for o in room_objects(mem, room):
        spr = mem[OBJ_SPRITE + o]
        col = PALETTE.get(mem[OBJ_COLOR + o], (255, 255, 255))
        x0, ybot = unit(mem[OBJ_X + o], mem[OBJ_Y + o])
        for r in range(16):
            bits = mem[SPRITES + 16 * spr + r]
            for b in range(7):
                if bits >> b & 1:
                    px(x0 + 2 * b, ybot - r, col)
                    px(x0 + 2 * b + 1, ybot - r, col)
    return W, H, img


def line(px, a, b, c):
    (x0, y0), (x1, y1) = a, b
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        px(x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n, c)


def world_layout(mem, rooms):
    """Grid position of each room, from a walk along the links."""
    pos, todo = {}, []
    for start in rooms:
        if start in pos:
            continue
        # new component: place to the right of everything
        base = max([p[0] for p in pos.values()], default=-2) + 2
        pos[start] = (base, 0)
        todo.append(start)
        while todo:
            r = todo.pop()
            x, y = pos[r]
            for t, dx, dy in ((ROOM_UP, 0, -1), (ROOM_DOWN, 0, 1), (ROOM_LEFT, -1, 0), (ROOM_RIGHT, 1, 0)):
                n = mem[t + r]
                if n != r and n in rooms and n not in pos and (x + dx, y + dy) not in pos.values():
                    pos[n] = (x + dx, y + dy)
                    todo.append(n)
    return pos


def write_pngs(mem, outdir, rooms):
    os.makedirs(outdir, exist_ok=True)
    tiles = {}
    for r in rooms:
        w, h, img = render_room(mem, r)
        write_png(os.path.join(outdir, 'room_%02X.png' % r), w, h, img)
        tiles[r] = img
    pos = world_layout(mem, rooms)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    gx, gy = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    tw, th = 140, 96                   # rooms halved
    W, H = gx * (tw + 4), gy * (th + 4)
    big = bytearray(W * H * 3)
    for r, (x, y) in pos.items():
        ox, oy = (x - min(xs)) * (tw + 4), (y - min(ys)) * (th + 4)
        img = tiles[r]
        for yy in range(th):
            for xx in range(tw):
                s = ((2 * yy) * 280 + 2 * xx) * 3
                d = ((oy + yy) * W + ox + xx) * 3
                big[d:d + 3] = img[s:s + 3]
        draw_hex(big, W, ox + 2, oy + 2, r)
    write_png(os.path.join(outdir, 'world.png'), W, H, big)
    return pos


DIGITS = ['111101101101111', '010110010010111', '111001111100111', '111001111001111',
          '101101111001001', '111100111001111', '111100111101111', '111001001001001',
          '111101111101111', '111101111001111', '111101111101101', '110101110101110',
          '111100100100111', '110101101101110', '111100111100111', '111100111100100']


def draw_hex(img, W, x, y, v):
    for k, d in enumerate((v >> 4, v & 15)):
        for i, ch in enumerate(DIGITS[d]):
            if ch == '1':
                for sy in range(2):
                    for sx in range(2):
                        p = ((y + (i // 3) * 2 + sy) * W + x + k * 8 + (i % 3) * 2 + sx) * 3
                        img[p:p + 3] = b'\xff\xff\x00'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--ram')
    src.add_argument('--level', type=int, choices=range(1, 6))
    for k in ('rooms', 'objects', 'circuit', 'robots', 'text'):
        ap.add_argument('--' + k, action='store_true')
    ap.add_argument('--png')
    o = ap.parse_args(argv)
    mem = bytearray(open(o.ram, 'rb').read()) if o.ram else load_static(o.level)
    mem += bytes(0x10000 - len(mem))
    every = not any((o.rooms, o.objects, o.circuit, o.robots, o.text))
    if o.rooms or every:
        dump_rooms(mem)
    if o.objects or every:
        dump_objects(mem)
    if o.text or every:
        dump_text(mem)
    if o.robots or every:
        dump_robots(mem)
    if o.circuit or every:
        dump_circuit(mem)
    if o.png:
        pos = write_pngs(mem, o.png, used_rooms(mem))
        print('# PNG: %d rooms in %s' % (len(pos), o.png), file=sys.stderr)


if __name__ == '__main__':
    main()
