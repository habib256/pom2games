#!/usr/bin/env python3
"""Mutable HGR rows, cold bases, invalid queries, page changes and display flags."""
from pathlib import Path
import tempfile
from test_hgr import build, a2test


def check_page_selection(work):
    source = work / 'page_select.c'
    source.write_text('''#include "hgr.h"
#include "hgr_internal.h"
void checkpoint(void);
unsigned char state[4];
int main(void) {
    unsigned p;
    unsigned char mode;
    for(mode=0; mode<2; ++mode) {
        if(mode) hgr_lores_build();
        for(p=0; p<256; ++p) {
            hgr_set_draw_page(2); hgr_show_page();
            hgr_set_draw_page((unsigned char)p);
            state[0]=hgr_get_draw_page(); state[1]=hgr_base;
            state[2]=hgr_lo_base; state[3]=hgr_lo_ready;
            checkpoint();
        }
    }
    for(;;) {}
    return 0;
}
''')
    marker = work / 'page_marker.s'
    marker.write_text('.export _checkpoint, resume\n.code\n_checkpoint: nop\nresume: rts\n')
    disk = build(work,source,extra_sources=(marker,))
    labels = a2test.labels(work/'test.lbl')
    steps = []
    for _ in range(512):
        steps += [labels.until('_checkpoint'), labels.peek('_state',4),
                  labels.peek('_hgr_rowlo',192), labels.peek('_hgr_rowhi',192),
                  labels.peek('_hgr_lo_rowlo',24), labels.peek('_hgr_lo_rowhi',24),
                  'peek:C01C:1', labels.until('resume')]
    for iie in (False,True):
        if iie and not a2test.have_a2shot('page selection on IIe'):
            continue
        result = a2test.run(disk,steps,iie=iie)
        for index in range(512):
            mode, p = divmod(index,256)
            page = 2 if p == 2 else 1
            base, lowbase = (0x40,8) if page == 2 else (0x20,4)
            assert result.mem(labels['_state'],4,index) == bytes((page,base,lowbase,mode)), (iie,index)
            rows = [(base<<8)+a2test.hgr_offset(y) for y in range(192)]
            for name,shift in (('_hgr_rowlo',0),('_hgr_rowhi',8)):
                assert result.mem(labels[name],192,index) == bytes(a>>shift & 255 for a in rows), (iie,index,name)
            rows = [(lowbase<<8)+(y&7)*128+(y>>3)*40 for y in range(24)]
            for name,shift in (('_hgr_lo_rowlo',0),('_hgr_lo_rowhi',8)):
                expected = bytes(a>>shift & 255 for a in rows) if mode else bytes(24)
                assert result.mem(labels[name],24,index) == expected, (iie,index,name)
            if iie:
                assert result.mem(0xC01C,1,index)[0]&128, 'select changed the displayed page'
    print('Page selection: all 256 arguments with LORES cold/ready; synchronous HGR/LORES rows, defaults, same-page calls and display preservation OK.')


def main():
    with tempfile.TemporaryDirectory(prefix='hgr-rows-') as directory:
        work = Path(directory)
        source = work / 'rows.c'
        source.write_text('''#include "hgr.h"
#include "hgr_internal.h"
void ready(void); void invalid_done(void); void checkpoint(void); void display_checkpoint(void);
unsigned rows[256], invalid;
static const unsigned char pages[5]={2,1,0,255,2};
static const unsigned char flags[4]={0,1,2,255};
int main(void) {
    unsigned y;
    unsigned char stage;
    ready();
    invalid=(unsigned)hgr_row(255);
    invalid_done();
    for(stage=0; stage<6; ++stage) {
        if(stage) hgr_set_draw_page(pages[stage-1]);
        for(y=0; y<256; ++y) rows[y]=(unsigned)hgr_row((unsigned char)y);
        hgr_build_rows(); /* already ready */
        hgr_show_page();
        checkpoint();
    }
    for(stage=0; stage<4; ++stage) {
        hgr_draw_page2=flags[stage];
        hgr_show_page();
        display_checkpoint();
    }
    for(;;) {}
    return 0;
}
''')
        marker = work / 'marker.s'
        marker.write_text('''.export _ready, _invalid_done, _checkpoint, resume, _display_checkpoint, display_resume
.code
_ready: rts
_invalid_done: rts
_checkpoint: nop
resume: rts
_display_checkpoint: nop
display_resume: rts
''')
        disk = build(work,source,extra_sources=(marker,))
        labels = a2test.labels(work/'test.lbl')
        tested = []
        for iie in (False,True):
            if iie and not a2test.have_a2shot('HGR rows/display on IIe'):
                continue
            for initial in (0,0x20,0x40):
                steps = [labels.until('_ready'), labels.poke('_hgr_base',initial),
                         labels.until('_invalid_done'), labels.peek('_invalid',2),
                         labels.peek('_hgr_base'), labels.peek('_hgr_rowlo',192), labels.peek('_hgr_rowhi',192)]
                for _ in range(6):
                    steps += [labels.until('_checkpoint'), labels.peek('_rows',512),
                              labels.peek('_hgr_rowlo',192), labels.peek('_hgr_rowhi',192),
                              'peek:C01C:1', labels.until('resume')]
                for _ in range(4):
                    steps += [labels.until('_display_checkpoint'), 'peek:C01C:1', labels.until('display_resume')]
                result = a2test.run(disk,steps,iie=iie)
                assert result.mem(labels['_invalid'],2) == b'\0\0'
                assert result.mem(labels['_hgr_base'],1) == bytes([initial]), 'invalid query initialized base'
                for name in ('_hgr_rowlo','_hgr_rowhi'):
                    assert result.mem(labels[name],192,0) == bytes(192), 'invalid query built tables'
                for index,base in enumerate((initial or 0x20,0x40,0x20,0x20,0x20,0x40)):
                    addresses = [(base<<8)+a2test.hgr_offset(y) for y in range(192)]
                    expected = b''.join(addr.to_bytes(2,'little') for addr in addresses) + bytes(128)
                    assert result.mem(labels['_rows'],512,index) == expected, (iie,initial,index,'queries')
                    assert result.mem(labels['_hgr_rowlo'],192,index+1) == bytes(a & 255 for a in addresses)
                    assert result.mem(labels['_hgr_rowhi'],192,index+1) == bytes(a>>8 for a in addresses)
                if iie:
                    shown = [bool(result.mem(0xC01C,1,k)[0]&128) for k in range(10)]
                    assert shown == [False,True,False,False,False,True,False,True,True,True], shown
            tested.append('IIe' if iie else 'II+')
        check_page_selection(work)
        print(f'HGR rows ({"/".join(tested)}): all 256 queries, cold bases 0/$20/$40, '
              'both table bytes, page changes, invalid pages/rows, warm guard; IIe display truth values checked when available.')


if __name__ == '__main__':
    main()
