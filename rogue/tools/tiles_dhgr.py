#!/usr/bin/env python3
"""ROGUE.DHGR graphics: the TMS9918 tiles, font and sprites for DHGR.

    python3 tools/tiles_dhgr.py src/video_dhgr_data.inc [--png DIR]

The DHGR back-end (src/video_dhgr.asm) emulates the core's virtual TMS9918
screen (docs/VIDEO_API.md): 32x24 characters of 8x8 pixels + 16x16 sprites,
256x192 pixels. Its text engine draws the full pages (title, bag, help...)
and the HUD rows of the game view (the map itself: tools/x2_dhgr.py, the X2
way) on the //e double hi-res colour screen (140x192 colour pixels) halved
horizontally: one DHGR colour pixel = two TMS pixels,
one line = one line. The TMS picture is 128 colour pixels wide there, from
x = 6 (6 black pixels each side); a character is 4 x 8, a sprite 8 x 16.

Inputs (never modified): src/gfx/tileset_rogue.inc (characters 0..127 and
their colour groups), src/gfx/sprite_pats.inc + src/gfx/sprites_boss.asm
(sprites, names 0..68). Output: one .inc of ca65 data (byte-stable) for the
back-end's byte composition. A line of the screen is 80 "stream" bytes of 7
dots (stream byte 2o = aux offset o, 2o + 1 = main offset o), a colour pixel
x = dots 4x..4x+3; character c of a row = 16 dots from dot 24 + 16 c, so
character 7q + p starts at bit (24 + 16 p) mod 7 of stream byte 16 q +
(24 + 16 p) div 7 (7 phases):

  dg_ri         8 x 128: row l of character ch as a piece index, 16 * its
                ink (0..3, the inks of the lit characters) + its 4 pixels
  dg_san        256: the name if it is a character with a lit pixel, else $FF
  dg_cp<p><i>   22 tables of 64: piece i (3 or 4 bytes) of a character row
                of phase p, by piece index: ready to OR / store
  dg_sm<r><i>   22 tables of 16: the dots of a 4-pixel sprite half (bit 3 =
                left) from bit r of a byte: piece i of its 3 or 4 bytes
  dg_cpat       16 x 16: stream byte k painted with pixel value N, at 16 N +
                (k AND 3) (+ 4, 8, 12: the same, for the next bytes)
  dg_sph/spl    18 x 16 each: the left / right 4 pixels of a sprite row
  dg_palette    16 bytes: TMS colour -> DHGR nibble (sprite colours)

compose() is that algorithm in Python; the generation checks it against
render() (the per-pixel model the tests compare the screen with) on the mock
screen.

Halving 8 pixels into 4: each output pixel is a pair of TMS pixels. Rules,
chosen by looking at the previews: the wall and the door keep a pixel only if both are
lit (AND: its one-pixel mortar survives), the other tiles and the sprites if
either is lit (OR: thin outlines and limbs survive), the font is a hand-made 3x7 alphabet (FONT below) at
pixels 0-2 of the cell (the Quale glyphs halved are unreadable: M, N, W).

Palette (TMS9918 -> DHGR / LORES colour number, see PALETTE_MAP).
--png DIR writes previews: dhgr_atlas.png (characters + sprites, x4),
dhgr_mock.png (a sample game screen, DHGR colour), dhgr_mock_tms.png (the
same screen on the TMS9918), dhgr_mock_mono.png (the 560-dot monochrome
alternative: the TMS picture 1:1, two dots per pixel).
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'dev/tools'))
from apple2img import PALETTE, png_write, dhgr_from_colors, dhgr_to_rgb, hgr_offset  # noqa: E402
from fonts import asm_bytes, write_if_changed  # noqa: E402

GRID_X = 6          # first colour pixel of the 128-pixel TMS picture

# TMS9918 colour -> DHGR colour number (LORES numbering, apple2img.PALETTE).
# 0 (transparent) is never drawn.
PALETTE_MAP = {
    0: 0,    # transparent
    1: 0,    # black          -> black
    2: 12,   # medium green   -> green (troll)
    3: 12,   # light green    -> green
    4: 6,    # dark blue      -> medium blue
    5: 7,    # light blue     -> light blue (the player)
    6: 1,    # dark red       -> magenta, the deep red of DHGR (tunic)
    7: 14,   # cyan           -> aqua (skeleton, scroll, gold/potion tiles)
    8: 9,    # medium red     -> orange: the hit flash, the boss (vivid, unlike any
             #                   monster's own colour)
    9: 11,   # light red      -> pink (torch)
    10: 13,  # dark yellow    -> yellow (stairs, door, DEATH, amulet)
    11: 13,  # light yellow   -> yellow (pit tile, ration)
    12: 4,   # dark green     -> dark green
    13: 3,   # magenta        -> purple (potion)
    14: 5,   # gray           -> grey (walls, ghost, dagger)
    15: 15,  # white          -> white
}
TMS_RGB = [(0, 0, 0), (0, 0, 0), (33, 200, 66), (94, 220, 120), (84, 85, 237),
           (125, 118, 252), (212, 82, 77), (66, 235, 245), (252, 85, 84),
           (255, 121, 120), (212, 193, 84), (230, 206, 128), (33, 176, 59),
           (201, 91, 186), (204, 204, 204), (255, 255, 255)]


def nib(c):
    """DHGR colour number -> the 4 dots of its pixel (low bit = first dot)."""
    return ((c >> 1) | (c << 3)) & 15


# 3x7 font, pixels 0-2 of the 4-pixel cell, rows 1-7 of the 8 (row 0 blank,
# as the Quale font). '#' = lit.
FONT = {
    ' ': ['...'] * 7,
    '!': ['.#.', '.#.', '.#.', '.#.', '.#.', '...', '.#.'],
    '(': ['..#', '.#.', '.#.', '.#.', '.#.', '.#.', '..#'],
    ')': ['#..', '.#.', '.#.', '.#.', '.#.', '.#.', '#..'],
    '*': ['...', '#.#', '.#.', '###', '.#.', '#.#', '...'],
    '+': ['...', '.#.', '.#.', '###', '.#.', '.#.', '...'],
    ',': ['...', '...', '...', '...', '...', '.#.', '#..'],
    '-': ['...', '...', '...', '###', '...', '...', '...'],
    '.': ['...', '...', '...', '...', '...', '...', '.#.'],
    '/': ['..#', '..#', '.#.', '.#.', '.#.', '#..', '#..'],
    '0': ['###', '#.#', '#.#', '#.#', '#.#', '#.#', '###'],
    '1': ['.#.', '##.', '.#.', '.#.', '.#.', '.#.', '###'],
    '2': ['###', '..#', '..#', '###', '#..', '#..', '###'],
    '3': ['###', '..#', '..#', '.##', '..#', '..#', '###'],
    '4': ['#.#', '#.#', '#.#', '###', '..#', '..#', '..#'],
    '5': ['###', '#..', '#..', '###', '..#', '..#', '###'],
    '6': ['###', '#..', '#..', '###', '#.#', '#.#', '###'],
    '7': ['###', '..#', '..#', '.#.', '.#.', '.#.', '.#.'],
    '8': ['###', '#.#', '#.#', '###', '#.#', '#.#', '###'],
    '9': ['###', '#.#', '#.#', '###', '..#', '..#', '###'],
    ':': ['...', '.#.', '.#.', '...', '.#.', '.#.', '...'],
    '=': ['...', '...', '###', '...', '###', '...', '...'],
    '?': ['###', '..#', '..#', '.##', '.#.', '...', '.#.'],
    'A': ['.#.', '#.#', '#.#', '###', '#.#', '#.#', '#.#'],
    'B': ['##.', '#.#', '#.#', '##.', '#.#', '#.#', '##.'],
    'C': ['.##', '#..', '#..', '#..', '#..', '#..', '.##'],
    'D': ['##.', '#.#', '#.#', '#.#', '#.#', '#.#', '##.'],
    'E': ['###', '#..', '#..', '##.', '#..', '#..', '###'],
    'F': ['###', '#..', '#..', '##.', '#..', '#..', '#..'],
    'G': ['.##', '#..', '#..', '#.#', '#.#', '#.#', '.##'],
    'H': ['#.#', '#.#', '#.#', '###', '#.#', '#.#', '#.#'],
    'I': ['###', '.#.', '.#.', '.#.', '.#.', '.#.', '###'],
    'J': ['..#', '..#', '..#', '..#', '..#', '#.#', '.#.'],
    'K': ['#.#', '#.#', '##.', '#..', '##.', '#.#', '#.#'],
    'L': ['#..', '#..', '#..', '#..', '#..', '#..', '###'],
    'M': ['#.#', '###', '###', '#.#', '#.#', '#.#', '#.#'],
    'N': ['##.', '#.#', '#.#', '#.#', '#.#', '#.#', '#.#'],
    'O': ['.#.', '#.#', '#.#', '#.#', '#.#', '#.#', '.#.'],
    'P': ['##.', '#.#', '#.#', '##.', '#..', '#..', '#..'],
    'Q': ['.#.', '#.#', '#.#', '#.#', '#.#', '##.', '.##'],
    'R': ['##.', '#.#', '#.#', '##.', '#.#', '#.#', '#.#'],
    'S': ['.##', '#..', '#..', '.#.', '..#', '..#', '##.'],
    'T': ['###', '.#.', '.#.', '.#.', '.#.', '.#.', '.#.'],
    'U': ['#.#', '#.#', '#.#', '#.#', '#.#', '#.#', '###'],
    'V': ['#.#', '#.#', '#.#', '#.#', '#.#', '#.#', '.#.'],
    'W': ['#.#', '#.#', '#.#', '#.#', '###', '###', '#.#'],
    'X': ['#.#', '#.#', '#.#', '.#.', '#.#', '#.#', '#.#'],
    'Y': ['#.#', '#.#', '#.#', '.#.', '.#.', '.#.', '.#.'],
    'Z': ['###', '..#', '..#', '.#.', '#..', '#..', '###'],
    '[': ['.##', '.#.', '.#.', '.#.', '.#.', '.#.', '.##'],
    '\\': ['#..', '#..', '.#.', '.#.', '.#.', '..#', '..#'],
    ']': ['##.', '.#.', '.#.', '.#.', '.#.', '.#.', '##.'],
}


# ------------------------------------------------------------------ inputs

def byte_lines(text):
    """ca65 `.byte` values of a text, in order."""
    out = []
    for line in text.splitlines():
        line = line.split(';', 1)[0]
        m = re.match(r'\s*\.byte\s+(.*)', line)
        if not m:
            continue
        for tok in m.group(1).split(','):
            tok = tok.strip()
            if tok:
                out.append(int(tok[1:], 16) if tok.startswith('$') else int(tok, 0))
    return out


def label_bytes(text, label, count):
    """`count` .byte values after `label:` in text."""
    i = text.index(label + ':')
    vals = byte_lines(text[i:])
    if len(vals) < count:
        raise ValueError(f'{label}: {len(vals)} bytes < {count}')
    return vals[:count]


def load_inputs(src):
    tiles = (src / 'gfx/tileset_rogue.inc').read_text()
    chars = label_bytes(tiles, 'tileset_rogue', 2048)
    colours = label_bytes(tiles, 'tileset_color_table', 32)
    spr = label_bytes((src / 'gfx/sprite_pats.inc').read_text(), 'sprite_pats', 448)
    spr += label_bytes((src / 'gfx/sprites_boss.asm').read_text(), 'boss_sprite_pats', 128)
    return chars, colours, spr


# ------------------------------------------------------------------ conversion

def halve(row8, rule):
    """8 TMS pixels (bit 7 = left) -> 4 pixels (bit 3 = left)."""
    out = 0
    for k in range(4):
        pair = (row8 >> (6 - 2 * k)) & 3
        lit = (pair == 3) if rule == 'and' else (pair != 0)
        out = out << 1 | lit
    return out


def font_rows(ch):
    rows = FONT[ch]
    return [0] + [sum(1 << (3 - x) for x in range(3) if r[x] == '#') for r in rows]


def convert(chars, colours, spr):
    dg_chars = []
    for c in range(128):
        pat = chars[8 * c:8 * c + 8]
        if c < 32:
            dg_chars += [halve(r, 'and' if 4 <= c < 8 or 12 <= c < 16 else 'or') for r in pat]
        elif chr(c) in FONT:
            dg_chars += font_rows(chr(c))
        elif chr(c).upper() in FONT and any(pat):
            dg_chars += font_rows(chr(c).upper())
        else:
            if any(pat):
                raise ValueError(f'character {c} has a glyph but no FONT entry')
            dg_chars += [0] * 8
    for g in range(16):
        if colours[g] & 15 not in (0, 1):
            raise ValueError(f'colour group {g}: paper {colours[g] & 15} is not black')
    dg_colours = [nib(PALETTE_MAP[colours[g] >> 4]) for g in range(16)]
    dg_sprites = []
    for s in range(18):
        blk = spr[32 * s:32 * s + 32]
        for r in range(16):
            left = blk[r]            # rows 0-15 of the left column (TL then BL)
            right = blk[16 + r]
            dg_sprites.append(halve(left, 'or') << 4 | halve(right, 'or'))
    dg_palette = [nib(PALETTE_MAP[c]) for c in range(16)]
    return dg_chars, dg_colours, dg_sprites, dg_palette


# ------------------------------------------------------------------ model
# The back-end's picture, pixel for pixel: tests compare the screen to it.

def sprite_list(sat):
    out = []
    for i in range(32):
        y, x, name, col = sat[4 * i:4 * i + 4]
        if y == 0xD0:
            break
        out.append((y, x, name, col))
    return out


def render(names, sat, data):
    """names: 768 bytes, sat: 128 bytes -> 192 rows of 140 DHGR colour numbers."""
    dg_chars, dg_colours, dg_sprites, _ = data
    unnib = {nib(c): c for c in range(16)}
    px = [[0] * 140 for _ in range(192)]
    for r in range(24):
        for c in range(32):
            ch = names[32 * r + c] & 0x7F if names[32 * r + c] < 128 else 0
            ink = unnib[dg_colours[ch >> 3]]
            for y in range(8):
                bits = dg_chars[8 * ch + y]
                for k in range(4):
                    if bits >> (3 - k) & 1:
                        px[8 * r + y][GRID_X + 4 * c + k] = ink
    for y0, x0, name, col in reversed(sprite_list(sat)):
        col &= 15
        if col == 0:
            continue
        ink = PALETTE_MAP[col]
        s = name >> 2
        if s >= 18:
            continue
        for y in range(16):
            yy = y0 + y
            if yy >= 192:
                break
            bits = dg_sprites[16 * s + y]
            for k in range(8):
                if bits >> (7 - k) & 1:
                    px[yy][GRID_X + (x0 >> 1) + k] = ink
    return px


def render_tms(names, sat, chars, colours, spr):
    """Reference TMS9918 picture, 256x192 RGB (previews only)."""
    img = [[TMS_RGB[1]] * 256 for _ in range(192)]
    for r in range(24):
        for c in range(32):
            ch = names[32 * r + c]
            ink = TMS_RGB[colours[ch >> 3] >> 4]
            for y in range(8):
                bits = chars[8 * ch + y]
                for k in range(8):
                    if bits >> (7 - k) & 1:
                        img[8 * r + y][8 * c + k] = ink
    for y0, x0, name, col in reversed(sprite_list(sat)):
        blk = spr[32 * (name >> 2):32 * (name >> 2) + 32]
        for y in range(16):
            for half in range(2):
                bits = blk[16 * half + y]
                for k in range(8):
                    if bits >> (7 - k) & 1 and y0 + y < 192 and x0 + 8 * half + k < 256:
                        img[y0 + y][x0 + 8 * half + k] = TMS_RGB[col & 15]
    return img


def render_mono(names, sat, chars, spr):
    """The 560-dot alternative: the TMS picture 1:1, 2 dots per pixel, white."""
    img = [[0] * 560 for _ in range(192)]
    ox = (560 - 512) // 2
    def put(y, x):
        if 0 <= y < 192 and 0 <= x < 256:
            img[y][ox + 2 * x] = img[y][ox + 2 * x + 1] = 255
    for r in range(24):
        for c in range(32):
            ch = names[32 * r + c]
            for y in range(8):
                for k in range(8):
                    if chars[8 * ch + y] >> (7 - k) & 1:
                        put(8 * r + y, 8 * c + k)
    for y0, x0, name, col in reversed(sprite_list(sat)):
        blk = spr[32 * (name >> 2):32 * (name >> 2) + 32]
        for y in range(16):
            for half in range(2):
                for k in range(8):
                    if blk[16 * half + y] >> (7 - k) & 1:
                        put(y0 + y, x0 + 8 * half + k)
    return img


# ------------------------------------------------------------------ previews

MOCK_MAP = [            # 16 x 10 logical cells: # wall, + door, > stairs, ^ pit
    '################',
    '#......#.......#',
    '#......+.......#',
    '#......#...^...#',
    '###+####.......#',
    '#..............#',
    '#.....>........+',
    '#..............#',
    '#..............#',
    '################',
]
CELL_BASE = {'#': 4, '+': 12, '>': 8, '^': 20, '.': 0, '<': 16}


def mock_screen():
    names = bytearray(768)
    for r, line in enumerate(MOCK_MAP):
        for c, ch in enumerate(line):
            b = CELL_BASE[ch]
            names[32 * 2 * r + 2 * c] = b
            names[32 * 2 * r + 2 * c + 1] = b + 1
            names[32 * (2 * r + 1) + 2 * c] = b + 2
            names[32 * (2 * r + 1) + 2 * c + 1] = b + 3
    hud = ['DEPTH   3', 'ATK: 3 DEF: 2                 05',
           '                          HP 14/20', '  12  07                  XP:  4']
    for i, text in enumerate(hud):
        for c, ch in enumerate(text):
            names[32 * (20 + i) + c] = ord(ch)
    sat = bytearray([0xD0] * 128)
    ents = [(5 * 16, 4 * 16, 0, 5), (160, 224, 24, 14),
            (2 * 16, 3 * 16, 4, 15), (2 * 16, 11 * 16, 8, 14), (6 * 16, 9 * 16, 48, 2),
            (7 * 16, 3 * 16, 20, 7), (1 * 16, 10 * 16, 12, 8), (3 * 16, 5 * 16, 28, 13),
            (8 * 16, 13 * 16, 36, 15), (5 * 16, 12 * 16, 44, 10), (7 * 16, 6 * 16, 52, 9),
            (8 * 16, 1 * 16, 16, 11), (1 * 16, 2 * 16, 32, 7), (3 * 16, 1 * 16, 40, 6),
            (176, 0, 36, 15), (176, 32, 40, 6),
            (6 * 16, 11 * 16, 56, 8), (6 * 16, 13 * 16, 60, 8),
            (8 * 16, 11 * 16, 64, 8), (8 * 16, 13 * 16, 68, 8)]
    for i, e in enumerate(ents):
        sat[4 * i:4 * i + 4] = bytes(e)
    return names, sat


def atlas(data):
    dg_chars, dg_colours, dg_sprites, dg_palette = data
    unnib = {nib(c): c for c in range(16)}
    px = [[0] * 140 for _ in range(192)]
    for ch in range(128):
        ox, oy = 2 + (ch % 16) * 6, 2 + (ch // 16) * 10
        ink = unnib[dg_colours[ch >> 3]] or 5
        for y in range(8):
            for k in range(4):
                if dg_chars[8 * ch + y] >> (3 - k) & 1:
                    px[oy + y][ox + k] = ink
    cols = [5, 15, 14, 13, 11, 7, 14, 13, 7, 15, 6, 10, 2, 9, 8, 8, 8, 8]
    for s in range(18):
        ox, oy = 2 + (s % 9) * 10, 88 + (s // 9) * 20
        for y in range(16):
            for k in range(8):
                if dg_sprites[16 * s + y] >> (7 - k) & 1:
                    px[oy + y][ox + k] = PALETTE_MAP[cols[s]]
    return px


def dhgr_rgb(px):
    return dhgr_to_rgb(*dhgr_from_colors(px))


def write_previews(out, inputs, data):
    out.mkdir(parents=True, exist_ok=True)
    chars, colours, spr = inputs
    names, sat = mock_screen()
    # DHGR colour pixels are 4 dots wide: x4 horizontally, x2 vertically
    png_write(out / 'dhgr_atlas.png', dhgr_rgb(atlas(data)), scale=(8, 4))
    png_write(out / 'dhgr_mock.png', dhgr_rgb(render(names, sat, data)), scale=(4, 2))
    png_write(out / 'dhgr_mock_tms.png', render_tms(names, sat, chars, colours, spr),
              scale=(2, 2))
    png_write(out / 'dhgr_mock_mono.png', render_mono(names, sat, chars, spr),
              scale=(1, 2), mode='gray')


# ------------------------------------------------------------------ output

CHAR_X0 = 4 * GRID_X        # stream bit of character 0's first dot (24)


def char_phase(p):
    """Character 7q + p: (first stream byte relative to 16 q, bit in it, pieces)."""
    start = CHAR_X0 + 16 * p
    return start // 7, start % 7, (start % 7 + 22) // 7


def pieces(r, nib4, rev=False):
    """A 4-pixel row (bit k = pixel k lit, or bit 3 - k with rev) whose pixels
    have the 4-bit value nib4 (0..15, low bit = first dot), at bit r of a
    stream byte: its ceil((r + 16) / 7) bytes."""
    def lit(m, k):
        return m >> (3 - k if rev else k) & 1
    def table(m):
        out = [0] * ((r + 22) // 7)
        for k in range(4):
            if lit(m, k):
                for j in range(4):
                    if nib4 >> j & 1:
                        s = r + 4 * k + j
                        out[s // 7] |= 1 << (s % 7)
        return out
    return [table(m) for m in range(16)]


def char_colours(data):
    """The inks of the characters with a lit pixel, in order (<= 4)."""
    dg_chars, dg_colours, _, _ = data
    cols = []
    for ch in range(128):
        if any(dg_chars[8 * ch:8 * ch + 8]) and dg_colours[ch >> 3] not in cols:
            cols.append(dg_colours[ch >> 3])
    if len(cols) > 4:
        raise ValueError(f'{len(cols)} character inks: the piece tables hold 4')
    return cols


def byte_tables(data):
    """The byte-composition tables of the back-end (see inc_text)."""
    dg_chars, dg_colours, dg_sprites, dg_palette = data
    cols = char_colours(data)
    lit = [any(dg_chars[8 * c:8 * c + 8]) for c in range(128)]
    ri = []
    for y in range(8):
        for c in range(128):
            m = sum(1 << k for k in range(4) if dg_chars[8 * c + y] >> (3 - k) & 1)
            ri.append(cols.index(dg_colours[c >> 3]) * 16 + m if lit[c] else 0)
    san = [c if c < 128 and lit[c] else 0xFF for c in range(256)]
    cp = {}
    for p in range(7):
        k0, r, n = char_phase(p)
        per_col = [pieces(r, cols[ci] if ci < len(cols) else 0) for ci in range(4)]
        for i in range(n):
            cp[p, i] = [per_col[ci][m][i] for ci in range(4) for m in range(16)]
    sm = {}
    for r in range(7):
        t = pieces(r, 15, rev=True)
        for i in range((r + 22) // 7):
            sm[r, i] = [t[m][i] for m in range(16)]
    # colour of stream byte k (k & 3 = a) for a pixel value N: dot b of the
    # byte is dot (7 k + b) mod 4 = (3 a + b) mod 4 of the pixel
    cpat = [sum((nv >> ((3 * (m & 3) + b) % 4) & 1) << b for b in range(7))
            for nv in range(16) for m in range(16)]
    sph = [b >> 4 for b in dg_sprites]
    spl = [b & 15 for b in dg_sprites]
    return dict(ri=ri, san=san, cp=cp, sm=sm, cpat=cpat, sph=sph, spl=spl)


def compose(names, sat, data, tabs=None):
    """The back-end's algorithm in Python: 192 lines of 80 stream bytes
    (stream byte 2 o = aux offset o, 2 o + 1 = main offset o)."""
    t = tabs or byte_tables(data)
    pal = data[3]
    lines = []
    sprs = list(reversed(sprite_list(sat)))
    for y in range(192):
        buf = [0] * 84
        for c in range(32):
            q, p = divmod(c, 7)
            k0, r, n = char_phase(p)
            k0 += 16 * q
            ch = t['san'][names[32 * (y >> 3) + c]]
            idx = 0 if ch == 0xFF else t['ri'][128 * (y & 7) + ch]
            for i in range(n):
                v = t['cp'][p, i][idx]
                buf[k0 + i] = buf[k0 + i] | v if i == 0 and r else v
        for y0, x0, name, col in sprs:
            if col & 15 == 0 or name >= 72 or y0 >= 192 or not y0 <= y < y0 + 16:
                continue
            nv = pal[col & 15]
            s0 = 4 * (GRID_X + (x0 >> 1))
            k, r = divmod(s0, 7)
            row = 16 * (name >> 2) + y - y0
            for hm, rr, kk in ((t['sph'][row], r, k), (t['spl'][row], (r + 16) % 7, k + (r + 16) // 7)):
                for i in range((rr + 22) // 7):
                    b = kk + i
                    buf[b] ^= (buf[b] ^ t['cpat'][16 * nv + (b & 3)]) & t['sm'][rr, i][hm]
        lines.append(buf[:80])
    return lines


def inc_text(data):
    dg_chars, dg_colours, dg_sprites, dg_palette = data
    t = byte_tables(data)
    lines = ['; video_dhgr_data.inc -- GENERATED by tools/tiles_dhgr.py. DO NOT EDIT.',
             '; Tiles: Quale\'s SCROLL-O-SPRITES (CC-BY-3.0), boss: Hexany\'s Monster',
             '; Menagerie (CC0), halved for DHGR (see the tool\'s docstring).',
             '', '.segment "RODATA"', '',
             '; dg_ri + 128 l + ch = row l of character ch as a piece index:',
             '; 16 * (its ink, 0..3) + its 4 pixels (bit k = pixel k, 0 = left)',
             'dg_ri:']
    lines.append(asm_bytes(t['ri'], per_line=16).rstrip('\n'))
    lines += ['', '; dg_san + name = the name if it is a character with a lit pixel,',
              '; else $FF (drawn black)', 'dg_san:']
    lines.append(asm_bytes(t['san'], per_line=16).rstrip('\n'))
    lines += ['', '; dg_cp<p><i> + index: piece i (stream byte k0 + i) of a character',
              '; row of phase p (character 7 q + p, first dot at stream bit 24 + 16 p)']
    for (p, i), v in sorted(t['cp'].items()):
        lines.append(f'dg_cp{p}{i}:')
        lines.append(asm_bytes(v, per_line=16).rstrip('\n'))
    lines += ['', '; dg_sm<r><i> + m: piece i of the dots of a 4-pixel sprite half m',
              '; (bit 3 = left) whose first dot is bit r of the first byte']
    for (r, i), v in sorted(t['sm'].items()):
        lines.append(f'dg_sm{r}{i}:')
        lines.append(asm_bytes(v, per_line=16).rstrip('\n'))
    lines += ['', '; dg_cpat + 16 N + m: stream byte k (k & 3 = m & 3) painted with',
              '; the pixel value N', 'dg_cpat:']
    lines.append(asm_bytes(t['cpat'], per_line=16).rstrip('\n'))
    lines += ['', '; 18 sprites (TMS name / 4) x 16 rows: left 4 pixels (dg_sph) and',
              '; right 4 pixels (dg_spl), bit 3 = left', 'dg_sph:']
    lines.append(asm_bytes(t['sph'], per_line=16).rstrip('\n'))
    lines.append('dg_spl:')
    lines.append(asm_bytes(t['spl'], per_line=16).rstrip('\n'))
    lines += ['', '; TMS9918 colour -> DHGR nibble (sprite colours)', 'dg_palette:']
    lines.append(asm_bytes(dg_palette, per_line=16).rstrip('\n'))
    return '\n'.join(lines) + '\n'


def load_data(src=ROOT / 'src'):
    inputs = load_inputs(src)
    return inputs, convert(*inputs)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('out')
    ap.add_argument('--png', type=Path)
    args = ap.parse_args(argv)
    inputs, data = load_data()
    names, sat = mock_screen()
    main_, aux = dhgr_from_colors(render(names, sat, data))
    for y, line in enumerate(compose(names, sat, data)):
        base = hgr_offset(y)
        if line[0::2] != list(aux[base:base + 40]) or line[1::2] != list(main_[base:base + 40]):
            raise SystemExit(f'compose() differs from render() at line {y}')
    write_if_changed(args.out, inc_text(data))
    if args.png:
        write_previews(args.png, inputs, data)


if __name__ == '__main__':
    main()
