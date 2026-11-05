#!/usr/bin/env python3
"""DHGR page state: full byte domains, flip ordering and preserved index registers."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, run, a2test


def expected(base, flip=False):
    output=bytearray(6*256)
    for index in range(256):
        if flip:
            shown=1 if base==32 else 2
            target=32 if index==1 else 64 if index==2 else base
            values=(target,shown,1 if target==32 else 2,shown,1,shown)
        else:
            target=32 if index==1 else 64 if index==2 else base
            values=(target,0xA5,1 if target==32 else 2,0xA5,0,0xA5)
        for plane,value in enumerate(values):output[plane*256+index]=value
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-pages-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "dhgr_internal.h"
void page_done(void);void finished(void);
unsigned char records[6][256],index,show_calls,show_arg;
static void record(void) {
    records[0][index]=dhgr_base;records[1][index]=dhgr_display;
    records[2][index]=dhgr_get_draw_page();records[3][index]=dhgr_get_display_page();
    records[4][index]=show_calls;records[5][index]=show_arg;
}
int main(void) {
    unsigned base,value;
    unsigned char mode;
    volatile unsigned guard=0xA55Au;
    if(dhgr_base!=32 || dhgr_display || dhgr_get_draw_page()!=1 || dhgr_get_display_page())for(;;) {}
    for(mode=0;mode<2;++mode)for(base=0;base<256;++base) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;show_calls=0;show_arg=0xA5u;
            dhgr_base=(unsigned char)base;dhgr_display=mode?index:0xA5u;
            if(mode)dhgr_flip();else dhgr_draw_page(index);
            record();if(guard!=0xA55Au)for(;;) {}
        }
        page_done();
    }
    for(value=0;value<256;++value) {
        index=(unsigned char)value;dhgr_base=32;dhgr_display=index;
        show_calls=0;show_arg=0xA5u;record();
    }
    page_done();finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        build(work,source,extra_sources=(marker,))
        # Like the real assembly show-page entry, this preserves X/Y. Flip
        # may retain the prior display in Y across the query/show calls.
        sink=work/'sink.s';sink.write_text('''.export _dhgr_show_page
.import _dhgr_display, _show_calls, _show_arg
.code
_dhgr_show_page:
 cmp #1
 beq valid
 cmp #2
 bne fail
valid:
 inc _show_calls
 sta _show_arg
 sta _dhgr_display
 rts
fail: jmp fail
''')
        obj=work/'sink.o';run(['ca65','-o',obj,sink])
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
             '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',work/'entry.o',
             work/'apple2io_asm.o',work/'marker.o',obj,work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        steps=[]
        for _ in range(513):
            steps += [labels.until('_page_done'),labels.peek('_records',1536),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==513
        for mode in range(2):
            for base in range(256):
                assert result.dumps[mode*256+base]==expected(base,bool(mode)),('page state',mode,base)
        getter=bytes(v for plane in range(6) for i in range(256)
                     for v in ((32,i,1,i,0,0xA5)[plane],))
        assert result.dumps[512]==getter
    registers(args.iie)
    print(f'DHGR pages: 131,328 state combinations, every page/base/display byte, initial state, '
          f'flip show-before-draw ordering, guards and real show/query register contracts; IIe={args.iie}.')


def registers(iie):
    """Use the real show entry and check its X/Y preservation and soft switch."""
    with tempfile.TemporaryDirectory(prefix='dhgr-page-regs-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "dhgr_internal.h"
void probe(void);void finished(void);
unsigned char index,records[3][256];
int main(void) {
    unsigned value;
    for(value=0;value<256;++value) {
        index=(unsigned char)value;dhgr_base=index;dhgr_display=0xA5u;probe();
    }
    finished();for(;;) {}return 0;
}
''')
        probe=work/'probe.s';probe.write_text('''.export _probe, _finished
.import _index, _records, _dhgr_base, _dhgr_display
.import _dhgr_show_page, _dhgr_get_draw_page, _dhgr_get_display_page
.code
_probe:
 ldy #$37
 ldx #$64
 lda _index
 jsr _dhgr_show_page
 cpy #$37
 bne fail
 cpx #$64
 bne fail
 ldx _index
 lda _dhgr_display
 sta _records,x
 lda $c01c
 sta _records+256,x
 jsr _dhgr_get_draw_page
 cpy #$37
 bne fail
 cpx #0
 bne fail
 ldx _index
 sta _records+512,x
 jsr _dhgr_get_display_page
 cpy #$37
 bne fail
 cpx #0
 bne fail
 rts
fail: jmp fail
_finished: rts
''')
        disk=build(work,source,extra_sources=(probe,));labels=a2test.labels(work/'test.lbl')
        result=a2test.run(disk,[labels.until('_finished'),labels.peek('_records',768)],iie=iie)
        data=result.dumps[0]
        for page in range(256):
            assert data[page]==(page if page in (1,2) else 0xA5),(page,'display')
            assert data[512+page]==(1 if page==32 else 2),(page,'query')
            if iie and page>=1:assert bool(data[256+page]&128)==(page>=2),(page,'soft switch')


if __name__=='__main__':
    main()
