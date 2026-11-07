#!/usr/bin/env python3
"""Native ellipses: exact ordered chords, all byte y pairs and hostile calls."""
from pathlib import Path
import tempfile
import random
import argparse
from test_hgr import DEV,build,compile_source,run,a2test

quarter=(64,64,63,61,59,56,53,49,45,41,36,30,24,19,12,6)
cosine=quarter+(0,)+tuple(-v for v in reversed(quarter[1:]))
cosine+=tuple(-v for v in cosine)
sine=cosine[48:]+cosine[:48]


def expected(w,h,box):
    x0,y0,x1,y1=box
    if min(x0,x1)>=w or min(y0,y1)>=h:return b'\0'
    x0,x1=sorted((x0,x1));rx=(x1-x0)//2;xc=x0+rx;yc=(y0+y1)//2;ry=abs(y1-y0)//2
    clip=lambda x,y:(min(x,w-1),max(0,min(y,h-1)))
    if not rx and(x0==x1 or y0!=y1):segments=[clip(xc,y0)+clip(xc,y1)]
    elif not ry:segments=[clip(x0,yc)+clip(x1,yc)]
    else:
        scale=lambda r,c:(1 if c>=0 else -1)*(r*abs(c)//64)
        points=[clip(xc+scale(rx,cosine[i]),yc+scale(ry,sine[i])) for i in range(64)]
        segments=[points[i]+points[(i+1)%64] for i in range(64)]
    out=bytearray((len(segments),))
    for a,b,c,d in segments:out.extend((a&255,a>>8,b,c&255,c>>8,d))
    return bytes(out)


def cases():
    # Exhaust the carry in the byte-centre sum and both y corner orders.
    for y0 in range(256):
        for y1 in range(256):yield 280,192,(10,y0,200,y1),None
    # Full-width x coordinates, off-screen and small custom backends.
    rng=random.Random(6502)
    for w,h in ((0,0),(0,192),(1,1),(1,192),(140,192),(280,192),(560,192),(65535,255)):
        for _ in range(512):
            x0=rng.randrange(max(w,1));x1=rng.choice((rng.randrange(65536),rng.randrange(max(w+1,1))))
            y0,y1=rng.randrange(256),rng.randrange(256)
            yield w,h,(x0,y0,x1,y1),None
            if _<64:yield w,h,(x1,y1,x0,y0),None
    for w in (1,140,280,560,65535):
        for h in (0,1,192,255):
            for x in (0,1,w-1,w,65535):
                for y in (0,1,h-1 if h else 0,h,255):
                    for dx,dy in ((0,0),(0,1),(1,0),(1,1)):
                        yield w,h,(x,y,min(65535,x+dx),min(255,y+dy)),None
    # Every low C-stack byte on drawing, degenerate and rejection paths.
    for box in ((0,0,559,191),(559,191,0,0),(0,0,65535,255),(65535,255,0,0),(0,0,0,255),(10,10,11,10),(65535,0,560,191),(0,192,559,255)):
        for low in range(256):yield 560,192,box,low


def check(args):
    with tempfile.TemporaryDirectory(prefix='gfx-ellipse-entry-') as tmp:
        work=Path(tmp);source=work/'entry.c';source.write_text('''#include "gfx.h"
void ready(void);void ellipse_done(void);void align_call(void);void set_grid(void);
unsigned char inputs[1411],records[384],*cursor,count,y0,y1,gridh,stack_low;
unsigned x0,x1,gridw;
static void fail(void){for(;;){}}
int main(void) {
    unsigned n,i,k;volatile unsigned guard=0xa55a;
    for (;;) {
        ready();n=inputs[0]+((unsigned)inputs[1]<<8);
        for (i=0,k=3;i<n;++i,k+=11) {
            gridw=inputs[k]+((unsigned)inputs[k+1]<<8);gridh=inputs[k+2];set_grid();
            x0=inputs[k+3]+((unsigned)inputs[k+4]<<8);y0=inputs[k+5];
            x1=inputs[k+6]+((unsigned)inputs[k+7]<<8);y1=inputs[k+8];stack_low=inputs[k+9];
            count=0;cursor=records;
            if (inputs[k+10]) align_call();else gfx_ellipse(x0,y0,x1,y1);
            if (guard!=0xa55a||count>64) fail();
            ellipse_done();
        }
    }
    return 0;
}
''')
        helpers=work/'helpers.s';helpers.write_text('''.export _ready,_ellipse_done,resume,_align_call,_set_grid
.import _gfx_ellipse,_gfx_width,_gfx_height,_x0,_x1,_y0,_y1,_stack_low,_gridw,_gridh,pushax,pusha
.importzp sp
.bss
saved_sp: .res 2
.code
_ready: rts
_ellipse_done: nop
resume: rts
_set_grid:
 lda _gridw
 sta _gfx_width
 lda _gridw+1
 sta _gfx_width+1
 lda _gridh
 sta _gfx_height
 rts
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
 lda _x0
 ldx _x0+1
 jsr pushax
 lda _y0
 jsr pusha
 lda _x1
 ldx _x1+1
 jsr pushax
 lda _y1
 jsr _gfx_ellipse
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
        # Relink the writable grid and hostile sink ahead of the archive.
        build(work,source,extra_sources=(helpers,))
        sink=work/'sink.s';s='''.export _gfx_line,_gfx_width,_gfx_height
.import _count,_cursor,incsp5
.importzp sp,ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4
.data
_gfx_width: .word 280
_gfx_height: .byte 192
.code
_gfx_line:
 sta tmp4
 lda _count
 cmp #64
 bcs fail
 lda _cursor
 sta ptr1
 lda _cursor+1
 sta ptr1+1
'''
        for i,slot in enumerate((3,4,2,0,1,'tmp4')):
            s+=(f' ldy #{slot}\n lda (sp),y\n' if isinstance(slot,int) else ' lda tmp4\n')+f' ldy #{i}\n sta (ptr1),y\n'
        s+=' clc\n lda _cursor\n adc #6\n sta _cursor\n bcc :+\n inc _cursor+1\n: inc _count\n lda #$5a\n'
        s+=''.join(f' sta {name}\n' for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'))
        s+=' tax\n tay\n jmp incsp5\nfail: jmp fail\n';sink.write_text(s);run(['ca65','-o',work/'sink.o',sink])
        reference=[]
        if args.reference:
            obj=work/'reference.o'
            compile_source(DEV/'lib/gfx/gfx_ellipse_ref.c',obj,['-t','none','-Oirs','-I',DEV/'lib/gfx'])
            reference.append(obj)
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',work/'entry.o',work/'apple2io_asm.o',work/'helpers.o',work/'sink.o',*reference,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin');assert labels['__BSS_RUN__']+labels['__BSS_SIZE__']<0xa000
        data=list(cases());total=0
        for chunk in range(0,len(data),1024):
            steps=[];wanted=bytearray()
            for batch in range(chunk,min(chunk+1024,len(data)),128):
                rows=data[batch:min(batch+128,chunk+1024,len(data))];packed=bytearray((len(rows)&255,len(rows)>>8,0))
                for w,h,(x0,y0,x1,y1),low in rows:packed.extend((w&255,w>>8,h,x0&255,x0>>8,y0,x1&255,x1>>8,y1,low or 0,int(low is not None)))
                f=work/f'input{batch}.bin';f.write_bytes(packed);steps.extend((labels.until('_ready'),f'load:{f}@{labels["_inputs"]:04X}'))
                for w,h,box,low in rows:
                    wanted_bytes=expected(w,h,box);n=wanted_bytes[0];total+=n
                    steps.extend((labels.until('_ellipse_done',limit=30000),labels.peek('_count')))
                    if n:steps.append(labels.peek('_records',n*6))
                    steps.append(labels.until('resume'));wanted.extend(wanted_bytes)
            result=a2test.run(disk,steps,iie=args.iie,timeout=180)
            assert result.data==wanted,('ordered chords',chunk,len(result.data),len(wanted))
        print(f'GFX ellipse: {len(data):,} exact traces / {total:,} ordered chords, all y pairs, '
                                f'wide/reversed/degenerate boxes, hostile scratch and 2,048 stack placements; '
                                f'IIe={args.iie}, reference={args.reference}.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--reference',action='store_true')
    check(parser.parse_args())


if __name__=='__main__':main()
