#!/usr/bin/env python3
"""lib/hgr/hgr_plot_hist.asm in a2run: the fast path (HGR_PLOT_HIST_FAST:
column/mask stepping, a history entry per byte) against the per-pixel one.

A fixture of each variant draws the same batches of lines over a random
backdrop (lit bits the lines must keep and skip) on both pages: every
octant, lengths 0..60 from random starts, the screen's edges and corners,
full-width and full-height lines. After each batch the frame buffers of
the two variants must be bit-identical, and after pl_erase both must be the
backdrop again. Fast variant only: pl_sprite (all seven shifts, rows
clipped at the top and bottom) == backdrop OR the sprite's bits,
pl_erase_to gives back the sprites alone, and a history filled past 255
bytes (lines and sprites cut short) still erases to the backdrop.

    python3 dev/tests/test_hgr_plot_hist.py
"""
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402

TABLE = 0x1000          # a batch: page, lines, sprites (LOWRAM, below PL_HIST)
SPRITE = 0x1400         # the sprite's descriptor and rows
MAXL = 60               # lines a batch
MAXS = 16               # sprites a batch

SRC = '''
PL_HIST = $1800
HGR_PLOT_HIST_ALL = 1
{fast}
.include "hgr_plot_hist.asm"
.code
start:  JSR     hgr_div7_init
        LDA     #0
        STA     pl_n
        STA     pl_n+1
        STA     go
idle:   LDA     go
        BEQ     idle
        LDA     #0
        STA     go
        LDA     {T}
        JSR     pl_page
        LDA     #0
        STA     k
lines:  LDX     k
        CPX     {T}+1
        BEQ     lend
        TXA
        ASL     A
        ASL     A
        TAX
        LDA     {T}+2,X
        STA     pl_x0
        LDA     {T}+3,X
        STA     pl_y0
        LDA     {T}+4,X
        STA     pl_x1
        LDA     {T}+5,X
        STA     pl_y1
        JSR     pl_line
        INC     k
        JMP     lines
lend:   LDX     pl_cur
        LDA     pl_n,X
        STA     mark
        STA     res
.ifdef HGR_PLOT_HIST_FAST
        LDA     #0
        STA     k
sprs:   LDX     k
        CPX     {T}+242
        BEQ     send
        TXA
        ASL     A
        TAX
        LDA     {T}+243,X
        STA     pl_x
        LDA     {T}+244,X
        STA     pl_y
        LDA     #<{S}
        STA     pl_sp
        LDA     #>{S}
        STA     pl_sp+1
        JSR     pl_sprite
        INC     k
        JMP     sprs
send:   LDX     pl_cur
        LDA     pl_n,X
        STA     res+1
.endif
drawn:  NOP
.ifdef HGR_PLOT_HIST_FAST
        LDA     mark
        JSR     pl_erase_to
.endif
marked: NOP
        JSR     pl_erase
erased: NOP
        JMP     idle
.bss
go:     .res 1
k:      .res 1
mark:   .res 1
res:    .res 2
.include "hgr_plot_hist.asm"            ; again: the routines referenced since
.code
.include "hgr_div7_ram.asm"
.segment "RODATA"
.include "hgr_scanline.inc"
.export start, idle, drawn, marked, erased, go, res
'''


def build(work, fast):
    name = 'fast' if fast else 'slow'
    src = SRC.format(fast='HGR_PLOT_HIST_FAST = 1' if fast else '', T=f'${TABLE:04X}', S=f'${SPRITE:04X}')
    (work / f'{name}.s').write_text(src)
    inc = ['-I', str(ROOT / 'dev/lib/hgr'), '-I', str(ROOT / 'dev/lib/apple2')]
    subprocess.run(['ca65', '-t', 'none'] + inc + ['-l', str(work / f'{name}.lst'), '-o', str(work / f'{name}.o'),
                    str(work / f'{name}.s')], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / f'{name}.lbl'),
                    '-o', str(work / f'{name}.bin'), str(work / f'{name}.o')], check=True)
    return work / f'{name}.bin', a2test.labels(work / f'{name}.lbl')


def pixels(x0, y0, x1, y1):
    """The reference: pl_line's Bresenham (dominant axis, both ends)."""
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx, sy = (1 if x1 >= x0 else -1), (1 if y1 >= y0 else -1)
    x, y, out = x0, y0, [(x0, y0)]
    if dy >= dx:
        err = dy >> 1
        for _ in range(dy):
            y += sy
            err += dx
            if err > 255 or (err & 255) >= dy:
                err = (err - dy) & 255
                x += sx
            out.append((x, y))
    else:
        err = dx >> 1
        for _ in range(dx):
            x += sx
            err += dy
            if err > 255 or (err & 255) >= dx:
                err = (err - dx) & 255
                y += sy
            out.append((x, y))
    return out


def batches(rng):
    """Batches of lines of at most 255 pixels together (the per-pixel
    variant's history): [(page, [lines])]."""
    lines = []
    for n in range(0, MAXL + 1):                       # every octant, lengths 0..60
        for ax, ay in [(1, 0), (4, 1), (2, 1), (4, 3), (1, 1), (3, 4), (1, 2), (1, 4), (0, 1)]:
            for sx in (1, -1):
                for sy in (1, -1):
                    dx, dy = sx * n * ax // max(ax, ay), sy * n * ay // max(ax, ay)
                    x0 = rng.randrange(max(0, -dx), 256 - max(0, dx))
                    y0 = rng.randrange(max(0, -dy), 192 - max(0, dy))
                    lines.append((x0, y0, x0 + dx, y0 + dy))
    for _ in range(300):                               # random lengths and slopes
        x0, x1 = rng.randrange(256), rng.randrange(256)
        y0, y1 = rng.randrange(192), rng.randrange(192)
        if max(abs(x1 - x0), abs(y1 - y0)) < 120:
            lines.append((x0, y0, x1, y1))
    edges = [(0, 0, 0, 0), (255, 191, 255, 191), (0, 191, 0, 191), (255, 0, 255, 0),
             (0, 0, 0, 191), (255, 191, 255, 0), (1, 0, 255, 0), (254, 191, 0, 191),
             (0, 0, 191, 191), (255, 0, 64, 191), (0, 191, 254, 0), (255, 191, 0, 0),
             (0, 5, 255, 6), (255, 100, 0, 99), (6, 0, 7, 191), (250, 191, 249, 0),
             (6, 10, 7, 10), (7, 10, 6, 10), (13, 20, 14, 20), (14, 20, 13, 20), (34, 30, 36, 30)]
    rng.shuffle(lines)
    out, cur, npx, page = [], [], 0, 0
    for ln in edges + lines:
        px = len(pixels(*ln))
        if cur and (npx + px > 255 or len(cur) == MAXL):
            out.append((page, cur))
            page ^= 1
            cur, npx = [], 0
        cur.append(ln)
        npx += px
    out.append((page, cur))
    return out


def sprite_rows(rng):
    """A 2-byte, 9-row sprite (a 10-pixel ring-ish shape, random holes)."""
    rows = [rng.getrandbits(10) | 1 << rng.randrange(10) for _ in range(9)]
    rows[4] = 0
    return rows


def sprite_bytes(rows, shift, w=3):
    return [((r << shift) >> (7 * b)) & 0x7F for r in rows for b in range(w)]


def descriptor(rows, w=3):
    data = []
    addrs = []
    base = SPRITE + 2 + 14
    for s in range(7):
        addrs += [(base + len(data)) & 0xFF, (base + len(data)) >> 8]
        data += sprite_bytes(rows, s, w)
    return bytes([w, len(rows)] + addrs + data)


def table(page, lines, sprites=()):
    t = bytearray(256 + 2 * MAXS)
    t[0], t[1] = page, len(lines)
    for i, ln in enumerate(lines):
        t[2 + 4 * i:6 + 4 * i] = bytes(ln)
    t[242] = len(sprites)
    for i, (x, y) in enumerate(sprites):
        t[243 + 2 * i:245 + 2 * i] = bytes([x, y])
    return bytes(t)


def run_batches(work, binary, lab, bd, jobs, tag):
    """jobs: [(page, lines, sprites)]. Dumps (drawn, marked, erased) and res
    for each."""
    steps = [f'load:{bd}@2000', f'load:{bd}@4000'] + a2test.bin_steps(binary, start=lab['start']) + [lab.until('idle', 50)]
    for i, (page, lines, sprites) in enumerate(jobs):
        f = work / f'{tag}{i}.bin'
        f.write_bytes(table(page, lines, sprites))
        base = 0x2000 + 0x2000 * page
        steps += [f'load:{f}@{TABLE:04X}', lab.poke('go', 1), lab.until('drawn', 50), lab.peek('res', 2),
                  f'peek:{base:04X}:8192', lab.until('marked', 50), f'peek:{base:04X}:8192',
                  lab.until('erased', 50), f'peek:{base:04X}:8192', lab.until('idle', 50)]
    r = a2test.run(None, steps, timeout=600)
    d = r.dumps                                        # res, drawn, marked, erased
    assert len(d) == 4 * len(jobs), f'{len(d)} dumps for {len(jobs)} batches'
    return [[d[4 * i + 1], d[4 * i + 2], d[4 * i + 3], d[4 * i]] for i in range(len(jobs))]


def paint(screen, pts):
    s = bytearray(screen)
    for x, y in pts:
        s[hgr_offset(y) + x // 7] |= 1 << (x % 7)
    return bytes(s)


def main():
    rng = random.Random(1979)
    backdrop = bytes(rng.getrandbits(8) & rng.getrandbits(8) & rng.getrandbits(8) & 0x7F
                     if (a % 128) < 120 else 0 for a in range(0x2000))
    with tempfile.TemporaryDirectory(prefix='plh-') as tmp:
        work = Path(tmp)
        (work / 'bd.bin').write_bytes(backdrop)
        slow_bin, slow_lab = build(work, False)
        fast_bin, fast_lab = build(work, True)
        jobs = [(page, lines, ()) for page, lines in batches(rng)]
        slow = run_batches(work, slow_bin, slow_lab, work / 'bd.bin', jobs, 's')
        fast = run_batches(work, fast_bin, fast_lab, work / 'bd.bin', jobs, 'f')
        nlines = npx = 0
        entries_slow = entries_fast = 0
        for i, ((page, lines, _), a, b) in enumerate(zip(jobs, slow, fast)):
            ref = backdrop
            for ln in lines:
                ref = paint(ref, pixels(*ln))
            assert a[0] == ref, f'batch {i}: the per-pixel pl_line is not the reference'
            assert b[0] == a[0], f'batch {i} (page {page + 1}): fast != per-pixel ({lines})'
            assert a[2] == backdrop and b[2] == backdrop, f'batch {i}: erase left a mark'
            nlines += len(lines)
            npx += sum(len(pixels(*ln)) for ln in lines)
            entries_slow += a[3][0]
            entries_fast += b[3][0]
        # pl_sprite + pl_erase_to, and a history filled past its end (fast only)
        rows = sprite_rows(rng)
        (work / 'spr.bin').write_bytes(descriptor(rows))
        sjobs = []
        for i in range(12):
            lines = [ln for ln in batches(rng)[i][1] if len(pixels(*ln)) < 30][:4]
            sprites = [(rng.randrange(0, 256 - 21), rng.randrange(0, 192 - 9)) for _ in range(4)]
            sprites += [(7 * i + i % 7, 187), (7 * i + 6 - i % 7, 252)]        # clipped rows
            sjobs.append((i & 1, lines, sprites))
        full = [(0, 0, 255, 191), (255, 0, 0, 191), (0, 191, 255, 0), (3, 0, 4, 191), (200, 0, 201, 191)] + \
               [(0, y, 255, y + 3) for y in range(0, 190, 7)]
        sjobs.append((1, full[:MAXL], [(rng.randrange(230), rng.randrange(180)) for _ in range(MAXS)]))
        sjobs.append((0, full[:3], [(rng.randrange(230), rng.randrange(180)) for _ in range(MAXS)]))
        steps_pre = [f'load:{work / "spr.bin"}@{SPRITE:04X}']
        orig_run = a2test.run

        def run_with_sprite(disk, steps, **kw):
            return orig_run(disk, steps_pre + steps, **kw)
        a2test.run = run_with_sprite
        try:
            sres = run_batches(work, fast_bin, fast_lab, work / 'bd.bin', sjobs, 'p')
        finally:
            a2test.run = orig_run
        nspr = 0
        for i, ((page, lines, sprites), d) in enumerate(zip(sjobs, sres)):
            assert d[2] == backdrop, f'sprite batch {i}: erase left a mark'
            if i >= 12:
                assert d[3][1] >= 255 - 3, f'full batch {i}: history {d[3][1]} entries, not full'
                continue
            assert d[3][1] < 255, f'sprite batch {i}: the history filled up'
            ref = backdrop
            for ln in lines:
                ref = paint(ref, pixels(*ln))
            assert d[1] == ref, f'sprite batch {i}: pl_erase_to did not give back the sprites alone'
            pts = []
            for x, y in sprites:
                for r, bits in enumerate(rows):
                    yy = (y + r) & 255
                    if yy < 192:
                        pts += [(x + c, yy) for c in range(10) if bits >> c & 1]
            assert d[0] == paint(ref, pts), f'sprite batch {i}: pl_sprite != backdrop OR its bits'
            nspr += len(sprites)
    print(f'hgr_plot_hist: {nlines} lines ({npx} pixels, {len(jobs)} batches, both pages) fast == per-pixel '
          f'== reference, history {entries_slow} -> {entries_fast} entries; {nspr} sprites (7 shifts, '
          f'clipped rows), pl_erase_to, a full history: erase == backdrop.')


if __name__ == '__main__':
    main()
