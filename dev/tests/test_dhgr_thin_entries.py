#!/usr/bin/env python3
"""DHGR clear/small-text forwarding, complete byte domains and stack crossings."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def batches():
    for high in range(256):
        yield [(1,v&255,v>>8,42,191,0xA5) for v in range(high*256,(high+1)*256)]
    for high in range(256):
        yield [(1,0xFF,0xFF,high,v,0xA5) for v in range(256)]
    yield [(2,v,0xA5,0xA5,0xA5,1) for v in range(256)]
    for values in ((1,0,0,0,0,0xA5),(1,255,255,255,255,0xA5),
                   (2,0,0xA5,0xA5,0xA5,1),(2,255,0xA5,0xA5,0xA5,1)):
        yield [values]*256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-thin-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "dhgr_internal.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[6][256],index,align_mode;
static void prepare(void) {
    unsigned char j;records[0][index]=0;
    for(j=1;j<6;++j)records[j][index]=0xA5u;
    dhgr_small_x=0xA5u;dhgr_small_y=0xA5u;
}
int main(void) {
    unsigned value;unsigned char mode;
    volatile unsigned guard=0xA55Au;
    for(mode=0;mode<3;++mode) {
        value=0;
        do {
            index=(unsigned char)value;prepare();
            if(mode==0)dhgr_puts_small((const char*)value,42,191);
            if(mode==1)dhgr_puts_small((const char*)65535u,(unsigned char)(value>>8),index);
            if(mode==2)dhgr_clear(index);
            if(mode<2 && (dhgr_small_x!=0xD3u || dhgr_small_y!=0xE7u))for(;;) {}
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
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _align_mode, _dhgr_puts_small, _dhgr_clear
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
 ldx _align_mode
 cpx #2
 bcs clear
 txa
 beq value
 lda #255
value:
 ldy #0
 sta (sp),y
 iny
 sta (sp),y
 iny
 sta (sp),y
 pha
 iny
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 pla
 jsr _dhgr_puts_small
 clc
 lda _index
 adc #3
 tax
 lda #$91
 adc #0
 jmp check
clear:
 ldy #0
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 cpx #2
 beq zero
 lda #255
 bne call_clear
zero: lda #0
call_clear:
 jsr _dhgr_clear
 ldx _index
 lda #$91
check:
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
        stub='''.export _dhgr_small_string, _dhgr_prepare_pattern, _dhgr_clear_asm
.import _records, _index, _dhgr_small_x, _dhgr_small_y
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.bss
saved_lo: .res 1
saved_hi: .res 1
.code
_dhgr_small_string:
 sta saved_lo
 stx saved_hi
 ldx _index
 lda _records,x
 bne fail
 lda #1
 sta _records,x
 lda saved_lo
 sta _records+256,x
 lda saved_hi
 sta _records+512,x
 lda _dhgr_small_x
 sta _records+768,x
 lda _dhgr_small_y
 sta _records+1024,x
 lda #$d3
 sta _dhgr_small_x
 lda #$e7
 sta _dhgr_small_y
 jmp clobber
_dhgr_prepare_pattern:
 sta saved_lo
 ldx _index
 lda _records,x
 bne fail
 lda #1
 sta _records,x
 lda saved_lo
 sta _records+256,x
 jmp clobber
_dhgr_clear_asm:
 ldx _index
 lda _records,x
 cmp #1
 bne fail
 sta _records+1280,x
 lda #2
 sta _records,x
clobber:
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
        for _ in cases:steps += [labels.until('_page_done'),labels.peek('_records',1536),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==len(cases)
        for index,batch in enumerate(cases):
            expected=bytes(values[plane] for plane in range(6) for values in batch)
            assert result.dumps[index]==expected,('DHGR thin entry batch',index)
        print(f'DHGR thin entries: {len(cases)*256:,} calls, all pointer values, x/y pairs and colors, '
              f'call ordering, callee coordinate changes, scratch/caller guards and 1,024 stack placements; IIe={args.iie}.')


if __name__=='__main__':main()
