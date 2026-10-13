#!/usr/bin/env python3
"""geo_atlas.py: lot 5 measurements for a resident fine-geography atlas.

Read-only analysis. A fine geography is the 224 x 168 native grid used by
cell_native (src/geography.s): one byte per cell (level, bit 7 water, bit 6
lake when the map uses the Sierra lake bit) plus the 28-byte-per-row woodland
bitmap, 42 336 bytes in all. This tool:

* builds fine geographies from the original data (build/re_geography ROM
  samples + build/files/TOPO.B, or TOPO.B alone through tools/topo.py), from
  tools/mkmap.py at several seeds and levels, and from adversarial synthetic
  data (noise, roughened terrain, dense rivers);
* splits them into blocks (24 bands of 7 rows as today, other row bands,
  16x16, 32x32, 32x24 and 56x42 tiles);
* compresses every block independently with the current loader LZ
  (tools/pack_boot.py), the retired in-place overlay LZ (format of the removed
  tools/pack_overlay.py, rebuilt on pack_boot), a byte RLE and three
  bit-packed elevation-delta codecs designed here for 6502 decoding;
* estimates decoder cycles from instruction counts of each decoder loop;
* measures query locality (blocks per WALK/SWIM step, per shore collection,
  block changes and LRU decodes along routes from the crash to the rangers).

Usage: geo_atlas.py [--quick] [--out build/geo] [--jobs N]
"""
import argparse
import json
import math
import random
import sys
from collections import Counter, OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
import mkmap                                   # noqa: E402
import topo                                    # noqa: E402
from pack_boot import compress as lz_compress, decompress as lz_decompress  # noqa: E402

W, H = mkmap.W, mkmap.H            # 224 x 168 fine cells
WROW = W // 8                      # woodland bytes per row
FINE_BYTES = W * H + WROW * H      # 42 336
CLOCK = 1_022_727                  # Apple IIe cycles per second
RECORD = 7                         # NEOWILD.DAT record (kind, address, length, stored)


# ---------------------------------------------------------------- geographies

class Fine:
    """A native fine geography: cells (W*H bytes), woods (WROW*H bitmap).

    lakebit: water cells keep their level in bits 0-5 and bit 6 marks a lake
    (the Sierra comparison banks). Generated maps have no lake/river
    distinction: water is level | $80 with a 7-bit level.
    """

    def __init__(self, name, cells, woods, start, goal, lakebit, note=''):
        assert len(cells) == W * H and len(woods) == WROW * H
        self.name, self.cells, self.woods = name, bytes(cells), bytes(woods)
        self.start, self.goal, self.lakebit, self.note = start, goal, lakebit, note

    def level(self, x, y):
        v = self.cells[y * W + x]
        return v & (0x3F if self.lakebit else 0x7F) if v & 0x80 else v

    def water(self, x, y):
        return bool(self.cells[y * W + x] & 0x80)

    def wooded(self, x, y):
        return bool(self.woods[y * WROW + x // 8] >> (x % 8) & 1)

    def raw(self):
        return self.cells + self.woods

    def coarse(self):
        """The resident 112 x 84 grid (mkmap.coarse_grid) derived from it."""
        h = [[self.level(x, y) for x in range(W)] for y in range(H)]
        wet = [[self.water(x, y) for x in range(W)] for y in range(H)]
        return mkmap.coarse_grid(h, wet)


def pack_woods(cover):
    out = bytearray(WROW * H)
    for y in range(H):
        for x in range(W):
            if cover[y][x]:
                out[y * WROW + x // 8] |= 1 << (x % 8)
    return bytes(out)


def topo_woods(raw):
    cover = [[False] * W for _ in range(H)]
    for y, spans in enumerate(topo.woods(raw)):
        for x0, x1 in spans:
            for x in range(x0, min(x1, W - 1) + 1):
                cover[y][x] = True
    return pack_woods(cover)


def topo_ends(raw):
    """Crash and rangers from the TOPO header ($6083 y,x and $6080 y,x)."""
    return (raw[0x84], raw[0x83]), (raw[0x81], raw[0x80])


def sierra(build=HERE / 'build'):
    """Native Sierra geography: ROM samples of $15A8 + TOPO woodland.

    Same bytes as the comparison banks of tests/test_adventure.original_map
    (types 1 = lake -> $C0, $80 = river -> $80).
    """
    raw = (build / 'files/TOPO.B').read_bytes()
    heights = (build / 're_geography/heights.bin').read_bytes()
    types = (build / 're_geography/types.bin').read_bytes()
    cells = bytes(v | (0xC0 if t == 1 else 0x80 if t == 0x80 else 0)
                  for v, t in zip(heights, types))
    start, goal = topo_ends(raw)
    return Fine('sierra', cells, topo_woods(raw), start, goal, True,
                'original TOPO.B, ROM samples (native banks)')


def sierra_topo(build=HERE / 'build'):
    """TOPO.B alone, interpolated like tools/topo2map.py (float, rounded).

    topo2map.py is a script (it runs on import), so its five lines of
    conversion are restated here on top of topo.rows/topo.heightmap.
    It differs from the ROM samples on interpolated cells.
    """
    raw = (build / 'files/TOPO.B').read_bytes()
    h = [[round(v) for v in r] for r in topo.heightmap(raw)]
    kind = [[0] * W for _ in range(H)]
    for y, items in enumerate(topo.rows(raw)):
        for x, v, f in items:
            if isinstance(f, tuple):
                for xx in range(x, min(f[1], W - 1) + 1):
                    kind[y][xx], h[y][xx] = 0xC0, v
            elif f == 0x80:
                kind[y][x], h[y][x] = 0x80, v
    cells = bytes(h[y][x] | kind[y][x] for y in range(H) for x in range(W))
    start, goal = topo_ends(raw)
    return Fine('sierra-topo', cells, topo_woods(raw), start, goal, True,
                'TOPO.B interpolated by tools/topo.py (no ROM samples)')


def generated(seed, level, extra_rivers=0):
    m = mkmap.Map(seed, level)
    if extra_rivers:
        m.rivers(extra_rivers)
    cells = bytes(m.h[y][x] | (0x80 if m.water[y][x] else 0)
                  for y in range(H) for x in range(W))
    name = f'gen-s{seed}-L{level}' + (f'-r{extra_rivers}' if extra_rivers else '')
    return Fine(name, cells, pack_woods(m.forest), m.start, m.goal, False,
                f'tools/mkmap.py seed {seed} level {level}'
                + (f' + {extra_rivers} extra rivers' if extra_rivers else ''))


def rough(seed, level):
    """Generated terrain with +-1 noise on every dry cell: no long runs."""
    base = generated(seed, level)
    rnd = random.Random(seed ^ 0x52)
    cells = bytearray(base.cells)
    for i, v in enumerate(cells):
        if not v & 0x80:
            cells[i] = min(125, max(0, v + rnd.choice((-1, 0, 1))))
    return Fine(f'rough-s{seed}-L{level}', cells, base.woods, base.start, base.goal,
                False, 'mkmap terrain with uniform +-1 noise (adversarial)')


def noise(seed):
    """Incompressible worst case: uniform levels, 10 % water, 50 % woods."""
    rnd = random.Random(seed)
    cells = bytes(rnd.randrange(126) | (0x80 if rnd.random() < .1 else 0)
                  for _ in range(W * H))
    woods = bytes(rnd.randrange(256) for _ in range(WROW * H))
    return Fine(f'noise-{seed}', cells, woods, (20, 20), (200, 150), False,
                'uniform random levels/water/woods (upper bound)')


def parity_reference(fine):
    """Compare with ../wilderness/build/parity-stage15/map.bin when present."""
    path = HERE.parent / 'wilderness/build/parity-stage15/map.bin'
    if not path.exists():
        return None
    return path.read_bytes()[-FINE_BYTES:] == fine.raw()


# --------------------------------------------------------------------- blocks

SHAPES = OrderedDict([
    ('band7', (W, 7)),      # lot 4: 24 banks of 7 rows (NEOWILD.GEO, retired)
    ('band4', (W, 4)),
    ('band8', (W, 8)),
    ('band14', (W, 14)),
    ('band21', (W, 21)),
    ('tile16', (16, 16)),
    ('tile32', (32, 32)),
    ('tile32x24', (32, 24)),
    ('tile56x42', (56, 42)),
])


class Block:
    __slots__ = ('x0', 'y0', 'w', 'h', 'cells', 'woods')

    def __init__(self, x0, y0, w, h, cells, woods):
        self.x0, self.y0, self.w, self.h, self.cells, self.woods = x0, y0, w, h, cells, woods

    def raw(self):
        """Decoded layout: w*h cell bytes row-major, then w/8 woods bytes per row."""
        return self.cells + self.woods


def blocks(fine, shape):
    bw, bh = SHAPES[shape] if isinstance(shape, str) else shape
    assert bw % 8 == 0, 'woods bytes stay aligned'
    out = []
    for y0 in range(0, H, bh):
        for x0 in range(0, W, bw):
            w, h = min(bw, W - x0), min(bh, H - y0)
            cells = b''.join(fine.cells[y * W + x0:y * W + x0 + w] for y in range(y0, y0 + h))
            woods = b''.join(fine.woods[y * WROW + x0 // 8:y * WROW + (x0 + w) // 8]
                             for y in range(y0, y0 + h))
            out.append(Block(x0, y0, w, h, cells, woods))
    return out


def block_index(shape, x, y):
    bw, bh = SHAPES[shape]
    return (y // bh) * -(-W // bw) + x // bw


def block_count(shape):
    bw, bh = SHAPES[shape]
    return -(-W // bw) * -(-H // bh)


# ------------------------------------------------------------- codec: LZ (now)
# tools/pack_boot.py tokens: 8 flags (LSB first), literal byte, or 12-bit
# distance + 4-bit length-3 (15 -> extension byte, length-18).

def lz_tokens(packed, length):
    """(groups, literals, matches, match bytes, extensions) of an LZ stream."""
    groups = lits = matches = mbytes = ext = 0
    pos = out = 0
    while out < length:
        flags = packed[pos]
        pos += 1
        groups += 1
        for bit in range(8):
            if flags >> bit & 1:
                count = (packed[pos + 1] & 15) + 3
                pos += 2
                if count == 18:
                    count += packed[pos]
                    pos += 1
                    ext += 1
                matches += 1
                mbytes += count
                out += count
            else:
                lits += 1
                pos += 1
                out += 1
            if out >= length:
                break
    return groups, lits, matches, mbytes, ext


# Cycle counts of src/boot.s ld_decode (6502, no page crossings):
#   group: end test 9 + flag fetch/advance 21 + final dec/beq 3   = 33
#   literal: lsr/bcs 7, lda/inc/bne 13, sta/inc/bne 14, end test 8,
#            dec bits/bne 8                                       = 50
#   match: parse 99 (two bytes, distance subtraction, length) + 18 per
#          copied byte (lda/sta (zp),y, iny, dex, bne) + tail 31   = 130 + 18 n
#   extension byte: +14
LZ_CYCLES = dict(group=33, literal=50, match=130, match_byte=18, extension=14, fixed=60)


def lz_cycles(packed, length):
    g, lit, m, mb, ext = lz_tokens(packed, length)
    c = LZ_CYCLES
    return (c['fixed'] + g * c['group'] + lit * c['literal'] + m * c['match']
            + mb * c['match_byte'] + ext * c['extension'])


def lz_encode(raw):
    return lz_compress(raw)


def lz_decode(packed, length):
    return lz_decompress(packed, length)


# ------------------------------------------------- codec: retired overlay LZ
# Format of the removed tools/pack_overlay.py / src/overlay_codec.s:
# 'W\0' magic... stored as MAGIC + length + packed length + reversed LZ of the
# reversed tail + raw 128-byte prefix, decoded in place backward. Raw when not
# smaller or not safe in place. The DOS rule "save two sectors" is reported
# separately (it only mattered to DOS 3.3 sector reads).

OV_MAGIC, OV_PREFIX, OV_HEADER = b'\x00W', 128, 6


def ov_safe(packed, length):
    source, dest, pos = OV_HEADER + len(packed), length, 0
    while dest > OV_PREFIX:
        flags = packed[pos]
        pos += 1
        source -= 1
        for bit in range(8):
            if flags & (1 << bit):
                count = (packed[pos + 1] & 15) + 3
                pos += 2
                source -= 2
                if count == 18:
                    count += packed[pos]
                    pos += 1
                    source -= 1
                dest -= count
            else:
                pos += 1
                source -= 1
                dest -= 1
            if dest < source:
                return False
            if dest == OV_PREFIX:
                return pos == len(packed)
    return False


def ov_encode(raw, dos_rule=False):
    import struct
    if len(raw) <= OV_PREFIX or raw.startswith(OV_MAGIC):
        return bytes(raw)
    enc = lz_compress(raw[OV_PREFIX:][::-1])
    if OV_HEADER + len(enc) + OV_PREFIX >= len(raw) or not ov_safe(enc, len(raw)):
        return bytes(raw)
    out = OV_MAGIC + struct.pack('<HH', len(raw), len(enc)) + enc[::-1] + raw[:OV_PREFIX]
    if dos_rule and (len(raw) + 259) // 256 - (len(out) + 259) // 256 < 2:
        return bytes(raw)
    return out


def ov_decode(data, length):
    import struct
    if not data.startswith(OV_MAGIC):
        return bytes(data)
    n, p = struct.unpack_from('<HH', data, 2)
    assert n == length and len(data) == OV_HEADER + p + OV_PREFIX
    return data[-OV_PREFIX:] + lz_decompress(data[OV_HEADER:OV_HEADER + p][::-1], n - OV_PREFIX)[::-1]


# Cycle counts of the removed src/overlay_codec.s: every source byte goes
# through jsr unpack_get (30 cycles with the rts); per literal 93, per match
# 230 + 18 per byte, plus the 128-byte prefix saved and restored (~4 100)
# and the 256-byte zero-page restore (~3 100, DOS specific, kept: it is the
# decoder as written).
OV_CYCLES = dict(group=40, literal=93, match=230, match_byte=18, extension=35, fixed=7200)


def ov_cycles(data, length):
    if not data.startswith(OV_MAGIC):
        return 17 * length          # raw: a copy (mem_fetch, 17.2 c/B measured)
    import struct
    n, p = struct.unpack_from('<HH', data, 2)
    g, lit, m, mb, ext = lz_tokens(data[OV_HEADER:OV_HEADER + p][::-1], n - OV_PREFIX)
    c = OV_CYCLES
    return (c['fixed'] + g * c['group'] + lit * c['literal'] + m * c['match']
            + mb * c['match_byte'] + ext * c['extension'])


# ------------------------------------------------------------- codec: RLE
# Control c < $80: c+1 literal bytes follow; c >= $80: next byte repeated
# c-$80+3 times (3..130).

def rle_encode(raw):
    out, lit, i, n = bytearray(), bytearray(), 0, len(raw)

    def flush():
        while lit:
            chunk = lit[:128]
            out.append(len(chunk) - 1)
            out.extend(chunk)
            del lit[:128]
    while i < n:
        j = i
        while j < n and raw[j] == raw[i] and j - i < 130:
            j += 1
        if j - i >= 3:
            flush()
            out += bytes((0x80 + j - i - 3, raw[i]))
            i = j
        else:
            lit.append(raw[i])
            i += 1
    flush()
    return bytes(out)


def rle_decode(data, length):
    out, pos = bytearray(), 0
    while len(out) < length:
        c = data[pos]
        if c < 0x80:
            out += data[pos + 1:pos + 2 + c]
            pos += 2 + c
        else:
            out += bytes((data[pos + 1],)) * (c - 0x80 + 3)
            pos += 2
    assert len(out) == length and pos == len(data)
    return bytes(out)


# token: lda (src),y / bmi / tax / advance source (~45 with pointer updates);
# literal byte: lda (src),y 5, sta (dst),y 6, iny 2, dex 2, bne 3 = 18;
# run byte: sta (dst),y, iny, dex, bne = 13.
RLE_CYCLES = dict(token=45, literal=18, run=13, fixed=40)


def rle_cycles(data, length):
    pos, cyc = 0, RLE_CYCLES['fixed']
    while pos < len(data):
        c = data[pos]
        cyc += RLE_CYCLES['token']
        if c < 0x80:
            cyc += (c + 1) * RLE_CYCLES['literal']
            pos += 2 + c
        else:
            cyc += (c - 0x80 + 3) * RLE_CYCLES['run']
            pos += 2
    return cyc




# -------------------------------------------- codecs: packed elevation deltas
# One MSB-first bit stream per block, three sections:
#   1. water plane: bit "any water"; then alternating dry/wet run lengths in
#      row-major order until the block is covered; with the lake bit (Sierra),
#      one bit after each wet run (1 = lake). A zero-length dry run separates
#      a river run from a touching lake run.
#   2. woods plane: bit "any woods"; then alternating bare/wooded runs.
#   3. levels: one residual per coded cell against a predictor.
# Run length R(n): 4 bits if n < 15, else 1111 then n-15 as bytes
# (byte 255 = add 255 and continue).
# Residual codes:
#   'nib' (fixed 2-bit/4-bit): 00 = 0, 01 = +1, 10 = -1, 11 + nibble k:
#          r = k-8; k = 8 escapes to a 7-bit absolute level.
#   'vlc' (1/2/3-bit): one bit per block picks the sign s of the frequent unit
#          step; 0 = 0, 10 = s, 110 = -s, 111 + nibble as above.
# Predictors:
#   'grad':   left + up - upleft inside the block (row 0: left, column 0: up,
#             first cell: escape). Blocks stay independent.
#   'coarse': rounded bilinear interpolation of the resident 112 x 84 grid
#             at $7040; even/even cells of a dry coarse cell equal it exactly
#             and are not coded at all.
DELTA_CODECS = OrderedDict([('nib', ('nib', 'grad')), ('vlc', ('vlc', 'grad')),
                            ('coarse', ('vlc', 'coarse'))])


class BitWriter:
    def __init__(self):
        self.bits = []

    def put(self, value, n):
        for i in range(n - 1, -1, -1):
            self.bits.append(value >> i & 1)

    def run(self, n):
        if n < 15:
            self.put(n, 4)
            return
        self.put(15, 4)
        n -= 15
        while n >= 255:
            self.put(255, 8)
            n -= 255
        self.put(n, 8)

    def data(self):
        b = self.bits + [0] * (-len(self.bits) % 8)
        return bytes(sum(bit << (7 - k) for k, bit in enumerate(b[i:i + 8]))
                     for i in range(0, len(b), 8))


class BitReader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def get(self, n):
        v = 0
        for _ in range(n):
            v = v << 1 | (self.data[self.pos >> 3] >> (7 - (self.pos & 7)) & 1)
            self.pos += 1
        return v

    def run(self):
        n = self.get(4)
        if n < 15:
            return n
        while True:
            b = self.get(8)
            n += b
            if b < 255:
                return n


def _segments(seq):
    out = []
    for v in seq:
        if out and out[-1][0] == v:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return out


def _block_woods(block):
    per = block.w // 8
    return [block.woods[(i // block.w) * per + (i % block.w) // 8] >> (i % block.w % 8) & 1
            for i in range(block.w * block.h)]


def _coarse_value(coarse, i, j):
    return coarse[min(j, mkmap.GH - 1) * mkmap.GW + min(i, mkmap.GW - 1)] & 0x7F


def coarse_pred(coarse, x, y):
    """Rounded bilinear interpolation of the 112 x 84 grid at fine (x, y)."""
    i, j, ox, oy = x >> 1, y >> 1, x & 1, y & 1
    s = (_coarse_value(coarse, i, j) + ox * _coarse_value(coarse, i + 1, j)
         + oy * _coarse_value(coarse, i, j + 1) + ox * oy * _coarse_value(coarse, i + 1, j + 1))
    n = (1 + ox) * (1 + oy)
    return (s + n // 2) // n


def coarse_skip(coarse, x, y):
    return not (x | y) & 1 and not coarse[(y >> 1) * mkmap.GW + (x >> 1)] & 0x80


def delta_encode(block, lakebit, code='vlc', predictor='grad', coarse=None, stats=None):
    bw = BitWriter()
    kinds = [(v & (0xC0 if lakebit else 0x80)) if v & 0x80 else 0 for v in block.cells]
    runs = 0
    bw.put(any(kinds), 1)
    if any(kinds):
        wet = False
        for kind, n in _segments(kinds):
            if bool(kind) != wet:          # kind dry while a wet run is due: impossible
                assert kind, 'segments alternate'
                bw.run(0)                  # wet after wet: empty dry run
                runs += 1
                wet = True
            bw.run(n)
            runs += 1
            if wet and lakebit:
                bw.put(kind == 0xC0, 1)
            wet = not wet
    woods = _block_woods(block)
    bw.put(any(woods), 1)
    if any(woods):
        if woods[0]:
            bw.run(0)                      # runs start bare
            runs += 1
        for _, n in _segments(woods):
            bw.run(n)
            runs += 1
    mask = 0x3F if lakebit else 0x7F
    lv = [v & mask if v & 0x80 else v for v in block.cells]
    w = block.w
    residuals = []
    for i, v in enumerate(lv):
        x, y = i % w, i // w
        if predictor == 'coarse':
            gx, gy = block.x0 + x, block.y0 + y
            if coarse_skip(coarse, gx, gy):
                continue
            p = coarse_pred(coarse, gx, gy)
        elif x and y:
            p = lv[i - 1] + lv[i - w] - lv[i - w - 1]
        elif x:
            p = lv[i - 1]
        elif y:
            p = lv[i - w]
        else:
            p = None
        residuals.append((v, None if p is None else v - p))
    unit = 1
    if code == 'vlc':
        c = Counter(r for _, r in residuals)
        unit = -1 if c[-1] > c[1] else 1
        bw.put(unit < 0, 1)
    escapes = 0
    for v, r in residuals:
        if code == 'nib':
            sym = {0: (0, 2), 1: (1, 2), -1: (2, 2)}.get(r)
            if sym:
                bw.put(*sym)
                continue
            bw.put(3, 2)
        else:
            sym = {0: (0, 1), unit: (2, 2), -unit: (6, 3)}.get(r)
            if sym:
                bw.put(*sym)
                continue
            bw.put(7, 3)
        escapes += 1
        if r is not None and -8 <= r <= 7:
            bw.put(r + 8, 4)
        else:
            bw.put(8, 4)
            bw.put(v, 7)
    if stats is not None:
        stats.update(cells=len(lv), coded=len(residuals), bits=len(bw.bits),
                     escapes=escapes, runs=runs, wet=any(kinds), wooded=any(woods))
    return bw.data()


def delta_decode(data, geometry, lakebit, code='vlc', predictor='grad', coarse=None):
    """geometry = (x0, y0, w, h) -> decoded block bytes (cells, then woods)."""
    x0, y0, w, h = geometry
    n = w * h
    br = BitReader(data)
    kinds = [0] * n
    if br.get(1):
        pos, wet = 0, False
        while pos < n:
            r = br.run()
            kind = 0
            if wet:
                kind = 0xC0 if (lakebit and br.get(1)) else 0x80
            kinds[pos:pos + r] = [kind] * r
            pos += r
            wet = not wet
        assert pos == n
    woods = [0] * n
    if br.get(1):
        pos, on = 0, 0
        while pos < n:
            r = br.run()
            woods[pos:pos + r] = [on] * r
            pos += r
            on ^= 1
        assert pos == n
    unit = 1
    if code == 'vlc':
        unit = -1 if br.get(1) else 1
    lv = [0] * n
    for i in range(n):
        x, y = i % w, i // w
        if predictor == 'coarse':
            gx, gy = x0 + x, y0 + y
            if coarse_skip(coarse, gx, gy):
                lv[i] = coarse[(gy >> 1) * mkmap.GW + (gx >> 1)] & 0x7F
                continue
            p = coarse_pred(coarse, gx, gy)
        elif x and y:
            p = lv[i - 1] + lv[i - w] - lv[i - w - 1]
        elif x:
            p = lv[i - 1]
        elif y:
            p = lv[i - w]
        else:
            p = None
        if code == 'nib':
            s = br.get(2)
            r = {0: 0, 1: 1, 2: -1}.get(s)
        elif not br.get(1):
            r = 0
        elif not br.get(1):
            r = unit
        elif not br.get(1):
            r = -unit
        else:
            r = None
        if r is None:
            k = br.get(4)
            if k == 8:
                lv[i] = br.get(7)
                continue
            r = k - 8
        lv[i] = p + r
    cells = bytes(v | kinds[i] for i, v in enumerate(lv))
    out = bytearray(n // 8)
    for i, b in enumerate(woods):
        if b:
            out[(i // w) * (w // 8) + (i % w) // 8] |= 1 << (i % w % 8)
    return cells + bytes(out)


# Decoder cycle model (6502, estimated from the loop below, not measured):
#   bit fetch: asl bitbuf 5 + bne 3, refill every 8 bits ~25 (+3/bit),
#   prefix branch 3                                            -> 14 per bit
#   grad cell: lda left 3, clc, adc up,x 4, sec, sbc ul,x 4 (15); apply
#   residual 6; sta (out),y 6, keep ul/up row buffer 10; iny/inx/cpx/bne 9
#                                                              -> 46 + bits
#   coarse cell: 2 or 4 coarse fetches (lda (cp),y 5) + add/lsr rounding
#   (~32) instead of 15                                         -> 63 + bits
#   skipped even/even cell: copy the coarse level 20
#   escape: nibble/absolute dispatch +20
#   water plane present: dec run/bne 8 + ora kind 6 per cell  -> 14
#   woods present: dec run/bne 8, rol 5, store every 8 cells  -> 16
#   absent planes: bulk clear of the woods bytes, 8 per byte
#   per run decoded: 4..12 bits + 30
DELTA_CYCLES = dict(bit=14, grad=46, coarse=63, skip=20, escape=20, water=14,
                    woods=16, woods_clear=8, run=30, fixed=150)


def delta_cycles(stats, predictor, w):
    c = DELTA_CYCLES
    cyc = c['fixed'] + stats['bits'] * c['bit'] + stats['escapes'] * c['escape']
    cyc += stats['coded'] * c[predictor] + (stats['cells'] - stats['coded']) * c['skip']
    cyc += stats['runs'] * c['run']
    cyc += stats['cells'] * c['water'] if stats['wet'] else 0
    cyc += stats['cells'] * c['woods'] if stats['wooded'] else stats['cells'] // 8 * c['woods_clear']
    return cyc


# Decoder code size estimates (bytes of 6502), for the memory budget.
DECODER_BYTES = dict(lz=140, overlay=260, rle=50, nib=260, vlc=280, coarse=360)


# ------------------------------------------------------- resident atlas (lot 5)
# The game's format (src/geoaux.s): tile16 blocks, codec 'coarse' with the
# lake bit, predicted from the map's own resident 112 x 84 grid. Layout at
# `base` (the geo_atlas label in the auxiliary language card, bank 1 view):
# 154 low then 154 high bytes of absolute stream addresses, 20 bytes of raw
# flags (bit = tile mod 8, least significant first), then the streams. A tile
# whose stream is not shorter than its decoded bytes is stored decoded.

ATLAS_SHAPE = 'tile16'
ATLAS_END = 0xFFFA                 # auxiliary $FFFA-$FFFF: interrupt vectors


def atlas_bytes(cells, woods, grid, base, stats=None):
    """Fine geography (map format: level, bit 7 water, bit 6 lake; woodland
    bitmap of 28 bytes per row) -> the resident atlas located at `base`.

    `grid` is the map's resident 112 x 84 grid, the predictor. The decoder
    takes the even/even cells of a dry coarse cell from it without coding,
    so every tile is decoded back here and must match exactly.
    """
    cells, woods, grid = bytes(cells), bytes(woods), bytes(grid)
    assert len(cells) == W * H and len(woods) == WROW * H
    assert len(grid) == mkmap.GW * mkmap.GH
    tiles = blocks(Fine('atlas', cells, woods, None, None, True), ATLAS_SHAPE)
    count = len(tiles)
    header = index_bytes(count)
    streams, raw = bytearray(), bytearray(-(-count // 8))
    lo, hi = bytearray(), bytearray()
    sizes = []
    for k, b in enumerate(tiles):
        p = delta_encode(b, True, 'vlc', 'coarse', grid)
        if delta_decode(p, (b.x0, b.y0, b.w, b.h), True, 'vlc', 'coarse', grid) != b.raw():
            raise ValueError(f'fine geography tile {k} at ({b.x0}, {b.y0}) does not round-trip: '
                             'the resident grid must be mkmap.coarse_grid of the fine cells '
                             'and water levels must fit 6 bits (bit 6 = lake)')
        if len(p) >= len(b.raw()):
            p = b.raw()
            raw[k // 8] |= 1 << (k % 8)
        address = base + header + len(streams)
        lo.append(address & 0xFF)
        hi.append(address >> 8 & 0xFF)   # past $FFFF only in a refused atlas
        streams += p
        sizes.append(len(p))
    out = bytes(lo + hi + raw + streams)
    if stats is not None:
        stats.update(tiles=count, index=header, size=len(out), worst=max(sizes),
                     raw_tiles=bin(int.from_bytes(raw, 'little')).count('1'))
    return out


def atlas_decode(atlas, base, grid):
    """Inverse of atlas_bytes (model of src/geoaux.s) -> (cells, woods)."""
    geometry = [(b.x0, b.y0, b.w, b.h) for b in
                blocks(Fine('shape', bytes(W * H), bytes(WROW * H), None, None, True), ATLAS_SHAPE)]
    count = len(geometry)
    cells, woods = bytearray(W * H), bytearray(WROW * H)
    for k, (x0, y0, w, h) in enumerate(geometry):
        start = (atlas[k] | atlas[count + k] << 8) - base
        end = ((atlas[k + 1] | atlas[count + k + 1] << 8) - base) if k + 1 < count else len(atlas)
        data = atlas[start:end]
        if atlas[2 * count + k // 8] >> (k % 8) & 1:
            tile = bytes(data)
        else:
            tile = delta_decode(data, (x0, y0, w, h), True, 'vlc', 'coarse', grid)
        for y in range(h):
            cells[(y0 + y) * W + x0:(y0 + y) * W + x0 + w] = tile[y * w:(y + 1) * w]
            row = w * h + y * (w // 8)
            woods[(y0 + y) * WROW + x0 // 8:(y0 + y) * WROW + (x0 + w) // 8] = tile[row:row + w // 8]
    return bytes(cells), bytes(woods)


# ------------------------------------------------------------------ measuring

CODECS = ('lz', 'overlay', 'rle', 'nib', 'vlc', 'coarse')


def encode_block(codec, block, lakebit, coarse=None):
    """-> (stored bytes, decoder cycles)."""
    raw = block.raw()
    n = len(raw)
    if codec == 'lz':
        p = lz_encode(raw)
        return p, lz_cycles(p, n)
    if codec == 'overlay':
        p = ov_encode(raw)
        return p, ov_cycles(p, n)
    if codec == 'rle':
        p = rle_encode(raw)
        return p, rle_cycles(p, n)
    code, predictor = DELTA_CODECS[codec]
    st = {}
    p = delta_encode(block, lakebit, code, predictor, coarse, st)
    return p, delta_cycles(st, predictor, block.w)


def decode_block(codec, data, block, lakebit, coarse=None):
    n = len(block.raw())
    if codec == 'lz':
        return lz_decode(data, n)
    if codec == 'overlay':
        return ov_decode(data, n)
    if codec == 'rle':
        return rle_decode(data, n)
    code, predictor = DELTA_CODECS[codec]
    return delta_decode(data, (block.x0, block.y0, block.w, block.h), lakebit,
                        code, predictor, coarse)


# A block whose encoding is not smaller is stored raw: one flag bit per block
# beside the 2-byte offsets; a raw block costs a copy (mem_fetch, 17.2 c/B).
COPY_CYCLES = 17


def index_bytes(count):
    return 2 * count + -(-count // 8)


def measure(fine, shape, codec, verify=True):
    coarse = fine.coarse() if codec == 'coarse' else None
    sizes, cycles = [], []
    raw_sizes = []
    stored_raw = 0
    for b in blocks(fine, shape):
        raw = b.raw()
        p, cyc = encode_block(codec, b, fine.lakebit, coarse)
        if verify:
            assert decode_block(codec, p, b, fine.lakebit, coarse) == raw, (fine.name, shape, codec)
        if len(p) >= len(raw):
            p, cyc = raw, COPY_CYCLES * len(raw)
            stored_raw += 1
        sizes.append(len(p))
        cycles.append(cyc)
        raw_sizes.append(len(raw))
    worst = max(range(len(sizes)), key=lambda i: cycles[i])
    return dict(map=fine.name, shape=shape, codec=codec, blocks=len(sizes),
                raw=sum(raw_sizes), block_raw=max(raw_sizes), stored_raw=stored_raw,
                total=sum(sizes), index=index_bytes(len(sizes)), worst=max(sizes),
                cycles_total=sum(cycles), cycles_worst=cycles[worst],
                cycles_per_byte=round(sum(cycles) / sum(raw_sizes), 1),
                ms_worst=round(cycles[worst] * 1000 / CLOCK, 1))


def overlay_dos(fine, shape='band7'):
    """Old overlay codec with its DOS two-sector rule (as shipped)."""
    return sum(len(ov_encode(b.raw(), dos_rule=True)) for b in blocks(fine, shape))


# ------------------------------------------------------------------ locality

def neighbourhood(x, y):
    """fauna_environment's 3 x 3 (clipped like src/fauna.s)."""
    return [(i, j) for j in range(max(0, y - 1), min(H, y + 2))
            for i in range(max(0, x - 1), min(W, x + 2))]


def line(a, b):
    """Half-cell raster from a to b: one fine unit on the major axis per step."""
    (x0, y0), (x1, y1) = a, b
    n = max(abs(x1 - x0), abs(y1 - y0))
    return [(x0 + round((x1 - x0) * k / n), y0 + round((y1 - y0) * k / n))
            for k in range(n + 1)] if n else [a]


def heading_route(start, degrees, steps):
    """Steps along a compass heading (0 = north = +y, 90 = east)."""
    dx, dy = math.sin(math.radians(degrees)), math.cos(math.radians(degrees))
    pts = [start]
    for k in range(1, steps + 1):
        x = min(W - 3, max(2, round(start[0] + dx * k / max(abs(dx), abs(dy)))))
        y = min(H - 3, max(2, round(start[1] + dy * k / max(abs(dx), abs(dy)))))
        pts.append((x, y))
    return pts


def meander(start, goal, seed):
    """Deterministic wandering walk toward the goal (legs of 5..20 steps)."""
    rnd = random.Random(seed)
    pts = [start]
    while math.dist(pts[-1], goal) > 3 and len(pts) < 4000:
        x, y = pts[-1]
        ang = math.atan2(goal[0] - x, goal[1] - y) + rnd.uniform(-1, 1)
        leg = rnd.randint(5, 20)
        end = (min(W - 3, max(2, round(x + leg * math.sin(ang)))),
               min(H - 3, max(2, round(y + leg * math.cos(ang)))))
        pts += line(pts[-1], end)[1:]
    return pts + line(pts[-1], goal)[1:]


def routes(fine):
    s, g = fine.start, fine.goal
    out = OrderedDict()
    out['direct'] = line(s, g)
    out['detour'] = line(s, (g[0], s[1])) + line((g[0], s[1]), g)[1:]
    out['meander'] = meander(s, g, 1985)
    # tests/scenario.py: WALK 1 H, SWIM 1 H, WALK 30 MIN from the crash at the
    # original's first heading of 128 degrees (~6 + 6 + 3 half-steps).
    out['scenario'] = heading_route(s, 128, 15)
    # tests/test_walk.py: legacy fixture at coarse (10, 40), WALK 4 H east:
    # 25 half-steps from fine (20, 80).
    out['walk-fixture'] = heading_route((20, 80), 90, 25)
    # tests/test_shore.py: WALK -> SWIM -> SWIM -> WALK across a two-cell lake,
    # headings 140/420/0/280/70 units = E, W, N, S, NE; ~28 half-steps each.
    for deg in (90, 270, 0, 180, 45):
        out[f'shore-fixture-{deg}'] = heading_route((20, 80), deg, 28)
    return out


def step_blocks(shape, here, nxt):
    """Blocks one step touches: the 3x3 around here (fauna), here, next."""
    return [block_index(shape, *p) for p in neighbourhood(*here)] + [block_index(shape, *nxt)]


def simulate(shape, path, capacity):
    """LRU cache of decoded blocks along a path -> (decodes, changes, per-step)."""
    cache, decodes, changes, last = OrderedDict(), 0, 0, None
    per_step = []
    for here, nxt in zip(path, path[1:]):
        touched = step_blocks(shape, here, nxt)
        per_step.append(len(set(touched)))
        for b in touched:
            if b != last:
                changes += 1
                last = b
            if b in cache:
                cache.move_to_end(b)
            else:
                decodes += 1
                cache[b] = True
                if len(cache) > capacity:
                    cache.popitem(last=False)
    return decodes, changes, per_step


def shore_cells(fine):
    """Dry cells with water in their 3x3 (where FILL/SWIM probes happen)."""
    return [(x, y) for y in range(1, H - 1) for x in range(1, W - 1)
            if not fine.water(x, y) and any(fine.water(i, j) for i, j in neighbourhood(x, y))]


def locality(fine, shape, capacities=(1, 2, 3, 4, 6)):
    res = OrderedDict(map=fine.name, shape=shape)
    for name, path in routes(fine).items():
        entry = dict(steps=len(path) - 1)
        for cap in capacities:
            d, ch, per = simulate(shape, path, cap)
            entry[f'decodes_{cap}'] = d
        entry['block_changes_1'] = simulate(shape, path, 1)[1]
        entry['distinct'] = len({block_index(shape, *p) for p in path})
        entry['max_per_step'] = max(per) if per else 0
        entry['mean_per_step'] = round(sum(per) / len(per), 3) if per else 0
        entry['multi_step_pct'] = round(100 * sum(k > 1 for k in per) / len(per), 1) if per else 0
        res[name] = entry
    shores = shore_cells(fine)
    touched = Counter(len({block_index(shape, *p) for p in neighbourhood(x, y)}) for x, y in shores)
    res['shore'] = dict(cells=len(shores), touched=dict(sorted(touched.items())),
                        max=max(touched) if touched else 0)
    return res


# ------------------------------------------------------------------ driver

def maps(quick=False, build=HERE / 'build'):
    out, missing = [], []
    have_samples = (build / 're_geography/heights.bin').exists() and (build / 'files/TOPO.B').exists()
    if have_samples:
        out.append(sierra(build))
    else:
        missing.append('build/re_geography/*.bin (tools/re_geography_probe.py)')
    if (build / 'files/TOPO.B').exists():
        if not quick:
            out.append(sierra_topo(build))
    else:
        missing.append('build/files/TOPO.B (make extract)')
    seeds = ((1985, 4),) if quick else tuple((s, l) for s in (1985, 7, 42) for l in (1, 4, 10))
    out += [generated(s, l) for s, l in seeds]
    if not quick:
        out += [generated(9999, 10, extra_rivers=120), rough(1985, 4), noise(1)]
    return out, missing


def _job(args):
    fine, shape, codec = args
    return measure(fine, shape, codec)


def run(quick=False, jobs=None, out=HERE / 'build/geo'):
    fines, missing = maps(quick)
    shapes = ('band7', 'tile32x24') if quick else tuple(SHAPES)
    work = [(f, s, c) for f in fines for s in shapes for c in CODECS
            if not (quick and c == 'overlay')]
    if jobs == 1:
        results = [_job(w) for w in work]
    else:
        from multiprocessing import Pool
        with Pool(jobs) as pool:
            results = pool.map(_job, work, chunksize=1)
    loc = [locality(f, s) for f in fines for s in shapes]
    extra = OrderedDict()
    for f in fines:
        extra[f.name] = dict(
            note=f.note, start=f.start, goal=f.goal,
            water=sum(f.water(x, y) for y in range(H) for x in range(W)),
            woods=sum(bin(b).count('1') for b in f.woods),
            overlay_dos_band7=None if quick else overlay_dos(f),
            parity_stage15=parity_reference(f) if f.name == 'sierra' else None)
    report = dict(fine_bytes=FINE_BYTES, missing=missing, maps=extra,
                  shapes={k: v for k, v in SHAPES.items() if k in shapes},
                  cycles=dict(lz=LZ_CYCLES, overlay=OV_CYCLES, rle=RLE_CYCLES, delta=DELTA_CYCLES),
                  decoder_bytes=DECODER_BYTES, results=results, locality=loc)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / ('report-quick.json' if quick else 'report.json')).write_text(json.dumps(report, indent=1) + '\n')
    (out / ('report-quick.md' if quick else 'report.md')).write_text(markdown(report))
    return report


def markdown(rep):
    lines = ['# geo_atlas measurements', '']
    if rep['missing']:
        lines += ['Missing inputs: ' + ', '.join(rep['missing']), '']
    lines += ['| map | water cells | wooded cells | crash | rangers | old overlay+DOS rule (band7) |',
              '|---|---:|---:|---|---|---:|']
    for name, m in rep['maps'].items():
        lines.append(f"| {name} | {m['water']} | {m['woods']} | {tuple(m['start'])} | "
                     f"{tuple(m['goal'])} | {m['overlay_dos_band7']} |")
    lines += ['', '| map | shape | codec | blocks | total | +index | worst block | c/B | worst ms |',
              '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for r in rep['results']:
        lines.append(f"| {r['map']} | {r['shape']} | {r['codec']} | {r['blocks']} | {r['total']} | "
                     f"{r['total'] + r['index']} | {r['worst']} | {r['cycles_per_byte']} | {r['ms_worst']} |")
    lines += ['', '| map | shape | route | steps | distinct | max/step | multi % | decodes N=1/2/3/4/6 |',
              '|---|---|---|---:|---:|---:|---:|---|']
    for l in rep['locality']:
        for name, e in l.items():
            if isinstance(e, dict) and 'steps' in e:
                lines.append(f"| {l['map']} | {l['shape']} | {name} | {e['steps']} | {e['distinct']} | "
                             f"{e['max_per_step']} | {e['multi_step_pct']} | "
                             + '/'.join(str(e[f'decodes_{c}']) for c in (1, 2, 3, 4, 6)) + ' |')
        s = l['shore']
        lines.append(f"| {l['map']} | {l['shape']} | shore cells | {s['cells']} | | {s['max']} | "
                     f"{s['touched']} | |")
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--quick', action='store_true', help='two shapes, one generated map')
    ap.add_argument('--jobs', type=int, default=None)
    ap.add_argument('--out', default=str(HERE / 'build/geo'))
    a = ap.parse_args()
    rep = run(a.quick, a.jobs, a.out)
    best = {}
    for r in rep['results']:
        key = (r['map'], r['codec'])
        if key not in best or r['total'] + r['index'] < best[key]['total'] + best[key]['index']:
            best[key] = r
    for (m, c), r in sorted(best.items()):
        print(f"{m:22} {c:8} best {r['shape']:10} {r['total'] + r['index']:6} B "
              f"worst block {r['worst']:5} B {r['cycles_per_byte']:6} c/B")
    print(f"wrote {a.out}")


if __name__ == '__main__':
    main()
