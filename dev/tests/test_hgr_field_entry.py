#!/usr/bin/env python3
"""HGR fields: decimal strings, erase/text arguments, clipping and scratch lifetime."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def batches():
    for high in range(256):yield [(6,176,v,14) for v in range(high*256,(high+1)*256)]
    for high in range(256):yield [(x,176,42,14) for x in range(high*256,(high+1)*256)]
    yield [(250,176,42,w) for w in range(256)]
    yield [(279,y,65535,1) for y in range(256)]
    yield [(250,176,42,14)]*256
    yield [(65535,255,65535,0)]*256


def expected(cases):
    output=bytearray([0]*256+[0xA5]*(13*256))
    for index,(x,y,value,width) in enumerate(cases):
        if not width or x>=280 or y>=192:continue
        width=min(width,14);digits=str(value).encode()+b'\0'
        tx=x+max(0,width-(len(digits)-1))*18
        params=(3,width*18-2,y,x&255,x>>8,y,tx&255,tx>>8,*digits)
        for plane,value in enumerate(params):output[plane*256+index]=value
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-field-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "hgr.h"
void page_done(void); void finished(void); void align_call(void);
unsigned char records[14][256],index,align_mode;
static void clear_slot(void) {
    unsigned char i;
    records[0][index]=0;
    for(i=1;i<14;++i) records[i][index]=0xA5u;
}
int main(void) {
    unsigned value;
    unsigned char field;
    volatile unsigned guard=0xA55Au;
    for(field=0;field<4;++field) {
        value=0;
        do {
            index=(unsigned char)value;clear_slot();
            if(field==0) hgr_putu_field(6,176,value,14);
            if(field==1) hgr_putu_field(value,176,42,14);
            if(field==2) hgr_putu_field(250,176,42,index);
            if(field==3) hgr_putu_field(279,index,65535u,1);
            if(guard!=0xA55Au) for(;;) {}
            ++value;
            if((unsigned char)value==0) page_done();
        } while(value && (field<2 || value<256));
    }
    for(align_mode=0;align_mode<2;++align_mode) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;clear_slot();align_call();
            if(guard!=0xA55Au) for(;;) {}
        }
        page_done();
    }
    finished();
    for(;;) {}
    return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n'
                                               '_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s'
        align.write_text('''.export _align_call
.import _index, _align_mode, _hgr_putu_field
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
 lda #$ff
 ldy #4
args: sta (sp),y
 dey
 bpl args
 lda _align_mode
 bne guards
 ldy #0
 lda #42
 sta (sp),y
 iny
 lda #0
 sta (sp),y
 iny
 lda #176
 sta (sp),y
 iny
 lda #250
 sta (sp),y
 iny
 lda #0
 sta (sp),y
guards:
 lda #$a5
 ldy #5
 sta (sp),y
 iny
 sta (sp),y
 lda #0
 ldx _align_mode
 bne call
 lda #14
call:
 jsr _hgr_putu_field
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
        stub='''.export _hgr_clear_pixrect, _hgr_puts
.import _records, _index, incsp3, incsp4
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.code
_hgr_clear_pixrect:
 cmp #16
 bne fail_clear
 ldx _index
 lda #1
 sta _records,x
'''
        for slot in range(4):
            stub+=f' ldy #{slot}\n lda (sp),y\n sta _records+{256*(slot+1)},x\n'
        # The real erase call may destroy every ordinary cc65 scratch byte.
        stub+=' lda #$a5\n'
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' jmp incsp4\nfail_clear: jmp fail_clear\n_hgr_puts:\n sta ptr1\n stx ptr1+1\n ldx _index\n lda _records,x\n cmp #1\n bne fail_text\n lda #3\n sta _records,x\n'
        for slot in range(3):
            stub+=f' ldy #{slot}\n lda (sp),y\n sta _records+{256*(slot+5)},x\n'
        stub+=' ldy #0\n'
        for plane in range(8,14):
            stub+=f' lda (ptr1),y\n sta _records+{256*plane},x\n beq done\n iny\n'
        stub+='fail_text: jmp fail_text\ndone: jmp incsp3\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',work/'entry.o',
             work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(516):
            steps += [labels.until('_page_done'),labels.peek('_records',3584),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==516
        for index,cases in enumerate(batches()):
            assert result.dumps[index]==expected(cases),('field batch',index,cases[0])
        print(f'HGR field entry: 131,584 calls, every value/x/y/width, decimal buffer, '
              f'erase-before-text, alignment, rejection, 512 stack placements and scratch/caller guards; IIe={args.iie}.')


if __name__=='__main__':
    main()
