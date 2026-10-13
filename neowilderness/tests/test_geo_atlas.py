#!/usr/bin/env python3
"""tools/geo_atlas.py: codec round-trips and deterministic sizes (pure Python).

No emulator, no disk image. Real data (build/re_geography, build/files/TOPO.B)
is used when present; generated maps come from tools/mkmap.py.
"""
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
import geo_atlas as g  # noqa: E402
import mkmap           # noqa: E402

CODECS = g.CODECS


def synthetic_fine(kind, seed=3):
    """Small hand-made geographies covering the codec edge cases."""
    rnd = random.Random(seed)
    cells = bytearray(g.W * g.H)
    woods = bytearray(g.WROW * g.H)
    for y in range(g.H):
        for x in range(g.W):
            if kind == 'flat':
                v = 10
            elif kind == 'ramp':
                v = (x // 3 + y // 5) % 120
            elif kind == 'noise':
                v = rnd.randrange(126) | (0x80 if rnd.random() < .1 else 0)
            else:                                   # 'hydro': rivers and lakes
                v = 20 + (x + y) // 16
                if 40 <= x < 60 and 30 <= y < 50:
                    v = 0xC0 | 18                   # lake, Sierra lake bit
                elif x == 60 and 30 <= y < 50 or y == 100:
                    v = 0x80 | 17                   # river touching the lake
            cells[y * g.W + x] = v
    if kind == 'noise':
        woods = bytearray(rnd.randrange(256) for _ in range(len(woods)))
    elif kind != 'flat':
        for y in range(0, g.H, 2):
            for x in range(0, 40):                  # wooded from column 0
                woods[y * g.WROW + x // 8] |= 1 << (x % 8)
    return g.Fine(kind, cells, woods, (10, 10), (200, 150), lakebit=(kind == 'hydro'))


def round_trip(fine, shapes=('band7', 'tile16', 'tile32x24'), codecs=CODECS, limit=None):
    """Encode/decode every block (or the first `limit`) -> {(shape, codec): bytes}."""
    sizes = {}
    coarse = fine.coarse()
    for shape in shapes:
        for codec in codecs:
            total = 0
            for b in g.blocks(fine, shape)[:limit]:
                p, cycles = g.encode_block(codec, b, fine.lakebit, coarse)
                assert g.decode_block(codec, p, b, fine.lakebit, coarse) == b.raw(), \
                    (fine.name, shape, codec, b.x0, b.y0)
                assert cycles > 0
                total += len(p)
            sizes[shape, codec] = total
    return sizes


def test_bitstream():
    for n in (0, 1, 14, 15, 16, 269, 270, 271, 524, 525, 1568):
        w = g.BitWriter()
        w.run(n)
        w.put(5, 3)
        r = g.BitReader(w.data())
        assert r.run() == n and r.get(3) == 5, n
    print('  run lengths 0..1568 and bit fields round-trip')


def test_blocks():
    fine = synthetic_fine('ramp')
    for shape in g.SHAPES:
        bl = g.blocks(fine, shape)
        assert len(bl) == g.block_count(shape)
        assert sum(len(b.cells) for b in bl) == g.W * g.H
        assert sum(len(b.raw()) for b in bl) == g.FINE_BYTES
        for i, b in enumerate(bl):
            assert g.block_index(shape, b.x0, b.y0) == i
            assert g.block_index(shape, b.x0 + b.w - 1, b.y0 + b.h - 1) == i
    print(f'  {len(g.SHAPES)} block shapes tile the 224 x 168 grid and the 42 336 bytes')


BIT_CODECS = ('rle', 'nib', 'vlc', 'coarse')
# Deterministic sizes (bytes) of the whole synthetic grids, band7 / tile16 /
# tile32x24. A codec change must update these and docs/GEOGRAPHY.md.
PINNED = {
    'flat': {('band7', 'rle'): 720, ('band7', 'nib'): 9456, ('band7', 'vlc'): 4752,
             ('band7', 'coarse'): 3552, ('tile16', 'rle'): 896, ('tile16', 'nib'): 9716,
             ('tile16', 'vlc'): 5012, ('tile16', 'coarse'): 3682, ('tile32x24', 'rle'): 686,
             ('tile32x24', 'nib'): 9506, ('tile32x24', 'vlc'): 4802, ('tile32x24', 'coarse'): 3577},
    'ramp': {('band7', 'rle'): 25728, ('band7', 'nib'): 9816, ('band7', 'vlc'): 5328,
             ('band7', 'coarse'): 5045, ('tile16', 'rle'): 30369, ('tile16', 'nib'): 10421,
             ('tile16', 'vlc'): 5871, ('tile16', 'coarse'): 5501, ('tile32x24', 'rle'): 27797,
             ('tile32x24', 'nib'): 9940, ('tile32x24', 'vlc'): 5334, ('tile32x24', 'coarse'): 5154,
             ('band7[:4]', 'lz'): 1150, ('band7[:4]', 'overlay'): 1682},
    'hydro': {('band7', 'rle'): 5441, ('band7', 'nib'): 9932, ('band7', 'vlc'): 6014,
              ('band7', 'coarse'): 4913, ('tile16', 'rle'): 10404, ('tile16', 'nib'): 10600,
              ('tile16', 'vlc'): 6745, ('tile16', 'coarse'): 5407, ('tile32x24', 'rle'): 7828,
              ('tile32x24', 'nib'): 10077, ('tile32x24', 'vlc'): 6215, ('tile32x24', 'coarse'): 5027,
              ('band7[:4]', 'lz'): 342, ('band7[:4]', 'overlay'): 880},
    'noise': {('band7', 'rle'): 42672, ('band7', 'nib'): 71507, ('band7', 'vlc'): 76129,
              ('band7', 'coarse'): 63190, ('tile16', 'rle'): 42783, ('tile16', 'nib'): 71740,
              ('tile16', 'vlc'): 76375, ('tile16', 'coarse'): 63357, ('tile32x24', 'rle'): 42679,
              ('tile32x24', 'nib'): 71685, ('tile32x24', 'vlc'): 76315, ('tile32x24', 'coarse'): 63258,
              ('band7[:4]', 'lz'): 7936, ('band7[:4]', 'overlay'): 7056},
}
GENERATED = {('tile32x24', 'lz'): 15093, ('tile32x24', 'overlay'): 19400, ('tile32x24', 'rle'): 29990,
             ('tile32x24', 'nib'): 10908, ('tile32x24', 'vlc'): 8598, ('tile32x24', 'coarse'): 5853}


def test_synthetic():
    sizes = {}
    for kind in ('flat', 'ramp', 'hydro', 'noise'):
        fine = synthetic_fine(kind)
        sizes[kind] = round_trip(fine, codecs=BIT_CODECS)
        # pack_boot's optimal parse is very slow on flat data (tool time
        # only): the LZ codecs are checked on four blocks of the others.
        if kind != 'flat':
            sizes[kind].update({(s + '[:4]', c): v for (s, c), v in
                                round_trip(fine, ('band7',), ('lz', 'overlay'), 4).items()})
    for kind, expected in PINNED.items():
        assert sizes[kind] == expected, (kind, sizes[kind])
    assert sizes['flat']['band7', 'rle'] == 24 * 30
    assert sizes['ramp']['tile32x24', 'coarse'] < sizes['ramp']['tile32x24', 'nib']
    for codec in ('nib', 'vlc', 'coarse'):
        assert sizes['noise']['band7', codec] > g.FINE_BYTES, 'noise expands: raw fallback needed'
    print('  flat, ramp, hydro (river touching lake, woods from column 0) and noise: '
          'all codecs round-trip, sizes pinned')
    return sizes


def test_overlay_format():
    fine = synthetic_fine('ramp')
    b = g.blocks(fine, 'band7')[3]
    p = g.ov_encode(b.raw())
    assert p.startswith(g.OV_MAGIC) and p.endswith(b.raw()[:g.OV_PREFIX])
    assert g.ov_safe(p[g.OV_HEADER:-g.OV_PREFIX][::-1], len(b.raw()))
    assert g.ov_decode(p, len(b.raw())) == b.raw()
    small = g.blocks(fine, (8, 8))[0]
    assert g.ov_encode(small.raw()) == small.raw(), 'blocks <= 128 bytes stay raw'
    print('  retired overlay format: magic, reversed in-place stream, raw 128-byte prefix')


def test_generated():
    fine = g.generated(1985, 4)
    sizes = round_trip(fine, shapes=('tile32x24',))
    assert sizes == GENERATED, sizes
    assert sizes['tile32x24', 'coarse'] < sizes['tile32x24', 'vlc'] < sizes['tile32x24', 'nib']
    assert sizes['tile32x24', 'vlc'] < sizes['tile32x24', 'lz']
    print('  mkmap seed 1985 level 4, 49 tiles: all codecs round-trip; '
          + ', '.join(f'{c} {sizes["tile32x24", c]}' for c in CODECS))


def test_sierra():
    build = HERE / 'build'
    if not ((build / 're_geography/heights.bin').exists() and (build / 'files/TOPO.B').exists()):
        print('  SKIP Sierra: build/re_geography or build/files/TOPO.B missing')
        return
    fine = g.sierra(build)
    parity = g.parity_reference(fine)
    assert parity in (None, True), 'differs from wilderness parity-stage15 map.bin'
    lz = g.measure(fine, 'band7', 'lz')
    # TODO.md lot 5 reference: 11 305 bytes in 24 independent blocks.
    assert lz['total'] == 11305, lz
    for codec in ('rle', 'nib', 'vlc', 'coarse'):
        r = g.measure(fine, 'band7', codec)          # verifies every block
        assert r['total'] < lz['total'] or codec == 'rle', r
    print(f'  Sierra band7: LZ 11 305 bytes (TODO reference) reproduced'
          + ('' if parity is None else ', identical to parity-stage15 map.bin'))


def test_locality():
    shape = 'band7'
    path = g.line((10, 3), (200, 3))
    assert g.simulate(shape, path, 1)[0] == 1, 'rows 2-4 stay in band 0'
    path = g.line((10, 7), (200, 7))                 # the 3x3 straddles bands 0/1
    d1, changes, per = g.simulate(shape, path, 1)
    d2 = g.simulate(shape, path, 2)[0]
    assert d2 == 2 and d1 > 100 and max(per) == 2
    fine = synthetic_fine('hydro')
    loc = g.locality(fine, 'tile16')
    assert loc['shore']['max'] <= 4
    print('  locality: a band edge thrashes one cached block, two blocks suffice')


def main():
    test_bitstream()
    test_blocks()
    test_synthetic()
    test_overlay_format()
    test_generated()
    test_sierra()
    test_locality()
    print('geo_atlas: OK')


if __name__ == '__main__':
    main()
