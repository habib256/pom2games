#!/usr/bin/env python3
"""GFX filled rectangle: full coordinate domains, sorting, clipping and span ABI."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


ALIGN_CASES=((65535,255,0,0),(279,191,279,191),(280,192,65535,255),(1,1,5,5))


def batches():
    for anchor in (0,279,65535):
        for reverse in (False,True):
            for high in range(256):
                yield [(anchor,255,v,0) if reverse else (v,0,anchor,255)
                       for v in range(high*256,(high+1)*256)]
    for high in range(256):
        yield [(v,191,v,191) for v in range(high*256,(high+1)*256)]
    for high in range(256):
        yield [(279,high,0,low) for low in range(256)]
    yield [(65535,y,0,y) for y in range(256)]
    for case in ALIGN_CASES:
        yield [case]*256


def expected(cases):
    result=bytearray([0]*256+[0xA5]*1536)
    for index,(x0,y0,x1,y1) in enumerate(cases):
        x,xr=sorted((x0,x1));y,end=sorted((y0,y1))
        if x>279 or y>191:continue
        xr=min(xr,279);rows=min(end,191)-y+1
        for plane,value in enumerate((1,x&255,x>>8,xr&255,xr>>8,y,rows)):
            result[plane*256+index]=value
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-rect-entry-') as directory:
        work=Path(directory);source=work/'axes.c'
        source.write_text('''#include "gfx.h"
void page_done(void); void finished(void); void align_call(void);
unsigned char records[7][256],index,align_kind;
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
            if(reverse) gfx_filled_rect(anchors[anchor],255,value,0);
            else gfx_filled_rect(value,0,anchors[anchor],255);
            if(guard!=0xA55Au) for(;;) {}
            ++value;
            if((unsigned char)value==0) page_done();
        } while(value);
    }
    value=0;
    do {
        index=(unsigned char)value;clear_slot();
        gfx_filled_rect(value,191,value,191);
        if(guard!=0xA55Au) for(;;) {}
        ++value;
        if((unsigned char)value==0) page_done();
    } while(value);
    value=0;
    do {
        index=(unsigned char)value;clear_slot();
        gfx_filled_rect(279,(unsigned char)(value>>8),0,(unsigned char)value);
        if(guard!=0xA55Au) for(;;) {}
        ++value;
        if((unsigned char)value==0) page_done();
    } while(value);
    for(value=0;value<256;++value) {
        index=(unsigned char)value;clear_slot();
        gfx_filled_rect(65535u,index,0,index);
    }
    if(guard!=0xA55Au) for(;;) {}
    page_done();
    for(align_kind=0;align_kind<4;++align_kind) {
        for(value=0;value<256;++value) {index=(unsigned char)value;clear_slot();align_call();}
        page_done();
    }
    finished();
    for(;;) {}
    return 0;
}
''')
        marker=work/'marker.s'
        marker.write_text('.export _page_done, resume, _finished\n.code\n'
                          '_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s'
        code=""".export _align_call
.import _gfx_filled_rect, _index, _align_kind, pushax, pusha
.importzp sp
.bss
saved_sp: .res 2
.code
_align_call:
 lda sp
 sta saved_sp
 lda sp+1
 sta saved_sp+1
 lda _index
 sta sp
 lda #$91
 sta sp+1
 ldy #0
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 ldy _align_kind
 lda x0hi,y
 tax
 lda x0lo,y
 jsr pushax
 ldy _align_kind
 lda y0,y
 jsr pusha
 ldy _align_kind
 lda x1hi,y
 tax
 lda x1lo,y
 jsr pushax
 ldy _align_kind
 lda y1,y
 jsr _gfx_filled_rect
 lda sp
 cmp _index
 bne fail
 lda sp+1
 cmp #$91
 bne fail
 ldy #0
 lda (sp),y
 cmp #$a5
 bne fail
 iny
 lda (sp),y
 cmp #$a5
 bne fail
 lda saved_sp
 sta sp
 lda saved_sp+1
 sta sp+1
 rts
fail: jmp fail
.rodata
"""
        planes=[(x0&255,x0>>8,y0,x1&255,x1>>8,y1) for x0,y0,x1,y1 in ALIGN_CASES]
        for i,name in enumerate(('x0lo','x0hi','y0','x1lo','x1hi','y1')):
            code+=name+': .byte '+','.join(str(v[i]) for v in planes)+'\n'
        align.write_text(code)
        build(work,source,extra_sources=(marker,align))
        sink=work/'sink.s'
        stub='''.export _hgr_fill_span
.import _records, _index
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
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
        stub+=' lda #$5a\n'
        for symbol in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {symbol}\n'
        sink.write_text(stub+' tax\n tay\n rts\n');obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'axes.o',work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(2053):
            steps += [labels.until('_page_done'),labels.peek('_records',1792),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==2053
        for index,cases in enumerate(batches()):
            assert result.dumps[index]==expected(cases),('axis batch',index,cases[0])
        print(f'GFX rectangle entry: 525,568 cases, both x endpoints in both orders, '
              f'all y pairs and degenerate rectangles, clipping/rejection, span parameters, hostile scratch, guards and 1,024 stack placements; IIe={args.iie}.')


if __name__=='__main__':
    main()
