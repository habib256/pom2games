#!/usr/bin/env python3
"""Colour DHGR preparation: all horizontal extents, colors and stack positions."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def batches():
    for x in range(256):yield [(x,191,w,255,w) for w in range(256)]
    for x,y,w,h in ((0,255,0,0),(139,191,255,255),(140,0,1,1)):
        yield [(x,y,w,h,c) for c in range(256)]
    yield [(127,y,255,255,42) for y in range(256)]
    yield [(63,190,2,h,255) for h in range(256)]
    for case in ((3,4,4,1,9),(139,191,255,255,255),(0,255,0,0,42),(255,0,1,1,9)):
        yield [case]*256


def expected(cases):
    output=bytearray([0]*256+[0xA5]*(7*256))
    for index,(x,y,width,height,color) in enumerate(cases):
        if x>=140:continue
        bits=x*4;extent=min(width,140-x)*4
        for plane,value in enumerate((3,color,bits&255,bits>>8,y,extent&255,extent>>8,height)):
            output[plane*256+index]=value
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-color-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "dhgr.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[8][256],index,align_mode;
static void prepare(void) {
    unsigned char j;records[0][index]=0;
    for(j=1;j<8;++j)records[j][index]=0xA5u;
}
int main(void) {
    unsigned value,x;
    unsigned char mode;
    volatile unsigned guard=0xA55Au;
    for(x=0;x<256;++x) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;prepare();dhgr_fill_rect((unsigned char)x,191,index,255,index);
            if(guard!=0xA55Au)for(;;) {}
        }
        page_done();
    }
    for(mode=0;mode<5;++mode) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;prepare();
            if(mode==0)dhgr_fill_rect(0,255,0,0,index);
            if(mode==1)dhgr_fill_rect(139,191,255,255,index);
            if(mode==2)dhgr_fill_rect(140,0,1,1,index);
            if(mode==3)dhgr_fill_rect(127,index,255,255,42);
            if(mode==4)dhgr_fill_rect(63,190,2,index,255);
            if(guard!=0xA55Au)for(;;) {}
        }
        page_done();
    }
    for(align_mode=0;align_mode<4;++align_mode) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;prepare();align_call();
            if(guard!=0xA55Au)for(;;) {}
        }
        page_done();
    }
    finished();for(;;) {} return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _align_mode, _dhgr_fill_rect
.importzp sp
.rodata
heights: .byte 1,255,0,1
widths: .byte 4,255,0,1
ys: .byte 4,191,255,0
xs: .byte 3,139,0,255
colors: .byte 9,255,42,9
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
 ldx _align_mode
 ldy #0
 lda heights,x
 sta (sp),y
 iny
 lda widths,x
 sta (sp),y
 iny
 lda ys,x
 sta (sp),y
 iny
 lda xs,x
 sta (sp),y
 iny
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda colors,x
 jsr _dhgr_fill_rect
 clc
 lda _index
 adc #4
 tax
 lda #$91
 adc #0
 cmp sp+1
 bne fail
 cpx sp
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
''')
        build(work,source,extra_sources=(marker,align))
        stub='''.export _dhgr_prepare_pattern, _dhgr_bit_rect
.import _records, _index, addysp
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.bss
saved_height: .res 1
.code
_dhgr_prepare_pattern:
 ldx _index
 sta _records+256,x
 lda #1
 sta _records,x
 jsr clobber
 rts
_dhgr_bit_rect:
 sta saved_height
 ldx _index
 lda _records,x
 cmp #1
 bne fail
 lda #3
 sta _records,x
 lda saved_height
 sta _records+1792,x
'''
        for slot,plane in enumerate((5,6,4,2,3)):
            stub+=f' ldy #{slot}\n lda (sp),y\n sta _records+{plane*256},x\n'
        stub+=' jsr clobber\n ldy #5\n jmp addysp\nfail: jmp fail\nclobber:\n lda #$a5\n'
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n rts\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',work/'entry.o',
             work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        cases=list(batches());steps=[]
        for _ in cases:
            steps += [labels.until('_page_done'),labels.peek('_records',2048),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==len(cases)
        for index,batch in enumerate(cases):
            assert result.dumps[index]==expected(batch),('DHGR color batch',index,batch[0])
        print(f'DHGR colour entry: {len(cases)*256:,} calls, all x/width pairs and y/height/color bytes, '
              f'pattern-before-helper ordering, clipped bit extents, scratch/caller guards '
              f'and 1,024 stack placements; IIe={args.iie}.')


if __name__=='__main__':
    main()
