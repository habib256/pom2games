#!/usr/bin/env python3
"""GFX DHGR rectangles: full coordinate domains, clipping and fill ABI."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


ALIGN_CASES=((65535,255,0,0),(279,191,279,191),(280,192,65535,255),(1,1,5,5))


AXIS_ALIGN_CASES=((65535,191,0,191),(139,255,139,0),(0,255,65535,255),(139,0,139,191))


def batches(width,axes=False):
    for anchor in (0,width-1,65535):
        for reverse in (False,True):
            for high in range(256):
                yield [((anchor,191,v,191) if reverse else (v,191,anchor,191)) if axes
                       else ((anchor,255,v,0) if reverse else (v,0,anchor,255))
                       for v in range(high*256,(high+1)*256)]
    for high in range(256):
        yield [(v,255,v,0) if axes else (v,191,v,191) for v in range(high*256,(high+1)*256)]
    for high in range(256):
        yield [(width-1,high,width-1 if axes else 0,low) for low in range(256)]
    yield [(65535,y,0,y) for y in range(256)]
    for case in AXIS_ALIGN_CASES if axes else ALIGN_CASES:
        yield [case]*256


def expected(cases,width,pen):
    result=bytearray([0]*256+[0xA5]*1792)
    for index,(x0,y0,x1,y1) in enumerate(cases):
        x,xr=sorted((x0,x1));y,end=sorted((y0,y1))
        if x>=width or y>191:continue
        xr=min(xr,width-1)-x+1;rows=min(end,191)-y+1
        for plane,value in enumerate((1,x&255,x>>8,xr&255,xr>>8,y,rows,pen)):
            result[plane*256+index]=value
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--color',action='store_true')
    parser.add_argument('--axes',action='store_true')
    args=parser.parse_args()
    if args.axes and not args.color:parser.error('--axes requires --color')
    width=140 if args.color else 560
    pen=15 if args.color else 1
    backend="gfx_backend_dhgr_"+("color" if args.color else "mono")+".c"
    with tempfile.TemporaryDirectory(prefix='gfx-dhgr-rect-entry-') as directory:
        work=Path(directory);source=work/'axes.c'
        source.write_text('''#include "gfx.h"
#include "dhgr.h"
void page_done(void); void finished(void); void align_call(void);
unsigned char records[8][256],index,align_kind;
static const unsigned anchors[]={0,279,65535u};
static void clear_slot(void) {
    unsigned char i;
    records[0][index]=0;
    for(i=1;i<8;++i) records[i][index]=0xA5u;
}
int main(void) {
    unsigned value;
    unsigned char anchor,reverse;
    volatile unsigned guard=0xA55Au;
    dhgr_set_color(255);
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
'''.replace('279',str(width-1)))
        if args.axes:
            text=source.read_text()
            for before,after in (
                ('gfx_filled_rect(anchors[anchor],255,value,0)','gfx_hline(anchors[anchor],value,191)'),
                ('gfx_filled_rect(value,0,anchors[anchor],255)','gfx_hline(value,anchors[anchor],191)'),
                ('gfx_filled_rect(value,191,value,191)','gfx_vline(value,255,0)'),
                (f'gfx_filled_rect({width-1},(unsigned char)(value>>8),0,(unsigned char)value)',
                 f'gfx_vline({width-1},(unsigned char)(value>>8),(unsigned char)value)'),
                ('gfx_filled_rect(65535u,index,0,index)','gfx_hline(65535u,0,index)')):
                assert before in text;text=text.replace(before,after)
            source.write_text(text)
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
        if args.axes:
            code=code.replace('.import _gfx_filled_rect,','.import _gfx_hline, _gfx_vline,')
            start=code.index(' ldy _align_kind\n lda y0,y')
            end=code.index(' lda sp\n cmp _index',start)
            code=code[:start]+""" ldy _align_kind
 tya
 and #1
 bne vertical
 lda x1hi,y
 tax
 lda x1lo,y
 jsr pushax
 ldy _align_kind
 lda y1,y
 jsr _gfx_hline
 jmp check
vertical:
 lda y0,y
 jsr pusha
 ldy _align_kind
 lda y1,y
 jsr _gfx_vline
check:
"""+code[end:]
        align_cases=AXIS_ALIGN_CASES if args.axes else ALIGN_CASES
        planes=[(x0&255,x0>>8,y0,x1&255,x1>>8,y1) for x0,y0,x1,y1 in align_cases]
        for i,name in enumerate(('x0lo','x0hi','y0','x1lo','x1hi','y1')):
            code+=name+': .byte '+','.join(str(v[i]) for v in planes)+'\n'
        align.write_text(code)
        build(work,source,extra_sources=(marker,align),gfx_backend=backend)
        sink=work/'sink.s'
        target='_dhgr_fill_rect' if args.color else '_dhgr_fill_bits'
        stub=f""".export {target}
.import _records, _index, incsp4, incsp6
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.code
{target}:
 ldx _index
 sta _records+1792,x
 lda #1
 sta _records,x
"""
        planes=(6,3,5,1) if args.color else (6,3,4,5,1,2)
        for offset,plane in enumerate(planes):
            stub+=f' ldy #{offset}\n lda (sp),y\n sta _records+{256*plane},x\n'
        if args.color:stub+=' lda #0\n sta _records+512,x\n sta _records+1024,x\n'
        stub+=' lda #$5a\n'
        for symbol in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {symbol}\n'
        sink.write_text(stub+' tax\n tay\n jmp incsp'+('4' if args.color else '6')+'\n');obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'axes.o',work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(2053):
            steps += [labels.until('_page_done'),labels.peek('_records',2048),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==2053
        for index,cases in enumerate(batches(width,args.axes)):
            assert result.dumps[index]==expected(cases,width,pen),('axis batch',index,cases[0])
        print(f'GFX DHGR rectangle entry: 525,568 cases, both x endpoints in both orders, '
              f'all y pairs and degenerate rectangles, clipping/rejection, span parameters, hostile scratch, guards and 1,024 stack placements; IIe={args.iie}, color={args.color}, axes={args.axes}.')


if __name__=='__main__':
    main()
