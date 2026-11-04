#!/usr/bin/env python3
"""Native-size text entry: all 16-bit x values, byte y values and cold tables."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test, offset


def expected(xs, ys):
    result=bytearray([0]*256+[0xA5]*(3*256))
    for index,(x,y) in enumerate(zip(xs,ys)):
        if x<=273 and y<=184:
            result[index]=1
            result[256+index]=(273-x)//8+1
            result[512+index]=x//7
            result[768+index]=x%7
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--folded',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='text8-entry-') as directory:
        work=Path(directory)
        source=work/'entry.c'
        source.write_text('''#include "hgr.h"
void cold_ready(void); void cold_done(void); void page_done(void); void ys_done(void);
unsigned char results[4][256],index,expected_y,test_y;
unsigned test_x;
const char message[]="A";
static void clear_slot(void) {
    results[0][index]=0;
    results[1][index]=results[2][index]=results[3][index]=0xA5;
}
int main(void) {
    unsigned x;
    for(x=0;x<256;++x) {index=(unsigned char)x;clear_slot();}
    index=0;
    cold_ready();
    expected_y=test_y;
    hgr_puts8(test_x,test_y,message);
    cold_done();
    x=0; expected_y=184;
    do {
        index=(unsigned char)x;
        clear_slot();
        hgr_puts8(x,184,message);
        ++x;
        if((unsigned char)x==0) page_done();
    } while(x!=0);
    for(x=0;x<256;++x) {
        index=(unsigned char)x; expected_y=index;
        clear_slot();
        hgr_puts8(273,index,message);
    }
    ys_done();
    for(;;) {}
    return 0;
}
''')
        marker=work/'marker.s'
        marker.write_text('.export _cold_ready, _cold_done, _page_done, resume, _ys_done\n.code\n'
                          '_cold_ready: rts\n_cold_done: rts\n_page_done: nop\nresume: rts\n_ys_done: rts\n')
        build(work,source,extra_sources=(marker,))
        stub=work/'sink.s'
        stub.write_text('''.export _hgr_puts_run8
.import _results, _index, _expected_y, _message, _hgr_font
.importzp _hgr_t_s, _hgr_t_font, _hgr_t_n, _hgr_t_col, _hgr_t_bit, _hgr_g_y
.code
_hgr_puts_run8:
 lda _hgr_t_s
 cmp #<_message
 bne fail
 lda _hgr_t_s+1
 cmp #>_message
 bne fail
 lda _hgr_t_font
 cmp #<_hgr_font
 bne fail
 lda _hgr_t_font+1
 cmp #>_hgr_font
 bne fail
 lda _hgr_g_y
 cmp _expected_y
 bne fail
 ldx _index
 lda #1
 sta _results,x
 lda _hgr_t_n
 sta _results+256,x
 lda _hgr_t_col
 sta _results+512,x
 lda _hgr_t_bit
 sta _results+768,x
 rts
fail: jmp fail
''')
        obj=work/'sink.o';run(['ca65','-o',obj,stub])
        overrides=[obj]
        if args.folded:
            folded=work/'folded.o'
            run(['ca65','-D','HGRC_X7_FOLDED=1','-o',folded,DEV/'lib/hgrc/hgr_columns.s'])
            overrides.append(folded)
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-m',work/'test.map','-Ln',work/'test.lbl','-o',work/'test.bin',
             work/'crt0_apple2.o',work/'entry.o',work/'apple2io_asm.o',*overrides,work/'hgrc.lib'])
        disk=a2test.build_disk(work,'TEST',work/'test.bin')
        labels=a2test.labels(work/'test.lbl')
        cold=[(28+phase,7) for phase in range(7)]+[(0,0),(256,184),(273,184),
              (274,0),(280,0),(65535,0),(7,185),(7,255)]
        for base in (0,0x40):
            for x,y in cold:
                steps=[labels.until('_cold_ready'),labels.poke('_test_x',x&255),
                       f'poke:{labels["_test_x"]+1:04X}:{x>>8:02X}',labels.poke('_test_y',y),
                       labels.poke('_hgr_base',base),labels.until('_cold_done'),labels.peek('_results',1024),
                       labels.peek('_hgr_rowlo',192),labels.peek('_hgr_rowhi',192),
                       labels.peek('_hgr_col7',280),labels.peek('_hgr_phase7',280)]
                result=a2test.run(disk,steps,iie=args.iie)
                assert result.mem(labels['_results'],1024)==expected([x],[y]),('cold',base,x,y)
                addresses=[((base or 0x20)<<8)+offset(row) for row in range(192)]
                for name,shift in (('_hgr_rowlo',0),('_hgr_rowhi',8)):
                    assert result.mem(labels[name],192)==bytes(a>>shift&255 for a in addresses),('cold',name)
                assert result.mem(labels['_hgr_col7'],280)==bytes(i//7 for i in range(280)),('cold','columns')
                assert result.mem(labels['_hgr_phase7'],280)==bytes(i%7 for i in range(280)),('cold','phases')
        steps=[]
        for _ in range(256):
            steps += [labels.until('_page_done'),labels.peek('_results',1024),labels.until('resume')]
        steps += [labels.until('_ys_done'),labels.peek('_results',1024)]
        result=a2test.run(disk,steps,iie=args.iie)
        for high in range(256):
            assert result.dumps[high]==expected(range(high*256,(high+1)*256),[184]*256),('x',high)
        assert result.dumps[256]==expected([273]*256,range(256)), 'y sweep'
        print(f'HGR text8 entry: all 65,536 x and 256 y values, {len(cold)*2} cold calls, '
              f'counts/columns/phases/string/font/rows and rejection; folded={args.folded}, IIe={args.iie}.')


if __name__=='__main__':
    main()
