#!/usr/bin/env python3
"""The explicit generic line implementation remains valid for both DHGR backends."""
from pathlib import Path
import random
import tempfile
from test_hgr import build
from test_dhgr import pixel, color_pixel
import a2test


def main():
    rng = random.Random(6502)
    for mono, width in ((False,140),(True,560)):
        cases = [(0,0,width-1,191),(width-1,191,0,0),
                 (0,191,width-1,0),(width-1,0,0,191),
                 (0,80,width-1,80),(width-1,0,width-1,191)]
        cases += [(rng.randrange(width),rng.randrange(192),rng.randrange(width),rng.randrange(192))
                  for _ in range(10)]
        with tempfile.TemporaryDirectory(prefix='gfx-dhgr-lines-') as directory:
            work = Path(directory)
            fixture = work/'lines.c'
            fixture.write_text('#include "dhgr.h"\n#include "gfx.h"\n#include "apple2io.h"\n'
                'static const struct {unsigned x0; unsigned char y0; unsigned x1; unsigned char y1;} lines[]={' +
                ','.join('{%d,%d,%d,%d}'%c for c in cases) + '};\n'
                'int main(void) {unsigned char page,i; if (!dhgr_init()) return 1;'
                'for(page=1;page<=2;++page) {dhgr_draw_page(page); dhgr_clear(0);}'
                'dhgr_set_color(%d);'% (1 if mono else 9) +
                'for(page=1;page<=2;++page) {dhgr_draw_page(page);'
                'for(i=0;i<sizeof(lines)/sizeof(lines[0]);++i) {dhgr_clear(0);'
                'gfx_line(lines[i].x0,lines[i].y0,lines[i].x1,lines[i].y1);'
                'gfx_line(65535u,0,0,1); gfx_line(0,255,1,0);'
                'apple2_getkey();}} return 0;}')
            disk = build(work,fixture,gfx_backend='gfx_backend_dhgr_'+('mono' if mono else 'color')+'.c')
            linked = (work/'test.map').read_text().split('Segment list:')[0]
            assert 'gfx_line.o):' in linked and 'gfx_line_hgr.o):' not in linked
            assert 'hgr_line_asm.o):' not in linked
            labels = a2test.labels(work/'test.lbl')
            steps = []
            for _ in range(2*len(cases)):
                steps += [labels.until('_apple2_getkey'),'peek:2000:16384',
                          'poke:C003:0','peek:2000:16384','poke:C002:0','key: ','wait:1']
            result = a2test.run(disk,steps,iie=True)
            expected = [[bytearray(8192),bytearray(8192)] for _ in range(2)]
            for stage in range(2*len(cases)):
                page,index = divmod(stage,len(cases))
                expected[page] = [bytearray(8192),bytearray(8192)]
                x0,y0,x1,y1 = cases[index]
                dx,dy=abs(x1-x0),abs(y1-y0)
                sx,sy=(1 if x0<=x1 else -1),(1 if y0<=y1 else -1)
                err=dx-dy
                while True:
                    if mono: pixel(expected[page],x0,y0,1)
                    else: color_pixel(expected[page],x0,y0,9)
                    if (x0,y0)==(x1,y1): break
                    e2=2*err
                    if e2>-dy: err-=dy; x0+=sx
                    if e2<dx: err+=dx; y0+=sy
                for bank in range(2):
                    assert result.dumps[stage*2+bank] == expected[0][bank]+expected[1][bank],(mono,page,index,bank)
    print('gfx DHGR generic lines: color/mono, two pages and banks, axes and diagonals OK.')


if __name__=='__main__':
    main()
