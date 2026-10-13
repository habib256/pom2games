#!/usr/bin/env python3
"""dhgr_ref.py: reference DHGR frame of the Neowilderness view (lot 3).

The geometry is NOT recomputed here. Terrain bands come from
tools/view_ref.columns (the events that view_ref.render paints), trees from
tools/forest_ref.trees and billboards from tests/scene_ref (select /
foreground): this module only gives each band a DHGR colour.

One ray = one DHGR colour pixel: column c (0..139) is ray c of view_ref.
Logical view rows 0..159 are placed as the HGR engine does:
  physical rows 16..159   logical rows 16..159 (visible terrain)
  physical rows 160..175  logical rows 0..15, the terrain cached under the HUD
  physical rows 0..15     HUD (doubled HGR compass box, src/hud.s), over black
  physical rows 176..191  unused, black (hidden by the 4 text lines)
The frame is two 8 KB banks (main, aux) in Apple memory order: byte offset
hgr_offset(y) + i of bank (main if i odd, aux if i even), i = 0..79 the
interleaved byte index of the row; see dhgr_palette for the bit order.

Usage:
  dhgr_ref.py MAP.bin [X8.8 Y8.8 HEADING] OUT.png [--sky day|dusk|night|moon]
      [--clouds] [--sun B,Y] [--moon B,Y,PHASE,WAXING] [--animal K]
      [--mood NAME | --sun8 S --moon8 S]
      [--no-forest] [--no-hud] [--main M.bin --aux A.bin]
"""
import argparse, os, sys, types
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE / 'tests'))
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import view_ref  # noqa: E402
import forest_ref  # noqa: E402
import topo  # noqa: E402
import dhgr_palette as P  # noqa: E402
import dhgr_sprites  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

ROWS, COLS = 192, 140
VIEW_ROWS, HUD_ROWS, HORIZON = view_ref.VIEW_ROWS, view_ref.HUD_ROWS, view_ref.HORIZON
CACHE_ROW = 160                 # physical row of logical row 0
SKY_OUTER = (3, 5, 6, 7, 7, 8, 7, 7, 6, 5, 3)   # src/sky.s sky_outer


def physical(row):
    """Physical page row of logical view row 0..159."""
    return row if row >= HUD_ROWS else CACHE_ROW + row


# ---------------------------------------------------------------------------
# Imports of the test oracles without their emulator harness: tests/common.py
# reads build/wild.lbl at import time, which the geometry does not need.
def _import_oracles():
    stub = 'common' not in sys.modules
    if stub:
        common = types.ModuleType('common')
        common.HERE, common.view_ref, common.L = HERE, view_ref, {}
        common.DISK = HERE.parent / 'dist/NEOWILDERNESS.po'
        common.a2test = common.disk_with = common.view_rows = common.text_screen = None
        sys.modules['common'] = common
    try:
        import scene_ref
    finally:
        if stub:
            del sys.modules['common']
    return scene_ref


scene_ref = _import_oracles()


# ---------------------------------------------------------------------------
# Terrain bands: the events of view_ref.columns (kind, r0, r1, n).
def terrain_events(m, px, py, heading):
    """Per column, in painting order: (kind, r0, r1, n), rows r0..r1-1."""
    return view_ref.columns(m, px, py, heading)


# ---------------------------------------------------------------------------
# Trees: tools/forest_ref.trees.
def tree_columns(m, px, py, heading):
    """{col: (begin, end, cx, crown_end, n)} of the canopy drawn per column."""
    return forest_ref.trees(m, px, py, heading)


# ---------------------------------------------------------------------------
@dataclass
class Sky:
    """Celestial state, as src/sky.s leaves it (sky_bearing, sky_y, ...).

    night: night physiology (black sky); dark: view_dark (black terrain,
    no sprites/foliage colours); dusk: proposed twilight flag (docs/DHGR.md);
    clouds: weather_sky != 0 (no sun or Moon). body: (bearing, y) or None
    (y = 255 hidden). phase: lunar phase sample 0..11 (11 = full disk),
    waxing: sky_waxing.
    """
    night: bool = False
    dark: bool = False
    dusk: bool = False
    clouds: bool = False
    body: tuple = None
    phase: int = 11
    waxing: bool = False
    sun8: int = None            # round(128 * sin(sun altitude)), proposed sun_alt8
    moon8: int = 127            # same for the Moon, proposed moon_alt8
    mood_name: str = None       # explicit mood (overrides everything)

    @property
    def mood(self):
        """dhgr_palette mood: explicit, from the altitudes, or legacy flags."""
        if self.mood_name:
            return self.mood_name
        if self.sun8 is not None:
            return P.select_mood(self.sun8, self.moon8, self.phase, self.clouds)
        if self.night:
            return 'night dark' if self.dark else 'night bright'
        if self.clouds:
            return 'overcast dusk' if self.dusk else 'overcast'
        return 'golden' if self.dusk else 'day'

    @property
    def hidden(self):
        """view_dark: terrain, foliage and sprites black (night dark)."""
        return self.mood == 'night dark'


def lighting(sky):
    """Default palette factory: the mood tables of tools/dhgr_palette."""
    return P.Lighting(sky.mood, sky.moon8)


def moon_inner(phase, waxing, x):
    """sky_moon_half: inner half-width of column x of the disk, 255 = full."""
    if waxing:
        x = 10 - x
    v = (x - phase) & 255
    return SKY_OUTER[v] if v < 11 else 255


def body_spans(sky, ang):
    """Rows of the sun/Moon in the ray at azimuth ang: [(start, end)], unclipped."""
    if sky.clouds or not sky.body or sky.body[1] > HORIZON:
        return []
    bearing, y = sky.body
    d = (ang - bearing + 5) % 560
    if d >= 11:
        return []
    half = SKY_OUTER[d]
    start, end = max(0, y - half), (y + half + 1) & 255
    if sky.night:
        inner = moon_inner(sky.phase, sky.waxing, d)
        if inner < 128:
            return [(start, (y - inner) & 255), (y + inner + 1, end)]
    return [(start, end)]


# ---------------------------------------------------------------------------
def dither_column(heading, col):
    """The checkerboard phase of a column: its azimuth, not its screen
    position, so that a turn (35 columns) scrolls dithered pixels unchanged."""
    return (heading - 70 + col) % 560


def view(m, px, py, heading, sky=None, animal=None, forest=True, sprites=True, pal=lighting):
    """Logical view: 160 rows x 140 colour indices (rows 0..15 included).

    pal(sky) returns the colour roles (default: the mood of tools/dhgr_palette);
    tests pass HGR codes to check the geometry against view_ref / scene_ref /
    test_forest."""
    sky = sky or Sky()
    lit = pal(sky)
    events = terrain_events(m, px, py, heading)
    pix = [[P.BLACK] * COLS for _ in range(VIEW_ROWS)]
    sky_top = [0] * COLS
    for col, evs in enumerate(events):
        az = dither_column(heading, col)
        for kind, r0, r1, n in evs:
            for r in range(r0, r1):
                if kind == 'sky':
                    c = lit.sky(r, az)
                elif kind == 'ridge':
                    c = lit.ridge(r, az)
                else:
                    c = lit.band(kind, n, r, az)
                pix[r][col] = c
            if kind == 'sky':
                sky_top[col] = r1

    # Billboard (scene_ref geometry), shaded by the mood, hidden in the dark.
    opaque = [set() for _ in range(COLS)]
    g = None if sky.hidden or not sprites else scene_ref.select(m, px, py, heading, animal)
    if g:
        name = scene_ref.ASSETS[g['asset']]
        colours = lit.sprite_colours(name)
        if colours is None:
            s = dhgr_sprites.load(name, g['shift'])
        else:
            s = dhgr_sprites.convert(name, g['shift'], colours=colours)
        for col in range(max(0, g['left']), min(COLS, g['left'] + g['width'])):
            front = scene_ref.foreground(m, px, py, heading, col, g['depth']) if g['depth'] else VIEW_ROWS
            for up, c in s['columns'][col - g['left']].items():
                out = g['anchor'] - up if g['depth'] else s['base'] - s['origin'] - up
                if 0 <= out < front:
                    pix[out][col] = lit.sprite(c)
                    opaque[col].add(out)

    # Sun / Moon: remaining sky rows only, after sprites (src/sky.s sky_column).
    body = lit.moon() if sky.night else lit.sun()
    for col in range(COLS if body is not None else 0):
        top = sky_top[col]
        while top and top - 1 in opaque[col]:
            top -= 1                          # scene_trim
        ang = (heading - 70 + col) % 560
        for start, end in body_spans(sky, ang):
            for r in range(start, min(end, top)):
                if r not in opaque[col]:
                    pix[r][col] = body

    # Foliage after the sky (forest_paint), below a nearer billboard only.
    if forest:
        depth = g['depth'] if g else 0
        for col, (begin, end, cx, crown_end, n) in tree_columns(m, px, py, heading).items():
            for r in range(max(HUD_ROWS, begin), end):
                if r in opaque[col] and depth < n:
                    continue
                if sky.hidden or r == begin:
                    c = lit.tree('outline', r, col)
                elif r >= crown_end:
                    c = lit.tree('trunk', r, col)
                else:
                    c = lit.tree('crown', r, col, (r ^ cx) & 1)
                pix[r][col] = c
    return pix


# ---------------------------------------------------------------------------
# HUD: the HGR compass box of src/hud.s (HGR bytes 13..26, 98 pixels, two
# azimuth units per HGR pixel), drawn in DHGR by doubling each HGR pixel
# (HGR byte y -> aux y, main y: white where both pixels of a colour pixel are
# lit, blue / orange fringes otherwise), plus the yellow index of
# tools/gendhgr.py on rows 11..13 (whole bytes 19 and 20).
HUD_LEFT, HUD_RIGHT = 45, 94          # colour pixels of the box frame
HUD_POINTER = 70
HUD_BYTES = range(13, 27)
LABELS = ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')


def hud_hgr(heading, magnetic=0):
    """16 x 40 HGR bytes of the compass box, without the index."""
    from fonts import glyph
    out = bytearray(16 * 40)
    left = ((heading - magnetic - 98) % 560) // 2

    def pixel(x, y):
        out[y * 40 + x // 7] |= 1 << (x % 7)
    for bearing, label in zip(range(0, 280, 35), LABELS):
        for i, letter in enumerate(label):
            for y, bits in enumerate(glyph(letter)[:7]):
                for b in range(7):
                    if bits & (1 << b):
                        x = 91 + (bearing - len(label) * 7 // 2 + i * 7 + b - left) % 280
                        if x < 189:
                            pixel(x, y + 2)
    for tick in range(16):
        x = 91 + (tick * 35 // 2 - left) % 280
        if x < 189:
            pixel(x, 9)
    for x in range(91, 189):
        pixel(x, 0)
        pixel(x, 15)
    for y in range(16):
        pixel(91, y)
        pixel(188, y)
    return bytes(out)


def hud_banks(heading, magnetic=0):
    """(main, aux): 16 rows x 40 bytes; only bytes 13..26 belong to the HUD."""
    from fonts import double7
    import gendhgr
    hgr = hud_hgr(heading, magnetic)
    main, aux = bytearray(16 * 40), bytearray(16 * 40)
    for y in range(16):
        for b in HUD_BYTES:
            aux[y * 40 + b], main[y * 40 + b] = double7(hgr[y * 40 + b])
    ptr = gendhgr.pointer_bytes()
    for k, y in enumerate((11, 12, 13)):
        main[y * 40 + 19], main[y * 40 + 20], aux[y * 40 + 19], aux[y * 40 + 20] = ptr[4 * k:4 * k + 4]
    return bytes(main), bytes(aux)


def hud(page, heading, magnetic=0):
    """Physical rows 0..15 of a colour page: the HUD bytes over the page."""
    main, aux = map(bytearray, encode(page))
    hmain, haux = hud_banks(heading, magnetic)
    for y in range(16):
        o = hgr_offset(y)
        for b in HUD_BYTES:
            main[o + b], aux[o + b] = hmain[y * 40 + b], haux[y * 40 + b]
    page[:16] = decode(main, aux)[:16]


def frame(m, px, py, heading, sky=None, animal=None, forest=True, show_hud=True, magnetic=0,
          sprites=True):
    """Physical page: 192 rows x 140 colour indices."""
    v = view(m, px, py, heading, sky, animal, forest, sprites)
    page = [[P.BLACK] * COLS for _ in range(ROWS)]
    for r in range(VIEW_ROWS):
        page[physical(r)] = v[r]
    if show_hud:
        hud(page, heading, magnetic)
    return page


# ---------------------------------------------------------------------------
def encode(page):
    """(main, aux): two 8 KB banks in Apple memory order, bit 7 clear."""
    main, aux = bytearray(8192), bytearray(8192)
    if len(page) < ROWS:
        page = list(page) + [[P.BLACK] * COLS] * (ROWS - len(page))
    for y, row in enumerate(page):
        bits = 0
        for x, c in enumerate(row):
            bits |= P.rot(c) << (4 * x)
        base = hgr_offset(y)
        for i in range(80):
            byte = (bits >> (7 * i)) & 0x7F
            (aux if i % 2 == 0 else main)[base + i // 2] = byte
    return bytes(main), bytes(aux)


def decode(main, aux):
    """Inverse of encode for the visible rows (memory holes ignored)."""
    page = []
    for y in range(ROWS):
        base = hgr_offset(y)
        bits = 0
        for i in range(80):
            bits |= ((aux if i % 2 == 0 else main)[base + i // 2] & 0x7F) << (7 * i)
        rot_inv = {P.rot(c): c for c in range(16)}
        page.append([rot_inv[(bits >> (4 * x)) & 15] for x in range(COLS)])
    return page


def column_runs(page, rows=range(ROWS), skip=P.BLACK):
    """Per column: [(y0, y1, colour)] maximal runs, colour skip omitted."""
    out = []
    for x in range(COLS):
        runs, y = [], rows.start
        while y < rows.stop:
            c = page[y][x]
            y1 = y + 1
            while y1 < rows.stop and page[y1][x] == c:
                y1 += 1
            if c != skip:
                runs.append((y, y1, c))
            y = y1
        out.append(runs)
    return out


def to_png(path, page, rows=None):
    """280 x len(rows) preview (2 pixels per colour pixel), POM2 colours."""
    rows = list(rows if rows is not None else range(len(page)))
    rgb = bytearray()
    for y in rows:
        for c in page[y]:
            rgb += bytes(P.RGB[c]) * 2
    topo.png(str(path), 2 * COLS, len(rows), rgb)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('map', type=Path)
    ap.add_argument('args', nargs='+', help='[X Y HEADING] OUT.png')
    ap.add_argument('--sky', choices=('day', 'dusk', 'night', 'moon'), default='day')
    ap.add_argument('--mood', choices=P.MOODS)
    ap.add_argument('--sun8', type=int, help='sun altitude, 128 * sin')
    ap.add_argument('--moon8', type=int, default=127)
    ap.add_argument('--clouds', action='store_true')
    ap.add_argument('--sun', help='bearing,y')
    ap.add_argument('--moon', help='bearing,y,phase,waxing')
    ap.add_argument('--animal', type=int, choices=(6, 7, 8))
    ap.add_argument('--no-forest', action='store_true')
    ap.add_argument('--no-hud', action='store_true')
    ap.add_argument('--main', type=Path)
    ap.add_argument('--aux', type=Path)
    a = ap.parse_args()
    m = a.map.read_bytes()
    if len(a.args) == 4:
        px, py, heading = (int(v, 0) for v in a.args[:3])
    else:
        px, py, heading = m[2] | m[3] << 8, m[4] | m[5] << 8, m[6] | m[7] << 8
    sky = Sky(night=a.sky in ('night', 'moon'), dark=a.sky == 'night', dusk=a.sky == 'dusk',
              clouds=a.clouds, sun8=a.sun8, moon8=a.moon8, mood_name=a.mood)
    if a.sun:
        sky.body = tuple(int(v) for v in a.sun.split(','))
    if a.moon:
        b, y, phase, waxing = (int(v) for v in a.moon.split(','))
        sky.body, sky.phase, sky.waxing = (b, y), phase, bool(waxing)
    animal = (a.animal, px, py, heading) if a.animal else None
    page = frame(m, px, py, heading, sky, animal, not a.no_forest, not a.no_hud)
    to_png(a.args[-1], page)
    main_bank, aux_bank = encode(page)
    if a.main:
        a.main.write_bytes(main_bank)
    if a.aux:
        a.aux.write_bytes(aux_bank)


if __name__ == '__main__':
    main()
