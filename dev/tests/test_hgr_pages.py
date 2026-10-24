#!/usr/bin/env python3
"""hgr_pages (draw page by patched operands) with hgr_line8: lines drawn on
page 1 then page 2 through hgr_select_page, the program's own site follows
too; built with and without HGR_LINE_DIV7/MOD7. Exact pixels, nothing else
touched."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(ROOT / 'dev/tests'))
import a2test  # noqa: E402

LINES = {0: [(0, 0, 255, 191), (255, 0, 0, 191), (3, 180, 8, 1), (100, 50, 228, 60)],
         1: [(20, 191, 20, 0), (255, 191, 255, 191), (0, 100, 255, 100), (7, 7, 13, 150)]}


def reference_line(x0, y0, x1, y1):
    if x1 < x0:
        x0, y0, x1, y1 = x1, y1, x0, y0
    dx, dy = x1 - x0, abs(y1 - y0)
    sy = 1 if y1 >= y0 else -1
    major, minor = max(dx, dy), min(dx, dy)
    error, pixels = major // 2, []
    for n in range(major + 1):
        pixels.append((x0, y0))
        if n == major:
            break
        if dx >= dy:
            x0 += 1
        else:
            y0 += sy
        error -= minor
        if error < 0:
            error += major
            if dx >= dy:
                y0 += sy
            else:
                x0 += 1
    return pixels


def put(**values):
    return ''.join(f'        LDA #{v}\n        STA {k}\n' for k, v in values.items())


def build(work, div7):
    body = ''
    for page, lines in LINES.items():
        body += f'        LDA #{page}\n        JSR hgr_select_page\n'
        body += f'        LDY #100\n        HGR_HI_SITE\n        LDX hgr_hi,Y\n        STX res+{page}\n'
        for x0, y0, x1, y1 in lines:
            body += put(hl_ln_x0=x0, hl_ln_y0=y0, hl_ln_x1=x1, hl_ln_y1=y1) + '        JSR hgr_line8\n'
    tables = ''
    if div7:
        tables = '''HGR_LINE_DIV7 = div7
HGR_LINE_MOD7 = mod7
.rodata
div7:
.repeat 256, I
.byte I / 7
.endrepeat
mod7:
.repeat 256, I
.byte I .mod 7
.endrepeat
.code
'''
    src = f'''.include "apple2.inc"
.include "hgr_pages.inc"
.globalzp hl_ln_x0, hl_ln_y0, hl_ln_x1, hl_ln_y1
.code
        LDA     #0
        TAY
        LDX     #$40
@c:     STA     $2000,Y                 ; clear both pages
        INY
        BNE     @c
        INC     @c+2
        DEX
        BNE     @c
        JSR     hgr_pages_init
{body}done:   JMP     done
.bss
res:    .res 2
.code
{tables}.include "hgr_line.asm"
.include "hgr_pages.asm"
.rodata
.include "hgr_scanline.inc"
.export done, res
'''
    (work / 'p.s').write_text(src)
    subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/hgr'), '-I', str(ROOT / 'dev/lib/apple2'),
                    '-o', str(work / 'p.o'), str(work / 'p.s')], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / 'p.lbl'),
                    '-o', str(work / 'p.bin'), str(work / 'p.o')], check=True)
    return a2test.labels(work / 'p.lbl'), work / 'p.bin'


def main():
    want = bytearray(16384)
    for page, lines in LINES.items():
        for line in lines:
            for x, y in reference_line(*line):
                want[page * 8192 + a2test.hgr_offset(y) + x // 7] |= 1 << (x % 7)
    for div7 in (False, True):
        with tempfile.TemporaryDirectory(prefix='hgr-pages-') as tmp:
            L, fixture = build(Path(tmp), div7)
            r = a2test.run(None, a2test.bin_steps(fixture) + [L.until('done', 4000), L.peek('res', 2), 'peek:2000:16384'])
            label = 'div7 tables' if div7 else 'division loop'
            assert r.mem(L['res'], 2) == bytes([0x20 + (a2test.hgr_offset(100) >> 8), 0x40 + (a2test.hgr_offset(100) >> 8)]), f'{label}: own site {r.mem(L["res"], 2).hex()}'
            got = r.mem(0x2000, 16384)
            for page in (0, 1):
                part = slice(page * 8192, page * 8192 + 8192)
                assert got[part] == bytes(want[part]), f'{label}: page {page + 1} raster'
    print('HGR pages: hgr_select_page patches hgr_line8 and program sites, exact lines on '
          'both pages, with and without div7/mod7 tables.')


if __name__ == '__main__':
    main()
