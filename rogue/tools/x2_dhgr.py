#!/usr/bin/env python3
"""ROGUE.DHGR, the X2 way: the playfield at x2 in big colour cells.

    python3 tools/x2_dhgr.py src/video_x2_data.inc [--png DIR]

The design is POM1's ROGUE X2 (sketchs/gen2/game_rogue_x2, HGR on the
Apple-1): the 16 x 10 map is not shown whole, but through a window of big
cells CENTRE-LOCKED on the hero, who always sits in the middle cell; the
window hangs past the map edges (off-map cells are black); every move
scrolls it by one cell, a free action (bump, rest, dagger flight) keeps it.
Colours per entity are baked into the art.

On the //e double hi-res screen (140 x 192 colour pixels):

  - a cell = 14 x 32 colour pixels = exactly two groups of 7 pixels (4
    bytes each, aux / main interleaved): byte-aligned blits, no shifting.
    A TMS 16 x 16 tile or sprite loses 2 columns (blank ones for the
    sprites, the outer ones for the tiles, two inner ones for the wall so
    its bricks stay 7 pixels apart) and doubles its lines;
  - the window = 9 x 5 cells (126 x 160 pixels, groups 1..18, lines
    0..159), the hero in cell (4, 2): truly centred (X2: 8 x 5, the hero
    at (3, 2), half a cell off);
  - lines 160..191 (text rows 20..23, the HUD) and every full-page screen
    (title, briefing, bag, help, death, victory) stay the halved TMS
    picture of tools/tiles_dhgr.py; the title's "ROGUE" becomes a big
    banner (BANNER below).

The back-end (src/video_x2.asm) derives everything from the core's virtual
TMS9918 screen (docs/VIDEO_API.md):

  - game or full-page screen: a name >= 32 (text) in rows 0..19 = a page;
  - the camera: sprite 0 when it is the hero (name 0, on the 16-pixel
    grid, above row 20): window column 0 = hero column - 4, row 0 = hero
    row - 2 (else the last camera);
  - a cell's tile: the name at its top left (base 0..28 of its 4 names),
    / 4: 0 floor or unseen (black), 1 wall, 2 stairs, 3 door, 4 arch,
    5 pit, 6 gold, 7 potion;
  - its sprites: the entries on the 16-pixel grid above row 20 (the HUD
    icons are below), the two front ones (lower entry = in front, as on
    the chip) per cell: name / 4 -> the art (the boss = 4 cells), its ink
    from the entity (INK), colour 8 (the core's "hit" red) on anything but
    the boss -> its FLASH ink.

Data (video_x2_data.inc, byte-stable): every asset as two 7-pixel halves a
row (bit 6 = left pixel), 16 rows; inks as DHGR pixel values (the 4 dots,
tiles_dhgr.nib); the dot masks of one pixel (x2_pm: the back-end builds
its 4 x 128 half masks from them at start); the banner's rows.
render_screen() is the model the tests compare both DHGR pages with.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'dev/tools'))
sys.path.insert(0, str(ROOT / 'tools'))
from apple2img import png_write, dhgr_from_colors, dhgr_to_rgb  # noqa: E402
from fonts import asm_bytes, write_if_changed  # noqa: E402
import tiles_dhgr  # noqa: E402

VW, VH = 9, 5               # window, cells
HERO_VC, HERO_VR = 4, 2     # the hero's cell in it
CW, CH = 14, 32             # a cell, colour pixels x lines
X0 = 7                      # first pixel of the window (group 1)
MAP_W, MAP_H = 16, 10

# DHGR colour numbers (LORES numbering, apple2img.PALETTE):
# 0 black 1 magenta 2 dark blue 3 purple 4 dark green 5 grey 6 medium blue
# 7 light blue 8 brown 9 orange 10 grey 11 pink 12 green 13 yellow 14 aqua
# 15 white
TILES = [  # (TMS base, columns dropped, ink): X2's table (TILE_HUES)
    (0, (0, 15), 0),        # floor / unseen: black
    (4, (3, 11), 5),        # wall: grey (TMS grey; X2 white)
    (8, (0, 15), 12),       # stairs down: green
    (12, (0, 15), 9),       # door: orange
    (16, (0, 15), 13),      # arch / rubble: yellow (TMS light yellow; X2 white)
    (20, (0, 15), 3),       # pit: violet
    (24, (0, 15), 9),       # gold (reserved): orange
    (28, (0, 15), 3),       # potion (reserved): violet
]
SPRITES = [  # (name / 4, columns dropped, ink): the hero and the monsters
    # in X2's SPRITE_HUES, in DHGR; the items in their TMS colour through
    # tiles_dhgr.PALETTE_MAP (the core's item_color_table), the colour the
    # bag and the HUD icons show them in (X2 had only 4 hues to choose from)
    ('hero', (0, 15), 7),           # light blue (TMS light blue)
    ('undead', (0, 15), 12),        # green
    ('ghost', (0, 15), 3),          # violet
    ('death', (0, 15), 9),          # orange
    ('ration', (0, 15), 13),        # TMS 11 light yellow -> yellow
    ('skeleton', (0, 15), 15),      # white bones
    ('dagger', (0, 15), 5),         # TMS 14 grey
    ('potion', (0, 15), 3),         # TMS 13 magenta -> violet
    ('scroll', (0, 15), 14),        # TMS 7 cyan -> aqua
    ('sword', (0, 15), 15),         # TMS 15 white
    ('tunic', (0, 15), 1),          # TMS 6 dark red -> magenta (deep red)
    ('amulet', (0, 15), 13),        # TMS 10 dark yellow -> yellow
    ('troll', (0, 15), 12),         # green
    ('torch', (0, 15), 11),         # TMS 9 light red -> pink
    ('boss_tl', (0, 1), 9),         # the demon, 2 x 2 cells: orange; its
    ('boss_tr', (14, 15), 9),       # quarters lose their outer columns
    ('boss_bl', (0, 1), 9),         # (blank: nothing lost, the halves
    ('boss_br', (14, 15), 9),       # still meet)
]
ITEM_TMS = {4: 11, 6: 14, 7: 13, 8: 7, 9: 15, 10: 6, 11: 10, 13: 9}   # art -> TMS colour
BOSS0 = 14                  # first boss quarter (name 56)


def flash_ink(ink):
    """A hit: orange, or white for what is orange already."""
    return 15 if ink == 9 else 9


# the title's banner: "ROGUE" in the TMS font, each TMS pixel 2 colour
# pixels x 4 lines, rows 3..6 (lines 24..55), x = 30..109 (groups 4..15)
BANNER_TEXT = 'ROGUE'
BANNER_ROW, BANNER_COL = 4, 13      # where the core writes it (title_table)
BANNER_Y0, BANNER_G0, BANNER_NG = 24, 4, 12
BANNER_X = 2                        # its first pixel in group BANNER_G0
BANNER_INK = [13, 13, 13, 9, 9, 9, 1, 1]    # per glyph row: yellow, orange, red


# ------------------------------------------------------------------ assets

def cell16(chars, base):
    """The 16 rows (16 bits, MSB = left) of the 2x2 tile at name base."""
    return [chars[8 * (base + (0 if r < 8 else 2)) + r % 8] << 8 |
            chars[8 * (base + (1 if r < 8 else 3)) + r % 8] for r in range(16)]


def sprite16(spr, s):
    blk = spr[32 * s:32 * s + 32]
    return [blk[r] << 8 | blk[16 + r] for r in range(16)]


def drop14(rows, drop):
    """16-pixel rows -> 14-pixel rows (bit 13 = left), columns `drop` gone."""
    keep = [c for c in range(16) if c not in drop]
    return [sum(1 << (13 - i) for i, c in enumerate(keep) if r >> (15 - c) & 1) for r in rows]


def load():
    chars, colours, spr = tiles_dhgr.load_inputs(ROOT / 'src')
    for art, tms in ITEM_TMS.items():
        if SPRITES[art][2] != tiles_dhgr.PALETTE_MAP[tms]:
            raise SystemExit(f'{SPRITES[art][0]}: not its TMS colour')
    tiles = [(drop14(cell16(chars, b), d), ink) for b, d, ink in TILES]
    sprites = [(drop14(sprite16(spr, s), d), ink) for s, (_, d, ink) in enumerate(SPRITES)]
    lost = [(SPRITES[s][0], sum(bin(r).count('1') for r in sprite16(spr, s)) -
             sum(bin(r).count('1') for r in sprites[s][0])) for s in range(len(SPRITES))]
    banner = []
    for gr in range(8):
        bits = [0] * (7 * BANNER_NG)
        for i, ch in enumerate(BANNER_TEXT):
            g = chars[8 * ord(ch) + gr]
            for k in range(8):
                if g >> (7 - k) & 1:
                    x = BANNER_X + 16 * i + 2 * k
                    bits[x] = bits[x + 1] = 1
        banner.append(bits)
    return dict(tiles=tiles, sprites=sprites, lost=lost, banner=banner,
                tdata=tiles_dhgr.load_data()[1])


# ------------------------------------------------------------------ model

def is_page(names):
    """A full-page screen (text in the map rows), else the game view."""
    return any(n >= 32 for n in names[:640])


def banner_on(names):
    row = names[32 * BANNER_ROW:32 * BANNER_ROW + 32]
    c = BANNER_COL
    return bytes(row[c:c + len(BANNER_TEXT)]) == BANNER_TEXT.encode() and \
        row[c - 1] == 0 and row[c + len(BANNER_TEXT)] == 0


def hero_cam(sat):
    """The camera (window column 0, row 0 in map cells) from sprite 0, or None."""
    y, x, name, col = sat[0:4]
    if y == 0xD0 or y >= 160 or name != 0 or (y | x) & 15:
        return None
    return (x >> 4) - HERO_VC, (y >> 4) - HERO_VR


def cell_keys(names, sat, cam):
    """45 (tile, front sprite, back sprite) keys, row by row; sprite codes:
    0 none, else name / 4 + 1, + $40 for the flash ink."""
    cc, cr = cam
    keys = []
    spr = [[] for _ in range(VW * VH)]
    for i in range(32):
        y, x, name, col = sat[4 * i:4 * i + 4]
        if y == 0xD0:
            break
        if y >= 160 or (y | x) & 15 or col & 15 == 0 or name >= 72:
            continue
        vc, vr = (x >> 4) - cc, (y >> 4) - cr
        if 0 <= vc < VW and 0 <= vr < VH:
            code = (name >> 2) + 1
            if col & 15 == 8 and name >> 2 < BOSS0:
                code |= 0x40
            if len(spr[vr * VW + vc]) < 2:
                spr[vr * VW + vc].append(code)
    for vr in range(VH):
        for vc in range(VW):
            mc, mr = cc + vc, cr + vr
            t = 0
            if 0 <= mc < MAP_W and 0 <= mr < MAP_H:
                t = names[64 * mr + 2 * mc] >> 2
            s = spr[vr * VW + vc] + [0, 0]
            keys.append((t, s[0], s[1]))
    return keys


def render_cell(key, data):
    """14 x 32 colour pixels of one cell."""
    t, sa, sb = key
    rows, ink = data['tiles'][t]
    px = [[ink if r >> (13 - k) & 1 else 0 for k in range(CW)] for r in rows]
    for code in (sb, sa):
        if not code:
            continue
        srows, sink = data['sprites'][(code & 0x3F) - 1]
        if code & 0x40:
            sink = flash_ink(sink)
        for y, r in enumerate(srows):
            for k in range(CW):
                if r >> (13 - k) & 1:
                    px[y][k] = sink
    out = []
    for r in px:
        out += [r, list(r)]
    return out


def render_screen(names, sat, data, cam=None):
    """192 rows of 140 DHGR colour numbers: what each page must show for
    this virtual screen. cam: the back-end's camera when sprite 0 is not
    the hero (the last one it saw). Returns (pixels, 'page' / 'game', cam)."""
    px = tiles_dhgr.render(names, sat, data['tdata'])
    if is_page(names):
        if banner_on(names):
            for gr in range(8):
                ink = BANNER_INK[gr]
                for y in range(4):
                    line = px[BANNER_Y0 + 4 * gr + y]
                    line[:] = [0] * 140
                    for i, b in enumerate(data['banner'][gr]):
                        if b:
                            line[7 * BANNER_G0 + i] = ink
        return px, 'page', cam
    cam = hero_cam(sat) or cam or (0, 0)
    for y in range(160):
        px[y] = [0] * 140
    for i, key in enumerate(cell_keys(names, sat, cam)):
        vr, vc = divmod(i, VW)
        for y, row in enumerate(render_cell(key, data)):
            px[32 * vr + y][X0 + CW * vc:X0 + CW * (vc + 1)] = row
    return px, 'game', cam


# ------------------------------------------------------------------ output

def halves(rows):
    """14-pixel rows -> (left 7 pixels, right 7), bit 6 = left."""
    return [r >> 7 for r in rows], [r & 0x7F for r in rows]


def pixel_masks():
    """x2_pm + 7 j + p: the dots of pixel p (0..6) in byte j of its group."""
    pm = [0] * 28
    for p in range(7):
        for d in range(4):
            s = 4 * p + d
            pm[7 * (s // 7) + p] |= 1 << (s % 7)
    return pm


def inc_text(data):
    nib = tiles_dhgr.nib
    out = ['; video_x2_data.inc -- GENERATED by tools/x2_dhgr.py. DO NOT EDIT.',
           '; Tiles: Quale\'s SCROLL-O-SPRITES (CC-BY-3.0), boss: Hexany\'s Monster',
           '; Menagerie (CC0); the X2 design (cells, palette): POM1\'s game_rogue_x2.',
           '', '.segment "LCDATA"', '']

    def table(label, values, comment=None):
        if comment:
            out.append(f'; {comment}')
        out.append(f'{label}:')
        out.append(asm_bytes(values, per_line=16).rstrip('\n'))

    tl, tr = zip(*[halves(rows) for rows, _ in data['tiles']])
    table('x2_tb0', sum(tl, []), 'tiles (name / 4) x 16 rows: left 7 pixels (bit 6 = left)')
    table('x2_tb1', sum(tr, []), 'right 7 pixels')
    table('x2_tink', [nib(ink) for _, ink in data['tiles']], 'tile inks (DHGR pixel values)')
    sl, sr = zip(*[halves(rows) for rows, _ in data['sprites']])
    table('x2_sb0', sum(sl, []), 'sprites (name / 4) x 16 rows: left 7 pixels')
    table('x2_sb1', sum(sr, []), 'right 7 pixels')
    table('x2_sink', [nib(ink) for _, ink in data['sprites']], 'sprite inks')
    table('x2_sfl', [nib(flash_ink(ink)) for _, ink in data['sprites']], 'their hit flash')
    table('x2_pm', pixel_masks(), 'x2_pm + 7 j + p: the dots of pixel p in byte j of a group')
    ban = []
    for gr in range(8):
        bits = data['banner'][gr]
        ban += [sum(bits[7 * g + i] << (6 - i) for i in range(7)) for g in range(BANNER_NG)]
    table('x2_ban', ban, f'the title banner: 8 rows x {BANNER_NG} groups (bit 6 = left)')
    table('x2_bink', [nib(c) for c in BANNER_INK], 'its ink per row')
    return '\n'.join(out) + '\n'


# ------------------------------------------------------------------ previews

def mock(data):
    names, sat = tiles_dhgr.mock_screen()
    return render_screen(names, sat, data)[0]


def atlas(data):
    px = [[0] * 140 for _ in range(192)]
    items = [(r, ink) for r, ink in data['tiles'][1:]] + list(data['sprites'])
    for i, (rows, ink) in enumerate(items):
        ox, oy = 2 + (i % 8) * 17, 2 + (i // 8) * 36
        for y, r in enumerate(rows):
            for k in range(CW):
                if r >> (13 - k) & 1:
                    px[oy + 2 * y][ox + k] = px[oy + 2 * y + 1][ox + k] = ink
    return px


def write_previews(out, data):
    out.mkdir(parents=True, exist_ok=True)
    rgb = lambda px: dhgr_to_rgb(*dhgr_from_colors(px))  # noqa: E731
    png_write(out / 'dhgr_x2_mock.png', rgb(mock(data)), scale=(4, 2))
    png_write(out / 'dhgr_x2_atlas.png', rgb(atlas(data)), scale=(4, 2))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('out')
    ap.add_argument('--png', type=Path)
    args = ap.parse_args(argv)
    data = load()
    for name, n in data['lost']:
        if n and not name.startswith('hero'):
            raise SystemExit(f'{name}: {n} pixels lost by the 16 -> 14 columns')
    write_if_changed(args.out, inc_text(data))
    if args.png:
        write_previews(args.png, data)


if __name__ == '__main__':
    main()
