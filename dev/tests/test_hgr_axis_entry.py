#!/usr/bin/env python3
"""Axis entries: complete coordinate domains, sorting, clipping and span ABI."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def batches():
    for anchor in (0,279,65535):
        for reverse in (False,True):
            for high in range(256):
                yield [('h',anchor,v,191) if reverse else ('h',v,anchor,191)
                       for v in range(high*256,(high+1)*256)]
    for high in range(256):
        yield [('v',v,255,0) for v in range(high*256,(high+1)*256)]
    for high in range(256):
        yield [('v',279,high,low) for low in range(256)]
    yield [('h',65535,0,y) for y in range(256)]


def expected(cases):
    result=bytearray([0]*256+[0xA5]*1536)
    for index,(kind,a,b,c) in enumerate(cases):
        if kind=='h':
            x,xr=sorted((a,b));y=c;rows=1
            if x>279 or y>191:continue
            xr=min(xr,279)
        else:
            x=xr=a;y,end=sorted((b,c))
            if x>279 or y>191:continue
            rows=min(end,191)-y+1
        for plane,value in enumerate((1,x&255,x>>8,xr&255,xr>>8,y,rows)):
            result[plane*256+index]=value
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-axis-entry-') as directory:
        work=Path(directory);source=work/'axes.c'
        source.write_text('''#include "hgr.h"
void page_done(void); void finished(void);
unsigned char records[7][256],index;
static const unsigned anchors[]={0,279,65535u};
static void clear_slot(void) {
    unsigned char i;
    records[0][index]=0;
    for(i=1;i<7;++i) records[i][index]=0xA5u;
}
int main(void) {
    unsigned value;
    unsigned char anchor,reverse;
    volatile unsigned guard=0xA55Au;
    for(anchor=0;anchor<3;++anchor) for(reverse=0;reverse<2;++reverse) {
        value=0;
        do {
            index=(unsigned char)value;clear_slot();
            if(reverse) hgr_hline(anchors[anchor],value,191);
            else hgr_hline(value,anchors[anchor],191);
            if(guard!=0xA55Au) for(;;) {}
            ++value;
            if((unsigned char)value==0) page_done();
        } while(value);
    }
    value=0;
    do {
        index=(unsigned char)value;clear_slot();
        hgr_vline(value,255,0);
        if(guard!=0xA55Au) for(;;) {}
        ++value;
        if((unsigned char)value==0) page_done();
    } while(value);
    value=0;
    do {
        index=(unsigned char)value;clear_slot();
        hgr_vline(279,(unsigned char)(value>>8),(unsigned char)value);
        if(guard!=0xA55Au) for(;;) {}
        ++value;
        if((unsigned char)value==0) page_done();
    } while(value);
    for(value=0;value<256;++value) {
        index=(unsigned char)value;clear_slot();
        hgr_hline(65535u,0,index);
    }
    if(guard!=0xA55Au) for(;;) {}
    page_done();finished();
    for(;;) {}
    return 0;
}
''')
        marker=work/'marker.s'
        marker.write_text('.export _page_done, resume, _finished\n.code\n'
                          '_page_done: nop\nresume: rts\n_finished: rts\n')
        build(work,source,extra_sources=(marker,))
        sink=work/'sink.s'
        stub='''.export _hgr_fill_span
.import _records, _index
.importzp _hgr_r_x, _hgr_r_xr, _hgr_r_y0, _hgr_r_rows
.code
_hgr_fill_span:
 ldx _index
 lda #1
 sta _records,x
'''
        for plane,name in enumerate(('_hgr_r_x','_hgr_r_x+1','_hgr_r_xr','_hgr_r_xr+1',
                                     '_hgr_r_y0','_hgr_r_rows'),1):
            stub+=f' lda {name}\n sta _records+{256*plane},x\n'
        sink.write_text(stub+' rts\n');obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'axes.o',work/'apple2io_asm.o',work/'marker.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(2049):
            steps += [labels.until('_page_done'),labels.peek('_records',1792),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==2049
        for index,cases in enumerate(batches()):
            assert result.dumps[index]==expected(cases),('axis batch',index,cases[0])
        print(f'HGR axis entries: 524,544 cases, both x endpoints in both orders, '
              f'all vertical y pairs, clipping/rejection, span parameters and caller guard; IIe={args.iie}.')


if __name__=='__main__':
    main()
