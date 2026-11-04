#!/usr/bin/env python3
"""Pre-shift sprites: both APIs, byte dimensions, modes, phases and cold tables."""
from pathlib import Path
import argparse
import tempfile
import test_hgr

DEV = test_hgr.DEV
CASES = [(7,255), (14,254), (140,240), (256,220), (279,217),
         (279,216), (1,255), (9,255), (10,255), (12,255),
         (256,255), (279,255), (14,255)]
CASES = [(x, stride, 1, 191) for x, stride in CASES]
CASES += [(28 + phase, 3, 16, 7) for phase in range(7)]
CASES += [(28 + phase, 2, 255, 0) for phase in range(7)]
CASES += [(273, 3, 255, 189), (279, 3, 255, 191),
          (28, 0, 255, 0), (28, 3, 0, 0), (280, 3, 16, 0), (0, 3, 16, 192)]

CASES += [(65535,3,16,0),(0,3,16,255)]


def paint(page, case, mode):
    x,stride,height,y=case
    if x>=280 or y>=192:
        return
    col,phase=divmod(x,7)
    for row in range(min(height,192-y)):
        for j in range(min(stride,40-col)):
            address=phase*stride*height+row*stride+j
            assert address<7*3*255, (case,address)
            value=(address*13+1)&255
            dest=test_hgr.offset(y+row)+col+j
            if mode==0: page[dest]|=value
            elif mode==2: page[dest]^=value
            else: page[dest]&=value^255


def check(work, iie=False, folded=False):
    source=work/'preshift_bounds.c'
    entries=','.join('{%du,%du,%du,%du}'%case for case in CASES)
    modes=(0,1,2,255)
    warm=[(*case,mode) for case in CASES for mode in modes]
    warm += [(28+s%7,s,1,191,modes[s%4]) for s in range(256)]
    warm += [(28+h%7,2,h,0,modes[h%4]) for h in range(256)]
    cold_indices=[0,*range(13,20),27,28,29,30,31,32,33,34]
    source.write_text('''#include "hgr.h"
void cold_ready(void); void cold_done(void); void painted(void);
unsigned char cold_index,cold_mode,cold_fast;
static unsigned char bank[7u*3u*255u];
static hgr_sprite_t sprite;
static const unsigned char modes[]={0,1,2,255};
static const struct {unsigned x; unsigned char stride,h,y;} cases[]={''' + entries + '''};
#define NCASES (sizeof(cases)/sizeof(cases[0]))
int main(void) {
    unsigned i,c,index,x;
    unsigned char page,y,mode,value;
    for(i=0;i<sizeof(bank);++i) bank[i]=(unsigned char)(i*13u+1u);
    sprite.bits=bank;
    for(i=0x2000;i<0x6000;++i) *(unsigned char *)i=0xA5;
    cold_ready();
    sprite.stride=cases[cold_index].stride; sprite.h=cases[cold_index].h;
    if(cold_fast) hgr_sprite_xor(cases[cold_index].x,cases[cold_index].y,&sprite);
    else hgr_sprite(cases[cold_index].x,cases[cold_index].y,&sprite,cold_mode);
    cold_done();
    hgr_init();
    for(page=1;page<=2;++page) {
        for(c=0;c<NCASES*4u+512u;++c) {
            if(c<NCASES*4u) {
                index=c>>2;
                x=cases[index].x; y=cases[index].y;
                sprite.stride=cases[index].stride; sprite.h=cases[index].h;
                mode=modes[c&3u];
            } else {
                value=(unsigned char)(c-NCASES*4u);
                x=28u+value%7u; mode=modes[value&3u];
                if(c<NCASES*4u+256u) {sprite.stride=value; sprite.h=1; y=191;}
                else {sprite.stride=2; sprite.h=value; y=0;}
            }
            hgr_set_draw_page(1); hgr_clear(0xA5);
            hgr_set_draw_page(2); hgr_clear(0xDA);
            hgr_set_draw_page(page); hgr_sprite(x,y,&sprite,mode);
            hgr_set_draw_page(3u-page); hgr_sprite_xor(x,y,&sprite);
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
    disk=test_hgr.build(work,source,extra_sources=(marker,))
    if folded:
        obj=work/'folded.o'
        test_hgr.run(['ca65','-D','HGRC_X7_FOLDED=1','-o',obj,DEV/'lib/hgrc/hgr_columns.s'])
        test_hgr.run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-m',work/'test.map','-Ln',work/'test.lbl','-o',work/'test.bin',
             work/'crt0_apple2.o',work/'preshift_bounds.o',work/'apple2io_asm.o',obj,work/'hgrc.lib'])
        disk=test_hgr.a2test.build_disk(work,'TEST',work/'test.bin')
    labels=test_hgr.a2test.labels(work/'test.lbl')
    for base in (0,0x40):
        for index in cold_indices:
            case=CASES[index]
            for fast,mode in [(False,m) for m in modes]+[(True,2)]:
                steps=[labels.until('_cold_ready'),labels.poke('_cold_index',index),
                       labels.poke('_cold_mode',mode),labels.poke('_cold_fast',int(fast)),
                       labels.poke('_hgr_base',base),labels.until('_cold_done'),
                       'peek:2000:16384',labels.peek('_hgr_rowlo',192),labels.peek('_hgr_rowhi',192),
                       labels.peek('_hgr_col7',280),labels.peek('_hgr_phase7',280)]
                result=test_hgr.a2test.run(disk,steps,iie=iie)
                pages=[bytearray([0xA5])*8192 for _ in range(2)]
                paint(pages[base==0x40],case,mode)
                assert result.mem(0x2000,16384)==pages[0]+pages[1],('cold',base,case,fast,mode)
                addresses=[((base or 0x20)<<8)+test_hgr.offset(y) for y in range(192)]
                for name,shift in (('_hgr_rowlo',0),('_hgr_rowhi',8)):
                    assert result.mem(labels[name],192)==bytes(a>>shift&255 for a in addresses),('cold',name)
                valid=case[0]<280 and case[1]>0 and case[2]>0 and case[3]<192
                cols=bytes(x//7 for x in range(280)) if valid else bytes(280)
                phases=bytes(x%7 for x in range(280)) if valid else bytes(280)
                assert result.mem(labels['_hgr_col7'],280)==cols,('cold','columns',case)
                assert result.mem(labels['_hgr_phase7'],280)==phases,('cold','phases',case)
    steps=[]
    for _ in range(2*len(warm)):
        steps += [labels.until('_painted'),'peek:2000:16384',labels.until('resume')]
    result=test_hgr.a2test.run(disk,steps,iie=iie)
    for frame in range(2*len(warm)):
        page,index=divmod(frame,len(warm)); case=warm[index][:4]; mode=warm[index][4]
        pages=[bytearray([0xA5])*8192,bytearray([0xDA])*8192]
        paint(pages[page],case,mode); paint(pages[1-page],case,2)
        assert result.dumps[frame]==pages[0]+pages[1],('warm',page,case,mode)
    print(f'Pre-shift sprites: {2*len(warm)} paired warm frames, {len(cold_indices)*10} cold calls; '
          f'all byte strides/heights, modes/phases, clipping, pages/palette/holes; '
          f'folded={folded}, IIe={iie}.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--folded',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='preshift-bounds-') as tmp:
        check(Path(tmp),args.iie,args.folded)
