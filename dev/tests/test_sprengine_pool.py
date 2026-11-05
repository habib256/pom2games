#!/usr/bin/env python3
"""Save-under pointer arithmetic for all capacities and positive slot counts."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, a2test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='sprengine-pool-') as directory:
        work = Path(directory)
        source = work/'pool.c'
        source.write_text('''#include "hgr.h"
extern unsigned char spr_capacity;
unsigned __fastcall__ advance(unsigned char n);unsigned advance_one(void);
void finished(void);
unsigned origin,calls;
unsigned char error;
static const unsigned starts[]={0,0x00ff,0x3ff8,0xfff0};
static unsigned cap,expected;
static unsigned char i,n;
int main(void) {
    for(i=0;i<4;++i)for(cap=1;cap<=255;++cap) {
        origin=starts[i];spr_capacity=(unsigned char)cap;expected=origin;
        for(n=1;n<=8;++n) {
            expected+=cap;
            if(advance(n)!=expected) {error=1;goto done;}
            ++calls;
        }
        if(advance_one()!=(unsigned)(origin+cap)) {error=2;goto done;}
        ++calls;
    }
done: finished();for(;;){}return 0;
}
''')
        kernel = work/'kernel.s'
        kernel.write_text((DEV/'lib/hgrc/hgr_sprengine_asm.s').read_text()+'''
; Test-only access to the private helpers, using their actual RAM pointer.
.import _origin
.export _advance,_advance_one,_finished
_advance:
 tax
 jsr load_pointer
 jsr add_under_n
 jmp return_pointer
_advance_one:
 jsr load_pointer
 jsr add_under
return_pointer:
 lda under
 ldx under+1
 rts
load_pointer:
 lda _origin
 sta under
 lda _origin+1
 sta under+1
 rts
_finished: rts
''')
        disk = build(work, source, extra_sources=[kernel])
        labels = a2test.labels(work/'test.lbl')
        result = a2test.run(disk, [labels.until('_finished', 30000),
                                 labels.peek('_error'), labels.peek('_calls', 2)], iie=args.iie)
        assert result.mem(labels['_error'], 1) == b'\0', result.dumps
        assert int.from_bytes(result.mem(labels['_calls'], 2), 'little') == 9180
        print(f'Sprite pool: 9,180 calls, capacities 1..255, slots 1..8 and single '
              f'advance, page crossings and 16-bit wrap OK; IIe={args.iie}.')


if __name__ == '__main__':
    main()
