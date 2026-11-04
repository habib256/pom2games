#!/usr/bin/env python3
"""Actual HGR axes from cold state: clipped pixels, palettes, pages and tables."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test, pixel, offset


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--folded',action='store_true')
    args=parser.parse_args()
    cases=[]
    for a,b in ((0,279),(1,6),(6,7),(7,14),(255,256),(256,279),(279,279),
                (7,65535),(280,65535),(65535,65535)):
        for x0,x1 in ((a,b),(b,a)):
            cases.append((0,x0,x1,191,0))
    cases += [(0,0,279,y,0) for y in (0,192,255)]
    for x in (0,6,7,255,256,279,280,65535):
        for a,b in ((0,191),(255,0),(191,255),(192,255),(191,191)):
            cases.append((1,x,0,a,b))
    with tempfile.TemporaryDirectory(prefix='hgr-axes-') as directory:
        work=Path(directory);source=work/'axes.c'
        source.write_text('''#include "hgr.h"
#include <string.h>
void ready(void); void painted(void);
unsigned x0,x1;
unsigned char kind,y0,y1;
int main(void) {
    memset((void *)0x2000,0xAAu,16384u);
    ready();
    if(kind) hgr_vline(x0,y0,y1); else hgr_hline(x0,x1,y0);
    painted();
    for(;;) {}
    return 0;
}
''')
        marker=work/'marker.s'
        marker.write_text('.export _ready, _painted\n.code\n_ready: rts\n_painted: rts\n')
        disk=build(work,source,extra_sources=(marker,))
        if args.folded:
            obj=work/'folded.o';run(['ca65','-D','HGRC_X7_FOLDED=1','-o',obj,DEV/'lib/hgrc/hgr_columns.s'])
            run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
                 '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
                 work/'axes.o',work/'apple2io_asm.o',work/'marker.o',obj,work/'hgrc.lib'])
            disk=a2test.build_disk(work,'TEST',work/'test.bin')
        labels=a2test.labels(work/'test.lbl')
        for base in (0,0x40):
            for kind,x0,x1,y0,y1 in cases:
                steps=[labels.until('_ready'),labels.poke('_kind',kind),labels.poke('_y0',y0),
                       labels.poke('_y1',y1),labels.poke('_hgr_base',base)]
                for name,value in (('_x0',x0),('_x1',x1)):
                    steps += [labels.poke(name,value&255),f'poke:{labels[name]+1:04X}:{value>>8:02X}']
                steps += [labels.until('_painted'),'peek:2000:16384',labels.peek('_hgr_rowlo',192),
                          labels.peek('_hgr_rowhi',192),labels.peek('_hgr_col7',280),labels.peek('_hgr_mask7',280)]
                result=a2test.run(disk,steps,iie=args.iie)
                pages=[bytearray([0xAA]*8192),bytearray([0xAA]*8192)];page=pages[bool(base)]
                if kind:
                    lo,hi=sorted((y0,y1));valid=x0<280 and lo<192
                    if valid:
                        for y in range(lo,min(hi,191)+1):pixel(page,x0,y,1,white=True)
                else:
                    lo,hi=sorted((x0,x1));valid=lo<280 and y0<192
                    if valid:
                        for x in range(lo,min(hi,279)+1):pixel(page,x,y0,1,white=True)
                assert result.mem(0x2000,16384)==pages[0]+pages[1],('pixels',base,kind,x0,x1,y0,y1)
                addresses=[((base or 0x20)<<8)+offset(y) for y in range(192)]
                for name,shift in (('_hgr_rowlo',0),('_hgr_rowhi',8)):
                    wanted=bytes(a>>shift&255 for a in addresses) if valid else bytes(192)
                    assert result.mem(labels[name],192)==wanted,('rows',valid,name)
                for name,wanted in (('_hgr_col7',bytes(x//7 for x in range(280))),
                                    ('_hgr_mask7',bytes(1<<(x%7) for x in range(280)))):
                    assert result.mem(labels[name],280)==(wanted if valid else bytes(280)),('tables',valid,name)
        print(f'HGR axes: {2*len(cases)} cold calls, sorting/clipping/rejection, both pages, '
              f'palette/holes, lazy rows/columns/masks; folded={args.folded}, IIe={args.iie}.')


if __name__=='__main__':
    main()
