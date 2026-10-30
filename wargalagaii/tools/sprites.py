#!/usr/bin/env python3
"""WARGALAGA II sprites -> src/sprites.inc (HGR, 7 pre-shifts, black background).

A drawing is a grid of CELLS, two HGR dots wide. A sprite moves by whole
cells (2 dots), so its left dot always sits on an even screen column:

    .  black            W  both dots: white
    L  left dot only    R  right dot only
    X  the tint's dot (aliens): L or R, chosen by the tint

With palette bit 0 the left dot shows violet and the right one green; with
bit 7 set, blue and orange (one palette per sprite: one byte cannot mix
them). Alien tints: 0 violet, 1 green, 2 blue, 3 orange.

Seven shifts (cell x mod 7) cover a 14-dot group of two bytes; each shift is
stored with the same byte width, starting at byte (2*shift)//7 of the group,
rows top to bottom, bytes left to right. Aliens have two animation frames:
the table for shift s and frame f is entry 2*s+f.

    tools/sprites.py            write src/sprites.inc (if changed)
    tools/sprites.py --check    fail if src/sprites.inc is stale
    tools/sprites.py --png F    preview sheet of every drawing and tint
"""
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'dev/tools'))
import fonts
OUT = ROOT / 'src/sprites.inc'
FIELD_COL = 4                   # model.FIELD_COL: the left wall's bytes

# name: (palette bit, drawing)
SPRITES = {
    'ship': (1, [
        '...W...',
        '...W...',
        '..WLW..',
        '..WWW..',
        'R.WWW.R',
        'W.WWW.W',
        'WWWLWWW',
        'WWWWWWW',
        'W.R.R.W',
        '..R.R..',
    ]),
    'shot': (0, [               # one byte wide: see ONE_BYTE
        'W',
        'W',
        'W',
        'W',
        'W',
        'W',
    ]),
    'ufo': (0, [                # the hurry-up saucer
        '..WWW..',
        '.WLWLW.',
        'WWWWWWW',
        'L.L.L.L',
        '.WWWWW.',
        '..L.L..',
        '.L...L.',
        '.......',
    ]),
    'bomb': (1, [               # one byte wide, blue (left dot, palette 1)
        'L',
        'L',
        'L',
        'L',
    ]),
}

# Explosions, two frames each: an alien's (7 x 8, drawn like a flying
# alien) and the ship's (7 x 10, drawn like the ship).
BOOM = (1, [
    '...W...',
    '.R.W.R.',
    '..RWR..',
    'WWW.WWW',
    '..RWR..',
    '.R.W.R.',
    '...W...',
    '.......',
], [
    'R..W..R',
    '.R...R.',
    '..R.R..',
    'WW...WW',
    '..R.R..',
    '.R...R.',
    'R..W..R',
    '.......',
])
SHIPBOOM = (1, [
    '.......',
    '...R...',
    '.R.W.R.',
    '..WWW..',
    'RWW.WWR',
    '..WWW..',
    '.R.W.R.',
    '...R...',
    '.......',
    '.......',
], [
    'R..R..R',
    '.R...R.',
    '..R.R..',
    'R.....R',
    'W.....W',
    'R.....R',
    '..R.R..',
    '.R...R.',
    'R..R..R',
    '.......',
])

# Small aliens: 7 cells x 10 rows, two frames. Pack n of 4 levels uses
# design n mod 6 in tint n div 6.
SMALL = [
    ('bee', [
        '.X...X.',
        '..X.X..',
        '.XWWWX.',
        'XXWXWXX',
        'X.WWW.X',
        'X.XWX.X',
        '..XWX..',
        '...W...',
    ], [
        '.X...X.',
        '..X.X..',
        '.XWWWX.',
        '.XWXWX.',
        '..WWW..',
        '.XXWXX.',
        'X.XWX.X',
        '...W...',
    ]),
    ('crab', [
        '..X.X..',
        '.XWWWX.',
        'XW.W.WX',
        'XWWWWWX',
        '.XWXWX.',
        '..X.X..',
        '.X...X.',
        'X.....X',
    ], [
        '..X.X..',
        '.XWWWX.',
        'XW.W.WX',
        'XWWWWWX',
        '.XWXWX.',
        '..X.X..',
        '..X.X..',
        '.X...X.',
    ]),
    ('squid', [
        '...W...',
        '..WWW..',
        '.WXWXW.',
        '.WWWWW.',
        '..XWX..',
        '.X.X.X.',
        'X..X..X',
        '.X.X.X.',
    ], [
        '...W...',
        '..WWW..',
        '.WXWXW.',
        '.WWWWW.',
        '..XWX..',
        '..XXX..',
        '.X.X.X.',
        '.X.X.X.',
    ]),
    ('moth', [
        'X.....X',
        'XX...XX',
        'XXXWXXX',
        '.XWWWX.',
        '..WXW..',
        '.XWWWX.',
        'XX.W.XX',
        'X.....X',
    ], [
        '.......',
        '.X...X.',
        'XXXWXXX',
        'XXWWWXX',
        '..WXW..',
        'XXWWWXX',
        '.X.W.X.',
        '.......',
    ]),
    ('saucer', [
        '..WWW..',
        '.WXXXW.',
        'WWWWWWW',
        'X.X.X.X',
        '.WWWWW.',
        '..X.X..',
        '.X...X.',
        '.......',
    ], [
        '..WWW..',
        '.WXXXW.',
        'WWWWWWW',
        '.X.X.X.',
        '.WWWWW.',
        '..X.X..',
        '..X.X..',
        '.......',
    ]),
    ('beetle', [
        '.X.W.X.',
        '..XWX..',
        '.WWWWW.',
        'XWXWXWX',
        '.WWWWW.',
        'XWXWXWX',
        '.WWWWW.',
        'X.X.X.X',
    ], [
        'X..W..X',
        '.X.W.X.',
        '.WWWWW.',
        'XWXWXWX',
        '.WWWWW.',
        'XWXWXWX',
        '.WWWWW.',
        '.X.X.X.',
    ]),
]

# Big aliens (level 3 of each pack, carriers of the rank marks): 10 x 16.
BIG = [
    ('hornet', [
        '..X....X..',
        '...X..X...',
        '...WWWW...',
        '..WWXXWW..',
        'X.WXWWXW.X',
        'XXWWWWWWXX',
        'XXXWXXWXXX',
        'XX.WWWW.XX',
        'X..XWWX..X',
        'X...WW...X',
        '...XWWX...',
        '..X.WW.X..',
        '..X.WW.X..',
        '.X..WW..X.',
        '.....W....',
        '..........',
    ], [
        '..X....X..',
        '...X..X...',
        '...WWWW...',
        '..WWXXWW..',
        '..WXWWXW..',
        '.XWWWWWWX.',
        'XXXWXXWXXX',
        'XXXWWWWXXX',
        'XX.XWWX.XX',
        'X...WW...X',
        '...XWWX...',
        '...XWWX...',
        '..X.WW.X..',
        '..X.WW.X..',
        '.....W....',
        '..........',
    ]),
    ('skull', [
        '...WWWW...',
        '..WWWWWW..',
        '.WWWWWWWW.',
        '.WX.WW.XW.',
        '.WX.WW.XW.',
        '.WWWWWWWW.',
        '..WWW.WW..',
        '...WWWW...',
        'X..W.W.W.X',
        '.X.......X',
        'X.X.XX.X.X',
        '.X.X..X.X.',
        'X...XX...X',
        '..........',
        '..........',
        '..........',
    ], [
        '...WWWW...',
        '..WWWWWW..',
        '.WWWWWWWW.',
        '.WX.WW.XW.',
        '.WX.WW.XW.',
        '.WWWWWWWW.',
        '..WWW.WW..',
        '...WWWW...',
        '...W.W.W..',
        'X........X',
        '.X.XXXX.X.',
        'X.X....X.X',
        '.X..XX..X.',
        '..........',
        '..........',
        '..........',
    ]),
]

# The Meteor Storm rock (lot 8): a small alien's size and table, tumbling
# (two frames), in tint ROCK_TINT; WG2.AUX after the big aliens, copied to
# cur_alien for the storm.
ROCK = ([
    '.WWWX..',
    'WWXWWX.',
    'WWWWWXX',
    'XWWWXWX',
    'WWXWWWX',
    'XWWWWX.',
    '.XXXX..',
    '.......',
], [
    '.XWWW..',
    'XWWWXW.',
    'WWXWWWX',
    'WWWWWXX',
    'XWWXWWX',
    'XXWWWX.',
    '.XXXX..',
    '.......',
])
ROCK_TINT = 3

# Clipped to the shift's start byte (a shot is one byte wide, so at shift 3
# only its left dot shows): half the cost of a two-byte sprite.
ONE_BYTE = {'shot', 'bomb'}

TINTS = ((0, 'L'), (0, 'R'), (1, 'L'), (1, 'R'))   # violet, green, blue, orange

# The boss (levels 25, 50, 75, 100): 16 cells x 24 rows, orange.
BOSS = (1, [
    '......WWWW......',
    '....WWXXXXWW....',
    '...WXXWWWWXXW...',
    '..WXXW.WW.WXXW..',
    '.WXXW.XWWX.WXXW.',
    'WXXW..XWWX..WXXW',
    'WXW...WWWW...WXW',
    'WXXWWWWXXWWWWXXW',
    '.WXXXXWXXWXXXXW.',
    '..WWWWXWWXWWWW..',
    '.X..WXXWWXXW..X.',
    'X.X.WXWXXWXW.X.X',
    'X..XWXW..WXWX..X',
    '.X.XWXW..WXWX.X.',
    '..XXWXXWWXXWXX..',
    '...XWWXXXXWWX...',
    '....WWWXXWWW....',
    '.....WXWWXW.....',
    '....X.XWWX.X....',
    '...X..X..X..X...',
    '..X...X..X...X..',
    '.X....X..X....X.',
    'X.....X..X.....X',
    '......X..X......',
])

# Falling objects (lot 5; redrawn for legibility 2026-10-23): 7 cells x
# ICON_H rows on an even byte column (an object never moves sideways, so no
# shifts), drawn in cells (two dots: white strokes stay white, no colour
# fringes). A family = a shape, its colour says which one:
#   coins          a disc with a $ cut out (green 10, orange 50, blue 100,
#                  violet 200)
#   gauges         a blue pill: S B T (the HUD's letters)
#   weapons        a violet pill: one, two, three shots; autofire: dashes
#   multipliers    an orange pill: 2, 5
#   EXTRA letters  a white pill: E X T R A (the HUD's row)
#   shield         a green bubble around the ship; armour: a blue shield
#   life           a heart; skull: a skull; freeze: a snowflake
#   rank marks     a medal (ribbon, disc of the mark's colour, its number);
#                  the dark mark: an empty white medal
#   sub-games      Meteor Storm: the rock; Memory Station: a green ? card
# X = the icon's colour (one palette per icon: a byte never mixes groups).
# Order = model.KINDS.
ICON_H = 13
COLOURS = {'violet': (0, 'L'), 'green': (0, 'R'), 'blue': (1, 'L'), 'orange': (1, 'R')}
FONT5 = {               # 5 cells x 7 rows, strokes one cell (2 dots) wide
    'S': ['.WWWW', 'W....', 'W....', '.WWW.', '....W', '....W', 'WWWW.'],
    'B': ['WWWW.', 'W...W', 'W...W', 'WWWW.', 'W...W', 'W...W', 'WWWW.'],
    'T': ['WWWWW', '..W..', '..W..', '..W..', '..W..', '..W..', '..W..'],
    'E': ['WWWWW', 'W....', 'W....', 'WWWW.', 'W....', 'W....', 'WWWWW'],
    'X': ['W...W', 'W...W', '.W.W.', '..W..', '.W.W.', 'W...W', 'W...W'],
    'R': ['WWWW.', 'W...W', 'W...W', 'WWWW.', 'W.W..', 'W..W.', 'W...W'],
    'A': ['.WWW.', 'W...W', 'W...W', 'WWWWW', 'W...W', 'W...W', 'W...W'],
    '2': ['.WWW.', 'W...W', '....W', '..WW.', '.W...', 'W....', 'WWWWW'],
    '5': ['WWWWW', 'W....', 'WWWW.', '....W', '....W', 'W...W', '.WWW.'],
    'w1': ['..W..'] * 7,
    'w2': ['.W.W.'] * 7,
    'w3': ['..W..', '..W..', 'W.W.W', 'W.W.W', 'W.W.W', 'W.W.W', 'W.W.W'],
    'auto': ['.W.W.', '.W.W.', '.....', '.W.W.', '.W.W.', '.....', '.W.W.'],
}
DIGIT3 = {              # 3 cells x 5 rows, cut out of a medal
    '1': ['.W.', 'WW.', '.W.', '.W.', 'WWW'], '2': ['WWW', '..W', 'WWW', 'W..', 'WWW'],
    '3': ['WWW', '..W', '.WW', '..W', 'WWW'], '4': ['W.W', 'W.W', 'WWW', '..W', '..W'],
    '5': ['WWW', 'W..', 'WWW', '..W', 'WWW'], '6': ['WWW', 'W..', 'WWW', 'W.W', 'WWW'],
}
DOLLAR = ['.W.', 'WWW', 'W..', 'WWW', '..W', 'WWW', '.W.']


def pill(glyph, cap='X'):
    """Caps of colour (or white) above and below a 5 x 7 glyph."""
    top = ['.' + cap * 5 + '.', cap * 7, '.......']
    return top + ['.' + r + '.' for r in FONT5[glyph]] + top[::-1]


def disc(cut, rows0=0):
    """A disc 7 x 13 of colour, cut (rows of W = black) in its middle."""
    shape = ['..XXX..', '.XXXXX.', 'XXXXXXX'] + ['XXXXXXX'] * 7 + ['XXXXXXX', '.XXXXX.', '..XXX..']
    out = [list(r) for r in shape]
    y0 = rows0 or (13 - len(cut)) // 2
    for y, r in enumerate(cut):
        for x, c in enumerate(r):
            if c == 'W':
                out[y0 + y][(7 - len(r)) // 2 + x] = '.'
    return [''.join(r) for r in out]


def medal(digit):
    """Ribbon, then a disc of colour with the number cut out."""
    body = ['..XXX..', '.XXXXX.', 'XXXXXXX', 'XXXXXXX', 'XXXXXXX', 'XXXXXXX', 'XXXXXXX',
            '.XXXXX.', '..XXX..']
    out = [list(r) for r in body]
    for y, r in enumerate(DIGIT3[digit]):
        for x, c in enumerate(r):
            if c == 'W':
                out[2 + y][2 + x] = '.'
    return ['.W...W.', '..W.W..', '...W...', '.......'] + [''.join(r) for r in out]


def centred(rows):
    pad = ICON_H - len(rows)
    return ['.......'] * (pad // 2) + list(rows) + ['.......'] * (pad - pad // 2)


ICON_SHAPES = [
    ('green', disc(DOLLAR)), ('orange', disc(DOLLAR)), ('blue', disc(DOLLAR)), ('violet', disc(DOLLAR)),
    ('blue', pill('S')), ('blue', pill('B')), ('blue', pill('T')),
    ('violet', pill('w1')), ('violet', pill('w2')), ('violet', pill('w3')), ('violet', pill('auto')),
    ('blue', centred(['XXXXXXX', 'XXX.XXX', 'XXX.XXX', 'X.....X', 'XXX.XXX', 'XXX.XXX',      # armour
                      '.XX.XX.', '.XXXXX.', '..XXX..', '...X...'])),
    ('orange', centred(['.XX.XX.', 'XXXXXXX', 'XXXXXXX', 'XXXXXXX', 'XXXXXXX', '.XXXXX.',  # life
                        '..XXX..', '...X...'])),
    ('white', centred(['.WWWWW.', 'WWWWWWW', 'W..W..W', 'W..W..W', 'WWWWWWW', '.WW.WW.',  # skull
                       '.WWWWW.', '.W.W.W.'])),
    ('white', pill('E', 'W')), ('white', pill('X', 'W')), ('white', pill('T', 'W')),
    ('white', pill('R', 'W')), ('white', pill('A', 'W')),
    ('orange', pill('2')), ('orange', pill('5')),
    ('green', ['..XXX..', '.X...X.', 'X.....X', 'X..W..X', 'X..W..X', 'X.WWW.X', 'X.WWW.X',  # shield
               'X.W.W.X', 'X.....X', '.X...X.', '..XXX..', '.......', '.......']),
    ('white', centred(['...W...', 'W..W..W', '.W.W.W.', '..WWW..', 'WWWWWWW', '..WWW..',  # freeze
                       '.W.W.W.', 'W..W..W', '...W...'])),
    ('orange', medal('1')), ('orange', medal('2')), ('orange', medal('3')),
    ('green', medal('4')), ('blue', medal('5')), ('violet', medal('6')),
    ('white', ['.W...W.', '..W.W..', '...W...', '.......', '..WWW..', '.W...W.', 'W.....W',  # dark
               'W.....W', 'W.....W', 'W.....W', 'W.....W', '.W...W.', '..WWW..']),
    ('orange', centred(ROCK[0][:7])),                                                      # meteor
    ('green', ['XXXXXXX', 'XXXXXXX', 'XX...XX', 'XXXXX.X', 'XXXXX.X', 'XXX..XX', 'XXX.XXX',  # memory
               'XXXXXXX', 'XXX.XXX', 'XXXXXXX', 'XXXXXXX', '.......', '.......']),
]


def icon_bytes(k):
    """Icon k (model.KINDS order): ICON_H rows of 2 bytes."""
    colour, rows = ICON_SHAPES[k]
    palette, side = COLOURS.get(colour, (0, 'L'))      # (white: either palette)
    assert len(rows) == ICON_H and all(len(r) == 7 for r in rows), k
    out = []
    for r in rows:
        line = dots(r.replace('X', side))
        out.append([palette << 7 | sum(line[7 * b + i] << i for i in range(7)) if any(line[7 * b:7 * b + 7])
                    else 0 for b in range(2)])
    return out


# The game links one small design and tint for now (lot 6: packs in aux RAM).
GAME_SMALL = (0, 0)


def alien_shapes(design, tint):
    """The 14 entries (shift*2 + frame) of a small alien, rows of bytes."""
    _, a, b = SMALL[design]
    frames = [shifted(tinted(f, tint), TINTS[tint][0])[1] for f in (a, b)]
    return [frames[f][s] for s in range(7) for f in range(2)]


def combo_table(combo):
    """Bytes of design combo // 4, tint combo % 4, entry after entry."""
    return bytes(b for entry in alien_shapes(combo // 4, combo % 4) for row in entry for b in row)


def rock_shapes():
    """The 14 entries (shift*2 + frame) of the rock."""
    frames = [shifted(tinted(f, ROCK_TINT), TINTS[ROCK_TINT][0])[1] for f in ROCK]
    return [frames[f][s] for s in range(7) for f in range(2)]


def big_shapes(design, tint):
    """The 14 entries (shift*2 + frame) of a big alien (10 cells, 4 bytes)."""
    _, a, b = BIG[design]
    frames = [shifted(tinted(f, tint), TINTS[tint][0])[1] for f in (a, b)]
    return [frames[f][s] for s in range(7) for f in range(2)]


def big_table(combo):
    return bytes(b for entry in big_shapes(combo // 4, combo % 4) for row in entry for b in row)


def aux_image():
    """WG2.AUX: the 24 small tables, the 8 big ones, then the rock."""
    return b''.join(combo_table(c) for c in range(len(SMALL) * len(TINTS))) + \
        b''.join(big_table(c) for c in range(len(BIG) * len(TINTS))) + \
        bytes(b for entry in rock_shapes() for row in entry for b in row)


def tinted(drawing, tint):
    side = TINTS[tint][1]
    return [r.replace('X', side) for r in drawing]


def dots(row):
    """Cell string -> list of dots (0/1), two per cell."""
    out = []
    for c in row:
        out += {'.': (0, 0), 'W': (1, 1), 'L': (1, 0), 'R': (0, 1)}[c]
    return out


def shifted(drawing, palette, nbytes=None):
    """-> (byte width, [7 lists of rows of bytes])."""
    width = len(drawing[0])
    assert all(len(r) == width for r in drawing)
    nbytes = nbytes or max((2 * s % 7 + 2 * width + 6) // 7 for s in range(7))
    phases = []
    for s in range(7):
        start = 2 * s % 7               # first dot inside the start byte
        rows = []
        for r in drawing:
            line = [0] * start + dots(r)
            line = (line + [0] * (7 * nbytes))[:7 * nbytes]
            rows.append([palette << 7 | sum(line[7 * b + i] << i for i in range(7))
                         for b in range(nbytes)])
        phases.append(rows)
    return nbytes, phases


def table(out, name, frames, palette):
    """Shift-major tables: entry 2*s+f (or s with one frame)."""
    shapes = [shifted(f, palette, 1 if name in ONE_BYTE else None) for f in frames]
    nbytes = shapes[0][0]
    entries = [(s, f) for s in range(7) for f in range(len(frames))]
    labels = [f'{name}_s{s}' + (f'f{f}' if len(frames) > 1 else '') for s, f in entries]
    up = name.upper()
    if name in ONE_BYTE:                # one byte, same on every row: the pattern
        assert all(len(set(map(tuple, shapes[0][1][sh]))) == 1 for sh in range(7))
        out.append(f'{name}_pat: .byte ' + ','.join(f'${shapes[0][1][sh][0][0]:02X}' for sh in range(7)))
    out.append(f'{up}_W = {nbytes}              ; bytes per row')
    out.append(f'{up}_H = {len(frames[0])}')
    out.append(f'{up}_CELLS = {len(frames[0][0])}')
    out.append(f'{name}_lo: .lobytes ' + ','.join(labels))
    out.append(f'{name}_hi: .hibytes ' + ','.join(labels))
    for (s, f), label in zip(entries, labels):
        out.append(f'{label}:')
        for row in shapes[f][1][s]:
            out.append('        .byte ' + ','.join(f'${b:02X}' for b in row))


def emit():
    out = ['; Generated by tools/sprites.py -- do not edit.']
    out.append('; cell x (0..139, two dots each, cell 0 at byte FIELD_COL: lot 10) -> byte column of the shift start, shift')
    out.append('cell_byte:')
    for i in range(0, 140, 14):
        out.append('        .byte ' + ','.join(str(FIELD_COL + 2 * (c // 7) + (2 * (c % 7) >= 7)) for c in range(i, i + 14)))
    out.append('cell_shift:')
    for i in range(0, 140, 14):
        out.append('        .byte ' + ','.join(str(c % 7) for c in range(i, i + 14)))
    out.append('cell_shift2:                    ; shift * 2: alien table entry, frame 0')
    for i in range(0, 140, 14):
        out.append('        .byte ' + ','.join(str(c % 7 * 2) for c in range(i, i + 14)))
    for name, (palette, drawing) in SPRITES.items():
        table(out, name, [drawing], palette)
    # Small aliens: every design x tint in WG2.AUX (aux memory); the game
    # copies the current pack's table to cur_alien (lot 6).
    out.append(f'ALIEN_W = {ALIEN_BYTES}              ; bytes per row')
    out.append(f'ALIEN_H = {len(SMALL[0][1])}')
    out.append(f'ALIEN_CELLS = {len(SMALL[0][1][0])}')
    out.append(f'ALIEN_TABLE = {ALIEN_TABLE}          ; bytes: 7 shifts x 2 frames x rows x width')
    out.append(f'NCOMBOS = {len(SMALL) * len(TINTS)}')
    out.append('AUX_BASE = $2000              ; aux memory: WG2.AUX')
    out.append(f'BIG_W = {BIG_BYTES}')
    out.append(f'BIG_TABLE = {BIG_TABLE}')
    out.append(f'NBIG = {len(BIG) * len(TINTS)}')
    out.append(f'AUX_BIG = AUX_BASE + {ALIEN_TABLE * len(SMALL) * len(TINTS)}')
    entry = BIG_TABLE // 14
    out.append('big_lo: .lobytes ' + ','.join(f'cur_big+{entry * e}' for e in range(14)))
    out.append('big_hi: .hibytes ' + ','.join(f'cur_big+{entry * e}' for e in range(14)))
    out.append(f'AUX_ROCK = AUX_BIG + {BIG_TABLE * len(BIG) * len(TINTS)}')
    out.append(f'AUX_SIZE = {len(aux_image())}')
    table(out, 'boom', list(BOOM[1:]), BOOM[0])
    # the boss leaps 7 cells at a time from a multiple of 7: shift 0 only
    nb = (2 * len(BOSS[1][0]) + 6) // 7
    rows = shifted(tinted(BOSS[1], 3), BOSS[0], nb)[1][0]
    out.append(f'BOSS_W = {nb}')
    out.append(f'BOSS_H = {len(BOSS[1])}')
    out.append(f'BOSS_CELLS = {len(BOSS[1][0])}')
    out.append('boss_s0:')
    for row in rows:
        out.append('        .byte ' + ','.join(f'${b:02X}' for b in row))
    table(out, 'shipboom', list(SHIPBOOM[1:]), SHIPBOOM[0])
    # Flying things share one pointer table: alien entries, then explosion
    # entries (render.s keeps the entry it drew, to EOR it away).
    out.append(f'; objects: {2 * ICON_H} bytes each (2 a row), in model.KINDS order')
    out.append(f'NKINDS = {len(ICON_SHAPES)}')
    out.append(f'ICON_H = {ICON_H}')
    out.append('.pushseg')
    out.append('.segment "HIDATA"                ; resident at $1C40 (game.cfg)')
    out.append('icons:')
    for k in range(len(ICON_SHAPES)):
        out.append('        .byte ' + ','.join(f'${b:02X}' for row in icon_bytes(k) for b in row)
                   + f'   ; {ICON_SHAPES[k][0]}')
    out.append('.popseg')
    out.append('icon_lo: .lobytes ' + ','.join(f'icons+{2 * ICON_H * k}' for k in range(len(ICON_SHAPES))))
    out.append('icon_hi: .hibytes ' + ','.join(f'icons+{2 * ICON_H * k}' for k in range(len(ICON_SHAPES))))
    out.append('BOOM_ENTRY = 14')
    entry = ALIEN_TABLE // 14
    out.append('fly_lo: .lobytes ' + ','.join([f'cur_alien+{entry * e}' for e in range(14)]
                                               + [f'boom_s{s}f{f}' for s in range(7) for f in range(2)]))
    out.append('fly_hi: .hibytes ' + ','.join([f'cur_alien+{entry * e}' for e in range(14)]
                                               + [f'boom_s{s}f{f}' for s in range(7) for f in range(2)]))
    return '\n'.join(out) + '\n'


# --- preview ----------------------------------------------------------------
RGB = {('L', 0): (0xC0, 0x40, 0xFF), ('R', 0): (0x40, 0xE0, 0x40),
       ('L', 1): (0x40, 0x90, 0xFF), ('R', 1): (0xFF, 0x80, 0x20)}


def png(path, scale=4):
    sheets = []                         # (palette, drawing)
    for _, a, b in SMALL:
        for t in range(4):
            sheets += [(TINTS[t][0], tinted(a, t)), (TINTS[t][0], tinted(b, t))]
    for _, a, b in BIG:
        for t in range(4):
            sheets += [(TINTS[t][0], tinted(a, t)), (TINTS[t][0], tinted(b, t))]
    sheets += [(p, d) for p, d in SPRITES.values()]
    sheets += [(BOOM[0], BOOM[1]), (BOOM[0], BOOM[2]), (SHIPBOOM[0], SHIPBOOM[1]), (SHIPBOOM[0], SHIPBOOM[2])]
    sheets += [(BOSS[0], tinted(BOSS[1], 3))]
    sheets += [(TINTS[ROCK_TINT][0], tinted(f, ROCK_TINT)) for f in ROCK]
    per_row, cw, ch = 8, 18, 26          # cells per slot
    rows = (len(sheets) + per_row - 1) // per_row
    w, h = per_row * cw * 2 * scale, rows * ch * scale
    pix = [[(0, 0, 0)] * w for _ in range(h)]
    for k, (palette, d) in enumerate(sheets):
        ox, oy = (k % per_row) * cw * 2 * scale, (k // per_row) * ch * scale
        for y, row in enumerate(d):
            for c, ch_ in enumerate(row):
                if ch_ == '.':
                    continue
                cols = {'W': (0, 1), 'L': (0,), 'R': (1,)}[ch_]
                for half in cols:
                    rgb = (255, 255, 255) if ch_ == 'W' else RGB[(ch_, palette)]
                    for yy in range(scale):
                        for xx in range(scale):
                            pix[oy + y * scale + yy][ox + (2 * c + half) * scale + xx] = rgb
    write_png(path, pix)


def write_png(path, pix):
    """pix: rows of (r, g, b), all the same length."""
    w, h = len(pix[0]), len(pix)
    raw = b''.join(b'\0' + bytes(v for p in line for v in p) for line in pix)
    chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


ALIEN_BYTES = 3
ALIEN_TABLE = 14 * 8 * ALIEN_BYTES
BIG_BYTES = 4
BIG_TABLE = 14 * 16 * BIG_BYTES


def main():
    assert len(combo_table(0)) == ALIEN_TABLE and len(big_table(0)) == BIG_TABLE
    if '--aux' in sys.argv:
        Path(sys.argv[sys.argv.index('--aux') + 1]).write_bytes(aux_image())
        return
    for _, a, b in SMALL:
        assert len(a) == len(b) == 8 and all(len(r) == 7 for r in a + b)
    for _, a, b in BIG:
        assert len(a) == len(b) == 16 and all(len(r) == 10 for r in a + b)
    assert all(len(f) == 8 and all(len(r) == 7 for r in f) for f in ROCK)
    if '--png' in sys.argv:
        png(sys.argv[sys.argv.index('--png') + 1])
        return
    text = emit()
    if '--check' in sys.argv:
        if OUT.read_text() != text:
            sys.exit(f'{OUT} is stale: run tools/sprites.py')
        return
    if not OUT.exists() or OUT.read_text() != text:
        OUT.write_text(text)


if __name__ == '__main__':
    main()
