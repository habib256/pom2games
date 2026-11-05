#!/usr/bin/env python3
"""DHGR sprite control: geometry, all phase products and pointer wraparound."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-sprite-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        offsets=[((y&7)<<10)+((y&0x38)<<4)+(y>>6)*40 for y in range(192)]
        source.write_text('''#include "dhgr_internal.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char xx,yy,width,height,stride,index,align_mode,aligned;
unsigned data_value,mask_value,expected_data,expected_mask;
unsigned char expected_y,expected_count,expected_rows,rows,valid,bx;
static const unsigned offsets[192]={'''+','.join(map(str,offsets))+'''};
static void fail(void) {for(;;) {}}
void row_check(void) {
    unsigned address;
    if(rows>=expected_rows)fail();
    address=((unsigned)dhgr_base<<8)+offsets[expected_y]+(bx>>1);
    if((unsigned)dhgr_addr!=address || (unsigned)dhgr_buffer!=expected_data ||
       (unsigned)dhgr_sprite_mask!=expected_mask || dhgr_aux!=(unsigned char)(1-(bx&1)) ||
       dhgr_count!=expected_count)fail();
    ++rows;++expected_y;expected_data+=stride;expected_mask+=stride;
}
static void check(void) {
    unsigned bank;
    unsigned char phase,n;
    volatile unsigned guard=0xA55Au;
    dhgr_base=(index&1)?0x40:0x20;dhgr_display=0xA5u;
    dhgr_addr=(unsigned char*)0xA55Au;dhgr_buffer=(unsigned char*)0x5AA5u;
    dhgr_sprite_mask=(unsigned char*)0x5678u;dhgr_aux=0xA5u;dhgr_count=0xA5u;
    rows=0;expected_rows=0;valid=xx<140 && yy<192 && width && height;
    if(valid) {
        phase=(unsigned)xx*4%7;bx=(unsigned)xx*4/7;
        n=((unsigned)width*4+phase+6)/7;
        valid=n<=stride;
        if(valid) {
            expected_count=n>80-bx?80-bx:n;
            expected_rows=height>192-yy?192-yy:height;
            expected_y=yy;bank=(unsigned)stride*height*phase;
            expected_data=data_value+bank;expected_mask=mask_value+bank;
        }
    }
    if(aligned)align_call();
    else dhgr_sprite(xx,yy,width,height,stride,(const unsigned char*)data_value,(const unsigned char*)mask_value);
    if(rows!=expected_rows || guard!=0xA55Au ||
       dhgr_base!=((index&1)?0x40:0x20) || dhgr_display!=0xA5u)fail();
    if(!rows) {
        if((unsigned)dhgr_addr!=0xA55Au || (unsigned)dhgr_buffer!=0x5AA5u ||
           (unsigned)dhgr_sprite_mask!=0x5678u || dhgr_aux!=0xA5u || dhgr_count!=0xA5u)fail();
    } else {
        if((unsigned)dhgr_addr!=((unsigned)dhgr_base<<8)+offsets[expected_y-1]+(bx>>1) ||
           (unsigned)dhgr_buffer!=(unsigned)(expected_data-stride) ||
           (unsigned)dhgr_sprite_mask!=(unsigned)(expected_mask-stride) ||
           dhgr_aux!=(unsigned char)(1-(bx&1)) || dhgr_count!=expected_count)fail();
    }
}
int main(void) {
    unsigned value;unsigned char mode;
    aligned=0;
    for(mode=0;mode<12;++mode) {
        value=0;
        do {
            index=(unsigned char)value;
            xx=1;yy=191;width=1;height=255;stride=255;data_value=65535u;mask_value=65408u;
            if(mode==0){xx=(unsigned char)(value>>8);width=index;}
            if(mode==1){xx=139;width=(unsigned char)(value>>8);stride=index;}
            if(mode==2){xx=3;yy=(unsigned char)(value>>8);height=index;stride=2;}
            if(mode==3){yy=190;data_value=value;}
            if(mode==4){yy=190;mask_value=value;}
            if(mode>=5){xx=mode-5;height=(unsigned char)(value>>8);stride=index;}
            check();++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    aligned=1;
    for(align_mode=0;align_mode<4;++align_mode) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;
            xx=0;yy=0;width=1;height=1;stride=1;data_value=0;mask_value=65535u;
            if(align_mode==1){xx=139;yy=190;width=255;height=255;stride=255;data_value=65534u;mask_value=1;}
            if(align_mode==2){xx=255;yy=255;width=0;height=0;stride=0;data_value=65535u;mask_value=0;}
            if(align_mode==3){xx=1;yy=191;width=2;height=1;stride=1;data_value=291;mask_value=65280u;}
            check();
        }
        page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _xx, _yy, _width, _height, _data_value, _mask_value, _stride, _dhgr_sprite
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
 lda _data_value
 sta (sp),y
 iny
 lda _data_value+1
 sta (sp),y
 iny
 lda _stride
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
 lda _xx
 sta (sp),y
 iny
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda _mask_value
 ldx _mask_value+1
 jsr _dhgr_sprite
 clc
 lda _index
 adc #7
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
        stub='''.export _dhgr_sprite_asm
.import _row_check
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.code
_dhgr_sprite_asm:
 jsr _row_check
 lda #$a5
'''
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n rts\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',work/'entry.o',
             work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(3076):steps += [labels.until('_page_done',10000),labels.until('resume')]
        steps += [labels.until('_finished')]
        a2test.run(disk,steps,iie=args.iie)
        print(f'DHGR sprite entry: 787,456 calls, all x/width, width/stride and y/height pairs, '
              f'all data/mask pointers, all height/stride products at seven phases, every row, '
              f'rejected state, scratch/caller guards and 1,024 stack placements; IIe={args.iie}.')


if __name__=='__main__':main()
