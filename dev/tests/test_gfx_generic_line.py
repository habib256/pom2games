#!/usr/bin/env python3
"""Generic lines: exact ordered pixels, axes/rejections, hostile scratch and stack."""
import argparse
import random
import tempfile
from pathlib import Path
from test_hgr import DEV, build, compile_source, run, a2test


def cases():
    for dx in range(1,33):
        for dy in range(1,33):
            for sx,sy in ((1,1),(1,-1),(-1,1),(-1,-1)):
                yield 560,192,(280,96,280+sx*dx,96+sy*dy),None
    for dx in range(1,560):
        for dy in (1,2,95,191):
            for reverse,up in ((False,False),(False,True),(True,False),(True,True)):
                x0,x1=(559,559-dx) if reverse else (0,dx)
                y0,y1=(191,191-dy) if up else (0,dy)
                yield 560,192,(x0,y0,x1,y1),None
    for dy in range(1,192):
        for dx in (1,2,70,139,279,559):
            yield 560,192,(0,0,dx,dy),None
            yield 560,192,(dx,dy,0,0),None
    rng=random.Random(6502)
    for width in (0,1,140,280,560):
        for height in (0,1,192,255):
            for _ in range(32):
                yield width,height,(rng.randrange(max(1,width)),rng.randrange(max(1,height)),
                                    rng.randrange(max(1,width)),rng.randrange(max(1,height))),None
    align=((0,0,559,191),(559,191,0,0),(5,191,15,0),(15,0,5,191),
           (65535,95,0,95),(559,255,559,0),(65535,0,0,191),(0,255,559,0))
    for case in align:
        for low in range(256):yield 560,192,case,low


def expected(width,height,case):
    x0,y0,x1,y1=case
    if y0==y1:kind=1
    elif x0==x1:kind=2
    else:kind=0
    if kind:return bytes((0,0,kind,x0&255,x0>>8,y0,x1&255,x1>>8,y1))
    if x0>=width or x1>=width or y0>=height or y1>=height:return bytes((0,0))+b'\xa5'*7
    result=bytearray();dx,dy=abs(x1-x0),abs(y1-y0)
    sx,sy=(1 if x1>x0 else -1),(1 if y1>y0 else -1);err=dx-dy
    while True:
        result.extend((x0&255,x0>>8,y0))
        if (x0,y0)==(x1,y1):break
        e2=2*err
        if e2>-dy:err-=dy;x0+=sx
        if e2<dx:err+=dx;y0+=sy
    count=len(result)//3
    return bytes((count&255,count>>8))+b'\xa5'*7+result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--reference',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-generic-line-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text(r'''#include "gfx.h"
void ready(void);void line_done(void);void align_call(void);void set_grid(void);
unsigned char inputs[1411],records[1680],span[7],*cursor;
unsigned count,x0,x1,gridw;
unsigned char y0,y1,gridh,stack_low;
static void reset(void) {unsigned char j;count=0;cursor=records;for(j=0;j<7;++j)span[j]=0xa5;}
static void fail(void) {for(;;) {}}
static void audit(void) {
    unsigned v=560;unsigned char a,b;
    gridw=560;gridh=192;set_grid();
    do {
        reset();gfx_line(v,0,1,1);if(count||span[0]!=0xa5)fail();
        gfx_line(1,1,v,0);if(count||span[0]!=0xa5)fail();
        ++v;
    }while(v);
    do {
        reset();gfx_line(v,255,65535u-v,255);
        if(count||span[0]!=1||span[1]!=(unsigned char)v||span[2]!=(v>>8)||span[3]!=255||
           span[4]!=(unsigned char)(65535u-v)||span[5]!=((65535u-v)>>8)||span[6]!=255)fail();
        reset();gfx_line(v,255,v,0);
        if(count||span[0]!=2||span[1]!=(unsigned char)v||span[2]!=(v>>8)||span[3]!=255||
           span[4]!=(unsigned char)v||span[5]!=(v>>8)||span[6]!=0)fail();
        ++v;
    }while(v);
    a=0;do {b=0;do {
        if(a!=b&&(a>=192||b>=192)) {
            reset();gfx_line(0,a,559,b);if(count||span[0]!=0xa5)fail();
        }
        ++b;
    }while(b);++a;}while(a);
}
int main(void) {
    unsigned n,i,k;volatile unsigned guard=0xa55a;
    for(;;) {
        ready();if(inputs[2])audit();n=inputs[0]+((unsigned)inputs[1]<<8);
        for(i=0,k=3;i<n;++i,k+=11) {
            gridw=inputs[k]+((unsigned)inputs[k+1]<<8);gridh=inputs[k+2];set_grid();
            x0=inputs[k+3]+((unsigned)inputs[k+4]<<8);y0=inputs[k+5];
            x1=inputs[k+6]+((unsigned)inputs[k+7]<<8);y1=inputs[k+8];stack_low=inputs[k+9];
            reset();if(inputs[k+10])align_call();else gfx_line(x0,y0,x1,y1);
            if(guard!=0xa55a||count>560)fail();line_done();
        }
    }
    return 0;
}
''')
        helpers=work/'helpers.s';helpers.write_text('''.export _ready,_line_done,resume,_align_call,_set_grid
.import _gfx_line,_x0,_x1,_y0,_y1,_stack_low,_gridw,_gridh,pushax,pusha
.importzp sp
.bss
saved_sp: .res 2
.code
_ready: rts
_line_done: nop
resume: rts
_set_grid: rts
_align_call:
 lda sp
 sta saved_sp
 lda sp+1
 sta saved_sp+1
 lda _stack_low
 sta sp
 lda #$91
 sta sp+1
 ldy #0
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda _x0
 ldx _x0+1
 jsr pushax
 lda _y0
 jsr pusha
 lda _x1
 ldx _x1+1
 jsr pushax
 lda _y1
 jsr _gfx_line
 lda sp
 cmp _stack_low
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
''')
        build(work,source,extra_sources=(helpers,),gfx_backend='gfx_backend_dhgr_mono.c')
        # Replace the dummy grid setter for the final link, alongside the sinks.
        text=helpers.read_text().replace('_set_grid: rts','''_set_grid:
 lda _gridw
 sta _gfx_width
 lda _gridw+1
 sta _gfx_width+1
 lda _gridh
 sta _gfx_height
 rts''').replace('.importzp sp','.import _gfx_width,_gfx_height\n.importzp sp')
        helpers.write_text(text);run(['ca65','-o',work/'helpers.o',helpers])
        sink=work/'sink.s';stub='''.export _gfx_plot,_gfx_hline,_gfx_vline,_gfx_width,_gfx_height
.import _count,_cursor,_span,incsp2,incsp3,incsp4
.importzp sp,ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4
.data
_gfx_width: .word 560
_gfx_height: .byte 192
.code
_gfx_plot:
 sta tmp4
 lda _count+1
 cmp #>560
 bcc store
 bne fail
 lda _count
 cmp #<560
 bcs fail
store:
 lda _cursor
 sta ptr1
 lda _cursor+1
 sta ptr1+1
 ldy #0
 lda (sp),y
 sta (ptr1),y
 iny
 lda (sp),y
 sta (ptr1),y
 iny
 lda tmp4
 sta (ptr1),y
 clc
 lda _cursor
 adc #3
 sta _cursor
 bcc :+
 inc _cursor+1
: inc _count
 bne :+
 inc _count+1
: jsr scratch
 jmp incsp2
fail: jmp fail
'''
        for name,kind,fields,cleanup in (('_gfx_hline',1,(2,3,'tmp4',0,1,'tmp4'),4),
                                         ('_gfx_vline',2,(1,2,0,1,2,'tmp4'),3)):
            stub+=f'{name}:\n sta tmp4\n lda #{kind}\n sta _span\n'
            for i,field in enumerate(fields,1):
                stub+=(f' ldy #{field}\n lda (sp),y\n' if isinstance(field,int) else f' lda {field}\n')
                stub+=f' sta _span+{i}\n'
            stub+=f' jsr scratch\n jmp incsp{cleanup}\n'
        stub+='scratch: lda #$5a\n'
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n rts\n';sink.write_text(stub);run(['ca65','-o',work/'sink.o',sink])
        reference=[]
        if args.reference:
            obj=work/'reference.o';compile_source(DEV/'lib/gfx/gfx_line.c',obj,['-t','none','-Oirs','-I',DEV/'lib/gfx'])
            reference.append(obj)
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',work/'test.lbl','-o',work/'test.bin',
             work/'crt0_apple2.o',work/'entry.o',work/'apple2io_asm.o',work/'helpers.o',work/'sink.o',
             *reference,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        assert labels['__BSS_RUN__']+labels['__BSS_SIZE__']<0x9000,'fixture overlaps alignment stack'
        data=list(cases());pixels=0
        for chunk in range(0,len(data),1024):
            steps=[];wanted=bytearray()
            for batch in range(chunk,min(chunk+1024,len(data)),128):
                rows=data[batch:min(batch+128,chunk+1024,len(data))]
                packed=bytearray((len(rows)&255,len(rows)>>8,int(batch==0)))
                for width,height,(x0,y0,x1,y1),low in rows:
                    packed.extend((width&255,width>>8,height,x0&255,x0>>8,y0,x1&255,x1>>8,y1,low or 0,int(low is not None)))
                path=work/f'input{batch}.bin';path.write_bytes(packed)
                steps.extend((labels.until('_ready'),f'load:{path}@{labels["_inputs"]:04X}'))
                for width,height,case,low in rows:
                    expected_bytes=expected(width,height,case);count=(len(expected_bytes)-9)//3;pixels+=count
                    steps.extend((labels.until('_line_done',limit=30000),labels.peek('_count',2),labels.peek('_span',7)))
                    if count:steps.append(labels.peek('_records',count*3))
                    steps.append(labels.until('resume'));wanted.extend(expected_bytes)
            result=a2test.run(disk,steps,iie=args.iie,timeout=180)
            assert result.data==wanted,('ordered generic lines',chunk,len(result.data),len(wanted))
        print(f'GFX generic line: {len(data):,} exact traces / {pixels:,} pixels, all x words for axes/rejection, '
              f'all invalid y pairs, hostile scratch and 2,048 stack placements; IIe={args.iie}, reference={args.reference}.')


if __name__=='__main__':main()
