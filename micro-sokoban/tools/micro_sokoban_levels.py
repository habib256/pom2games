#!/usr/bin/env python3
"""micro_sokoban_levels.py -- XSB level collections -> MICRO-SOKOBAN disk packs.

    micro_sokoban_levels.py --out build [--solutions levels/solutions.txt --demo I:1,I:7]
                      MB1:I:levels/microban.xsb  [MB2:II:levels/microban2.xsb]

Each argument is PREFIX:HUD:FILE -- the pack file prefix on the disk (MB1 ->
MB1A, MB1B, ...), the collection name shown in the HUD (roman numerals, drawn
with the game font) and the XSB file.

A level is kept when it fits the screen without scrolling:
  - 20 x 12 tiles at most (after cropping to its walls),
  - and a placement exists that leaves the HUD cells outside the walls: three
    tiles in each screen corner (rows 0 and 11, columns 0-2 and 17-19), four
    bottom left (columns 0-3: the level name, "III:056", is 7 glyphs).
The placement closest to the centre wins. A level that does not fit upright
but fits once turned a quarter clockwise (9 x 13 -> 13 x 9) is kept turned:
the puzzle and its solution are the same, rotated. Everything else is
reported and left out; the original level numbers are kept for the HUD and
the report, which also lists the turned levels.

Outputs in --out:
  levels.inc     ca65 tables: collections, packs, original numbers
  <PACK>.bin     one per pack, BLOADed at $1000 (LOWBSS, 4 KB):
                   byte n, n offset lows, n offset highs (from the pack start),
                   then per level: w, h, row, col, runs.
                 A run is one byte: tile type << 5 | (length - 1), in row-major
                 order over the w x h box; the tile types are the game's
                 TILE_* codes (0 floor/outside, 1 wall, 2 target, 3 box,
                 4 box on target, 5 player, 6 player on target).
  microsave.bin   the empty save file: "SOK2", last collection and level
                 solved, one 16-bit fingerprint per collection, then 4 bytes
                 per kept level (best moves, best pushes; 0 = unsolved)
  microhof.bin    HOF3 ranking, ten profile names, active slot and options (120 bytes)
  tutorial.inc   five inline teaching levels and their hints
  packs.args     the --bin arguments for dos33.py
  report.txt     what was kept and what was left out, and why

--demo lists the levels (HUD:original number) the title-screen demo plays,
with their solutions from --solutions (tools/make_solutions.py), packed
four moves a byte into levels.inc (demo_* tables, DIR_* codes: up, down,
left, right = 0-3, first move in the low bits).
"""
import argparse
import os
import sys

COLS, ROWS = 20, 12
HUD_CELLS = ([(0, c) for c in (0, 1, 2, COLS - 3, COLS - 2, COLS - 1)] +
             [(ROWS - 1, c) for c in (0, 1, 2, 3, COLS - 3, COLS - 2, COLS - 1)])
PACK_MAX = 2048  # upper half of LOWRAM holds the active profile's records
PACK_ADDR = 0x1000
TILE = {' ': 0, '#': 1, '.': 2, '$': 3, '*': 4, '@': 5, '+': 6}
SAVE_MAGIC = b'SOK2'


def crc16(data, crc=0xFFFF):
    """CRC-16/CCITT-FALSE."""
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


def fingerprint(kept):
    """16 bits that change when the kept levels of a collection change:
    which levels (original numbers), their order, cells, turn and placement.
    The save file keeps one per collection; the game wipes the records of a
    collection whose fingerprint differs (they would land on wrong levels)."""
    crc = 0xFFFF
    for num, data in kept:
        crc = crc16(bytes([num & 0xFF, num >> 8, len(data) & 0xFF]) + data, crc)
    return crc


def parse_xsb(path):
    """Return [(number, title, rows)], numbered in file order from 1."""
    levels, cur, titles = [], [], []
    with open(path, encoding='latin-1') as f:
        lines = f.read().splitlines() + ['']
    for line in lines:
        body = line.rstrip()
        if body and set(body) <= set('#@$.*+ -_') and '#' in body:
            cur.append(body.replace('-', ' ').replace('_', ' '))
            continue
        if cur:
            levels.append((len(levels) + 1, ' / '.join(titles), cur))
            cur, titles = [], []
        if body.startswith(';'):
            titles.append(body[1:].strip())
        elif body:
            titles.append(body.strip())
    return levels


def analyse(rows):
    """Crop, find the outside (flood fill from the border through spaces)."""
    h = len(rows)
    w = max(len(r) for r in rows)
    grid = [r.ljust(w) for r in rows]
    outside = [[False] * w for _ in range(h)]
    stack = [(y, x) for y in range(h) for x in range(w)
             if (y in (0, h - 1) or x in (0, w - 1)) and grid[y][x] == ' ']
    for y, x in stack:
        outside[y][x] = True
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and not outside[yy][xx] and grid[yy][xx] == ' ':
                outside[yy][xx] = True
                stack.append((yy, xx))
    return grid, outside, w, h


def place(outside, w, h):
    """(row, col) of the top-left corner, or None."""
    if w > COLS or h > ROWS:
        return None
    rows = sorted(range(ROWS - h + 1), key=lambda r: (abs(2 * r + h - ROWS), r))
    cols = sorted(range(COLS - w + 1), key=lambda c: (abs(2 * c + w - COLS), c))
    for r0 in rows:
        for c0 in cols:
            if all(not (0 <= r - r0 < h and 0 <= c - c0 < w) or outside[r - r0][c - c0]
                   for r, c in HUD_CELLS):
                return r0, c0
    return None


def rotate(rows):
    """The rows turned a quarter clockwise."""
    w = max(len(r) for r in rows)
    grid = [r.ljust(w) for r in rows]
    return [''.join(grid[len(grid) - 1 - y][x] for y in range(len(grid))).rstrip() for x in range(w)]


def fit(rows):
    """How a level goes on screen: (grid, outside, w, h, pos, turned, why).
    pos is None and why says why when it does not fit, upright or turned."""
    grid, outside, w, h = analyse(rows)
    why = check(grid)
    if why:
        return grid, outside, w, h, None, False, why
    pos = place(outside, w, h)
    if pos:
        return grid, outside, w, h, pos, False, None
    g2, o2, w2, h2 = analyse(rotate(rows))
    pos2 = place(o2, w2, h2)
    if pos2:
        return g2, o2, w2, h2, pos2, True, None
    if w > COLS or h > ROWS:
        why = '%dx%d, larger than %dx%d (turned too)' % (w, h, COLS, ROWS)
    else:
        why = '%dx%d, no placement clear of the HUD corners (turned either)' % (w, h)
    return grid, outside, w, h, None, False, why


def kept_levels(path):
    """[(number, grid)] of the levels of an XSB file the game keeps, as drawn."""
    out = []
    for num, title, rows in parse_xsb(path):
        grid, _, _, _, pos, _, _ = fit(rows)
        if pos:
            out.append((num, grid))
    return out


def encode(grid, outside, w, h, r0, c0):
    cells = [0 if outside[y][x] else TILE[grid[y][x]] for y in range(h) for x in range(w)]
    runs, i = [], 0
    while i < len(cells):
        j = i
        while j < len(cells) and cells[j] == cells[i] and j - i < 32:
            j += 1
        runs.append((cells[i] << 5) | (j - i - 1))
        i = j
    return bytes([w, h, r0, c0] + runs)


def check(grid):
    flat = ''.join(grid)
    players = flat.count('@') + flat.count('+')
    boxes = flat.count('$') + flat.count('*')
    targets = flat.count('.') + flat.count('+') + flat.count('*')
    if players != 1:
        return 'expects one player, has %d' % players
    if boxes != targets or boxes == 0:
        return '%d boxes for %d targets' % (boxes, targets)
    if boxes - flat.count('*') > 255:
        return 'too many boxes'
    return None


def demo_tables(a, colls):
    """levels.inc lines for the title-screen demo."""
    wanted = [d.split(':') for d in a.demo.split(',') if d]
    sols = {}
    if wanted:
        for row in open(a.solutions):
            if row.strip() and not row.startswith(';'):
                hud, num, _, moves = row.split()
                sols[(hud, int(num))] = moves.lower()
    L = ['', 'DEMO_COUNT = %d' % len(wanted)]
    cs, ls, lens, data = [], [], [], []
    for k, (hud, num) in enumerate(wanted):
        num = int(num)
        ci = next(i for i, c in enumerate(colls) if c['hud'] == hud)
        rank = [n for n, _ in colls[ci]['kept']].index(num)
        moves = sols[(hud, num)]
        codes = ['udlr'.index(m) for m in moves]
        packed = [sum(c << (2 * j) for j, c in enumerate(codes[i:i + 4])) for i in range(0, len(codes), 4)]
        cs.append(ci)
        ls.append(rank)
        lens.append(len(codes))
        data.append('demo_%d:          ; %s:%d, %d moves' % (k, hud, num, len(codes)))
        for i in range(0, len(packed), 16):
            data.append('        .byte %s' % ', '.join('$%02X' % b for b in packed[i:i + 16]))
    if wanted:
        L.append('demo_coll:       .byte %s' % ', '.join(map(str, cs)))
        L.append('demo_lvl:        .byte %s' % ', '.join(map(str, ls)))
        L.append('demo_len_lo:     .byte %s' % ', '.join('<%d' % n for n in lens))
        L.append('demo_len_hi:     .byte %s' % ', '.join('>%d' % n for n in lens))
        L.append('demo_ptr_lo:     .byte %s' % ', '.join('<demo_%d' % k for k in range(len(wanted))))
        L.append('demo_ptr_hi:     .byte %s' % ', '.join('>demo_%d' % k for k in range(len(wanted))))
        L.extend(data)
    return L


def make_packs(prefix, records):
    """Split [(orig, data)] into packs of at most PACK_MAX bytes."""
    packs, cur, size = [], [], 1
    for rec in records:
        need = 2 + len(rec[1])
        if cur and size + need > PACK_MAX:
            packs.append(cur)
            cur, size = [], 1
        cur.append(rec)
        size += need
    if cur:
        packs.append(cur)
    if len(packs) > 26:
        sys.exit('%s: too many packs' % prefix)
    out = []
    for k, levels in enumerate(packs):
        n = len(levels)
        offs, body, off = [], b'', 1 + 2 * n
        for _, data in levels:
            offs.append(off)
            body += data
            off += len(data)
        blob = bytes([n]) + bytes(o & 0xFF for o in offs) + bytes(o >> 8 for o in offs) + body
        assert len(blob) <= PACK_MAX
        out.append(('%s%c' % (prefix, ord('A') + k), levels, blob))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    ap.add_argument('--solutions')
    ap.add_argument('--demo', default='')
    ap.add_argument('collections', nargs='+', help='PREFIX:HUD:FILE')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    colls, report = [], []
    for spec in a.collections:
        prefix, hud, path = spec.split(':', 2)
        levels = parse_xsb(path)
        kept, dropped, turned = [], [], []
        for num, title, rows in levels:
            grid, outside, w, h, pos, rot, why = fit(rows)
            if why:
                dropped.append((num, title, why))
                continue
            if rot:
                turned.append(num)
            kept.append((num, encode(grid, outside, w, h, *pos)))
        packs = make_packs(prefix, kept)
        colls.append(dict(prefix=prefix, hud=hud, path=path, total=len(levels),
                          kept=kept, dropped=dropped, packs=packs))
        report.append('%s (%s): %d levels, %d kept (%d turned), %d left out, %d bytes in %d packs'
                      % (path, hud, len(levels), len(kept), len(turned), len(dropped),
                         sum(len(p[2]) for p in packs), len(packs)))
        if turned:
            report.append('  turned a quarter clockwise: %s' % ', '.join(map(str, turned)))
        for num, title, why in dropped:
            report.append('  - level %d%s: %s' % (num, ' (%s)' % title if title and title != str(num) else '', why))

    total = sum(len(c['kept']) for c in colls)
    save_hdr = len(SAVE_MAGIC) + 2 + 2 * len(colls)
    record_len = save_hdr + 4 * total
    save_len = record_len + 134
    for c in colls:
        c['fp'] = fingerprint(c['kept'])

    # --- pack files, dos33.py arguments, empty save ---
    args = []
    for c in colls:
        for name, _, blob in c['packs']:
            with open(os.path.join(a.out, name + '.bin'), 'wb') as f:
                f.write(blob)
            args.append('--bin %s=%s@0x%04X' % (name, os.path.join(a.out, name + '.bin'), PACK_ADDR))
    with open(os.path.join(a.out, 'microsave.bin'), 'wb') as f:
        hdr = SAVE_MAGIC + bytes(2) + b''.join(bytes([c['fp'] & 0xFF, c['fp'] >> 8]) for c in colls)
        f.write(hdr + bytes(save_len - len(hdr)))
    # Independent of level fingerprints and the existing SOK2 record slots:
    # magic, active initials, 10 entries (initials + move total + solved (bit 15 carries sum bit 24)).
    with open(os.path.join(a.out, 'microhof.bin'), 'wb') as f:
        f.write(b'HOF3GIS' + bytes(10 * 8) + bytes([2, 1]) + b'GIS' + bytes(27) + bytes([0]))
    # The five tiny teaching levels are inline, independent of Microban
    # fingerprints and score records. This keeps existing saves compatible.
    tutorial_path = os.path.join(os.path.dirname(__file__), '..', 'levels', 'tutorial.xsb')
    tutorial = parse_xsb(tutorial_path)
    assert len(tutorial) == 5
    lines = ['.rodata']
    for label, prefix in [('tutorial_ptr', 'tutorial'), ('tutorial_hint', 'tutorial_hint')]:
        for suffix, op in [('lo', '<'), ('hi', '>')]:
            lines.append(label + '_' + suffix + ': .byte ' + ', '.join(
                op + prefix + str(i) for i in range(5)))
    for i, (_, hint, rows) in enumerate(tutorial):
        grid, outside, w, h = analyse(rows)
        data = encode(grid, outside, w, h, 4 + (6 - h) // 2, (20 - w) // 2)
        lines.append('tutorial%d: .byte ' % i + ', '.join('$%02X' % b for b in data))
        lines.append('tutorial_hint%d: GSTR "%s"' % (i, hint))
    with open(os.path.join(a.out, 'tutorial.inc'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    with open(os.path.join(a.out, 'packs.args'), 'w') as f:
        f.write(' '.join(args) + '\n')

    # --- ca65 tables ---
    L = ['; levels.inc -- generated by tools/micro_sokoban_levels.py from %s. Do not edit.'
         % ', '.join(c['path'] for c in colls), '']
    L.append('NUM_COLLS    = %d' % len(colls))
    L.append('NUM_PACKS    = %d' % sum(len(c['packs']) for c in colls))
    L.append('TOTAL_LEVELS = %d' % total)
    L.append('PACK_ADDR    = $%04X' % PACK_ADDR)
    L.append('PACK_MAX     = %d' % PACK_MAX)
    L.append('SAVE_HDR     = %d            ; "SOK2", last collection, last level, then one' % save_hdr)
    L.append('                            ; fingerprint per collection (lo, hi)')
    L.append('RECORD_LEN   = %d' % record_len)
    L.append('SAVE_LEN     = %d          ; then per level: best moves, best pushes (0 = unsolved)' % save_len)
    L.append('')
    if len(colls) == 1:
        title = 'MICROBAN %d LEVELS' % total
    else:
        title = 'MICROBAN %s %d LEVELS' % ('+'.join(c['hud'] for c in colls), total)
    if len(title) > 20:
        title = '%d LEVELS' % total
    L.append('.macro LEVELS_TITLE')
    L.append('        GSTR "%s"' % title)
    L.append('.endmacro')
    L.append('LEVELS_TITLE_COL = %d        ; centred: 14-pixel glyphs' % (20 - len(title)))
    L.append('')
    L.append('.rodata')
    L.append('coll_count:      .byte %s' % ', '.join(str(len(c['kept'])) for c in colls))
    base, bases, first, firsts = 0, [], 0, []
    for c in colls:
        bases.append(base)
        base += len(c['kept'])
        firsts.append(first)
        first += len(c['packs'])
    L.append('coll_base_lo:    .byte %s      ; first save slot of the collection' % ', '.join('<%d' % b for b in bases))
    L.append('coll_base_hi:    .byte %s' % ', '.join('>%d' % b for b in bases))
    L.append('coll_first_pack: .byte %s' % ', '.join(str(f) for f in firsts))
    L.append('coll_npacks:     .byte %s' % ', '.join(str(len(c['packs'])) for c in colls))
    L.append('coll_fp_lo:      .byte %s      ; fingerprints of the kept levels' % ', '.join('$%02X' % (c['fp'] & 0xFF) for c in colls))
    L.append('coll_fp_hi:      .byte %s' % ', '.join('$%02X' % (c['fp'] >> 8) for c in colls))
    L.append('coll_orig_lo:    .byte %s' % ', '.join('<orig_%d' % i for i in range(len(colls))))
    L.append('coll_orig_hi:    .byte %s' % ', '.join('>orig_%d' % i for i in range(len(colls))))
    L.append('coll_hud_lo:     .byte %s' % ', '.join('<coll_hud_%d' % i for i in range(len(colls))))
    L.append('coll_hud_hi:     .byte %s' % ', '.join('>coll_hud_%d' % i for i in range(len(colls))))
    pf, pc, pn = [], [], []
    for c in colls:
        for name, levels, _ in c['packs']:
            pf.append(sum(len(p[1]) for p in c['packs'][:[p[0] for p in c['packs']].index(name)]))
            pc.append(len(levels))
            pn.append(name)
    L.append('pack_first:      .byte %s      ; first level (in its collection)' % ', '.join(map(str, pf)))
    L.append('pack_count:      .byte %s' % ', '.join(map(str, pc)))
    L.append('pack_name_lo:    .byte %s' % ', '.join('<pack_name_%d' % i for i in range(len(pn))))
    L.append('pack_name_hi:    .byte %s' % ', '.join('>pack_name_%d' % i for i in range(len(pn))))
    for i, n in enumerate(pn):
        L.append('pack_name_%d:     .byte "%s", 0' % (i, n))
    glyph = {'I': 29, 'V': 11, 'X': 35}     # the game font (bbfont_subset.inc)
    for i, c in enumerate(colls):
        if not set(c['hud']) <= set(glyph):
            sys.exit('HUD name %r: roman numerals I, V, X only' % c['hud'])
        if len(c['hud']) > 3:
            sys.exit('HUD name %r: 3 letters at most (with ":NNN", 4 tiles)' % c['hud'])
        L.append('coll_hud_%d:      .byte %s, $FF   ; "%s"'
                 % (i, ', '.join(str(glyph[ch]) for ch in c['hud']), c['hud']))
    for i, c in enumerate(colls):
        nums = [num for num, _ in c['kept']]
        L.append('orig_%d:          ; original level numbers' % i)
        for k in range(0, len(nums), 16):
            L.append('        .byte %s' % ', '.join(str(n) for n in nums[k:k + 16]))
    L.extend(demo_tables(a, colls))
    with open(os.path.join(a.out, 'levels.inc'), 'w') as f:
        f.write('\n'.join(L) + '\n')

    with open(os.path.join(a.out, 'report.txt'), 'w') as f:
        f.write('\n'.join(report) + '\n')
    print('\n'.join(report))


if __name__ == '__main__':
    main()
