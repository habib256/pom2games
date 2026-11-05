#!/usr/bin/env python3
"""X2 native entry: all extents/pointers, exact maximum, scratch and stack ABI."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test

ALIGN_CASES=((1,1,0),(255,64,4),(127,129,5),(128,128,1),(0,255,2),(255,0,3))


def expected(kind,high):
    result=bytearray([0]*256+[0xA5]*2304)
    for low in range(256):
        value=high*256+low
        if kind==0:src,out,w,h,color=0x1234,0x5678,low,high,167
        elif kind==1:src,out,w,h,color=value,0x5678,127,129,high
        elif kind==2:src,out,w,h,color=0x1234,value,255,64,high
        else:
            w,h,color=ALIGN_CASES[high];src,out=0x1234,0x5678
        if not w or not h or w*h>16383:continue
        for plane,byte in enumerate((1,src&255,src>>8,out&255,out>>8,w,h,color,(w*2)&255,w>>7)):
            result[plane*256+low]=byte
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-x2-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "hgr_x2.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[10][256],index,align_kind;
static void clear_slot(void) {unsigned char i;records[0][index]=0;for(i=1;i<10;++i)records[i][index]=0xA5u;}
int main(void) {
    unsigned value;
    unsigned char kind;
    volatile unsigned guard=0xA55Au;
    for(kind=0;kind<3;++kind) {
        value=0;
        do {
            index=(unsigned char)value;clear_slot();
            if(kind==0)hgr_inflate_x2((void*)0x1234,index,(unsigned char)(value>>8),167,(void*)0x5678);
            else if(kind==1)hgr_inflate_x2((void*)value,127,129,(unsigned char)(value>>8),(void*)0x5678);
            else hgr_inflate_x2((void*)0x1234,255,64,(unsigned char)(value>>8),(void*)value);
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    for(align_kind=0;align_kind<6;++align_kind) {
        for(value=0;value<256;++value) {index=(unsigned char)value;clear_slot();align_call();}
        page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done,resume,_finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s'
        code='''.export _align_call
.import _hgr_inflate_x2, _index, _align_kind, pushax, pusha
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
 lda #$34
 ldx #$12
 jsr pushax
 ldy _align_kind
 lda widths,y
 jsr pusha
 ldy _align_kind
 lda heights,y
 jsr pusha
 ldy _align_kind
 lda colors,y
 jsr pusha
 lda #$78
 ldx #$56
 jsr _hgr_inflate_x2
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
 rts
fail: jmp fail
.rodata
'''
        for i,name in enumerate(('widths','heights','colors')):
            code+=name+': .byte '+','.join(str(v[i]) for v in ALIGN_CASES)+'\n'
        align.write_text(code)
        build(work,source,extra_sources=(marker,align))
        stub='''.export _hgr_inflate_x2_asm
.import _records, _index
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.code
_hgr_inflate_x2_asm:
 ldx _index
 lda #1
 sta _records,x
'''
        for plane,name in enumerate(('ptr1','ptr1+1','ptr2','ptr2+1','tmp1','tmp2','tmp3'),1):
            stub+=f' lda {name}\n sta _records+{256*plane},x\n'
        stub+=' ldy #3\n lda (sp),y\n sta _records+2048,x\n iny\n lda (sp),y\n sta _records+2304,x\n lda #$5a\n'
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n rts\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'entry.o',work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(774):
            steps += [labels.until('_page_done'),labels.peek('_records',2560),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==774
        pos=0
        for kind in range(3):
            for high in range(256):
                assert result.dumps[pos]==expected(kind,high),(kind,high)
                pos+=1
        for high in range(6):
            assert result.dumps[pos]==expected(3,high),('stack',high)
            pos+=1
        print(f'HGR x2 entry: 198,144 calls, all width/height and pointer words, '
              f'16383/16384 limit, exact kernel arguments, hostile scratch, guards and 1,536 stack placements; IIe={args.iie}.')


if __name__=='__main__':main()
