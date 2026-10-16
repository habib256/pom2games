#!/usr/bin/env python3
"""Pure Python checks of the DHGR TOPO sheet (tools/topo_dhgr_ref.py), no emulator.

- mapping: row positions, DDA, every cell row sampled, square-ish cells;
- determinism and byte layout of known pixels (both banks, Apple order);
- markers at the header positions (crash, cabin, rangers), edge placement;
- water and woods coverage against the map;
- the integer "6502-style" algorithm (Sheet6502: tables, DDA, floor
  averages, causal tests, packing) reproduces the reference bit for bit,
  for several maps, a legacy map without woods and all vertical precisions;
- table sizes and the cycle budget of the gallery maps.

  test_topo_dhgr.py [--refs]     (--refs: PNG captures in build/topo/)
"""
import argparse, sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import topo_dhgr_ref as R  # noqa: E402
import topo_palette as T  # noqa: E402
import dhgr_palette as P  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

MAPS = {}


def get_map(seed, level):
    if (seed, level) not in MAPS:
        MAPS[seed, level] = R.make_map(seed, level)
    return MAPS[seed, level]


def legacy_map():
    """The synthetic alternate map of test_graphical_topo, without woods."""
    data = bytearray(get_map(1985, 4)[:64 + 9408])
    data[26] = 0
    data[21] = 0
    data[64:64 + 9408] = bytes((x // 4 + y // 6) | (128 if 45 <= x <= 48 else 0)
                               for y in range(84) for x in range(112))
    return bytes(data)


def pixel_nibble(main, aux, x, y):
    """rot(colour) of colour pixel (x, y), read from the banks bit by bit."""
    o, v = hgr_offset(y), 0
    for j in range(4):
        bit = 4 * x + j                 # bit index in the 560-dot row
        i = bit // 7                    # interleaved byte 0..79
        byte = (aux if i % 2 == 0 else main)[o + i // 2]
        v |= ((byte >> (bit % 7)) & 1) << j
    return v


def check_mapping():
    for qb in (1, 2, 3):
        R.QB = qb
        assert R.vq(0) == 83 << qb and R.vq(159) == 0
        assert {R.nearest(sy) for sy in range(R.ROWS)} == set(range(84)), qb
        # DDA of Sheet6502 == closed form
        num = 83 << qb
        step, rem = divmod(num, 159)
        v, acc = num, 158
        for sy in range(R.ROWS):
            assert v == R.vq(sy) == ((159 - sy) * num) // 159
            acc += rem
            v -= step
            if acc >= 159:
                acc -= 159
                v -= 1
        steps = [R.vq(sy) - R.vq(sy + 1) for sy in range(R.ROWS - 1)]
        assert set(steps) <= {step, step + 1}
    R.QB = 1
    # one cell = 1 pixel x 160/83.6 rows; a DHGR pixel is 1.83 rows wide (4:3)
    aspect = (160 / 84) / ((4 / 140) / (3 / 192))
    assert 1.0 < aspect < 1.1, aspect
    # floor averages == exact floor of the interpolation (all h0, h1, q)
    for qb in (1, 2, 3):
        for q in range(1, 1 << qb):
            low = (q & -q).bit_length() - 1
            steps = [(q >> b) & 1 for b in range(low + 1, qb)]
            for h0 in range(0, 126, 5):
                for h1 in range(126):
                    a = (h0 + h1) >> 1
                    for bit in steps:
                        a = (a + (h1 if bit else h0)) >> 1
                    assert a == int(h0 + (h1 - h0) * Fraction(q, 1 << qb)), (qb, q, h0, h1)
    print('  mapping: rows, DDA, nearest rows cover the 84 cell rows, floor averages: OK')


def check_layout():
    assert all(x < R.SHEET_X and 149 <= y <= 157 for x, y in R.SCALE)
    assert all(y < 26 for _, y in R.NORTH + R.ARROW)
    page = [[P.BLACK] * R.COLS for _ in range(R.PAGE_ROWS)]
    known = {(0, 0): 9, (1, 0): 6, (6, 0): 13, (7, 1): 11, (125, 10): 15, (139, 191): 3,
             (3, 64): 12, (70, 100): 1}
    for (x, y), c in known.items():
        page[y][x] = c
    main, aux = R.encode(page)
    for (x, y), c in known.items():
        assert pixel_nibble(main, aux, x, y) == P.rot(c), (x, y)
    # first group of row 0: x0 orange in aux bits 0-3, x1 medium blue across aux/main
    assert aux[0] & 15 == P.rot(9) and (aux[0] >> 4) | (main[0] & 1) << 3 == P.rot(6)
    # solid rows equal the TN #3 patterns
    for c in range(16):
        page = [[c] * R.COLS for _ in range(R.PAGE_ROWS)]
        main, aux = R.encode(page, [5])
        o = hgr_offset(5)
        assert (aux[o], main[o], aux[o + 1], main[o + 1]) == P.PATTERNS[c]
    assert R.decode(*R.encode(page)) == page
    # pack tables == encode on random rows
    import random
    rnd = random.Random(140)
    pk = T.pack_tables()
    for _ in range(50):
        row = [rnd.randrange(16) for _ in range(R.COLS)]
        main, aux = R.encode([row], [0])
        for g in range(20):
            c = row[7 * g:7 * g + 7]
            assert aux[2 * g] == pk['T0'][c[0]] | pk['T1a'][c[1]]
            assert main[2 * g] == pk['T1b'][c[1]] | pk['T2'][c[2]] | pk['T3a'][c[3]]
            assert aux[2 * g + 1] == pk['T3b'][c[3]] | pk['T4'][c[4]] | pk['T5a'][c[5]]
            assert main[2 * g + 1] == pk['T5b'][c[5]] | pk['T6'][c[6]]
    print('  layout: known pixels in both banks, TN #3 patterns, pack tables: OK')


def check_sheet(data, name):
    page = R.sheet(data)
    assert page == R.sheet(data), 'deterministic'
    main, aux = R.encode(page, range(R.ROWS))
    # rows 160..191 are never written
    for y in range(R.ROWS, R.PAGE_ROWS):
        o = hgr_offset(y)
        assert not any(main[o:o + 40]) and not any(aux[o:o + 40])
    # bit for bit: the 6502-style algorithm
    s = R.Sheet6502(data)
    m6, a6 = s.run()
    if (bytes(m6), bytes(a6)) != (main, aux):
        bad = next((x, y) for y in range(R.ROWS) for x in range(R.COLS)
                   if pixel_nibble(m6, a6, x, y) != pixel_nibble(main, aux, x, y))
        raise AssertionError(f'{name}: 6502-style differs first at pixel {bad}')
    # known strip pixels: north arrow shaft white, strip background black
    assert pixel_nibble(main, aux, R.ARROW_X, 20) == P.rot(T.INK)
    assert pixel_nibble(main, aux, 139, 0) == 0 and pixel_nibble(main, aux, 126, 80) == 0
    assert pixel_nibble(main, aux, 0, 80) == 0 and pixel_nibble(main, aux, 13, 80) == 0
    base, snow, top, timber = T.header(data)
    # scale bar: band 0 at the bottom row of the bar, the top band at its top
    assert page[R.BAR_BOTTOM][R.BAR_X0 + 1] in (T.pick(T.tint(0, snow), 0), T.pick(T.tint(0, snow), 1))
    assert page[R.BAR_BOTTOM - 4 * (top + 1)][R.BAR_X0] == T.STRIP

    m = R.map_area(page)       # the map columns (cell x), centred on the screen
    assert len(m[0]) == R.GW and R.SHEET_X == (R.COLS - R.GW) // 2
    # the margins hold the strip: arrow and distance left, altitude scale right
    assert all(0 <= x < R.SHEET_X or R.STRIP_X <= x < R.COLS for x, _ in R.strip_pixels(data))
    assert all(x < R.SHEET_X for x, _ in R.NORTH + R.ARROW + R.SCALE)
    # markers at the header positions
    covered = set()
    for letter, x, y in R.markers(data):
        pix = R.marker_pixels(letter, x, y)
        row = R.marker_row(y)
        assert R.nearest(row) == y
        box, ink = T.MARKERS[letter]
        covered |= {p for p in pix if 0 <= p[0] < R.GW}
    for letter, x, y in reversed(R.markers(data)):      # drawn last = on top
        box, ink = T.MARKERS[letter]
        row = R.marker_row(y)
        if letter == 'C':
            assert m[row][x] == box, (letter, x, y)
        pix = R.marker_pixels(letter, x, y)
        glyph = [p for p, c in pix.items() if c == ink]
        assert len(glyph) == sum(bin(b).count('1') for b in T.GLYPHS[letter])
        assert all(0 <= p[0] < R.GW and 0 <= p[1] < R.ROWS for p in pix), (letter, x, y)
    crash = R.markers(data)[-1]
    assert crash == ('C', data[3], data[5])
    assert ('R', data[8], data[9]) in R.markers(data)
    assert (('H', data[17], data[18]) in R.markers(data)) == bool(data[16])

    # water: exactly the nearest water cells, every water cell shown
    grid = data[64:64 + 9408]
    water_px = {(x, sy) for sy in range(R.ROWS) for x in range(R.GW)
                if grid[R.nearest(sy) * 112 + x] & 0x80}
    shown = {(x, sy) for sy in range(R.ROWS) for x in range(R.GW)
             if m[sy][x] in (T.WATER, T.SHORE)}
    assert shown - covered == water_px - covered, name
    cells = {(x, R.nearest(sy)) for x, sy in water_px}
    assert cells == {(i % 112, i // 112) for i, v in enumerate(grid) if v & 0x80}
    # water touching land is the lighter rim; open water is never next to land
    for x, sy in water_px - covered:
        land = any((xx, yy) not in water_px for xx, yy in
                   ((x - 1, sy), (x + 1, sy), (x, sy - 1), (x, sy + 1))
                   if 0 <= xx < R.GW and 0 <= yy < R.ROWS)
        assert m[sy][x] == (T.SHORE if land else T.WATER), (x, sy)

    # woods: WOODS pixels only on forest cells; every plain forest pixel in the
    # woods window is WOODS
    woods_px = {(x, sy) for sy in range(R.ROWS) for x in range(R.GW)
                if m[sy][x] == T.WOODS} - covered
    forest_px = {(x, sy) for sy in range(R.ROWS) for x in range(R.GW)
                 if R.forest(data, x, R.nearest(sy)) and (x, sy) not in water_px}
    assert woods_px <= forest_px, name
    plain = 0
    info = R.samples(data)
    at = lambda x, y: info[y][x]
    for x, sy in forest_px - covered:
        s0 = at(x, sy)
        if not (s0[1] and T.woods_dot(x, sy)):
            continue
        around = [at(xx, yy) for xx, yy in
                  ((x - 1, sy), (x + 1, sy), (x, sy - 1), (x, sy + 1))
                  if 0 <= xx < R.GW and 0 <= yy < R.ROWS]
        if all(n is not None and n[0] == s0[0] for n in around):
            plain += 1
            assert (x, sy) in woods_px, (x, sy)
    if data[26]:
        forest_cells = sum(R.forest(data, x, y) and not grid[y * 112 + x] & 0x80
                           for y in range(84) for x in range(112))
        assert forest_cells == 0 or woods_px, name
    else:
        assert not woods_px and not forest_px
    cyc = R.estimate(s.n)
    return page, s, cyc, len(water_px), len(woods_px), len(forest_px), plain


def check_rules(data):
    """Index contours are bold (both sides); normal contours one pixel."""
    page = R.map_area(R.sheet(data))
    base, snow, _, _ = T.header(data)
    info = R.samples(data)
    covered = set()
    for m in R.markers(data):
        covered |= set(R.marker_pixels(*m))
    bold = normal = 0
    for sy in range(1, R.ROWS):
        for x in range(R.GW):
            a, b = info[sy][x], info[sy - 1][x]
            if a is None or b is None or a[0] == b[0]:
                continue
            if T.index_count(a[0], base) != T.index_count(b[0], base):
                bold += 1           # both pixels of the crossing
                for xx, yy, band in ((x, sy, a[0]), (x, sy - 1, b[0])):
                    assert (xx, yy) in covered or \
                        page[yy][xx] == T.INDEX[T.ramp_index(band, snow)], (xx, yy)
            else:
                normal += 1         # the south pixel
                assert (x, sy) in covered or page[sy][x] in (
                    T.LINE[T.ramp_index(a[0], snow)], T.INDEX[T.ramp_index(a[0], snow)]), (x, sy)
    assert bold and normal
    # labels: thousands of feet at every index band of the bar
    labels = [str((4 * b + base) // 10) for b in range(1, 32) if T.is_index(b, base)]
    assert labels[:4] == ['4', '6', '8', '10'], labels
    print(f'  contours: {normal} normal crossings (1 px), {bold} index crossings (bold): OK')


def check_edges():
    data = bytearray(get_map(1985, 4))
    # crash in the north-east corner, rangers in the south-west, no cabin
    data[3], data[5] = 111, 83
    data[8], data[9] = 0, 0
    data[16] = 0
    data = bytes(data)
    page, s, *_ = check_sheet(data, 'edges')
    for letter, x, y in R.markers(data):
        pix = R.marker_pixels(letter, x, y)
        assert all(0 <= p[0] < R.GW and 0 <= p[1] < R.ROWS for p in pix), letter
    assert R.marker_row(83) == 0 and R.marker_row(0) == R.ROWS - 1
    print('  markers at the edges stay in the map area: OK')


def check_tables_budget(results):
    sizes = T.table_sizes()
    assert sum(v for k, v in sizes.items() if k.startswith('fill')) == 8 * 65
    assert sizes['mark'] == 65 and sizes['indexk'] == sizes['idxk'] == 64
    assert sum(v for k, v in sizes.items() if k.startswith('T')) == 160
    assert sum(sizes.values()) <= 1024
    for name, cyc in results:
        assert cyc < 2.0 * 1_020_484, (name, cyc)
    for line in R.LEGEND:
        assert len(line) <= 79, line
    print(f'  tables {sum(sizes.values())} bytes; cycle estimates '
          + ', '.join(f'{n} {c / 1_020_484:.2f} s' for n, c in results) + ': OK')


def refs():
    out = HERE / 'build/topo'
    out.mkdir(parents=True, exist_ok=True)
    for seed, level in R.GALLERY:
        data = get_map(seed, level)
        (out / f'map_{seed}_{level}.bin').write_bytes(data)
        R.render_files(data, out / f'topo_{seed}_{level}')
    R.render_files(legacy_map(), out / 'topo_legacy')
    print(f'  captures written to {out}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--refs', action='store_true')
    a = ap.parse_args()
    if a.refs:
        refs()
        return
    check_mapping()
    check_layout()
    results = []
    for seed, level in ((1985, 4), (7, 1), (2026, 7)):
        data = get_map(seed, level)
        _, _, cyc, w, wd, f, plain = check_sheet(data, f'{seed}/{level}')
        results.append((f'{seed}/{level}', cyc))
        print(f'  map {seed}/{level}: water {w} px, woods {wd} of {f} forest px '
              f'({plain} plain checked), 6502-style identical: OK')
    _, _, cyc, *_ = check_sheet(legacy_map(), 'legacy')
    results.append(('legacy', cyc))
    print('  legacy map (no woods, no highest level): OK')
    for qb in (2, 3):
        R.QB = qb
        check_sheet(get_map(1985, 4), f'QB={qb}')
    R.QB = 1
    print('  QB 2 and 3 (quarters, eighths) also bit for bit: OK')
    check_rules(get_map(1985, 4))
    check_edges()
    check_tables_budget(results)
    print('DHGR TOPO reference: OK')


if __name__ == '__main__':
    main()
