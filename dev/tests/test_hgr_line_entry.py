#!/usr/bin/env python3
"""HGR line entry: complete coordinate domains and exact axis/core dispatch."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--folded',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-line-entry-') as directory:
        work=Path(directory)
        source=work/'entry.c'
        source.write_text('''#include "hgr.h"
void cold_ready(void); void cold_done(void); void page_done(void); void finished(void);
unsigned x0,x1;
unsigned char y0,y1,route,records[256];
int main(void) {
    unsigned value;
    unsigned char field;
    volatile unsigned guard=0xA55Au;
    cold_ready();
    hgr_line(x0,y0,x1,y1);
    cold_done();
    for(field=0;field<4;++field) {
        value=0;
        do {
            x0=28; y0=7; x1=31; y1=9;
            if(field==0) x0=value;
            if(field==1) x1=value;
            if(field==2) y0=(unsigned char)value;
            if(field==3) y1=(unsigned char)value;
            route=0;
            hgr_line(x0,y0,x1,y1);
            if(guard!=0xA55Au) for(;;) {}
            records[(unsigned char)value]=route;
            ++value;
            if((unsigned char)value==0) page_done();
        } while(value && (field<2 || value<256));
    }
    finished();
    for(;;) {}
    return 0;
}
''')
        marker=work/'marker.s'
        marker.write_text('.export _cold_ready, _cold_done, _page_done, resume, _finished\n.code\n'
                          '_cold_ready: rts\n_cold_done: rts\n_page_done: nop\nresume: rts\n_finished: rts\n')
        build(work,source,extra_sources=(marker,))
        # Sink checks arguments before returning, so a wrong branch or byte
        # cannot silently produce an expected route marker.
        stub='''.export _hgr_line_asm, _hgr_hline, _hgr_vline
.export _hgr_l_x0, _hgr_l_x1, _hgr_l_y0, _hgr_l_y1
.import _x0, _x1, _y0, _y1, _route, incsp3, incsp4
.importzp sp
.bss
_hgr_l_x0: .res 2
_hgr_l_x1: .res 2
_hgr_l_y0: .res 1
_hgr_l_y1: .res 1
.code
fail: jmp fail
_hgr_line_asm:
'''
        for name in ('x0','x1','y0','y1'):
            for offset in range(2 if name[0]=='x' else 1):
                stub+=f' lda _hgr_l_{name}+{offset}\n cmp _{name}+{offset}\n bne fail\n'
        stub+=' lda #1\n sta _route\n rts\n_hgr_hline:\n cmp _y0\n bne fail\n'
        for offset,name in enumerate(('x1','x1+1','x0','x0+1')):
            stub+=f' ldy #{offset}\n lda (sp),y\n cmp _{name}\n bne fail\n'
        stub+=' lda #2\n sta _route\n jmp incsp4\n_hgr_vline:\n cmp _y1\n bne fail_v\n'
        for offset,name in enumerate(('y0','x0','x0+1')):
            stub+=f' ldy #{offset}\n lda (sp),y\n cmp _{name}\n bne fail_v\n'
        stub+=' lda #3\n sta _route\n jmp incsp3\nfail_v: jmp fail_v\n'
        sink=work/'sink.s';sink.write_text(stub)
        obj=work/'sink.o';run(['ca65','-o',obj,sink]);overrides=[obj]
        if args.folded:
            obj=work/'folded.o'
            run(['ca65','-D','HGRC_X7_FOLDED=1','-o',obj,DEV/'lib/hgrc/hgr_columns.s'])
            overrides.append(obj)
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
             work/'entry.o',work/'apple2io_asm.o',work/'marker.o',*overrides,work/'hgrc.lib'])
        disk=a2test.build_disk(work,'TEST',work/'test.bin');labels=a2test.labels(work/'test.lbl')
        cases=((28,7,31,9),(279,191,0,0),(279,80,0,80),(279,191,279,0),
               (279,191,279,191),(280,0,0,0),(0,0,65535,1),(0,192,7,8),(7,8,0,255))
        for case in cases:
            steps=[labels.until('_cold_ready')]
            for name,value in zip(('x0','y0','x1','y1'),case):
                steps.append(labels.poke('_'+name,value&255))
                if name[0]=='x':steps.append(f'poke:{labels["_"+name]+1:04X}:{value>>8:02X}')
            steps += [labels.until('_cold_done'),labels.peek('_route',1),
                      labels.peek('_hgr_rowhi',192),labels.peek('_hgr_col7',280),labels.peek('_hgr_mask7',280)]
            result=a2test.run(disk,steps,iie=args.iie)
            route=expected(*case)
            assert result.mem(labels['_route'],1)==bytes([route]),('cold',case)
            # Mock axes do not construct tables; only diagonal dispatch does.
            for name,length in (('_hgr_rowhi',192),('_hgr_col7',280),('_hgr_mask7',280)):
                data=result.mem(labels[name],length)
                assert any(data)==(route==1),('lazy tables',case,name)
        steps=[]
        for _ in range(514):
            steps += [labels.until('_page_done'),labels.peek('_records',256),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        at=0
        for field,limit in enumerate((65536,65536,256,256)):
            for high in range(limit//256):
                wanted=[]
                for low in range(256):
                    case=[28,7,31,9];case[(0,2,1,3)[field]]=high*256+low
                    wanted.append(expected(*case))
                assert result.dumps[at]==bytes(wanted),(field,high)
                at+=1
        print(f'HGR line entry: 131,584 coordinate cases, exact core/axis arguments, '
              f'rejection, lazy tables, caller guard; folded={args.folded}, IIe={args.iie}.')


def expected(x0,y0,x1,y1):
    if x0>279 or x1>279 or y0>191 or y1>191:return 0
    if y0==y1:return 2
    if x0==x1:return 3
    return 1


if __name__=='__main__':
    main()
