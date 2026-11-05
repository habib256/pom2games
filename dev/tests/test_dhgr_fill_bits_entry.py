#!/usr/bin/env python3
"""Monochrome DHGR forwarding: all argument bits, truth values and stack pages."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def batches():
    for high in range(256):
        yield [(v,255,65535,255,v&255) for v in range(high*256,(high+1)*256)]
    for high in range(256):
        yield [(65535,191,v,0,42) for v in range(high*256,(high+1)*256)]
    yield [(559,v,0,255,v) for v in range(256)]
    yield [(513,190,16,v,v) for v in range(256)]
    yield [(3,4,16,1,v) for v in range(256)]
    yield [(65535,255,0,0,v) for v in range(256)]
    for case in ((3,4,16,1,0),(559,191,65535,255,255),
                 (65535,255,0,0,1),(513,190,32768,128,128)):
        yield [case]*256


def expected(cases):
    output=bytearray(11*256)
    for index,(x,y,width,height,set_bit) in enumerate(cases):
        values=(1,x&255,x>>8,y,width&255,width>>8,height,*((127 if set_bit else 0,)*4))
        for plane,value in enumerate(values):output[plane*256+index]=value
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-mono-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "dhgr_internal.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[11][256],index,align_mode;
static void prepare(void) {
    unsigned char j;records[0][index]=0;
    for(j=1;j<11;++j)records[j][index]=0xA5u;
    for(j=0;j<4;++j)dhgr_pattern[j]=0xA5u;
}
int main(void) {
    unsigned value;
    unsigned char mode;
    volatile unsigned guard=0xA55Au;
    for(mode=0;mode<6;++mode) {
        value=0;
        do {
            index=(unsigned char)value;prepare();
            if(mode==0)dhgr_fill_bits(value,255,65535u,255,index);
            if(mode==1)dhgr_fill_bits(65535u,191,value,0,42);
            if(mode==2)dhgr_fill_bits(559,index,0,255,index);
            if(mode==3)dhgr_fill_bits(513,190,16,index,index);
            if(mode==4)dhgr_fill_bits(3,4,16,1,index);
            if(mode==5)dhgr_fill_bits(65535u,255,0,0,index);
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value && (mode<2 || value<256));
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
.import _index, _align_mode, _dhgr_fill_bits
.importzp sp
.rodata
heights: .byte 1,255,0,128
wlo: .byte 16,255,0,0
whi: .byte 0,255,0,128
ys: .byte 4,191,255,190
xlo: .byte 3,47,255,1
xhi: .byte 0,2,255,2
sets: .byte 0,255,1,128
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
 lda sets,x
 jsr _dhgr_fill_bits
 clc
 lda _index
 adc #6
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
        stub='''.export _dhgr_bit_rect, _dhgr_pattern
.import _records, _index, addysp
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.bss
_dhgr_pattern: .res 4
saved_height: .res 1
.code
_dhgr_bit_rect:
 sta saved_height
 ldx _index
 lda _records,x
 bne fail
 lda #1
 sta _records,x
 lda saved_height
 sta _records+1536,x
'''
        for slot,plane in enumerate((4,5,3,1,2)):
            stub+=f' ldy #{slot}\n lda (sp),y\n sta _records+{plane*256},x\n'
        for i in range(4):
            stub+=f' lda _dhgr_pattern+{i}\n sta _records+{(7+i)*256},x\n'
        stub+=' lda #$a5\n'
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n ldy #5\n jmp addysp\nfail: jmp fail\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',work/'entry.o',
             work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        cases=list(batches());steps=[]
        for _ in cases:
            steps += [labels.until('_page_done'),labels.peek('_records',2816),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==len(cases)
        for index,batch in enumerate(cases):
            assert result.dumps[index]==expected(batch),('DHGR mono batch',index,batch[0])
        print(f'DHGR monochrome entry: {len(cases)*256:,} calls, all x/width/y/height/set bits, '
              f'raw forwarding and four-byte patterns including rejected geometry, '
              f'scratch/caller guards and 1,024 stack placements; IIe={args.iie}.')


if __name__=='__main__':
    main()
