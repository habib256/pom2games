#!/usr/bin/env python3
"""All signed HGR values through the C ABI, including stack page boundaries."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-signed-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "hgr.h"
void page_done(void); void finished(void); void align_call(void); void aligned_done(void);
unsigned bits;
unsigned char records[7][256],position;
int main(void) {
    unsigned i;
    volatile unsigned guard=0xA55Au;
    bits=0;
    do {
        if((unsigned char)bits==0)
            for(i=0;i<1792;++i) ((unsigned char *)records)[i]=0xA5u;
        hgr_puti(bits,(unsigned char)bits,(int)bits);
        if(guard!=0xA55Au) for(;;) {}
        ++bits;
        if((unsigned char)bits==0) page_done();
    } while(bits);
    /* Exercise every stack position for both signs and a zero low byte. */
    for(i=0;i<4;++i) {
        bits=i==0?0u:i==1?32767u:i==2?32768u:65535u;
        position=0;
        do {align_call();aligned_done();++position;} while(position);
        if(guard!=0xA55Au) for(;;) {}
    }
    finished();
    for(;;) {}
    return 0;
}
''')
        marker=work/'marker.s'
        marker.write_text('.export _page_done, resume, _finished, _aligned_done, resume_align\n.code\n'
                          '_page_done: nop\nresume: rts\n_finished: rts\n'
                          '_aligned_done: nop\nresume_align: rts\n')
        align=work/'align.s'
        align.write_text('''.export _align_call
.import _bits, _position, _hgr_puti
.importzp sp
.bss
saved_sp: .res 2
.code
_align_call:
 lda sp
 sta saved_sp
 lda sp+1
 sta saved_sp+1
 lda _position
 sta sp
 lda #$91
 sta sp+1
 ldy #0
 lda _bits
 sta (sp),y
 iny
 sta (sp),y
 iny
 lda _bits+1
 sta (sp),y
 iny
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda _bits
 ldx _bits+1
 jsr _hgr_puti
 clc
 lda _position
 adc #3
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
        # Capture the exact string passed to the text API and validate x/y.
        stub='''.export _hgr_puts
.import _bits, _records, incsp3
.importzp sp, ptr1
.code
_hgr_puts:
 sta ptr1
 stx ptr1+1
 ldy #0
 lda (sp),y
 cmp _bits
 bne fail
 iny
 lda (sp),y
 cmp _bits
 bne fail
 iny
 lda (sp),y
 cmp _bits+1
 bne fail
 ldx _bits
 ldy #0
'''
        for plane in range(7):
            stub+=f' lda (ptr1),y\n sta _records+{plane*256},x\n beq done\n iny\n'
        stub+='fail: jmp fail\ndone: jmp incsp3\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'entry.o',work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(256):
            steps += [labels.until('_page_done'),labels.peek('_records',1792),labels.until('resume')]
        # Observe every alignment call; the C loop advances position afterward.
        for bits in (0,32767,32768,65535):
            for position in range(256):
                steps += [labels.until('_aligned_done'),labels.peek('_records',1792),labels.until('resume_align')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        for high in range(256):
            expected=bytearray([0xA5]*1792)
            for low in range(256):
                bits=high*256+low;value=bits-65536 if bits>=32768 else bits
                for index,char in enumerate(str(value).encode()+b'\0'):
                    expected[index*256+low]=char
            assert result.dumps[high]==expected,('signed strings',high)
        for index,block in enumerate(result.dumps[256:]):
            bits=(0,32767,32768,65535)[index//256]
            value=bits-65536 if bits>=32768 else bits
            digits=bytes(block[plane*256+(bits&255)] for plane in range(7))
            assert digits.startswith(str(value).encode()+b'\0'),('stack alignment',bits,index%256)
        assert len(result.dumps)==1280
        print(f'HGR signed entry: all 65,536 strings, NULs/tails, x/y arguments, '
              f'1,024 stack alignments and caller guards; IIe={args.iie}.')


if __name__=='__main__':
    main()
