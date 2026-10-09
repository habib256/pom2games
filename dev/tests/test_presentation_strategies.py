#!/usr/bin/env python3
"""All row-address comparison prototypes resolve the same two pages."""
from pathlib import Path
import sys
import tempfile
from test_hgr import DEV, build, offset
import a2test
sys.path.insert(0,str(DEV/'bench'))
from run import presentation_source


def main():
    for variant in ('compact','unrolled','fixed'):
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
            result=a2test.run(disk,steps)
            # Adjacent dumps merge: inspect each symbol by address/occurrence.
            for frame in range(4):
                base=0x40 if frame%2==0 else 0x20
                assert result.mem(labels['output_lo'],192,frame)==bytes(offset(y)&255 for y in range(192))
                assert result.mem(labels['output_hi'],192,frame)==bytes(base+(offset(y)>>8) for y in range(192)),variant
    print('Presentation prototypes: all 192 row addresses on both pages, compact/unrolled/fixed-base OK.')


if __name__=='__main__':main()
