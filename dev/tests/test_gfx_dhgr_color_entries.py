#!/usr/bin/env python3
"""Color GFX point clipping, pen masking, clear independence and exact forwarding."""
import argparse
import re
import tempfile
from pathlib import Path
from test_hgr import DEV, build, compile_source, run, a2test


ALIGN_CASES=((139,191),(65535,191),(0,255),(140,0))


def expected(kind,high):
    result=bytearray([0]*256+[0xA5]*1536)
    for low in range(256):
        x=high*256+low if kind==0 else 139
        y=low if kind<2 else 191
        pen=(high if kind<2 else low^255)&15
        if kind==3:x,y=ALIGN_CASES[high];pen=low&15
        result[6*256+low]=pen
        if kind==2:result[4*256+low]=low
        if x>=140:continue
        for plane,byte in ((0,1),(1,x),(2,y),(3,pen),(5,x)):
            result[plane*256+low]=byte
    return result


def check_archive(work):
    prefix='gfx_backend_dhgr_color'
    cases=(('set_color','dhgr_set_color(255);',('set_color',)),
           ('dimensions','return gfx_width==140u && gfx_height==192u;',('',)),
           ('plot','gfx_plot(139,191);',('plot',)),
           ('hline','gfx_hline(0,65535u,191);',('hline','rect')),
           ('vline','gfx_vline(139,255,0);',('vline','rect')),
           ('rect','gfx_filled_rect(65535u,255,0,0);',('rect',)),
           ('clear','gfx_clear(255);',('clear',)))
    for name,call,members in cases:
        source=work/('link_'+name+'.c');obj=source.with_suffix('.o');mapfile=source.with_suffix('.map')
        source.write_text('#include "gfx.h"\n#include "dhgr.h"\nint main(void){'+call+'return 0;}\n')
        compile_source(source,obj,['-t','none','-Oirs','-I',DEV/'lib/gfx','-I',DEV/'lib/hgrc'])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-m',mapfile,'-o',source.with_suffix('.bin'),work/'crt0_apple2.o',obj,work/'hgrc.lib'])
        linked=set(re.findall(r'hgrc\.lib\(([^)]+)\)',mapfile.read_text()))
        actual={n for n in linked if n.startswith(prefix)}
        expected={prefix+('_'+n if n else '')+'.o' for n in members}
        assert actual==expected,(name,actual,expected)
        assert not any(n.startswith('hgr_') for n in linked),(name,'HGR dependency')
        assert ('dhgr_color_state.o' in linked)==(name not in ('dimensions','clear')),(name,'pen state')
        if name in ('set_color','dimensions'):
            assert not any(n.startswith('dhgr_') and n!='dhgr_color_state.o' for n in linked),(name,'drawing dependency')
    print('GFX DHGR color archive: seven minimal clients omit unused backend and drawing families.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--reference',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-dhgr-color-entries-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "gfx.h"
#include "dhgr.h"
void page_done(void);void finished(void);void align_call(void);
extern unsigned char dhgr_dot_x,dhgr_dot_color;
unsigned char records[7][256],index,align_kind;
static void clear_slot(void) {unsigned char i;records[0][index]=0;for(i=1;i<7;++i)records[i][index]=0xA5u;dhgr_dot_x=0xA5u;}
int main(void) {
    unsigned value;
    unsigned char kind;
    volatile unsigned guard=0xA55Au;
    for(kind=0;kind<2;++kind) {
        value=0;
        do {
            index=(unsigned char)value;clear_slot();
            dhgr_set_color((unsigned char)(value>>8));
            gfx_plot(kind==0?value:139,index);
            records[5][index]=dhgr_dot_x;records[6][index]=dhgr_dot_color;
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    for(value=0;value<256;++value) {
        index=(unsigned char)value;clear_slot();
        dhgr_set_color(index^255u);gfx_clear(index);gfx_plot(139,191);
        records[5][index]=dhgr_dot_x;records[6][index]=dhgr_dot_color;
        if(guard!=0xA55Au)for(;;) {}
    }
    page_done();
    for(align_kind=0;align_kind<4;++align_kind) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;clear_slot();dhgr_set_color(index);align_call();
            records[5][index]=dhgr_dot_x;records[6][index]=dhgr_dot_color;
        }
        page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done,resume,_finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s'
        code='''.export _align_call
.import _gfx_plot, _index, _align_kind, pushax
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
 jsr _gfx_plot
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
        planes=[(x&255,x>>8,y) for x,y in ALIGN_CASES]
        for i,name in enumerate(('xlo','xhi','ys')):
            code+=name+': .byte '+','.join(str(v[i]) for v in planes)+'\n'
        align.write_text(code)
        build(work,source,extra_sources=(marker,align),gfx_backend='gfx_backend_dhgr_color.c')
        if not args.reference:check_archive(work)
        stub='''.export _dhgr_color_dot, _dhgr_clear, _dhgr_dot_x, _dhgr_dot_color
.import _records, _index
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.bss
_dhgr_dot_x: .res 1
_dhgr_dot_color: .res 1
.code
_dhgr_color_dot:
 ldx _index
 sta _records+512,x
 inc _records,x
 lda _dhgr_dot_x
 sta _records+256,x
 lda _dhgr_dot_color
 sta _records+768,x
 jmp scratch
_dhgr_clear:
 ldx _index
 sta _records+1024,x
scratch:
 lda #$5a
'''
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n rts\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        reference=[]
        if args.reference:
            ref=work/'reference.o'
            compile_source(DEV/'lib/gfx/gfx_backend_dhgr_color.c',ref,
                           ['-t','none','-Oirs','-I',DEV/'lib/gfx','-I',DEV/'lib/hgrc'])
            reference.append(ref)
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'entry.o',work/'apple2io_asm.o',work/'marker.o',work/'align.o',obj,*reference,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(517):
            steps += [labels.until('_page_done'),labels.peek('_records',1792),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==517
        pos=0
        for kind in range(2):
            for high in range(256):
                assert result.dumps[pos]==expected(kind,high),(kind,high)
                pos+=1
        assert result.dumps[pos]==expected(2,0),'clear/pen independence'
        for high in range(4):
            pos+=1;assert result.dumps[pos]==expected(3,high),('stack',high)
        print(f'GFX DHGR color: 131,072 point calls, every x word and y/color byte pair, '
              f'rejected x leaves coordinates alone, all clear bytes, pen independence, hostile scratch, guards and 1,024 stack placements; IIe={args.iie}, reference={args.reference}.')


if __name__=='__main__':main()
