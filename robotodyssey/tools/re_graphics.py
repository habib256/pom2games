#!/usr/bin/env python3
"""re_graphics.py: export Robot Odyssey I's graphics and room texts (ignored build/).

Reads the local disk images build/<side>.po (ProDOS block order, made by
extract.py) and the resident module's loader descriptors; nothing original is
embedded here. Outputs:
  build/original_graphics/  PNG fonts, sprites, room maps, pictures + manifest.json
  build/texts/              room texts of every world (UTF-8)
See docs/logic/graphics.md for the formats and the engine routines mirrored here.

  python3 -I tools/re_graphics.py                 export everything
  python3 -I tools/re_graphics.py --verify RAM.bin  redraw the room held in a
        64 KB RAM dump (a2shot peek) and compare with its displayed HGR page
"""
import argparse, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
from loadcalls import calls  # noqa: E402
import apple2img  # noqa: E402
from apple2img import WHITE, BLACK  # noqa: E402

SIDES = {'A': 'A_ROBOTROPOLIS', 'B': 'B_LABS', 'C': 'C_TUTORIAL'}

# ---------------------------------------------------------------- disk / memory

def po(side):
    return (HERE / 'build' / f'{SIDES[side]}.po').read_bytes()


def resident():
    """64 KB image with the resident module (blocks $030-$038 at $4000)."""
    m = bytearray(0x10000)
    r = po('A')[0x30 * 512:0x39 * 512]
    m[0x4000:0x4000 + len(r)] = r
    return m


LOADS = {a: ds for a, cmd, ds in calls(resident(), 0x4000, 0x5200) if cmd == 1}


def load(mem, side, call, skip_zero=True):
    """Apply loader call `call` (address of its JSR $4B03) from disk side."""
    d = po(side)
    for _, blk, ad, ln in LOADS[call]:
        if blk == 0 and skip_zero:
            continue
        mem[ad:ad + ln] = d[blk * 512:blk * 512 + ln]
    return mem


# Worlds = memory states holding a room table set. (side, calls applied in
# order, name). Levels 2-5 only reload $6E40-$81FF (+ code/data) over level 1.
ENGINE = 0x45EF          # 05B $9500 engine, 072, 075, 07C, 080, 088
WORLDS = [
    ('A', (ENGINE, 0x4602), 'robotropolis_level1'),
    ('A', (ENGINE, 0x4602, 0x40B6), 'robotropolis_level2'),
    ('A', (ENGINE, 0x4602, 0x40C2), 'robotropolis_level3'),
    ('A', (ENGINE, 0x4602, 0x40CE), 'robotropolis_level4'),
    ('A', (ENGINE, 0x4602, 0x40DA), 'robotropolis_level5'),
    ('B', (0x45D5,), 'preview_45D5'),
    ('B', (0x4630,), 'innovation_lab_4630'),
    ('B', (0x46A6,), 'chip_design_46A6'),
    ('C', (0x4590, 0x4662), 'tutorial_1'),
    ('C', (0x4590, 0x466E), 'tutorial_2'),
    ('C', (0x4590, 0x467A), 'tutorial_3'),
    ('C', (0x4590, 0x4684), 'tutorial_4'),
    ('C', (0x4590, 0x4690), 'tutorial_5'),
    ('C', (0x4590, 0x469C), 'tutorial_6'),
]


def world_mem(side, seq):
    m = resident()
    for c in seq:
        load(m, side, c)
    return m

# ---------------------------------------------------------------- HGR helpers

def line_addr(line, page=1):
    """Address of HGR line 0..191 (top = 0) on page 1 ($2000) or 2 ($4000)."""
    return 0x2000 * page + (line & 7) * 0x400 + ((line >> 3) & 7) * 0x80 + (line >> 6) * 0x28


def gline(y):
    """Game Y (0 = bottom, table $9839/$98F9/$99B9) -> HGR line."""
    return 191 - y


def page_bytes(mem, page):
    return mem[0x2000 * page:0x2000 * page + 0x2000]


# NTSC artefact model: dev/tools/apple2img.hgr_to_rgb.


def hgr_rgb(mem, page=1, base=None):
    """Render an HGR page to 280x192 RGB rows (one tuple per pixel)."""
    base = 0x2000 * page if base is None else base
    return apple2img.hgr_to_rgb(mem[base:base + 0x2000])


def png(path, rows, scale=(1, 1), alpha=False):
    """Write rows of RGB(A) tuples to PNG, scaled by integer (sx, sy)."""
    apple2img.png_write(path, rows, scale, 'rgba' if alpha else 'rgb')


def sheet(cells, cols, gap=1, bg=(40, 40, 40)):
    """Tile equally sized RGB cell images into one sheet."""
    ch, cw = len(cells[0]), len(cells[0][0])
    nrows = (len(cells) + cols - 1) // cols
    out = [[bg] * (cols * (cw + gap) + gap) for _ in range(nrows * (ch + gap) + gap)]
    for k, cell in enumerate(cells):
        oy, ox = gap + (k // cols) * (ch + gap), gap + (k % cols) * (cw + gap)
        for y in range(ch):
            out[oy + y][ox:ox + cw] = cell[y]
    return out

# ---------------------------------------------------------------- engine mirrors
# Engine tables (segment $05B at $9500, same bytes on the three sides).
FONT = 0x9460          # room font: row r (0 = bottom) of char c at FONT + r*$60 + c
XBYTE, XSHIFT = 0x9B05, 0x9A79   # game X (0-139, 2 pixels) -> byte column, bit shift
COLOURS = (0x9B91, 0x9BB1, 0x9BD1, 0x9BF1)   # 32 colour entries x 4 pattern bytes
BIGCOL = (0xA4B9, 0xA4C1)                    # 8 colours for the large text
REVERSE = 0xA4C9                             # bit reversal table


def draw_background(mem, room, page):
    """$9D03 -> $9CD0 + $B450 (page 1) / $B6B8 (page 2): 20x12 cells of 14x16."""
    bitmap = mem[0x7000 + 30 * room:0x7000 + 30 * room + 30]
    cx, cy = mem[0x6E40 + room], mem[0x6E80 + room]
    c3f = [mem[t + cx] for t in COLOURS]     # $9C3F-$9C42: bit 0 cells
    c43 = [mem[t + cy] for t in COLOURS]     # $9C43-$9C46: bit 1 cells
    # $B496-$B4A1 interleave
    t = [c3f[0], c43[0], c3f[1], c43[1], c3f[2], c43[2], c3f[3], c43[3],
         c3f[0], c43[0], c3f[1], c43[1]]
    for i in range(30):
        v = bitmap[i]
        for h in (0, 1):
            x = 4 * i + 2 * h
            third, col = divmod(x, 40)
            for q in range(4):
                y = 4 * h + (v & 1)
                v >>= 1
                if t[y] == 0xF0:
                    continue
                for j in range(16):
                    a = line_addr(third * 64 + q * 16 + j, page)
                    odd = 4 if j & 1 else 0
                    mem[a + col] = t[y + odd]
                    mem[a + col + 1] = t[y + 2 + odd]
    return bitmap, cx, cy


def draw_sprite(mem, page, x, y, rows, c0, c1):
    """$AF1F: 16 rows (row 0 = bottom), 7 pixels b6..b0 each 2 HGR pixels wide."""
    if x >= 0x86 or y >= 0xB1:
        return
    col0, shift = mem[XBYTE + x], mem[XSHIFT + x]
    for k, v in enumerate(rows[:16]):
        if not v:
            continue
        a = line_addr(gline(y + k), page)
        masks = [0x80, 0x80, 0x80]
        for i in range(7):
            if v >> (6 - i) & 1:
                for p in (shift + 2 * i, shift + 2 * i + 1):
                    masks[p // 7] |= 1 << (p % 7)
        nbytes = 2 if shift == 0 else 3
        for b in range(nbytes):
            col = col0 + b
            colour = c0 if col % 2 == 0 else c1
            mem[a + col] = (mem[a + col] & ~masks[b] & 0xFF) | (masks[b] & colour)
        if shift == 0 and col0 + 2 < 40 and mem[a + col0 + 2] == 0:
            mem[a + col0 + 2] = 0x80 & (c0 if (col0 + 2) % 2 == 0 else c1)


def text_string(mem, ptr, limit=1024):
    out = bytearray()
    while len(out) < limit and mem[ptr]:
        out.append(mem[ptr])
        ptr += 1
    return bytes(out)


def draw_text_small(mem, page, x, y, ptr):
    """$A2FA: font ORed byte-aligned; $A0 space, $00 end, other < $A0 newline (y-9)."""
    col = mem[XBYTE + x] if x < 0x8C else -mem[XBYTE + ((-x) & 0xFF)]
    c = col
    while True:
        if y >= 0xB9:
            return
        ch = mem[ptr]
        ptr += 1
        if ch == 0:
            return
        if ch == 0xA0:
            c += 1
        elif ch > 0xA0:
            if 0 <= c < 0x28:
                for r in range(8):
                    a = line_addr(gline(y + r), page) + c
                    mem[a] |= mem[FONT + r * 0x60 + ch]
            c += 1
        else:
            y -= 9
            c = col


def draw_text_big(mem, page, x, y, ptr, colour):
    """$A3E1: glyphs doubled (16 rows, 2-pixel dots) drawn by $AF1F in a colour."""
    c0, c1 = mem[BIGCOL[0] + colour], mem[BIGCOL[1] + colour]
    x0 = x
    while True:
        ch = mem[ptr]
        ptr += 1
        if ch == 0:
            return
        if ch == 0x8D:
            x = x0
            y = (y - 0x12) & 0xFF
            continue
        if ch != 0xA0 and x < 0x86 and y < 0xB1:
            rows = []
            for r in range(8):
                v = mem[REVERSE + mem[FONT + r * 0x60 + ch]] >> 1
                rows += [v, v]
            draw_sprite(mem, page, x, y, rows, c0, c1)
        x = (x + 7) & 0xFF


TEXTS = (0x7880, 0x7900, 0x7980, 0x7A00, 0x7A80, 0x7B00, 0x7B80, 0x7C00)


def room_texts(mem):
    """Text table $7880-$7C7F (128 entries), read by $A2A2."""
    out = []
    for i in range(128):
        room, x, y, kind, unk, colour = (mem[t + i] for t in TEXTS[:6])
        ptr = mem[0x7B80 + i] | mem[0x7C00 + i] << 8
        out.append(dict(index=i, room=room, x=x, y=y, kind=kind, field_7A80=unk,
                        colour=colour, ptr=ptr))
    return out


def draw_texts(mem, room, page):
    for t in room_texts(mem):
        if t['room'] != room:
            continue
        if t['kind'] == 0:
            draw_text_small(mem, page, t['x'], t['y'], t['ptr'])
        elif t['kind'] == 2:
            draw_text_big(mem, page, t['x'], t['y'], t['ptr'], t['colour'])


def sprite_rows(mem, gid):
    a = 0x6A00 + 16 * gid
    return list(mem[a:a + 16])


def draw_objects(mem, room, page):
    """$9D18: linked list head $6E00[room], next $6000[obj]; graphic $6100,
    colour $6200, X $6400, Y $6500."""
    o, n, drawn = mem[0x6E00 + room], 0xFF, []
    while o != 0xFF and n:
        g, colour, x, y = mem[0x6100 + o], mem[0x6200 + o], mem[0x6400 + o], mem[0x6500 + o]
        draw_sprite(mem, page, x, y, sprite_rows(mem, g), mem[COLOURS[0] + colour],
                    mem[COLOURS[1] + colour])
        drawn.append(dict(obj=o, graphic=g, colour=colour, x=x, y=y))
        o = mem[0x6000 + o]
        n -= 1
    return drawn


def render_room(mem, room, page=1, objects=True):
    draw_background(mem, room, page)
    draw_texts(mem, room, page)
    return draw_objects(mem, room, page) if objects else []

# ---------------------------------------------------------------- menu / intro pictures
# Script interpreter at $0986 (menu code, block $039 at $0803, entered by
# JSR $0803 followed by inline byte code). Operand byte counts per opcode.
SCRIPT_OPS = {0: ('PICTURE', 2), 1: ('DISSOLVE', 0), 2: ('NATIVE', 0), 3: ('CALL', 3),
              4: ('KEYABORT_ON', 0), 5: ('KEYABORT_OFF', 0), 6: ('XORBLIT', 4),
              7: ('CLEARHGR', 0), 8: ('ABORTVEC', 2), 9: ('TUNE', 2), 10: ('TEMPO', 1)}


def script(mem, a):
    """Decode one inline script (after a JSR $0803) up to NATIVE."""
    out = []
    while mem[a] in SCRIPT_OPS:
        name, n = SCRIPT_OPS[mem[a]]
        args = list(mem[a + 1:a + 1 + n])
        out.append((a, name, args))
        a += 1 + n
        if name == 'NATIVE':
            break
    return out


def word(args, i=0):
    return args[i] | args[i + 1] << 8


def draw_picture(mem, ptr, base=None):
    """$0A74: tiled picture. Header (16 bytes): rows, cols, page hi, start row,
    start column, 8, 0, ?, BE offset of tile set 2, BE offset of the map, BE
    map length. Tiles = 8 bytes (line 0-7) from set 1 at ptr+$10 or set 2.
    The map runs down columns: tile index, $FF n t (n times t), $FE k (next
    column; k > 1 = repeat the column just ended k times), $FD end,
    $FC / $FB select tile set 2 / 1."""
    h = mem[ptr:ptr + 16]
    page = h[2] if base is None else base
    set1 = ptr + 0x10
    set2 = set1 + (h[8] << 8 | h[9])
    pos = set2 + (h[10] << 8 | h[11])
    start = pos
    r0, c = h[3], h[4]
    r = r0
    tb = set1                  # ($FB/$FC); the code leaves it from the last run
    count, saved_pos, saved_hi = 1, pos, tb >> 8
    tiles = 0

    def put(t):
        nonlocal r, tiles
        a = (tb + t * 8) & 0xFFFF
        for y in range(8):
            line = r * 8 + y
            mem[(page << 8) + line_addr(line, 1) - 0x2000 + c] = mem[a + y]
        r += 1
        tiles += 1

    def rd():
        nonlocal pos
        pos += 1
        return mem[pos - 1]
    while True:
        t = rd()
        if t == 0xFD:
            break
        if t == 0xFC:
            tb = set2
        elif t == 0xFB:
            tb = set1
        elif t == 0xFF:
            n = rd() or 256
            t2 = rd()
            for _ in range(n):
                put(t2)
        elif t == 0xFE:
            r = r0
            c += 1
            k = rd()
            if k == 1 or k == count:
                count = 1
                saved_pos, saved_hi = pos, tb >> 8
            else:
                count += 1
                pos = saved_pos
                tb = (saved_hi << 8) | (tb & 0xFF)   # only $FC is restored
        else:
            put(t)
    return dict(rows=h[0], cols=h[1], page=f'${page:02X}00', row=r0, col=h[4],
                tiles_set1=(set2 - set1) // 8, map_bytes=pos - start, size=pos - ptr,
                tiles_drawn=tiles)


def xor_blit(mem, ptr, line, col, page=0x20):
    """$0D24: bitmap of [3] bytes x [4] lines from ptr+5, EORed (| $80)."""
    w, h = mem[ptr + 3], mem[ptr + 4]
    p = ptr + 5
    for y in range(h):
        a = (page << 8) + line_addr(line + y, 1) - 0x2000
        for x in range(w):
            mem[a + col + x] = (mem[a + col + x] ^ mem[p]) | 0x80
            p += 1
    return w, h


def blit_rgb(mem, ptr):
    """Bitmap of a XOR blit rendered alone (colour model on black)."""
    w, h = mem[ptr + 3], mem[ptr + 4]
    m = bytearray(mem)
    m[0x2000:0x4000] = bytes(0x2000)
    xor_blit(m, ptr, 0, 0)
    rows = hgr_rgb(m, 1)
    return [r[:w * 7] for r in rows[:h]]

PRINT_AT = {0x4913: 'clear+at', 0x491E: 'at', 0x4920: 'cont'}


def export_prompts(txtdir, manifest):
    """Inline strings of the resident module ($4000-$51FF): JSR $4913 (clear
    HGR, row A, column Y), $491E (row A, column Y) or $4920 (continue),
    followed by low ASCII ending at the first byte with bit 7 set, printed by
    the $0300 driver. Control codes kept as <$xx>. Only strings right after
    such a JSR are found (words inserted by code, e.g. $4973 'game'/'lab',
    are listed as separate fragments)."""
    m = resident()
    out = []
    for a in range(0x4000, 0x5200 - 3):
        if m[a] != 0x20 or (m[a + 1] | m[a + 2] << 8) not in PRINT_AT:
            continue
        p, s = a + 3, []
        while p < 0x5200:
            c = m[p]
            s.append(c & 0x7F)
            p += 1
            if c & 0x80:
                break
        txt = ''.join(chr(c) if 32 <= c < 127 else ('\n' if c == 13 else f'<${c:02X}>') for c in s)
        out.append(f'## ${a:04X} {PRINT_AT[m[a + 1] | m[a + 2] << 8]}\n{txt}\n')
    (txtdir / 'resident_prompts.txt').write_text(
        '# Resident module prompts (blocks $030-$038, identical on the three sides)\n\n'
        + '\n'.join(out), encoding='utf-8')
    manifest['resident_prompts'] = len(out)

# ---------------------------------------------------------------- text decoding

# Room font glyphs that differ from ASCII (checked on the bitmaps).
GLYPHS = {'`': '\u201c', '"': '\u201d', '^': '\u25cf', '{': '\u2190', '}': '\u2192',
          '~': '\u2191', '\x7f': '\u2193'}


def decode_text(raw):
    """Room text bytes -> UTF-8 (high ASCII; codes $01-$9F = line break; GLYPHS)."""
    out = []
    for c in raw:
        if c < 0xA0:
            out.append('\n')
        else:
            ch = chr(c & 0x7F)
            out.append(GLYPHS.get(ch, ch))
    return ''.join(out)

# ---------------------------------------------------------------- exports

def glyph_rgb(mem, ch, fg=WHITE, scale=1):
    rows = []
    for r in range(7, -1, -1):
        v = mem[FONT + r * 0x60 + ch]
        rows.append([fg if v >> i & 1 else BLACK for i in range(7)])
    return rows


def sprite_rgb(rows, fg=WHITE):
    img = []
    for v in reversed(rows):
        line = []
        for i in range(7):
            p = fg if v >> (6 - i) & 1 else BLACK
            line += [p, p]
        img.append(line)
    return img


def export_fonts(mem, out, manifest):
    cells = [glyph_rgb(mem, c) for c in range(0xA0, 0x100)]
    png(out / 'font_room_7x8.png', sheet(cells, 16), (4, 4))
    big = []
    for c in range(0xA0, 0x100):
        rows = []
        for r in range(8):
            v = mem[REVERSE + mem[FONT + r * 0x60 + c]] >> 1
            rows += [v, v]
        big.append(sprite_rgb(rows))
    png(out / 'font_room_large_14x16.png', sheet(big, 16), (2, 2))
    manifest['fonts'].update({
        'font_room_7x8.png': {'address': '$9500-$97FF', 'segment': 'block $05B +$0000',
                              'chars': '$A0-$FF (ASCII $20-$7F)', 'cell': '7x8, row 0 = bottom'},
        'font_room_large_14x16.png': {'routine': '$A3E1', 'derived_from': 'font_room_7x8',
                                      'cell': '14x16 (doubled)'}})


def world_sprites(mem):
    return [sprite_rows(mem, g) for g in range(64)]


def export_world(name, side, seq, out, txtdir, manifest, shot_rooms):
    mem = world_mem(side, seq)
    # levels 2-5 reload only $6E40-$81FF: the object table $6000-$69FF is
    # the level 1 one here, so their maps are drawn without objects
    objects = not name.startswith('robotropolis_level') or name.endswith('1')
    w = {'side': SIDES[side], 'loader_calls': [f'${c:04X}' for c in seq],
         'objects_drawn': objects}
    # texts
    texts = room_texts(mem)
    lines, used, rejected = [], [], []
    for t in texts:
        if t['room'] == 0xFF:
            continue
        raw = text_string(mem, t['ptr'])
        if not raw:
            continue
        if not all(c >= 0xA0 or c == 0x8D for c in raw):
            rejected.append(t['index'])
            continue
        used.append(t)
        kind = {0: 'small', 2: 'large'}.get(t['kind'], f'kind{t["kind"]}')
        lines.append(f'## text {t["index"]} room {t["room"]} x={t["x"]} y={t["y"]} '
                     f'{kind} colour={t["colour"]} @${t["ptr"]:04X}\n{decode_text(raw)}\n')
    (txtdir / f'{name}.txt').write_text(f'# {name} ({SIDES[side]}, loader calls '
                                        f'{", ".join(w["loader_calls"])}); slots skipped as non-text: '
                                        f'{rejected}\n\n' + '\n'.join(lines),
                                        encoding='utf-8')
    w['texts'] = len(used)
    w['text_entries_rejected'] = rejected   # pointer to non-text bytes (unused slots)
    # sprites
    spr = world_sprites(mem)
    png(out / f'{name}_sprites.png', sheet([sprite_rgb(r) for r in spr], 16), (3, 3))
    w['sprites'] = '64 x 16 bytes at $6A00'
    # rooms: background + texts + objects at their initial place
    rooms = sorted({t['room'] for t in used if t['room'] < 64} | set(range(64)))
    cells = []
    for room in rooms:
        m2 = bytearray(mem)
        m2[0x2000:0x4000] = bytes(0x2000)
        render_room(m2, room, 1, objects)
        cells.append(hgr_rgb(m2, 1))
    png(out / f'{name}_rooms.png', sheet(cells, 8, gap=4), (1, 1))
    for room in shot_rooms:
        m2 = bytearray(mem)
        m2[0x2000:0x4000] = bytes(0x2000)
        render_room(m2, room, 1, objects)
        png(out / f'{name}_room{room:02d}.png', hgr_rgb(m2, 1), (2, 2))
    w['rooms_sheet'] = f'{name}_rooms.png (64 rooms, 8 per row, room 0 top left)'
    manifest['worlds'][name] = w
    return mem


def play_scripts(mem, starts, out, prefix, manifest_key, manifest, skip_blits=False):
    """Run the drawing ops of scripts, saving a PNG at each visible change."""
    info = {'scripts': {}, 'pictures': {}, 'blits': {}, 'frames': []}
    shown = set()
    frame = 0
    for s in starts:
        ops = script(mem, s)
        info['scripts'][f'${s:04X}'] = [f'{a:04X} {n} ' + ' '.join(f'{v:02X}' for v in args)
                                        for a, n, args in ops]
        for a, name, args in ops:
            snap = None
            if name == 'CLEARHGR':
                mem[0x2000:0x4000] = bytes(0x2000)
            elif name == 'PICTURE':
                p = word(args)
                d = draw_picture(mem, p)
                info['pictures'][f'${p:04X}'] = d
                # the picture alone, on black, from a scratch copy
                m2 = bytearray(mem)
                base = int(d['page'][1:3], 16)
                m2[base << 8:(base << 8) + 0x2000] = bytes(0x2000)
                draw_picture(m2, p)
                png(out / f'{prefix}_picture_{p:04X}.png', hgr_rgb(m2, base=base << 8), (2, 2))
                if base == 0x20:
                    snap = f'picture ${p:04X}'
            elif name == 'DISSOLVE':
                mem[0x2000:0x4000] = mem[0xD000:0xF000]
                snap = 'dissolve $D000 -> page 1'
            elif name == 'XORBLIT' and not skip_blits:
                p, line, col = word(args), args[2], args[3]
                w, h = xor_blit(mem, p, line, col)
                if p not in info['blits']:
                    png(out / f'{prefix}_blit_{p:04X}.png', blit_rgb(mem, p), (2, 2))
                info['blits'][f'${p:04X}'] = {'width_bytes': w, 'lines': h}
                key = (p, line, col)
                if key in shown:
                    shown.discard(key)
                else:
                    shown.add(key)
                    snap = f'xor ${p:04X} at line {line} col {col}'
            if snap:
                frame += 1
                png(out / f'{prefix}_frame{frame:02d}.png', hgr_rgb(mem, 1), (2, 2))
                info['frames'].append(f'{prefix}_frame{frame:02d}.png: {snap} (script op at ${a:04X})')
    manifest[manifest_key] = info
    return info


# Script sequences: (name, side, loader calls, script starts). The interpreter
# (block $039) is the same on the three sides; only side A carries scripts.
SEQUENCES = [
    ('menu', 'A', (0x4070,), (0x6029,)),                 # 03C script, 03E pictures
    ('intro', 'A', (0x456D,), (0x6003, 0x60AC)),         # 008 script, 009 pictures
    ('ending_40F0', 'A', (0x4070, 0x40F0), (0x6003, 0x6072)),  # 02E script, 009 pictures
]


def export_sequences(out, manifest):
    for name, side, seq, starts in SEQUENCES:
        mem = world_mem(side, seq)
        # ending_40F0: its XORBLIT operand $6200 lies outside the data it loads
        # (probably patched at run time, uncertain) -> pictures only
        info = play_scripts(mem, starts, out, name, name, manifest,
                            skip_blits=(name == 'ending_40F0'))
        info['source'] = f'{SIDES[side]} loader calls ' + ', '.join(f'${c:04X}' for c in seq)
    # menu selection frame: XOR blit $6300 of block $03E (script at $60B4)
    mem = world_mem('A', (0x4070,))
    png(out / 'menu_blit_6300.png', blit_rgb(mem, 0x6300), (2, 2))


def export_prompt_font(out, manifest):
    """Monospace 7x8 font of the HGR text driver at $0300 (text-page RAM).
    Disk: track 0, ProDOS blocks 6-7 (+$C00-$EFF of the image) -> $5C00-$5EFF
    at boot -> $0500-$07FF; glyph c ($20-$7F) at ((c|$80)>>5)*256 + (c&$1F)*8,
    row 0 = top. Glyphs $xF (screen holes) are moved to $04B8+(c&$70)/2."""
    d = po('A')
    cells = []
    for c in range(0x20, 0x80):
        a = ((c | 0x80) >> 5) << 8 | (c & 0x1F) * 8
        rows = d[0xB00 + a - 0x400:0xB00 + a - 0x400 + 8]
        cells.append([[WHITE if v >> i & 1 else BLACK for i in range(7)] for v in rows])
    png(out / 'font_prompt_7x8.png', sheet(cells, 16), (4, 4))
    manifest['fonts']['font_prompt_7x8.png'] = {
        'address': '$0500-$07FF (+$04B8-$04F7)', 'disk': 'track 0, image offset $C00-$EFF',
        'routine': '$0300 (char in A), inline strings via $4913/$491E/$4920',
        'chars': '$20-$7F', 'cell': '7x8, row 0 = top'}


def export_engine_sprites(out, manifest):
    """Robot parts etc.: 16-byte sprites of block $075 ($8200) used by the LC code."""
    mem = world_mem('A', (ENGINE,))
    cells = [sprite_rgb(list(mem[a:a + 16])) for a in range(0x8440, 0x8560, 16)]
    png(out / 'engine_sprites_8440.png', sheet(cells, 6), (3, 3))
    manifest['engine_sprites'] = {'file': 'engine_sprites_8440.png',
                                  'range': '$8440-$855F (18 x 16 bytes, block $075)',
                                  'known_users': '$84C0-$8550 robot parts, $D2BC-$D830'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=HERE / 'build/original_graphics')
    ap.add_argument('--texts', type=Path, default=HERE / 'build/texts')
    ap.add_argument('--verify', type=Path, help='64 KB RAM dump to check a room redraw against')
    ap.add_argument('--only-pictures', action='store_true', help='menu/intro pictures only (fast)')
    args = ap.parse_args()
    if args.verify:
        return verify(args.verify)
    args.out.mkdir(parents=True, exist_ok=True)
    args.texts.mkdir(parents=True, exist_ok=True)
    manifest = {'sources': {s: hashlib.sha256(po(s)).hexdigest() for s in SIDES}, 'worlds': {}}
    manifest['fonts'] = {}
    export_sequences(args.out, manifest)
    export_prompt_font(args.out, manifest)
    export_engine_sprites(args.out, manifest)
    export_prompts(args.texts, manifest)
    if args.only_pictures:
        (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        return 0
    for side, seq, name in WORLDS:
        mem = export_world(name, side, seq, args.out, args.texts, manifest,
                           [40] if name == 'robotropolis_level1' else [])
        if name == 'robotropolis_level1':
            export_fonts(mem, args.out, manifest)
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{len(manifest["worlds"])} worlds -> {args.out}, {args.texts}')


def verify(path):
    ram = bytearray(path.read_bytes().ljust(0x10000, b'\0'))
    shown = 1 if ram[0x9C47] == 0 else 2          # $AEED: $9C47=0 -> $C054 page 1
    room = ram[0x6300]                             # player's room ($9C2D copy)
    m = bytearray(ram)
    m[0x2000 * shown:0x2000 * shown + 0x2000] = bytes(0x2000)
    drawn = render_room(m, room, shown)
    a, b = page_bytes(ram, shown), page_bytes(m, shown)
    diff = [i for i in range(0x2000) if a[i] != b[i] and (i & 0x7F) < 0x78]
    print(f'room {room}, page {shown}: {len(drawn)} objects; {len(diff)} of 7680 bytes differ')
    lines = sorted({next(l for l in range(192) if 0 <= i - (line_addr(l, 1) - 0x2000) < 40)
                    for i in diff})
    if lines:
        print('differing lines', lines[0], '...', lines[-1], f'({len(lines)} lines)')
    png(path.with_suffix('.redraw.png'), hgr_rgb(m, shown), (2, 2))
    png(path.with_suffix('.shown.png'), hgr_rgb(ram, shown), (2, 2))
    return 0 if not diff else 1


if __name__ == '__main__':
    sys.exit(main())
