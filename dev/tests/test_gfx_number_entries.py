#!/usr/bin/env python3
"""All GFX numeric text values, terminated strings, scratch and stack crossings."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def encoded(kind,value):
    s=str(value) if kind==0 else str(value if value<32768 else value-65536) if kind==1 else format(value,'X')
    return (s.encode()+b'\0').ljust(7,b'\xa5')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-number-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "gfx.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[7][256],index,kind;
unsigned value;
static void prepare(void) {unsigned char j;for(j=0;j<7;++j)records[j][index]=0xA5u;}
int main(void) {
    unsigned i;unsigned char mode;
    static const unsigned values[]={0,65535u,32768u,15};
    volatile unsigned guard=0xA55Au;
    for(kind=0;kind<3;++kind) {
        value=0;
        do {
            index=(unsigned char)value;prepare();
            if(kind==0)gfx_putu(value);else if(kind==1)gfx_puti((int)value);else gfx_putx(value);
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    for(kind=0;kind<3;++kind)for(mode=0;mode<4;++mode) {
        value=values[mode];
        for(i=0;i<256;++i) {
            index=(unsigned char)i;prepare();align_call();
            if(guard!=0xA55Au)for(;;) {}
        }
        page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _kind, _value, _gfx_putu, _gfx_puti, _gfx_putx
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
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 ldy _kind
 lda _value
 ldx _value+1
 cpy #0
 bne signed
 jsr _gfx_putu
 jmp check
signed:
 cpy #1
 bne hex
 jsr _gfx_puti
 jmp check
hex:
 jsr _gfx_putx
check:
 lda _index
 cmp sp
 bne fail
 lda #$91
 cmp sp+1
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
        stub='''.export _gfx_text
.import _records, _index
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.code
_gfx_text:
 sta ptr1
 stx ptr1+1
 clc
 lda #<_records
 adc _index
 sta ptr2
 lda #>_records
 adc #0
 sta ptr2+1
 ldx #7
 ldy #0
copy:
 lda (ptr1),y
 sta (ptr2),y
 beq done
 inc ptr1
 bne :+
 inc ptr1+1
: inc ptr2+1
 dex
 bne copy
fail: jmp fail
done:
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
        cases=[(kind,list(range(high*256,(high+1)*256))) for kind in range(3) for high in range(256)]
        cases += [(kind,[value]*256) for kind in range(3) for value in (0,65535,32768,15)]
        steps=[]
        for _ in cases:steps += [labels.until('_page_done'),labels.peek('_records',1792),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==len(cases)
        for batch,(kind,values) in enumerate(cases):
            expected=bytes(encoded(kind,value)[plane] for plane in range(7) for value in values)
            assert result.dumps[batch]==expected,('numeric string',kind,batch)
        print(f'GFX numeric text: 199,680 calls, all unsigned/signed/hex words, NULs, '
              f'text scratch clobbers, guards and 3,072 stack placements; IIe={args.iie}.')


if __name__=='__main__':main()
