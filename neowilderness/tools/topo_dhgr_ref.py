#!/usr/bin/env python3
"""topo_dhgr_ref.py: reference DHGR TOPO sheet, generated from the resident map.

Layout (mixed mode: graphics rows 0..159, the 4 text lines carry the legend):
  x   0..111  the journey map, one colour pixel per cell column, north up;
  x 112..139  legend strip: north arrow, hypsometric scale with index labels.
Rows 0..159 sample the 84 cell rows: row sy is at position
  v(sy) = floor((159 - sy) * 83 * 2^QB / 159) / 2^QB   (cells, 0 = south edge)
so row 0 is cell row 83 and row 159 cell row 0 (1.916 rows per cell; a cell is
1 x 1.92 colour pixels, 1.05 times taller than wide on a 4:3 screen).
Rows 160..191 are not written (hidden by the text window).

The elevation of a pixel is the exact linear interpolation between cell rows
j = floor(v) and j + 1 of the same column; its band is floor(e / 4) (400 ft).
Water and woods come from the nearest cell row (round half up). Rules:
  water pixel with a land 4-neighbour          SHORE (lighter rim; whole rivers)
  other water pixel                            WATER
  land pixel separated from a land 4-neighbour INDEX of its band (bold: both
    by an index level (multiple of 2000 ft)      sides of the crossing)
  land pixel whose east or north land          LINE of its band (one pixel, on
    neighbour has another band                   the west/south side of a crossing)
  otherwise                                    tint (dither) or woods texture
(land pixels ignore water neighbours), then the strip and the C/H/R markers.

Two implementations: sheet() states the rules with exact fractions;
Sheet6502 is the integer, row-major, table-driven algorithm for the 6502
(DDA rows, floor averages, causal tests east/north with idempotent
retro-marking, packing delayed by one row). tests/test_topo_dhgr.py checks
they agree bit for bit; Sheet6502 counts the events of the cycle budget.

Usage: topo_dhgr_ref.py MAP.bin OUT_PREFIX      (writes OUT_PREFIX.png 280x192,
       OUT_PREFIX_x2.png 560x320, OUT_PREFIX_screen.png with the legend
       lines, OUT_PREFIX.main/.aux rows 0..159; prints the cycle estimate)
       topo_dhgr_ref.py --gallery [DIR]       (maps + captures in build/topo/)
"""
import argparse, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import dhgr_palette as P  # noqa: E402
import topo_palette as T  # noqa: E402
import topo  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

GW, GH = 112, 84
HEADER = 64
ROWS, COLS, PAGE_ROWS = 160, 140, 192
STRIP_X = 112
QB = 1                          # fraction bits of the vertical position (half cells)
LEGEND = ('TOPO  N UP  CONTOURS 400 FT, BOLD 2000',
          'C CRASH  H CABIN  R RANGERS  SCALE KFT',
          'MAP: PLAYER MAP',
          'ESC/RETURN/SPACE: VIEW')
# Strip geometry.
BAR_X0, BAR_X1 = 115, 120       # scale bar columns (inclusive)
TICK_X = 121
LABEL_X = 123
BAR_BOTTOM = 157                # bottom row of band 0
BAR_ROWS = 4                    # rows per band
ARROW_X = 125
NORTH = [(ARROW_X - 1 + c, 3 + r) for r, bits in enumerate(T.GLYPHS['N'])
         for c in range(3) if bits & (4 >> c)]
ARROW = ([(ARROW_X, 10)] + [(ARROW_X + d, 11) for d in (-1, 0, 1)]
         + [(ARROW_X + d, 12) for d in (-1, 0, 1)] + [(ARROW_X + d, 13) for d in range(-2, 3)]
         + [(ARROW_X, r) for r in range(14, 26)])


# ---------------------------------------------------------------------------
# Geometry shared by both implementations (closed forms).
def vq(sy):
    """Vertical position of row sy in 1/2^QB cells."""
    return ((ROWS - 1 - sy) * (GH - 1) << QB) // (ROWS - 1)


def nearest(sy):
    v = vq(sy)
    return (v + (1 << (QB - 1))) >> QB


def marker_row(y):
    """Top-most sheet row whose nearest cell row is y."""
    return min(sy for sy in range(ROWS) if nearest(sy) == y)


def markers(data):
    """[(letter, cell x, cell y)] in drawing order (crash last, on top)."""
    out = [('R', data[8], data[9])]
    if data[16]:
        out.append(('H', data[17], data[18]))
    out.append(('C', data[3], data[5]))
    return out


def marker_pixels(letter, x, y):
    """{(px, row): colour} of one marker: site pixel + 5 x 7 label box
    touching it diagonally (north-east; west near the east edge; south near
    the north edge). Pixels outside the map area are clipped by the caller."""
    box, ink = T.MARKERS[letter]
    row = marker_row(y)
    bx = x + 1 if x + 5 < GW else x - 5          # box north-east of the site, else west
    by = row - 7 if row >= 7 else row + 1         # else south
    pix = {(x, row): box}
    for r in range(7):
        for c in range(5):
            pix[(bx + c, by + r)] = box
    for r, bits in enumerate(T.GLYPHS[letter]):
        for c in range(3):
            if bits & (4 >> c):
                pix[(bx + 1 + c, by + 1 + r)] = ink
    return pix


def strip_pixels(data):
    """{(x, row): colour} of the legend strip; everything else there is STRIP."""
    base, snow, top, _ = T.header(data)
    pix = {}
    for b in range(top + 1):
        y1 = BAR_BOTTOM - BAR_ROWS * b
        for r in range(y1 - BAR_ROWS + 1, y1 + 1):
            for x in range(BAR_X0, BAR_X1 + 1):
                pix[(x, r)] = T.pick(T.tint(b, snow), (x + r) & 1)
        if b and T.is_index(b, base):
            for x in range(BAR_X0, BAR_X1 + 1):
                pix[(x, y1)] = T.INDEX[T.ramp_index(b, snow)]
                pix[(x, y1 + 1)] = T.INDEX[T.ramp_index(b - 1, snow)]
            pix[(TICK_X, y1)] = T.INK
            label = str((4 * b + base) // 10)
            for i, ch in enumerate(label):
                for r, bits in enumerate(T.GLYPHS[ch]):
                    for c in range(3):
                        if bits & (4 >> c):
                            pix[(LABEL_X + 4 * i + c, y1 - 2 + r)] = T.INK
        elif b:                 # as on the map: the line is on the south side
            for x in range(BAR_X0, BAR_X1 + 1):
                pix[(x, y1 + 1)] = T.LINE[T.ramp_index(b - 1, snow)]
    for p in NORTH + ARROW:
        pix[p] = T.INK
    return pix


def forest(data, x, y):
    if len(data) < HEADER + GW * GH + 294 or not data[26]:
        return False
    return bool(data[HEADER + GW * GH + (y // 2) * 7 + (x // 2) // 8] & (1 << ((x // 2) % 8)))


# ---------------------------------------------------------------------------
# Reference: exact rules.
def samples(data):
    """info[sy][x]: None for water, else (band, woods); exact arithmetic:
    band = floor((h0 + (h1 - h0) * q / 2^QB) / 4), computed as one floor
    division of the scaled product (Sheet6502 uses no multiply)."""
    base, _snow, _top, timber = T.header(data)
    grid = data[HEADER:HEADER + GW * GH]
    info = []
    for sy in range(ROWS):
        d = 1 << QB
        j, q, n = vq(sy) >> QB, vq(sy) & (d - 1), nearest(sy)
        row = []
        for x in range(GW):
            if grid[n * GW + x] & 0x80:
                row.append(None)
                continue
            h0 = grid[j * GW + x] & 0x7F
            h1 = grid[min(j + 1, GH - 1) * GW + x] & 0x7F
            band = (h0 * d + (h1 - h0) * q) // (4 * d)
            row.append((band, forest(data, x, n) and T.wooded(band, base, timber)))
        info.append(row)
    return info


def sheet(data, you=None):
    """192 rows x 140 colours; rows 160..191 black (never written)."""
    if len(data) < HEADER + GW * GH:
        raise ValueError('incomplete journey map')
    base, snow, _top, _timber = T.header(data)
    info = samples(data)
    idx = [T.index_count(b, base) for b in range(32)]
    at = lambda x, y: info[y][x] if 0 <= x < GW and 0 <= y < ROWS else 'out'
    page = [[P.BLACK] * COLS for _ in range(PAGE_ROWS)]
    for sy in range(ROWS):
        for x in range(GW):
            me = at(x, sy)
            around = [at(x - 1, sy), at(x + 1, sy), at(x, sy - 1), at(x, sy + 1)]
            if me is None:
                c = T.SHORE if any(n not in (None, 'out') for n in around) else T.WATER
            else:
                b, woods = me
                i = T.ramp_index(b, snow)
                land = [n for n in around if n not in (None, 'out')]
                east_north = [n for n in (around[1], around[2]) if n not in (None, 'out')]
                if any(idx[n[0]] != idx[b] for n in land):
                    c = T.INDEX[i]
                elif any(n[0] != b for n in east_north):
                    c = T.LINE[i]
                elif woods and T.woods_dot(x, sy):
                    c = T.WOODS
                else:
                    c = T.pick(T.tint(b, snow), (x + sy) & 1)
            page[sy][x] = c
        for x in range(STRIP_X, COLS):
            page[sy][x] = T.STRIP
    for (x, r), c in strip_pixels(data).items():
        page[r][x] = c
    for letter, x, y in markers(data):
        for (px, r), c in marker_pixels(letter, x, y).items():
            if 0 <= px < GW and 0 <= r < ROWS:
                page[r][px] = c
    if you is not None:         # optional: the HGR sheet does not show the player
        x, y = you
        r = marker_row(y)
        for dx, dr in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
            if 0 <= x + dx < GW and 0 <= r + dr < ROWS:
                page[r + dr][x + dx] = P.YELLOW if (dx, dr) == (0, 0) else P.BLACK
    return page


def encode(page, rows=range(PAGE_ROWS)):
    """(main, aux) 8 KB banks, Apple memory order (same as dhgr_ref.encode)."""
    main, aux = bytearray(8192), bytearray(8192)
    for y in rows:
        bits = 0
        for x, c in enumerate(page[y]):
            bits |= P.rot(c) << (4 * x)
        o = hgr_offset(y)
        for i in range(80):
            (aux if i % 2 == 0 else main)[o + i // 2] = (bits >> (7 * i)) & 0x7F
    return bytes(main), bytes(aux)


def decode(main, aux, rows=range(PAGE_ROWS)):
    inv = {P.rot(c): c for c in range(16)}
    out = []
    for y in rows:
        o, bits = hgr_offset(y), 0
        for i in range(80):
            bits |= ((aux if i % 2 == 0 else main)[o + i // 2] & 0x7F) << (7 * i)
        out.append([inv[(bits >> (4 * x)) & 15] for x in range(COLS)])
    return out


# ---------------------------------------------------------------------------
# Integer, row-major algorithm for the 6502 (with event counts).
class Sheet6502:
    """Only byte tables, 8-bit adds/shifts and compares (docs/TOPO_DHGR.md §5).

    prime     row 0 sampled into KP (its north neighbour is itself)
    per row   DDA (no multiply): j, q; pointers r0 = grid row j, r1 = row j+1;
              WROW (woods row, 112 bytes of K_WOODS) when nearest >> 1 changes
    per pixel x = 111 .. 0 (DEY/BPL); the first pixel of a row seeds kr
      sample  q = 0: K = (h0 >> 2) | WROW[x];  q != 0: floor averages, the
              first (h0 + h1) >> 1 (CLC/ADC/ROR), then one per higher bit of q
              with h1 (bit set) or h0; water from the nearest raw byte (BMI)
      fast    K == kr (east) and K == KP[x] (north): C[x] = FILL[row&3][x&1][K]
      slow    per differing pair: water/land -> rim on the water pixel (retro
              CC[x+1] or CP[x]); band differs -> LINE; IDXK differ -> INDEX on
              both (retro INDEXK[nk]); woods only -> nothing
    flush     strip and markers into CP, then 20 groups packed to row sy - 1
    """
    def __init__(self, data):
        self.data = data
        self.t = T.tables(data)
        self.pk = T.pack_tables()
        self.n = {}
        self.main, self.aux = bytearray(8192), bytearray(8192)
        self.grid = data[HEADER:HEADER + GW * GH]

    def count(self, key, k=1):
        self.n[key] = self.n.get(key, 0) + k

    def wrow(self, fy):
        """Expand forest row fy (7 bytes, LSB first) to 112 bytes of K_WOODS."""
        d = self.data
        out = bytearray(GW)
        if len(d) >= HEADER + GW * GH + 294 and d[26]:
            row = d[HEADER + GW * GH + fy * 7:HEADER + GW * GH + fy * 7 + 7]
            for x in range(GW):
                if row[x >> 4] & (1 << ((x >> 1) & 7)):
                    out[x] = T.K_WOODS
        self.count('wrow')
        return out

    def sample_row(self, j, q, steps, nb, wr, x):
        g = self.grid
        rn = g[nb * GW + x]
        if rn & 0x80:
            self.count('sample_water')
            return T.K_WATER
        h0 = g[j * GW + x] & 0x7F
        if not q:
            self.count('sample_cell')
            return (h0 >> 2) | wr[x]
        h1 = g[min(j + 1, GH - 1) * GW + x] & 0x7F
        a = (h0 + h1) >> 1                      # CLC / ADC h1 / ROR (9-bit sum)
        for bit in steps:
            a = (a + (h1 if bit else h0)) >> 1
        self.count(f'sample_mid_s{1 + len(steps)}')
        return (a >> 2) | wr[x]                 # LSR / LSR / ORA WROW,Y

    def run(self):
        t = self.t
        idxk, mark, indexk = t['idxk'], t['mark'], t['indexk']
        num = (GH - 1) << QB                    # 83 * 2^QB
        step, rem = divmod(num, ROWS - 1)
        v, acc = num, ROWS - 2                  # v(sy) = num - step*sy - ceil(rem*sy/159)
        cp, kp = None, None
        fy, wr = None, None
        strip = StripRows(self.data)
        for sy in range(ROWS):
            j, q = v >> QB, v & ((1 << QB) - 1)
            nb = j + (q >> (QB - 1))
            if nb >> 1 != fy:
                fy, wr = nb >> 1, self.wrow(nb >> 1)
            steps = []
            if q:
                low = (q & -q).bit_length() - 1
                steps = [(q >> b) & 1 for b in range(low + 1, QB)]
            self.count('row')
            if kp is None:                      # prime: row 0 is its own north row
                kp = bytearray(self.sample_row(j, q, steps, nb, wr, x) for x in range(GW))
                self.count('prime_px', GW)
            fill = (t[f'fill{sy & 3}0'], t[f'fill{sy & 3}1'])
            kc, cc = bytearray(GW), bytearray(GW)
            kr = None
            for x in range(GW - 1, -1, -1):
                k = self.sample_row(j, q, steps, nb, wr, x)
                kc[x] = k
                if kr is None:
                    kr = k                      # east edge: seeded by the first pixel
                if k == kr and k == kp[x]:
                    cc[x] = fill[x & 1][k]
                    self.count('fast')
                    continue
                self.count('slow_north' if k != kp[x] else 'slow_east')
                f = 0
                for nk, buf, nx in ((kp[x], cp, x), (kr, cc, x + 1)):
                    if nk == k:
                        continue
                    if (k ^ nk) & T.K_WATER:    # exactly one is water
                        self.count('pair_water')
                        if k == T.K_WATER:
                            f |= 4
                        else:
                            buf[nx] = T.SHORE   # retro: the water neighbour is a rim
                        continue
                    if not (k ^ nk) & 31:
                        self.count('pair_woods')
                        continue
                    f |= 1
                    if idxk[k] != idxk[nk]:
                        f |= 2
                        buf[nx] = indexk[nk]    # retro: bold, idempotent
                        self.count('pair_index')
                    else:
                        self.count('pair_band')
                if f & 4:
                    cc[x] = mark[k]             # k == K_WATER: the rim
                elif f & 2:
                    cc[x] = indexk[k]
                elif f & 1:
                    cc[x] = mark[k]
                else:
                    cc[x] = fill[x & 1][k]
                self.count('end_special' if f else 'end_fill')
                kr = k
            if cp is not None:
                self.flush(cp, sy - 1, strip)
            cp, kp = cc, kc
            acc += rem
            v -= step
            if acc >= ROWS - 1:
                acc -= ROWS - 1
                v -= 1
        self.flush(cp, ROWS - 1, strip)
        return self.main, self.aux

    def flush(self, cp, sy, strip):
        row = bytearray(COLS)
        row[:GW] = cp
        self.count('overlay_px', strip.overlay(row, sy))
        self.count('strip_row')
        pk, o = self.pk, hgr_offset(sy)
        for g in range(20):
            c = row[7 * g:7 * g + 7]
            self.aux[o + 2 * g] = pk['T0'][c[0]] | pk['T1a'][c[1]]
            self.main[o + 2 * g] = pk['T1b'][c[1]] | pk['T2'][c[2]] | pk['T3a'][c[3]]
            self.aux[o + 2 * g + 1] = pk['T3b'][c[3]] | pk['T4'][c[4]] | pk['T5a'][c[5]]
            self.main[o + 2 * g + 1] = pk['T5b'][c[5]] | pk['T6'][c[6]]
        self.count('groups', 20)


class StripRows:
    """Row-by-row strip and markers, as the 6502 draws them before packing."""
    def __init__(self, data):
        self.base, self.snow, self.top, _ = T.header(data)
        t = T.tables(data)
        self.mark, self.indexk, self.idxk = t['mark'], t['indexk'], t['idxk']
        self.fill = [(t[f'fill{r}0'], t[f'fill{r}1']) for r in range(4)]
        self.bar_top = BAR_BOTTOM - BAR_ROWS * (self.top + 1) + 1
        self.labels = []                        # (first row, glyph rows of the label)
        for b in range(1, self.top + 1):
            if self.idxk[b] != self.idxk[b - 1]:
                text = str((4 * b + self.base) // 10)
                self.labels.append((BAR_BOTTOM - BAR_ROWS * b - 2, text))
        self.boxes = []                         # (x0, row0, box, ink, glyph, site x, site row)
        for letter, x, y in markers(data):
            box, ink = T.MARKERS[letter]
            row = marker_row(y)
            bx = x + 1 if x + 5 < GW else x - 5
            by = row - 7 if row >= 7 else row + 1
            self.boxes.append((bx, by, box, ink, T.GLYPHS[letter], x, row))
        self.north = T.GLYPHS['N']

    def overlay(self, row, r):
        n = 0
        for x in range(STRIP_X, COLS):
            row[x] = T.STRIP
        if self.bar_top <= r <= BAR_BOTTOM:     # bar: the band of the row, its tint
            d = BAR_BOTTOM - r
            b, sub = d // BAR_ROWS, d % BAR_ROWS
            kb = b                              # K of a bare land pixel of band b
            for x in range(BAR_X0, BAR_X1 + 1):
                c = self.fill[r & 3][x & 1][kb]
                above = b + 1 if sub == BAR_ROWS - 1 and b < self.top else None
                below = b - 1 if sub == 0 and b else None
                if above is not None and self.idxk[above] != self.idxk[b]:
                    c = self.indexk[b]
                elif below is not None and self.idxk[below] != self.idxk[b]:
                    c = self.indexk[b]
                elif above is not None:
                    c = self.mark[b]
                row[x] = c
                n += 1
        for r0, text in self.labels:
            if r0 <= r < r0 + 5:
                if r == r0 + 2:
                    row[TICK_X] = T.INK
                for i, ch in enumerate(text):
                    bits = T.GLYPHS[ch][r - r0]
                    for c in range(3):
                        if bits & (4 >> c):
                            row[LABEL_X + 4 * i + c] = T.INK
                            n += 1
        if 3 <= r < 8:
            bits = self.north[r - 3]
            for c in range(3):
                if bits & (4 >> c):
                    row[ARROW_X - 1 + c] = T.INK
        if 10 <= r <= 25:
            half = {10: 0, 11: 1, 12: 1, 13: 2}.get(r, 0)
            for x in range(ARROW_X - half, ARROW_X + half + 1):
                row[x] = T.INK
                n += 1
        for bx, by, box, ink, glyph, sx, srow in self.boxes:
            if r == srow:
                row[sx] = box
            if by <= r < by + 7:
                bits = glyph[r - by - 1] if 1 <= r - by <= 5 else 0
                for c in range(5):
                    x = bx + c
                    if 0 <= x < GW:
                        row[x] = ink if 1 <= c <= 3 and bits & (4 >> (c - 1)) else box
                        n += 1
        return n


# ---------------------------------------------------------------------------
# Cycle model: cycles per event of the 6502 sketches (docs/TOPO_DHGR.md §5).
def _mid(s):
    return 32 + 7 * (s - 1) + (3 if s < QB else 0)


CYCLES = {
    'sample_cell': 15,          # LDA (r0),Y  BMI  LSR LSR  ORA WROW,Y
    'sample_mid_s1': _mid(1),   # LDA (r1),Y BMI STA h1 LDA (r0),Y AND CLC ADC ROR LSR LSR ORA
    'sample_mid_s2': _mid(2),   # (QB 2, 3 only) one more CLC/ADC/ROR per step
    'sample_mid_s3': _mid(3),
    'sample_water': 13,         # LDA (rn),Y  BMI (taken)  LDA #$40  BNE tail
    'fast': 31,                 # STA KC,Y CMP KP,Y BNE CMP kr BNE TAX LDA FILL,X STA CC,Y DEY (+BPL/2)
    'slow_north': 12 + 8,       # tail to the taken BNE; the east compare done in the slow path
    'slow_east': 17,            # tail to the second taken BNE
    'pair_band': 35,            # EOR, water test, band test, IDXK compare
    'pair_index': 35 + 20,      # + LDA INDEXK,X / STA CP,Y or CC+1,Y (retro), flag
    'pair_woods': 18,
    'pair_water': 30,           # rim flag, or retro STA of the medium blue rim
    'end_fill': 15,             # LDA FILL,X STA CC,Y STX kr JMP loop
    'end_special': 15,          # LDA LINEK|INDEXK|MARK,X ...
    'prime_px': 25,
    'row': 330,                 # DDA, r0/r1, ~30 operand patches (KC/KP/CC/CP/FILL/ROW), kr seed
    'wrow': 112 * 10 + 60,      # 56 bits -> 112 bytes
    'strip_row': 240,           # 28 STA (black), bar band/tint, label/arrow/marker row tests
    'overlay_px': 15,
    'groups': 137,              # looped: 7 LDX + 10 LDA/ORA + 3 temps + 2 PAGE2 + 4 STA abs,X + loop
}
SETUP = 25_000                  # FILL 8x65, K tables 3x64, pack 10x16, marker rows


def estimate(counts):
    return SETUP + sum(CYCLES[k] * v for k, v in counts.items())


def breakdown(counts):
    groups = {
        'sample': [k for k in counts if k.startswith('sample') or k == 'prime_px'],
        'classify fast': ['fast'],
        'classify slow': [k for k in counts if k.startswith(('slow', 'pair', 'end'))],
        'pack': ['groups'],
        'rows/woods/strip': ['row', 'wrow', 'strip_row', 'overlay_px'],
    }
    out = {g: sum(CYCLES[k] * counts.get(k, 0) for k in ks) for g, ks in groups.items()}
    out['setup'] = SETUP
    return out


# ---------------------------------------------------------------------------
def to_png(path, page, rows=range(PAGE_ROWS), sx=2, sy=1):
    rgb = bytearray()
    for y in rows:
        line = bytearray()
        for c in page[y]:
            line += bytes(P.RGB[c]) * sx
        rgb += line * sy
    topo.png(str(path), sx * COLS, sy * len(list(rows)), rgb)


def screen_png(path, page):
    """Whole mixed-mode screen, 560 x 384: the sheet (each colour pixel 4 x 2)
    and the LEGEND lines as the game prints them under DHGR (40-column
    characters in the odd 80-column cells, bbfont from dev/lib/font)."""
    from fonts import glyph
    W = 560
    rgb = bytearray()
    for y in range(ROWS):
        line = bytearray()
        for c in page[y]:
            line += bytes(P.RGB[c]) * 4
        rgb += line * 2
    for text in LEGEND:
        for gy in range(8):
            dots = bytearray(W)
            for i, ch in enumerate(text.ljust(40)[:40]):
                bits = glyph(ch)[gy]
                for b in range(7):
                    if bits & (1 << b):
                        dots[14 * i + 7 + b] = 1
            line = b''.join(b'\xff\xff\xff' if d else b'\0\0\0' for d in dots)
            rgb += line * 2
    topo.png(str(path), W, 2 * (ROWS + 8 * len(LEGEND)), rgb)


def make_map(seed, level, path=None):
    """Generate a journey map in-process with tools/mkmap.py (no subprocess)."""
    import mkmap
    m = mkmap.Map(seed, level)
    head = mkmap.heading_to(*m.start, mkmap.W // 2, mkmap.H // 2)
    data = mkmap.map_bin(m.h, m.water, m.start, m.goal, head, level, woods=m.forest)
    if path:
        Path(path).write_bytes(data)
    return data


GALLERY = ((1985, 4), (7, 1), (2026, 7), (42, 10))


def render_files(data, prefix):
    page = sheet(data)
    main, aux = encode(page, range(ROWS))
    Path(f'{prefix}.main').write_bytes(main)
    Path(f'{prefix}.aux').write_bytes(aux)
    to_png(f'{prefix}.png', page)
    to_png(f'{prefix}_x2.png', page, range(ROWS), 4, 2)
    screen_png(f'{prefix}_screen.png', page)
    s = Sheet6502(data)
    s.run()
    return page, s


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('map', nargs='?', type=Path)
    ap.add_argument('prefix', nargs='?')
    ap.add_argument('--gallery', nargs='?', const=str(HERE / 'build/topo'))
    a = ap.parse_args()
    jobs = []
    if a.gallery:
        out = Path(a.gallery)
        out.mkdir(parents=True, exist_ok=True)
        for seed, level in GALLERY:
            jobs.append((make_map(seed, level, out / f'map_{seed}_{level}.bin'),
                         str(out / f'topo_{seed}_{level}')))
    elif a.map and a.prefix:
        jobs.append((a.map.read_bytes(), a.prefix))
    else:
        ap.error('MAP.bin OUT_PREFIX or --gallery')
    for data, prefix in jobs:
        page, s = render_files(data, prefix)
        same = decode(s.main, s.aux, range(ROWS)) == page[:ROWS]
        cyc = estimate(s.n)
        print(f'{prefix}: {cyc:,} cycles = {cyc / 1_020_484:.2f} s; 6502-style identical: {same}')
        print('   ', ', '.join(f'{k} {v:,}' for k, v in breakdown(s.n).items()))
        print('   ', ', '.join(f'{k} {s.n[k]}' for k in sorted(s.n)))


if __name__ == '__main__':
    main()
