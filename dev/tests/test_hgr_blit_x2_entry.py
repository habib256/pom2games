#!/usr/bin/env python3
"""Inflate-and-blit control: bounded dimensions, forwarding, scratch and stack."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


ALIGN_CASES=((14,180,0x1234,3,16,4,2),(0,0,0x5678,64,1,5,255),
             (279,191,0xabcd,1,64,1,1),(0,0,0x1234,65,1,1,0),
             (280,0,0x1234,1,1,1,0),(0,192,0x1234,1,1,1,0),
             (0,0,0x1234,0,255,1,0),(0,0,0x1234,255,0,1,0))


def expected(kind,high):
    result=bytearray([0]*256+[0xA5]*3072)
    for low in range(256):
        value=high*256+low
        if kind==0:x,y,src,w,h,color,mode=14,180,0x1234,low,high,4,2
        elif kind==1:x,y,src,w,h,color,mode=value,191,0xabcd,3,16,5,1
        elif kind==2:x,y,src,w,h,color,mode=279,191,value,1,1,high,low
        elif kind==3:x,y,src,w,h,color,mode=14,low,0x1234,3,16,high,255
        else:x,y,src,w,h,color,mode=ALIGN_CASES[high]
        if not w or not h or w*h>64 or x>279 or y>191:continue
        values=(2,src&255,src>>8,w,h,color,x&255,x>>8,y,w*2,h*2,mode,1)
        for plane,byte in enumerate(values):result[plane*256+low]=byte
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-blit-x2-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "hgr_x2.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[13][256],index,align_kind;
static void clear_slot(void) {unsigned char i;records[0][index]=0;for(i=1;i<13;++i)records[i][index]=0xA5u;}
int main(void) {
    unsigned value;
    unsigned char kind;
    volatile unsigned guard=0xA55Au;
    for(kind=0;kind<4;++kind) {
        value=0;
        do {
            index=(unsigned char)value;clear_slot();
            if(kind==0)hgr_blit_x2(14,180,(void*)0x1234,index,(unsigned char)(value>>8),4,2);
            else if(kind==1)hgr_blit_x2(value,191,(void*)0xabcd,3,16,5,1);
            else if(kind==2)hgr_blit_x2(279,191,(void*)value,1,1,(unsigned char)(value>>8),index);
            else hgr_blit_x2(14,index,(void*)0x1234,3,16,(unsigned char)(value>>8),255);
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    for(align_kind=0;align_kind<8;++align_kind) {
        for(value=0;value<256;++value) {index=(unsigned char)value;clear_slot();align_call();}
        page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done,resume,_finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s'
        code='''.export _align_call
.import _hgr_blit_x2, _index, _align_kind, pushax, pusha
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
 ldy _align_kind
 ldx xhi,y
 lda xlo,y
 jsr pushax
 ldy _align_kind
 lda ys,y
 jsr pusha
 ldy _align_kind
 ldx srchi,y
 lda srclo,y
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
 ldy _align_kind
 lda modes,y
 jsr _hgr_blit_x2
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
        planes=[(x&255,x>>8,y,src&255,src>>8,w,h,color,mode) for x,y,src,w,h,color,mode in ALIGN_CASES]
        for i,name in enumerate(('xlo','xhi','ys','srclo','srchi','widths','heights','colors','modes')):
            code+=name+': .byte '+','.join(str(v[i]) for v in planes)+'\n'
        align.write_text(code)
        build(work,source,extra_sources=(marker,align))
        stub='''.export _hgr_inflate_x2, _hgr_blit7
.import _records, _index, incsp5, incsp7
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.bss
buffer: .res 2
.code
_hgr_inflate_x2:
 sta buffer
 stx buffer+1
 ldx _index
 inc _records,x
'''
        for offset,plane in enumerate((5,4,3,1,2)):
            stub+=f' ldy #{offset}\n lda (sp),y\n sta _records+{plane*256},x\n'
        stub+=' jsr scratch\n jmp incsp5\n_hgr_blit7:\n ldx _index\n sta _records+2816,x\n inc _records,x\n'
        for offset,plane in ((2,10),(3,9),(4,8),(5,6),(6,7)):
            stub+=f' ldy #{offset}\n lda (sp),y\n sta _records+{plane*256},x\n'
        stub+=''' lda #0
 sta _records+3072,x
 ldy #0
 lda (sp),y
 cmp buffer
 bne done
 iny
 lda (sp),y
 cmp buffer+1
 bne done
 inc _records+3072,x
done:
 jsr scratch
 jmp incsp7
scratch:
 lda #$5a
'''
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n rts\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'entry.o',work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(1032):
            steps += [labels.until('_page_done'),labels.peek('_records',3328),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==1032
        pos=0
        for kind in range(4):
            for high in range(256):
                assert result.dumps[pos]==expected(kind,high),(kind,high)
                pos+=1
        for high in range(8):
            assert result.dumps[pos]==expected(4,high),('stack',high)
            pos+=1
        print(f'HGR blit x2 entry: 264,192 calls, all dimensions, x/source words, y/color/mode bytes, '
              f'exact inflate/blit arguments and buffer identity, hostile scratch, guards and 2,048 stack placements; IIe={args.iie}.')


if __name__=='__main__':main()
