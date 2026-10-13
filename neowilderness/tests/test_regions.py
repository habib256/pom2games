#!/usr/bin/env python3
"""Original region data (lot 7): headers, decoded fields, sprites, DOS check.

Needs the local originals (make extract). The pinned values are the decoded
numbers documented in docs/REGIONS.md; the bytes themselves stay in build/.
"""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
import regions  # noqa: E402

# region: (species name, rate) of the occupied slots, then latitude range,
# climate index, wind, precipitation min/max/phase, declination, summit,
# river sources, scrub altitude.
PINNED = {
    1: ((('BEAR', 80), ('WOLF', 100), ('MOOSE', 75)), (49, 58), 28, 30, (10, 60, 60), 26, 120, 16, 110),
    2: ((('BEAR', 80), ('COUGAR', 40), ('RATTLESNAKE', 100)), (35, 40), 31, 30, (2, 60, 47), 17, 145, 13, 110),
    3: ((('TIGER', 70), ('ELEPHANT', 70), ('COBRA', 70), ('PYTHON', 75)), (12, 27), 75, 20, (10, 120, 270), -5, 100, 21, 50),
    4: ((('CANNIBAL', 50), ('ADDER', 80), ('CROCODILE', 120)), (-8, -3), 130, 20, (60, 150, 60), 5, 120, 23, 50),
    5: ((('PUMA', 80), ('JAGUAR', 100), ('FERDELANCE', 80), ('ANACONDA', 50)), (-22, -10), 40, 20, (10, 70, 60), 0, 125, 12, 50),
    6: ((('PUMA', 100), ('CAT', 100)), (-55, -22), 11, 30, (1, 6, 270), 10, 210, 2, 110),
}
# The Sierra filters of tests/fauna_cases.py, as (centre, signed width).
SIERRA_FILTERS = {1: ((50, 34), (11, -4), (15, 6), (55, 25), (25, 25), (30, 20)),
                  2: ((50, 50), (12, -5), (10, 12), (50, 40), (35, 35), (30, 20)),
                  3: ((58, 25), (12, 6), (5, 6), (40, 40), (30, 30), (30, 20))}
# name: (track, sector, columns, height, encoded bytes) of the 27 sprites.
SPRITES = {
    'cabin': (0x16, 4, 61, 64, 1133), 'wreck': (0, 0, 119, 92, 1900),
    'bear': (0x1C, 0xC, 39, 53, 781), 'cougar': (0x1D, 0, 52, 43, 539),
    'rattlesnake': (0x1D, 3, 33, 47, 485), 'grizzly_bc': (0x1C, 0, 51, 54, 759),
    'wolf_bc': (0x1C, 3, 52, 96, 1121), 'moose_bc': (0x1C, 8, 51, 82, 958),
    'tiger': (0x1D, 5, 50, 68, 906), 'elephant': (0x1D, 9, 48, 73, 949),
    'cobra': (0x1D, 0xD, 41, 88, 730), 'python': (0x1E, 0, 48, 26, 464),
    'dani': (0x1E, 2, 45, 122, 905), 'adder': (0x1E, 6, 37, 47, 544),
    'crocodile': (0x1E, 9, 72, 59, 828), 'puma': (0x1E, 0xD, 30, 73, 639),
    'jaguar': (0x1F, 0, 62, 68, 1227), 'ferdelance': (0x1F, 5, 44, 31, 491),
    'anaconda': (0x1F, 7, 45, 44, 668), 'cat': (0x1F, 0xA, 53, 61, 937),
    'tent': (0x16, 0, 58, 55, 969), 'igloo': (0x16, 9, 57, 55, 859),
    'trench': (0x16, 0xD, 56, 17, 403), 'log': (0x16, 0xF, 88, 50, 1216),
    'rock': (0x17, 4, 59, 68, 1158), 'lost_city': (0, 8, 91, 93, 2428),
    'outpost': (1, 2, 75, 111, 2289)}


def main():
    headers = regions.read_headers(HERE / 'build/SIERRA.dsk')
    sums = dict(reversed(line.split()) for line in (HERE / 'docs/regions.sha256').read_text().splitlines())
    for r, data in headers.items():
        assert hashlib.sha256(data).hexdigest() == sums[f'r{r}.bin'], r
    print('6 region sectors (T00/S9-SE) match docs/regions.sha256: OK')

    for r, (fauna, lat, index, wind, rain, dec, summit, rivers, scrub) in PINNED.items():
        e = regions.decode(r, headers[r])
        c = e['climate']
        assert headers[r][0x1F] == r
        assert tuple((s['name'], s['rate']) for s in e['species']) == fauna, (r, e['species'])
        assert (c['latitude_min'], c['latitude_max']) == lat
        assert (c['climate_index'], c['wind_max']) == (index, wind)
        assert (c['precipitation_min'], c['precipitation_max'], c['precipitation_phase']) == rain
        assert (c['declination'], c['summit_altitude'], c['river_sources'], c['scrub_altitude']) == \
            (dec, summit, rivers, scrub), (r, c)
        assert c['rock_altitude'] == 120 and c['byte_b7'] == c['byte_b8'] == 0
        empty = [s for s in regions.species(headers[r]) if not s['rate']]
        assert all(s['name'] == 'NO ANIMAL' for s in empty) and len(empty) == 4 - len(fauna)
    for slot, pairs in SIERRA_FILTERS.items():
        s = regions.species(headers[2])[slot - 1]
        assert tuple((f['centre'], f['width']) for f in s['filters']) == pairs, slot
    s = regions.species(headers[2])
    assert [(x['injury']['14'], x['injury']['15'], x['injury']['18'], x['success']['18'],
             x['severity_exponent'], x['theft']) for x in s[:3]] == \
        [(10, 2, 35, 3, 1, 1), (10, 2, 25, 10, 2, 1), (30, 3, 20, 30, 5, 0)]
    print('decoded fauna records, climate blocks and Sierra filters/reactions pinned: OK')

    topo = HERE / 'build/files/TOPO.B'
    if topo.exists():
        t = topo.read_bytes()
        same = [o for o in range(0x100) if t[o] == headers[2][o]]
        region_bytes = [o for o in range(0x7F) if o not in (0x3F, 0x5F)] + \
            list(range(0xA4, 0xA8)) + list(range(0xAA, 0xBB)) + list(range(0xD0, 0x100))
        assert set(region_bytes) <= set(same), sorted(set(region_bytes) - set(same))
        assert (t[0xA8], t[0xA9]) == (38, 17)
        assert regions.tmake0_declination(35, 40, 17, 38) == 17
        print('Sierra sector = supplied TOPO $6000-$60FF on every region byte: OK')

    assert regions.go2_temperatures(38) == (41, 77)          # $4BB0/$4BB1 of the port
    assert regions.snowline(38) == 72                         # 7200 ft: map.bin snow 48 + base 24
    assert [regions.season_class(v) for v in (23, 22, -22, -23)] == ['north', 'tropical', 'tropical', 'south']
    assert regions.base_altitude(headers[2], 2, 4, 84) == 24  # POSTP: map.bin base
    assert regions.base_altitude(headers[3], 3, 4, 84, 0) == 0
    print('GO2 temperatures, snow line, GO1 seasons and POSTP base on the Sierra: OK')

    go3 = HERE / 'build/files/GO3.B'
    if go3.exists():
        texts = regions.go3_texts(go3.read_bytes())
        assert texts[1][1] == 'GRIZZLY BEAR, TIMBER WOLF, & MOOSE.'
        assert texts[6] == ('CHILE', 'PUMA, AND AN OCCASIONAL MOUNTAIN CAT.')
        print('GO3 region names and fauna sentences: OK')

    manifest = HERE / 'build/original_graphics/manifest.json'
    if manifest.exists():
        m = json.loads(manifest.read_text())['sprites']
        assert set(m) == set(SPRITES), sorted(set(m) ^ set(SPRITES))
        for name, (track, sector, columns, height, size) in SPRITES.items():
            e = m[name]
            assert (e['track'], e['sector'], e['columns'], e['height'], e['encoded_bytes']) == \
                (track, sector, columns, height, size), name
            assert e['encoded_bytes'] <= 256 * e['sectors']
            if 'dos_columns' in e:
                assert abs(e['dos_columns'] - columns) <= 3, name
        ids = [regions.SPRITE_ORDER.index(n) for n in
               ('grizzly_bc', 'wolf_bc', 'moose_bc', 'bear', 'cougar', 'rattlesnake')]
        assert ids == list(range(6))
        print('27 Journey sprites: positions, sizes and DOS column counts: OK')

    z = regions.dos_zip()
    if z:
        check = regions.dos_check(headers, z)
        for r, v in check.items():
            assert v['climate_block'] and v['a4_a7'] and v['filters'], r
            ids = [i for i in v['animal_ids'] if i]
            assert len(ids) == len(PINNED[r][0])
            assert [regions.SPRITE_ORDER[i - 1] for i in ids]
        assert all(not v['record_differences'] for r, v in check.items() if r != 2)
        # MS-DOS lowered the three Sierra rates (80/40/100 -> 70/35/70).
        assert check[2]['record_differences'] == [(1, 12, 80, 70), (2, 12, 40, 35), (3, 12, 100, 70)]
        print('MS-DOS .CIM: same climate block $60AA-$60BA, $60A4-$60A7 and filters: OK')
    else:
        print('MS-DOS archive absent: cross-check skipped')

    fauna = HERE / 'build/regions/fauna.json'
    if fauna.exists():
        f = json.loads(fauna.read_text())['regions']
        for r, (pairs, *_rest) in PINNED.items():
            assert [(s['name'], s['rate']) for s in f[str(r)]['species']] == list(pairs), r
        assert [s['sprite'] for s in f['4']['species']] == ['dani', 'adder', 'crocodile']
        print('probe output build/regions/fauna.json consistent with the headers: OK')


if __name__ == '__main__':
    main()
