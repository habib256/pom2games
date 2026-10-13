#!/usr/bin/env python3
"""DHGR mood of the engine against tools/dhgr_palette (lot 3).

dhgr_frame (src/dhgr.s) is called directly with poked inputs: the mood
(select_mood with the HGR view_dark rule first), its 21 entries (five sky
zones, then ground...shade), the sun / Moon colour and the shaded sprite colours
must equal the Python tables for every mood, cloud state, Moon height and
phase, and every asset.

Lot 7: the same cases for each of the six region packs, chosen at the start
menu: the region's tables (dhgr_palette.REGIONS, gendhgr.py) and the
colours of its animals, the fourth one through module 23.
"""
import itertools
from common import L, DISK, a2test, mood_name, menu_keys
from test_thermal import call
import dhgr_palette as P

SLOTS = (5, 6, 7, 8, 9, 23)
SIERRA_SHA256 = '04ffd349ba065ddf0b655cf3e6d0bd33dcf8abdda2e4a9ec720fe97f1570b94d'     # dhgr_assets order: overlays 5..9, then module 23


def expected(night, dark, sun8, moon8, phase, clouds, asset, region=2):
    if dark:
        mood = 'night dark'
    elif night:
        mood = P.select_mood(-128, moon8, phase, clouds)
    else:
        mood = P.select_mood(max(sun8, P.SUN_NAUTICAL), -128, 0, clouds)
    table = P.mood_table(region)[19 * P.MOODS.index(mood):19 * P.MOODS.index(mood) + 19]
    sky = table[:3]
    zones = bytes((sky[0], sky[0] & 0xF0 | sky[1] & 15, sky[1], sky[1] & 0xF0 | sky[2] & 15, sky[2]))
    if night:
        body = (1, 0xDD if moon8 < P.MOON_LOW else 0xFF)
    else:
        body = (0, None) if P.MOOD[mood]['sun'] is None else (1, P.MOOD[mood]['sun'] * 17)
    shade = P.MOOD[mood]['shade']
    hidden = shade is None or dark
    names = dict(zip(SLOTS, P.region_assets(region)))
    sprites = None if hidden or not names.get(asset) else bytes(
        shade[c] * 17 for c in P.SPRITES[names[asset]])
    return mood, table, zones, body, int(hidden), sprites


def run(region):
    cases = []
    for sun8, clouds in itertools.product((60, 22, 21, 4, 3, -2, -3, -13, -14, -27, -28, -100), (0, 1)):
        cases.append((0, 0, sun8, -128, 0, clouds, 5))
    for moon8, phase, clouds in itertools.product((-128, -5, 0, 1, 21, 22, 90), (11, 9, 8, 6, 5, 0), (0, 1)):
        cases.append((1, 0, -128, moon8, phase, clouds, 6))
    for asset in SLOTS + (0,):
        cases.append((0, 0, 12, -128, 0, 0, asset))
        cases.append((1, 0, -128, 90, 11, 0, asset))
    cases.append((1, 1, -128, 90, 11, 0, 5))
    cases.append((0, 1, 60, -128, 0, 0, 5))
    steps = [L.until('idle', 20000)] + call(['dhgr_frame'])
    for night, dark, sun8, moon8, phase, clouds, asset in cases:
        steps += [L.poke('night', night), L.poke('view_dark', dark), L.poke('sun_alt8', sun8),
                  L.poke('moon_alt8', moon8), L.poke('moon_phase', phase),
                  L.poke('weather_sky', clouds), L.poke('scene_asset', asset),
                  f'until:{L["idle"]+3:04X}:2000', L.peek('sky_mood'), L.peek('cur_pal', 21),
                  L.peek('body_on', 2), L.peek('draw_dark'),
                  L.peek('spr_map', 4), L.until('idle', 2000)]
    result = a2test.run(DISK, menu_keys(str(region)) + steps, timeout=600, menu=False)
    rows = result.dumps
    per = 5
    assert len(rows) == per * len(cases), len(rows)
    moods = set()
    for k, case in enumerate(cases):
        mood, pal_zone, body, dark, sprites = rows[per * k:per * k + per]
        want_mood, table, zones, want_body, hidden, want_sprites = expected(*case, region)
        assert mood_name(mood) == want_mood, (case, mood_name(mood), want_mood)
        # Resident layout (tools/gendhgr.py): five sky zones, then the
        # 16 entries that follow the sky in dhgr_palette.mood_table.
        assert pal_zone == zones + table[3:], (case, pal_zone.hex(), (zones + table[3:]).hex())
        assert body[0] == want_body[0] and (not body[0] or body[1] == want_body[1]), (case, body.hex(), want_body)
        assert dark[0] == hidden, (case, dark)
        if want_sprites is not None:
            assert sprites == want_sprites, (case, sprites.hex(), want_sprites.hex())
        moods.add(want_mood)
    assert moods == set(P.MOODS), moods
    print(f'  region {region}: {len(cases)} sun/Moon/cloud/asset cases: 10 moods, entries, sky zones, '
          f'sun/Moon colour, sprite shades: OK', flush=True)


def main():
    import gendhgr, hashlib
    # The Sierra tables of lots 3-6 (310 bytes, as in the volumes built before
    # lot 7 step 4) stay byte-identical; the fourth asset slot follows them.
    sierra = gendhgr.region_tables(2)
    assert hashlib.sha256(sierra[:310]).hexdigest() == SIERRA_SHA256, 'Sierra tables changed'
    assert sierra[310:] == bytes(4) and len(sierra) == 314
    for region in range(1, 7):
        run(region)


if __name__ == '__main__':
    main()
