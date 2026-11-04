#!/usr/bin/env python3
"""Byte-aligned HGR sprites: full byte dimensions, modes, clipping and cold calls."""
import argparse
from pathlib import Path
import tempfile
from test_hgr import build, a2test, offset, DEV, run


def expected(page, box):
    x,y,width,height,mode,start=box
    if x>=280 or y>=192:
        return
    col=x//7
    for row in range(min(height,192-y)):
        for byte in range(min(width,40-col)):
            source=start+row*width+byte
            assert source<1024, (box,source)  # every drawn source byte belongs to the fixture
            value=((source*73+19)^(source>>3))&255
            address=offset(y+row)+col+byte
            if mode==0:
                page[address]|=value
            elif mode==2:
                page[address]^=value
            else:
                page[address]&=value^255


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--folded',action='store_true')
    args=parser.parse_args()
    modes=(0,1,2,255)
    cold=[(255,189,255,255,mode,i*127) for i,mode in enumerate(modes)]
    cold += [(0,0,0,255,2,0),(0,0,255,0,2,0),(65535,0,255,255,2,0),
             (280,0,1,1,1,0),(0,192,1,1,1,0)]
    boxes=[(x,189,x%255+1,255) for x in range(280)]
    boxes += [(273,190,w,255) for w in range(256)]
    boxes += [(7,0,1,h) for h in range(256)]
    boxes += [(279,y,1,255) for y in range(256)]
    boxes += [(x,40,255,255) for x in (280,511,512,1792,65535)]
    cases=cold+[(*box,modes[i%4],(i%4)*127) for i,box in enumerate(boxes)]
    cases += [(x,31,w,8,mode,i*127) for x,w in ((0,40),(7,39),(13,41),(255,7),(279,1))
              for i,mode in enumerate(modes)]
    with tempfile.TemporaryDirectory(prefix='hgr-blit7-') as directory:
        work=Path(directory)
        source=work/'blit7.c'
        source.write_text('''#include "hgr.h"
void cold_ready(void); void cold_done(void); void painted(void);
unsigned char cold_index;
#pragma bss-name(push,"LOWBSS")
static unsigned char data[1024];
#pragma bss-name(pop)
static const struct {unsigned x; unsigned char y,w,h,mode,bank;} cases[]={'''
             + ','.join('{%du,%du,%du,%du,%du,%du}'%(*box[:5],box[5]//127) for box in cases)+'''};
int main(void) {
    unsigned i;
    unsigned char page;
    for(i=0;i<sizeof(data);++i) data[i]=(unsigned char)((i*73u+19u)^(i>>3));
    for(i=0x2000;i<0x6000;++i) *(unsigned char *)i=0xA5;
    cold_ready();
    hgr_blit7(cases[cold_index].x,cases[cold_index].y,cases[cold_index].w,
              cases[cold_index].h,data+(unsigned)cases[cold_index].bank*127u,cases[cold_index].mode);
    cold_done();
    hgr_init();
    for(page=1;page<=2;++page) {
        for(i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
            hgr_set_draw_page(1); hgr_clear(0xA5);
            hgr_set_draw_page(2); hgr_clear(0xDA);
            hgr_set_draw_page(page);
            hgr_blit7(cases[i].x,cases[i].y,cases[i].w,cases[i].h,
                      data+(unsigned)cases[i].bank*127u,cases[i].mode);
            painted();
        }
    }
    for(;;) {}
    return 0;
}
''')
        marker=work/'marker.s'
        marker.write_text('.export _cold_ready, _cold_done, _painted, resume\n.code\n'
                          '_cold_ready: rts\n_cold_done: rts\n_painted: nop\nresume: rts\n')
        disk=build(work,source,extra_sources=(marker,))
        if args.folded:
            folded=work/'folded.o'
            run(['ca65','-D','HGRC_X7_FOLDED=1','-o',folded,DEV/'lib/hgrc/hgr_columns.s'])
            run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
                 '-m',work/'test.map','-Ln',work/'test.lbl','-o',work/'test.bin',
                 work/'crt0_apple2.o',work/'blit7.o',work/'apple2io_asm.o',folded,work/'hgrc.lib'])
            disk=a2test.build_disk(work,'TEST',work/'test.bin')
        labels=a2test.labels(work/'test.lbl')
        for base in (0,0x40):
            for index,box in enumerate(cold):
                steps=[labels.until('_cold_ready'),labels.poke('_cold_index',index),
                       labels.poke('_hgr_base',base),labels.until('_cold_done'),
                       'peek:2000:16384',labels.peek('_hgr_col7',280)]
                result=a2test.run(disk,steps,iie=args.iie)
                pages=[bytearray([0xA5])*8192 for _ in range(2)]
                expected(pages[base==0x40],box)
                assert result.mem(0x2000,16384)==pages[0]+pages[1],('cold',base,box)
                assert result.mem(labels['_hgr_col7'],280)==bytes(x//7 for x in range(280)),('cold table',box)
        steps=[]
        for _ in range(2*len(cases)):
            steps += [labels.until('_painted'),'peek:2000:16384',labels.until('resume')]
        result=a2test.run(disk,steps,iie=args.iie)
        for frame in range(2*len(cases)):
            page,index=divmod(frame,len(cases))
            pages=[bytearray([0xA5])*8192,bytearray([0xDA])*8192]
            expected(pages[page],cases[index])
            assert result.dumps[frame]==pages[0]+pages[1],('warm',page,cases[index])
        print(f'HGR byte sprites: {2*len(cases)} warm and {2*len(cold)} cold cases; '
              f'all visible x and byte dimensions, SET/CLEAR/XOR/other mode, source stride, '
              f'both pages/high bits/holes; folded={args.folded}, IIe={args.iie}.')


if __name__=='__main__':
    main()
