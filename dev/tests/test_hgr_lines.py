#!/usr/bin/env python3
"""Full-width assembly lines must match the original Bresenham pixel choices."""
from pathlib import Path
import argparse
import random
import tempfile
from test_hgr import DEV, build, offset, run
import a2test


def line(page, x0, y0, x1, y1):
    dx, dy = abs(x1-x0), abs(y1-y0)
    sx, sy = (1 if x0 <= x1 else -1), (1 if y0 <= y1 else -1)
    err = dx - dy
    while True:
        index = offset(y0) + x0//7
        # Existing axis spans force white palette, diagonal plots retain bit 7.
        if dx == 0 or dy == 0: page[index] &= 127
        page[index] |= 1 << (x0 % 7)
        if (x0, y0) == (x1, y1): return
        e2 = 2*err
        if e2 > -dy: err -= dy; x0 += sx
        if e2 < dx: err += dx; y0 += sy


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--folded',action='store_true')
    args=parser.parse_args()
    rng = random.Random(6502)
    cases = [(0,0,279,191), (279,191,0,0), (279,0,0,191), (0,191,279,0),
             (0,0,279,1), (279,191,0,190), (256,0,257,191), (257,191,256,0),
             (255,80,279,80), (279,0,279,191), (279,191,279,191),
             (1,1,9,5), (9,5,1,1)]
    cases += [(rng.randrange(280),rng.randrange(192),rng.randrange(280),rng.randrange(192))
              for _ in range(100)]
    cases += [(0,80,65535,80),(279,0,279,255),(65535,0,65535,191)]
    with tempfile.TemporaryDirectory(prefix='hgr-lines-') as directory:
        work = Path(directory)
        fixture = work / 'lines.c'
        fixture.write_text('#include "hgr.h"\n#include "gfx.h"\nstatic const struct {unsigned x0; unsigned char y0;'
                           'unsigned x1; unsigned char y1;} lines[] = {' +
                           ','.join('{%d,%d,%d,%d}' % c for c in cases) + '''};
int main(void) {
    unsigned i;
    unsigned char page, api;
    hgr_init();
    for (page=1; page<=2; ++page) {hgr_set_draw_page(page); hgr_clear(0x80);}
    for (api=0; api<2; ++api) for (page=1; page<=2; ++page) {
        hgr_set_draw_page(page);
        for (i=0; i<sizeof(lines)/sizeof(lines[0]); ++i) {
            hgr_clear(0x80);
            if (api) gfx_line(lines[i].x0,lines[i].y0,lines[i].x1,lines[i].y1);
            else hgr_line(lines[i].x0,lines[i].y0,lines[i].x1,lines[i].y1);
            hgr_line(65535u,0,0,0); hgr_line(0,255,279,0);
            gfx_line(65535u,0,0,1); gfx_line(0,255,1,0);
            *(volatile unsigned char *)0x1000=page;
            *(volatile unsigned char *)0x1001=(unsigned char)i;
            apple2_getkey();
        }
    }
    return 0;
}
''')
        disk = build(work, fixture)
        if args.folded:
            obj=work/'folded.o'
            run(['ca65','-D','HGRC_X7_FOLDED=1','-o',obj,DEV/'lib/hgrc/hgr_columns.s'])
            run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
                 '-m',work/'test.map','-Ln',work/'test.lbl','-o',work/'test.bin',
                 work/'crt0_apple2.o',work/'lines.o',work/'apple2io_asm.o',obj,work/'hgrc.lib'])
            disk=a2test.build_disk(work,'TEST',work/'test.bin')
        linked = (work / 'test.map').read_text().split('Segment list:')[0]
        assert 'gfx_line_hgr.o):' in linked and 'hgr_line_asm.o):' in linked
        assert 'gfx_line.o):' not in linked, 'generic C Bresenham linked in HGR'
        steps = ['wait:1100']
        for _ in range(4*len(cases)):
            steps += ['peek:1000:2','peek:2000:16384','key: ','wait:10']
        result = a2test.run(disk, steps, iie=args.iie)
        pages = [bytearray([128])*8192 for _ in range(2)]
        for stage in range(4*len(cases)):
            pg, index = divmod(stage % (2*len(cases)), len(cases))
            assert result.dumps[2*stage] == bytes((pg+1,index)), 'line did not terminate'
            pages[pg] = bytearray([128])*8192
            x0,y0,x1,y1 = cases[index]
            if stage < 2*len(cases):
                if x0<280 and x1<280 and y0<192 and y1<192:
                    line(pages[pg],x0,y0,x1,y1)
            elif y0==y1:
                x0,x1=sorted((x0,x1))
                if x0<280 and y0<192: line(pages[pg],x0,y0,min(x1,279),y1)
            elif x0==x1:
                y0,y1=sorted((y0,y1))
                if x0<280 and y0<192: line(pages[pg],x0,y0,x1,min(y1,191))
            elif x0<280 and x1<280 and y0<192 and y1<192:
                line(pages[pg],x0,y0,x1,y1)
            assert result.dumps[2*stage+1] == pages[0]+pages[1], ('Bresenham',pg,cases[index])
    print(f'HGR lines: 464 hgr/gfx lines, ASM selection, clipped/rejected axes, '
          f'octants, ties and palette OK; folded={args.folded}, IIe={args.iie}.')


if __name__ == '__main__':
    main()
