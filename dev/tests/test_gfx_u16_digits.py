#!/usr/bin/env python3
"""Optional 65C02 digits: every input, decimal/IRQ flags and hostile scratch."""
import argparse
from pathlib import Path
import tempfile
from test_hgr import DEV, build, a2test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path,
                        help='test a saved reference assembly source instead of the current kernel')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-u16-digits-') as directory:
        work = Path(directory)
        kernel = work / 'kernel.s'
        kernel.write_bytes((args.reference or DEV / 'lib/gfx/gfx_u16_digits.s').read_bytes())
        source = work / 'entry.c'
        source.write_text(r'''#include "gfx.h"
void ready(void);void digits_done(void);
const char *__fastcall__ probe(unsigned n);
unsigned char inputs[2],flags,seen,records[1536];
static void fail(void) {for (;;) {}}
int main(void) {
    unsigned value,k;
    unsigned char i,j;
    const char *p,*last=0;
    volatile unsigned guard=0xa55a;
    for (;;) {
        ready();value=(unsigned)inputs[0]<<8;k=0;i=0;
        do {
            /* Every value sees all D/I combinations. Also alternate C/V. */
            flags=inputs[1]|(i&1u)|((i&2u)<<5);
            p=probe(value+i);
            if (seen!=flags||(last&&p!=last)||guard!=0xa55a) fail();
            last=p;
            for (j=0;j<6;++j) records[k++]=p[j];
            ++i;
        } while (i);
        digits_done();
    }
    return 0;
}
''')
        helpers = work / 'helpers.s'
        helpers.write_text('''.setcpu "65C02"
.export _ready,_digits_done,resume,_probe
.import _gfx_u16_digits,_flags,_seen
.importzp sp,ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4
.bss
input: .res 2
saved_sp: .res 2
saved_hw: .res 1
.code
_ready: rts
_digits_done: nop
resume: rts
_probe:
 php
 sta input
 stx input+1
 lda sp
 sta saved_sp
 lda sp+1
 sta saved_sp+1
 tsx
 stx saved_hw
 lda #$a5
'''+''.join(f' sta {name}\n' for name in
            ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1',
             'tmp1','tmp2','tmp3','tmp4'))+''' lda _flags
 pha
 plp
 lda input
 ldx input+1
 jsr _gfx_u16_digits
 sta ptr4
 stx ptr4+1
 php
 pla
 and #$4d
 sta _seen
 tsx
 cpx saved_hw
 bne fail
 lda sp
 cmp saved_sp
 bne fail
 lda sp+1
 cmp saved_sp+1
 bne fail
 plp
 lda ptr4
 ldx ptr4+1
 rts
fail: jmp fail
''')
        disk = build(work, source, extra_sources=(helpers, kernel))
        labels = a2test.labels(work / 'test.lbl')
        calls = 0
        for batch in range(0, 256, 32):
            steps = []
            expected = bytearray()
            for high in range(batch, batch + 32):
                for flags in (0, 4, 8, 12):
                    inputs = work / f'input-{high}-{flags}.bin'
                    inputs.write_bytes(bytes((high, flags)))
                    steps.extend((labels.until('_ready'),
                                  f'load:{inputs}@{labels["_inputs"]:04X}',
                                  labels.until('_digits_done', limit=10000),
                                  labels.peek('_records', 1536), labels.until('resume')))
                    expected.extend(b''.join(f'{high * 256 + low:05}\0'.encode()
                                             for low in range(256)))
                    calls += 256
            result = a2test.run(disk, steps, iie=True, timeout=180)
            assert result.data == expected, ('five digits and NUL', batch)
        print(f'GFX 65C02 digits: {calls:,} exact conversions, every 16-bit input '
              'and D/I combination, C/V preservation, stable buffer, hostile scratch, '
              f'caller guard and both stacks; reference={bool(args.reference)}.')


if __name__ == '__main__':
    main()
