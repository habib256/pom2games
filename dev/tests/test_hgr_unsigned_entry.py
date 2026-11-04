#!/usr/bin/env python3
"""All unsigned values through both HGR number entries and the real C ABI."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test, fonts, text


def strings(work, iie):
    source=work/'numbers.c'
    source.write_text('''#include "hgr.h"
void page_done(void); void finished(void); void alignment(void);
unsigned value;
unsigned char mode, records[6][256];
int main(void) {
    unsigned i;
    volatile unsigned guard=0xA55Au;
    for(mode=0;mode<2;++mode) {
        value=0;
        do {
            if((unsigned char)value==0)
                for(i=0;i<1536;++i) ((unsigned char *)records)[i]=0xA5u;
            if(mode) hgr_putu8(value,(unsigned char)value,value);
            else hgr_putu(value,(unsigned char)value,value);
            if(guard!=0xA55Au) for(;;) {}
            ++value;
            if((unsigned char)value==0) page_done();
        } while(value);
    }
    alignment();
    if(guard!=0xA55Au) for(;;) {}
    finished();
    for(;;) {}
    return 0;
}
''')
    markers=work/'markers.s'
    markers.write_text('.export _page_done, resume, _finished\n.code\n'
                       '_page_done: nop\nresume: rts\n_finished: rts\n')
    align=work/'alignment.s'
    align.write_text('''.export _alignment
.import _mode, _value, _records, _hgr_putu, _hgr_putu8
.importzp sp
.bss
saved_sp: .res 2
position: .res 1
.code
_alignment:
 lda sp
 sta saved_sp
 lda sp+1
 sta saved_sp+1
 lda #$ff
 sta _value
 sta _value+1
 lda #0
 sta _mode
 sta position
again:
 lda position
 sta sp
 lda #$91
 sta sp+1
 ldy #2
 lda #$ff
args: sta (sp),y
 dey
 bpl args
 ldy #3
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda #$ff
 tax
 ldy _mode
 bne small
 jsr _hgr_putu
 jmp check
small:
 jsr _hgr_putu8
check:
 clc
 lda position
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
 .repeat 6, I
 lda _records+256*I+255
 cmp digits+I
 bne fail
 .endrepeat
 inc position
 beq next_mode
 jmp again
next_mode:
 inc _mode
 lda _mode
 cmp #2
 beq done
 jmp again
done:
 lda saved_sp
 sta sp
 lda saved_sp+1
 sta sp+1
 rts
fail: jmp fail
digits: .byte "65535",0
''')
    build(work,source,extra_sources=(markers,align))
    sink=work/'sink.s'
    sink.write_text('''.export _hgr_puts, _hgr_puts8
.import _records, _value, _mode, incsp3
.importzp sp, ptr1
.code
_hgr_puts:
 ldy _mode
 bne fail
 beq common
_hgr_puts8:
 ldy _mode
 beq fail
common:
 sta ptr1
 stx ptr1+1
 ldy #0
 lda (sp),y
 cmp _value
 bne fail
 iny
 lda (sp),y
 cmp _value
 bne fail
 iny
 lda (sp),y
 cmp _value+1
 bne fail
 ldx _value
 ldy #0
.repeat 6, I
 lda (ptr1),y
 sta _records+256*I,x
 beq done
 iny
.endrepeat
fail: jmp fail
done: jmp incsp3
''')
    obj=work/'sink.o';run(['ca65','-o',obj,sink])
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
         '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
         work/'numbers.o',work/'apple2io_asm.o',work/'markers.o',work/'alignment.o',obj,work/'hgrc.lib'])
    disk=a2test.build_disk(work,'TEST',work/'test.bin')
    labels=a2test.labels(work/'test.lbl')
    steps=[]
    for _ in range(512):
        steps += [labels.until('_page_done'),labels.peek('_records',1536),labels.until('resume')]
    steps += [labels.until('_finished')]
    result=a2test.run(disk,steps,iie=iie)
    assert len(result.dumps)==512
    for mode in range(2):
        for high in range(256):
            expected=bytearray([0xA5]*1536)
            for low in range(256):
                for index,char in enumerate(str(high*256+low).encode()+b'\0'):
                    expected[index*256+low]=char
            assert result.dumps[mode*256+high]==expected,(mode,high)
    print('HGR unsigned entries: 131,072 decimal strings, NULs, untouched tails, '
          'all x/y bits, font selection, 512 stack alignments and caller guards OK.')


def rendering(work, iie):
    values=(0,1,9,10,99,100,999,1000,9999,10000,32767,32768,65535)
    source=work/'render.c'
    source.write_text('''#include "hgr.h"
void painted(void);
static const unsigned values[]={'''+','.join(str(v)+'u' for v in values)+'''};
int main(void) {
    unsigned char page,small,phase,i;
    for(page=1;page<=2;++page) {
        hgr_set_draw_page(page); hgr_clear(42);
    }
    for(page=1;page<=2;++page) for(small=0;small<2;++small)
        for(phase=0;phase<7;++phase) {
            hgr_set_draw_page(page); hgr_clear(170);
            for(i=0;i<13;++i) {
                unsigned x=7u+phase+(i%3u)*84u;
                unsigned char y=8u+(i/3u)*32u;
                if(small) hgr_putu8(x,y,values[i]); else hgr_putu(x,y,values[i]);
            }
            if(small) {
                hgr_putu8(264u+phase,184,65535u);
                hgr_putu8(65535u,0,12345u); hgr_putu8(0,185,12345u);
            } else {
                hgr_putu(258u+phase,176,65535u);
                hgr_putu(65535u,0,12345u); hgr_putu(0,177,12345u);
            }
            painted();
        }
    for(;;) {}
    return 0;
}
''')
    markers=work/'paint.s'
    markers.write_text('.export _painted, resume\n.code\n_painted: nop\nresume: rts\n')
    disk=build(work,source,extra_sources=(markers,))
    labels=a2test.labels(work/'test.lbl')
    steps=[]
    for _ in range(28):
        steps += [labels.until('_painted'), 'peek:2000:16384', labels.until('resume')]
    result=a2test.run(disk,steps,iie=iie)
    font=bytes(fonts.glyphs(0x20,0x7F))
    pages=[bytearray([42]*8192),bytearray([42]*8192)]
    for scene in range(28):
        page,within=divmod(scene,14);small,phase=divmod(within,7)
        image=pages[page]=bytearray([170]*8192)
        for i,value in enumerate(values):
            text(image,font,7+phase+(i%3)*84,8+(i//3)*32,str(value),1 if small else 2)
        text(image,font,(264 if small else 258)+phase,184 if small else 176,
             '65535',1 if small else 2)
        assert result.dumps[scene]==pages[0]+pages[1],('render',scene)
    print('HGR unsigned rendering: decimal boundaries, both fonts/pages, seven phases, '
          'right/bottom edges, invalid coordinates, palette and holes OK.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-unsigned-') as directory:
        work=Path(directory)
        strings(work,args.iie)
        rendering(work,args.iie)


if __name__=='__main__':
    main()
