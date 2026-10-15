#!/usr/bin/env python3
"""genfire.py: the animated campfire of the view (docs/CAMP.md section 8).

The original game has no fire graphic. A fire burns on the player's cell
(src/camp.s fire_on; M5 forbids walking away from it), so it is drawn at
the player's feet, bottom centre of the view, never as a distant billboard.

Art: four frames of 28 x 32 DHGR colour pixels (pixels 56..83 = byte groups
8..11, physical rows TOP..TOP + 31 = 125..156), one character per pixel:
  .  transparent        k  black (0)        r  magenta, the red (1)
  b  brown (8)          o  orange (9)       y  yellow (13)
  g  grey (5)           m  glow: magenta (night only)
The fire is its own light: no mood shading. The logs, the stones and the
black bed of embers are the same in every frame; the flames, the embers'
glints and the sparks change.

Three layers of 2-bit codes, four pixels a byte (pixel 4b + j in bits 2j and
2j + 1 of byte b), each with its palette of three colours (code 0: the layer
below shows):
  static  rows 24..31, columns 0..27: logs, bed of embers, stones (k b g)
  glow    rows GLOW_R0..31, columns 0..27, at night only (sky_mood >= civil
          twilight): a dithered magenta ring on the ground (m)
  flames  rows 0..28, columns 4..23, four frames (r o y), each with a 32-bit
          mask of the rows that differ from the frame before
src/fire.s composes a row from the saved background and the layers, then
writes only the bytes that differ from the screen.

Usage: genfire.py OUT.inc [--png DIR]   (DIR: previews x4 on the real start
view, tools/dhgr_ref.py, in five moods)
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import dhgr_palette as P  # noqa: E402

W, H = 28, 32                   # colour pixels, rows
X0 = 56                         # first pixel: byte group 8 (7 pixels a group)
TOP = 125                       # first physical row (the last TOP + 31): raised
                                # 3 rows from 128 on 2026-10-15; any row works
NIGHT_MOOD = 5                  # sky_mood >= civil twilight: the glow
CODES = {'k': P.BLACK, 'r': P.MAGENTA, 'b': P.BROWN, 'o': P.ORANGE,
         'y': P.YELLOW, 'g': P.GREY1, 'm': P.MAGENTA}
# Layers: name -> (first row, rows, first column, columns, codes 0..3)
FLAMES = (0, 29, 4, 20, '.roy')
STATIC = (24, 8, 0, 28, '.kbg')
# One art: as in the original the fire burns until DOUSE (no lifetime, no
# burning-down stages).
FRAMES = (
    (  # frame 0
        '............................',  #  0
        '.........y..................',  #  1
        '............................',  #  2
        '............................',  #  3
        '..............r.............',  #  4
        '..............r.............',  #  5
        '.............rr....o........',  #  6
        '.............rr.............',  #  7
        '.............ror............',  #  8
        '............ror.............',  #  9
        '..........r.ror.............',  # 10
        '..........r.ror......r......',  # 11
        '.........rr.roor....rr......',  # 12
        '.........rr.roor....r.......',  # 13
        '.........rorooor...rr.......',  # 14
        '.........rooooor..ror.......',  # 15
        '........rooooooor.ror.......',  # 16
        '........roooooooorooor......',  # 17
        '........roooooooooooor......',  # 18
        '.......rooooyyooooooor......',  # 19
        '.......roooyyyoooooooor.....',  # 20
        '.......rooyyyyyooooooor.....',  # 21
        '.......rooyyyyyyyoyyoor.....',  # 22
        '........rooyyyyyyyyoor......',  # 23
        '......bbrooyyyyyyyyoor......',  # 24
        '......bbbroooooooooorb......',  # 25
        '......kkkkroooooooorbb......',  # 26
        '..kgbbbbbbkkkkkbbbbbbbbbgk..',  # 27
        '..gbbbkkkkrkokorkkrkkkbbbg..',  # 28
        '..kgkkk...............kkgk..',  # 29
        '.gg......................gg.',  # 30
        '...ggg.gg.ggg..ggg.gg.ggg...',  # 31
    ),
    (  # frame 1
        '..........o.................',  #  0
        '............................',  #  1
        '............................',  #  2
        '..................y.........',  #  3
        '.............r..............',  #  4
        '........r....r..............',  #  5
        '.............rr.............',  #  6
        '............ror.............',  #  7
        '............ror.............',  #  8
        '............roor............',  #  9
        '.....r.......ror............',  # 10
        '.....r.......ror.....r......',  # 11
        '......r.....roor.....rr.....',  # 12
        '......rr....roor.....rr.....',  # 13
        '.......r...roooor...ror.....',  # 14
        '.......rr.rooooor..ror......',  # 15
        '.......rorooooooor.ror......',  # 16
        '........roooooooooror.......',  # 17
        '........roooooooooooor......',  # 18
        '.......roooooyyoooooor......',  # 19
        '.......rooooyyyooooooor.....',  # 20
        '.......rooyyyyyyoooooor.....',  # 21
        '.......rooyyyyyyyyoooor.....',  # 22
        '........rooyyyyyyyyoor......',  # 23
        '......bbrooyyyyyyyyoor......',  # 24
        '......bbbroooooooooorb......',  # 25
        '......kkkkroooooooorbb......',  # 26
        '..kgbbbbbbkkkkkbbbbbbbbbgk..',  # 27
        '..gbbbkkkkkorkkokrkkkkbbbg..',  # 28
        '..kgkkk...............kkgk..',  # 29
        '.gg......................gg.',  # 30
        '...ggg.gg.ggg..ggg.gg.ggg...',  # 31
    ),
    (  # frame 2
        '............................',  #  0
        '...................o........',  #  1
        '............................',  #  2
        '............................',  #  3
        '.........y...........rr.....',  #  4
        '......................r.....',  #  5
        '..............r.............',  #  6
        '..............rr............',  #  7
        '.............ror............',  #  8
        '.............ror............',  #  9
        '............roor............',  # 10
        '............roor.....r......',  # 11
        '........r...roor.....rr.....',  # 12
        '........r...rooor....rr.....',  # 13
        '........rr.roooor...ror.....',  # 14
        '........rorooooor..ror......',  # 15
        '........roooooooor.ror......',  # 16
        '........roooooooooroor......',  # 17
        '.......rooooooyoooooor......',  # 18
        '.......roooooyyoooooor......',  # 19
        '.......roooyyyyooooooor.....',  # 20
        '.......rooyyyyyyoooooor.....',  # 21
        '.......rooyyyyyyyyoyoor.....',  # 22
        '........rooyyyyyyyyoor......',  # 23
        '......bbrooyyyyyyyyoor......',  # 24
        '......bbbroooooooooorb......',  # 25
        '......kkkkroooooooorbb......',  # 26
        '..kgbbbbbbkkkkkbbbbbbbbbgk..',  # 27
        '..gbbbkkkkrokkkoykrkkkbbbg..',  # 28
        '..kgkkk...............kkgk..',  # 29
        '.gg......................gg.',  # 30
        '...ggg.gg.ggg..ggg.gg.ggg...',  # 31
    ),
    (  # frame 3
        '....................r.......',  #  0
        '.................y..........',  #  1
        '........o...................',  #  2
        '............................',  #  3
        '...............r............',  #  4
        '...............r............',  #  5
        '..............rr............',  #  6
        '..............rr............',  #  7
        '.............ror............',  #  8
        '.............ror............',  #  9
        '.........r..roor............',  # 10
        '.........r..roor.......r....',  # 11
        '........rr..rooor......r....',  # 12
        '........rr..rooor.....rr....',  # 13
        '........ror.rooor.....rr....',  # 14
        '........rooroooor....ror....',  # 15
        '........roooooooor..ror.....',  # 16
        '........rooooooooorror......',  # 17
        '.......rooooooyoooooor......',  # 18
        '.......rooooooyoooooor......',  # 19
        '.......rooyoyyyooooooor.....',  # 20
        '.......rooyyyyyyoooooor.....',  # 21
        '.......rooyyyyyyyyoooor.....',  # 22
        '........rooyyyyyyyyoor......',  # 23
        '......bbrooyyyyyyyyoor......',  # 24
        '......bbbroooooooooorb......',  # 25
        '......kkkkroooooooorbb......',  # 26
        '..kgbbbbbbkkkkkbbbbbbbbbgk..',  # 27
        '..gbbbkkkkkkorykkkokkkbbbg..',  # 28
        '..kgkkk...............kkgk..',  # 29
        '.gg......................gg.',  # 30
        '...ggg.gg.ggg..ggg.gg.ggg...',  # 31
    ),
)

# Night glow: a ring of dithered magenta on the ground, dense near the logs,
# where every frame is transparent.
GLOW_CX, GLOW_CY, GLOW_RX, GLOW_RY = 13.5, 29.0, 14.5, 4.2


def in_layer(layer, x, y):
    r0, rows, c0, cols, _ = layer
    return r0 <= y < r0 + rows and c0 <= x < c0 + cols


def glow_art():
    rows = []
    for y in range(H):
        row = ''
        for x in range(W):
            d = ((x - GLOW_CX) / GLOW_RX) ** 2 + ((y - GLOW_CY) / GLOW_RY) ** 2
            on = d < 1 and (d < .45 or (x + y) % 2 == 0)
            row += 'm' if on and all(f[y][x] == '.' for f in FRAMES) else '.'
        rows.append(row)
    return rows


def glow_layer():
    art = glow_art()
    r0 = min(y for y, row in enumerate(art) if 'm' in row)
    return (r0, H - r0, 0, W, '.m')


def split():
    """The frames as layers: (static art, flame codes per frame)."""
    static = [['.'] * W for _ in range(H)]
    flames = [[['.'] * W for _ in range(H)] for _ in FRAMES]
    for y in range(H):
        for x in range(W):
            seen = [f[y][x] for f in FRAMES]
            flame = in_layer(FLAMES, x, y)
            under = {c for c in seen if not (flame and c in FLAMES[4][1:])}
            assert len(under) <= 1, ('two colours under a flame pixel', x, y)
            u = under.pop() if under else '.'
            assert u == '.' or in_layer(STATIC, x, y), ('a pixel outside the layers', x, y)
            static[y][x] = u
            for i, c in enumerate(seen):
                if flame and c in FLAMES[4][1:]:
                    flames[i][y][x] = c
    return static, flames


def layer_bytes(layer, art):
    """Rows of the layer, 2-bit codes, four pixels a byte."""
    r0, rows, c0, cols, codes = layer
    out = bytearray()
    for y in range(r0, r0 + rows):
        for b in range(cols // 4):
            v = 0
            for j in range(4):
                c = art[y][c0 + 4 * b + j]
                assert c in codes, ('colour outside the layer palette', c, y)
                v |= codes.index(c) << 2 * j
            out.append(v)
    return bytes(out)


def decode(layer, data, page):
    """src/fire.s fm_layer: a layer's codes over a colour page (rows 0..31)."""
    r0, rows, c0, cols, codes = layer
    for y in range(rows):
        for x in range(cols):
            v = data[y * (cols // 4) + x // 4] >> 2 * (x % 4) & 3
            if v:
                page[r0 + y][c0 + x] = CODES[codes[v]]
    return page


def changed_rows(flames, layer=FLAMES):
    r0, rows = layer[:2]
    return [sum(1 << y for y in range(r0, r0 + rows) if flames[i][y] != flames[i - 1][y])
            for i in range(len(flames))]


def data():
    static, flames = split()
    g = glow_layer()
    return dict(static=layer_bytes(STATIC, static), glow=layer_bytes(g, glow_art()),
                frames=[layer_bytes(FLAMES, f) for f in flames],
                changed=changed_rows(flames))


_DATA = []


def frame_pixels(i, night=False):
    """Frame i as src/fire.s draws it, from the emitted bytes: colours or
    None."""
    if not _DATA:
        _DATA.append(data())
    d = _DATA[0]
    page = [[None] * W for _ in range(H)]
    decode(STATIC, d['static'], page)
    if night:
        decode(glow_layer(), d['glow'], page)
    decode(FLAMES, d['frames'][i], page)
    return page


def emit(path):
    d = data()
    g = glow_layer()

    def byte_lines(name, blob, per=16):
        out = [f'{name}:  ; {len(blob)} bytes']
        for i in range(0, len(blob), per):
            out.append('        .byte ' + ', '.join(f'${b:02X}' for b in blob[i:i + per]))
        return out
    lines = ['; Generated by tools/genfire.py: the campfire of src/fire.s (docs/CAMP.md 8).',
             f'FIRE_ROWS = {H}', f'FIRE_TOP = {TOP}', f'FIRE_NIGHT = {NIGHT_MOOD}', f'FIRE_FLAME_ROWS = {FLAMES[1]}',
             f'FIRE_FRAME_SIZE = {len(d["frames"][0])}',
             '; layers 0 static, 1 glow, 2 flames (fire_frames + frame * FIRE_FRAME_SIZE):',
             '; first row, rows, first column, bytes a row; palettes (codes 1..3, code 0',
             '; unused).']
    layers = (STATIC, g, FLAMES)
    lines += ['fl_r0:   .byte ' + ', '.join(str(l[0]) for l in layers),
              'fl_rows: .byte ' + ', '.join(str(l[1]) for l in layers),
              'fl_col:  .byte ' + ', '.join(str(l[2]) for l in layers),
              'fl_w:    .byte ' + ', '.join(str(l[3] // 4) for l in layers),
              'fl_lo:   .byte <fire_static, <fire_glow, 0',
              'fl_hi:   .byte >fire_static, >fire_glow, 0',
              'fl_pl:   .byte <fire_pal_static, <fire_pal_glow, <fire_pal_flames',
              'fl_ph:   .byte >fire_pal_static, >fire_pal_glow, >fire_pal_flames']
    for name, layer in (('static', STATIC), ('glow', g), ('flames', FLAMES)):
        codes = layer[4]
        lines.append(f'fire_pal_{name}: .byte 0, '
                     + ', '.join(str(CODES[c]) for c in codes[1:]) + ', 0' * (3 - len(codes[1:])))
    lines.append('; rows that change, frame by frame (bits 0..7 = rows 0..7 ...)')
    lines.append('fire_changed:')
    for m in d['changed']:
        lines.append('        .byte ' + ', '.join(f'${m >> 8 * i & 255:02X}' for i in range(4)))
    lines += byte_lines('fire_static', d['static'], 7)
    lines += byte_lines('fire_glow', d['glow'], 7)
    lines += byte_lines('fire_frames', b''.join(d['frames']), 10)
    Path(path).write_text('\n'.join(lines) + '\n')
    return d


# ---------------------------------------------------------------------------
def scene(mood):
    import dhgr_ref as R
    m = (HERE / 'build/map.bin').read_bytes()
    px, py, heading = m[2] | m[3] << 8, m[4] | m[5] << 8, m[6] | m[7] << 8
    return R.frame(m, px, py, heading, R.Sky(mood_name=mood))


def with_fire(page, i, night):
    page = [list(r) for r in page]
    for y, row in enumerate(frame_pixels(i, night)):
        for x, c in enumerate(row):
            if c is not None:
                page[TOP + y][X0 + x] = c
    return page


def write_png(path, tiles, scale=4, gap=2):
    """tiles: colour-row images side by side; a colour pixel = 2 x 1, then x scale."""
    import topo
    h = max(len(t) for t in tiles)
    w = sum(len(t[0]) for t in tiles) + gap * (len(tiles) - 1)
    rgb = bytearray(b'\x40\x40\x40' * (2 * w * h))
    x0 = 0
    for t in tiles:
        for y, row in enumerate(t):
            for x, c in enumerate(row):
                o = (y * 2 * w + 2 * (x0 + x)) * 3
                rgb[o:o + 6] = bytes(P.RGB[c]) * 2
        x0 += len(t[0]) + gap
    W2, out = 2 * w, bytearray()
    for y in range(h):
        line = bytearray()
        for x in range(W2):
            line += rgb[(y * W2 + x) * 3:(y * W2 + x) * 3 + 3] * scale
        out += bytes(line) * scale
    topo.png(str(path), W2 * scale, h * scale, out)


def previews(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    crop_x, crop_y = range(X0 - 14, X0 + W + 14), range(TOP - 16, TOP + H)
    for mood in ('day', 'golden', 'sunset', 'night bright', 'night dark'):
        night = P.MOODS.index(mood) >= NIGHT_MOOD
        base, tiles = scene(mood), []
        for i in range(len(FRAMES)):
            page = with_fire(base, i, night)
            tiles.append([[page[y][x] for x in crop_x] for y in crop_y])
        name = mood.replace(' ', '_')
        write_png(out / f'fire_frames_{name}.png', tiles)
        write_png(out / f'fire_view_{name}.png', [with_fire(base, 0, night)[16:160]], scale=2)
    tiles = [[[c if c is not None else P.GREY2 for c in row] for row in frame_pixels(i)]
             for i in range(len(FRAMES))]
    tiles.append([[c if c is not None else P.BLACK for c in row] for row in frame_pixels(0, True)])
    write_png(out / 'fire_sprite.png', tiles)


def check():
    """The layers give back the art (the glow under it at night)."""
    glow = glow_art()
    for i, f in enumerate(FRAMES):
        for night in (False, True):
            got = frame_pixels(i, night)
            for y in range(H):
                for x in range(W):
                    c = f[y][x] if f[y][x] != '.' else (glow[y][x] if night else '.')
                    assert got[y][x] == (None if c == '.' else CODES[c]), (i, night, x, y)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('out')
    ap.add_argument('--png', type=Path)
    a = ap.parse_args()
    for f in FRAMES:
        assert len(f) == H and all(len(r) == W and set(r) <= set(CODES) | {'.'} for r in f)
    check()
    d = emit(a.out)
    if a.png:
        previews(a.png)
    sizes = dict(static=len(d['static']), glow=len(d['glow']),
                 frames=sum(map(len, d['frames'])))
    print(f'{a.out}: ' + ', '.join(f'{k} {v}' for k, v in sizes.items()) + f'; {sum(sizes.values())} bytes')


if __name__ == '__main__':
    main()
