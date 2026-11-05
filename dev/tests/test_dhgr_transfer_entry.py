#!/usr/bin/env python3
"""DHGR block control: every geometry byte, pointer and row, with hostile callees."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-transfer-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        offsets=[((y&7)<<10)+((y&0x38)<<4)+(y>>6)*40 for y in range(192)]
        source.write_text('''#include "dhgr_internal.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char bx,yy,width,height,stride,read_mode,index,align_mode,aligned;
unsigned pointer_value,expected_pointer;
unsigned char expected_y,expected_count,expected_rows,rows,valid;
static const unsigned offsets[192]={'''+','.join(map(str,offsets))+'''};
static void fail(void) {for(;;) {}}
void row_check(void) {
    unsigned address;
    if(rows>=expected_rows)fail();
    address=((unsigned)dhgr_base<<8)+offsets[expected_y]+(bx>>1);
    if((unsigned)dhgr_addr!=address || (unsigned)dhgr_buffer!=expected_pointer ||
       dhgr_aux!=(unsigned char)(1-(bx&1)) || dhgr_count!=expected_count)fail();
    ++rows;++expected_y;expected_pointer+=stride;
}
static void check(void) {
    volatile unsigned guard=0xA55Au;
    dhgr_base=(index&1)?0x40:0x20;dhgr_display=0xA5u;
    dhgr_addr=(unsigned char*)0xA55Au;dhgr_buffer=(unsigned char*)0x5AA5u;
    dhgr_aux=0xA5u;dhgr_count=0xA5u;
    rows=0;expected_y=yy;expected_pointer=pointer_value;
    valid=bx<80 && yy<192 && width && width<=stride;
    expected_count=valid?(width>80-bx?80-bx:width):0xA5u;
    expected_rows=valid?(height>192-yy?192-yy:height):0;
    if(aligned)align_call();
    else if(read_mode)dhgr_read_block(bx,yy,width,height,(unsigned char*)pointer_value,stride);
    else dhgr_write_block(bx,yy,width,height,(unsigned char*)pointer_value,stride);
    if(rows!=expected_rows || dhgr_count!=expected_count || guard!=0xA55Au ||
       dhgr_base!=((index&1)?0x40:0x20) || dhgr_display!=0xA5u)fail();
    if(!rows) {
        if((unsigned)dhgr_addr!=0xA55Au || (unsigned)dhgr_buffer!=0x5AA5u || dhgr_aux!=0xA5u)fail();
    } else {
        if((unsigned)dhgr_addr!=((unsigned)dhgr_base<<8)+offsets[expected_y-1]+(bx>>1) ||
           (unsigned)dhgr_buffer!=(unsigned)(expected_pointer-stride) ||
           dhgr_aux!=(unsigned char)(1-(bx&1)))fail();
    }
}
int main(void) {
    unsigned value;unsigned char mode;
    aligned=0;
    for(read_mode=0;read_mode<2;++read_mode)for(mode=0;mode<4;++mode) {
        value=0;
        do {
            index=(unsigned char)value;
            bx=1;yy=191;width=1;height=1;stride=255;pointer_value=65535u;
            if(mode==0){bx=(unsigned char)(value>>8);width=index;}
            if(mode==1){bx=79;width=(unsigned char)(value>>8);stride=index;height=3;yy=189;}
            if(mode==2){yy=(unsigned char)(value>>8);height=index;pointer_value=65280u;}
            if(mode==3){bx=78;yy=189;width=2;height=3;pointer_value=value;}
            check();++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    aligned=1;
    for(read_mode=0;read_mode<2;++read_mode)for(align_mode=0;align_mode<4;++align_mode) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;
            bx=0;yy=0;width=1;height=1;pointer_value=0;stride=1;
            if(align_mode==1){bx=79;yy=190;width=255;height=255;pointer_value=65534u;stride=255;}
            if(align_mode==2){bx=255;yy=255;width=0;height=0;pointer_value=65535u;stride=0;}
            if(align_mode==3){bx=1;yy=191;width=0;height=1;pointer_value=291;stride=255;}
            check();
        }
        page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _bx, _yy, _width, _height, _pointer_value, _stride, _read_mode
.import _dhgr_read_block, _dhgr_write_block
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
 lda _pointer_value
 sta (sp),y
 iny
 lda _pointer_value+1
 sta (sp),y
 iny
 lda _height
 sta (sp),y
 iny
 lda _width
 sta (sp),y
 iny
 lda _yy
 sta (sp),y
 iny
 lda _bx
 sta (sp),y
 iny
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda _read_mode
 beq write
 lda _stride
 jsr _dhgr_read_block
 jmp check
write:
 lda _stride
 jsr _dhgr_write_block
check:
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
        stub='''.export _dhgr_read_block_asm, _dhgr_write_block_asm
.import _row_check, _read_mode
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.code
_dhgr_read_block_asm:
 lda _read_mode
 beq fail
 bne check
_dhgr_write_block_asm:
 lda _read_mode
 bne fail
check:
 jsr _row_check
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
        steps=[]
        for _ in range(2056):steps += [labels.until('_page_done',10000),labels.until('resume')]
        steps += [labels.until('_finished')]
        # The exhaustive row callbacks can exceed two host minutes on the
        # IIe core under load. Guest breakpoint limits and assertions stay fixed.
        a2test.run(disk,steps,iie=args.iie,timeout=300)
        print(f'DHGR transfers: 526,336 calls, all bx/width, width/stride and y/height pairs, '
              f'all pointers, every row address/bank/count/buffer, read/write selection, '
              f'zero-height/rejected state, scratch/caller guards and 2,048 stack placements; IIe={args.iie}.')


if __name__=='__main__':main()
