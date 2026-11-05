#!/usr/bin/env python3
"""GFX HGR line dispatch: full word/byte domains and argument preservation."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


ALIGN_CASES=((65535,95,0,95),(279,255,279,0),(0,0,279,191),(65535,255,65535,255))


def batches():
    for anchor in (0,279,65535):
        for reverse in (False,True):
            for horizontal in (False,True):
                for high in range(256):
                    yield [(anchor,95 if horizontal else 1,v,95 if horizontal else 191)
                           if reverse else (v,95 if horizontal else 1,anchor,95 if horizontal else 191)
                           for v in range(high*256,(high+1)*256)]
    for vertical in (False,True):
        for y0 in range(256):
            yield [(279 if vertical else 0,y0,279,y1) for y1 in range(256)]
    for case in ALIGN_CASES:
        yield [case]*256


def expected(cases):
    result=bytearray(7*256)
    for index,(x0,y0,x1,y1) in enumerate(cases):
        kind=1 if y0==y1 else 2 if x0==x1 else 3
        for plane,value in enumerate((kind,x0&255,x0>>8,y0,x1&255,x1>>8,y1)):
            result[plane*256+index]=value
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-line-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text(r'''#include "gfx.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[7][256],index,align_kind;
static const unsigned anchors[]={0,279,65535u};
int main(void) {
    unsigned value;
    unsigned char anchor,reverse,horizontal,vertical;
    volatile unsigned guard=0xA55Au;
    for(anchor=0;anchor<3;++anchor) for(reverse=0;reverse<2;++reverse)
    for(horizontal=0;horizontal<2;++horizontal) {
        value=0;
        do {
            index=(unsigned char)value;
            if(reverse) gfx_line(anchors[anchor],horizontal?95:1,value,horizontal?95:191);
            else gfx_line(value,horizontal?95:1,anchors[anchor],horizontal?95:191);
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    for(vertical=0;vertical<2;++vertical) {
        value=0;
        do {
            index=(unsigned char)value;
            gfx_line(vertical?279:0,(unsigned char)(value>>8),279,(unsigned char)value);
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    for(align_kind=0;align_kind<4;++align_kind) {
        for(value=0;value<256;++value) {index=(unsigned char)value;align_call();}
        page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done,resume,_finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s'
        code=""".export _align_call
.import _gfx_line, _index, _align_kind, pushax, pusha
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
 jsr _gfx_line
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
        stub='''.export _gfx_hline, _gfx_vline, _hgr_line
.import _records, _index, incsp3, incsp4, incsp5
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.code
'''
        for name,kind,stack,cleanup in (
                ('_gfx_hline',1,(4,5,1,2),4),
                ('_gfx_vline',2,(3,1,2),3),
                ('_hgr_line',3,(4,5,3,1,2),5)):
            stub+=f'{name}:\n ldx _index\n sta _records+1536,x\n'
            if kind==1:stub+=' sta _records+768,x\n'
            for offset,plane in enumerate(stack):
                stub+=f' ldy #{offset}\n lda (sp),y\n sta _records+{plane*256},x\n'
            if kind==2:stub+=' lda _records+256,x\n sta _records+1024,x\n lda _records+512,x\n sta _records+1280,x\n'
            stub+=f' lda #{kind}\n sta _records,x\n jsr scratch\n jmp incsp{cleanup}\n'
        stub+='scratch: lda #$5a\n'
        for symbol in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {symbol}\n'
        stub+=' tax\n tay\n rts\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o'
        run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'entry.o',work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(3588):
            steps += [labels.until('_page_done'),labels.peek('_records',1792),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==3588
        for index,cases in enumerate(batches()):
            assert result.dumps[index]==expected(cases),('dispatch batch',index,cases[0])
        print(f'GFX line entry: 918,528 calls, full x words in both orders, all y pairs, '
              f'axis priority, exact arguments, hostile scratch, guards and 1,024 stack placements; IIe={args.iie}.')


if __name__=='__main__':main()
