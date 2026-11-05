#!/usr/bin/env python3
"""Move-entry contract: all IDs, undefined shapes, full coordinates and stacks."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import build, a2test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='sprengine-move-') as directory:
        work = Path(directory)
        source = work/'move.c'
        source.write_text('''#include "hgr.h"
extern const hgr_mspr_t *spr_shape[8];
extern unsigned spr_x[8];
extern unsigned char spr_y[8],spr_active[8],spr_count;
unsigned read_sp(void); unsigned char read_hwsp(void); void finished(void);
unsigned calls;
unsigned char error;
static const unsigned positions[]={0,1,256,279,65535u};
static const unsigned char rows[]={0,40,191,192,255},counts[]={0,1,2,8};
static const unsigned pointers[]={0,0x0034,0x3400,0x3456};
static unsigned id,stack_before;
static unsigned char ci,pi,si,slot,hw_before;
int main(void) {
    volatile unsigned guard=0xa55a;
    for(ci=0;ci<4;++ci)for(pi=0;pi<5;++pi)for(si=0;si<4;++si)
    for(id=0;id<256;++id) {
        spr_count=counts[ci];
        for(slot=0;slot<8;++slot) {
            spr_shape[slot]=(const hgr_mspr_t *)pointers[si];
            spr_x[slot]=0xaa00u+slot; spr_y[slot]=0xa0u+slot;
            spr_active[slot]=0x80u+slot;
        }
        stack_before=read_sp(); hw_before=read_hwsp();
        hgr_spr_move((unsigned char)id,positions[pi],rows[pi]);
        if(read_sp()!=stack_before || read_hwsp()!=hw_before || guard!=0xa55a) {
            error=1;goto done;
        }
        if(spr_count!=counts[ci]){error=2;goto done;}
        for(slot=0;slot<8;++slot) {
            if(spr_shape[slot]!=(const hgr_mspr_t *)pointers[si]){error=3;goto done;}
            if(id<counts[ci] && slot==id) {
                if(spr_x[slot]!=positions[pi] || spr_y[slot]!=rows[pi] ||
                   spr_active[slot]!=(si!=0)) {error=4;goto done;}
            } else if(spr_x[slot]!=0xaa00u+slot || spr_y[slot]!=0xa0u+slot ||
                      spr_active[slot]!=0x80u+slot) {error=5;goto done;}
        }
        ++calls;
    }
done: finished();for(;;){}return 0;
}
''')
        marker = work/'marker.s'
        marker.write_text('''.export _read_sp,_read_hwsp,_finished
.importzp sp
.code
_read_sp: lda sp
 ldx sp+1
 rts
_read_hwsp: tsx
 txa
 ldx #0
 rts
_finished: rts
''')
        disk = build(work, source, extra_sources=[marker])
        labels = a2test.labels(work/'test.lbl')
        result = a2test.run(disk, [labels.until('_finished', 100000),
                                 labels.peek('_error'), labels.peek('_calls', 2)], iie=args.iie)
        assert result.mem(labels['_error'], 1) == b'\0', result.dumps
        assert int.from_bytes(result.mem(labels['_calls'], 2), 'little') == 20480
        print(f'Sprite move: 20,480 calls, all IDs, counts 0/1/2/8, null/low/high/full '
              f'shape pointers, full coordinate domain boundaries, untouched slots '
              f'and both stacks OK; IIe={args.iie}.')


if __name__ == '__main__':
    main()
