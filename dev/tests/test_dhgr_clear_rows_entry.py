#!/usr/bin/env python3
"""DHGR row-clear arguments, rejected calls, clipping and software-stack pages."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def batches():
    for y in range(256):yield [(y,rows,42) for rows in range(256)]
    yield [(190,255,color) for color in range(256)]
    yield [(255,255,color) for color in range(256)]
    for case in ((40,1,255),(191,255,249),(40,0,42),(255,255,42)):
        yield [case]*256


def expected(cases):
    output=bytearray([0]*256+[0xA5]*768)
    for index,(y,rows,color) in enumerate(cases):
        if y>=192 or not rows:continue
        for plane,value in enumerate((3,color,y,min(rows,192-y))):
            output[plane*256+index]=value
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-rows-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "dhgr.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[4][256],index,align_mode;
static void prepare(void) {
    records[0][index]=0;
    records[1][index]=records[2][index]=records[3][index]=0xA5u;
}
int main(void) {
    unsigned y,value;
    volatile unsigned guard=0xA55Au;
    for(y=0;y<256;++y) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;prepare();dhgr_clear_rows((unsigned char)y,index,42);
            if(guard!=0xA55Au)for(;;) {}
        }
        page_done();
    }
    for(value=0;value<256;++value) {
        index=(unsigned char)value;prepare();dhgr_clear_rows(190,255,index);
    }
    page_done();
    for(value=0;value<256;++value) {
        index=(unsigned char)value;prepare();dhgr_clear_rows(255,255,index);
    }
    page_done();
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
.import _index, _align_mode, _dhgr_clear_rows
.importzp sp
.rodata
ys: .byte 40,191,40,255
counts: .byte 1,255,0,255
colors: .byte 255,249,42,42
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
 lda counts,x
 sta (sp),y
 iny
 lda ys,x
 sta (sp),y
 iny
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda colors,x
 jsr _dhgr_clear_rows
 clc
 lda _index
 adc #2
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
        stub='''.export _dhgr_prepare_pattern, _dhgr_clear_rows_asm
.import _records, _index
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.bss
saved_y: .res 1
saved_rows: .res 1
.code
_dhgr_prepare_pattern:
 ldx _index
 sta _records+256,x
 lda #1
 sta _records,x
 lda #$a5
'''
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=''' tax
 tay
 rts
_dhgr_clear_rows_asm:
 sta saved_y
 stx saved_rows
 ldx _index
 lda _records,x
 cmp #1
 bne fail
 lda #3
 sta _records,x
 lda saved_y
 sta _records+512,x
 lda saved_rows
 sta _records+768,x
 rts
fail: jmp fail
'''
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',work/'entry.o',
             work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        cases=list(batches());steps=[]
        for _ in cases:
            steps += [labels.until('_page_done'),labels.peek('_records',1024),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==len(cases)
        for index,batch in enumerate(cases):
            assert result.dumps[index]==expected(batch),('DHGR rows batch',index,batch[0])
        print(f'DHGR clear rows entry: {len(cases)*256:,} calls, all y/count pairs, every color, '
              f'clipping/rejection, scratch clobbers and 1,024 stack placements; IIe={args.iie}.')


if __name__=='__main__':
    main()
