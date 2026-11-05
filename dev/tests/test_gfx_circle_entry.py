#!/usr/bin/env python3
"""Native circles: every byte radius/height, exact ordered points and hostile calls."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, compile_source, run, a2test


def cases():
    for r in range(256):
        for y in range(256):yield 280,192,(140,y,r),None
    for width in (140,280,560):
        for r in range(256):
            for x,y in ((0,0),(0,96),(width-1,191),(width,96),(width+r,96),(65535,255)):
                yield width,192,(x,y,r),None
    for width in (0,1,140,280,560):
        for height in (0,1,255):
            for r in (0,1,2,16,255):
                for x,y in ((0,0),(width//2,height//2),(width,height),(65535,255)):
                    yield width,height,(x,y,r),None
    for x in range(815):yield 560,192,(x,96,255),None
    for case in ((140,96,0),(140,96,1),(140,96,16),(140,96,90),
                 (0,0,31),(280,96,31),(140,96,255),(65535,255,255)):
        for low in range(256):yield 280,192,case,low


def expected(width,height,case):
    cx,cy,r=case
    if (cx>=width and cx-width>=r) or (cy>=height and cy-height>=r):return b'\0\0'
    if not r:return bytes((1,0,cx&255,cx>>8,cy))
    result=bytearray();x,y,d=0,r,1-r
    while x<=y:
        points=[]
        if x:points.extend(((cx+x,cy+y),(cx-x,cy-y)))
        points.extend(((cx-x,cy+y),(cx+x,cy-y)))
        if x!=y:
            points.extend(((cx+y,cy+x),(cx-y,cy+x)))
            if x:points.extend(((cx+y,cy-x),(cx-y,cy-x)))
        for px,py in points:
            if 0<=px<width and 0<=py<height:result.extend((px&255,px>>8,py))
        if d<0:d+=2*x+3
        else:d+=2*(x-y)+5;y-=1
        x+=1
    count=len(result)//3
    return bytes((count&255,count>>8))+result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--reference',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-circle-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text(r'''#include "gfx.h"
void ready(void);void circle_done(void);void align_call(void);void set_grid(void);
unsigned char inputs[1155],records[6144],*cursor;
unsigned count,xc,gridw;unsigned char yc,radius,gridh,stack_low;
static void fail(void) {for(;;) {}}
static void audit(void) {
    unsigned v=815;gridw=560;gridh=192;set_grid();
    do {count=0;cursor=records;gfx_circle(v,96,255);if(count)fail();
        gfx_circle(v,96,0);if(count)fail();++v;}while(v);
}
int main(void) {
    unsigned n,i,k;volatile unsigned guard=0xa55a;
    for(;;) {
        ready();if(inputs[2])audit();n=inputs[0]+((unsigned)inputs[1]<<8);
        for(i=0,k=3;i<n;++i,k+=9) {
            gridw=inputs[k]+((unsigned)inputs[k+1]<<8);gridh=inputs[k+2];set_grid();
            xc=inputs[k+3]+((unsigned)inputs[k+4]<<8);yc=inputs[k+5];radius=inputs[k+6];stack_low=inputs[k+7];
            count=0;cursor=records;if(inputs[k+8])align_call();else gfx_circle(xc,yc,radius);
            if(guard!=0xa55a||count>2048)fail();circle_done();
        }
    }
    return 0;
}
''')
        helpers=work/'helpers.s';helpers.write_text('''.export _ready,_circle_done,resume,_align_call,_set_grid
.import _gfx_circle,_xc,_yc,_radius,_stack_low,_gridw,_gridh,pushax,pusha
.importzp sp
.bss
saved_sp: .res 2
.code
_ready: rts
_circle_done: nop
resume: rts
_set_grid: rts
_align_call:
 lda sp
 sta saved_sp
 lda sp+1
 sta saved_sp+1
 lda _stack_low
 sta sp
 lda #$a1
 sta sp+1
 ldy #0
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda _xc
 ldx _xc+1
 jsr pushax
 lda _yc
 jsr pusha
 lda _radius
 jsr _gfx_circle
 lda sp
 cmp _stack_low
 bne fail
 lda sp+1
 cmp #$a1
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
        build(work,source,extra_sources=(helpers,))
        text=helpers.read_text().replace('_set_grid: rts','''_set_grid:
 lda _gridw
 sta _gfx_width
 lda _gridw+1
 sta _gfx_width+1
 lda _gridh
 sta _gfx_height
 rts''').replace('.importzp sp','.import _gfx_width,_gfx_height\n.importzp sp')
        helpers.write_text(text);run(['ca65','-o',work/'helpers.o',helpers])
        sink=work/'sink.s';stub='''.export _gfx_plot,_gfx_width,_gfx_height
.import _count,_cursor,incsp2
.importzp sp,ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4
.data
_gfx_width: .word 280
_gfx_height: .byte 192
.code
_gfx_plot:
 sta tmp4
 lda _count+1
 cmp #8
 bcs fail
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
: lda #$5a
'''
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n jmp incsp2\nfail: jmp fail\n';sink.write_text(stub);run(['ca65','-o',work/'sink.o',sink])
        reference=[]
        if args.reference:
            obj=work/'reference.o';compile_source(DEV/'lib/gfx/gfx_circle.c',obj,['-t','none','-Oirs','-I',DEV/'lib/gfx'])
            reference.append(obj)
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',work/'test.lbl','-o',work/'test.bin',
             work/'crt0_apple2.o',work/'entry.o',work/'apple2io_asm.o',work/'helpers.o',work/'sink.o',
             *reference,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        assert labels['__BSS_RUN__']+labels['__BSS_SIZE__']<0xa000,'fixture overlaps alignment stack'
        data=list(cases());pixels=0
        for chunk in range(0,len(data),1024):
            steps=[];wanted=bytearray()
            for batch in range(chunk,min(chunk+1024,len(data)),128):
                rows=data[batch:min(batch+128,chunk+1024,len(data))]
                packed=bytearray((len(rows)&255,len(rows)>>8,int(batch==0)))
                for width,height,(x,y,r),low in rows:
                    packed.extend((width&255,width>>8,height,x&255,x>>8,y,r,low or 0,int(low is not None)))
                path=work/f'input{batch}.bin';path.write_bytes(packed)
                steps.extend((labels.until('_ready'),f'load:{path}@{labels["_inputs"]:04X}'))
                for width,height,case,low in rows:
                    expected_bytes=expected(width,height,case);count=(len(expected_bytes)-2)//3;pixels+=count
                    steps.extend((labels.until('_circle_done',limit=30000),labels.peek('_count',2)))
                    if count:steps.append(labels.peek('_records',count*3))
                    steps.append(labels.until('resume'));wanted.extend(expected_bytes)
            result=a2test.run(disk,steps,iie=args.iie,timeout=180)
            assert result.data==wanted,('ordered circles',chunk,len(result.data),len(wanted))
        print(f'GFX circle: {len(data):,} exact traces / {pixels:,} pixels, all radius/y pairs, full x rejection, '
              f'empty/narrow grids, hostile scratch and 2,048 stack placements; IIe={args.iie}, reference={args.reference}.')


if __name__=='__main__':main()
