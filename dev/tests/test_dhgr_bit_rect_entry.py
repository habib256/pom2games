#!/usr/bin/env python3
"""DHGR rectangle preparation: full 16-bit domains, bounds and untouched rejected state."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def batches():
    for mode in range(5):
        for high in range(256):
            values=range(high*256,(high+1)*256)
            if mode==0:yield [(v,191,65535,255) for v in values]
            if mode==1:yield [(0,0,v,1) for v in values]
            if mode==2:yield [(559,191,v,255) for v in values]
            if mode==3:yield [(513,high,65535,v&255) for v in values]
            if mode==4:yield [(v,0,1,1) for v in values]
    for case in ((3,4,16,1),(559,191,65535,255),(65535,0,1,1),(0,0,1,0)):
        yield [case]*256


def expected(cases):
    output=bytearray([0]*256+[0xA5]*(6*256))
    for index,(x,y,width,height) in enumerate(cases):
        if x>=560 or y>=192 or not width or not height:continue
        end=min(x+width-1,559)
        for plane,value in enumerate((1,x&255,x>>8,end&255,end>>8,y,min(height,192-y))):
            output[plane*256+index]=value
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-rect-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "dhgr_internal.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[7][256],index,align_mode;
static void prepare(void) {
    records[0][index]=0;records[5][index]=records[6][index]=0xA5u;
    dhgr_span_x=dhgr_span_end=0xA5A5u;
}
static void record(void) {
    records[1][index]=(unsigned char)dhgr_span_x;
    records[2][index]=(unsigned char)(dhgr_span_x>>8);
    records[3][index]=(unsigned char)dhgr_span_end;
    records[4][index]=(unsigned char)(dhgr_span_end>>8);
}
int main(void) {
    unsigned value;
    unsigned char mode;
    volatile unsigned guard=0xA55Au;
    for(mode=0;mode<5;++mode) {
        value=0;
        do {
            index=(unsigned char)value;prepare();
            if(mode==0)dhgr_bit_rect(value,191,65535u,255);
            if(mode==1)dhgr_bit_rect(0,0,value,1);
            if(mode==2)dhgr_bit_rect(559,191,value,255);
            if(mode==3)dhgr_bit_rect(513,(unsigned char)(value>>8),65535u,index);
            if(mode==4)dhgr_bit_rect(value,0,1,1);
            record();if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    for(align_mode=0;align_mode<4;++align_mode) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;prepare();align_call();record();
            if(guard!=0xA55Au)for(;;) {}
        }
        page_done();
    }
    finished();for(;;) {} return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _align_mode, _dhgr_bit_rect
.importzp sp
.rodata
wlo: .byte 16,255,1,1
whi: .byte 0,255,0,0
ys: .byte 4,191,0,0
xlo: .byte 3,47,255,0
xhi: .byte 0,2,255,0
heights: .byte 1,255,1,0
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
 lda wlo,x
 sta (sp),y
 iny
 lda whi,x
 sta (sp),y
 iny
 lda ys,x
 sta (sp),y
 iny
 lda xlo,x
 sta (sp),y
 iny
 lda xhi,x
 sta (sp),y
 iny
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda heights,x
 jsr _dhgr_bit_rect
 clc
 lda _index
 adc #5
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
        stub='''.export _dhgr_span_asm, _dhgr_span_x, _dhgr_span_end
.import _records, _index
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.bss
_dhgr_span_x: .res 2
_dhgr_span_end: .res 2
saved_y: .res 1
saved_rows: .res 1
.code
_dhgr_span_asm:
 sta saved_y
 stx saved_rows
 ldx _index
 lda _records,x
 bne fail
 lda #1
 sta _records,x
 lda saved_y
 sta _records+1280,x
 lda saved_rows
 sta _records+1536,x
 lda #$a5
'''
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n rts\nfail: jmp fail\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',work/'entry.o',
             work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        cases=list(batches());steps=[]
        for _ in cases:
            steps += [labels.until('_page_done'),labels.peek('_records',1792),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==len(cases)
        for index,batch in enumerate(cases):
            assert result.dumps[index]==expected(batch),('DHGR rectangle batch',index,batch[0])
        print(f'DHGR bit rectangle entry: {len(cases)*256:,} calls, all x and widths at both edges, '
              f'all y/height pairs, wrap-safe endpoints, rejected-state/scratch/caller guards '
              f'and 1,024 stack placements; IIe={args.iie}.')


if __name__=='__main__':
    main()
