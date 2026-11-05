#!/usr/bin/env python3
"""Exhaust all legal ellipse radius/coefficient pairs and stack placements."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, compile_source, run, a2test

ALIGN=((0,0),(32767,64),(32767,-64),(32767,63),(32767,-63),(511,-45),(512,45),(32766,1))


def value(radius,c):
    magnitude=radius*abs(c)//64
    return (-magnitude if c<0 else magnitude)&65535


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--reference',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-ellipse-offset-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text(r'''int __fastcall__ gfx_ellipse_offset(unsigned radius,signed char c);
int align_call(void);void ready(void);void page_done(void);void finished(void);
unsigned char records[2][256],first,last,index,align_kind;
int main(void) {
    unsigned v;int c,result;unsigned char high;volatile unsigned guard=0xa55a;
    ready();
    for(high=first;high<last;++high)for(c=-64;c<=64;++c) {
        v=(unsigned)high<<8;
        do {index=(unsigned char)v;result=gfx_ellipse_offset(v,(signed char)c);
            records[0][index]=(unsigned char)result;records[1][index]=(unsigned)result>>8;
            if(guard!=0xa55a)for(;;) {}++v;
        }while((unsigned char)v);page_done();
    }
    if(!first)for(align_kind=0;align_kind<8;++align_kind) {
        index=0;do {result=align_call();records[0][index]=(unsigned char)result;
            records[1][index]=(unsigned)result>>8;++index;}while(index);page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        helper=work/'helper.s';code='''.export _ready,_page_done,resume,_finished,_align_call
.import _gfx_ellipse_offset,_index,_align_kind,pushax
.importzp sp
.bss
saved_sp: .res 2
result: .res 2
.code
_ready: rts
_page_done: nop
resume: rts
_finished: rts
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
 ldy _align_kind
 lda radiuslo,y
 ldx radiushi,y
 jsr pushax
 ldy _align_kind
 lda coefficients,y
 jsr _gfx_ellipse_offset
 sta result
 stx result+1
 lda sp
 cmp _index
 bne fail
 lda sp+1
 cmp #$91
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
 lda result
 ldx result+1
 rts
fail: jmp fail
.rodata
'''
        for name,values in (('radiuslo',[r&255 for r,c in ALIGN]),('radiushi',[r>>8 for r,c in ALIGN]),
                            ('coefficients',[c&255 for r,c in ALIGN])):
            code+=name+': .byte '+','.join(map(str,values))+'\n'
        helper.write_text(code);build(work,source,extra_sources=(helper,))
        if args.reference:
            text=(DEV/'lib/gfx/gfx_ellipse.c').read_text();start=text.index('static int gfx_ellipse_offset(')
            opening=text.index('{',start);depth=1;end=opening+1
            while depth:
                if text[end]=='{':depth+=1
                elif text[end]=='}':depth-=1
                end+=1
            ref=work/'reference.c';ref.write_text(text[start:end].replace('static int','int',1)+'\n')
            compile_source(ref,work/'reference.o',['-t','none','-Oirs'])
            run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',work/'test.lbl','-o',work/'test.bin',
                 work/'crt0_apple2.o',work/'entry.o',work/'apple2io_asm.o',work/'helper.o',work/'reference.o',work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        assert labels['__BSS_RUN__']+labels['__BSS_SIZE__']<0x9000
        for first in range(0,128,8):
            steps=[labels.until('_ready'),labels.poke('_first',first),labels.poke('_last',first+8)]
            total=8*129+(8 if first==0 else 0)
            for _ in range(total):steps.extend((labels.until('_page_done'),labels.peek('_records',512),labels.until('resume')))
            steps.append(labels.until('_finished'));result=a2test.run(disk,steps,iie=args.iie,timeout=180)
            assert len(result.dumps)==total
            index=0
            for high in range(first,first+8):
                for c in range(-64,65):
                    values=[value(r,c) for r in range(high*256,(high+1)*256)]
                    wanted=bytes(v&255 for v in values)+bytes(v>>8 for v in values)
                    assert result.dumps[index]==wanted,(high,c);index+=1
            if first==0:
                for radius,c in ALIGN:
                    v=value(radius,c);wanted=bytes([v&255])*256+bytes([v>>8])*256
                    assert result.dumps[index]==wanted,('alignment',radius,c);index+=1
        print(f'Ellipse offset: all 4,227,072 radius/coefficient pairs, signed truncation, guards and '
              f'2,048 stack placements; IIe={args.iie}, reference={args.reference}.')


if __name__=='__main__':main()
