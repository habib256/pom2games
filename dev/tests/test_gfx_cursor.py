#!/usr/bin/env python3
"""GFX cursor domains, control characters, wrapping and string page crossings."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test

GRIDS=((35,24),(1,1),(255,255),(0,0))


def glyphs(cols,rows,col,row,data):
    col=col if col<cols else (cols-1)&255
    row=row if row<rows else (rows-1)&255
    result=[]
    for ch in data:
        if ch==10:
            col=0
            if row+1<rows:row+=1
        elif ch==13:col=0
        elif ch>=32:
            result.append((ch,col,row))
            col=(col+1)&255
            if col>=cols:
                col=0
                if row+1<rows:row+=1
    return result


def expected(cols,rows,kind,high):
    result=bytearray(7*256)
    for low in range(256):
        col,row,ch=((high,low,65),(low,23,high),(34,low,high))[kind]
        out=glyphs(cols,rows,col,row,(ch,90))
        for plane,value in enumerate((len(out),*out[0],*out[-1])):
            result[plane*256+low]=value
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-cursor-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "gfx.h"
void page_done(void);void finished(void);void set_grid(void);void align_call(void);
unsigned char records[7][256],index,grid,stream,align_kind;
static char buffer[384];
int main(void) {
    unsigned value,i;
    unsigned char kind,col,row,ch;
    volatile unsigned guard=0xA55Au;
    for(grid=0;grid<4;++grid) {
        set_grid();
        for(kind=0;kind<3;++kind) {
            value=0;
            do {
                index=(unsigned char)value;
                records[0][index]=0;
                if(kind==0) {col=(unsigned char)(value>>8);row=index;ch=65;}
                else if(kind==1) {col=index;row=23;ch=(unsigned char)(value>>8);}
                else {col=34;row=index;ch=(unsigned char)(value>>8);}
                gfx_gotoxy(col,row);gfx_putc(ch);gfx_putc(90);
                if(guard!=0xA55Au)for(;;) {}
                ++value;if((unsigned char)value==0)page_done();
            } while(value);
        }
    }
    grid=0;set_grid();
    for(align_kind=0;align_kind<3;++align_kind) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;records[0][index]=0;
            gfx_gotoxy(align_kind==1?34:33,align_kind==1?23:22);
            align_call();gfx_putc(90);
        }
        page_done();
    }
    stream=1;
    for(value=0;value<256;++value) {
        for(i=0;i<127;++i)buffer[value+i]=(char)(i+1);
        buffer[value+127]=0;
        for(i=0;i<256;++i)records[0][i]=records[1][i]=records[2][i]=0xA5u;
        index=0;gfx_gotoxy(33,22);gfx_text(buffer+value);
        if(guard!=0xA55Au)for(;;) {}
        page_done();
    }
    index=0;gfx_text("");page_done();
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done,resume,_finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        dummy=work/'grid_stub.s';dummy.write_text('.export _set_grid\n.code\n_set_grid: rts\n')
        align=work/'align.s'
        code=""".export _align_call
.import _gfx_gotoxy, _gfx_putc, _gfx_text, _index, _align_kind, pusha
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
 lda _align_kind
 beq position
 cmp #1
 beq character
 lda #<message
 ldx #>message
 jsr _gfx_text
 jmp check
character:
 lda #65
 jsr _gfx_putc
 jmp check
position:
 lda #255
 jsr pusha
 lda #255
 jsr _gfx_gotoxy
check:
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
message: .byte 65,10,66,13,67,0
"""
        align.write_text(code)
        build(work,source,extra_sources=(marker,dummy,align))
        stub='''.export _gfx_cell_glyph, _gfx_text_cols, _gfx_text_rows, _set_grid
.import _records, _index, _grid, _stream, incsp2
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.data
_gfx_text_cols: .byte 35
_gfx_text_rows: .byte 24
.bss
saved_row: .res 1
.rodata
cols: .byte 35,1,255,0
rows: .byte 24,1,255,0
.code
_set_grid:
 ldx _grid
 lda cols,x
 sta _gfx_text_cols
 lda rows,x
 sta _gfx_text_rows
 rts
_gfx_cell_glyph:
 sta saved_row
 ldx _index
 lda _stream
 beq pair
 lda saved_row
 sta _records+512,x
 ldy #0
 lda (sp),y
 sta _records+256,x
 iny
 lda (sp),y
 sta _records,x
 inc _index
 jmp done
pair:
 inc _records,x
 lda _records,x
 cmp #1
 bne last
 lda saved_row
 sta _records+768,x
 ldy #0
 lda (sp),y
 sta _records+512,x
 iny
 lda (sp),y
 sta _records+256,x
last:
 lda saved_row
 sta _records+1536,x
 ldy #0
 lda (sp),y
 sta _records+1280,x
 iny
 lda (sp),y
 sta _records+1024,x
done:
 lda #$5a
'''
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n jmp incsp2\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'entry.o',work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(3075):
            steps += [labels.until('_page_done'),labels.peek('_records',1792),labels.until('resume')]
        for _ in range(256):
            steps += [labels.until('_page_done'),labels.peek('_records',768),labels.peek('_index'),labels.until('resume')]
        steps += [labels.until('_page_done'),labels.peek('_index'),labels.until('resume'),labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==3588
        offset=0
        for cols,rows in GRIDS:
            for kind in range(3):
                for high in range(256):
                    assert result.dumps[offset]==expected(cols,rows,kind,high),(cols,rows,kind,high)
                    offset+=1
        for col,row,data in ((255,255,(90,)),(34,23,(65,90)),(33,22,(65,10,66,13,67,90))):
            out=glyphs(35,24,col,row,data)
            want=b''.join(bytes((v,))*256 for v in (len(out),*out[0],*out[-1]))
            assert result.dumps[offset]==want,('stack alignment',col,row,data)
            offset+=1
        out=glyphs(35,24,33,22,range(1,128));want=bytearray([0xA5]*768)
        for index,values in enumerate(out):
            for plane,value in enumerate(values):want[plane*256+index]=value
        for alignment in range(256):
            assert result.dumps[offset]==want,('string',alignment)
            assert result.dumps[offset+1]==bytes((len(out),)),('length',alignment)
            offset+=2
        assert result.dumps[offset]==b'\0','empty string rendered'
        print(f'GFX cursor: 786,432 coordinate/control cases, four grids, all byte characters, '
              f'256 string alignments, 768 stack placements, exact glyph streams, hostile scratch and guards; IIe={args.iie}.')


if __name__=='__main__':main()
