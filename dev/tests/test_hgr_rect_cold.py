#!/usr/bin/env python3
"""Cold C rectangle/cell wrappers: arguments across lazy table builders."""
from pathlib import Path
import tempfile
from test_hgr import build, a2test, offset, rect


def main():
    with tempfile.TemporaryDirectory(prefix='hgr-rect-cold-') as directory:
        work = Path(directory)
        source = work/'cold.c'
        source.write_text('''#include "hgr.h"
void ready(void); void done(void);
unsigned char kind;
int main(void) {
    unsigned i;
    for(i=0x2000; i<0x6000; ++i) *(unsigned char *)i=0xA5;
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
    }
    done();
    for(;;) {}
    return 0;
}
''')
        marker=work/'marker.s'
        marker.write_text('.export _ready, _done\n.code\n_ready: rts\n_done: rts\n')
        disk=build(work,source,extra_sources=(marker,))
        labels=a2test.labels(work/'test.lbl')
        for iie in (False,True):
            if iie and not a2test.have_a2shot('cold rectangle wrappers on IIe'):
                continue
            for base in (0,0x40):
                for kind in range(8):
                    steps=[labels.until('_ready'),labels.poke('_kind',kind),labels.poke('_hgr_base',base),
                           labels.until('_done'),'peek:2000:16384',labels.peek('_hgr_rowlo',192),
                           labels.peek('_hgr_rowhi',192),labels.peek('_hgr_col7',280),labels.peek('_hgr_mask7',280)]
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
                    assert result.mem(0x2000,16384)==pages[0]+pages[1], (iie,base,kind,'screen')
                    addresses=[((base or 0x20)<<8)+offset(y) for y in range(192)]
                    for name,shift in (('_hgr_rowlo',0),('_hgr_rowhi',8)):
                        assert result.mem(labels[name],192)==bytes(a>>shift & 255 for a in addresses), (iie,base,kind,name)
                    cols=bytes(x//7 for x in range(280)) if kind>=2 else bytes(280)
                    masks=bytes(1<<(x%7) for x in range(280)) if kind>=2 else bytes(280)
                    assert result.mem(labels['_hgr_col7'],280)==cols, (iie,base,kind,'columns')
                    assert result.mem(labels['_hgr_mask7'],280)==masks, (iie,base,kind,'masks')
        print('Cold rectangles/cells: arguments survive lazy row/column/mask builds; '
              'valid, empty and invalid calls, default/page 2, both screen pages and holes checked on II+/IIe.')


if __name__=='__main__':
    main()
