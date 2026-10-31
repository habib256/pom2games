#!/usr/bin/env python3
"""Apple II image helpers, standard library only (importable, no CLI).

PNG
  png_write(path, rows, scale=1, mode='rgb', palette=None, level=9)
      rows: list of rows. A row is either raw sample bytes (bytes/bytearray/
      memoryview, already `mode`'s channel count per pixel) or a sequence of
      pixels: tuples for 'rgb'/'rgba' (extra channels are cut, so RGBA tuples
      can be written as 'rgb'), ints for 'gray'/'pal'. 'pal' needs `palette`
      (list of RGB triples, written as PLTE). scale: int or (sx, sy), integer
      pixel repeat. level: zlib level (9 = smallest; -1 = zlib's default, what a
      bare zlib.compress() gives). Same bytes as the hand-written writers it
      replaced, given the same level.
  png_read(path) -> (w, h, rows of RGBA tuples); load(path) -> (w, h, flat
      RGBA list). PNG (non-interlaced, 8-bit gray/RGB/index/gray+alpha/RGBA,
      all five filters, tRNS) or PPM P3/P6 (max 255).
HGR (8192-byte page, page-relative offsets from hgr_tables.hgr_offset)
  hgr_from_mono(px, hibits=None) -> bytearray(8192). px: rows (<= 192) of
      0/1 dots (<= 280). hibits: None (bit 7 clear), an int 0/1 for every
      byte of the rows given, or rows of 40 ints (palette bit per byte).
  hgr_to_rgb(page, mono=False, colours=None) -> 192 rows of 280 RGB tuples.
      NTSC artefact model: a lit dot next to a lit dot is white, an isolated
      lit dot takes the colour of its column parity and its byte's bit 7, an
      unlit dot between two lit dots takes their colour. mono: white/black.
      colours: {(x & 1, bit7): rgb}, default HGR_COLOURS.
DHGR (main and aux 8192-byte pages; colour IDs are the LORES numbers)
  dhgr_from_colors(px) -> (main, aux). px: rows (<= 192) of colour IDs 0-15
      (<= 140 pixels of 4 dots).
  dhgr_to_rgb(main, aux, palette=PALETTE) -> 192 rows of 140 RGB tuples.
Sprites
  preshift7(rows_bits, width, nbytes=None, palette=0, mask=False, step=1,
            fit=False) -> 7 phases of rows of `nbytes` HGR bytes (and the
      matching masks when mask=True: returns (phases, masks)).
      rows_bits: rows given as ints (bit x = dot x) or sequences of 0/1 dots.
      Phase s draws dot x at bit position (step*s) % 7 + x of the row, low
      bit first, 7 dots per byte; bit 7 = palette. nbytes default: the widest
      phase. step=2 is the 2-dot-cell layout (phases 0,2,4,6,1,3,5): expand
      each cell to two dots first. fit=True moves a phase left rather than
      cut dots that do not fit in nbytes. Mask bytes: $FF with the drawn dot
      bits cleared (AND mask, bit 7 set), as assets/convert.py banks.
  asm_bytes(data, per_line=8, hexa=True): ca65 `.byte` lines (fonts.py).
"""
from pathlib import Path
import re
import struct
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hgr_tables import hgr_offset  # noqa: E402
from fonts import asm_bytes, write_if_changed  # noqa: E402,F401

# DHGR/LORES colour IDs 0-15 (assets/convert.py preview palette).
PALETTE = [(0, 0, 0), (157, 9, 102), (42, 42, 165), (199, 52, 255),
           (0, 118, 44), (128, 128, 128), (0, 157, 255), (170, 170, 255),
           (128, 80, 0), (255, 106, 0), (128, 128, 128), (255, 137, 229),
           (0, 208, 55), (255, 244, 0), (77, 255, 191), (255, 255, 255)]
# HGR artefact colours keyed by (column parity, bit 7).
HGR_COLOURS = {(0, 0): (255, 68, 253), (1, 0): (20, 245, 60),     # violet, green
               (0, 1): (20, 207, 253), (1, 1): (255, 106, 60)}    # blue, orange
WHITE, BLACK = (255, 255, 255), (0, 0, 0)

_PNG_TYPE = {'gray': (0, 1), 'rgb': (2, 3), 'pal': (3, 1), 'rgba': (6, 4)}


# ------------------------------------------------------------------ PNG

def _chunk(kind, body):
    return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))


def _row_bytes(row, ch, sx):
    if isinstance(row, (bytes, bytearray, memoryview)):
        row = bytes(row)
        if sx == 1:
            return row
        return b''.join(row[i:i + ch] * sx for i in range(0, len(row), ch))
    if ch == 1:
        data = bytes(row)
        return data if sx == 1 else bytes(v for v in data for _ in range(sx))
    if sx == 1:
        return bytes(v for p in row for v in p[:ch])
    return b''.join(bytes(p[:ch]) * sx for p in row)


def png_write(path, rows, scale=1, mode='rgb', palette=None, level=9):
    """Write `rows` as an 8-bit PNG (see the module docstring)."""
    typ, ch = _PNG_TYPE[mode]
    sx, sy = (scale, scale) if isinstance(scale, int) else scale
    lines = [_row_bytes(r, ch, sx) for r in rows]
    w = len(lines[0]) // ch if lines else 0
    raw = b''.join((b'\0' + line) * sy for line in lines)
    body = _chunk(b'IHDR', struct.pack('>IIBBBBB', w, len(lines) * sy, 8, typ, 0, 0, 0))
    if mode == 'pal':
        if palette is None:
            raise ValueError("mode 'pal' needs a palette")
        body += _chunk(b'PLTE', b''.join(bytes(rgb) for rgb in palette))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + body + _chunk(b'IDAT', zlib.compress(raw, level))
                           + _chunk(b'IEND', b''))


def load(path):
    """PNG or PPM (P3/P6) -> (w, h, flat list of RGBA tuples)."""
    data = Path(path).read_bytes()
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        # P3/P6 with comments, maximum sample value 255.
        tokens = list(re.finditer(rb'#[^\n]*|\S+', data))
        tokens = [t for t in tokens if not t[0].startswith(b'#')]
        if len(tokens) < 4 or tokens[0][0] not in (b'P3', b'P6'):
            raise ValueError('expected PNG or PPM (P3/P6)')
        w, h, maxval = (int(t[0]) for t in tokens[1:4])
        if maxval != 255:
            raise ValueError('PPM max value must be 255')
        if tokens[0][0] == b'P3':
            raw = bytes(int(t[0]) for t in tokens[4:])
        else:
            start = tokens[3].end()
            start += 2 if data[start:start + 2] == b'\r\n' else 1
            raw = data[start:]
        if len(raw) != w * h * 3:
            raise ValueError('invalid PPM sample count')
        return w, h, [tuple(raw[i:i + 3]) + (255,) for i in range(0, len(raw), 3)]
    pos = 8
    compressed = bytearray()
    palette = []
    alpha = b''
    while pos < len(data):
        size, = struct.unpack_from('>I', data, pos)
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + size]
        crc, = struct.unpack_from('>I', data, pos + 8 + size)
        if zlib.crc32(kind + body) != crc:
            raise ValueError('PNG CRC mismatch')
        pos += 12 + size
        if kind == b'IHDR':
            w, h, depth, typ, comp, filt, inter = struct.unpack('>IIBBBBB', body)
        elif kind == b'PLTE':
            palette = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif kind == b'tRNS':
            alpha = body
        elif kind == b'IDAT':
            compressed.extend(body)
        elif kind == b'IEND':
            break
    if depth != 8 or inter or comp or filt or typ not in (0, 2, 3, 4, 6):
        raise ValueError('PNG must be non-interlaced with 8-bit gray/RGB/index/RGBA samples')
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[typ]
    stride = w * bpp
    raw = zlib.decompress(compressed)
    if len(raw) != h * (stride + 1):
        raise ValueError('invalid PNG sample count')
    rows = []
    previous = bytearray(stride)
    for y in range(h):
        f = raw[y * (stride + 1)]
        row = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if f > 4:
            raise ValueError('invalid PNG filter')
        for i in range(stride):
            a = row[i - bpp] if i >= bpp else 0
            b = previous[i]
            c = previous[i - bpp] if i >= bpp else 0
            estimate = a + b - c
            pa, pb, pc = abs(estimate - a), abs(estimate - b), abs(estimate - c)
            predictor = (0, a, b, (a + b) // 2, a if pa <= pb and pa <= pc else b if pb <= pc else c)[f]
            row[i] = (row[i] + predictor) & 255
        rows.extend(row)
        previous = row
    pixels = []
    for i in range(0, len(rows), bpp):
        px = rows[i:i + bpp]
        if typ == 6:
            rgba = tuple(px)
        elif typ == 2:
            transparent = len(alpha) == 6 and tuple(px) == struct.unpack('>HHH', alpha)
            rgba = tuple(px) + (0 if transparent else 255,)
        elif typ == 3:
            rgba = palette[px[0]] + (alpha[px[0]] if px[0] < len(alpha) else 255,)
        else:
            transparent = typ == 0 and len(alpha) == 2 and px[0] == struct.unpack('>H', alpha)[0]
            rgba = (px[0],) * 3 + (px[1] if typ == 4 else 0 if transparent else 255,)
        pixels.append(rgba)
    return w, h, pixels


def png_read(path):
    """PNG/PPM -> (w, h, rows of RGBA tuples)."""
    w, h, pixels = load(path)
    return w, h, [pixels[y * w:(y + 1) * w] for y in range(h)]


# ------------------------------------------------------------------ HGR

def hgr_from_mono(px, hibits=None):
    """Rows of 0/1 dots -> 8192-byte HGR page (bit 7 from `hibits`)."""
    if len(px) > 192 or any(len(row) > 280 for row in px):
        raise ValueError('HGR picture must fit 280x192')
    page = bytearray(8192)
    for y, row in enumerate(px):
        base = hgr_offset(y)
        for x, dot in enumerate(row):
            if dot:
                page[base + x // 7] |= 1 << (x % 7)
        if hibits:
            for col in range(40):
                hb = hibits if isinstance(hibits, int) else hibits[y][col]
                if hb:
                    page[base + col] |= 0x80
    return page


def hgr_to_rgb(page, mono=False, colours=None):
    """8192-byte HGR page -> 192 rows of 280 RGB tuples (artefact colours)."""
    col = HGR_COLOURS if colours is None else colours
    rows = []
    for line in range(192):
        a = hgr_offset(line)
        bits, hb = [], []
        for c in range(40):
            v = page[a + c]
            for i in range(7):
                bits.append(v >> i & 1)
                hb.append(v >> 7)
        if mono:
            rows.append([WHITE if b else BLACK for b in bits])
            continue
        row = []
        for x in range(280):
            if not bits[x]:
                # off dot between two lit ones takes their colour (artefact fill)
                if 0 < x < 279 and bits[x - 1] and bits[x + 1]:
                    row.append(col[((x + 1) & 1, hb[x - 1])])
                else:
                    row.append(BLACK)
            elif (x > 0 and bits[x - 1]) or (x < 279 and bits[x + 1]):
                row.append(WHITE)
            else:
                row.append(col[(x & 1, hb[x])])
        rows.append(row)
    return rows


# ------------------------------------------------------------------ DHGR

def dhgr_from_colors(px):
    """Rows of LORES colour IDs (140 wide max) -> (main, aux) 8192-byte pages."""
    if len(px) > 192 or any(len(row) > 140 for row in px):
        raise ValueError('DHGR picture must fit 140x192')
    main, aux = bytearray(8192), bytearray(8192)
    for y, row in enumerate(px):
        base = hgr_offset(y)
        for x, c in enumerate(row):
            value = ((c >> 1) | (c << 3)) & 15      # LORES ID -> 4 dots, low first
            for k in range(4):
                byte, bit = divmod(4 * x + k, 7)
                # even DHGR bytes are aux, odd ones main, both at offset byte // 2
                (aux if byte % 2 == 0 else main)[base + byte // 2] |= ((value >> k) & 1) << bit
    return main, aux


def dhgr_to_rgb(main, aux, palette=None):
    """(main, aux) 8192-byte pages -> 192 rows of 140 RGB tuples."""
    pal = PALETTE if palette is None else palette
    rows = []
    for line in range(192):
        a = hgr_offset(line)
        dots = []
        for b in range(80):
            v = (aux if b % 2 == 0 else main)[a + b // 2]
            dots += [v >> i & 1 for i in range(7)]
        row = []
        for x in range(140):
            v = dots[4 * x] | dots[4 * x + 1] << 1 | dots[4 * x + 2] << 2 | dots[4 * x + 3] << 3
            row.append(pal[((v << 1) | (v >> 3)) & 15])
        rows.append(row)
    return rows


# ------------------------------------------------------------------ sprites

def _row_int(row, width):
    if isinstance(row, int):
        return row & ((1 << width) - 1)
    return sum(1 << x for x, dot in enumerate(row[:width]) if dot)


def preshift7(rows_bits, width, nbytes=None, palette=0, mask=False, step=1, fit=False):
    """Seven HGR pre-shifted copies of a 1-bit sprite (see module docstring)."""
    rows = [_row_int(r, width) for r in rows_bits]
    shifts = [(step * s) % 7 for s in range(7)]
    if nbytes is None:
        nbytes = max((sh + width + 6) // 7 for sh in shifts)
    hb = 0x80 if palette else 0
    phases, masks = [], []
    for sh in shifts:
        if fit:
            sh = max(0, min(sh, 7 * nbytes - width))
        data, cover = [], []
        for r in rows:
            bits = r << sh
            line = [(bits >> (7 * b)) & 0x7F for b in range(nbytes)]
            data.append([hb | v for v in line])
            cover.append([0xFF ^ v for v in line])
        phases.append(data)
        masks.append(cover)
    return (phases, masks) if mask else phases
