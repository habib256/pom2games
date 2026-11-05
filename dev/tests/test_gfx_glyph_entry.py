#!/usr/bin/env python3
"""GFX HGR cell forwarding: complete byte domains, wrap rules and local strings."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def batches():
    for high in range(256):yield [(65,high,v) for v in range(256)]
    for high in range(256):yield [(high,v,255) for v in range(256)]
    for high in range(256):yield [(high,255,v) for v in range(256)]
    for case in ((0,0,0),(65,34,23),(255,255,255),(90,35,32)):yield [case]*256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-glyph-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "gfx.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[6][256],index,align_mode;
static void prepare(void) {
    unsigned char j;records[0][index]=0;for(j=1;j<6;++j)records[j][index]=0xA5u;
}
int main(void) {
    unsigned value;unsigned char mode;
    volatile unsigned guard=0xA55Au;
    if(gfx_text_cols!=35 || gfx_text_rows!=24)for(;;) {}
    for(mode=0;mode<3;++mode) {
        value=0;
        do {
            index=(unsigned char)value;prepare();gfx_cell_color(index);
            if(mode==0)gfx_cell_glyph(65,(unsigned char)(value>>8),index);
            if(mode==1)gfx_cell_glyph((char)(value>>8),index,255);
            if(mode==2)gfx_cell_glyph((char)(value>>8),255,index);
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    for(align_mode=0;align_mode<4;++align_mode) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;prepare();align_call();
            if(guard!=0xA55Au)for(;;) {}
        }
        page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _align_mode, _gfx_cell_glyph
.importzp sp
.rodata
chars: .byte 0,65,255,90
cols: .byte 0,34,255,35
rows: .byte 0,23,255,32
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
 lda cols,x
 sta (sp),y
 iny
 lda chars,x
 sta (sp),y
 iny
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda rows,x
 jsr _gfx_cell_glyph
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
        stub='''.export _hgr_puts8
.import _records, _index, addysp
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.code
_hgr_puts8:
 sta ptr1
 stx ptr1+1
 ldx _index
 lda _records,x
 bne fail
 lda #1
 sta _records,x
 ldy #0
 lda (sp),y
 sta _records+768,x
 iny
 lda (sp),y
 sta _records+256,x
 iny
 lda (sp),y
 sta _records+512,x
 ldy #0
 lda (ptr1),y
 sta _records+1024,x
 iny
 lda (ptr1),y
 sta _records+1280,x
 lda #$a5
'''
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n ldy #3\n jmp addysp\nfail: jmp fail\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',work/'entry.o',
             work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        cases=list(batches());steps=[]
        for _ in cases:steps += [labels.until('_page_done'),labels.peek('_records',1536),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==len(cases)
        for batch,values in enumerate(cases):
            expected=bytes((1,(col*8)&255,col>>5,(row*8)&255,ch,0)[plane]
                           for plane in range(6) for ch,col,row in values)
            assert result.dumps[batch]==expected,('glyph forwarding',batch)
        print(f'GFX HGR glyph: 197,632 calls, all col/row, char/col and char/row pairs, '
              f'full-width x and wrapped y, two-byte strings, no-op colors, scratch/caller guards '
              f'and 1,024 stack placements; IIe={args.iie}.')


if __name__=='__main__':main()
