#!/usr/bin/env python3
"""Shared OR/XOR kernels and LOGO adapters: raster, palette and clipping."""
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'dev/tools'))
import a2test

PALETTE = [0]*4 + [128]*6 + [0]*6


def reference(page, ends, mode, color, palette):
    x, y, xe, ye = ends
    if x >= 32768: x -= 65536
    if xe >= 32768: xe -= 65536
    dx, dy = abs(xe-x), abs(ye-y)
    sx, sy = (1 if xe >= x else -1), (1 if ye >= y else -1)
    err = dx-dy
    while True:
        if 0 <= x < 280 and 0 <= y < 192:
            addr, mask = a2test.hgr_offset(y)+x//7, 1 << (x % 7)
            if mode:
                page[addr] ^= mask
            else:
                page[addr] |= mask
                if palette: page[addr] = (page[addr] & 127) | PALETTE[color]
        if (x, y) == (xe, ye): return
        e2 = err*2
        if e2 >= -dy: err -= dy; x += sx
        if e2 < dx: err += dx; y += sy


def build(work, adapter):
    # The same fixture drives default library scratch and LOGO's old aliases.
    if adapter:
        names = ['ln_x0','ln_x0h','ln_y0','ln_x1','ln_x1h','ln_y1',
                 'pix_x','pix_xh','pix_y','pen_color','plot_mode']
        imports = '.import line_xy16, plot_set_x16\n.importzp ' + ','.join(names[:-1]) + '\n'
        exports = '.exportzp tmp,tmp2\n.export plot_mode\n.zeropage\ntmp: .res 1\ntmp2: .res 1\n.bss\nplot_mode: .res 1\n'
        library = ''
    else:
        names = ['h16_x0','h16_x0+1','h16_y0','h16_x1','h16_x1+1','h16_y1',
                 'hp_x','hp_x+1','hp_y','unused_color','hp_mode']
        imports = '.globalzp h16_x0,h16_y0,h16_x1,h16_y1,hp_x,hp_y,hp_mode\n'
        exports = '.bss\nunused_color: .res 1\n'
        library = '''.include "hgr_scanline.inc"
HGR_FULL_WIDTH_TABLES = 1
.include "hgr_plot_tables.inc"
.include "hgr_plot.asm"
.include "hgr_line16.asm"
line_xy16 = hgr_line16
plot_set_x16 = hgr_plot16
'''
    source = work/'fixture.s'
    source.write_text(imports+exports+'''.zeropage
fill_ptr: .res 2
.bss
params: .res 11
kind: .res 1
.code
entry:
        cld
ready:
        jsr wait_key
        lda #0
        sta fill_ptr
        lda #$20
        sta fill_ptr+1
        ldy #0
@fill:  lda #$a5
        sta (fill_ptr),y
        iny
        bne @fill
        inc fill_ptr+1
        lda fill_ptr+1
        cmp #$60
        bne @fill
''' + '\n'.join(f'        lda params+{i}\n        sta {name}' for i,name in enumerate(names)) + '''
        lda kind
        bne @point
        jsr line_xy16
        jmp done
@point: jsr plot_set_x16
done:   jmp ready
wait_key:
        lda $c000
        bpl wait_key
        bit $c010
        rts
''' + library)
    cfg = work/'fixture.cfg'
    cfg.write_text('''MEMORY {
 ZP: start=$50,size=$B0,type=rw;
 MAIN: start=$6000,size=$3600,type=rw,file=%O;
}
SEGMENTS {ZEROPAGE: load=ZP,type=zp; CODE: load=MAIN,type=ro; BSS: load=MAIN,type=bss;}
''')
    sources = [source] + ([ROOT/'logo/src/hgr_logom2.asm'] if adapter else [])
    objects = []
    for i, src in enumerate(sources):
        obj = work/f'{i}.o'
        subprocess.run(['ca65','-g','-I',str(ROOT/'dev/lib/apple2'),'-I',str(ROOT/'dev/lib/hgr'),
                        '-o',str(obj),str(src)], check=True)
        objects.append(obj)
    binary = work/'fixture.bin'
    subprocess.run(['ld65','-C',str(cfg),'-Ln',str(work/'fixture.lbl'),'-o',str(binary),
                    *map(str,objects)], check=True)
    return a2test.build_disk(work,'FIXTURE',binary), a2test.labels(work/'fixture.lbl')


def check(work, adapter):
    rng = random.Random(6502)
    lines = [(0,0,279,191),(279,191,0,0),(279,0,0,191),(0,191,279,0),
             (0,80,279,80),(279,0,279,191),(255,20,279,21),(279,21,255,20),
             (1,1,9,5),(9,5,1,1),(256,10,256,10),(270,180,300,210),
             (65531,80,5,84),(5,84,65531,80)]
    lines += [tuple(rng.randrange(limit) for limit in (280,192,280,192)) for _ in range(40)]
    cases = [(0, line, mode, color) for line in lines for mode in (0,1) for color in (4,15)]
    cases += [(0,(255,96,279,100),mode,color) for mode in (0,1) for color in range(16)]
    points = [(0,0),(255,191),(256,0),(279,191),(280,0),(511,0),(65535,95),(1,192),(1,255)]
    cases += [(1,(x,y,x,y),mode,4) for x,y in points for mode in (0,1)]
    disk, labels = build(work, adapter)
    steps = [labels.until('ready')]
    for kind, (x,y,xe,ye), mode, color in cases:
        params = [x&255,x>>8,y,xe&255,xe>>8,ye,x&255,x>>8,y,color,mode]
        steps += [labels.poke('params',value,i) for i,value in enumerate(params)]
        steps += [labels.poke('kind',kind),'press: ',labels.until('done'),
                  'peek:2000:16384',labels.until('ready')]
    result = a2test.run(disk,steps)
    for i,(kind,ends,mode,color) in enumerate(cases):
        expected = bytearray([165])*8192
        reference(expected,ends,mode,color,adapter)
        assert result.dumps[i] == expected+bytes([165])*8192, (adapter,kind,ends,mode,color)
    print(f'{"LOGO adapter" if adapter else "shared defaults"}: {len(cases)} lines/points, 280 pixels, palette, XOR, clipping, holes and inactive page OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='hgr-logo-') as tmp:
        for adapter in (False,True):
            work = Path(tmp)/str(adapter)
            work.mkdir()
            check(work,adapter)
