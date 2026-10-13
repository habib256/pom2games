#!/usr/bin/env python3
"""Pure Python checks of the DHGR reference (no emulator).

- palette: TN #3 bytes, rotation of dev/lib/hgrc, determinism;
- byte layout of known pixels, encode/decode round trips;
- sprites: binary round trips and the scene_ref scaling rule;
- geometry: with HGR colour codes as palette, dhgr_ref must reproduce
  view_ref.render, scene_ref.render and forest_ref.hgr bit for bit
  (rows 16..159), so the DHGR palette cannot hide a projection change;
- night rules, HUD and the physical row layout.

  test_dhgr_ref.py [--map build/dhgr/map.bin] [--refs]   (--refs: PNG captures)
"""
import argparse, random, sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(ROOT / 'dev/tests'))
import dhgr_ref as R  # noqa: E402
import dhgr_palette as P  # noqa: E402
import dhgr_sprites as S  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

BUILD = HERE / 'build/dhgr'

class HGR:
    """HGR pair codes (bit 0 even pixel, bit 1 odd pixel) as a palette."""
    def __init__(self, sky):
        self.night = sky.night
    def sky(self, row, col): return 0 if self.night else 1
    def ridge(self, row, col): return 0
    def band(self, kind, n, row, col): return {'ground': 2, 'snow': 3, 'water': 1}[kind]
    def tree(self, part, row, col, odd=False): return 2 if part == 'crown' and odd else 0
    def sun(self): return 3
    def moon(self): return 3
    def sprite(self, c): return c
    def sprite_colours(self, name): return (0, 1, 2, 3)

# One reference scene per mood: (sun8, moon8, phase, clouds, night, body y).
MOOD_SCENES = {
    'day': (60, -128, 0, False, False, 40),
    'overcast': (60, -128, 0, True, False, 40),
    'golden': (12, -128, 0, False, False, 84),
    'sunset': (0, -128, 0, False, False, 94),
    'overcast dusk': (8, -128, 0, True, False, 88),
    'civil': (-8, 40, 7, False, True, 255),
    'nautical': (-20, 40, 7, False, True, 70),
    'night bright': (-60, 80, 11, False, True, 50),
    'night dim': (-60, 80, 7, False, True, 50),
    'night dark': (-60, 80, 3, False, True, 50),
}


def mood_sky(name, bearing):
    sun8, moon8, phase, clouds, night, y = MOOD_SCENES[name]
    sky = R.Sky(night=night, clouds=clouds, body=(bearing, y), phase=phase, sun8=sun8, moon8=moon8)
    assert sky.mood == name, (name, sky.mood)
    return sky


def hgr_bytes(view):
    """160 x 40 HGR bytes of a view drawn with HGR codes."""
    fb = bytearray(160 * 40)
    for r, row in enumerate(view):
        for c, code in enumerate(row):
            for bit in (0, 1):
                if code >> bit & 1:
                    p = 2 * c + bit
                    fb[r * 40 + p // 7] |= 1 << (p % 7)
    return bytes(fb)


def rows16(fb):
    return fb[16 * 40:]


def check_palette():
    from test_dhgr import PATTERNS          # dev/tests: Apple IIe TN #3, table 2
    assert P.PATTERNS == tuple(PATTERNS), 'solid colour bytes differ from TN #3'
    assert all(P.rot(c) == ((c >> 1) | (c << 3)) & 15 for c in range(16))
    assert len(set(P.rot(c) for c in range(16))) == 16
    assert len(P.RGB) == 16 and P.RGB[0] == (0, 0, 0) and P.RGB[15] == (255, 255, 255)
    assert set(P.MOOD) == set(P.MOODS)
    for name, t in P.MOOD.items():
        flat = lambda e: list(e) if isinstance(e, tuple) else [e]
        values = [c for k in ('sky', 'ground', 'snow', 'water', 'crown') for e in t[k] for c in flat(e)]
        values += [c for k in ('ridge', 'outline', 'trunk', 'sun') if t[k] is not None for c in flat(t[k])]
        assert all(0 <= c < 16 for c in values), name
        assert t['shade'] is None or len(t['shade']) == 16
    table = P.mood_table()
    assert len(table) <= 300, len(table)
    # Mood thresholds (S8 = 128 sin(altitude)) and graded moonlight.
    cases = [((22, 0, 0, 0), 'day'), ((22, 0, 0, 1), 'overcast'), ((21, 0, 0, 0), 'golden'),
             ((4, 0, 0, 0), 'golden'), ((3, 0, 0, 0), 'sunset'), ((-2, 0, 0, 0), 'sunset'),
             ((3, 0, 0, 1), 'overcast dusk'), ((-3, 0, 0, 0), 'civil'), ((-3, 0, 0, 1), 'nautical'),
             ((-13, 0, 0, 0), 'civil'), ((-14, 0, 0, 0), 'nautical'), ((-27, 0, 0, 0), 'nautical'),
             ((-28, 90, 11, 0), 'night bright'), ((-28, 10, 11, 0), 'night bright'),
             ((-28, 10, 11, 1), 'night dim'), ((-28, 90, 6, 0), 'night dim'),
             ((-28, 90, 5, 0), 'night dark'), ((-28, -5, 11, 0), 'night dark'),
             ((-28, 90, 11, 1), 'night dim'), ((-28, 10, 7, 0), 'night dark')]
    for (sun8, moon8, phase, clouds), want in cases:
        assert P.select_mood(sun8, moon8, phase, bool(clouds)) == want, (sun8, moon8, phase, clouds, want)
    print(f'  palette: TN #3 bytes, rotation; {len(P.MOODS)} moods, thresholds, '
          f'tables {len(table)} bytes: OK')


def check_layout():
    page = [[0] * 140 for _ in range(192)]
    expect = {0: [('aux', 0, 0x0F)], 1: [('aux', 0, 0x70), ('main', 0, 0x01)],
              2: [('main', 0, 0x1E)], 3: [('main', 0, 0x60), ('aux', 1, 0x03)],
              4: [('aux', 1, 0x3C)], 5: [('aux', 1, 0x40), ('main', 1, 0x07)],
              6: [('main', 1, 0x78)]}
    for x, writes in expect.items():
        for y in (0, 63, 64, 191):
            page = [[0] * 140 for _ in range(192)]
            page[y][x + 133] = 15                  # last group, x = 133..139
            main, aux = R.encode(page)
            want = {'main': bytearray(8192), 'aux': bytearray(8192)}
            for bank, off, bits in writes:
                want[bank][hgr_offset(y) + 38 + off] = bits
            assert (main, aux) == (bytes(want['main']), bytes(want['aux'])), (x, y)
    rnd = random.Random(7)
    for _ in range(3):
        page = [[rnd.randrange(16) for _ in range(140)] for _ in range(192)]
        main, aux = R.encode(page)
        assert R.decode(main, aux) == page
        assert not any(b & 0x80 for b in main + aux)
    print('  byte layout of pixels 133..139 on rows 0/63/64/191, round trips: OK')


def check_sprites():
    scene_ref = R.scene_ref
    for name in S.NAMES:
        image = S.original(name)
        opaque = {(y, x) for y, row in enumerate(image) for x, c in enumerate(row) if c >= 0}
        for shift in S.SHIFTS:
            s = S.convert(name, shift, image)
            data = S.encode(s)
            back = S.parse(data)
            assert back['columns'] == s['columns'] and back['width'] == s['width']
            assert back['base'] == scene_ref.BASES[{v: k for k, v in scene_ref.ASSETS.items()}[name]]
            g = scene_ref.geometry({v: k for k, v in scene_ref.ASSETS.items()}[name], 0, 1, shift, 0, 0)
            assert s['width'] == g['width'], (name, shift)
            built = BUILD / 'sprites' / f'{name}_s{shift}.bin'
            if built.exists():
                assert built.read_bytes() == data, f'{built} is stale'
            if shift == 0:
                got = {(s['base'] - up, x) for x, col in enumerate(s['columns']) for up in col}
                assert got == opaque, name
    print('  sprites: 5 assets x 4 scales, round trips, scene_ref widths, masks: OK')


def check_geometry(m):
    import view_ref
    import forest_ref
    px0, py0, h0 = (int.from_bytes(m[o:o + 2], 'little') for o in (2, 4, 6))
    rnd = random.Random(1985)
    cases = [(px0, py0, h0), (px0, py0, (h0 + 280) % 560), ((m[17] << 8) + 128, (m[18] << 8) + 128, 0)]
    while len(cases) < 14:
        x, y = rnd.randrange(4, 108), rnd.randrange(4, 80)
        cases.append(((x << 8) + rnd.randrange(256), (y << 8) + rnd.randrange(256), rnd.randrange(560)))
    for px, py, h in cases:
        bare = R.view(m, px, py, h, forest=False, sprites=False, pal=HGR)
        assert rows16(hgr_bytes(bare)) == rows16(view_ref.render(m, px, py, h)), ('terrain', px, py, h)
        scene = R.view(m, px, py, h, forest=False, pal=HGR)
        assert rows16(hgr_bytes(scene)) == rows16(R.scene_ref.render(m, px, py, h)), ('sprites', px, py, h)
        woods = R.view(m, px, py, h, sprites=False, pal=HGR)
        assert rows16(hgr_bytes(woods)) == rows16(forest_ref.hgr(m, px, py, h)), ('forest', px, py, h)
    for kind in (6, 7, 8):                        # nearby fauna, all scales
        for d in range(0, 8, 2):
            a = (kind, px0 + d * 256, py0, 140)
            scene = R.view(m, px0, py0, 140, forest=False, animal=a, pal=HGR)
            ref = R.scene_ref.render(m, px0, py0, 140, a)
            assert rows16(hgr_bytes(scene)) == rows16(ref), ('fauna', kind, d)
    print(f'  geometry: {len(cases)} views = view_ref, scene_ref, forest_ref (HGR codes); 12 fauna: OK')


def check_rules(m):
    px, py, h = (int.from_bytes(m[o:o + 2], 'little') for o in (2, 4, 6))
    moon = (h, 50)
    day = R.view(m, px, py, h, R.Sky())
    assert R.view(m, px, py, h, R.Sky()) == day, 'not deterministic'
    colours = lambda v, rows: {c for r in rows for c in v[r]}
    views = {name: R.view(m, px, py, h, mood_sky(name, h)) for name in P.MOODS}
    dark, dim, bright = views['night dark'], views['night dim'], views['night bright']
    assert colours(dark, range(96, 160)) == {P.BLACK}, 'dark night shows terrain'
    assert P.MOON_HIGH in colours(dark, range(16, 96)), 'Moon missing'
    lit = lambda v: sum(c != P.BLACK for r in range(96, 160) for c in v[r])
    assert 0 < lit(dim) < lit(bright), 'moonlight must be graded: dark < dim < bright'
    assert all(c == P.BLACK for c in P.MOOD['night bright']['sky'][:2]), 'night sky is black'
    wreck = P.SPRITES['wreck'][3]
    assert any(P.SHADE_MOON[wreck] in row for row in bright[100:]), 'wreck hidden by the full Moon'
    assert not any(c != P.BLACK for row in dark[100:] for c in row), 'wreck shown in the dark'
    for name, v in views.items():
        sun = P.MOOD[name]['sun']
        if MOOD_SCENES[name][4] or sun is None:
            continue
        assert sun in colours(v, range(160)), (name, 'sun missing')
    assert [P.MOOD[k]['sun'] for k in ('day', 'golden', 'sunset')] == [P.YELLOW, P.ORANGE, P.MAGENTA]
    cloudy = R.view(m, px, py, h, R.Sky(clouds=True, body=(h, 40), sun8=60))
    assert P.YELLOW not in colours(cloudy, range(16, 95)), 'clouds must hide the sun'
    low = R.view(m, px, py, h, R.Sky(night=True, body=(h, 40), phase=11, sun8=-60, moon8=10))
    assert P.MOON_LOW_COLOUR in colours(low, range(16, 96)), 'low Moon is pale yellow'

    # Moon phase: waxing / waning mirror each other, new Moon draws nothing.
    for phase in range(12):
        w = [R.body_spans(R.Sky(night=True, body=(100, 50), phase=phase, waxing=True), a) for a in range(95, 106)]
        n = [R.body_spans(R.Sky(night=True, body=(100, 50), phase=phase), a) for a in range(95, 106)]
        assert w == n[::-1], phase
    page = R.frame(m, px, py, h, R.Sky())
    assert all(page[y][R.HUD_POINTER] == P.HUD['pointer'] for y in (11, 12, 13))
    # Native ribbon (lot 4): dark blue box over pixels 49..90, black around.
    assert page[0][R.HUD_LEFT] == page[0][R.HUD_RIGHT] == P.DARK_BLUE
    assert page[0][R.HUD_LEFT - 1] == page[0][R.HUD_RIGHT + 1] == P.BLACK
    assert page[11][R.HUD_POINTER - 1] == P.BLACK and page[13][R.HUD_POINTER - 2] == P.YELLOW
    assert all(page[160 + r] == day[r] for r in range(16)), 'cache rows 160..175'
    assert all(page[r] == day[r] for r in range(16, 160))
    assert all(c == P.BLACK for r in range(176, 192) for c in page[r])
    print('  moods: graded moonlight, sun colours, low Moon, clouds, phases, HUD, rows 160..191: OK')


def refs(m):
    px, py, h = (int.from_bytes(m[o:o + 2], 'little') for o in (2, 4, 6))
    BUILD.mkdir(parents=True, exist_ok=True)
    cx, cy = (m[17] << 8) + 128, (m[18] << 8) + 128
    shots = {}
    for k, name in enumerate(P.MOODS):          # start view, body slightly right
        shots['mood_' + name.replace(' ', '_')] = (px, py, h, mood_sky(name, (h + 25) % 560), None)
        hd = (h + 140) % 560
        shots['mood_' + name.replace(' ', '_') + '_east'] = (px, py, hd, mood_sky(name, (hd - 20) % 560), None)
    shots.update({
        'cabin': (cx, cy, int.from_bytes(m[19:21], 'little'), R.Sky(), None),
        'bear': (px, py, 280, R.Sky(), (6, px + 2 * 256, py, 280)),
        'cougar': (px, py, 280, R.Sky(), (7, px + 3 * 256, py, 280)),
        'rattlesnake': (px, py, 280, R.Sky(), (8, px + 256, py, 280)),
        'cougar_golden': (px, py, 280, mood_sky('golden', 300), (7, px + 3 * 256, py, 280)),
        'cougar_moonlit': (px, py, 280, mood_sky('night bright', 300), (7, px + 3 * 256, py, 280)),
    })
    for name, (x, y, hd, sky, animal) in shots.items():
        page = R.frame(m, x, y, hd, sky, animal)
        R.to_png(BUILD / f'ref_{name}.png', page)
        R.to_png(BUILD / f'ref_{name}_visible.png', page, range(160))
    # Woods: a forested cell, if any, looking along the map.
    from mkmap import forest_at
    spot = next(((x, y) for y in range(10, 74) for x in range(10, 100)
                 if forest_at(m, x + 2, y) and not m[64 + y * 112 + x] & 128), None)
    if spot:
        for name in ('day', 'golden', 'sunset', 'night bright'):
            page = R.frame(m, (spot[0] << 8) + 128, (spot[1] << 8) + 128, 140, mood_sky(name, 150))
            R.to_png(BUILD / f"ref_woods_{name.replace(' ', '_')}.png", page, range(160))
    swatch = bytearray()
    for _ in range(24):
        swatch += P.swatch_rgb(20)
    import topo
    topo.png(str(BUILD / 'palette.png'), 320, 24, swatch)
    print(f'  reference captures written to {BUILD}/ref_*.png and palette.png')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', type=Path, default=BUILD / 'map.bin')
    ap.add_argument('--refs', action='store_true')
    a = ap.parse_args()
    m = a.map.read_bytes()
    if a.refs:
        refs(m)
        return
    check_palette()
    check_layout()
    check_sprites()
    check_geometry(m)
    check_rules(m)
    print('DHGR reference: OK')


if __name__ == '__main__':
    main()
