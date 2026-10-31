#!/usr/bin/env python3
"""ROGUE.DHGR graphics: the TMS9918 tiles, font and sprites for DHGR.

    python3 tools/tiles_dhgr.py src/video_dhgr_data.inc [--png DIR]

The DHGR back-end (src/video_dhgr.asm) emulates the core's virtual TMS9918
screen (docs/VIDEO_API.md): 32x24 characters of 8x8 pixels + 16x16 sprites,
256x192 pixels. It draws it on the //e double hi-res colour screen (140x192
colour pixels) halved horizontally: one DHGR colour pixel = two TMS pixels,
one line = one line. The TMS picture is 128 colour pixels wide there, from
x = 6 (6 black pixels each side); a character is 4 x 8, a sprite 8 x 16.

Inputs (never modified): src/gfx/tileset_rogue.inc (characters 0..127 and
their colour groups), src/gfx/sprite_pats.inc + src/gfx/sprites_boss.asm
(sprites, names 0..68). Output: one .inc of ca65 data (byte-stable):

  dg_cpx        32 x 128 bytes: pixel k of row l of character ch at
                128 (4 l + k) + ch, as its DHGR nibble (the ink of the
                character's colour group, or 0: the paper is black for every
                group of this tileset): one load a pixel, no masking
  dg_lit        128 bytes: 1 if the character has a lit pixel
  dg_sprites    18 x 16 bytes: one row of a sprite, 8 pixels, bit 7 = left
  dg_palette    16 bytes: TMS colour -> DHGR nibble (sprite colours)

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
from apple2img import PALETTE, png_write, dhgr_from_colors, dhgr_to_rgb  # noqa: E402
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

def inc_text(data):
    dg_chars, dg_colours, dg_sprites, dg_palette = data
    lines = ['; video_dhgr_data.inc -- GENERATED by tools/tiles_dhgr.py. DO NOT EDIT.',
             '; Tiles: Quale\'s SCROLL-O-SPRITES (CC-BY-3.0), boss: Hexany\'s Monster',
             '; Menagerie (CC0), halved for DHGR (see the tool\'s docstring).',
             '', '.segment "RODATA"', '',
             '; dg_cpx + 128 * (4 l + k) + ch = pixel k (0 = left) of row l of',
             '; character ch: its ink\'s DHGR nibble when lit, else 0 (black paper)',
             'dg_cpx:']
    for y in range(8):
        for k in range(4):
            lines.append(asm_bytes([dg_colours[c >> 3] if dg_chars[8 * c + y] >> (3 - k) & 1
                                    else 0 for c in range(128)], per_line=16).rstrip('\n'))
    lines += ['', '; 1 if the character has a lit pixel (0: drawn as black)', 'dg_lit:']
    lines.append(asm_bytes([int(any(dg_chars[8 * c:8 * c + 8])) for c in range(128)],
                           per_line=16).rstrip('\n'))
    lines += ['', '; 18 sprites (TMS name / 4) x 16 rows, 8 pixels a row (bit 7 = left)',
              'dg_sprites:']
    lines.append(asm_bytes(dg_sprites, per_line=16).rstrip('\n'))
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
    write_if_changed(args.out, inc_text(data))
    if args.png:
        write_previews(args.png, inputs, data)


if __name__ == '__main__':
    main()
