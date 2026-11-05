#!/usr/bin/env python3
"""Monochrome GFX pen, point/span forwarding and independent clear semantics."""
import argparse
import re
import tempfile
from pathlib import Path
from test_hgr import DEV, build, compile_source, run, a2test


def expected(kind,high):
    result=bytearray([0xA5]*2304)
    for low in range(256):
        value=high*256+low
        fields={0:kind+1,1:low,2:high,7:int(high!=0)}
        if kind==0:fields[5]=low
        elif kind==1:fields.update({3:255-low,4:255-high,5:low})
        elif kind==2:fields.update({5:low,6:high})
        else:fields.update({0:1,2:0,5:191,7:int(low!=255),8:15 if low else 0})
        for plane,byte in fields.items():result[plane*256+low]=byte
    return result


def check_archive(work):
    prefix='gfx_backend_dhgr_mono'
    cases=(('set_color','dhgr_set_color(255);',('set_color','state')),
           ('dimensions','return gfx_width==560u && gfx_height==192u;',('',)),
           ('plot','gfx_plot(559,191);',('plot','state')),
           ('hline','gfx_hline(0,65535u,191);',('hline','state')),
           ('vline','gfx_vline(559,255,0);',('vline','state')),
           ('rect','gfx_filled_rect(65535u,255,0,0);',('rect','state')),
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
        if name in ('set_color','dimensions'):
            assert not any(n.startswith('dhgr_') for n in linked),(name,'drawing dependency')
    print('GFX DHGR mono archive: seven minimal clients omit unused backend and drawing families.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-dhgr-mono-entries-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "gfx.h"
#include "dhgr.h"
void page_done(void);void finished(void);
unsigned char records[9][256],index;
static void clear_slot(void) {unsigned char i;for(i=0;i<9;++i)records[i][index]=0xA5u;}
int main(void) {
    unsigned value;
    unsigned char kind;
    volatile unsigned guard=0xA55Au;
    for(kind=0;kind<3;++kind) {
        value=0;
        do {
            index=(unsigned char)value;clear_slot();
            dhgr_set_color((unsigned char)(value>>8));
            if(kind==0)gfx_plot(value,index);
            else if(kind==1)gfx_hline(value,65535u-value,index);
            else gfx_vline(value,index,(unsigned char)(value>>8));
            if(guard!=0xA55Au)for(;;) {}
            ++value;if((unsigned char)value==0)page_done();
        } while(value);
    }
    for(value=0;value<256;++value) {
        index=(unsigned char)value;clear_slot();
        dhgr_set_color(index^255u);gfx_clear(index);gfx_plot(value,191);
        if(guard!=0xA55Au)for(;;) {}
    }
    page_done();finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done,resume,_finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        build(work,source,extra_sources=(marker,),gfx_backend='gfx_backend_dhgr_mono.c')
        check_archive(work)
        stub='''.export _dhgr_plot, _dhgr_hline, _dhgr_vline, _dhgr_clear
.import _records, _index, incsp3, incsp4, incsp5
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.code
'''
        for name,kind,planes,cleanup in (('_dhgr_plot',1,(5,1,2),3),
                ('_dhgr_hline',2,(5,3,4,1,2),5),('_dhgr_vline',3,(6,5,1,2),4)):
            stub+=f'{name}:\n ldx _index\n sta _records+1792,x\n lda #{kind}\n sta _records,x\n'
            for offset,plane in enumerate(planes):
                stub+=f' ldy #{offset}\n lda (sp),y\n sta _records+{plane*256},x\n'
            stub+=f' jsr scratch\n jmp incsp{cleanup}\n'
        stub+='_dhgr_clear:\n ldx _index\n sta _records+2048,x\nscratch:\n lda #$5a\n'
        for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'):
            stub+=f' sta {name}\n'
        stub+=' tax\n tay\n rts\n'
        sink=work/'sink.s';sink.write_text(stub);obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'entry.o',work/'apple2io_asm.o',work/'marker.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(769):
            steps += [labels.until('_page_done'),labels.peek('_records',2304),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==769
        pos=0
        for kind in range(3):
            for high in range(256):
                assert result.dumps[pos]==expected(kind,high),(kind,high)
                pos+=1
        assert result.dumps[pos]==expected(3,0),'clear/pen independence'
        print(f'GFX DHGR mono: 196,608 full-coordinate forwarding calls, all pen/color bytes, '
              f'clear/pen independence, hostile scratch and guards; IIe={args.iie}.')


if __name__=='__main__':main()
