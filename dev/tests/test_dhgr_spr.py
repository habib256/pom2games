#!/usr/bin/env python3
"""DHGR sprite compositor (dhgr.h dhgr_spr_*) against a Python model.

Scripted op lists (1-px moves, jumps, overlaps, mirror, palette, hide, the
screen edges, a shape larger than the canvas, invalidation, a restricted
area, cell backgrounds, an overlay) play in a cc65 fixture on the //e (and
the //c with --iic). After each update both banks of page 1 are compared
with the model (background + sprites -> nibbles -> bytes), and a2shot's
storewatch checks the write-once rule: during one update each (bank,
address) is stored at most once, with its final value, exactly the bytes of
the model's damage pieces; auxiliary stores run with IRQs masked, main ones
not (the caller's IRQs are on). Page 2 must stay untouched.
"""
import argparse
from pathlib import Path
import re
import tempfile
from test_hgr import DEV, build, compile_source, run
import a2test

HGRC = DEV / 'lib/hgrc'
A2SHOT = DEV / 'tools/a2shot/a2shot'
SOURCES = ('dhgr_spr_api.s', 'dhgr_spr_palette.s', 'dhgr_spr_area.s', 'dhgr_spr_update.s', 'dhgr_spr_asm.s', 'dhgr_cv_asm.s', 'dhgr_spr_overlay.s', 'dhgr_spr_cursor.s', 'dhgr_spr_cells.s', 'dhgr_cv_bitmap.s')
MAX = 8
DMAX = 2 * MAX + 6
NONE = 0xFF
MIRROR, HIDDEN = 1, 2


def nib(c):
    return ((c >> 1) | (c << 3)) & 15


def pack(n):
    """Seven nibbles -> aux even, main even, aux odd, main odd."""
    return ((n[0] | (n[1] & 7) << 4) & 0x7F,
            (n[1] >> 3 | n[2] << 1 | (n[3] & 3) << 5) & 0x7F,
            (n[3] >> 2 | n[4] << 2 | (n[5] & 1) << 6) & 0x7F,
            (n[5] >> 1 | n[6] << 3) & 0x7F)


# Shapes: (kind, w, h, rects). The drone and the technician of Robot Space
# Station (16..19 = the slot's palette), a block larger than any canvas
# piece, a dot.
DRONE = [(3, 0, 1, 2, 17), (2, 2, 6, 4, 16), (5, 3, 3, 2, 2), (6, 3, 2, 1, 15),
         (1, 6, 8, 4, 10), (2, 7, 5, 1, 16), (7, 8, 3, 1, 18), (2, 10, 2, 2, 19),
         (6, 10, 2, 2, 19)]
TECH = [(1, 0, 3, 3, 15), (3, 1, 2, 1, 14), (0, 3, 1, 3, 10), (1, 3, 3, 4, 9),
        (4, 4, 1, 1, 15), (1, 7, 1, 2, 10), (3, 7, 1, 2, 10)]
BIG = [(0, 0, 40, 50, 9), (3, 4, 30, 6, 13), (10, 20, 4, 25, 16)]
DOT = [(0, 0, 2, 2, 12)]
C = 0x80                                    # DHGR_CLEAR
SHIP = [C, C, 13, 13, C, C,
        C, 9, 15, 15, 9, C,
        6, 6, 2, 7, 6, 6,
        C, 12, C, C, 12, 1,
        11, C, C, C, C, 11]
TILE_A = [nib((x + y) % 16) for y in range(8) for x in range(7)]          # nibbles
TILE_C = [nib(4 if (x + y) % 3 else 14) for y in range(8) for x in range(7)]
WALL = [(0, 0, 7, 8, 5), (0, 7, 7, 1, 2)]
FLOOR = [(0, 0, 7, 8, 0), (3, 2, 1, 4, 12)]
SHAPES = [(0, 10, 12, DRONE), (0, 5, 9, TECH), (0, 40, 50, BIG), (0, 2, 2, DOT),
          (1, 6, 5, SHIP), (2, 7, 8, TILE_A), (0, 7, 8, WALL), (0, 7, 8, FLOOR),
          (1, 7, 8, [(x * 5 + y) % 16 for y in range(8) for x in range(7)]),
          (2, 7, 8, TILE_C), (2, 9, 6, [nib((x * y) % 16) for y in range(6) for x in range(9)])]
TSET = (5, 6, 7, 8)                         # tile set: shape numbers
OVBITS = [0x01, 0x03, 0x07, 0x0F, 0x03, 0x01, 0x40, 0x60, 0x70, 0x78, 0x30, 0x10] * 2


def initial_tmap():
    return [(c * 7 + r * 3 + (c * r) % 5) % 4 for r in range(24) for c in range(20)]


def initial_tiles():
    return [(((c * 3 + r * 5) % 16) | ((((c + r) % 4 == 0) * ((c + 2 * r) % 15 + 1)) << 4))
            for r in range(24) for c in range(20)]


class Model:
    def __init__(self, inside=False, double=False):
        self.inside = inside    # DHGR_SPR_OVERLAY_INSIDE: no save-under part
        self.double = double    # DHGR_SPR_DOUBLE: two pages, damage history
        # dhgr_clear(5) on page 1, dhgr_clear(10) on page 2, holes too
        self.pages = {1: [bytearray(b'\x55' * 8192), bytearray(b'\x2a' * 8192)],
                      2: [bytearray(b'\x2a' * 8192), bytearray(b'\x55' * 8192)]}
        self.draw = 2 if double else 1
        self.pend, self.pend_page, self.mvp = [], None, set()
        self.curs = {1: (None, {}), 2: (None, {})}   # double: each page's cursor
        self.slots = [dict(shape=None, x=0, y=0, flags=0, dirty=False, box=None, drawn=None,
                           pal=[0, 0, 0, 0]) for _ in range(MAX)]
        self.area = (0, 19, 0, 191)
        self.solid, self.cells = 0, None
        self.tiles = initial_tiles()
        self.tmode = None                       # (ox, oy, ch): tiles background
        self.tmap = initial_tmap()
        self.tset = list(TSET)
        self.dmg = []
        self.ov = None          # wanted (bx, y, w, h)
        self.ov_dirty = False
        self.ov_drawn = None    # (g0, g1, y0, y1)
        self.cur = None         # cursor on screen (bx, y, w, h), its saved bytes
        self.saved = {}

    @property
    def main(self):
        return self.pages[self.draw][0]

    @property
    def aux(self):
        return self.pages[self.draw][1]

    # -- damage, as dhgr_spr.c does it -----------------------------------
    def clip(self, r):
        g0, g1, y0, y1 = r
        a = self.area
        g0, g1, y0, y1 = max(g0, a[0]), min(g1, a[1]), max(y0, a[2]), min(y1, a[3])
        return (g0, g1, y0, y1) if g0 <= g1 and y0 <= y1 else None

    def add(self, r):
        r = self.clip(r)
        if not r:
            return
        if len(self.dmg) == DMAX:
            o = self.dmg[0]
            self.dmg[0] = (min(o[0], r[0]), max(o[1], r[1]), min(o[2], r[2]), max(o[3], r[3]))
        else:
            self.dmg.append(r)

    def set(self, i, shape, x, y, flags):
        s = self.slots[i]
        if (s['shape'], s['x'], s['y'], s['flags']) == (shape, x, y, flags):
            return
        s.update(shape=shape, x=x, y=y, flags=flags, dirty=True, box=None)
        if shape is not None and not flags & HIDDEN and x < 140 and y < 192:
            _, w, h, _ = SHAPES[shape]
            s['box'] = (x, min(x + w - 1, 139), y, min(y + h - 1, 191))

    def palette(self, i, four):
        if self.slots[i]['pal'] != list(four):
            self.slots[i]['pal'] = list(four)
            self.slots[i]['dirty'] = True

    def invalidate(self, x, y, w, h):
        if not w or not h or x >= 140 or y >= 192:
            return
        self.add((x // 7, min(x + w - 1, 139) // 7, y, min(y + h - 1, 191)))

    def overlay(self, bx, y, w, h):
        if bx >= 80 or y >= 192 or not h:
            w = 0
        w = min(w, 80 - bx) if w else 0
        h = min(h, 192 - y)
        if w * h > 127:
            w = 0
        new = (bx, y, w, h) if w else None
        if new != self.ov:
            self.ov, self.ov_dirty = new, True

    def update(self):
        for s in self.slots:
            if not s['dirty']:
                continue
            s['dirty'] = False
            if s['drawn']:
                self.add(s['drawn'])
                s['drawn'] = None
            if s['box']:
                x0, x1, y0, y1 = s['box']
                r = self.clip((x0 // 7, x1 // 7, y0, y1))
                if r:
                    s['drawn'] = r
                    self.add(r)
        moved = self.ov_dirty
        if self.double:                 # page_moved: each page owes the pass
            if self.ov_dirty:
                self.mvp |= {1, 2}
            moved = self.draw in self.mvp
            self.mvp.discard(self.draw)
        if self.ov_dirty:
            self.ov_dirty = False
            if self.ov_drawn:
                self.add(self.ov_drawn)
            self.ov_drawn = None
            if self.ov:
                bx, y, w, h = self.ov
                self.ov_drawn = (bx >> 2, (bx + w - 1) >> 2, y, y + h - 1)
                self.add(self.ov_drawn)
        if self.double:                 # history: the other page's pending list
            merge(self.dmg)
            n0 = len(self.dmg)
            if self.pend_page == self.draw:
                for r in self.pend:
                    self.add(r)
                self.pend = []
            for r in self.dmg[:n0]:
                if len(self.pend) == DMAX:
                    o = self.pend[0]
                    self.pend[0] = (min(o[0], r[0]), max(o[1], r[1]), min(o[2], r[2]), max(o[3], r[3]))
                else:
                    self.pend.append(r)
            self.pend_page = 3 - self.draw
        d = self.dmg
        merge(d)
        stores = {}
        page = 0x2000 * self.draw
        for g0, g1, y0, y1 in d:
            for y in range(y0, y1 + 1):
                row = self.row_bytes(y, g0, g1)
                base = a2test.hgr_offset(y)
                for g in range(g0, g1 + 1):
                    b = row[g]
                    for k, bank in enumerate(('aux', 'main', 'aux', 'main')):
                        addr = base + 2 * g + k // 2
                        key = (bank, page + addr)
                        assert key not in stores, 'model damage overlaps'
                        stores[key] = b[k]
                        getattr(self, bank)[addr] = b[k]
        self.dmg = []
        if moved and not self.inside:
            a = self.area
            if self.double:
                self.cur, self.saved = self.curs[self.draw]
            self.cursor(self.ov, stores, lambda b, y: a[2] <= y <= a[3] and a[0] <= b // 4 <= a[1])
            if self.double:
                self.curs[self.draw] = (self.cur, self.saved)
        return stores

    def frame_check(self, label):
        """The draw page's area equals the whole frame composed afresh."""
        g0, g1, y0, y1 = self.area
        for y in range(y0, y1 + 1):
            row = self.row_bytes(y, g0, g1)
            base = a2test.hgr_offset(y)
            for g in range(g0, g1 + 1):
                for k, bank in enumerate(('aux', 'main', 'aux', 'main')):
                    got = getattr(self, bank)[base + 2 * g + k // 2]
                    assert got == row[g][k], (label, 'page has not converged', y, g, k)

    def cursor(self, new, stores, excluded=lambda b, y: False):
        """dhgr_cursor_core: one pass over old U new outside the excluded box."""
        old, saved = self.cur, {}
        cells = set()
        for box in (old, new):
            if box:
                bx, y, w, h = box
                cells |= {(b, r) for b in range(bx, bx + w) for r in range(y, y + h)}
        for b, r in sorted(cells, key=lambda c: (c[1], c[0])):
            if excluded(b, r):
                continue
            bank = 'aux' if b % 2 == 0 else 'main'
            addr = a2test.hgr_offset(r) + b // 2
            key = (bank, 0x2000 * self.draw + addr)
            inside = lambda box: box and box[0] <= b < box[0] + box[2] and box[1] <= r < box[1] + box[3]
            base = self.saved[(b, r)] if inside(old) else getattr(self, bank)[addr] & 0x7F
            out = base
            if inside(new):
                saved[(b, r)] = base
                bx, y, w, h = new
                out = base | (OVBITS[(r - y) * w + b - bx] & 0x7F)
            assert key not in stores, 'cursor byte inside the damage'
            stores[key] = out
            getattr(self, bank)[addr] = out
        self.cur, self.saved = new, saved

    # -- composition ----------------------------------------------------
    def background(self, x, y):
        """The background nibble at x, y (None: not covered)."""
        if self.tmode:
            ox, oy, ch = self.tmode
            if y < oy:
                return None
            col, row = x // 7 - ox // 7, (y - oy) // ch
            shape = self.tset[self.tmap[row * 20 + col]]
            px = {x: None}
            paint(px, shape, ox + col * 7, oy + row * ch, 0, (0, 0, 0, 0), y)
            return px[x]
        if self.cells is None:
            return nib(self.solid)
        ox, oy, ch = self.cells
        if y < oy:
            return None
        col, row = x // 7 - ox // 7, (y - oy) // ch
        t = self.tiles[row * 20 + col]
        cx, cy = ox + col * 7, oy + row * ch
        if t >> 4 and cx + 1 <= x < cx + 6 and cy + 2 <= y < cy + ch - 2:
            return nib(t >> 4)
        return nib(t & 15)

    def row_bytes(self, y, g0, g1):
        px = {x: self.background(x, y) for x in range(g0 * 7, g1 * 7 + 7)}
        for s in self.slots:
            if s['shape'] is not None and s['box']:
                paint(px, s['shape'], s['x'], s['y'], s['flags'], s['pal'], y)
        out = {}
        for g in range(g0, g1 + 1):
            values = [px[x] for x in range(g * 7, g * 7 + 7)]
            assert None not in values, 'the background does not cover the area'
            b = list(pack(values))
            if self.ov_drawn and self.ov:
                bx, oy, w, h = self.ov
                if oy <= y < oy + h:
                    for k in range(4):
                        if bx <= 4 * g + k < bx + w:
                            b[k] |= OVBITS[(y - oy) * w + 4 * g + k - bx] & 0x7F
            out[g] = b
        return out


def merge(d):
    """dhgr_spr_update's merge: entry i absorbs every entry j it overlaps
    (scanning again after each); an earlier j absorbs i and becomes i."""
    i = 0
    while i < len(d):
        j = 0
        while j < len(d):
            a, b = d[i], d[j]
            if j != i and a[0] <= b[1] and b[0] <= a[1] and a[2] <= b[3] and b[2] <= a[3]:
                box = (min(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), max(a[3], b[3]))
                keep, drop = (i, j) if j > i else (j, i)
                d[keep] = box
                d[drop] = d[-1]
                d.pop()
                i, j = keep, 0
                continue
            j += 1
        i += 1


def paint(px, shape, sx, sy, flags, pal, y):
    """Row y of shape number `shape` at sx, sy into px {x: nibble}."""
    kind, sw, sh, data = SHAPES[shape]
    if kind == 0:
        for rx, ry, rw, rh, c in data:
            if flags & MIRROR:
                rx = sw - rx - rw
            if sx + rx > 255 or sy + ry > 255 or not sy + ry <= y < sy + ry + rh:
                continue
            colour = pal[c & 3] if c >= 16 else c
            for x in range(sx + rx, sx + rx + rw):
                if x in px:
                    px[x] = nib(colour)
        return
    if not sy <= y < sy + sh or y > 191:
        return
    for c in range(sw):
        x = sx + c
        if x not in px:
            continue
        v = data[(y - sy) * sw + (sw - 1 - c if kind == 1 and flags & MIRROR else c)]
        if kind == 2:
            px[x] = v
        elif not v & 0x80:
            px[x] = nib(v)


class Script:
    """Op bytes for the fixture, played on the model at the same time."""

    def __init__(self, inside=False, double=False):
        self.ops, self.model, self.updates = [], Model(inside, double), []

    def set(self, i, shape, x, y, flags=0):
        self.ops += [1, i, NONE if shape is None else shape, x, y, flags]
        self.model.set(i, shape, x, y, flags)

    def palette(self, i, four):
        self.ops += [2, i, *four]
        self.model.palette(i, four)

    def invalidate(self, x, y, w, h):
        self.ops += [3, x, y, w, h]
        self.model.invalidate(x, y, w, h)

    def overlay(self, bx, y, w, h):
        self.ops += [4, bx, y, w, h]
        self.model.overlay(bx, y, w, h)

    def area(self, x0, y0, x1, y1):
        self.ops += [6, x0, y0, x1, y1]
        self.model.area = (x0 // 7, min(x1, 139) // 7, y0, min(y1, 191))

    def solid(self, c):
        self.ops += [7, c]
        self.model.solid, self.model.cells, self.model.tmode = c, None, None

    def cells(self, ox, oy, ch):
        self.ops += [8, ox, oy, ch]
        self.model.cells, self.model.tmode = (ox, oy, ch), None

    def tile(self, col, row, value):
        self.ops += [9, col, row, value]
        self.model.tiles[row * 20 + col] = value

    def cursor(self, bx, y, w, h, label):
        self.ops += [13, bx, y, w, h]
        if bx >= 80 or bx + w > 80 or y >= 192 or y + h > 192 or not h or w * h > 127:
            w = 0
        stores = {}
        self.model.cursor((bx, y, w, h) if w else None, stores)
        m = self.model
        self.updates.append((label, stores, bytes(m.pages[1][0]), bytes(m.pages[1][1]),
                             bytes(m.pages[2][0]), bytes(m.pages[2][1]), 1))

    def tiles(self, ox, oy, ch):
        self.ops += [10, ox, oy, ch]
        self.model.tmode, self.model.cells = (ox, oy, ch), None

    def tset(self, index, shape):
        self.ops += [11, index, shape]
        self.model.tset[index] = shape

    def tmap(self, col, row, value):
        self.ops += [12, col, row, value]
        self.model.tmap[row * 20 + col] = value

    def update(self, label):
        self.ops.append(5)
        m = self.model
        drawn = m.draw
        stores = m.update()
        if m.double:                    # dhgr_spr_present: show it, draw on the other
            m.frame_check(label)
            m.draw = 3 - drawn
        self.updates.append((label, stores, bytes(m.pages[1][0]), bytes(m.pages[1][1]),
                             bytes(m.pages[2][0]), bytes(m.pages[2][1]), drawn))


def scenario(inside=False, double=False):
    s = Script(inside, double)
    s.solid(2)
    s.invalidate(0, 0, 140, 192)
    s.update('full solid')
    s.palette(0, (7, 13, 15, 9))
    s.set(0, 0, 20, 30)
    s.update('drone appears')
    for x, y in ((21, 30), (22, 30), (22, 31), (21, 30), (20, 29), (27, 29), (28, 29)):
        s.set(0, 0, x, y)
        s.update(f'drone 1px {x},{y}')
    s.set(0, 0, 90, 120)
    s.update('drone jumps')
    s.palette(1, (14, 5, 1, 1))
    s.set(1, 0, 95, 124, MIRROR)
    s.set(2, 1, 93, 118)
    s.update('overlap: three slots')
    s.set(1, 0, 96, 124, MIRROR)
    s.update('lower slot moves under')
    s.set(1, 0, 96, 124)
    s.update('mirror off')
    s.palette(1, (14, 5, 15, 9))
    s.update('palette change')
    s.palette(1, (14, 5, 15, 9))
    s.update('same palette: nothing')
    s.set(0, 0, 90, 120, HIDDEN)
    s.update('hide')
    s.set(0, 0, 90, 120)
    s.update('show again')
    for x, y in ((0, 0), (139, 0), (135, 185), (0, 191), (134, 191), (133, 180)):
        s.set(3, 0, x, y, MIRROR if x & 1 else 0)
        s.update(f'edge {x},{y}')
    s.set(3, None, 0, 0)
    s.update('slot 3 empty')
    s.set(4, 2, 30, 60)
    s.update('big shape')
    s.set(4, 2, 31, 61)
    s.update('big shape moves')
    s.set(5, 3, 45, 80)
    s.set(4, 2, 110, 150)
    s.update('big shape to the corner')
    s.cells(0, 8, 8)
    s.area(0, 8, 139, 183)
    s.invalidate(0, 0, 140, 192)
    s.update('cells, area rows 8..183')
    s.set(0, 0, 41, 40)
    s.update('drone over cells')
    s.set(0, 0, 42, 41)
    s.update('drone over cells 1px')
    s.tile(6, 4, 0x3C)
    s.invalidate(42, 40, 7, 8)
    s.update('tile changed + invalidate')
    s.set(0, 0, 41, 2)
    s.update('drone partly above the area')
    s.area(14, 8, 125, 183)
    s.set(0, 0, 8, 100)
    s.update('area columns 2..17: drone clipped at the left')
    s.set(0, 0, 9, 100)
    s.update('clipped drone 1px')
    s.overlay(30, 50, 4, 6)
    s.update('overlay on')
    s.overlay(31, 51, 4, 6)
    s.update('overlay 1 byte right, 1 row down')
    s.set(2, 1, 52, 50)
    s.update('sprite under the overlay')
    s.set(2, 1, 53, 50)
    s.update('sprite under the overlay 1px')
    s.overlay(31, 51, 0, 6)
    s.update('overlay off')
    for k in range(8):
        s.set(k, k % 4, 15 + k * 13, 20 + k * 17, k & 1)
    s.update('eight slots')
    for k in range(8):
        s.set(k, k % 4, 16 + k * 13, 20 + k * 17, k & 1)
    s.update('eight slots move')
    s.set(6, 4, 70, 70)
    s.set(7, 4, 74, 72, MIRROR)
    s.update('chunky ships, one mirrored')
    s.set(7, 4, 75, 72, MIRROR)
    s.set(6, 10, 69, 69)
    s.update('chunky ship 1px, tile-kind sprite')
    s.tiles(0, 16, 8)
    s.area(0, 16, 139, 175)
    s.invalidate(0, 0, 140, 192)
    s.update('tiles background, rows 16..175')
    s.set(0, 0, 50, 60)
    s.update('drone over tiles')
    s.set(0, 0, 51, 60)
    s.update('drone over tiles 1px')
    s.set(6, 4, 3, 170, MIRROR)
    s.update('chunky ship clipped by the area bottom')
    s.tset(1, 9)
    s.invalidate(0, 16, 140, 160)
    s.update('tile set entry changed')
    s.tmap(7, 5, 2)
    s.invalidate(49, 56, 7, 8)
    s.update('map cell changed')
    s.overlay(40, 172, 4, 6)
    s.update('overlay across the area bottom')
    s.overlay(41, 173, 4, 6)
    s.update('overlay across the bottom, 1 byte, 1 row')
    s.set(0, 0, 70, 166)
    s.update('drone under the overlay part in the area')
    s.overlay(41, 180, 4, 6)
    s.update('overlay outside the area')
    s.overlay(42, 181, 4, 6)
    s.update('overlay outside, moved')
    s.overlay(0, 186, 3, 4)
    s.update('overlay bottom-left corner')
    s.overlay(0, 0, 0, 0)
    s.update('overlay hidden')
    if double:                  # (dhgr_cursor draws on one page: left out)
        s.overlay(60, 2, 4, 6)
        s.update('overlay above the area')
        s.overlay(61, 3, 4, 6)
        s.update('overlay above the area, moved')
        s.update('nothing changed: page 1 catches up')
        s.update('nothing changed at all')
        s.overlay(61, 3, 0, 0)
        s.update('overlay hidden again')
        s.update('overlay hidden on both pages')
        s.ops.append(0)
        return s
    s.cursor(76, 4, 4, 6, 'cursor alone')
    s.cursor(77, 5, 3, 6, 'cursor alone at the right edge')
    s.cursor(79, 186, 1, 6, 'cursor alone, bottom-right byte')
    s.cursor(78, 186, 2, 6, 'cursor alone, one byte left')
    s.cursor(0, 0, 0, 0, 'cursor alone hidden')
    s.ops.append(0)
    return s


def scenario_vbl():
    """DHGR_SPR_VBL timing: a 2-group drone 1 px moves (12 and 13 rows) at
    rows 20, 100 and 180: each such update waits for a VBL edge, then writes
    every row before the beam starts it."""
    s = Script()
    s.solid(2)
    s.invalidate(0, 0, 140, 192)
    s.update('full solid')
    s.palette(0, (7, 13, 15, 9))
    for y in (20, 100, 180):
        s.set(0, 0, 42, y)
        s.update(f'vbl: drone appears at row {y}' if y == 20 else f'drone to row {y} (two boxes)')
        s.set(0, 0, 43, y)
        s.update(f'vbl: 1 px right, row {y}')
        s.set(0, 0, 43, y - 1)
        s.update(f'vbl: 1 px up, row {y - 1} (13 rows)')
    s.set(0, 0, 50, 60)
    s.set(1, 1, 60, 70)
    s.update('two rectangles: plain order')
    s.ops.append(0)
    return s


def a2test_frame(machine):
    return 17030                # NTSC frame (a2shot without --pal)


ROW_OF = {a2test.hgr_offset(y) + b: y for y in range(192) for b in range(40)}
BLANK, LINE = 4550, 65


def write_inc(work, script, canvas, groups):
    shapes, data = [], ''
    for n, (kind, w, h, rects) in enumerate(SHAPES):
        values = [v for r in rects for v in r] if kind == 0 else rects
        data += f'static const unsigned char shape{n}[] = {{' + ','.join(map(str, values)) + '};\n'
        shapes.append(f'{{{kind},{w},{h},{len(rects) if kind == 0 else 0},shape{n}}}')
    (work / 'dhgr_spr_ops.inc').write_text(
        f'#define CANVAS_BYTES {canvas}u\n#define CANVAS_GROUPS {groups}u\n' + data +
        'static const dhgr_shape_t shapes[] = {' + ','.join(shapes) + '};\n'
        'static const unsigned char ovbits[] = {' + ','.join(map(str, OVBITS)) + '};\n'
        'static unsigned char tiles[480] = {' + ','.join(map(str, initial_tiles())) + '};\n'
        'static unsigned char tmap[480] = {' + ','.join(map(str, initial_tmap())) + '};\n'
        'static const dhgr_shape_t *tset[4] = {' + ','.join(f'shapes+{t}' for t in TSET) + '};\n'
        'static const unsigned char ops[] = {' + ','.join(map(str, script.ops)) + '};\n')


MARKERS = '''.export _begin, _end, _irq_on
.code
_begin: rts
_end: rts
_irq_on: cli
    rts
'''
# VIA T1 IRQs every ~2,000 cycles (Mockingboard, slot 4) during the whole
# run (test_dhgr_clear_rows.py's probe): the handler checks, through the
# enhanced ROM's saved frame, that no IRQ arrives with RAMRD/RAMWRT on.
VIA_IRQ = '''.export _begin, _end, _irq_on, irq_ticks, irq_errors
.bss
irq_ticks: .res 2
irq_errors: .res 1
irq_fault_pass: .res 1
.code
_begin: rts
_end: rts
_irq_on:
    sei
    lda #<handler
    sta $03fe
    lda #>handler
    sta $03ff
    lda #$7f
    sta $c40e
    lda #$40
    sta $c40b
    lda #$fe
    sta $c404
    lda #$07
    sta $c405
    lda #$c0
    sta $c40e
    ; negative control: one IRQ with RAMWRT on must count as an error
    lda irq_ticks
    sta $c005
    cli
fault:
    cmp irq_ticks
    beq fault
    sta $c004
    sei
    lda irq_errors
    sta irq_fault_pass
    lda #0
    sta irq_errors
    cli
    rts
handler:
    pha
    txa
    pha
    tsx
    lda $0107,x             ; (enhanced ROM frame: RAMRD $20 / RAMWRT $10)
    and #$30
    beq ok
    inc irq_errors
ok: lda $c404
    inc irq_ticks
    bne done
    inc irq_ticks+1
done:
    pla
    tax
    pla
    rti
'''
STORE = re.compile(r'^store ([0-9A-F]{4}) ([0-9A-F]{4}) \S+ A=([0-9A-F]{2}) X=([0-9A-F]{2}) '
                   r'Y=([0-9A-F]{2}) S=[0-9A-F]{2} P=([0-9A-F]{2}) LC=(\d)(\d)(\d)(\d)(\d) op=(\w\w)')


def link(work, name, variant, markers='markers.o'):
    """Fixture + compositor (variant defines) + work/hgrc.lib -> a disk."""
    defines = [f'-D{d}=1' for d in variant]
    objects = []
    clock = 'DHGR_SPR_DOUBLE' in variant or 'DHGR_SPR_VBL' in variant
    for source in SOURCES + (('dhgr_spr_present.s',) if 'DHGR_SPR_DOUBLE' in variant else ()):
        src = HGRC / source
        if source.endswith('.s') and defines:
            src = work / f'{name}_{source}'
            src.write_text(''.join(f'{d} = 1\n' for d in variant) + f'.include "{source}"\n')
        obj = work / f'{name}_{Path(source).stem}.o'
        compile_source(src, obj, ['-t', 'none', '-Oirs', *(defines if source.endswith('.c') else ()),
                                  '-I', HGRC, '--asm-include-dir', HGRC,
                                  '--asm-include-dir', DEV / 'lib/apple2'])
        objects.append(obj)
    if clock:                   # the VBL clock: apple2vbl (+ its mouse and frame imports)
        for src in (DEV / 'lib/apple2c/apple2vbl.s', DEV / 'lib/apple2c/apple2frame.s',
                    DEV / 'lib/mouse/mouse.s'):
            obj = work / f'{name}_{src.stem}.o'
            compile_source(src, obj, ['-t', 'none'])
            objects.append(obj)
    fixture = work / f'{name}_fixture.o'
    compile_source(DEV / 'tests/dhgr_spr_fixture.c', fixture,
                   ['-t', 'none', '-Oirs', '-I', work, '-I', HGRC, '-I', DEV / 'lib/apple2c',
                    *(['-DFIXTURE_DOUBLE'] if 'DHGR_SPR_DOUBLE' in variant else ()),
                    *(['-DFIXTURE_VBL'] if 'DHGR_SPR_VBL' in variant else ())])
    cfg = work / 'test.cfg'
    text = (DEV / 'cc65/apple2_hgr_c.cfg').read_text()
    text = text.replace('__STACKSIZE__:  type = weak, value = $0800', '__STACKSIZE__:  type = weak, value = $0200')
    cfg.write_text(text.replace('    CODE:', '    DHGRSPRCODE: load = RAM, type = ro, optional = yes;\n    CODE:', 1))
    binary = work / f'{name}.bin'
    run(['cl65', '-t', 'none', '-C', cfg, '-m', work / f'{name}.map', '-Ln', work / f'{name}.lbl',
         '-o', binary, work / 'crt0_apple2.o', fixture, work / markers,
         work / 'apple2io_asm.o', *objects, work / 'hgrc.lib'])
    if 'DHGR_SPR_CODE_SEGMENT' in variant:
        owner, mine = None, {f'{name}_{Path(source).stem}.o' for source in SOURCES}
        for line in (work / f'{name}.map').read_text().split('Segment list:')[0].splitlines():
            if line and not line[0].isspace():
                owner = Path(line.rstrip(':')).name
            elif owner in mine and line.split()[:1] in (['CODE'], ['RODATA']):
                raise AssertionError((owner, 'code outside DHGRSPRCODE', line))
    return a2test.build_disk(work, name.upper()[:8], binary), a2test.labels(work / f'{name}.lbl')


def check(work, name, script, machine, variant=(), irq=False, timing=None):
    """timing: a list receiving (label, edges seen, smallest beam lead) per
    update: the VBL watch is on and each store after an edge is checked."""
    disk, labels = link(work, name, variant, 'via.o' if irq else 'markers.o')
    double = 'DHGR_SPR_DOUBLE' in variant
    page2 = ['peek:4000:8192', 'poke:C003:0', 'peek:4000:8192', 'poke:C002:0']
    steps = ['watch:%04X' % labels['vbl_seen']] if timing is not None else []
    for _ in script.updates:
        steps += [labels.until('_begin'), 'storewatch:2000:5FFF', labels.until('_end'),
                  'unstorewatch', 'peek:%04X:2' % labels['sp'], 'peek:2000:8192', 'poke:C003:0', 'peek:2000:8192',
                  'poke:C002:0', *(page2 if double else ()), 'press: ']
    # Before the last key (the program then exits): page 2, both banks.
    if not double:
        steps[-1:-1] = page2
    if irq:
        steps[-1:-1] = [labels.peek('irq_ticks', 4)]
    out = run([A2SHOT, machine, *(['--mockingboard'] if irq else []), '--disk', disk, *steps],
              timeout=900)
    result = a2test.Result(out)
    # Update i's stores come before its first dump: segment 2i of the split.
    segments = re.split(r'(?m)^2000: ', out)
    total_stores = 0
    ticks = [int(c) for c in re.findall(r'(?m)^until \S+ cycles=(\d+)', out)]
    cycles = {label: ticks[2 * i + 1] - ticks[2 * i] for i, (label, *_) in enumerate(script.updates)}
    per = 4 if double else 3      # (contiguous peeks join: aux 1 + main 2)
    for index, (label, expected, main, aux, main2, aux2, drawn) in enumerate(script.updates):
        seen = {}
        previous = None
        edge = None
        edges = 0
        lead = None
        for line in segments[2 * index].split('\n'):
            if timing is not None and line.startswith('watch '):
                # The edge lies between this poll's read and the one before
                # (11 cycles a poll): count from the earliest it can be.
                edge = int(line.rsplit('cycles=', 1)[1]) - 15
                edges += 1
                timing.append(('phase', edge % a2test_frame(machine)))
                continue
            m = STORE.match(line)
            if not m:
                continue
            # storewatch prints an instruction before stepping it: when an
            # IRQ is taken there instead, the same store shows up again after
            # the handler (same PC and registers): one store.
            if irq and previous and m.group(1, 2, 3, 4, 5) == previous:
                continue
            previous = m.group(1, 2, 3, 4, 5)
            addr = int(m[2], 16)
            if edge is not None:
                # The store's write cycle (its last) before the beam starts its row.
                at = int(line.rsplit('cycles=', 1)[1]) + 5
                row = ROW_OF[(addr - 0x2000) & 0x1FFF]
                spare = edge + BLANK + LINE * row - at
                assert spare > 0, (label, 'store behind the beam', row, hex(addr), spare)
                lead = spare if lead is None else min(lead, spare)
            bank = 'aux' if m[11] == '1' else 'main'
            assert m[9] == '0' and m[10] == '0', (label, 'ALTZP/RAMRD on', line)
            key = (bank, addr)
            assert key not in seen, (label, 'stored twice', bank, hex(addr))
            assert 0x2000 * drawn <= addr < 0x2000 * (drawn + 1), (label, 'store outside the draw page', line)
            seen[key] = int(m[3], 16)
            irq_masked = bool(int(m[6], 16) & 4)
            assert irq_masked == (bank == 'aux'), (label, 'IRQ mask around the stores', line)
        total_stores += len(seen)
        if timing is not None:
            timing.append((label, edges, lead))
        missing = set(expected) - set(seen)
        extra = set(seen) - set(expected)
        assert not missing and not extra, (label, 'stores differ from the model damage',
                                           sorted(missing)[:4], sorted(extra)[:4], len(missing), len(extra))
        wrong = [k for k in expected if seen[k] != expected[k]]
        assert not wrong, (label, 'stored value is not the final one', wrong[:4])
        sp, got_main, joined, *more = result.dumps[per * index:per * index + per]
        got_aux = joined[:8192]
        assert sp == result.dumps[0], (label, 'C stack pointer moved', sp.hex(), result.dumps[0].hex())
        compare = [('main', got_main, main, 0x2000), ('aux', got_aux, aux, 0x2000)]
        if double:
            compare += [('main', joined[8192:], main2, 0x4000), ('aux', more[0][:8192], aux2, 0x4000)]
        for bank, got, want, at in compare:
            if got != want:
                diff = [i for i in range(8192) if got[i] != want[i]]
                raise AssertionError((label, bank, 'screen != model', len(diff),
                                      [(hex(at + i), got[i], want[i]) for i in diff[:6]]))
    # dhgr_clear(10) on page 2: main $2A, aux $55 everywhere (holes too).
    dumps = result.dumps
    if irq:
        ticks, errors, control = int.from_bytes(dumps[-1][:2], 'little'), dumps[-1][2], dumps[-1][3]
        assert control, 'negative control: the IRQ with RAMWRT on was not detected'
        assert errors == 0, 'an IRQ arrived with RAMRD/RAMWRT on'
        assert ticks > 1000, ('IRQs not serviced', ticks)
        dumps = dumps[:-1]
    # (page 2 main continues the last aux dump: contiguous addresses)
    if not double:
        assert dumps[-2][8192:] == b'\x2a' * 8192 and dumps[-1] == b'\x55' * 8192, 'page 2 changed'
    return total_stores, cycles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iic', action='store_true', help='the //c only')
    ap.add_argument('--quick', action='store_true', help='one configuration')
    ap.add_argument('--only', help='configurations to run (comma-separated names)')
    ap.add_argument('--keep', help='work directory to keep')
    ap.add_argument('--cycles', action='store_true', help='print each update\'s cycles')
    args = ap.parse_args()
    machines = ['--iic'] if args.iic else ['--iie', '--iic']
    configs = [('base', 1024, 4, ()), ('small', 70, 2, ()),
               ('wide', 1024, 20, ('DHGR_SPR_PACK_TABLES',)),
               ('segment', 512, 3, ('DHGR_SPR_PACK_TABLES', 'DHGR_SPR_CODE_SEGMENT')),
               ('inside', 255, 4, ('DHGR_SPR_OVERLAY_INSIDE',)),
               ('double', 255, 4, ('DHGR_SPR_DOUBLE',)),
               ('vbl', 255, 4, ('DHGR_SPR_VBL',))]
    if args.quick:
        configs = configs[:1]
    if args.only:
        configs = [c for c in configs if c[0] in args.only.split(',')]
    with tempfile.TemporaryDirectory(prefix='dhgr-spr-') as directory:
        work = Path(args.keep) if args.keep else Path(directory)
        work.mkdir(exist_ok=True)
        build(work)                              # hgrc.lib, crt0, apple2io
        (work / 'markers.s').write_text(MARKERS)
        compile_source(work / 'markers.s', work / 'markers.o', ['-t', 'none'])
        (work / 'via.s').write_text(VIA_IRQ)
        compile_source(work / 'via.s', work / 'via.o', ['-t', 'none'])
        for name, canvas, groups, variant in configs:
            script = scenario('DHGR_SPR_OVERLAY_INSIDE' in variant, 'DHGR_SPR_DOUBLE' in variant)
            write_inc(work, script, canvas, groups)
            for machine in machines:
                stores, cycles = check(work, name, script, machine, variant)
                print(f'DHGR compositor {name} ({canvas} B canvas, {groups} groups'
                      f'{", " + "+".join(variant) if variant else ""}) {machine[2:]}: '
                      f'{len(script.updates)} updates == model, {stores} stores each once.')
                if args.cycles:
                    for label, c in cycles.items():
                        print(f'  {c:8} {label}')
            if name == 'vbl':
                script = scenario_vbl()
                write_inc(work, script, canvas, groups)
                for machine in machines:
                    timing = []
                    check(work, 'vblt', script, machine, variant, timing=timing)
                    phases = [t[1] for t in timing if t[0] == 'phase']
                    timing = [t for t in timing if t[0] != 'phase']
                    # $C019 falls at the start of row 192 every frame: the
                    # same phase each time (the beam model used above).
                    assert not phases or max(phases) - min(phases) <= 15, ('edge phase', phases)
                    waited = [t for t in timing if t[0].startswith('vbl:')]
                    if machine == '--iie':
                        assert all(t[1] == 1 for t in waited), ('no VBL wait', timing)
                        assert all(t[1] == 0 for t in timing if not t[0].startswith('vbl:')), \
                            ('waited for a VBL edge in the plain order', timing)
                        print(f'DHGR compositor vbl timing iie: {len(waited)} updates wait for the '
                              'VBL edge, every store before the beam reaches its row (least lead '
                              f'{min(t[2] for t in waited)} cycles, edge at frame cycle '
                              f'{min(phases)}); the others do not wait.')
                        if args.cycles:
                            for label, edges, lead in timing:
                                print(f'  {edges} edge, lead {lead}: {label}')
                    else:
                        print(f'DHGR compositor vbl timing iic (no VBL clock without ProDOS: the '
                              f'plain order): {len(timing)} updates == model, write-once.')
            if name == 'base' and '--iie' in machines:
                check(work, name, script, '--iie', variant, irq=True)
                print(f'DHGR compositor {name} iie + VIA IRQs every 2,046 cycles: '
                      f'{len(script.updates)} updates == model, no IRQ with RAMRD/RAMWRT on '
                      '(negative control detected).')

if __name__ == '__main__':
    main()
