#!/usr/bin/env python3
"""All row-address comparison prototypes resolve the same two pages."""
from pathlib import Path
import sys
import argparse
import tempfile
from test_hgr import DEV, build, offset
import a2test
sys.path.insert(0,str(DEV/'bench'))
from run import presentation_source


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--iie",action="store_true");args=ap.parse_args()
    for variant in ('compact','unrolled','fixed','explicit'):
        with tempfile.TemporaryDirectory(prefix='hgr-present-') as directory:
            work=Path(directory);source=work/'present.c'
            source.write_text('''#include "hgr.h"
void bench_present(void);
int main(void) {unsigned char i; hgr_build_tables();
for(i=0;i<4;++i) {bench_present(); apple2_getkey();}return 0;}
''')
            asm=work/'strategy.s'
            code=presentation_source(variant)
            code=code.replace('sta ptr1\n','sta output_lo,x\nsta ptr1\n')
            code=code.replace('sta ptr1+1\n','sta output_hi,x\nsta ptr1+1\n')
            code='.export output_lo, output_hi\n.bss\noutput_lo: .res 192\noutput_hi: .res 192\n'+code
            asm.write_text(code)
            disk=build(work,source,extra_sources=[asm]);labels=a2test.labels(work/'test.lbl')
            steps=[]
            for _ in range(4):
                steps += [labels.until('_apple2_getkey'),labels.peek('output_lo',192),labels.peek('output_hi',192),'key: ']
            result=a2test.run(disk,steps,iie=args.iie)
            # Adjacent dumps merge: inspect each symbol by address/occurrence.
            for frame in range(4):
                base=0x40 if frame%2==0 else 0x20
                assert result.mem(labels['output_lo'],192,frame)==bytes(offset(y)&255 for y in range(192))
                assert result.mem(labels['output_hi'],192,frame)==bytes(base+(offset(y)>>8) for y in range(192)),variant
    with tempfile.TemporaryDirectory(prefix='hgr-explicit-') as directory:
        work=Path(directory);source=work/'explicit.c'
        source.write_text('''#include "hgr.h"
unsigned char lo[192],hi[192];
int main(void) {unsigned char y,page;unsigned addr;
for(page=1;page<=2;++page) {
    for(y=0;y<192;++y) {addr=(unsigned)hgr_row_on_page(page,y);lo[y]=addr;hi[y]=addr>>8;}
    if(hgr_row_on_page(0,0)||hgr_row_on_page(3,0)||hgr_row_on_page(page,192)) return 1;
    apple2_getkey();
}return 0;}
''')
        disk=build(work,source); labels=a2test.labels(work/'test.lbl')
        result=a2test.run(disk,[labels.until('_apple2_getkey'),labels.peek('_lo',192),labels.peek('_hi',192),'key: ',
                             labels.until('_apple2_getkey'),labels.peek('_lo',192),labels.peek('_hi',192)],iie=args.iie)
        for page in (1,2):
            assert result.mem(labels['_lo'],192,page-1)==bytes(offset(y)&255 for y in range(192))
            assert result.mem(labels['_hi'],192,page-1)==bytes(page*0x20+(offset(y)>>8) for y in range(192))
        linked=(work/'test.map').read_text()
        assert 'hgr_init.o' not in linked and 'hgr_rows_asm.o' not in linked, 'mutable row tables linked'
    print('Presentation prototypes: all 192 row addresses on both pages, compact/unrolled/fixed-base and explicit immutable API OK.')


if __name__=='__main__':main()
