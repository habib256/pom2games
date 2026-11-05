#!/usr/bin/env python3
"""DHGR axes: full endpoint domains, ordering, clipped extents and stack pages."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test

ALIGN_H=((0,559,191,0),(65535,513,191,255),(65535,65535,255,128),(559,0,255,1))
ALIGN_V=((559,0,191,0),(513,255,191,255),(65535,255,255,128),(0,191,0,1))


def batches():
    for position in range(2):
        for anchor in (0,559,65535):
            for high in range(256):
                yield [(0,v,anchor,191,v&255) if position==0 else (0,anchor,v,191,v&255)
                       for v in range(high*256,(high+1)*256)]
    yield [(0,65535,0,y,y) for y in range(256)]
    yield [(0,513,559,191,s) for s in range(256)]
    for high in range(256):
        yield [(1,x,255,0,42) for x in range(high*256,(high+1)*256)]
    for high in range(256):yield [(1,559,high,y,y) for y in range(256)]
    yield [(1,65535,255,192,s) for s in range(256)]
    for case in ALIGN_H:yield [(0,*case)]*256
    for case in ALIGN_V:yield [(1,*case)]*256


def expected(cases):
    output=bytearray(8*256)
    for index,(vertical,a,b,c,set_bit) in enumerate(cases):
        if vertical:
            x=a;y,end=sorted((b,c));width=1;height=(min(end,191)-y+1)&255
        else:
            x,end=sorted((a,b));y=c;width=(min(end,559)-x+1)&65535;height=1
        values=(1,x&255,x>>8,y,width&255,width>>8,height,set_bit)
        for plane,value in enumerate(values):output[plane*256+index]=value
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-axes-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "dhgr.h"
void page_done(void);void finished(void);void align_call(void);
unsigned char records[8][256],index,align_mode;
static const unsigned anchors[3]={0,559,65535u};
static void prepare(void) {
    unsigned char j;records[0][index]=0;
    for(j=1;j<8;++j)records[j][index]=0xA5u;
}
int main(void) {
    unsigned value,anchor;
    unsigned char mode;
    volatile unsigned guard=0xA55Au;
    for(mode=0;mode<6;++mode) {
        value=0;anchor=anchors[mode%3];
        do {
            index=(unsigned char)value;prepare();
            if(mode<3)dhgr_hline(value,anchor,191,index);
            else dhgr_hline(anchor,value,191,index);
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    for(value=0;value<256;++value) {
        index=(unsigned char)value;prepare();dhgr_hline(65535u,0,index,index);
    }
    page_done();
    for(value=0;value<256;++value) {
        index=(unsigned char)value;prepare();dhgr_hline(513,559,191,index);
    }
    page_done();value=0;
    do {
        index=(unsigned char)value;prepare();dhgr_vline(value,255,0,42);
        ++value;if((unsigned char)value==0)page_done();
    } while(value);
    value=0;
    do {
        index=(unsigned char)value;prepare();dhgr_vline(559,(unsigned char)(value>>8),index,index);
        ++value;if((unsigned char)value==0)page_done();
    } while(value);
    for(value=0;value<256;++value) {
        index=(unsigned char)value;prepare();dhgr_vline(65535u,255,192,index);
    }
    page_done();
    for(align_mode=0;align_mode<8;++align_mode) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;prepare();align_call();
            if(guard!=0xA55Au)for(;;) {}
        }
        page_done();
    }
    if(guard!=0xA55Au)for(;;) {}
    finished();for(;;) {} return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        frames=[(y,x1&255,x1>>8,x0&255,x0>>8) for x0,x1,y,s in ALIGN_H]
        frames += [(y1,y0,x&255,x>>8,0) for x,y0,y1,s in ALIGN_V]
        tables=''.join(f'arg{slot}: .byte '+','.join(str(frame[slot]) for frame in frames)+'\n' for slot in range(5))
        tables+='sets: .byte '+','.join(str(c[-1]) for c in (*ALIGN_H,*ALIGN_V))+'\ncounts: .byte 5,5,5,5,4,4,4,4\n'
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _align_mode, _dhgr_hline, _dhgr_vline
.importzp sp
.rodata
'''+tables+'''.bss
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
 lda arg0,x
 sta (sp),y
 iny
 lda arg1,x
 sta (sp),y
 iny
 lda arg2,x
 sta (sp),y
 iny
 lda arg3,x
 sta (sp),y
 iny
 cpx #4
 bcs guards
 lda arg4,x
 sta (sp),y
 iny
guards:
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda sets,x
 cpx #4
 bcs vertical
 jsr _dhgr_hline
 jmp verify
vertical:
 jsr _dhgr_vline
verify:
 ldx _align_mode
 clc
 lda _index
 adc counts,x
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
        stub='''.export _dhgr_fill_bits
.import _records, _index, addysp
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.bss
saved_set: .res 1
.code
_dhgr_fill_bits:
 sta saved_set
 ldx _index
 lda _records,x
 bne fail
 lda #1
 sta _records,x
 lda saved_set
 sta _records+1792,x
'''
        for slot,plane in enumerate((6,4,5,3,1,2)):
            stub+=f' ldy #{slot}\n lda (sp),y\n sta _records+{plane*256},x\n'
        stub+=' lda #$a5\n'
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n ldy #6\n jmp addysp\nfail: jmp fail\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',work/'entry.o',
             work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        cases=list(batches());steps=[]
        for _ in cases:
            steps += [labels.until('_page_done'),labels.peek('_records',2048),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==len(cases)
        for index,batch in enumerate(cases):
            assert result.dumps[index]==expected(batch),('DHGR axes batch',index,batch[0])
        print(f'DHGR axes entry: {len(cases)*256:,} calls, full endpoint domains, byte pairs/selectors, '
              f'ordering and clipped/wrapped extents, scratch/caller guards '
              f'and 2,048 stack placements; IIe={args.iie}.')


if __name__=='__main__':
    main()
