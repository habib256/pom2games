#!/usr/bin/env python3
"""All hexadecimal HGR values through the C ABI, including stack page boundaries."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test, fonts, text


def rendering(work,iie):
    cases=[(x,y,v) for v in (0,15,16,255,256,4095,4096,65535)
           for x,y in ((0,0),(6,176),(250,176),(264,176),(65535,0),(0,177))]
    source=work/'render.c'
    source.write_text('''#include "hgr.h"
void painted(void);
static const struct {unsigned x; unsigned char y; unsigned value;} cases[]={'''
        +','.join('{%du,%d,%du}'%case for case in cases)+'''};
int main(void) {
    unsigned char page,i;
    for(page=1;page<=2;++page) for(i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
        hgr_set_draw_page(1);hgr_clear(0xA5);
        hgr_set_draw_page(2);hgr_clear(0xDA);
        hgr_set_draw_page(page);
        hgr_putx(cases[i].x,cases[i].y,cases[i].value);
        painted();
    }
    for(;;) {}
    return 0;
}
''')
    marker=work/'paint.s'
    marker.write_text('.export _painted, resume\n.code\n_painted: nop\nresume: rts\n')
    disk=build(work,source,extra_sources=(marker,));labels=a2test.labels(work/'test.lbl')
    steps=[]
    for _ in range(2*len(cases)):
        steps += [labels.until('_painted'),'peek:2000:16384',labels.until('resume')]
    result=a2test.run(disk,steps,iie=iie);font=bytes(fonts.glyphs(32,127))
    for scene in range(2*len(cases)):
        page,index=divmod(scene,len(cases));x,y,value=cases[index]
        pages=[bytearray([0xA5]*8192),bytearray([0xDA]*8192)]
        text(pages[page],font,x,y,f'{value:X}',2)
        assert result.dumps[scene]==pages[0]+pages[1],('hex pixels',page,x,y,value)
    print('HGR hex rendering: 96 scenes, digit boundaries, clipping/rejection, '
          'both pages, palette and screen holes OK.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-hex-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "hgr.h"
void page_done(void); void finished(void); void align_call(void); void aligned_done(void);
unsigned bits;
unsigned char records[5][256],position;
int main(void) {
    unsigned i;
    volatile unsigned guard=0xA55Au;
    bits=0;
    do {
        if((unsigned char)bits==0)
            for(i=0;i<1280;++i) ((unsigned char *)records)[i]=0xA5u;
        hgr_putx(bits,(unsigned char)bits,bits);
        if(guard!=0xA55Au) for(;;) {}
        ++bits;
        if((unsigned char)bits==0) page_done();
    } while(bits);
    /* Exercise every stack position for one/four digits and a zero low byte. */
    for(i=0;i<4;++i) {
        bits=i==0?0u:i==1?15u:i==2?4096u:65535u;
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
.import _bits, _position, _hgr_putx
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
 jsr _hgr_putx
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
        for plane in range(5):
            stub+=f' lda (ptr1),y\n sta _records+{plane*256},x\n beq done\n iny\n'
        stub+='fail: jmp fail\ndone: jmp incsp3\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'entry.o',work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(256):
            steps += [labels.until('_page_done'),labels.peek('_records',1280),labels.until('resume')]
        # Observe every alignment call; the C loop advances position afterward.
        for bits in (0,15,4096,65535):
            for position in range(256):
                steps += [labels.until('_aligned_done'),labels.peek('_records',1280),labels.until('resume_align')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        for high in range(256):
            expected=bytearray([0xA5]*1280)
            for low in range(256):
                bits=high*256+low
                for index,char in enumerate(f'{bits:X}'.encode()+b'\0'):
                    expected[index*256+low]=char
            assert result.dumps[high]==expected,('hex strings',high)
        for index,block in enumerate(result.dumps[256:]):
            bits=(0,15,4096,65535)[index//256]
            digits=bytes(block[plane*256+(bits&255)] for plane in range(5))
            assert digits.startswith(f'{bits:X}'.encode()+b'\0'),('stack alignment',bits,index%256)
        assert len(result.dumps)==1280
        print(f'HGR hexadecimal entry: all 65,536 strings, NULs/tails, x/y arguments, '
              f'1,024 stack alignments and caller guards; IIe={args.iie}.')
        rendering(work,args.iie)


if __name__=='__main__':
    main()
