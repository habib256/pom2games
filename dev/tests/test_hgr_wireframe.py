#!/usr/bin/env python3
"""Execute the standalone wireframe library and compare every framebuffer byte."""
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test


def put(**values):
    return ''.join(f' LDA #{value}\n STA {name}\n' for name, value in values.items())


def edges(rect, window):
    x0, y0, x1, y1 = rect
    left, right = window
    if left > right:
        return []
    candidates = [(x0, y0, x1, y0), (x0, y1, x1, y1),
                  (x0, y0, x0, y1), (x1, y0, x1, y1)]
    return [(max(a, left), b, min(c, right), d) for a, b, c, d in candidates
            if c >= left and a <= right]


def paint(memory, base, line, draw):
    x0, y0, x1, y1 = line
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            address = base + a2test.hgr_offset(y) + x // 7
            mask = 1 << (x % 7)
            if draw:
                memory[address] |= mask
            else:
                memory[address] &= ~mask


def check(work, page):
    cases = [((0, 0, 255, 191), (0, 255)), ((3, 2, 4, 8), (0, 255)),
             ((6, 20, 7, 30), (0, 255)), ((254, 190, 255, 191), (0, 255)),
             ((70, 79, 70, 79), (70, 70)), ((3, 24, 201, 24), (8, 193)),
             ((10, 20, 120, 90), (30, 100)), ((10, 20, 120, 90), (121, 255)),
             ((10, 20, 120, 90), (100, 30)), ((10, 20, 120, 90), (0, 9))]
    rng = random.Random(0xF17)
    for _ in range(30):
        x, y = rng.randrange(256), rng.randrange(192)
        left = rng.randrange(256)
        cases.append(((x, y, rng.randrange(x, 256), rng.randrange(y, 192)),
                      (left, rng.randrange(left, 256))))
    body = f' LDA #{page}\n JSR hgr_set_draw_page\n'
    expected = []
    stops = []
    base = 8192 if page else 0
    for index, (rect, window) in enumerate(cases):
        lines = edges(rect, window)
        # The history deliberately crosses a page boundary.
        body += ' JSR fill\n' + put(wf_history=0xFE, **{'wf_history+1': 0x10},
                    wf_x0=rect[0], wf_y0=rect[1], wf_x1=rect[2], wf_y1=rect[3],
                    wf_clip_left=window[0], wf_clip_right=window[1])
        body += f' JSR hgr_wire_rect\ndrawn_{index}:\n NOP\n'
        body += put(wf_history=0xFE, **{'wf_history+1': 0x10}, wf_count=len(lines))
        body += f' JSR hgr_wire_erase\nerased_{index}:\n NOP\n'
        image = bytearray([0x55] * 16384)
        for line in lines:
            paint(image, base, line, True)
        expected.append(bytes(image))
        for line in lines:
            paint(image, base, line, False)
        expected.append(bytes(image))
        stops += [f'drawn_{index}', f'erased_{index}']
    source = '.include "apple2.inc"\n.globalzp fill_ptr, wf_x0, wf_y0, wf_x1, wf_y1, wf_history, wf_count, wf_clip_left, wf_clip_right\n.code\nentry:\n' + body + '''
done: JMP done
fill:
 LDA #0
 STA fill_ptr
 LDA #$20
 STA fill_ptr+1
 LDY #0
@byte:
 LDA #$55
 STA (fill_ptr),Y
 INY
 BNE @byte
 INC fill_ptr+1
 LDA fill_ptr+1
 CMP #$60
 BNE @byte
 RTS
.zeropage
fill_ptr: .res 2
.code
.include "hgr_scanline.inc"
.include "hgr_plot_tables.inc"
.include "hgr_flip.asm"
.include "hgr_wireframe.asm"
.include "hgr_wireframe.asm"
'''
    src = work / 'wire.s'
    src.write_text(source)
    cfg = work / 'wire.cfg'
    cfg.write_text('''MEMORY {
 ZP: start=$50, size=$B0, type=rw;
 MAIN: start=$6000, size=$3600, type=rw, file=%O;
}
SEGMENTS {
 ZEROPAGE: load=ZP, type=zp;
 CODE: load=MAIN, type=ro;
 BSS: load=MAIN, type=bss;
}
''')
    obj, binary, lbl = (work / name for name in ('wire.o', 'wire.bin', 'wire.lbl'))
    subprocess.run(['ca65', '-g', '-I', str(ROOT/'dev/lib/apple2'), '-I',
                    str(ROOT/'dev/lib/hgr'), '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(cfg), '-Ln', str(lbl), '-o', str(binary), str(obj)], check=True)
    disk = a2test.build_disk(work, 'WIRE', binary)
    labels = a2test.labels(lbl)
    steps = []
    for name in stops:
        steps += [labels.until(name), 'peek:2000:16384']
    result = a2test.run(disk, steps, emulator=a2test.A2SHOT)
    for index, wanted in enumerate(expected):
        actual = result.dumps[index]
        assert actual == wanted, ('wireframe pixel mismatch', page, cases[index//2],
                                  'draw' if index % 2 == 0 else 'erase')
    print(f'HGR wireframe page {2 if page else 1}: clipping, contours, black line erase, default scratch OK')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='hgr-wire-') as tmp:
        for page in (0, 0x60):
            check(Path(tmp), page)
