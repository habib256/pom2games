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
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'dev/tools'))
import apple2img
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
    'bomb': (0, [               # one byte wide, white (2026-10-30: coloured
        'W',                    # dots were taken for stars)
        'W',
        'W',
        'W',
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
# Lot 11, Warblade's rocks of every size: a small one in the same box
# (cur_alien2: its drawing inside cells 1-5, rows 1-6, the hit box) and a
# big one in a big alien's (cur_big, two-tone), WG2.AUX after the boss.
SMALL_ROCK = ([
    '.......',
    '..WWX..',
    '.WWXWW.',
    '.XWWWX.',
    '.WWXWW.',
    '..XWX..',
    '.......',
    '.......',
], [
    '.......',
    '..XWW..',
    '.WWWXW.',
    '.WXWWW.',
    '.XWWWX.',
    '..WWX..',
    '.......',
    '.......',
])
BIG_ROCK = ([
    '...WWWX...',
    '..WWXWWWX.',
    '.WWWWWXWWX',
    'WWXWWWWWWX',
    'WWWWYYWWXX',
    'XWWWYYWWWX',
    'WWWWWWWXWX',
    'WXWWWWWWWX',
    'WWWWWXWWYX',
    'XWWYWWWWWX',
    'WWWYYWWXWX',
    '.WWWWWWWXX',
    '.XWWXWWWX.',
    '..XWWWWX..',
    '...XXXX...',
    '..........',
], [
    '...XWWW...',
    '.XWWWXWW..',
    'XWWXWWWWW.',
    'XWWWWWWXWW',
    'XXWWYYWWWW',
    'XWWWYYWWWX',
    'XWXWWWWWWW',
    'XWWWWWWWXW',
    'XYWWXWWWWW',
    'XWWWWWYWWX',
    'XWXWWYYWWW',
    'XXWWWWWWW.',
    '.XWWWXWWX.',
    '..XWWWWX..',
    '...XXXX...',
    '..........',
])

# Clipped to the shift's start byte (a shot is one byte wide, so at shift 3
# only its left dot shows): half the cost of a two-byte sprite.
ONE_BYTE = {'shot', 'bomb'}

TINTS = ((0, 'L'), (0, 'R'), (1, 'L'), (1, 'R'))   # violet, green, blue, orange

# The boss (levels 25, 50, 75, 100): 16 cells x 24 rows, orange.
# The boss (lot 10c: bigger, two-tone, moving a cell at a time): 24 cells x
# 28 rows, the left half mirrored; an original mothership after Warblade's
# big bosses: a dome over a white core (cells 9-14, the only part shots
# hurt), claws (Y: the palette's other colour), engines and stingers.
BOSS_HALF = [
    '..........WW',
    '........WWXX',
    '.......WXXWW',
    '......WXXW.W',
    'Y.....WXW.XW',
    'YY...WXXW.XW',
    'YYY..WXW..WW',
    '.YYYWXXWWWWX',
    '..YYWXXXXXWX',
    '...YWWWWWWXW',
    '..YYYYWXXXXW',
    '.YY..YWXWWXX',
    'YY...YWXW.XW',
    'Y....YWXW.XW',
    '.....YWXXWWX',
    '....YYYWXXXW',
    '...YY..YWWXX',
    '..YY....YWXW',
    '.YY.....YWXX',
    'YY......YXWW',
    'Y......YXX.W',
    '......YX...W',
    '.....YX....W',
    '....YX.....W',
    '...YX....YWX',
    '..YX.....YXX',
    '..X......YXW',
    '.........Y.X',
]
BOSS = (1, [r + r[::-1] for r in BOSS_HALF])
BOSS_TINT = 3                   # orange, claws blue

# Falling objects (lot 5; redrawn for legibility 2026-10-23, silhouettes 10-30): 7 cells x
# ICON_H rows on an even byte column (an object never moves sideways, so no
# shifts), drawn in cells (two dots: white strokes stay white, no colour
# fringes). A family = a shape, its colour says which one:
#   coins          a disc with a $ cut out (green 10, orange 50, blue 100,
#                  violet 200)
#   gauges         a blue tile, S B T in white (the HUD's letters)
#   weapons        a violet cannon under one, two, three white shots;
#                  autofire: a stream
#   multipliers    an orange gem, 2 or 5 cut out
#   EXTRA letters  a white tile, E X T R A cut out (the HUD's row)
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
DIGIT3['0'] = ['WWW', 'W.W', 'W.W', 'W.W', 'WWW']
DIGIT3['K'] = ['W.W', 'WW.', 'W..', 'WW.', 'W.W']


def tab(top):
    """Lot 11, Meteor Storm's point tabs: a square tablet of colour, the
    thousands (3 x 5 digits, '1' narrow beside another) cut out above a K."""
    out = [list('XXXXXXX') for _ in range(13)]
    glyphs = [['W'] * 5 if ch == '1' and len(top) > 1 else DIGIT3[ch] for ch in top]
    for line, cut in ((1, glyphs), (7, [DIGIT3['K']])):
        width = sum(len(g[0]) for g in cut) + len(cut) - 1
        x = (7 - width) // 2
        for g in cut:
            for y, r in enumerate(g):
                for dx, c in enumerate(r):
                    if c == 'W':
                        out[line + y][x + dx] = '.'
            x += len(g[0]) + 1
    return [''.join(r) for r in out]


def cut5(glyph, shape, colour='X', ink='.'):
    """A 7 x 13 silhouette (X) with a 5 x 7 glyph cut out (black) in its
    rows 3-9, one cell of colour around it (or written in ink)."""
    out = [list(r.replace('X', colour)) for r in shape]
    for y, r in enumerate(FONT5[glyph]):
        for x, c in enumerate(r):
            if c == 'W':
                out[3 + y][1 + x] = ink
    return [''.join(r) for r in out]


# Silhouettes (2026-10-30: were a white glyph between two bars, little colour
# and one shape for four families): one per family, the glyph cut out.
TILE = ['.XXXXX.'] + ['XXXXXXX'] * 11 + ['.XXXXX.']                 # gauges, letters
CANNON = ['...X...', '..XXX..', '..XXX..', '.XXXXX.', 'XXXXXXX', 'XXXXXXX', 'XX...XX']  # weapons,
SHOTS = {                                                           # under their white shots
    'w1': ['...W...', '...W...', '.......', '...W...', '...W...', '.......'],
    'w2': ['.W...W.', '.W...W.', '.......', '.W...W.', '.W...W.', '.......'],
    'w3': ['W..W..W', 'W..W..W', '.......', '.W.W.W.', '.W.W.W.', '.......'],
    'auto': ['..W.W..', '.......', '..W.W..', '.......', '..W.W..', '.......'],
}
GEM = ['...X...', '..XXX..', '.XXXXX.'] + ['XXXXXXX'] * 7 + ['.XXXXX.', '..XXX..', '...X...']  # multipliers


def pill(glyph, cap='X'):
    """Lot 5's family marks, now a silhouette: a tile (gauges; white for the
    EXTRA letters), a gem (multipliers); weapons: a cannon and its shots."""
    if glyph in SHOTS:
        return SHOTS[glyph] + CANNON
    if glyph in ('S', 'B', 'T') and cap == 'X':     # (white on blue: no blue coin)
        return cut5(glyph, TILE, cap, 'W')
    return cut5(glyph, GEM if glyph in ('2', '5') else TILE, cap)


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
    ('green', tab('1')), ('orange', tab('5')), ('white', [r.replace('X', 'W') for r in tab('10')]),  # tabs
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
    frames = [shifted(tinted(two_tone(f), tint), TINTS[tint][0])[1] for f in (a, b)]
    return [frames[f][s] for s in range(7) for f in range(2)]


def combo_table(combo):
    """Bytes of design combo // 4, tint combo % 4, entry after entry."""
    return bytes(b for entry in alien_shapes(combo // 4, combo % 4) for row in entry for b in row)


def rock_shapes():
    """The 14 entries (shift*2 + frame) of the rock."""
    frames = [shifted(tinted(f, ROCK_TINT), TINTS[ROCK_TINT][0])[1] for f in ROCK]
    return [frames[f][s] for s in range(7) for f in range(2)]


def small_rock_shapes():
    frames = [shifted(tinted(f, ROCK_TINT), TINTS[ROCK_TINT][0])[1] for f in SMALL_ROCK]
    return [frames[f][s] for s in range(7) for f in range(2)]


def big_rock_shapes():
    frames = [shifted(tinted(f, ROCK_TINT), TINTS[ROCK_TINT][0])[1] for f in BIG_ROCK]
    return [frames[f][s] for s in range(7) for f in range(2)]


def storm_image():
    """WG2.AUX after the boss (lot 11): the small rock's table, the big one's."""
    return bytes(b for shapes in (small_rock_shapes(), big_rock_shapes())
                 for entry in shapes for row in entry for b in row)


def big_shapes(design, tint):
    """The 14 entries (shift*2 + frame) of a big alien (10 cells, 4 bytes)."""
    _, a, b = BIG[design]
    frames = [shifted(tinted(two_tone(f), tint), TINTS[tint][0])[1] for f in (a, b)]
    return [frames[f][s] for s in range(7) for f in range(2)]


def boss_shapes():
    """-> (bytes a row, the 7 shifts' rows of bytes) of the boss with an
    empty cell on each side: drawn with STA at cell x - 1, it wipes where
    it was a cell away (render.s boss_draw)."""
    drawing = ['.' + r + '.' for r in BOSS[1]]
    nb = max((2 * s % 7 + 2 * len(drawing[0]) + 6) // 7 for s in range(7))
    shapes = shifted(tinted(drawing, BOSS_TINT), BOSS[0], nb)[1]
    # (a byte without a dot: 0, not the palette bit alone, which its STA
    # would leave behind as a non-black byte: no star there)
    return nb, [[[b if b & 0x7F else 0 for b in row] for row in shape] for shape in shapes]


def boss_image():
    """WG2.AUX at BOSS_AUX: shift after shift, rows top to bottom."""
    return bytes(b for shape in boss_shapes()[1] for row in shape for b in row)


def big_table(combo):
    return bytes(b for entry in big_shapes(combo // 4, combo % 4) for row in entry for b in row)


def aux_image():
    """WG2.AUX: the 24 small tables, the 8 big ones, then the rock."""
    return b''.join(combo_table(c) for c in range(len(SMALL) * len(TINTS))) + \
        b''.join(big_table(c) for c in range(len(BIG) * len(TINTS))) + \
        bytes(b for entry in rock_shapes() for row in entry for b in row)


def tinted(drawing, tint):
    """X -> the tint's dot; Y (two_tone) -> the palette's other dot."""
    side = TINTS[tint][1]
    other = {'L': 'R', 'R': 'L'}[side]
    return [r.replace('X', side).replace('Y', other) for r in drawing]


def two_tone(drawing):
    """Lot 10b, Warblade's two-coloured aliens: the X of the two outer
    columns on each side (wings, claws) become Y, the palette's other
    colour (violet body, green wings; blue and orange)."""
    w = len(drawing[0])
    wings = {0, 1, w - 2, w - 1}
    return [''.join('Y' if ch == 'X' and c in wings else ch for c, ch in enumerate(r)) for r in drawing]


def dots(row):
    """Cell string -> list of dots (0/1), two per cell."""
    out = []
    for c in row:
        out += {'.': (0, 0), 'W': (1, 1), 'L': (1, 0), 'R': (0, 1)}[c]
    return out


def shifted(drawing, palette, nbytes=None):
    """-> (byte width, [7 lists of rows of bytes])."""
    assert all(len(r) == len(drawing[0]) for r in drawing)
    # Shift s starts at dot 2*s % 7; one byte: a dot left rather than cut
    # (fit), shots and bombs stay white.
    ph = apple2img.preshift7([dots(r) for r in drawing], 2 * len(drawing[0]), nbytes, palette,
                             step=2, fit=nbytes == 1)
    return len(ph[0][0]), ph


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
    out.append('AUX_BASE = $2000              ; aux memory: WG2.AUX (the PT3 player first)')
    out.append('AUX_PACKS = $3000             ; the alien packs (2026-10-30: were at $2000)')
    out.append(f'BIG_W = {BIG_BYTES}')
    out.append(f'BIG_TABLE = {BIG_TABLE}')
    out.append(f'NBIG = {len(BIG) * len(TINTS)}')
    out.append(f'AUX_BIG = AUX_PACKS + {ALIEN_TABLE * len(SMALL) * len(TINTS)}')
    entry = BIG_TABLE // 14
    out.append('big_lo: .lobytes ' + ','.join(f'cur_big+{entry * e}' for e in range(14)))
    out.append('big_hi: .hibytes ' + ','.join(f'cur_big+{entry * e}' for e in range(14)))
    out.append(f'AUX_ROCK = AUX_BIG + {BIG_TABLE * len(BIG) * len(TINTS)}')
    out.append(f'AUX_SIZE = {len(aux_image())}')
    table(out, 'boom', list(BOOM[1:]), BOOM[0])
    # The boss (lot 10c): its 7 shifts in WG2.AUX (boss_image); on a boss
    # level boss_check copies shifts 0-3 to iobuf, 4-6 to cur_big (free
    # there: no walls to draw, no big alien, one species).
    nb, _ = boss_shapes()
    size = nb * len(BOSS[1])
    out.append(f'BOSS_W = {nb}')
    out.append(f'BOSS_H = {len(BOSS[1])}')
    out.append(f'BOSS_CELLS = {len(BOSS[1][0])}')
    out.append(f'BOSS_SHIFT = {size}             ; bytes a shift')
    places = [f'iobuf+{size * k}' for k in range(4)] + [f'cur_big+{size * k}' for k in range(3)]
    out.append('boss_lo: .lobytes ' + ','.join(places))
    out.append('boss_hi: .hibytes ' + ','.join(places))
    out.append(f'.assert 4 * BOSS_SHIFT <= 1024 && 3 * BOSS_SHIFT <= BIG_TABLE, error, "the boss\'s shifts"')
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
    # (lot 10b: then the second species' entries, from DESIGN2 = 28)
    fly = ([f'cur_alien+{entry * e}' for e in range(14)] + [f'boom_s{s}f{f}' for s in range(7) for f in range(2)]
           + [f'cur_alien2+{entry * e}' for e in range(14)])
    out.append('fly_lo: .lobytes ' + ','.join(fly))
    out.append('fly_hi: .hibytes ' + ','.join(fly))
    return '\n'.join(out) + '\n'


# --- preview ----------------------------------------------------------------
RGB = {('L', 0): (0xC0, 0x40, 0xFF), ('R', 0): (0x40, 0xE0, 0x40),
       ('L', 1): (0x40, 0x90, 0xFF), ('R', 1): (0xFF, 0x80, 0x20)}


def png(path, scale=4):
    sheets = []                         # (palette, drawing)
    for _, a, b in SMALL + BIG:
        for t in range(4):
            sheets += [(TINTS[t][0], tinted(two_tone(a), t)), (TINTS[t][0], tinted(two_tone(b), t))]
    sheets += [(p, d) for p, d in SPRITES.values()]
    sheets += [(BOOM[0], BOOM[1]), (BOOM[0], BOOM[2]), (SHIPBOOM[0], SHIPBOOM[1]), (SHIPBOOM[0], SHIPBOOM[2])]
    sheets += [(BOSS[0], tinted(BOSS[1], BOSS_TINT))]
    sheets += [(TINTS[ROCK_TINT][0], tinted(f, ROCK_TINT)) for f in ROCK]
    per_row, cw, ch = 8, 26, 30          # cells per slot (the boss: 24 x 28)
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
    """pix: rows of (r, g, b), all the same length (walls.py too)."""
    apple2img.png_write(path, pix)


ALIEN_BYTES = 3
ALIEN_TABLE = 14 * 8 * ALIEN_BYTES
BIG_BYTES = 4
BIG_TABLE = 14 * 16 * BIG_BYTES


def main():
    assert len(combo_table(0)) == ALIEN_TABLE and len(big_table(0)) == BIG_TABLE
    if '--aux' in sys.argv:
        Path(sys.argv[sys.argv.index('--aux') + 1]).write_bytes(aux_image())
        return
    if '--boss' in sys.argv:
        Path(sys.argv[sys.argv.index('--boss') + 1]).write_bytes(boss_image())
        return
    if '--storm' in sys.argv:
        Path(sys.argv[sys.argv.index('--storm') + 1]).write_bytes(storm_image())
        return
    for _, a, b in SMALL:
        assert len(a) == len(b) == 8 and all(len(r) == 7 for r in a + b)
    for _, a, b in BIG:
        assert len(a) == len(b) == 16 and all(len(r) == 10 for r in a + b)
    assert all(len(f) == 8 and all(len(r) == 7 for r in f) for f in ROCK + SMALL_ROCK)
    assert all(len(f) == 16 and all(len(r) == 10 for r in f) for f in BIG_ROCK)
    assert len(storm_image()) == ALIEN_TABLE + BIG_TABLE
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
