#!/usr/bin/env python3
"""tools/stars_ref.py and tools/stars_catalog.py, pure Python (no emulator).

The integer reference (what the 6502 computes, bit for bit) is checked
against an independent floating-point almanac (Meeus: GMST, low-precision
Sun, equation of time) and against facts any 1985 almanac gives: Polaris at
the height of the latitude, Sirius rising in the evening and culminating at
local midnight around 1 January, the Southern Cross in the southern sky of
Bolivia in May and never above the Sierra Nevada. Also: tables, list and
bucket invariants, the Moon mask, mood rules, LOOK STARS, PNG previews.
"""
import math, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
import stars_ref as R  # noqa: E402
import stars_catalog as K  # noqa: E402
import dhgr_palette as P  # noqa: E402


def star(name):
    return next(s for s in R.CATALOGUE if s['name'] == name)


def test_catalogue():
    cat = R.CATALOGUE
    assert len(cat) == 282 and len(K.encode()) == 846
    assert len({s['name'] for s in cat}) == len(cat), 'unique names'
    assert [s['name'] for s in cat[:5]] == ['ACRUX', 'MIMOSA', 'GACRUX', 'POLARIS', 'IMAI']
    rest = [s['v'] for s in cat[5:]]
    assert rest == sorted(rest), 'magnitude order after the priority stars'
    assert max(s['v'] for s in cat) == 3.50 and sum(s['v'] <= 2.31 for s in cat) == 78
    assert sum(s['cls'] == 0 for s in cat) == 21          # first magnitude, Sirius..Regulus
    assert R.LAYOUT == ((0, 0, 1, 1, 2), (24, 91))
    # Sources: the 79 brightest from Hipparcos (positions, SIMBAD) and the
    # Bright Star Catalogue (V, B-V); the 203 others from the BSC5 (CDS V/50).
    sources = [s['source'] for s in cat]
    assert sources.count('Hipparcos') == 79 and all(x.startswith('BSC5 HR ') for x in sources
                                                    if x != 'Hipparcos')
    hr = {int(s['source'][8:]): s for s in cat if s['source'] != 'Hipparcos'}
    assert len(hr) == 203 and 5958 not in hr and 681 not in hr     # T CrB, Mira left out
    # Pins: BSC5 values (J2000) and 1985.0 records of a few additions.
    pins = {39: ('GAM PEG', 2.83, -0.23, 3.309, 15.184), 99: ('ALF PHE', 2.39, 1.09, 6.571, -42.306),
            4295: ('BET UMA', 2.37, -0.02, 165.460, 56.383),
            6175: ('ZET OPH', 2.56, 0.02, 249.290, -10.567),
            8414: ('ALF AQR', 2.96, 0.98, 331.446, -0.320),      # -0 deg 19': sign kept
            7710: ('TET AQL', 3.23, -0.07, 302.826, -0.821),
            1865: ('ALF LEP', 2.58, 0.21, 83.182, -17.822),
            5602: ('BET BOO', 3.50, 0.97, 225.487, 40.391)}    # the faintest kept
    for n, (name, v, bv, ra, dec) in pins.items():
        st = hr[n]
        assert (st['name'], st['v'], st['bv']) == (name, v, bv), (n, st['name'])
        assert abs(st['ra2000'] - ra) < 0.002 and abs(st['dec2000'] - dec) < 0.002, \
            (n, st['ra2000'], st['dec2000'])
    assert star('SIRIUS')['record'].hex() == '75821a' and star('POLARIS')['record'].hex() == 'd4008b'
    worst = 0
    for k, s in enumerate(cat):
        rec = s['record']
        assert rec[0] | (rec[1] & 15) << 8 == s['ra_q'] < 2240
        assert s['ra_q'] == round(s['ra'] / 360 * 2240) % 2240
        assert rec[2] == s['dec_u'] == round(abs(s['dec']) * 560 / 360) <= 140
        assert rec[1] >> 7 == (s['dec'] < 0) and rec[1] >> 4 & 3 == s['tint'] and not rec[1] & 0x40
        assert K.star_class(k, R.LAYOUT) == s['cls']
        a, d = map(math.radians, (s['ra'], s['dec']))
        a0, d0 = map(math.radians, (s['ra2000'], s['dec2000']))
        cosang = (math.sin(d) * math.sin(d0) + math.cos(d) * math.cos(d0) * math.cos(a - a0))
        worst = max(worst, math.degrees(math.acos(min(1, cosang))))
    assert 0.15 < worst < 0.25, worst                     # J2000 -> 1985.0: <= 12.6'
    # No two stars within 0.3 deg: close pairs are the combined light of the
    # first table (Acrux, Castor, Alpha Centauri).
    for i, s1 in enumerate(cat):
        for s2 in cat[i + 1:i + 40]:
            a1, d1, a2, d2 = map(math.radians, (s1['ra'], s1['dec'], s2['ra'], s2['dec']))
            c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(a1 - a2)
            assert math.degrees(math.acos(min(1, c))) > 0.3, (s1['name'], s2['name'])
    assert star('POLARIS')['landmark'] == 1 and star('ACRUX')['landmark'] == 2
    print(f'  catalogue: {len(cat)} stars to V = 3.50 (79 Hipparcos + 203 BSC5), 846 bytes, '
          f'classes {R.LAYOUT}, precession 1985 - J2000 <= {worst:.3f} deg: OK')


def test_tables():
    diffs = [(R.C_TABLE[i + 1] - R.C_TABLE[i]) & 0xFFFF for i in range(46)]
    assert 1250 < min(diffs) and max(diffs) < 1700, (min(diffs), max(diffs))
    assert R.T_TABLE == tuple(sorted(R.T_TABLE)) and R.T_TABLE[R.T_HIGH] >= 256 > R.T_TABLE[R.T_HIGH - 1]
    assert R.AT_TABLE[0] == 0 and R.AT_TABLE[128] == 70
    assert all(R.lst_quarter(l) == round(l * 2240 / 65536) % 2240 or (l * 2240) % 65536 * 2 == 65536
               for l in range(0, 65536, 7))
    assert all(b - a in (0, 1) for a, b in zip(R.AT_TABLE, R.AT_TABLE[1:]))
    assert all(R.lat_units(l) == round(l * 14 / 9 + 1e-9) or (l * 14) % 9 * 2 == 9 for l in range(91))
    assert all(R.lat_units(l) == (l * 28 + 9) // 18 for l in range(91))
    print('  tables: C (47 words, steps 1306..1616 < 4096), T (80, 9 bits), AT (129): OK')


def test_sidereal_time():
    worst = 0
    for day in range(0, 365, 3):
        for minute in range(0, 1440, 37):
            for _, lat, lon in R.REGIONS.values():
                d = R.lst16(day, minute, lon) * 360 / 65536 - R.lst_float(day, minute, lon)
                worst = max(worst, abs((d + 180) % 360 - 180))
    assert worst < 0.25, worst
    print(f'  local sidereal time vs Meeus GMST + equation of time: max {worst:.3f} deg: OK')


def test_positions():
    alt_err, az_err, row_low, row_all = [], [], [], []
    for day in range(0, 365, 9):
        for minute in range(0, 1440, 131):
            for _, lat, lon in R.REGIONS.values():
                lst = R.lst16(day, minute, lon)
                for s in R.CATALOGUE:
                    up, az, row = R.position(lst, lat, s)
                    alt, azf = R.altaz_float(day, minute, lat, lon, s['ra'], s['dec'])
                    if not 1 < alt < 59:
                        continue
                    alt_err.append(math.degrees(math.asin(up / 65536)) - alt)
                    az_err.append(((az - azf * 560 / 360 + 280) % 560 - 280)
                                  * math.cos(math.radians(alt)))
                    if row is not None:
                        (row_low if alt < 30 else row_all).append(row - R.row_float(alt))
    sd = statistics.pstdev(alt_err)
    assert abs(statistics.mean(alt_err)) < 0.05 and sd < 0.3 and max(map(abs, alt_err)) < 1.2
    assert max(map(abs, az_err)) < 2.0 and statistics.pstdev(az_err) < 0.5
    assert all(-1 < e < 2 for e in row_low), (min(row_low), max(row_low))
    assert all(-2.5 < e < 4.5 for e in row_all), (min(row_all), max(row_all))
    print(f'  {len(alt_err)} positions vs float: altitude mean {statistics.mean(alt_err):+.3f} '
          f'sd {sd:.3f} max {max(map(abs, alt_err)):.2f} deg; azimuth x cos(alt) sd '
          f'{statistics.pstdev(az_err):.2f} max {max(map(abs, az_err)):.2f} units; row '
          f'(INT, so +0.5 on average) {min(row_low):+.1f}..{max(row_low):+.1f} below 30 deg, '
          f'{min(row_all):+.1f}..{max(row_all):+.1f} at 30-59 deg: OK')


def test_polaris():
    pol = star('POLARIS')
    for r in (1, 2):
        name, lat, lon = R.REGIONS[r]
        for day in range(0, 365, 30):
            for minute in range(0, 1440, 60):
                up, az, row = R.position(R.lst16(day, minute, lon), lat, pol)
                assert abs(R.alt_degrees(up) - lat) <= 1.5, (name, day, minute, R.alt_degrees(up))
                assert min(az, 560 - az) <= 2, (name, az)
                assert row is not None and abs(row - (95 - 48 * math.tan(math.radians(lat)))) < 3
    print('  Polaris: height = latitude +-1.5 deg, bearing north +-2 units (BC, Sierra): OK')


def test_sirius():
    sir = star('SIRIUS')
    _, lat, lon = R.REGIONS[2]

    def rise(f):
        return next(m for m in range(1, 1440) if f(m - 1) <= 0 < f(m))

    for day in (0, 30, 125, 300):
        fl = lambda m: R.altaz_float(day, m, lat, lon, sir['ra'], sir['dec'])[0]
        it = lambda m: R.position(R.lst16(day, m, lon), lat, sir)[0]
        rf, ri = rise(fl), rise(it)
        assert abs(rf - ri) <= 5, (day, rf, ri)
    transit = max(range(1440), key=lambda m: R.altaz_float(0, m, lat, lon, sir['ra'], sir['dec'])[0])
    assert transit >= 23 * 60 + 30 or transit <= 30, transit   # midnight culmination, 1 Jan
    rf = rise(lambda m: R.altaz_float(0, m, lat, lon, sir['ra'], sir['dec'])[0])
    print(f'  Sirius, Sierra, 1 Jan 1985: rises {rf // 60}:{rf % 60:02d}, culminates '
          f'{transit // 60}:{transit % 60:02d} apparent solar time; integer rise within 5 min '
          f'(4 dates): OK')


def test_southern_cross():
    _, lat, lon = R.REGIONS[5]
    vis = R.visible(125, 21 * 60, lat, lon)
    cross = {v['star']['name']: v for v in vis if v['star']['name'] in K.CROSS}
    assert set(cross) == set(K.CROSS), cross.keys()
    for v in cross.values():
        assert 160 * 560 / 360 < v['az'] < 210 * 560 / 360 and 40 < v['row'] < 80, v
    _, lat, lon = R.REGIONS[2]
    acrux = star('ACRUX')
    assert all(R.position(R.lst16(125, m, lon), lat, acrux)[0] <= 0 for m in range(0, 1440, 10))
    for r in (4, 6):
        _, lat, lon = R.REGIONS[r]
        assert any(v['star']['name'] == 'ACRUX' for m in range(0, 1440, 60)
                   for v in R.visible(125, m, lat, lon))
    print('  Southern Cross: four stars due south from Bolivia (6 May 21 h), up in New Guinea '
          'and Chile, never above the Sierra: OK')


def test_list_and_moon():
    longest = 0
    for r, (_, lat, lon) in R.REGIONS.items():
        for day, minute in ((0, 0), (125, 23 * 60), (200, 3 * 60), (56, 30)):
            vis = R.visible(day, minute, lat, lon)
            assert len(vis) <= R.LIST_MAX
            longest = max(longest, len(vis))
            attr, row, buckets, srt = R.resident(vis)
            assert [v['az'] >> 4 for v in srt] == sorted(v['az'] >> 4 for v in vis)
            assert buckets[35] == len(vis) and list(buckets) == sorted(buckets)
            for b in range(35):                 # catalogue order inside a bucket
                idx = [v['index'] for v in srt[buckets[b]:buckets[b + 1]]]
                assert idx == sorted(idx)
            assert R.decode_resident(attr, row, buckets) == [R.entry(v['attr'], v['row'], v['az'])
                                                              for v in srt]
            for i, v in enumerate(srt):
                assert buckets[v['az'] >> 4] <= i < buckets[(v['az'] >> 4) + 1]
                assert 16 <= v['row'] <= 95 and attr[i] & 15 == v['az'] & 15
                assert attr[i] >> 6 == v['star']['cls'] and v['colour'] in (P.WHITE, P.YELLOW, P.LIGHT_BLUE)
            assert not any(attr[len(vis):]) and not any(row[len(vis):])
    # Bolivia, 26 February 0 h 30: 161 stars up, the list keeps the 160 first.
    _, lat, lon = R.REGIONS[5]
    full = R.visible(56, 30, lat, lon, limit=999)
    assert len(full) == 161 and R.visible(56, 30, lat, lon) == full[:160]
    # The module's early skip changes nothing: up <= 0 at every hour angle.
    for _, lat, _ in R.REGIONS.values():
        for s in R.CATALOGUE:
            if R.never_rises(lat, s):
                assert all(R.position(l, lat, s)[0] <= 0 for l in range(0, 65536, 29)), s['name']
    _, lat, lon = R.REGIONS[2]
    vis = R.visible(125, 23 * 60, lat, lon)
    v = vis[3]
    moon = (v['az'], v['row'])
    masked = R.visible(125, 23 * 60, lat, lon, moon)
    assert all(m['index'] != v['index'] for m in masked)
    assert R.behind_moon(v['az'] + 5, v['row'] + 3, moon) and not R.behind_moon(v['az'] + 6, v['row'], moon)
    assert R.behind_moon(v['az'], v['row'] + 8, moon) and not R.behind_moon(v['az'], v['row'] + 9, moon)
    assert not R.behind_moon(v['az'], v['row'], (v['az'], 255))
    print(f'  list: <= {R.LIST_MAX} (longest here {longest}), 36 buckets of 16 units in catalogue '
          f'order, attr; early skip of the stars that never rise; Moon disc mask: OK')


def test_moods():
    T = R.threshold
    for mood in ('day', 'overcast', 'golden', 'sunset', 'overcast dusk', 'civil', 'nautical'):
        assert T(mood, False) == 0
    assert (T('night bright', False), T('night dim', False), T('night dark', False)) == (0x80, 0xC0, 0xC0)
    assert all(T(m, True) == 0 for m in P.MOODS)
    M = R.engine_mood
    assert M(False, sun8=60) == 'day' and M(False, sun8=-5) == 'civil' and M(False, sun8=-20) == 'nautical'
    assert M(True, view_dark=True) == 'night dark'
    assert M(True, moon8=60, phase=11) == 'night bright'           # full Moon: classes 0-1
    assert M(True, moon8=10, phase=11) == 'night bright'           # low: 11 - 2 = 9
    assert M(True, moon8=-5, phase=11) == 'night dark'             # set: every star
    print('  moods: none by day, at dusk or under clouds; full Moon $80, dim and dark $C0: OK')


def test_look_stars():
    _, lat, lon = R.REGIONS[2]
    lines = R.look_stars(125, 23 * 60, lat, lon, 'night dark', False)
    assert lines[0].startswith('POLARIS: BEARING 0, HEIGHT 3'), lines
    _, lat, lon = R.REGIONS[5]
    lines = R.look_stars(125, 21 * 60, lat, lon, 'night bright', False)
    assert lines[0].startswith('SOUTHERN CROSS: BEARING '), lines
    assert 160 <= int(lines[0].split()[3].rstrip(',')) <= 200, lines
    assert R.look_stars(125, 13 * 60, lat, lon, 'day', False)[0].startswith('IT IS NOT DARK')
    assert R.look_stars(125, 23 * 60, lat, lon, 'night dark', True) == ['CLOUDS HIDE THE STARS.']
    assert all(len(s) <= 40 for r in R.REGIONS.values()
               for s in R.look_stars(125, 22 * 60, r[1], r[2], 'night dark', False))
    print('  LOOK STARS: Polaris (Sierra), Southern Cross (Bolivia), day and clouds, <= 40 chars: OK')


def test_previews():
    out = HERE / 'build/stars'
    sys.argv = ['stars_ref.py', '--out', str(out)]
    R.main()
    assert (out / 'view_bolivia_south.png').exists()


def main():
    test_catalogue()
    test_tables()
    test_sidereal_time()
    test_positions()
    test_polaris()
    test_sirius()
    test_southern_cross()
    test_list_and_moon()
    test_moods()
    test_look_stars()
    test_previews()
    print('Stars reference: OK')


if __name__ == '__main__':
    main()
