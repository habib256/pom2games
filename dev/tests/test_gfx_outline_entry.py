#!/usr/bin/env python3
"""Generic outlines: exact span sequences, full coordinates, grids and stack."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, compile_source, run, a2test

GRIDS=((280,192),(0,0),(1,1),(140,192),(560,192),(65535,255),(280,0),(0,192),(65535,1))
ALIGN_CASES=((65535,255,0,0),(0,0,279,191),(1,1,5,5),(279,191,279,191),
             (1,0,5,0),(280,0,65535,255),(0,192,279,255),(5,6,4,3))


def grid_cases(width,height):
    xs=(0,1,max(0,width-1),width,min(width+1,65535),32767,32768,65535)
    ys=(0,1,max(0,height-1),height,min(height+1,255),191,192,255)
    return [(xs[v>>5],ys[(v>>4)&7],xs[(v>>2)&7],ys[v&7]) for v in range(256)]


def batches():
    for anchor in (0,279,65535):
        for reverse in (False,True):
            for high in range(256):
                yield 280,192,[(anchor,180,v,20) if reverse else (v,20,anchor,180)
                               for v in range(high*256,(high+1)*256)]
    for high in range(256):
        yield 280,192,[(v,255,v,0) for v in range(high*256,(high+1)*256)]
    for high in range(256):
        yield 280,192,[(279,high,0,low) for low in range(256)]
    yield 280,192,[(65535,y,0,y) for y in range(256)]
    for width,height in GRIDS:yield width,height,grid_cases(width,height)
    for case in ALIGN_CASES:yield 280,192,[case]*256


def spans(width,height,case):
    x0,y0,x1,y1=case;x0,x1=sorted((x0,x1));y0,y1=sorted((y0,y1))
    if x0>=width or y0>=height:return []
    horizontal=lambda y:(1,x0&255,x0>>8,x1&255,x1>>8,y)
    vertical=lambda x,a,b:(2,x&255,x>>8,a,0,b)
    if x0==x1:return [vertical(x0,y0,y1)]
    if y0==y1:return [horizontal(y0)]
    result=[horizontal(y0)]
    if y1<height:result.append(horizontal(y1))
    if y0+1<y1:
        result.append(vertical(x0,y0+1,y1-1))
        if x1<width:result.append(vertical(x1,y0+1,y1-1))
    return result


def expected(width,height,cases):
    result=bytearray([0]*256+[0xA5]*6144)
    for index,case in enumerate(cases):
        calls=spans(width,height,case);result[index]=len(calls)
        for call,values in enumerate(calls):
            for field,value in enumerate(values):result[(1+call*6+field)*256+index]=value
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--reference',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-outline-entry-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "gfx.h"
void page_done(void);void finished(void);void align_call(void);void set_grid(void);
unsigned char records[25][256],index,align_kind,grid;
static const unsigned anchors[]={0,279,65535u};
static unsigned xs[8];static unsigned char ys[8];
static void clear_slot(void) {unsigned char i;records[0][index]=0;for(i=1;i<25;++i)records[i][index]=0xA5u;}
int main(void) {
    unsigned value,w;
    unsigned char anchor,reverse,h;
    volatile unsigned guard=0xA55Au;
    for(anchor=0;anchor<3;++anchor)for(reverse=0;reverse<2;++reverse) {
        value=0;
        do {
            index=(unsigned char)value;clear_slot();
            if(reverse)gfx_rect(anchors[anchor],180,value,20);
            else gfx_rect(value,20,anchors[anchor],180);
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    value=0;
    do {
        index=(unsigned char)value;clear_slot();gfx_rect(value,255,value,0);
        if(guard!=0xA55Au)for(;;) {}
        ++value;if((unsigned char)value==0)page_done();
    } while(value);
    value=0;
    do {
        index=(unsigned char)value;clear_slot();gfx_rect(279,(unsigned char)(value>>8),0,index);
        if(guard!=0xA55Au)for(;;) {}
        ++value;if((unsigned char)value==0)page_done();
    } while(value);
    for(value=0;value<256;++value) {index=(unsigned char)value;clear_slot();gfx_rect(65535u,index,0,index);}
    page_done();
    for(grid=0;grid<9;++grid) {
        set_grid();w=gfx_width;h=gfx_height;
        xs[0]=0;xs[1]=1;xs[2]=w?w-1u:0;xs[3]=w;xs[4]=w==65535u?w:w+1u;
        xs[5]=32767;xs[6]=32768u;xs[7]=65535u;
        ys[0]=0;ys[1]=1;ys[2]=h?h-1u:0;ys[3]=h;ys[4]=h==255u?h:h+1u;
        ys[5]=191;ys[6]=192;ys[7]=255;
        for(value=0;value<256;++value) {
            index=(unsigned char)value;clear_slot();
            gfx_rect(xs[value>>5],ys[(value>>4)&7],xs[(value>>2)&7],ys[value&7]);
            if(guard!=0xA55Au)for(;;) {}
        }
        page_done();
    }
    grid=0;set_grid();
    for(align_kind=0;align_kind<8;++align_kind) {
        for(value=0;value<256;++value) {index=(unsigned char)value;clear_slot();align_call();}
        page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done,resume,_finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        dummy=work/'grid_stub.s';dummy.write_text('.export _set_grid\n.code\n_set_grid: rts\n')
        align=work/'align.s'
        code='''.export _align_call
.import _gfx_rect, _index, _align_kind, pushax, pusha
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
 ldx x0hi,y
 lda x0lo,y
 jsr pushax
 ldy _align_kind
 lda y0,y
 jsr pusha
 ldy _align_kind
 ldx x1hi,y
 lda x1lo,y
 jsr pushax
 ldy _align_kind
 lda y1,y
 jsr _gfx_rect
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
        planes=[(x0&255,x0>>8,y0,x1&255,x1>>8,y1) for x0,y0,x1,y1 in ALIGN_CASES]
        for i,name in enumerate(('x0lo','x0hi','y0','x1lo','x1hi','y1')):
            code+=name+': .byte '+','.join(str(v[i]) for v in planes)+'\n'
        align.write_text(code)
        build(work,source,extra_sources=(marker,dummy,align))
        stub='''.export _gfx_hline, _gfx_vline, _gfx_width, _gfx_height, _set_grid
.import _records, _index, _grid, incsp3, incsp4
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.data
_gfx_width: .word 280
_gfx_height: .byte 192
.rodata
'''
        for name,values in (('widthlo',[w&255 for w,h in GRIDS]),('widthhi',[w>>8 for w,h in GRIDS]),('heights',[h for w,h in GRIDS])):
            stub+=name+': .byte '+','.join(map(str,values))+'\n'
        stub+='''.code
_set_grid:
 ldx _grid
 lda widthlo,x
 sta _gfx_width
 lda widthhi,x
 sta _gfx_width+1
 lda heights,x
 sta _gfx_height
 rts
'''
        for name,kind,fields,cleanup in (('_gfx_hline',1,(2,3,0,1,'tmp4'),4),('_gfx_vline',2,(1,2,0,'zero','tmp4'),3)):
            stub+=f'''{name}:
 sta tmp4
 ldx _index
 lda _records,x
 cmp #4
 bcc :+
fail_{kind}: jmp fail_{kind}
: inc _records,x
 sta tmp1
 asl
 clc
 adc tmp1
 asl
 clc
 adc #>(_records+256)
 sta ptr3+1
 lda #<(_records+256)
 sta ptr3
 ldy _index
 lda #{kind}
 sta (ptr3),y
 inc ptr3+1
'''
            for field in fields:
                if isinstance(field,int):stub+=f' ldy #{field}\n lda (sp),y\n'
                elif field=='zero':stub+=' lda #0\n'
                else:stub+=f' lda {field}\n'
                stub+=' ldy _index\n sta (ptr3),y\n inc ptr3+1\n'
            stub+=f' jsr scratch\n jmp incsp{cleanup}\n'
        stub+='scratch: lda #$5a\n'
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n rts\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        reference=[]
        if args.reference:
            ref=work/'reference.o';compile_source(DEV/'lib/gfx/gfx_rect_ref.c',ref,['-t','none','-Oirs','-I',DEV/'lib/gfx'])
            reference.append(ref)
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'entry.o',work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,*reference,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        assert labels['__BSS_RUN__']+labels['__BSS_SIZE__']<0x9000,'fixture overlaps alignment stack'
        steps=[]
        for _ in range(2066):
            steps += [labels.until('_page_done'),labels.peek('_records',6400),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==2066
        for index,(width,height,cases) in enumerate(batches()):
            assert result.dumps[index]==expected(width,height,cases),('outline batch',index,width,height,cases[0])
        print(f'GFX outline entry: 528,896 cases, full coordinates, nine grids, exact ordered spans, '
              f'hostile scratch, guards and 2,048 stack placements; IIe={args.iie}, reference={args.reference}.')


if __name__=='__main__':main()
