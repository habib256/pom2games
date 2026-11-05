#!/usr/bin/env python3
"""Every DHGR pixel, all invalid 16-bit x values, banks, IRQ masks and stack pages."""
import argparse
import subprocess
import tempfile
from pathlib import Path
from test_hgr import build, a2test
from test_dhgr import pixel


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iic',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-points-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "dhgr.h"
void row_done(void);void page_done(void);void finished(void);void align_call(void);
unsigned char index,align_mode,expected_irq,irq,result;
static void fail(void) {for(;;) {}}
static void check_irq(void) {
    asm("php");asm("pla");asm("and #$04");asm("sta _irq");
    if(irq!=expected_irq)fail();
}
int main(void) {
    unsigned x,value;
    unsigned char page,y,bit;
    volatile unsigned guard=0xA55Au;
    if(!dhgr_init())fail();
    dhgr_draw_page(1);dhgr_clear(0);dhgr_draw_page(2);dhgr_clear(0);
    for(page=1;page<=2;++page) {
        dhgr_draw_page(page);expected_irq=page==1?4:0;
        if(expected_irq){asm("sei");}else{asm("cli");}
        for(y=0;y<192;++y) {
            for(x=0;x<560;++x) {
                bit=(unsigned char)(x+y);dhgr_plot(x,y,bit);
                if(dhgr_getpixel(x,y)!=(bit!=0))fail();
                check_irq();
            }
            if(guard!=0xA55Au)fail();row_done();
        }
        x=560;
        do {dhgr_plot(x,191,255);if(dhgr_getpixel(x,191))fail();check_irq();++x;}while(x);
        for(value=192;value<256;++value) {
            dhgr_plot(559,(unsigned char)value,255);
            if(dhgr_getpixel(559,(unsigned char)value))fail();check_irq();
        }
        for(align_mode=0;align_mode<4;++align_mode)for(value=0;value<256;++value) {
            index=(unsigned char)value;align_call();if(guard!=0xA55Au)fail();
        }
        page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('''.export _row_done, row_resume, _page_done, page_resume, _finished
.code
_row_done: nop
row_resume: rts
_page_done: nop
page_resume: rts
_finished: rts
''')
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _align_mode, _expected_irq, _result, _dhgr_plot, _dhgr_getpixel
.importzp sp
.macpack longbranch
.rodata
xlo: .byte 0,47,255,47
xhi: .byte 0,2,255,2
ys: .byte 0,191,191,255
.bss
saved_sp: .res 2
.code
_align_call:
 lda sp
 sta saved_sp
 lda sp+1
 sta saved_sp+1
 jsr reset
 ldx _align_mode
 ldy #0
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
 lda #0
 cpx #0
 bne plot
 lda _index
plot:
 jsr _dhgr_plot
 clc
 lda _index
 adc #3
 tax
 lda #$91
 adc #0
 jsr check_sp
 jsr reset
 ldx _align_mode
 ldy #0
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
 lda ys,x
 jsr _dhgr_getpixel
 sta _result
 cpx #0
 jne fail
 lda _align_mode
 bne zero
 lda _index
 beq zero
 lda #1
 bne expected
zero: lda #0
expected:
 cmp _result
 jne fail
 clc
 lda _index
 adc #2
 tax
 lda #$91
 adc #0
 jsr check_sp
 lda saved_sp
 sta sp
 lda saved_sp+1
 sta sp+1
 rts
reset:
 lda _index
 sta sp
 lda #$91
 sta sp+1
 rts
check_sp:
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
 php
 pla
 and #4
 cmp _expected_irq
 bne fail
 rts
fail: jmp fail
''')
        disk=build(work,source,extra_sources=(marker,align));labels=a2test.labels(work/'test.lbl')
        steps=[]
        for _ in range(2):
            for _ in range(192):steps += [labels.until('_row_done'),labels.until('row_resume')]
            steps += [labels.until('_page_done',10000),'peek:C013:2','poke:C002:0',
                      'peek:2000:16384','poke:C003:0','peek:2000:16384','poke:C002:0',
                      labels.until('page_resume')]
        steps += [labels.until('_finished')]
        page=[bytearray(8192),bytearray(8192)]
        for y in range(192):
            for x in range(560):pixel(page,x,y,int(bool((x+y)&255)))
        pixel(page,0,0,1);pixel(page,559,191,0)
        for machine in (['--iic'] if args.iic else ['--iie','--iic']):
            result=subprocess.run([str(a2test.A2SHOT),machine,'--disk',str(disk),*steps],
                                  capture_output=True,text=True,timeout=180)
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)
            dumps=a2test.Result(result.stdout).dumps
            assert len(dumps)==6
            for stage in range(2):
                assert not any(v&128 for v in dumps[stage*3]),('banks',machine,stage)
                for bank in range(2):
                    expected=page[bank]+(page[bank] if stage else bytes(8192))
                    assert dumps[stage*3+1+bank]==expected,(machine,stage,bank)
            print(f'DHGR points {machine[2:]}: 694,336 calls, every pixel on both pages, all selectors, '
                  f'all invalid x words/y bytes, banks/holes, IRQ masks, ABI returns and 2,048 stack placements.')


if __name__=='__main__':main()
