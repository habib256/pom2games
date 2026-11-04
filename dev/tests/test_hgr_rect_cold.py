#!/usr/bin/env python3
"""Cold rectangles/cells/recoloring: arguments across lazy table builders."""
from pathlib import Path
import argparse
import tempfile
from test_hgr import build, a2test, offset, rect, DEV, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folded',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-rect-cold-') as directory:
        work = Path(directory)
        source = work/'cold.c'
        source.write_text('''#include "hgr.h"
#include "hgr_internal.h"
void ready(void); void done(void);
unsigned char kind;
int main(void) {
    unsigned i;
    for(i=0x2000; i<0x6000; ++i) *(unsigned char *)i=0xA5;
    hgr_z_ce=0x96; hgr_z_co=0x69; hgr_z_hi=0xC3;
    ready();
    switch(kind) {
    case 0: hgr_fill_rect(189,255,38,255,0xDA); break;
    case 1: hgr_fill_rect(192,1,0,40,255); break;
    case 2: hgr_fill_pixrect(255,189,255,255); break;
    case 3: hgr_clear_pixrect(279,191,255,255); break;
    case 4: hgr_fill_pixrect(65535u,255,255,255); break;
    case 5: hgr_fill_pixrect(0,0,0,1); break;
    case 6: hgr_cell(34,23,255); break;
    case 7: hgr_cell(255,0,1); break;
    case 8: hgr_colorize(255,189,255,255,HGR_ORANGE); break;
    case 9: hgr_colorize(7,40,1,1,255); break;
    case 10: hgr_colorize(65535u,40,1,1,HGR_VIOLET); break;
    case 11: hgr_colorize(7,40,0,1,HGR_ORANGE); break;
    }
    done();
    for(;;) {}
    return 0;
}
''')
        marker=work/'marker.s'
        marker.write_text('.export _ready, _done\n.code\n_ready: rts\n_done: rts\n')
        disk=build(work,source,extra_sources=(marker,))
        if args.folded:
            # Resolve all three table families before the archive is scanned.
            folded=work/'folded.o'
            run(['ca65','-D','HGRC_X7_FOLDED=1','-o',folded,DEV/'lib/hgrc/hgr_columns.s'])
            run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
                 '-m',work/'test.map','-Ln',work/'test.lbl','-o',work/'test.bin',
                 work/'crt0_apple2.o',work/'cold.o',work/'apple2io_asm.o',folded,work/'hgrc.lib'])
            disk=a2test.build_disk(work,'TEST',work/'test.bin')
        labels=a2test.labels(work/'test.lbl')
        for iie in (False,True):
            if iie and not a2test.have_a2shot('cold rectangle wrappers on IIe'):
                continue
            for base in (0,0x40):
                for kind in range(12):
                    steps=[labels.until('_ready'),labels.poke('_kind',kind),labels.poke('_hgr_base',base),
                           labels.until('_done'),'peek:2000:16384',labels.peek('_hgr_rowlo',192),
                           labels.peek('_hgr_rowhi',192),labels.peek('_hgr_col7',280),labels.peek('_hgr_mask7',280),
                           labels.peek('_hgr_z_ce'),labels.peek('_hgr_z_co'),labels.peek('_hgr_z_hi')]
                    result=a2test.run(disk,steps,iie=iie)
                    pages=[bytearray([0xA5])*8192,bytearray([0xA5])*8192]
                    page=pages[base==0x40]
                    if kind==0:
                        for y in range(189,192):
                            page[offset(y)+38:offset(y)+40]=bytes([0xDA])*2
                    elif kind==2:
                        rect(page,255,189,279,191,set=True)
                    elif kind==3:
                        rect(page,279,191,279,191,set=False)
                    elif kind==6:
                        rect(page,272,184,277,189,set=True)
                    elif kind==8:
                        for y in range(189,192):
                            for col in range(36,40):
                                page[offset(y)+col]=(0xA5 & (0x55 if col&1 else 0x2A)) | 128
                    carrier=(0x2A,0x55,128) if kind==8 else (0x96,0x69,0xC3)
                    for name,value in zip(('_hgr_z_ce','_hgr_z_co','_hgr_z_hi'),carrier):
                        assert result.mem(labels[name],1)==bytes([value]), (iie,base,kind,name)
                    assert result.mem(0x2000,16384)==pages[0]+pages[1], (iie,base,kind,'screen')
                    addresses=[((base or 0x20)<<8)+offset(y) for y in range(192)]
                    for name,shift in (('_hgr_rowlo',0),('_hgr_rowhi',8)):
                        assert result.mem(labels[name],192)==bytes(a>>shift & 255 for a in addresses), (iie,base,kind,name)
                    cols=bytes(x//7 for x in range(280)) if kind>=2 else bytes(280)
                    masks=bytes(1<<(x%7) for x in range(280)) if kind>=2 and (kind<8 or args.folded) else bytes(280)
                    assert result.mem(labels['_hgr_col7'],280)==cols, (iie,base,kind,'columns')
                    assert result.mem(labels['_hgr_mask7'],280)==masks, (iie,base,kind,'masks')
        print(f'Cold rectangles/cells/recoloring (folded={args.folded}): arguments survive lazy row/column/mask builds; '
              'valid, empty and invalid calls, default/page 2, both screen pages and holes checked on II+/IIe.')


if __name__=='__main__':
    main()
